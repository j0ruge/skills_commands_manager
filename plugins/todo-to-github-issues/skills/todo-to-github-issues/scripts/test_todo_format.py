#!/usr/bin/env python3
"""Offline checks for todo_format.py (--audit / --fix). Usage: python3 test_todo_format.py

Needs the sdd kit on this machine (the same requirement the skill has) and git; nothing touches
the network. Every AUTO rule is measured in both directions: the off-standard input comes out in
the standard, and a file already in the standard comes out byte for byte the same.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit
import todo_format as f

ROOT, _ = kit.find_kit()
if ROOT is None:
    sys.exit("FAIL  the sdd kit is not on this machine — the format tests measure against its seed and sensor")


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def write(p, text, mode="w"):
    with open(p, mode, encoding="utf-8") as fh:
        fh.write(text)


def run(*args):
    return subprocess.run([sys.executable, S, *args], capture_output=True, text=True, check=False)


S = os.path.join(HERE, "todo_issues.py")
SEED_PT = read(os.path.join(ROOT, "templates", "todo.pt-BR.md"))
LEGACY = read(os.path.join(ROOT, "tests", "fixtures", "todo-seed-legacy-en.md"))
fails = 0


def check(name, cond):
    global fails
    print(("ok    " if cond else "FAIL  ") + name)
    fails += 0 if cond else 1


def fix(text, repo=None, heading=None, lang="pt-BR"):
    new, auto, manual, _ = f.fix_text(text, ROOT, repo, lang, heading)
    return new, auto, manual


def anchor_world(root):
    """Write the files the fixtures' anchors name. Since the kit's ADR 0011 an anchor must name a
    file of the CHECKED file's repository, and a backticked span of the item's head must occur in
    it near the anchored line — so a fixture anchored in thin air is refused, not accepted."""
    for rel, body in (("bin/x", "um_simbolo\ncode span com espaço\n"),
                      ("src/b.py", "import os\n\ndef login_flow():\n    pass\n")):
        os.makedirs(os.path.dirname(os.path.join(root, rel)) or root, exist_ok=True)
        write(os.path.join(root, rel), body)


BOX = tempfile.mkdtemp(prefix="todo-format-anchors-")
subprocess.run(["git", "init", "-q", BOX], check=True)
anchor_world(BOX)


def sensor_rc(text):
    return f.sensor_violations(ROOT, text, BOX)[0]


GOOD = ("- [ ] **Um achado bem formado** — `bin/x:1` — `um_simbolo` por que importa.\n"
        "  — descoberto por `sdd-qa` na missão `m` (2026-09-24)\n")
STANDARD = SEED_PT.replace("<!-- sdd:open -->\n", "<!-- sdd:open -->\n\n### Tema\n\n" + GOOD, 1)

# ── a file already in the standard is left alone ────────────────────────────────────────────────
new, auto, manual = fix(STANDARD)
check("standard file: sensor accepts it", sensor_rc(STANDARD) == 0)
check("standard file: --fix changes nothing", new == STANDARD and not auto and not manual)
new, auto, manual = fix(SEED_PT)
check("the seed itself: --fix changes nothing", new == SEED_PT and not auto)

# ── the legacy seed ─────────────────────────────────────────────────────────────────────────────
new, auto, _ = fix(LEGACY)
check("untouched legacy seed -> replaced by the language's seed", new == SEED_PT and len(auto) == 1)
legacy_item = LEGACY.replace("## Open\n", "## Open\n\n- [ ] ajustar o fluxo — `src/b.py:3` — `login_flow` quebra o login"
                             " — found by `opus` in mission `m1` (2026-09-18)\n", 1)
new, auto, manual = fix(legacy_item)
check("legacy seed + one finding -> NOT replaced wholesale, the finding survives",
      new != SEED_PT and "ajustar o fluxo" in new)
check("...its preamble becomes the seed's", new.startswith(SEED_PT.split("## Aberto")[0]))
check("...`## Open` becomes the seed's heading, with the marker under it",
      "## Aberto\n<!-- sdd:open -->" in new and "## Open\n" not in new)
check("...the empty `## Resolved` is removed, the decided section appended",
      "## Resolved" not in new and new.rstrip().endswith("<!-- sdd:decided -->"))
check("...the one-liner gets a bold title cut at its first separator",
      "- [ ] **ajustar o fluxo** — `src/b.py:3`" in new)
check("...and the result passes the kit's sensor", sensor_rc(new) == 0)
again, auto2, _ = fix(new)
check("...and a second --fix is a no-op (idempotent)", again == new and not auto2)

# ── the kit token ───────────────────────────────────────────────────────────────────────────────
pt = STANDARD.replace("(2026-09-24)\n", "RESOLVIDO por `abc1234` (2026-09-24)\n", 1)
pt = pt.replace("Achados que", "Achados (RESOLVIDO por `def5678` citado aqui) que", 1)
new, _, _ = fix(pt)
check("RESOLVIDO por <hash> in the open section -> RESOLVED by <hash>", "RESOLVED by `abc1234`" in new)
check("...and the same words in the preamble are left alone", "RESOLVIDO por `def5678`" in new)

# ── bold titles ─────────────────────────────────────────────────────────────────────────────────
long_title = "x" * (f.TITLE_MAX + 1)
plain = STANDARD.replace(GOOD, GOOD + "\n- [ ] curto — `a:1` — por que. — descoberto por `x` (2026-09-24)\n"
                         f"\n- [ ] {long_title} — `a:1` — por que. — descoberto por `x` (2026-09-24)\n")
new, _, _ = fix(plain)
check("a short text before the first separator becomes the bold title", "- [ ] **curto** — `a:1`" in new)
check("a title longer than an issue title is left for the human",
      f"\n- [ ] {long_title}" in new and f"**{long_title}" not in new)

# ── wrapping ────────────────────────────────────────────────────────────────────────────────────
words = " ".join(f"palavra{k}" for k in range(60))
longi = STANDARD.replace(GOOD, f"- [ ] **Longo** — `bin/x:1` — {words} [link](http://x) `code span com espaço` fim.\n"
                               "  — descoberto por `x` (2026-09-24)\n")
new, auto, _ = fix(longi)
block = new.split("- [ ] **Longo**")[1].split("\n\n")[0]
parts = ("- [ ] **Longo**" + block).split("\n")
check("an overlong line is wrapped", len(parts) > 3 and any("wrapped" in a for a in auto))
check("...no piece over the limit", all(len(p) <= f.WRAP for p in parts))
check("...no continuation opens a new markdown block", all(not f.BAD_LINE_START_RE.match(p.strip()) for p in parts[1:]))
orig = "- [ ] **Longo**" + longi.split("- [ ] **Longo**")[1].split("\n\n")[0]
check("...the words are unchanged", "\n".join(parts).split() == orig.split())
# Wrapping is honest about length: a 60-word item on ONE physical line passed the 8-line cap, and
# wrapped it shows the 9 lines it really has. The only new violation may be the cap.
check("...and the only thing wrapping reveals is the cap it was hiding",
      [m for _, m in f.sensor_violations(ROOT, new, BOX)[1]] == ["9 content lines, cap is 8"])
short = longi.replace(words, " ".join(f"palavra{k}" for k in range(30)))
new2, _, _ = fix(short)
check("a long line that fits the cap once wrapped passes the sensor", sensor_rc(new2) == 0 and new2 != short)
tl = STANDARD.replace(GOOD, "- [ ] " + "y" * 120 + " — `a:1` — w. — descoberto por `x` (2026-09-24)\n")
new3, _, _ = fix(tl)
check("wrapping never leaves the box alone on its line", "- [ ]\n" not in new3 and "\n- [ ] **" + "y" * 20 in new3)

# ── ticked items, against a real git history ───────────────────────────────────────────────────
repo = tempfile.mkdtemp(prefix="todo-format-")
def g(*a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout.strip()
g("init", "-q", "-b", "main"); g("config", "user.email", "t@e.x"); g("config", "user.name", "t")
write(os.path.join(repo, "a"), "1"); g("add", "a"); g("commit", "-qm", "merged")
# the CLI case at the end checks a TODO.md INSIDE this repo, so its anchors must resolve here too
os.makedirs(os.path.join(repo, "src")); write(os.path.join(repo, "src", "b.py"), read(os.path.join(BOX, "src", "b.py")))
g("add", "src"); g("commit", "-qm", "anchored file")
merged = g("rev-parse", "--short=7", "HEAD")
g("switch", "-qc", "feat"); write(os.path.join(repo, "a"), "2"); g("commit", "-qam", "open")
unmerged = g("rev-parse", "--short=7", "HEAD"); g("switch", "-q", "main")

def ticked_world(line):
    return STANDARD.replace(GOOD, GOOD + "\n" + line + "\n")

new, auto, manual = fix(ticked_world(f"- [x] RESOLVED by `{merged}` — **feito** — `a:1` — ok"), repo)
check("a ticked item whose declared commit is merged -> deleted", "**feito**" not in new and any("deleted" in a for a in auto))
new, _, manual = fix(ticked_world(f"- [x] RESOLVED by `{unmerged}` — **ainda não** — `a:1`"), repo)
check("a ticked item whose commit has NOT merged -> kept, and named for the human",
      "**ainda não**" in new and any(m.rule == "ticked item" and unmerged in m.action for m in manual))
new, _, manual = fix(ticked_world(f"- [x] RESOLVED by `{merged}` e `{unmerged}` — **metade** — `a:1`"), repo)
check("two declared commits, one unmerged -> kept", "**metade**" in new)
new, _, manual = fix(ticked_world(f"- [x] **sem hash** — `a:1` — cita `{merged}` só de passagem"), repo)
check("a ticked item citing a hash only in its prose is NOT deleted", "**sem hash**" in new
      and any(m.rule == "ticked item" for m in manual))
check("...and the MANUAL line points at the item in the fixed text",
      any(m.rule == "ticked item" and m.line and new.split("\n")[m.line - 1].startswith("- [x] **sem hash**")
          for m in manual))

# ── which heading holds the findings ────────────────────────────────────────────────────────────
two = "# T\n\n## Open\n\n- [ ] **a** — `x:1` — w. — por `x` (2026-09-24)\n\n## Findings\n\n"
new, _, manual = fix(two)
check("two candidate headings -> no guess, a MANUAL naming both",
      kit.OPEN_MARKER not in new and any("candidates" in m.action and "Findings" in m.action for m in manual))
new, _, _ = fix(two, heading="Findings")
check("--open-heading picks the named one", "## Findings\n" + kit.OPEN_MARKER in new)
none = "# T\n\n## Bloqueado em terceiro\n\n- [ ] **a** — `x:1` — w. — por `x` (2026-09-24)\n"
new, _, manual = fix(none)
check("no candidate heading -> MANUAL, never a guess", kit.OPEN_MARKER not in new and manual)

# ── the CLI: --fix shows, --fix --write writes, and only over a clean file ──────────────────────
todo = os.path.join(repo, "TODO.md")
write(todo, legacy_item)
g("add", "TODO.md"); g("commit", "-qm", "todo")
before = read(todo)
r = run("--fix", "--file", todo, "--lang", "pt-BR")
check("--fix without --write prints a diff and leaves the file alone",
      "+++ b/" in r.stdout and read(todo) == before)
write(todo, "\nsujo\n", "a")
r = run("--fix", "--write", "--file", todo, "--lang", "pt-BR")
check("--fix --write over uncommitted changes is refused (rc 6)", r.returncode == 6)
g("checkout", "--", "TODO.md")
r = run("--fix", "--write", "--file", todo, "--lang", "pt-BR")
check("--fix --write over a clean file writes, and the sensor then accepts it",
      r.returncode == 0 and "ok    1 finding(s)" in r.stdout and kit.OPEN_MARKER in read(todo))

subprocess.run(["rm", "-rf", repo, BOX], check=False)
sys.exit(1 if fails else 0)
