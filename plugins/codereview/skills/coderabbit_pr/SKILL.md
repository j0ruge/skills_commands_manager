---
name: coderabbit_pr
metadata:
  version: 3.3.1
description: Resolves AI review comments on a GitHub PR — auto-detects CodeRabbit, Copilot, Gemini, Codex; creates per-reviewer checklists, verifies findings against current code, applies fixes, runs regression tests, resolves GitHub conversations. Triggers — coderabbit, copilot review, gemini review, codex review, fix PR review.
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

If `$ARGUMENTS` is empty or does not contain a PR number, ask: "What is the PR number?"

## Goal

Extract all review comments left by AI reviewers on a GitHub PR, create a structured checklist file **per reviewer** (e.g., `coderabbit-review.md`, `copilot-review.md`), verify each comment against the current code, fix valid issues, run regression tests, and resolve all GitHub conversations. Every item ends resolved with a justification.

This skill is **project-agnostic** and **reviewer-agnostic** — it works with any repo and any supported AI reviewer.

---

## Model Routing Strategy

This skill uses different model tiers to optimize token usage. The orchestrating model (you) stays in control and delegates mechanical work to cheaper models via Agent subagents.

| Phase | Task | Model | Why |
|-------|------|-------|-----|
| 1.1 | GitHub API calls, repo detection | **haiku** | Pure CLI commands, no reasoning needed |
| 1.2 | Fetch raw comments from API | **haiku** | Data retrieval, returns raw JSON |
| 1.3 | Parse & structure comments | **sonnet** | Needs pattern matching intelligence but not deep reasoning |
| 2 | Create checklist file | Main model | Quick write from structured data |
| 3 | Analyze each comment (verdict) | **Main model (opus)** | Critical judgment: is the issue real? Does the spec support it? |
| 3 | Apply code fixes | **sonnet** | Mechanical code edits based on opus verdict |
| 4 | Run tests | Main model | Simple command execution |
| 5 | Resolve GitHub threads | **haiku** | Mechanical GraphQL mutations |

**How to delegate**: Use the `Agent` tool with the `model` parameter:
```
Agent({ model: "haiku", prompt: "..." })   // for data fetching
Agent({ model: "sonnet", prompt: "..." })  // for parsing/fixing
```

**When NOT to delegate**: If the PR has fewer than 5 total comments across all reviewers, skip model routing — process everything in the main model. The overhead of spawning agents isn't worth it for small reviews.

---

## Operating Constraints

**MODIFIES CODE**: This skill reads review comments, verifies issues, and applies fixes. It creates one tracking file per reviewer in the project root.

**Git awareness**: All fixes are made on the current branch. The skill does NOT create commits — the user decides when to commit.

**Scope discipline**: Only fix issues raised by the reviewers. Do not introduce unrelated refactors, improvements, or style changes.

**Error Handling**:

- **`gh` CLI not available or not authenticated**: Stop with: "The `gh` CLI is not installed or authenticated. Run `gh auth login` before using this skill."
- **PR not found**: Stop with: "PR #{n} not found or insufficient permissions."
- **No review comments from any bot**: Stop with: "No AI review comments found on PR #{n}."
- **File no longer exists**: Mark as `[x] File removed — not applicable`.
- **Line not locatable** (heavy modifications since review): Use context clues (function name, surrounding code) to locate. If truly unmappable: `[x] Not locatable in current code — requires manual review`.
- **Test command not detected**: Ask the user which command to use. Never skip tests silently.

---

## Execution Steps

### Phase 1: Detect Reviewers & Extract Comments

#### 1.1 Detect Repository Context

Verify `gh` is available and authenticated:

```bash
gh auth status
```

Detect the repo:

```bash
gh repo view --json nameWithOwner -q '.nameWithOwner'
```

Capture the result as `REPO` (format: `owner/repo`).

#### 1.2 Detect Which Reviewers Are Present

**Spawn a haiku agent** to discover which AI review bots left comments:

```
Agent(model: "haiku", prompt: "Run these two commands and return ONLY the unique bot
logins that appear in both outputs, one per line:

gh api 'repos/{REPO}/pulls/{PR}/comments' --paginate --jq '[.[].user.login] | unique[]'
gh api 'repos/{REPO}/pulls/{PR}/reviews' --paginate --jq '[.[].user.login] | unique[]'
")
```

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

For each detected reviewer, **spawn a sonnet agent** to fetch and parse all comments. Launch agents **in parallel** (one per reviewer) for efficiency.

The agent prompt should include:
1. The reviewer's GitHub login
2. The parsing rules from `references/reviewer-registry.md` for that specific reviewer
3. Instructions to return a **structured numbered list** (not raw JSON) with these fields per finding:
   - Sequential number
   - Severity (CRITICAL/HIGH/MEDIUM/LOW)
   - File path and line number
   - Title (bold text or first sentence)
   - Summary (1-2 sentences)
   - Whether a code suggestion is included (yes/no)
   - Source (inline/review-body/nitpick)

**Important — Large Output Handling**: The GitHub API can return 30-50KB+ of raw data. The sonnet agent absorbs this within its own context, parses it, and returns only the structured summary. This prevents the main (opus) context from being polluted with raw API data.

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

For reviewers with **zero findings** (e.g., Gemini approved without issues), generate a minimal file:

```markdown
# {Reviewer Name} Review — PR #{number}

**Repository**: {owner/repo}
**Reviewer**: {bot login}
**Date**: {YYYY-MM-DD}

No actionable findings — reviewer approved without issues.
```

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

#### 5.1 Fetch All Review Threads

**Spawn a haiku agent** to fetch all unresolved thread IDs:

```
Agent(model: "haiku", prompt: "Run this GraphQL query and return the results:

gh api graphql -f query='{
  repository(owner: \"{OWNER}\", name: \"{REPO_NAME}\") {
    pullRequest(number: {PR_NUMBER}) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 1) {
            nodes {
              author { login }
              path
            }
          }
        }
      }
    }
  }
}'

Return ONLY the unresolved threads as: id, author login, path — one per line.
")
```

#### 5.2 Resolve Each Unresolved Thread

**Spawn a haiku agent** to resolve all unresolved threads in batch:

```
Agent(model: "haiku", prompt: "Resolve each of these GitHub review threads by running
this GraphQL mutation for each thread ID:

gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: \"{ID}\"}) { thread { isResolved } } }'

Thread IDs: {list of IDs}

Run them in parallel. Report how many succeeded.
")
```

Resolve threads from ALL reviewers (coderabbitai, copilot, gemini, codex, etc.) — not just the ones processed in Phase 3.

#### 5.3 Verify All Resolved

Run the fetch query again to confirm zero unresolved threads remain. Update each checklist with:

```markdown
### Conversations

- **Total threads**: {n}
- **Resolved in this run**: {n}
- **Previously resolved**: {n}
```

---

## Operating Principles

### Fidelity

- **Address every comment**: Every item across all reviewer files must end with `[x]` and a justification. Never skip or ignore.
- **Respect original intent**: Follow the reviewer's suggestion unless it is demonstrably wrong or contradicts project specs. Explain alternative approaches.
- **Verify against specs**: When a reviewer questions a design decision, check the project's specs, data models, and documentation before deciding. AI reviewers don't have full project context — many "issues" are by-design choices.
- **Preserve code style**: Match the existing project's coding conventions.

### Progress

- **Incremental saves**: Each checklist file is updated after each resolved item.
- **Resumability**: If the skill is interrupted, re-running it will verify already-checked items without re-applying fixes.

### Discipline

- **No scope creep**: Only fix issues raised by the reviewers.
- **No unrelated changes**: Even if you notice other issues while reading code, do NOT fix them.
- **Don't expand scope to fix latent bugs**: pre-existing test failures unmasked by your fixes (see Phase 4.0 baseline) are NOT yours to fix. Document and open follow-up issue.
- **Verify before trust**: reviewer claims about files, line numbers, runtime behavior, prior-session diagnoses, or external artifacts ("as documented in X", cached plans, old issues) are hypotheses to validate against the live PR diff and current code, not facts. Same anti-silencing principle from Phase 4.0 applied in another direction: don't propagate a reviewer's diagnosis without primary evidence that it still holds. Phase 3.1 step 1.5 enforces this per-item.
- **No commits**: Leave committing to the user.

### Token Efficiency

- **Delegate data fetching** to haiku agents — they handle API calls and return summaries
- **Delegate parsing** to sonnet agents — they absorb large outputs and return structured lists
- **Keep analysis in opus** — judgment calls about code correctness need the strongest model
- **Delegate mechanical fixes** to sonnet agents when there are many (>5) fixes to apply
- **Skip agent routing** for small PRs (<5 comments) — the overhead isn't worth it
