---
name: coderabbit_pr
metadata:
  version: 3.5.1
description: Resolves AI review comments on a GitHub PR — auto-detects CodeRabbit, Copilot, Gemini, Codex; creates per-reviewer checklists, verifies findings against current code (with byte-exact inspection when reviewers cite invisible/control characters), applies fixes, runs regression tests, resolves GitHub conversations, then cleans up its own checklist files. Triggers — coderabbit, copilot review, gemini review, codex review, fix PR review.
---

## User Input

```text
$ARGUMENTS
```

Parse the user input before proceeding:

- **PR number** (required): integer, e.g. `49` or `#49`
- **Optional flags**:
  - `--skip-tests` — skip Phase 4 (regression testing)
  - `--dry-run` — verify only, do not apply fixes
  - `--reviewer <name>` — process only a specific reviewer (e.g., `--reviewer coderabbit`). Default: all detected reviewers.
  - `--keep-checklists` — keep the `{reviewer}-review.md` files after a successful run instead of deleting them (Phase 6). Use when you want the checklist as a durable audit artifact.

If `$ARGUMENTS` is empty or does not contain a PR number, ask: "What is the PR number?"

## Goal

Extract all review comments left by AI reviewers on a GitHub PR, create a structured checklist file **per reviewer** (e.g., `coderabbit-review.md`, `copilot-review.md`), verify each comment against the current code, fix valid issues, run regression tests, and resolve all GitHub conversations. Every item ends resolved with a justification.

This skill is **project-agnostic** and **reviewer-agnostic** — it works with any repo and any supported AI reviewer.

---

## Model Routing Strategy

This skill uses different model tiers to optimize token usage. The orchestrating model (you) stays in control and delegates mechanical work to cheaper models via Agent subagents.

| Phase | Task | Model | Why |
|-------|------|-------|-----|
| 1.1 | Repo/branch/PR context | **Run inline** | Fixed commands with a single correct answer |
| 1.2 | Detect which reviewers commented | **Run inline** | An API projection, not a judgment call |
| 1.3 | Fetch comments (extraction) | **Run inline** | Fixed `--jq` projection — see 1.3 |
| 1.3 | Structure findings (interpretation) | **sonnet**, only if large | Pattern matching over prose; delegate only past the size threshold |
| 2 | Create checklist file | Main model | Quick write from structured data |
| 3 | Analyze each comment (verdict) | **Main model (opus)** | Critical judgment: is the issue real? Does the spec support it? |
| 3 | Apply code fixes | **sonnet** | Mechanical code edits based on opus verdict |
| 4 | Run tests | Main model | Simple command execution |
| 5 | Resolve GitHub threads | **Run inline** | GraphQL mutations + a count that must reach zero |
| 6 | Clean up checklist files | **Run inline** | Deleting known paths |

**How to delegate** (for the rows that still delegate): use the `Agent` tool with the `model` parameter:
```
Agent({ model: "sonnet", prompt: "..." })  // for parsing/fixing
```

**Why so much of this is inline now.** Fetching comments and resolving threads are mechanical: the commands have one correct answer, and a subagent in the middle can only add variance, latency, and silent omission. A run that skips a thread or drops a comment looks identical to a clean run — the failure is invisible. Determinism here isn't about saving tokens, it's about being able to trust the result. Delegation stays where a model genuinely adds something: reading prose findings (1.3, above the size threshold), judging correctness (3), and editing code (3.2).

**When NOT to delegate anything**: if the PR has fewer than 5 total comments across all reviewers, process everything in the main model.

---

## Operating Constraints

**MODIFIES CODE**: This skill reads review comments, verifies issues, and applies fixes. It creates one tracking file per reviewer in the project root — these are **ephemeral working state**, deleted in Phase 6, not deliverables.

**Git awareness**: fixes must land on **the PR's head branch**, which is not necessarily the branch you happen to be on — see Phase 1.1. The skill does NOT create commits — the user decides when to commit.

**Scope discipline**: Only fix issues raised by the reviewers. Do not introduce unrelated refactors, improvements, or style changes.

**Error Handling**:

- **`gh` CLI not available or not authenticated**: Stop with: "The `gh` CLI is not installed or authenticated. Run `gh auth login` before using this skill."
- **PR not found**: Stop with: "PR #{n} not found or insufficient permissions."
- **No known reviewer bot posted anything at all** (nothing in `/comments` *and* nothing in `/reviews`): Stop with: "No AI review comments found on PR #{n}."
  This is **not** the same as a reviewer that posted but yielded zero actionable findings — an approval, a summary with no issues, or "unable to review". Those go through Phase 2's zero-findings path and must be reported, because case (b) there is a coverage gap the user needs to hear about. Stopping on them would swallow the most important thing the run learned.
- **File no longer exists**: Mark as `[x] File removed — not applicable`.
- **Line not locatable** (heavy modifications since review): Use context clues (function name, surrounding code) to locate. If truly unmappable: `[x] Not locatable in current code — requires manual review`.
- **Test command not detected**: Ask the user which command to use. Never skip tests silently.

---

## Execution Steps

### Phase 1: Detect Reviewers & Extract Comments

#### 1.1 Detect Repository, Branch, and Leftover State

```bash
gh auth status                                          # must be authenticated
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)   # owner/repo
PR=<the PR number from the user input>
```

**Confirm you are on the PR's branch.** The branch you start on is frequently *not* the
PR's branch — the user may have moved on to other work since opening it. Applying review
fixes to whatever branch happens to be checked out puts them on unrelated work and they
never reach the PR, with nothing failing loudly to reveal it:

```bash
git branch --show-current
gh pr view "$PR" --json headRefName -q .headRefName
```

If they differ:
- **Working tree clean** → `git checkout <headRefName>`, and tell the user you switched.
- **Working tree dirty** → stop and report. Moving HEAD over uncommitted work is exactly
  the surprise to avoid; let the user stash or commit first.

When the run ends, state which branch the edits landed on — the user may have started elsewhere.

**Sweep leftover checklists.** Files matching `*-review.md` in the project root are this
skill's own scratch space from a previous run. If one exists whose header names a
**different** PR, it is stale garbage: delete it rather than reading it as if it described
the current PR (Phase 3's cross-reviewer check consults these files, so a stale one
actively misleads the run).

```bash
grep -l "Review — PR #" *-review.md 2>/dev/null | while read -r f; do
  head -5 "$f" | grep -q "PR #${PR}\b" || { echo "stale, removing: $f"; rm -- "$f"; }
done
```

#### 1.2 Detect Which Reviewers Are Present

Run both directly — a login list is an API projection, and the `--jq` filter already
produces the exact answer:

```bash
gh api "repos/$REPO/pulls/$PR/comments" --paginate --jq '[.[].user.login] | unique[]'
gh api "repos/$REPO/pulls/$PR/reviews"  --paginate --jq '[.[].user.login] | unique[]'
```

Query **both** endpoints and union the results. They disagree in practice: a reviewer can
post only a review body with no inline comments (Gemini's summary, or a bot reporting it
could not run), and another can post inline comments without a review body. Reading one
endpoint alone silently drops a reviewer.

Match the returned logins against the reviewer registry in `references/reviewer-registry.md`. The known bots are:

| Login | Reviewer |
|-------|----------|
| `coderabbitai[bot]` / `coderabbitai` | CodeRabbit |
| `copilot-pull-request-reviewer` | Copilot |
| `gemini-code-assist[bot]` | Gemini |
| `github-codex[bot]` / `codex-reviewer[bot]` | Codex |

If `--reviewer` flag was passed, filter to only that reviewer.

If no known reviewers are found, stop with the "no comments" error.

Report to the user: "Found reviews from: {list of reviewers}. Processing {N} reviewer(s)."

#### 1.3 Fetch & Parse Comments Per Reviewer

Separate **extraction** (mechanical, fixed) from **interpretation** (needs a model). Only the second half benefits from delegation.

**Extraction — always run these directly:**

```bash
# Inline comments (attached to diff lines)
gh api "repos/$REPO/pulls/$PR/comments" --paginate --jq '.[] |
  "=====\nID: \(.id)\nAUTHOR: \(.user.login)\nPATH: \(.path)\nLINE: \(.line // .original_line)\nBODY:\n\(.body)\n"'

# Review bodies (where CodeRabbit and Gemini put most findings)
gh api "repos/$REPO/pulls/$PR/reviews" --paginate --jq '.[] | select(.body != "") |
  "=====\nID: \(.id)\nAUTHOR: \(.user.login)\nSTATE: \(.state)\nBODY:\n\(.body)\n"'
```

Two details that are easy to get wrong:

- `\(.line // .original_line)` — `line` comes back **null** once the diff around a comment
  goes stale (force-push, rebase, later commits). Without the fallback to `original_line`
  those findings arrive with no anchor and get misfiled as "not locatable".
- `select(.body != "")` — approvals and review stubs carry an empty body; keeping them
  produces phantom findings.

This projection is also what solves the context problem: the raw endpoints return 30-50KB
of `diff_hunk`, URLs, reactions, and nested user objects. Projecting to the five fields
that matter discards that **before** it reaches any context — better than absorbing it
into a subagent and hoping the summary is faithful.

**Interpretation — delegate only when the output is genuinely big.** If the projected text
is large (roughly >1500 lines, or 3+ reviewers each with a long review body), hand *that
text* to a sonnet agent per reviewer, in parallel. Otherwise structure it yourself; for the
typical PR the projection is already short and a round trip buys nothing.

Whoever does it, produce a **structured numbered list** with these fields per finding:
- Sequential number
- Severity (CRITICAL/HIGH/MEDIUM/LOW) — per `references/reviewer-registry.md`
- File path and line number
- Title (bold text or first sentence)
- Summary (1-2 sentences)
- Whether a code suggestion is included (yes/no)
- Source (inline/review-body/nitpick)

**Deduplication rules** the agent must apply:
- Match by file path + line range + first 100 chars of title
- If the same finding appears both inline and in the review body, keep the inline version (it has more precise line info)
- If multiple findings share the same root cause (same file section, same fix), keep them as separate items but note "Related to item #N"

**Discard**: Comments that are purely metadata (walkthrough summaries, paused review notices, "Actionable comments posted" headers, `<!-- fingerprinting:... -->` blocks).

If the total count after filtering is 0 for a reviewer, note it — Phase 2 will still create a minimal file for audit completeness.

---

### Phase 2: Create Checklist Files

For each reviewer with findings, generate `{reviewer}-review.md` in the project root following the structure in `references/checklist-template.md`.

Output file names:
- CodeRabbit → `coderabbit-review.md`
- Copilot → `copilot-review.md`
- Gemini → `gemini-review.md`
- Codex → `codex-review.md`
- Unknown → `{bot-login}-review.md`

For reviewers with **zero findings**, first work out *why* there are none — the two causes look identical in the data and mean opposite things. Then decide **where that belongs**:

- **Without `--keep-checklists`** (the default): do **not** write a file. Phase 6 would delete it seconds later, so it never becomes the audit artifact the file is for — it is pure churn. Carry the (a)/(b) determination into the **final report** instead, which is where the user actually reads it.
- **With `--keep-checklists`**: write the minimal file using the matching template below, since it will survive the run.

Either way the *determination* is mandatory — it is the difference between "this PR passed review" and "nobody looked at this PR".

**(a) It reviewed and found nothing** — a genuine pass:

```markdown
# {Reviewer Name} Review — PR #{number}

**Repository**: {owner/repo}
**Reviewer**: {bot login}
**Date**: {YYYY-MM-DD}

No actionable findings — reviewer approved without issues.
```

**(b) It never actually ran** — quota exhausted, bot error, review still pending. Bots
announce this in the review body (e.g. *"Copilot was unable to review this pull request
because the user who requested the review has reached their quota limit"*), and a check
that sits `PENDING` forever is the same story. Recording that as "approved without issues"
is false and it buries a real coverage gap — nobody looked at this PR:

```markdown
# {Reviewer Name} Review — PR #{number}

**Repository**: {owner/repo}
**Reviewer**: {bot login}
**Date**: {YYYY-MM-DD}

**No review was performed** — this is not an approval. Reviewer reported:

> {literal text the bot returned}

Coverage gap: this PR has not been reviewed by {Reviewer Name}. Re-request the review
once the underlying cause clears.
```

Do not count a reviewer in case (b) as coverage in the final summary, and say so in the
closing report — the user is entitled to know which reviewers actually looked.

For reviewers **with findings**:
- Items ordered by severity: CRITICAL > HIGH > MEDIUM > LOW
- Each item has a checkbox (`- [ ]`), sequential number, severity tag, file:line, and title
- Include a summary of the issue (1-2 sentences)
- Note items pre-addressed
- Add a "Final Result" summary table at the bottom (initially all Pending)

---

### Phase 3: Verify and Fix Each Comment

Process ALL checklist items across ALL reviewer files. Group items by file to minimize reads — a single file may have findings from multiple reviewers.

#### 3.1 Analysis (Main Model — Opus)

For each item (or group of items in the same file):

1. **Read the current code** at the referenced file and line (with ~30 lines of context)
1.1. **Byte-exact verification for control-character claims** — when the reviewer mentions NUL bytes (`\0`, `0x00`, `^@`), BOM, zero-width characters, non-printable bytes, embedded escape sequences, or anything described as "invisible/control character", the `Read` tool will render those bytes as plain whitespace and silently mislead the analysis. The screen output of `\0create\0` is indistinguishable from ` create ` (regular spaces) — both look like leading-space sentinels. Before classifying such a finding as false positive, confirm against the actual bytes:
   - Inspect a specific line: `awk 'NR==<line>' <file> | od -c | head`
   - Count NUL bytes in a whole file: `tr -cd '\000' < <file> | wc -c`
   - Search for arbitrary byte patterns: `xxd <file> | grep -i <pattern>`
   - Fallback when `od`/`xxd`/`tr` are unavailable: `python -c "print(repr(open('<file>').read()))"` — `repr()` produces a byte-faithful representation that escapes control characters.

   The `Read` view is a normalized text rendering, not byte-faithful. Trust `od`/`xxd` over `Read` whenever the finding hinges on what specific bytes are present. Same anti-trust principle as 1.5 (verify referenced state) applied to a different surface: don't outsource truth about bytes to a normalized view.
1.5. **Verify referenced state** — if the reviewer cites a file path, line number, runtime behavior, or references an external artifact ("as documented in X", "see previous session", a cached plan, an old issue, "this was fixed in commit Y"), confirm against the current state BEFORE accepting the diagnosis. PR diff and live code are authoritative; reviewer comments may have been written against a snapshot that is now obsolete (force-pushed, rebased, or simply old). If the cited file/line/behavior no longer matches what the reviewer described, mark the item as `[x]` — "Reviewer claim no longer applies: <what changed>" and move on. This is the same anti-silencing principle from Phase 4.0 baseline applied in another direction: do not propagate a reviewer's diagnosis without primary evidence that it still holds.
2. **Check project specs/docs** if the comment questions a design decision. Many "issues" flagged by AI reviewers are actually by-design choices documented in specs, data models, or CLAUDE.md. Before marking as "Fixed", verify the reviewer isn't wrong.
3. **Recalibrate severity**: AI reviewers often default to MEDIUM or don't assign severity at all (Copilot, Codex). After reading the code and understanding the real impact, **reassign the severity** based on actual risk:
   - **CRITICAL**: data loss, security vulnerability, crash in production path
   - **HIGH**: broken feature flow, silent data corruption, regression from recent commit
   - **MEDIUM**: incorrect behavior in edge case, inconsistency, missing validation
   - **LOW**: style, naming, docs, nitpick
   Update the severity tag in the checklist if it changes from the original.
4. **Cross-reviewer check**: Before fixing, check if the same issue was already resolved in another reviewer's checklist. If so, mark as: `[x]` — "Already fixed — see {other-reviewer}-review.md #{item number}". This avoids duplicate work and creates an audit trail across reviewer files.
5. **Evaluate**: Does the issue described still exist? Is the reviewer's concern valid?
6. **Decide**:

   | Situation | Action | Checklist Status |
   |-----------|--------|-----------------|
   | Issue does not exist (already fixed or code rewritten) | None | `[x]` — "Already fixed" |
   | Issue fixed by another reviewer's round | None | `[x]` — "Already fixed — see {reviewer}-review.md #{N}" |
   | Issue exists, suggestion is valid | Prepare fix description | `[x]` — "Fixed" |
   | Issue exists, better fix available | Prepare alternative fix | `[x]` — "Fixed (alternative approach: {reason})" |
   | Issue exists but code is actually correct | None | `[x]` — "Not applicable: {reason}" |
   | Design decision documented in spec/docs | None | `[x]` — "Not applicable — by design per {spec reference}" |
   | `--dry-run` mode | None (verify only) | `[x]` — "Verified: {needs fix / already fixed / not applicable}" |

#### 3.2 Fix Execution

After the main model decides which items need fixes:

- **5 or fewer fixes**: Apply them directly in the main model (the overhead of spawning agents isn't worth it).
- **More than 5 fixes**: **Spawn sonnet agents** to apply fixes in parallel, grouped by file. Each agent receives:
  - The file path
  - The list of fixes to apply (with exact old_string → new_string or clear descriptions)
  - Instructions to NOT make any changes beyond what's specified

#### 3.3 Efficiency

- When multiple comments reference the same file, read it once and process all together
- Use parallel tool calls to read independent files simultaneously
- For large files (>500 lines), read only the relevant section
- Cross-reference items across reviewers: if CodeRabbit and Copilot flag the same line, verify once and update both checklists

#### 3.4 Update Checklists

After each item (or batch), update the corresponding reviewer's checklist file. Mark the checkbox and add the status line.

---

### Phase 4: Regression Testing

Skip if `--skip-tests` was passed.

**Also skip if Phase 3 changed no files** — zero findings, or every item resolved as
already-fixed / not-applicable. This phase compares a before and an after; with no edits
there is no after, so a run proves nothing. Two concrete costs to running it anyway: on a
large suite it is minutes of pointless work, and any failure it surfaces is pre-existing
by construction yet arrives looking like this run caused it — the exact confusion the
4.0 baseline exists to prevent. Say in the report that tests were skipped and why.

#### 4.0 Capture Pre-Fix Baseline

**Run the project's test command BEFORE applying any review fixes.** Save the pass/fail counts and the list of failing test names. This is your **baseline** of pre-existing latent failures.

Why this matters: when CI is broken by an early-step failure (lint syntax error, missing config, broken `npm exec`), GitHub never reaches the test step — so failing tests in the test step are invisible until the early step is fixed. After your fixes unblock CI, those latent failures **appear as if they were caused by your edits**, but they were always there.

Without a baseline, Phase 4.2 cannot tell "regression caused by my fix" from "pre-existing latent unmasked by my fix" — and the skill ends up trying to fix unrelated bugs, expanding scope uncontrollably.

**Save the baseline as:**

```
baseline_pass: <number>
baseline_fail: <number>
baseline_failing_tests:
  - <test 1 name>
  - <test 2 name>
  ...
```

If the baseline already shows N>0 failures, document them in each `{reviewer}-review.md` checklist (a "Pre-existing latent failures" subsection) BEFORE applying any fixes. They are out of scope for this run.

#### 4.1 Detect Test Command

| Priority | Detection | Command |
|----------|-----------|---------|
| 1 | `package.json` has `scripts.test` | `npm test` |
| 2 | Monorepo with multiple `package.json` | `npm test` in each package with modified files |
| 3 | `*.sln` or `*.csproj` exists | `dotnet test` |
| 4 | `Cargo.toml` exists | `cargo test` |
| 5 | `pyproject.toml` or `setup.py` | `pytest` |
| 6 | `go.mod` exists | `go test ./...` |
| 7 | `Makefile` has `test` target | `make test` |
| 8 | None detected | Ask the user |

#### 4.2 Run and Compare Against Baseline

Execute the test command after applying fixes. Compare against the Phase 4.0 baseline:

- **All pass and baseline was 0**: update all checklists with "All tests passed ({n} tests)."
- **Same failures as baseline (no new fails, no fewer fails)**: pre-existing latent — note in checklists, **do NOT attempt to fix in this PR**. Open a follow-up issue with the error signature and a link to this PR. Scope discipline is the priority.
- **New failures (failing tests not in baseline)**: caused by your fixes — diagnose and correct. These ARE regressions.
- **Fewer failures than baseline**: your fixes accidentally fixed something. Note it but don't claim credit; the fix may be incidental and could regress later.
- **Mixed (some pre-existing + some new)**: separate the two lists. Fix only the new failures in this PR. Pre-existing go to the follow-up issue.

**Do not silence failing tests** (e.g., `it.skip`, `if: false` on the workflow step, `continue-on-error: true`) to make CI green. Document and defer.

**Cascade-aware rerun**: if your fixes uncovered new failures (the "new failures" branch above), consider rerunning the baseline AGAIN after addressing them — fail-fast cascades can have more than 2 levels (bug 1 masks bug 2 masks bug 3). The second bug surfaced is not necessarily the last; sibling cicd skill v2.5.0 documents a real 3-level cascade in PR #6 of `validade_bateria_estoque`. After each layer of fixes, capture a fresh baseline before declaring victory.

#### 4.3 Update Final Status

Update the "Final Result" table in each `{reviewer}-review.md` with:
- Count of items by status (Fixed, Already fixed, Not applicable, Pending)
- Test results

---

### Phase 5: Resolve GitHub Conversations

After all items are processed and tests pass, resolve all review threads on the PR.

Run all three steps directly. This is pure mechanics, and the closing count is the point:
a delegated batch that silently skips a thread reports success just as convincingly as one
that didn't.

#### 5.1 List Unresolved Threads

`OWNER` and `REPO_NAME` are the two halves of `$REPO`.

```bash
gh api graphql -f query='{
  repository(owner: "OWNER", name: "REPO_NAME") {
    pullRequest(number: PR_NUMBER) {
      reviewThreads(first: 100) {
        nodes { id isResolved comments(first: 1) { nodes { author { login } path } } }
      }
    }
  }
}' --jq '.data.repository.pullRequest.reviewThreads.nodes[]
         | select(.isResolved == false)
         | "\(.id)\t\(.comments.nodes[0].author.login)\t\(.comments.nodes[0].path)"'
```

#### 5.2 Resolve Each Thread

Resolve threads from ALL reviewers (coderabbitai, copilot, gemini, codex, …) — not just the ones processed in Phase 3.

```bash
for id in <thread IDs from 5.1>; do
  gh api graphql -f query="mutation { resolveReviewThread(input: {threadId: \"$id\"}) { thread { isResolved } } }" \
    --jq '.data.resolveReviewThread.thread.isResolved' | sed "s|^|$id -> |"
done
```

Each line must print `true`. Anything else (an error, `false`) means that thread is still open — carry it into 5.3 rather than moving on.

#### 5.3 Verify Zero Remain

```bash
gh api graphql -f query='{
  repository(owner: "OWNER", name: "REPO_NAME") {
    pullRequest(number: PR_NUMBER) { reviewThreads(first: 100) { nodes { id isResolved } } }
  }
}' --jq '"total: \(.data.repository.pullRequest.reviewThreads.nodes | length)  unresolved: \([.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved==false)] | length)"'
```

`unresolved: 0` is the success condition, and the gate for Phase 6. If it is not zero,
report which threads remain and why — never describe the run as complete. Note that
`reviewThreads(first: 100)` caps at 100; on a PR that busy, page through and say so
instead of quietly covering the first hundred.

Update each checklist with:

```markdown
### Conversations

- **Total threads**: {n}
- **Resolved in this run**: {n}
- **Previously resolved**: {n}
```

---

### Phase 6: Clean Up the Checklist Files

The `{reviewer}-review.md` files are scratch space for this run, not deliverables. Left
behind, they rot: a checklist from PR #7 still sitting in the tree weeks later gets read
by the next run's cross-reviewer check (Phase 3.1 step 4) as though it described the
current PR, and it clutters `git status` for everyone else.

Once 5.3 reports `unresolved: 0` and the report is written, delete them — matching on the
header this skill writes, so an unknown reviewer's `{bot-login}-review.md` is covered
without a hardcoded list, and an unrelated project doc that merely ends in `-review.md`
(`security-review.md`, `architecture-review.md`) is left alone:

```bash
grep -l "Review — PR #${PR}\b" *-review.md 2>/dev/null | while read -r f; do
  echo "removing: $f"; rm -- "$f"
done
```

A bare `rm -f *-review.md` is the tempting one-liner and the wrong answer: it deletes files
this skill never created. Matching the header is both deterministic and scoped — the same
guard Phase 1.1 uses to sweep leftovers.

Skip this when `--keep-checklists` was passed, or in `--dry-run` (which never claims completion).

Two rules that only work as a pair:

- **Always name the file exactly `{reviewer}-review.md`** — never a per-PR variant like
  `gemini-review-pr15.md`. Projects gitignore these with `*-review.md`, and a suffixed
  name slips past that pattern and becomes a permanently untracked file.
- **Always delete on success.** The fixed name is only safe *because* nothing survives to
  collide with it. If a previous run's file is still there, that is a bug this phase
  exists to prevent (and Phase 1.1 sweeps as a backstop) — not a reason to rename.

This does not break the resumability promised under Operating Principles: cleanup runs
only on the success path, so an interrupted run leaves its checklists exactly where a
resume needs them.

If the project has no `.gitignore` entry for these, suggest adding `*-review.md` as
defence in depth — but the deletion above is the real fix, not the ignore rule.

**Where the audit trail lives instead**: the resolved GitHub threads, the PR diff, and the
commit message. The final report to the user should carry the findings table, since the
file it came from is gone.

---

## Operating Principles

### Fidelity

- **Address every comment**: Every item across all reviewer files must end with `[x]` and a justification. Never skip or ignore.
- **Respect original intent**: Follow the reviewer's suggestion unless it is demonstrably wrong or contradicts project specs. Explain alternative approaches.
- **Verify against specs**: When a reviewer questions a design decision, check the project's specs, data models, and documentation before deciding. AI reviewers don't have full project context — many "issues" are by-design choices.
- **Preserve code style**: Match the existing project's coding conventions.

### Progress

- **Incremental saves**: Each checklist file is updated after each resolved item.
- **Resumability**: If the skill is interrupted, re-running it will verify already-checked items without re-applying fixes. This is why Phase 6 deletes the checklists only on the success path — a run that died halfway leaves them intact, and a checklist that survives is a signal the previous run did not finish.

### Discipline

- **No scope creep**: Only fix issues raised by the reviewers.
- **No unrelated changes**: Even if you notice other issues while reading code, do NOT fix them.
- **Don't expand scope to fix latent bugs**: pre-existing test failures unmasked by your fixes (see Phase 4.0 baseline) are NOT yours to fix. Document and open follow-up issue.
- **Verify before trust**: reviewer claims about files, line numbers, runtime behavior, prior-session diagnoses, or external artifacts ("as documented in X", cached plans, old issues) are hypotheses to validate against the live PR diff and current code, not facts. Same anti-silencing principle from Phase 4.0 applied in another direction: don't propagate a reviewer's diagnosis without primary evidence that it still holds. Phase 3.1 step 1.5 enforces this per-item.
- **No commits**: Leave committing to the user.

### Determinism and Token Efficiency

- **Run the mechanical phases inline** — reviewer detection (1.2), comment extraction (1.3), thread resolution (5), cleanup (6). Fixed commands with one correct answer; a subagent here only adds variance and the chance of an omission nobody notices.
- **Project with `--jq` instead of absorbing raw JSON** — filtering to the fields you need beats handing 30-50KB to a subagent and trusting the summary, and it costs less.
- **Delegate parsing** to sonnet agents only above the 1.3 size threshold — they absorb long review bodies and return structured lists.
- **Keep analysis in opus** — judgment calls about code correctness need the strongest model.
- **Delegate mechanical fixes** to sonnet agents when there are many (>5) fixes to apply.
- **Skip agent routing entirely** for small PRs (<5 comments) — the overhead isn't worth it.
