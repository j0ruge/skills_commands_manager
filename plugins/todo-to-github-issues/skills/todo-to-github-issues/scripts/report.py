"""Report mode: a findings report (`### N. <title>` sections + a routing table) -> GitHub issues.

A report is a dated snapshot, not a backlog: most of its findings are already closed, and the
open ones were routed to a tracker that has its own issue. So, per finding:
  closed (routing table says RESOLVIDO/RESOLVED/FIXED)  -> issue created already CLOSED as completed
  open + --link N=<issue>                               -> one comment on that issue, text in <details>
  open without a link                                   -> LINK? in the plan; --open-unlinked opens one
Markers: <!-- report-key: <file-stem>#<N> --> in the issue body or comment, plus a report-hash.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

import todo_issues as t

NUM_RE = re.compile(r"^### (\d+)\.\s+(.+?)\s*$")
SEC_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
CLOSED_RE = re.compile(r"^\W*(RESOLVIDO|RESOLVED|FECHADO|FIXED)\b", re.IGNORECASE)
STATUS_RE = re.compile(r"^\W*(RESOLVIDO|RESOLVED|FECHADO|FIXED|PARCIAL|PARTIAL|ROTEADO|ROUTED)\b", re.IGNORECASE)
SHA_RE = re.compile(r"`([0-9a-f]{7,40})`")
LIST_RE = re.compile(r"^\s*([-*+]|\d+\.)\s")
HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
# a continuation line that opens one of these keeps its own line instead of joining the paragraph
BREAK_RE = re.compile(r"^(— |RESOLVIDO|PARCIAL|ROTEADO|\*\*(RESOLVIDO|ROTEADO|PARCIAL))")
RKEY_RE = re.compile(r"<!-- report-key: (.+?) -->")
RHASH_RE = re.compile(r"<!-- report-hash: ([0-9a-f]+) -->")
LABEL_COLOR = "f9d0c4"


@dataclass
class Finding:
    key: str
    title: str
    start: int
    end: int
    lines: list[str]
    status: str = "unknown"  # closed | open | unknown
    outcome: str = ""
    evidence: list[str] = field(default_factory=list)
    digest: str = ""


def section_spans(lines: list[str]) -> list[tuple[int, int, int, str]]:
    """(level, start, end, heading) for every ##/### outside fences; a section ends at the next one."""
    heads, in_fence = [], False
    for n, line in enumerate(lines, 1):
        if t.FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence and (m := SEC_RE.match(line)):
            heads.append((len(m.group(1)), n, m.group(2)))
    out = []
    for i, (lvl, n, text) in enumerate(heads):
        end = heads[i + 1][1] - 1 if i + 1 < len(heads) else len(lines)
        out.append((lvl, n, end, text))
    return out


def routing_table(lines: list[str]) -> dict[str, tuple[str, list[str]]]:
    """First table whose header starts with `#`: key -> (outcome cell, evidence shas)."""
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else []
        if not cells or cells[0] != "#":
            continue
        low = [c.lower() for c in cells]
        oi = next((j for j, c in enumerate(low) if c in ("desfecho", "status", "outcome", "estado", "resultado")), None)
        ei = next((j for j, c in enumerate(low) if c in ("evidência", "evidencia", "evidence")), None)
        if oi is None:
            continue
        rows = {}
        for row in lines[i + 2:]:
            if not row.lstrip().startswith("|"):
                break
            c = [x.strip() for x in row.strip().strip("|").split("|")]
            if len(c) > oi:
                rows[c[0]] = (c[oi], SHA_RE.findall(c[ei]) if ei is not None and len(c) > ei else [])
        return rows
    return {}


def body_lines(lines: list[str], start: int, end: int) -> list[str]:
    body = lines[start:end]  # start is the heading's 1-based line, so this skips the heading
    while body and (not body[-1].strip() or HR_RE.match(body[-1].strip())):
        body.pop()
    while body and not body[0].strip():
        body.pop(0)
    return body


def parse_report(path: str) -> tuple[list[Finding], list[tuple[int, int, int, str]], list[str]]:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    spans = section_spans(lines)
    table = routing_table(lines)
    found = []
    for _lvl, start, end, text in spans:
        m = NUM_RE.match(f"### {text}") if _lvl == 3 else None
        if not m:
            continue
        f = Finding(key=m.group(1), title=m.group(2), start=start, end=end,
                    lines=body_lines(lines, start, end))
        if f.key in table:
            f.outcome, f.evidence = table[f.key]
            f.status = "closed" if CLOSED_RE.match(f.outcome) else "open"
        else:
            for ln in f.lines:
                if (s := STATUS_RE.match(ln.strip())):
                    f.status = "closed" if CLOSED_RE.match(s.group(0)) else "open"
                    f.outcome = ln.strip()[:120]
                    break
        found.append(f)
    for f in found:
        payload = "\n".join([f.title, f.outcome, " ".join(f.evidence), *f.lines])
        f.digest = hashlib.sha1(payload.encode()).hexdigest()[:12]
    return found, spans, lines


def unwrap(lines: list[str], ctx: t.Ctx | None = None) -> str:
    """Hard-wrapped markdown -> GitHub issue markdown, where every single newline renders as <br>.
    Paragraphs, list items and quotes are joined; fences, tables, headings and rules stay as-is."""
    out: list[str] = []
    in_fence, prev, last_list = False, "blank", False
    for raw in lines:
        line = raw.rstrip()
        s = line.strip()
        if t.FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            prev = "block"
            continue
        if in_fence:
            out.append(line)
            continue
        line = t.defang(t.absolutize(line, ctx) if ctx else line)
        s = line.strip()
        if not s:
            out.append("")
            prev = "blank"
            continue
        if s.startswith(("|", "#")) or HR_RE.match(s):
            out.append(line)
            prev, last_list = "block", False
            continue
        if s.startswith(">"):
            content = s[1:].strip()
            if content and prev == "quote":
                out[-1] += " " + content
            else:
                out.append(line)
            prev = "quote" if content else "quote-break"
            continue
        if LIST_RE.match(line):
            out.append(line)
            prev, last_list = "para", True
            continue
        if prev == "para":
            if BREAK_RE.match(s):
                indent = line[: len(line) - len(line.lstrip())]
                out.append(indent + s)
            else:
                out[-1] += " " + s
            continue
        indented = line[:1] == " "
        out.append(line if (indented and last_list) else s)
        prev = "para"
        if not indented:
            last_list = False
    return "\n".join(out).strip() + "\n"


def stem_of(ctx: t.Ctx) -> str:
    return os.path.splitext(os.path.basename(ctx.relpath))[0]


def label_of(ctx: t.Ctx) -> str:
    return ("achados: " + re.sub(r"^achados-", "", stem_of(ctx), flags=re.IGNORECASE))[:50]


def commit_link(ctx: t.Ctx, sha: str) -> str:
    r = subprocess.run(["git", "-C", ctx.root, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
                       capture_output=True, text=True, check=False)
    full = r.stdout.strip()
    on_remote = full and t.sh("git", "-C", ctx.root, "branch", "-r", "--contains", full, check=False).strip()
    return f"[`{sha}`](https://github.com/{ctx.repo}/commit/{full})" if on_remote else f"`{sha}`"


def outcome_line(f: Finding, ctx: t.Ctx, lead: str) -> str:
    parts = [lead]
    if f.outcome:
        parts.append(f"**Desfecho:** {f.outcome}")
    if f.evidence:
        parts.append("**Evidência:** " + " ".join(commit_link(ctx, s) for s in f.evidence))
    return " · ".join(parts)


def src_link(f: Finding, ctx: t.Ctx) -> str:
    return f"[`{ctx.relpath}`]({t.blob(ctx, ctx.relpath, (f.start, f.end))})"


def markers(f: Finding, ctx: t.Ctx) -> str:
    return f"<!-- report-key: {stem_of(ctx)}#{f.key} -->\n<!-- report-hash: {f.digest} -->"


def issue_body(f: Finding, ctx: t.Ctx) -> str:
    why = ("Registrado já fechado: foi resolvido antes de virar issue."
           if f.status == "closed" else "Aberto a partir do relatório.")
    return "\n\n".join([
        outcome_line(f, ctx, f"**Achado {f.key}** de {src_link(f, ctx)}"),
        unwrap(f.lines, ctx).rstrip(),
        "---",
        f"<sub>{why} O arquivo continua sendo a fonte.</sub>",
        markers(f, ctx),
    ]) + "\n"


def comment_body(f: Finding, ctx: t.Ctx) -> str:
    return "\n\n".join([
        outcome_line(f, ctx, f"**Origem:** achado {f.key} de {src_link(f, ctx)}"),
        f"<details>\n<summary>Texto do achado na origem — {t.defang(f.title)}</summary>",
        unwrap(f.lines, ctx).rstrip(),
        "</details>",
        markers(f, ctx),
    ]) + "\n"


def extra_findings(links: dict[str, int], spans, lines, have: set[str]) -> list[Finding]:
    """--link keys that are not finding numbers name an unnumbered section by heading prefix."""
    out = []
    for key in links:
        if key in have:
            continue
        hits = [(s, e, h) for _lvl, s, e, h in spans if h.casefold().startswith(key.casefold())]
        if len(hits) != 1:
            raise SystemExit(f"--link {key}=…: {len(hits)} section heading(s) start with that text, need exactly 1")
        s, e, h = hits[0]
        f = Finding(key=key, title=h, start=s, end=e, lines=body_lines(lines, s, e), status="open")
        f.digest = hashlib.sha1("\n".join([h, *f.lines]).encode()).hexdigest()[:12]
        out.append(f)
    return out


@dataclass
class RPlan:
    create: list[Finding] = field(default_factory=list)
    comment: list[tuple[Finding, int]] = field(default_factory=list)
    update: list[tuple[Finding, dict]] = field(default_factory=list)
    close: list[tuple[Finding, dict]] = field(default_factory=list)
    ok: list[tuple[Finding, str]] = field(default_factory=list)
    needs_link: list[Finding] = field(default_factory=list)


def build_rplan(found: list[Finding], issues: list[dict], links: dict[str, int],
                comments: dict[int, list[str]], stem: str, open_unlinked: bool) -> RPlan:
    p = RPlan()
    by_key: dict[str, dict] = {}
    for iss in sorted(issues, key=lambda i: i["number"]):
        m = RKEY_RE.search(iss.get("body") or "")
        if m:
            by_key.setdefault(m.group(1), iss)
    for f in found:
        k = f"{stem}#{f.key}"
        if f.key in links:
            n = links[f.key]
            if any(RKEY_RE.search(c) and RKEY_RE.search(c).group(1) == k for c in comments.get(n, [])):
                p.ok.append((f, f"comment on #{n}"))
            else:
                p.comment.append((f, n))
            continue
        iss = by_key.get(k)
        if iss:
            h = RHASH_RE.search(iss["body"] or "")
            if f.status == "closed" and iss["state"] == "OPEN":
                p.close.append((f, iss))
            if not h or h.group(1) != f.digest:
                p.update.append((f, iss))
            elif not (f.status == "closed" and iss["state"] == "OPEN"):
                p.ok.append((f, f"#{iss['number']}"))
        elif f.status == "closed" or open_unlinked:
            p.create.append(f)
        else:
            p.needs_link.append(f)
    return p


def run(a, ctx: t.Ctx) -> int:
    found, spans, lines = parse_report(a.file)
    links: dict[str, int] = {}
    for spec in a.link or []:
        key, _, num = spec.rpartition("=")
        if not key or not num.lstrip("#").isdigit():
            raise SystemExit(f"--link wants KEY=ISSUE, got {spec!r}")
        links[key] = int(num.lstrip("#"))
    found += extra_findings(links, spans, lines, {f.key for f in found})
    if not found:
        print(f"FAIL  0 findings parsed from {a.file} — no `### N. <title>` section", file=sys.stderr)
        return 2
    stem, label = stem_of(ctx), label_of(ctx)

    if a.dump:
        os.makedirs(a.dump, exist_ok=True)
        for f in found:
            body = comment_body(f, ctx) if f.key in links else issue_body(f, ctx)
            with open(os.path.join(a.dump, f"{stem}-{f.key}.md"), "w", encoding="utf-8") as fh:
                fh.write(f"# {f.title}\n\n{body}")
        print(f"dumped {len(found)} bodies to {a.dump}")
        return 0

    comments = {n: [c["body"] for c in json.loads(t.sh("gh", "issue", "view", str(n), "--repo", ctx.repo,
                                                         "--json", "comments"))["comments"]]
                for n in set(links.values())}
    p = build_rplan(found, t.fetch_issues(ctx.repo), links, comments, stem, a.open_unlinked)
    print(f"repo {ctx.repo} · report {ctx.relpath} · {len(found)} findings · label `{label}`")
    for f in p.create:
        print(f"CREATE  {f.status:<7} achado {f.key:<4} L{f.start:<4} {t.short(f.title, 80)}")
    for f, n in p.comment:
        print(f"COMMENT #{n:<5} ← achado {f.key:<4} {t.short(f.title, 70)}")
    for f, iss in p.update:
        print(f"UPDATE  #{iss['number']:<5} achado {f.key:<4} {t.short(f.title, 70)}")
    for f, iss in p.close:
        print(f"CLOSE   #{iss['number']:<5} achado {f.key:<4} resolved in the report, issue still open")
    for f in p.needs_link:
        print(f"LINK?   open    achado {f.key:<4} {t.short(f.title, 60)} — routed somewhere? "
              f"--link {f.key}=<issue>; or --open-unlinked")
    print(f"summary create={len(p.create)} comment={len(p.comment)} update={len(p.update)} "
          f"close={len(p.close)} ok={len(p.ok)} link?={len(p.needs_link)}")
    if not a.apply:
        print("plan only — rerun with --apply (try --limit 1 first)")
        return 0

    todo = p.create[: a.limit] if a.limit else p.create
    if todo:
        have = {x["name"] for x in json.loads(t.sh("gh", "label", "list", "--repo", ctx.repo,
                                                    "--limit", "500", "--json", "name"))}
        if label not in have:
            t.gh_mut("label", "create", label, "--repo", ctx.repo, "--color", LABEL_COLOR,
                     "--description", f"Achado de {ctx.relpath}"[:100])
            print(f"label {label}")
    for f in todo:
        url = t.gh_with_body(issue_body(f, ctx), "issue", "create", "--repo", ctx.repo,
                             "--title", t.issue_title(f), "--label", label)
        print(f"created {url}")
        if f.status == "closed":
            t.gh_mut("issue", "close", url.rsplit("/", 1)[1], "--repo", ctx.repo, "--reason", "completed")
            print("        closed as completed")
    for f, n in p.comment:
        print(f"commented {t.gh_with_body(comment_body(f, ctx), 'issue', 'comment', str(n), '--repo', ctx.repo)}")
    for f, iss in p.update:
        t.gh_with_body(issue_body(f, ctx), "issue", "edit", str(iss["number"]), "--repo", ctx.repo,
                       "--title", t.issue_title(f))
        print(f"updated #{iss['number']}")
    for f, iss in p.close:
        t.gh_mut("issue", "close", str(iss["number"]), "--repo", ctx.repo, "--reason", "completed")
        print(f"closed #{iss['number']}")
    return 0
