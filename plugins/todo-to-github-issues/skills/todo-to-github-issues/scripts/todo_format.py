"""Audit and fix the FORMAT of a TODO.md against the kit's two-section skeleton.

  --audit          what is off, split into AUTO (this script can fix it) and MANUAL (a human
                   decides); touches nothing
  --fix            the same, plus the unified diff of the AUTO fixes; touches nothing
  --fix --write    applies the AUTO fixes and re-runs the kit's sensor

AUTO is only what is deterministic and loses nothing: the marker under an unambiguous findings
heading, the decided section, `RESOLVIDO por` -> `RESOLVED by`, a bold title cut at the first
separator, an overlong physical line wrapped, the untouched legacy seed replaced, and a ticked
item deleted ONLY when `git merge-base --is-ancestor` proves its commit reached the default
branch. Everything that needs judgement — an item over the cap, a narrative `##`, which heading
holds the findings, what is decided — is listed as MANUAL with the rule, the line and the action.
"""
from __future__ import annotations

import difflib
import os
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass

import kit

LEGACY_SEED_BLOB = "1bcb41467fec35ec67cf74948a3e2acfdafcc194"
# Names a findings heading carries in the files this skill has met. Only a SINGLE match is acted
# on; two candidates, or none, is a question for the human (--open-heading), never a guess.
OPEN_CANDIDATE_RE = re.compile(r"^(aberto|abertos|em aberto|open|findings|achados(\s*\(sdd\))?)$", re.IGNORECASE)
LEGACY_OPEN_HEADINGS = {"Open"}  # what the pre-skeleton seed wrote; renamed to the seed's own
LEGACY_RESOLVED_RE = re.compile(r"^(resolved|resolvidos?)\b", re.IGNORECASE)
TICKED_RE = re.compile(r"^([-*+]|[0-9]+[.)])[ \t]+\[[xX]\]")
OPEN_ITEM_RE = re.compile(r"^- \[ \] ")
# Only a hash the item DECLARES as its fix is proof. The first hash anywhere in the prose would
# delete an item that merely cites a commit — the one deletion this script exists never to make.
HASH_RE = re.compile(r"(?:RESOLVED\**\s+by|RESOLVIDO\**\s+(?:por|em))\**\s+`?([0-9a-f]{7,40})\b")
# `RESOLVED by `a` e `b`` declares TWO commits, and both must have merged: the fix may be split.
MORE_HASH_RE = re.compile(r"^`?\s*(?:,|\be\b|\band\b|\+)\s*`([0-9a-f]{7,40})`")
PT_RESOLVED_RE = re.compile(r"RESOLVIDO por(\**)(\s+`?[0-9a-f]{7,40}\b)")
WRAP = 100
TITLE_MAX = 150
# a piece that is only a list marker (and its box) is never cut off from its first word: `- [ ]`
# alone on a line is a bare box, and the rest of the item would fall outside it
MARKER_ONLY_RE = re.compile(r"^\s*(([-*+]|[0-9]+[.)])(\s+\[[ xX]\])?)?\s*$")
# a continuation line must not open with something markdown reads as a new block
BAD_LINE_START_RE = re.compile(r"^(\[|[-*+>#]\s|[-*+>#]$|[0-9]+[.)]\s)")

# sensor message -> the action a human takes; the first matching fragment wins
ACTIONS = [
    ("content lines, cap is", "move the analysis to docs/ (or the mission handoff) and point at it; keep ~6 lines"),
    ("an H2 with no section marker", ("narrative → docs/; a category → `###` inside the open section; "
                                      "a settled matter → one line in the decided section")),
    ("above the findings section", "move the item into the open section"),
    ("under an H2 the skeleton does not have", "move the item into the open section"),
    ("prose at column 0", "indent it into the item above, or move it out of the section"),
    ("belongs to no finding", "indent it into the item above, or move it out of the section"),
    ("does not open with", ("write it as `- [ ] **<title>** — …` (--fix cuts a title at the first ` — ` "
                            f"only when there is one and the text before it fits an issue title, <= {TITLE_MAX} chars)")),
    ("must open with", "write it as `- [ ] **<title>** — …` at column 0"),
    ("no non-empty `file:line` anchor", "add the `file:line` the finding is about"),
    ("names no `<agent>`", "end with the found-by field of the preamble: — <found by> `<agent>` … (YYYY-MM-DD)"),
    ("no (YYYY-MM-DD)", "end with the found-by field of the preamble: — <found by> `<agent>` … (YYYY-MM-DD)"),
    ("a fenced block", "remove the fence; code belongs in docs/ or the handoff"),
    ("ticked box", "see the ticked-item entries above"),
    ("a decided record", "rewrite it as `- **<title>** — <decision> — `<pointer>` (YYYY-MM-DD)`, one line"),
    ("section marker with no `##`", "put the marker on the line right under its `##`"),
]


@dataclass
class Manual:
    line: int | None  # 1-based, in the file AFTER every AUTO fix (resolved by Fixer.finish)
    rule: str
    action: str
    text: str = ""    # the line it is about, kept verbatim until the numbering settles


class Fixer:
    """One pass over the lines of a file; every method is one AUTO rule."""

    def __init__(self, lines, seed_lines, repo_root, ref, open_heading):
        self.lines = list(lines)
        self.seed = seed_lines
        self.root = repo_root
        self.ref = ref
        self.open_heading = open_heading
        self.auto: list[str] = []
        self.manual: list[Manual] = []

    # ── helpers ────────────────────────────────────────────────────────────────────────────────
    def h2(self, i):
        return self.lines[i][3:].strip() if self.lines[i].startswith("## ") else None

    def seed_heading(self, marker):
        for i, line in enumerate(self.seed):
            if line.rstrip() == marker and i > 0 and self.seed[i - 1].startswith("## "):
                return self.seed[i - 1]
        raise SystemExit(f"the kit's seed has no heading above {marker} — the kit is broken")

    def item_end(self, i):
        """Index past the item starting at i: indented lines belong to it, and a blank line does
        too when an indented line follows (a finding in two paragraphs)."""
        j = i + 1
        while j < len(self.lines):
            line = self.lines[j]
            indented = line[:1] in (" ", "\t") and line.strip()
            blank_before_indented = (not line.strip() and j + 1 < len(self.lines)
                                     and self.lines[j + 1][:1] in (" ", "\t") and self.lines[j + 1].strip())
            if not (indented or blank_before_indented):
                break
            j += 1
        return j

    def open_span(self):
        """(first, past-last) line indices of the open section, or None."""
        m = kit.open_marker_line(self.lines)
        if m is None:
            return None
        end = next((j for j in range(m + 1, len(self.lines)) if self.lines[j].startswith("## ")),
                   len(self.lines))
        return m + 1, end

    def is_ancestor(self, sha):
        if self.root is None or self.ref is None:
            return None
        if subprocess.run(["git", "-C", self.root, "cat-file", "-e", sha + "^{commit}"],
                          capture_output=True, check=False).returncode != 0:
            return None
        rc = subprocess.run(["git", "-C", self.root, "merge-base", "--is-ancestor", sha, self.ref],
                            capture_output=True, check=False).returncode
        return True if rc == 0 else False if rc == 1 else None

    # ── the AUTO rules, in the order they run ──────────────────────────────────────────────────
    def legacy_preamble(self, legacy_lines):
        """The pre-skeleton seed's preamble, untouched, becomes the current seed's."""
        cut = next(i for i, l in enumerate(legacy_lines) if l.startswith("## "))
        old = legacy_lines[:cut]
        if self.lines[:cut] == old:
            new_cut = next(i for i, l in enumerate(self.seed) if l.startswith("## "))
            self.lines[:cut] = self.seed[:new_cut]
            self.auto.append("the legacy seed's preamble was replaced by the current seed's")

    def ticked(self):
        i, deleted = 0, 0
        while i < len(self.lines):
            if not TICKED_RE.match(self.lines[i]):
                i += 1
                continue
            end = self.item_end(i)
            block = " ".join(self.lines[i:end])
            m = HASH_RE.search(block)
            shas, sha, verdict = [], None, None
            if m:
                shas, rest = [m.group(1)], block[m.end():]
                more = MORE_HASH_RE.match(rest)
                while more:
                    shas.append(more.group(1))
                    rest = rest[more.end():]
                    more = MORE_HASH_RE.match(rest)
                verdicts = [self.is_ancestor(h) for h in shas]
                bad = [h for h, v in zip(shas, verdicts) if v is not True]
                sha = bad[0] if bad else shas[0]
                verdict = True if not bad else (None if None in verdicts else False)
            if verdict is True:
                del self.lines[i:end]
                while i < len(self.lines) and i > 0 and not self.lines[i].strip() and not self.lines[i - 1].strip():
                    del self.lines[i]
                deleted += 1
                continue
            if sha is None:
                act = ("no `RESOLVED by <hash>`: if it was fixed, cite the commit and rerun; if it was refuted or decided, "
                       "record it as one line in the decided section")
            elif verdict is False:
                act = (f"`{sha}` has not reached {self.ref}: keep it as `- [ ] … RESOLVED by {sha}` "
                       "in the open section until it merges, then delete it")
            else:
                act = f"`{sha}` is not a commit this clone knows (or no default branch): fetch, then decide"
            self.manual.append(Manual(None, "ticked item", act, self.lines[i]))
            i = end
        if deleted:
            self.auto.append(f"{deleted} ticked item(s) deleted — each cites a commit already in {self.ref}")

    def open_marker(self):
        if kit.open_marker_line(self.lines) is not None:
            return
        h2s = [i for i in range(len(self.lines)) if self.lines[i].startswith("## ")]
        if self.open_heading is not None:
            pick = [i for i in h2s if self.h2(i) == self.open_heading.strip()]
            if len(pick) != 1:
                raise SystemExit(f"--open-heading {self.open_heading!r} matches {len(pick)} `##` "
                                 f"heading(s); it must name exactly one of: "
                                 + ", ".join(repr(self.h2(i)) for i in h2s))
        else:
            pick = [i for i in h2s if OPEN_CANDIDATE_RE.match(self.h2(i))]
        if len(pick) != 1:
            names = ", ".join(f"L{i + 1} `## {self.h2(i)}`" for i in pick) or "none"
            self.manual.append(Manual(None, "no open marker", (
                f"which `##` holds the findings cannot be told (candidates: {names}); rerun with "
                f"--open-heading '<text>', or add `{self.seed_heading(kit.OPEN_MARKER)}` + "
                f"{kit.OPEN_MARKER} above the first finding")))
            return
        i = pick[0]
        old = self.h2(i)
        if old in LEGACY_OPEN_HEADINGS and self.seed_heading(kit.OPEN_MARKER) != self.lines[i]:
            self.lines[i] = self.seed_heading(kit.OPEN_MARKER)
            self.auto.append(f"the legacy heading `## {old}` became `{self.lines[i]}` (the seed's)")
        self.lines.insert(i + 1, kit.OPEN_MARKER)
        self.auto.append(f"{kit.OPEN_MARKER} added under `{self.lines[i]}` (L{i + 1})")

    def legacy_resolved(self):
        i = 0
        while i < len(self.lines):
            name = self.h2(i)
            if name is None or not LEGACY_RESOLVED_RE.match(name):
                i += 1
                continue
            end = next((j for j in range(i + 1, len(self.lines)) if self.lines[j].startswith("## ")),
                       len(self.lines))
            if any(l.strip() for l in self.lines[i + 1:end]):
                self.manual.append(Manual(None, "legacy resolved section", (
                    "it still holds content: each entry is deleted (fixed, with proof) or becomes one line "
                    "in the decided section; then remove the heading"), self.lines[i]))
                i = end
                continue
            del self.lines[i:end]
            self.auto.append(f"the empty legacy `## {name}` was removed")

    def decided_section(self):
        if any(l.rstrip() == kit.DECIDED_MARKER for l in self.lines):
            return
        while self.lines and not self.lines[-1].strip():
            self.lines.pop()
        head = self.seed_heading(kit.DECIDED_MARKER)
        self.lines += ["", head, kit.DECIDED_MARKER, ""]
        self.auto.append(f"the decided section was appended (`{head}`)")

    def resolved_token(self):
        span = self.open_span()
        if span is None:
            return
        n = 0
        for i in range(*span):
            new, k = PT_RESOLVED_RE.subn(r"RESOLVED by\1\2", self.lines[i])
            if k:
                self.lines[i], n = new, n + k
        if n:
            self.auto.append(f"{n} `RESOLVIDO por <hash>` became `RESOLVED by <hash>` (the kit token)")

    def bold_titles(self):
        span = self.open_span()
        if span is None:
            return
        n = 0
        for i in range(*span):
            line = self.lines[i]
            if not OPEN_ITEM_RE.match(line) or line.startswith("- [ ] **"):
                continue
            body = line[len("- [ ] "):]
            cut = first_sep_outside_code(body)
            title = body[:cut].strip() if cut >= 0 else ""
            if cut < 0 or not title or "**" in title or len(title) > TITLE_MAX:
                continue  # left for the sensor to report, with the action that says why
            self.lines[i] = f"- [ ] **{title}** — {body[cut + 3:].lstrip()}"
            n += 1
        if n:
            self.auto.append(f"{n} item(s) got a bold title, cut at their first ` — `")

    def finish(self):
        """Give every MANUAL entry its line number in the final text."""
        for m in self.manual:
            if m.text:
                m.line = next((k + 1 for k, l in enumerate(self.lines) if l == m.text), None)

    def wrap_long_lines(self):
        span = self.open_span()
        if span is None:
            return
        i, end, n = span[0], span[1], 0
        while i < end:
            if not OPEN_ITEM_RE.match(self.lines[i]):
                i += 1
                continue
            stop = self.item_end(i)
            j = i
            while j < stop:
                line = self.lines[j]
                if len(line) > WRAP and line.strip():
                    indent = "  " if j == i else re.match(r"^[ \t]*", line).group(0) or "  "
                    parts = wrap_line(line, indent)
                    if len(parts) > 1:
                        self.lines[j:j + 1] = parts
                        stop += len(parts) - 1
                        end += len(parts) - 1
                        j += len(parts) - 1
                        n += 1
                j += 1
            i = stop
        if n:
            self.auto.append(f"{n} overlong physical line(s) wrapped at {WRAP} columns (text unchanged)")


def first_sep_outside_code(text, sep=" — "):
    in_code = False
    for k in range(len(text)):
        if text[k] == "`":
            in_code = not in_code
        elif not in_code and text.startswith(sep, k):
            return k
    return -1


def wrap_line(line, indent):
    """Split one physical line at spaces outside code spans, each piece <= WRAP where possible,
    never letting a continuation open with something markdown reads as a new block. The words and
    their order are unchanged: joining the pieces with single spaces gives the line back."""
    lead = re.match(r"^[ \t]*", line).group(0)
    words, cur, in_code = [], "", False
    for ch in line[len(lead):]:
        if ch == "`":
            in_code = not in_code
        if ch == " " and not in_code:
            words.append(cur)
            cur = ""
        else:
            cur += ch
    words.append(cur)
    out, cur = [], lead + words[0]
    for w in words[1:]:
        if len(cur) + 1 + len(w) <= WRAP or not w or BAD_LINE_START_RE.match(w) or MARKER_ONLY_RE.match(cur):
            cur += " " + w
        else:
            out.append(cur)
            cur = indent + w
    out.append(cur)
    return out


# ── the run ────────────────────────────────────────────────────────────────────────────────────
def git(root, *args):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, check=False)
    return r.returncode, r.stdout.strip()


def config_value(root, key):
    path = os.path.join(root or "", ".sdd", "config.sh")
    if not root or not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(rf'^{key}=["\']?([^"\'\n#]*)', line.strip())
            if m:
                return m.group(1).strip()
    return None


def default_ref(root):
    if not root:
        return None
    branch = config_value(root, "DEFAULT_BRANCH")
    if not branch:
        rc, out = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
        branch = out.split("/", 1)[1] if rc == 0 and "/" in out else "main"
    for ref in (f"origin/{branch}", branch):
        if git(root, "rev-parse", "--verify", "--quiet", ref)[0] == 0:
            return ref
    return None


def sensor_violations(kit_root, text, beside):
    """(rc, [(line, message)]) of the kit's sensor over `text`, written to a scratch file.

    The scratch file is written in `beside` — the directory of the file being checked — and not in
    the system temp dir. Since the kit's ADR 0011 an anchor resolves against the CHECKED file's
    repository: a copy under /tmp belongs to no repository, so every anchor failed as "names no
    file" (measured on a real TODO.md: 188 violations reported where the kit itself sees 97). The
    kit's own `with_decided` writes its copies beside the fixture for the same reason. Hidden name,
    removed in `finally`.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".md", prefix=".sdd-todo-check-", dir=beside,
                                     delete=False, encoding="utf-8") as fh:
        fh.write(text)
    try:
        rc, out = kit.run_sensor(kit_root, "--check", fh.name, "--allow-empty")
    finally:
        os.unlink(fh.name)
    found = [(int(m.group(1)), m.group(2)) for m in re.finditer(r"^  line (\d+): (.+)$", out, re.MULTILINE)]
    return rc, found


def action_for(message):
    return next((a for frag, a in ACTIONS if frag in message), message)


def describe(rc, found):
    if rc == 99:
        return "no open marker (the sensor refuses the file before reading it)"
    return f"{len(found)} violation(s)" if found else "clean"


def fix_text(text, kit_root, repo_root, lang, open_heading):
    """(new text, auto notes, manual entries, seed path)."""
    seed_path = os.path.join(kit_root, "templates", f"todo.{lang}.md") if lang else ""
    if not (lang and os.path.isfile(seed_path)):
        seed_path = os.path.join(kit_root, "templates", "todo.md")
    with open(seed_path, encoding="utf-8") as fh:
        seed_text = fh.read()
    # the pre-skeleton seed is the kit's fixture, not a copy here: one owner for the old bytes too
    legacy_path = os.path.join(kit_root, "tests", "fixtures", "todo-seed-legacy-en.md")
    blob = subprocess.run(["git", "hash-object", "--stdin"], input=text, capture_output=True,
                          text=True, check=False).stdout.strip()
    if blob == LEGACY_SEED_BLOB:
        note = f"the untouched legacy seed was replaced by {os.path.basename(seed_path)} (it held no finding)"
        return seed_text, [note], [], seed_path
    lines = text.split("\n")
    f = Fixer(lines, seed_text.split("\n"), repo_root, default_ref(repo_root), open_heading)
    if os.path.isfile(legacy_path):
        with open(legacy_path, encoding="utf-8") as fh:
            f.legacy_preamble(fh.read().split("\n"))
    f.ticked()
    f.open_marker()
    f.legacy_resolved()
    f.decided_section()
    f.resolved_token()
    f.bold_titles()
    f.wrap_long_lines()
    f.finish()
    return "\n".join(f.lines), f.auto, f.manual, seed_path


def compress(lines):
    shown = ", ".join(f"L{n}" for n in lines[:12])
    return shown + (f" … (+{len(lines) - 12})" if len(lines) > 12 else "")


def run(a, kit_root):
    path = a.file
    if not os.path.isfile(path):
        print(f"FAIL  {path} not found", file=sys.stderr)
        return 2
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    rc, out = git(os.path.dirname(os.path.abspath(path)), "rev-parse", "--show-toplevel")
    repo_root = out if rc == 0 else None
    lang = a.lang if a.lang is not None else (config_value(repo_root, "OUTPUT_LANG") or "")
    new, auto, manual, seed = fix_text(text, kit_root, repo_root, lang, a.open_heading)
    beside = os.path.dirname(os.path.abspath(path))
    before = sensor_violations(kit_root, text, beside)
    after = sensor_violations(kit_root, new, beside)

    print(f"{'fix' if a.fix else 'audit'}  {path} · OUTPUT_LANG={lang or '(none)'} · seed "
          f"templates/{os.path.basename(seed)} · default branch {default_ref(repo_root) or '?'}")
    for note in auto:
        print(f"AUTO    {note}")
    for m in manual:
        print(f"MANUAL  {('L' + str(m.line)) if m.line else '    '}  {m.rule}: {m.action}")
    groups: OrderedDict[str, list[int]] = OrderedDict()
    for line, msg in after[1]:
        key = re.sub(r"^\d+ content lines", "N content lines", msg)
        groups.setdefault(key, []).append(line)
    for msg, where in groups.items():
        print(f"MANUAL  {len(where)}× {msg}\n        at {compress(where)}\n        → {action_for(msg)}")
    if groups:
        print("        (line numbers refer to the file after the AUTO fixes — see --fix)")
    print(f"summary auto={len(auto)} manual={len(manual) + sum(len(w) for w in groups.values())} · "
          f"sensor: before {describe(*before)} → after the AUTO fixes {describe(*after)}")

    if a.fix and new != text:
        sys.stdout.writelines(difflib.unified_diff(
            text.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}"))
    pending = bool(manual or groups)
    if not a.write:
        if a.fix and new != text:
            print("diff only — rerun with --fix --write to apply the AUTO part")
        return 1 if (pending or new != text) else 0
    if new == text:
        print("nothing to write — the AUTO part is already applied")
        return 1 if pending else 0
    if repo_root:
        rel = os.path.relpath(os.path.abspath(path), repo_root)
        tracked = git(repo_root, "ls-files", "--error-unmatch", rel)[0] == 0
        if tracked and git(repo_root, "diff", "--quiet", "HEAD", "--", rel)[0] != 0:
            print(f"FAIL  {rel} has uncommitted changes — commit or stash them first, so the fix "
                  "arrives as a diff of its own", file=sys.stderr)
            return 6
        if not tracked:
            print(f"warn  {rel} is not tracked by git — the change is written with no diff to review it by",
                  file=sys.stderr)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    rc, out = kit.run_sensor(kit_root, "--check", path, "--allow-empty")
    print(f"written. the kit's sensor now says (rc {rc}): {out.strip().splitlines()[-1] if out.strip() else ''}")
    return 1 if pending else 0
