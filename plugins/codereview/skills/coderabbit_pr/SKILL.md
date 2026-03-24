---
name: coderabbit_pr
metadata:
  version: 1.0.0
description: >
  Resolve CodeRabbit review comments on a GitHub PR. Extracts all review comments
  from coderabbitai[bot], creates a structured checklist with checkboxes, verifies
  each finding against current code, applies fixes when needed, and runs regression
  tests. Use this skill whenever the user mentions coderabbit, wants to fix or resolve
  coderabbit comments, address PR review feedback from CodeRabbit, handle coderabbit
  findings, process coderabbit suggestions, or triage coderabbit bot comments — even
  if they say it casually like "fix coderabbit" or "resolve the PR comments".
  Triggers: "coderabbit", "coderabbit review", "fix coderabbit", "coderabbit PR",
  "resolve coderabbit", "address coderabbit", "coderabbit comments", "fix PR review",
  "resolver comentarios do coderabbit", "corrigir coderabbit"
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

If `$ARGUMENTS` is empty or does not contain a PR number, ask: "What is the PR number containing the CodeRabbit comments?"

## Goal

Extract all review comments left by CodeRabbit (`coderabbitai[bot]`) on a GitHub PR, create a structured checklist file (`coderabbit-review.md`), verify each comment against the current code, fix valid issues, and run regression tests. Every item ends resolved with a justification.

This skill is **project-agnostic** — it works with any repo that has a GitHub remote and CodeRabbit reviews.

---

## Operating Constraints

**MODIFIES CODE**: This skill reads CodeRabbit comments, verifies issues, and applies fixes. It creates one tracking file (`coderabbit-review.md`) in the project root.

**Git awareness**: All fixes are made on the current branch. The skill does NOT create commits — the user decides when to commit.

**Scope discipline**: Only fix issues raised by CodeRabbit. Do not introduce unrelated refactors, improvements, or style changes.

**Error Handling**:

- **`gh` CLI not available or not authenticated**: Stop with: "The `gh` CLI is not installed or authenticated. Run `gh auth login` before using this skill."
- **PR not found**: Stop with: "PR #{n} not found or insufficient permissions."
- **No CodeRabbit comments**: Stop with: "No CodeRabbit comments found on PR #{n}."
- **File no longer exists**: Mark as `[x] File removed — not applicable`.
- **Line not locatable** (heavy modifications since review): Use context clues (function name, surrounding code) to locate. If truly unmappable: `[x] Not locatable in current code — requires manual review`.
- **Test command not detected**: Ask the user which command to use. Never skip tests silently.

---

## Execution Steps

### Phase 1: Extract CodeRabbit Comments

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

#### 1.2 Fetch Review Comments

Run these API calls to get all CodeRabbit comments. Use `--paginate` for PRs with many comments:

```bash
# Inline review comments (file-level, attached to diff lines)
gh api "repos/{REPO}/pulls/{PR_NUMBER}/comments" --paginate \
  --jq '.[] | select(.user.login == "coderabbitai[bot]") | {path, line: (.line // .original_line), body}'

# Review-level comments (summary/walkthrough reviews)
gh api "repos/{REPO}/pulls/{PR_NUMBER}/reviews" --paginate \
  --jq '.[] | select(.user.login == "coderabbitai[bot]") | {state, body}'
```

If the output is very large, use `--jq` filtering to extract only what is needed rather than loading raw JSON into context.

#### 1.3 Parse Each Comment

From the inline comments, extract for each one:

1. **`path`**: file path relative to repo root
2. **`line`**: line number (use `line` or fallback to `original_line`)
3. **Severity**: parse from comment body:
   - `🔴` or text containing `Critical` → **CRITICAL**
   - `🟠` or text containing `Major` → **HIGH**
   - `🟡` or text containing `Medium` → **MEDIUM**
   - `🔵` or text containing `Minor` or `Low` → **LOW**
   - Refactor suggestion (`Refactor`) → **MEDIUM**
   - No marker found → **MEDIUM** (default)
4. **Title**: first bold text (`**...**`) or heading in the body
5. **Summary**: first paragraph after the title, stripped of HTML comments and CodeRabbit metadata
6. **Addressed status**: if body contains `✅ Addressed` or similar markers, set `pre_addressed: true`
7. **Suggested fix**: if body contains a code block with `suggestion` or `diff`, extract it

Discard comments that are purely metadata (walkthrough summaries, paused review notices) — keep only actionable review findings.

Store as a structured list ordered by: severity (CRITICAL first) then file path.

If the total count after filtering is 0, stop with the "no comments" error.

---

### Phase 2: Create Checklist File

Generate `coderabbit-review.md` in the project root following the structure defined in `references/checklist-template.md`.

Key points:
- Items ordered by severity: CRITICAL > HIGH > MEDIUM > LOW
- Each item has a checkbox (`- [ ]`), sequential number, severity tag, file:line, and title
- Include a summary of the issue (1-2 sentences)
- Note items pre-addressed by CodeRabbit
- Add a "Final Result" summary table at the bottom

---

### Phase 3: Verify and Fix Each Comment

Process each checklist item. Group items by file to minimize file reads.

#### 3.1 For Each Item

1. **Read the current code** at the referenced file and line (with ~30 lines of context)
2. **Evaluate**: Does the issue described still exist in the current code?
3. **Decide**:

   | Situation | Action | Checklist Status |
   |-----------|--------|-----------------|
   | Issue does not exist (already fixed or code rewritten) | None | `[x]` — "Already fixed" |
   | Issue exists, CodeRabbit suggestion is valid | Apply the fix | `[x]` — "Fixed" |
   | Issue exists, better fix available | Apply alternative fix | `[x]` — "Fixed (alternative approach: {reason})" |
   | Issue exists but code is actually correct | None | `[x]` — "Not applicable: {reason}" |
   | `--dry-run` mode | None (verify only) | `[x]` — "Verified: {needs fix / already fixed / not applicable}" |

4. **Update the checklist file** after each item (incremental progress)

#### 3.2 Efficiency

- When multiple comments reference the same file, read it once and process all together
- Use parallel tool calls to read independent files simultaneously
- For large files (>500 lines), read only the relevant section
- Use Explore subagents for bulk verification when there are many items (e.g., 10+ items) to check simultaneously

---

### Phase 4: Regression Testing

Skip if `--skip-tests` was passed.

#### 4.1 Detect Test Command

| Priority | Detection | Command |
|----------|-----------|---------|
| 1 | `package.json` has `scripts.test` | `npm test` |
| 2 | Monorepo with multiple `package.json` | `npm test` in each package with modified files |
| 3 | `Cargo.toml` exists | `cargo test` |
| 4 | `pyproject.toml` or `setup.py` | `pytest` |
| 5 | `go.mod` exists | `go test ./...` |
| 6 | `Makefile` has `test` target | `make test` |
| 7 | None detected | Ask the user |

#### 4.2 Run and Report

Execute the test command. Capture results.

- **All pass**: Update checklist with "All tests passed ({n} tests)."
- **Failures**: Check if failures are related to the applied fixes. If related, attempt to fix. If pre-existing, note in the checklist.

#### 4.3 Update Final Status

Update the "Final Result" table in `coderabbit-review.md` with:
- Count of items by status (Fixed, Already fixed, Not applicable, Pending)
- Test results

---

## Operating Principles

### Fidelity

- **Address every comment**: Every CodeRabbit item must end with `[x]` and a justification. Never skip or ignore.
- **Respect original intent**: Follow CodeRabbit's suggestion unless it is demonstrably wrong. Explain alternative approaches.
- **Preserve code style**: Match the existing project's coding conventions.

### Progress

- **Incremental saves**: The checklist file is updated after each resolved item.
- **Resumability**: If the skill is interrupted, re-running it will verify already-checked items without re-applying fixes.

### Discipline

- **No scope creep**: Only fix issues raised by CodeRabbit.
- **No unrelated changes**: Even if you notice other issues while reading code, do NOT fix them.
- **No commits**: Leave committing to the user.
