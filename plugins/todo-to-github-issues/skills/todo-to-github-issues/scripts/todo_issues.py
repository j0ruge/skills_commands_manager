#!/usr/bin/env python3
"""Mirror every open finding of an sdd-style TODO.md as a GitHub issue — idempotent.

The findings are the items of the section marked `<!-- sdd:open -->` (the kit's two-section
skeleton, templates/todo.md), up to the next `## `; its `###` headings are the sections that become
labels. Nothing outside it is read: not the preamble, not the decided records, not a narrative.

The file stays the source of truth. Each issue carries two hidden markers:
  <!-- todo-key: K -->   identity of the item (hash of its title; retitling = new identity)
  <!-- todo-hash: H -->  hash of title + section + text, so a re-run edits only what changed

Default is a PLAN (read-only). --apply creates and updates; --close-orphans also closes the
issues whose item left the file (in the sdd convention a closed finding is DELETED).

Usage:
  python3 todo_issues.py [--file TODO.md] [--repo OWNER/NAME]            # plan, touches nothing
  python3 todo_issues.py --apply --limit 1                                # canary: one issue
  python3 todo_issues.py --apply [--close-orphans]                        # the rest
  python3 todo_issues.py --audit                                          # format: what is off
  python3 todo_issues.py --fix [--write]                                  # format: fix the mechanical part
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field

import kit

ITEM_RE = re.compile(r"^- \[ \] \*\*")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{2,6})\s+(.*?)\s*#*\s*$")
DATE_TAIL_RE = re.compile(r"\(\d{4}-\d{2}-\d{2}\)\s*$")
# `RESOLVED by <hash>` in the BODY closes an item; the bare phrase inside backticks (an item
# ABOUT the convention) must not. The token is the kit's, English in every OUTPUT_LANG.
RESOLVED_RE = re.compile(r"RESOLVED by\**\s+`?[0-9a-f]{7,40}\b")
ANCHOR_RE = re.compile(r"`([A-Za-z0-9_./-]+):(\d+)(?:-(\d+))?`")
KEY_RE = re.compile(r"<!-- todo-key: ([0-9a-f]+) -->")
HASH_RE = re.compile(r"<!-- todo-hash: ([0-9a-f]+) -->")
SRC_RE = re.compile(r"<!-- todo-src: (.+?) -->")
# issues created before the src marker existed name their file only in the footer link
LEGACY_SRC_RE = re.compile(r"Espelho do item de \[`([^`]+)`\]")


def issue_source(body: str) -> str | None:
    m = SRC_RE.search(body) or LEGACY_SRC_RE.search(body)
    return m.group(1) if m else None

LABEL_ROOT = "todo"
LABEL_ROOT_COLOR = "c5def5"
LABEL_SECTION_COLOR = "ededed"
TITLE_MAX = 250
PACE_S = 1.0


@dataclass
class Item:
    start: int
    end: int
    section: str
    raw: list[str]
    title: str = ""
    rest: str = ""
    resolved: bool = False
    key: str = ""
    digest: str = ""
    anchor: tuple[str, int, int | None] | None = None


@dataclass
class Plan:
    create: list[Item] = field(default_factory=list)
    update: list[tuple[Item, dict]] = field(default_factory=list)
    ok: list[tuple[Item, dict]] = field(default_factory=list)
    skip_resolved: list[Item] = field(default_factory=list)
    closed_present: list[tuple[Item, dict]] = field(default_factory=list)
    orphans: list[dict] = field(default_factory=list)
    dup_issues: list[tuple[str, list[int]]] = field(default_factory=list)
    renames: list[tuple[dict, Item, float]] = field(default_factory=list)


def sh(*cmd: str, check: bool = True, cwd: str | None = None) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=False)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:4])}… rc={r.returncode}: {r.stderr.strip()}")
    return r.stdout


def outside_code_rfind(text: str, needle: str) -> int:
    """Last index of needle that is not inside a `code span`."""
    pos, in_code, last = 0, False, -1
    while pos < len(text):
        if text[pos] == "`":
            in_code = not in_code
            pos += 1
            continue
        if not in_code and text.startswith(needle, pos):
            last = pos
        pos += 1
    return last


class NoOpenMarker(Exception):
    """The file has no `<!-- sdd:open -->` under a `## ` — it predates the skeleton."""


def parse(path: str) -> list[Item]:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    start = kit.open_marker_line(lines)
    if start is None:
        raise NoOpenMarker(path)
    items: list[Item] = []
    section, in_fence, cur = "", False, None

    def close():
        nonlocal cur
        if cur is not None:
            while cur.raw and not cur.raw[-1].strip():
                cur.raw.pop()
            cur.end = cur.start + len(cur.raw) - 1
            items.append(cur)
            cur = None

    for n, line in enumerate(lines, 1):
        if n <= start + 1:
            continue  # the preamble and the marker itself
        if line.startswith("## ") and not in_fence:
            break  # the open section ends at the next `##` — never at the end of the file
        if FENCE_RE.match(line):
            close()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if ITEM_RE.match(line):
            close()
            cur = Item(start=n, end=n, section=section, raw=[line])
            continue
        if cur is not None and (not line.strip() or line[:1] in (" ", "\t")):
            cur.raw.append(line)
            continue
        close()
        m = HEADING_RE.match(line)
        if m:
            section = m.group(2)  # `###` and deeper: a `## ` already ended the loop
    close()

    for it in items:
        text = " ".join(l.strip() for l in it.raw if l.strip())[len("- [ ] **"):]
        end = text.find("**")
        if end < 0:
            raise SystemExit(f"TODO line {it.start}: title opens `**` and never closes it")
        it.title = re.sub(r"\s+", " ", text[:end]).strip()
        it.rest = text[end + 2:].strip()
        if it.rest.startswith("—"):
            it.rest = it.rest[1:].strip()
        it.resolved = bool(RESOLVED_RE.search(it.rest))
        m = ANCHOR_RE.match(it.rest)
        if m:
            it.anchor = (m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else None)

    seen: dict[str, int] = {}
    for it in items:
        norm = it.title.casefold()
        seen[norm] = seen.get(norm, 0) + 1
        ident = norm if seen[norm] == 1 else f"{norm}#{seen[norm]}"
        it.key = hashlib.sha1(ident.encode()).hexdigest()[:12]
        payload = f"{it.title}\n{it.section}\n{it.rest}"
        it.digest = hashlib.sha1(payload.encode()).hexdigest()[:12]
    return items


def detect_format(text: str, path: str = "") -> str:
    """The open marker decides first: a TODO.md may name a category `### 1. Bloqueia`, and the
    numbered-heading test alone would read it as a findings report. Then the NAME: a file called
    TODO*.md is the backlog by definition, whatever its narratives number — a legacy one without
    the marker must reach the sensor's refusal (rc 4), not be mirrored as a report. `--format
    report` still forces it."""
    if kit.open_marker_line(text.split("\n")) is not None:
        return "todo"
    if os.path.basename(path).upper().startswith("TODO"):
        return "todo"
    return "report" if re.search(r"^### \d+\.\s", text, re.MULTILINE) else "todo"


def sensor_gate(root: str, path: str, items: list[Item]) -> int:
    """0 when the kit's sensor accepts the file AND counts what `parse` counts; else the rc to
    exit with. Two parsers answering the same question is how they drift, so the mirror never
    trusts its own count alone."""
    rc, out = kit.run_sensor(root, "--check", path, "--allow-empty")
    if rc == 99:
        print(f"FAIL  {path} has no `{kit.OPEN_MARKER}` marker — it predates the kit's two-section "
              "skeleton, and the findings section is never guessed.\n"
              f"      Run --audit to see what is off and --fix to add it.", file=sys.stderr)
        return 4
    if rc != 0:
        print(f"FAIL  the kit's sensor refuses {path} (rc {rc}) — mirroring a malformed file would "
              f"copy its defects into the issues. Run --audit.\n{out.rstrip()}", file=sys.stderr)
        return 4
    rc, out = kit.run_sensor(root, "--count", path)
    if rc != 0 or out.strip() != str(len(items)):
        print(f"FAIL  parser drift: the kit's sensor counts {out.strip() or '?'} finding(s), this "
              f"script parsed {len(items)} — stop before mirroring either number", file=sys.stderr)
        return 5
    return 0


def section_label(section: str) -> str | None:
    if not section:
        return None
    short = section.split(" — ")[0].strip()
    return f"{LABEL_ROOT}: {_label_safe(short)}"[:50]


def _label_safe(text: str) -> str:
    """Troca a vírgula, que o GitHub recusa em nome de label, por ` ·`.

    Medido em 2026-09-24 no JRC-Brasil/sales_quote: `todo: Aprovação, pendências e ciclo da
    cotação` respondia 422 `Label.name is invalid`, e o mesmo nome sem a vírgula passava. O teto
    de 50 é de CARACTERES (50 caracteres com 97 bytes foram aceitos), então o `[:50]` fica.

    @param text Nome curto da seção (antes do ` — `).
    @returns O nome sem vírgula; sem vírgula na entrada, volta idêntico.
    """
    return text.replace(", ", " · ").replace(",", " ·")


@dataclass
class Ctx:
    repo: str
    root: str
    relpath: str
    sha: str | None  # commit that permalinks point at; None = no stable permalink
    branch: str


def context(path: str, repo: str | None) -> Ctx:
    d = os.path.dirname(os.path.abspath(path))
    root = sh("git", "-C", d, "rev-parse", "--show-toplevel").strip()
    relpath = os.path.relpath(os.path.abspath(path), root)
    if not repo:
        repo = json.loads(sh("gh", "repo", "view", "--json", "nameWithOwner", cwd=root))["nameWithOwner"]
    branch = json.loads(sh("gh", "repo", "view", repo, "--json", "defaultBranchRef"))["defaultBranchRef"]["name"]
    sha = sh("git", "-C", root, "rev-parse", "HEAD").strip()
    pushed = sh("git", "-C", root, "branch", "-r", "--contains", sha, check=False).strip()
    # `git diff` is silent about an untracked file, so tracked-at-HEAD is its own condition
    tracked = subprocess.run(["git", "-C", root, "cat-file", "-e", f"{sha}:{relpath}"],
                             capture_output=True, check=False).returncode == 0
    clean = tracked and subprocess.run(
        ["git", "-C", root, "diff", "--quiet", "HEAD", "--", relpath], check=False).returncode == 0
    if not (pushed and clean):
        why = "HEAD is not on any remote branch" if not pushed else f"{relpath} differs from HEAD"
        print(f"warn  no line permalinks: {why} — links point at `{branch}` without line numbers",
              file=sys.stderr)
        sha = None
    return Ctx(repo=repo, root=root, relpath=relpath, sha=sha, branch=branch)


def blob(ctx: Ctx, path: str, lines: tuple[int, int | None] | None = None) -> str:
    ref = ctx.sha or ctx.branch
    url = f"https://github.com/{ctx.repo}/blob/{ref}/{path}"
    if ctx.sha and lines:
        a, b = lines
        url += f"#L{a}" + (f"-L{b}" if b and b != a else "")
    return url


MENTION_RE = re.compile(r"(?<![\w.])@(?=[A-Za-z0-9])")


def defang(md: str) -> str:
    """A mirrored `@name` would notify that person, and a bot reads it even inside backticks
    (`@codex review` in a finding made the Codex connector reply on the issue). A zero-width space
    after the @ keeps the text as it reads and takes the mention away."""
    return MENTION_RE.sub("@\u200b", md)


REL_LINK_RE = re.compile(r"\]\((?!https?://|mailto:|#|/)([^)\s]+)\)")


def absolutize(md: str, ctx: Ctx) -> str:
    """A relative link resolves against the ISSUE url, not the file. Point it where GitHub's own
    view of the file would: the same path, relative to the file's directory, at the permalink ref."""
    def fix(m: re.Match) -> str:
        target, _, frag = m.group(1).partition("#")
        path = os.path.normpath(os.path.join(os.path.dirname(ctx.relpath), target))
        return f"]({blob(ctx, path)}{'#' + frag if frag else ''})"
    return REL_LINK_RE.sub(fix, md)


def render_body(it: Item, ctx: Ctx) -> str:
    rest = it.rest
    parts: list[str] = []
    if it.anchor:
        path, a, b = it.anchor
        token = f"`{path}:{a}" + (f"-{b}" if b else "") + "`"
        exists = ctx.sha and subprocess.run(
            ["git", "-C", ctx.root, "cat-file", "-e", f"{ctx.sha}:{path}"],
            capture_output=True, check=False).returncode == 0
        parts.append(f"**Âncora:** [{token}]({blob(ctx, path, (a, b))})" if exists else f"**Âncora:** {token}")
        if rest.startswith(token):
            rest = rest[len(token):].lstrip()
            if rest.startswith("—"):
                rest = rest[1:].lstrip()
    cut = outside_code_rfind(rest, " — ")
    tail = rest[cut + 3:] if cut >= 0 else ""
    if cut >= 0 and DATE_TAIL_RE.search(tail):
        parts += [rest[:cut].strip(), f"— {tail.strip()}"]
    else:
        parts.append(rest)
    src = blob(ctx, ctx.relpath, (it.start, it.end))
    sec = f" · seção *{it.section}*" if it.section else ""
    parts[:] = [defang(absolutize(x, ctx)) for x in parts]
    parts.append("---")
    parts.append(f"<sub>Espelho do item de [`{ctx.relpath}`]({src}){sec}. O arquivo é a fonte da "
                 f"verdade: edite lá e sincronize de novo; o item apagado fecha esta issue.</sub>")
    parts.append(f"<!-- todo-key: {it.key} -->\n<!-- todo-hash: {it.digest} -->\n<!-- todo-src: {ctx.relpath} -->")
    return "\n\n".join(parts) + "\n"


def issue_title(it: Item) -> str:
    return it.title if len(it.title) <= TITLE_MAX else it.title[:TITLE_MAX - 1].rstrip() + "…"


def fetch_issues(repo: str) -> list[dict]:
    out = sh("gh", "issue", "list", "--repo", repo, "--state", "all", "--limit", "5000",
             "--json", "number,title,body,state,labels,url")
    return json.loads(out)


def build_plan(items: list[Item], issues: list[dict], relpath: str = "TODO.md") -> Plan:
    """Only issues mirrored FROM relpath take part: another file's mirror is never an orphan here."""
    plan = Plan()
    by_key: dict[str, list[dict]] = {}
    for iss in issues:
        body = iss.get("body") or ""
        m = KEY_RE.search(body)
        if m and issue_source(body) == relpath:
            by_key.setdefault(m.group(1), []).append(iss)
    for k, lst in by_key.items():
        if len(lst) > 1:
            plan.dup_issues.append((k, sorted(i["number"] for i in lst)))
    keys = set()
    for it in items:
        keys.add(it.key)
        found = by_key.get(it.key)
        if not found:
            (plan.skip_resolved if it.resolved else plan.create).append(it)
            continue
        iss = min(found, key=lambda i: i["number"])
        m = HASH_RE.search(iss.get("body") or "")
        if iss["state"] != "OPEN":
            plan.closed_present.append((it, iss))
        elif not m or m.group(1) != it.digest:
            plan.update.append((it, iss))
        else:
            plan.ok.append((it, iss))
    for k, lst in by_key.items():
        if k not in keys:
            plan.orphans += [i for i in lst if i["state"] == "OPEN"]
    return plan


def prose(body: str) -> str:
    """The item's own text inside a rendered body: no footer, no markers, no links."""
    body = body.split("\n---\n")[0]
    return re.sub(r"\]\([^)]*\)", "]", body)


def guess_renames(plan: Plan, ctx: Ctx, threshold: float = 0.85) -> None:
    """A retitled item reads as ORPHAN + CREATE; pair them when the text barely moved."""
    for iss in plan.orphans:
        old = prose(iss.get("body") or "")
        best = max(((difflib.SequenceMatcher(None, old, prose(render_body(it, ctx))).ratio(), it)
                    for it in plan.create), key=lambda x: x[0], default=(0.0, None))
        if best[1] is not None and best[0] >= threshold:
            plan.renames.append((iss, best[1], best[0]))


def gh_mut(*cmd: str) -> str:
    for attempt in range(4):
        r = subprocess.run(["gh", *cmd], capture_output=True, text=True, check=False)
        if r.returncode == 0:
            time.sleep(PACE_S)
            return r.stdout.strip()
        if "rate limit" in r.stderr.lower() and attempt < 3:
            wait = 60 * (attempt + 1)
            print(f"      rate limited, waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        raise RuntimeError(f"gh {' '.join(cmd[:3])}… rc={r.returncode}: {r.stderr.strip()}")
    raise AssertionError("unreachable")


def ensure_labels(repo: str, names: set[str]) -> None:
    have = {l["name"] for l in json.loads(sh("gh", "label", "list", "--repo", repo,
                                             "--limit", "500", "--json", "name"))}
    for name in sorted(names - have):
        color = LABEL_ROOT_COLOR if name == LABEL_ROOT else LABEL_SECTION_COLOR
        desc = "Espelho de um item do TODO.md" if name == LABEL_ROOT else "Seção do TODO.md"
        gh_mut("label", "create", name, "--repo", repo, "--color", color, "--description", desc)
        print(f"label {name}")


def gh_with_body(body: str, *cmd: str) -> str:
    """gh_mut with the body passed through a temp file (argv would choke on long markdown)."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(body)
        name = fh.name
    try:
        return gh_mut(*cmd, "--body-file", name)
    finally:
        os.unlink(name)


def short(s: str, n: int = 90) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default="TODO.md")
    ap.add_argument("--repo", help="OWNER/NAME (default: the file's repo, via gh)")
    ap.add_argument("--apply", action="store_true", help="create and update issues")
    ap.add_argument("--close-orphans", action="store_true",
                    help="with --apply: close open issues whose item left the file")
    ap.add_argument("--limit", type=int, default=0, help="with --apply: at most N creations (canary)")
    ap.add_argument("--dump", metavar="DIR", help="write every rendered body to DIR, touch nothing")
    ap.add_argument("--format", choices=("auto", "todo", "report"), default="auto",
                    help="report = `### N. <title>` findings report (auto: any such heading)")
    ap.add_argument("--link", action="append", metavar="KEY=ISSUE",
                    help="report: an open finding already tracked by ISSUE gets a comment there; "
                         "KEY is the finding number or an unnumbered section's heading prefix")
    ap.add_argument("--open-unlinked", action="store_true",
                    help="report: open a new issue for each open finding without --link")
    ap.add_argument("--audit", action="store_true",
                    help="format: report what is off against the kit's skeleton, touch nothing")
    ap.add_argument("--fix", action="store_true",
                    help="format: show the diff of the mechanical fixes (add --write to apply)")
    ap.add_argument("--write", action="store_true", help="with --fix: write the fixed file")
    ap.add_argument("--open-heading", metavar="TEXT",
                    help="format: the existing `## TEXT` that holds the findings, when --audit cannot tell")
    ap.add_argument("--lang", metavar="LANG",
                    help="format: the seed language when the repo declares no OUTPUT_LANG (e.g. pt-BR)")
    a = ap.parse_args()
    if a.close_orphans and not a.apply:
        ap.error("--close-orphans needs --apply")
    if a.write and not a.fix:
        ap.error("--write needs --fix")
    if (a.audit or a.fix) and (a.apply or a.dump or a.link or a.open_unlinked):
        ap.error("--audit/--fix work on the file only; mirror in a separate run")

    if a.audit or a.fix:
        root = kit.preflight(need_gh=False, need_kit=True)
        import todo_format
        return todo_format.run(a, root)

    with open(a.file, encoding="utf-8") as fh:
        text = fh.read()
    fmt = a.format if a.format != "auto" else detect_format(text, a.file)
    if fmt == "report":
        if a.close_orphans:
            ap.error("--close-orphans is TODO mode only: a report is a snapshot, nothing leaves it")
        kit.preflight(need_gh=True, need_kit=False)
        import report
        return report.run(a, context(a.file, a.repo))
    if a.link or a.open_unlinked:
        ap.error("--link/--open-unlinked are report mode only")

    root = kit.preflight(need_gh=True, need_kit=True)
    try:
        items = parse(a.file)
    except NoOpenMarker:
        items = []
    rc = sensor_gate(root, a.file, items)
    if rc:
        return rc
    if not items:
        print(f"FAIL  0 items parsed from {a.file} — refusing to plan against an empty file "
              "(every existing issue would read as an orphan)", file=sys.stderr)
        return 2
    ctx = context(a.file, a.repo)

    if a.dump:
        os.makedirs(a.dump, exist_ok=True)
        for it in items:
            with open(os.path.join(a.dump, f"L{it.start:04d}-{it.key}.md"), "w", encoding="utf-8") as fh:
                fh.write(f"# {issue_title(it)}\n\n{render_body(it, ctx)}")
        print(f"dumped {len(items)} bodies to {a.dump}")
        return 0

    plan = build_plan(items, fetch_issues(ctx.repo), ctx.relpath)
    guess_renames(plan, ctx)
    print(f"repo {ctx.repo} · file {ctx.relpath} · {len(items)} items · permalinks at "
          f"{ctx.sha[:7] if ctx.sha else ctx.branch}")
    for k, nums in plan.dup_issues:
        print(f"DUP     key {k} is on issues {nums} — the lowest number wins; close the others by hand")
    for it in plan.create:
        print(f"CREATE  L{it.start:<4} {short(it.title)}")
    for it, iss in plan.update:
        print(f"UPDATE  #{iss['number']:<4} L{it.start:<4} {short(it.title)}")
    for it in plan.skip_resolved:
        print(f"SKIP    L{it.start:<4} RESOLVED by, no issue to mirror — {short(it.title, 60)}")
    for it, iss in plan.closed_present:
        print(f"CLOSED  #{iss['number']:<4} L{it.start:<4} issue closed but the item is still in the file")
    for iss in plan.orphans:
        verb = "CLOSE " if a.close_orphans else "ORPHAN"
        print(f"{verb}  #{iss['number']:<4} item left the file — {short(iss['title'], 70)}")
    for iss, it, r in plan.renames:
        old = KEY_RE.search(iss["body"]).group(1)
        print(f"RENAME? #{iss['number']} ↔ L{it.start} ({r:.0%} same text) — to keep the issue instead of "
              f"closing it and opening a new one, rekey it BEFORE --apply:\n"
              f"        gh issue view {iss['number']} -R {ctx.repo} --json body -q .body | "
              f"sed 's/todo-key: {old}/todo-key: {it.key}/' | gh issue edit {iss['number']} -R {ctx.repo} --body-file -")
    print(f"summary create={len(plan.create)} update={len(plan.update)} ok={len(plan.ok)} "
          f"skip={len(plan.skip_resolved)} closed-present={len(plan.closed_present)} "
          f"orphans={len(plan.orphans)} dup={len(plan.dup_issues)}")
    if not a.apply:
        print("plan only — rerun with --apply (try --limit 1 first)")
        return 0

    todo = plan.create[: a.limit] if a.limit else plan.create
    wanted = {section_label(it.section) for it in todo + [u for u, _ in plan.update]}
    ensure_labels(ctx.repo, {LABEL_ROOT} | {l for l in wanted if l})
    for it in todo:
        labels = ["--label", LABEL_ROOT]
        lab = section_label(it.section)
        if lab:
            labels += ["--label", lab]
        url = gh_with_body(render_body(it, ctx), "issue", "create", "--repo", ctx.repo,
                           "--title", issue_title(it), *labels)
        print(f"created {url}")
    for it, iss in plan.update:
        want = section_label(it.section)
        old = [l["name"] for l in iss["labels"] if l["name"].startswith(f"{LABEL_ROOT}: ") and l["name"] != want]
        lab = (["--add-label", want] if want else []) + [x for o in old for x in ("--remove-label", o)]
        gh_with_body(render_body(it, ctx), "issue", "edit", str(iss["number"]), "--repo", ctx.repo,
                     "--title", issue_title(it), *lab)
        print(f"updated #{iss['number']}")
    if a.close_orphans:
        ref = ctx.sha[:7] if ctx.sha else ctx.branch
        for iss in plan.orphans:
            gh_mut("issue", "close", str(iss["number"]), "--repo", ctx.repo, "--comment",
                   f"O item saiu de `{ctx.relpath}` em `{ref}` — neste formato, achado fechado é apagado do arquivo.")
            print(f"closed #{iss['number']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
