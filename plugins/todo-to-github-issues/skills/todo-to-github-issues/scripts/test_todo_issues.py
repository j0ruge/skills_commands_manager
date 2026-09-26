#!/usr/bin/env python3
"""Offline checks for todo_issues.py. Usage: python3 test_todo_issues.py <path/to/TODO.md>

Needs a real sdd-style TODO.md (the kit's two-section skeleton) with at least 5 items, and the sdd
kit on this machine; nothing here touches the network.
"""
import copy
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
import todo_issues as t

path = sys.argv[1] if len(sys.argv) > 1 else "TODO.md"
ctx = t.Ctx(repo="o/r", root=os.path.dirname(os.path.abspath(path)), relpath="TODO.md", sha=None, branch="main")
items = t.parse(path)
fails = 0


def check(name, cond):
    global fails
    print(("ok    " if cond else "FAIL  ") + name)
    fails += 0 if cond else 1


def as_issues(its, c=ctx, labels=("todo",)):
    return [{"number": n, "title": t.issue_title(i), "body": t.render_body(i, c), "state": "OPEN",
             "labels": [{"name": x} for x in labels]} for n, i in enumerate(its, 100)]


check(f"parsed {len(items)} items (>= 5)", len(items) >= 5)
check("keys unique", len({i.key for i in items}) == len(items))
check("every title closed and non-empty", all(i.title for i in items))
check("RESOLVED_RE ignores the bare phrase", not t.RESOLVED_RE.search("o ciclo do `RESOLVED by` e x"))
check("RESOLVED_RE fires on a real marker", bool(t.RESOLVED_RE.search("x — RESOLVED by `2f3eb29` em y")))
check("RESOLVED_RE fires on a bold marker", bool(t.RESOLVED_RE.search("**RESOLVED by** 2f3eb29")))
check("RESOLVED_RE: the pre-skeleton Portuguese token is not the kit's", not t.RESOLVED_RE.search("RESOLVIDO por `2f3eb29`"))

# ── the section: read by its marker, never by the heading text ──────────────────────────────────
def parsed(text):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(text)
    try:
        return t.parse(fh.name)
    finally:
        os.unlink(fh.name)

ITEM = "- [ ] **{}** — `f:1` — w. — por `x` (2026-09-24)\n"
SKEL = ("# T\n\n> exemplo: - [ ] **<title>** — ...\n\n## {open}\n<!-- sdd:open -->\n\n" + ITEM.format("antes")
        + "\n### Tema\n\n" + ITEM.format("um") + "\n" + ITEM.format("dois")
        + "\n## {dec}\n<!-- sdd:decided -->\n\n- **decidido** — sim — `docs/x.md` (2026-09-24)\n"
        + "\n- [ ] **parado depois** — `f:1` — w. — por `x` (2026-09-24)\n")
en = parsed(SKEL.format(open="Open", dec="Decided"))
pt = parsed(SKEL.format(open="Aberto", dec="Decidido"))
check("only the open section is read: preamble, decided records and what follows are not",
      [i.title for i in en] == ["antes", "um", "dois"])
check("the heading text does not matter: English and Portuguese parse the same",
      [(i.title, i.section) for i in en] == [(i.title, i.section) for i in pt])
check("the label is the `###` inside the section; before any `###`, none",
      [i.section for i in en] == ["", "Tema", "Tema"])
try:
    parsed("## Aberto\n\n" + ITEM.format("x"))
    check("a file without the marker is refused, never guessed", False)
except t.NoOpenMarker:
    check("a file without the marker is refused, never guessed", True)
check("label: a comma in the section never reaches GitHub (422 `Label.name is invalid`, medido)",
      t.section_label("Aprovação, pendências e ciclo da cotação") == "todo: Aprovação · pendências e ciclo da cotação")
check("label: the 50 cap counts characters, as GitHub does (not bytes)",
      len(t.section_label("ç" * 60)) == 50)
check("label: a section without a comma is unchanged (no label swap on existing mirrors)",
      t.section_label("PDF da proposta") == "todo: PDF da proposta")
check("format: a marked TODO.md with a numbered category is still a TODO.md",
      t.detect_format("## Aberto\n<!-- sdd:open -->\n\n### 1. Bloqueia\n") == "todo")
check("format: an unmarked file with numbered sections is a report", t.detect_format("### 1. Achado\n") == "report")
check("format: an unmarked TODO.md with numbered narratives is still a TODO.md (it meets the sensor)",
      t.detect_format("## Uma narrativa\n\n### 1. Achado\n", "repo/TODO.md") == "todo")

# ── the kit: required, found, never replaced by a guess ─────────────────────────────────────────
root, how = kit.find_kit(env={"SDD_HOME": "/no/such/dir"})
check("a wrong SDD_HOME is reported, not silently replaced by another kit", root is None and "SDD_HOME" in how)
root, how = kit.find_kit(env={}, which=lambda _: None, home="/no/such/home")
check("no SDD_HOME, no `sdd` on PATH, no default clone -> not found", root is None)
KIT, _ = kit.find_kit()
if KIT is None:
    check("the kit is on this machine (the rest of this block needs it)", False)
else:
    rc, out = kit.run_sensor(KIT, "--count", path)
    check("the kit's sensor counts what parse() counts on the real file",
          rc == 0 and out.strip() == str(len(items)))
    import subprocess as _sp
    r = _sp.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "todo_issues.py"),
                 "--file", path], env=dict(os.environ, SDD_HOME="/no/such/dir"), capture_output=True, text=True,
                check=False)
    check("preflight: a missing kit exits 3 and says how to install it",
          r.returncode == 3 and "git clone" in r.stderr and "SDD_HOME" in r.stderr)

issues = as_issues(items)
p = t.build_plan(items, issues)
check("rerun is a no-op", len(p.ok) == len(items) and not (p.create or p.update or p.orphans))
ctx2 = t.Ctx(repo="o/r", root=ctx.root, relpath="TODO.md", sha="deadbeef", branch="main")
check("a new HEAD sha alone is a no-op", len(t.build_plan(items, as_issues(items, ctx2)).ok) == len(items))

def reparsed(old: str, new: str):
    """Edit the real file's text in a temp copy and parse it again — keys and digests come from
    the code under test, never from the test."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert text.count(old) >= 1, f"probe anchor vanished: {old!r}"
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(text.replace(old, new, 1))
    try:
        return t.parse(fh.name)
    finally:
        os.unlink(fh.name)


it3 = items[3]
last = it3.raw[-1]
p = t.build_plan(reparsed(last, last + " extra"), issues)
check("body edit -> 1 update", len(p.update) == 1 and p.update[0][1]["number"] == 103)
sec = next(i for i in items if i.section and i.section != items[0].section)
p = t.build_plan(reparsed(f"# {sec.section}\n", f"# {sec.section} renomeada\n"), issues)
check("section rename -> its items update", len(p.update) == sum(i.section == sec.section for i in items))
check("4 deleted -> 4 orphans", len(t.build_plan(items[:-4], issues).orphans) == 4)
check("another file's mirror is never an orphan here", not t.build_plan(items[:1], issues, "OUTRO.md").orphans)
legacy = [dict(x, body=x["body"].replace("\n<!-- todo-src: TODO.md -->", "")) for x in issues]
check("legacy body (no src marker) is attributed by its footer",
      legacy[0]["body"] != issues[0]["body"] and len(t.build_plan(items, legacy).ok) == len(items))

closed = copy.deepcopy(issues)
closed[0]["state"] = "CLOSED"
p = t.build_plan(items, closed)
check("closed issue + present item -> reported, not recreated", len(p.closed_present) == 1 and not p.create)
res = copy.deepcopy(items[:1])
res[0].resolved = True
p = t.build_plan(res, [])
check("resolved item without issue -> skip", len(p.skip_resolved) == 1 and not p.create)
p = t.build_plan(items, issues + [dict(issues[0], number=999)])
check("duplicate key on GitHub is reported", bool(p.dup_issues) and p.dup_issues[0][1] == [100, 999])

block = "\n".join(items[0].raw)
twin = reparsed(block, block + "\n\n" + block)
check("two items with the same title get two keys", len({i.key for i in twin}) == len(items) + 1)

renamed = reparsed("- [ ] **" + items[2].raw[0][len("- [ ] **"):], "- [ ] **Um título novo " + items[2].raw[0][len("- [ ] **"):])
p = t.build_plan(renamed, issues)
t.guess_renames(p, ctx)
check("retitle -> 1 create + 1 orphan paired as RENAME?",
      len(p.create) == 1 and len(p.orphans) == 1 and len(p.renames) == 1 and p.renames[0][0]["number"] == 102)
p = t.build_plan(items[1:3] + [renamed[2]] + items[3:], issues)
t.guess_renames(p, ctx)
check("unrelated delete is not paired", all(iss["number"] != 100 for iss, _, _ in p.renames))

# ── report mode, on a synthetic report: every rule below has its own world ──────────────────
import report as r

REPORT = """# Achados

| # | Achado | Desfecho | Evidência |
|---|---|---|---|
| 1 | um | **RESOLVIDO** — feito | `abc1234` + `def5678` |
| 2 | dois | roteado ao `TODO.md` | `1111111` |
| 3 | três | **PARCIAL** — metade | `2222222` |

## Itens

### 1. Primeiro achado

- [ ] **Sub-item no formato TODO** — `bin/x:1` — prosa que continua
  na linha seguinte.
  — descoberto por `a` na missão `m` (2026-09-01)
  RESOLVIDO por `abc1234`: veja [a ADR](docs/adr/0001.md#contexto) e [site](https://x.y/z).

```text
### 9. isto é código, não achado
linha   com   espaços
```

| a | b |
|---|---|
| 1 | 2 |

---

### 2. Segundo achado

> citação que
> continua

### 3. Terceiro achado

texto

### Uma nota sem número

não é achado

### 4. Quarto sem linha na tabela

  ROTEADO para o `TODO.md` (não implementado).

## Uma observação solta

corpo da observação
"""
with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
    fh.write(REPORT)
found, spans, rlines = r.parse_report(fh.name)
os.unlink(fh.name)
by = {f.key: f for f in found}
check("report: numbered sections only, fenced heading ignored", sorted(by) == ["1", "2", "3", "4"])
check("report: `- [ ]` inside a section is not its own finding", len(found) == 4)
check("report: table RESOLVIDO -> closed, with its evidence",
      by["1"].status == "closed" and by["1"].evidence == ["abc1234", "def5678"])
check("report: table roteado / PARCIAL -> open", by["2"].status == "open" and by["3"].status == "open")
check("report: no table row -> first status line of the body", by["4"].status == "open")
check("report: trailing rule and blanks dropped from the body", by["1"].lines[-1].startswith("| 1"))

rctx = t.Ctx(repo="o/r", root=ctx.root, relpath="docs/R.md", sha=None, branch="main")
u = r.unwrap(by["1"].lines, rctx)
check("unwrap: list continuation joined", "prosa que continua na linha seguinte." in u)
check("unwrap: attribution and RESOLVIDO keep their own lines",
      "\n  — descoberto por" in u and "\n  RESOLVIDO por" in u)
check("unwrap: fence content verbatim", "linha   com   espaços" in u and "### 9." in u)
check("unwrap: table rows untouched", "\n| 1 | 2 |" in u)
check("unwrap: quote joined", "citação que continua" in r.unwrap(by["2"].lines))
check("absolutize: relative link -> blob, relative to the file's directory, fragment kept",
      "](https://github.com/o/r/blob/main/docs/docs/adr/0001.md#contexto)" in u)
check("absolutize: absolute link untouched", "](https://x.y/z)" in u)
check("defang: mention in prose and in backticks loses its ping, e-mail untouched",
      t.defang("o `@codex review` e @fulano, a@b.com") == "o `@\u200bcodex review` e @\u200bfulano, a@b.com")
check("defang: applied on the report path",
      "@\u200bcodex" in r.unwrap(["pediu `@codex review`"], rctx))
check("defang: applied on the TODO path", all("@codex" not in t.render_body(i, ctx) for i in items))

stem = "R"
extra = r.extra_findings({"Uma obs": 9}, spans, rlines, set(by))
check("--link by heading prefix picks the unnumbered section", len(extra) == 1 and extra[0].lines == ["corpo da observação"])
for name, links in (("no", {"Nada casa": 9}), ("two", {"Uma": 9})):
    try:
        r.extra_findings(links, spans, rlines, set(by))
        check(f"--link whose prefix matches {name} heading(s) is refused", False)
    except SystemExit:
        check(f"--link whose prefix matches {name} heading(s) is refused", True)

p = r.build_rplan(found, [], {}, {}, stem, False)
check("rplan: closed -> create, open without link -> LINK?",
      [f.key for f in p.create] == ["1"] and sorted(f.key for f in p.needs_link) == ["2", "3", "4"])
check("rplan: --open-unlinked creates the open ones too", len(r.build_rplan(found, [], {}, {}, stem, True).create) == 4)
p = r.build_rplan(found, [], {"2": 50}, {50: []}, stem, False)
check("rplan: linked open finding -> comment", [(f.key, n) for f, n in p.comment] == [("2", 50)])
posted = r.comment_body(by["2"], rctx)
p = r.build_rplan(found, [], {"2": 50}, {50: ["outro", posted]}, stem, False)
check("rplan: comment already there -> ok, not posted twice", not p.comment and any(f.key == "2" for f, _ in p.ok))
iss = {"number": 7, "state": "CLOSED", "body": r.issue_body(by["1"], rctx)}
p = r.build_rplan(found, [iss], {}, {}, stem, False)
check("rplan: issue with the same key and hash -> ok", not p.create and not p.update and not p.close)
p = r.build_rplan(found, [dict(iss, state="OPEN")], {}, {}, stem, False)
check("rplan: resolved finding whose issue is open -> close (crash between create and close)",
      [i["number"] for _, i in p.close] == [7])
p = r.build_rplan(found, [dict(iss, body=iss["body"].replace("report-hash: ", "report-hash: 0"))], {}, {}, stem, False)
check("rplan: changed text -> update", [i["number"] for _, i in p.update] == [7])

sys.exit(1 if fails else 0)
