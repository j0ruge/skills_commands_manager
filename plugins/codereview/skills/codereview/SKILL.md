---
name: codereview
metadata:
  version: 1.8.0
description: >
  Automated pre-PR code review. Diffs current branch against main, analyzes all
  changed files, and produces a structured report with severity-rated findings,
  test coverage assessment, documentation sync verification, and a final grade.
  Checks docstring coverage, OpenAPI/README/rules sync, race conditions (TOCTOU),
  accessibility, data integrity, hardcoded secrets (passwords, JWT, AWS/GCP/
  GitHub tokens, PEM keys — GitGuardian-equivalent), and code quality. Uses
  model routing to optimize token usage: lightweight models for git context and
  file reading, full-power model for cross-file analysis and final report.
  Use this skill whenever the user asks for code review, pre-PR review, code
  analysis, quality check, documentation check, security review, accessibility
  audit, secret scanning, or wants to review changes before merging — even if
  they don't say "codereview" explicitly.
  Triggers: "code review", "pre-PR review", "review my code", "quality check",
  "review changes", "codereview", "check my code", "analyze code", "PR review",
  "check docs", "documentation review", "security review", "accessibility check",
  "race condition", "toctou", "secret detection", "hardcoded credentials",
  "gitguardian", "ggshield", "leaked password", "api key", "check for secrets"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). Valid inputs:

- Empty: full review of all changed files
- Focus area: `security`, `performance`, `types`, `bugs`, `tests`, `docs`, `a11y`, `race-conditions`
- File path or glob: review only matching changed files
- Key-value overrides: `baseDir=app/ fileExtensions=ts,js` (see `references/configuration.md`)

Read `references/configuration.md` for default values and override syntax.

## Goal

Perform a comprehensive, automated code review of all changes in the current branch compared to the base branch. Produce a structured Markdown report with severity-rated findings, test coverage assessment, and a final grade.

This skill is **stack-agnostic**. Defaults target TypeScript/React but all values are configurable. Set `frameworkPatterns=dotnet` for C#/.NET projects.

---

## Model Routing Strategy

This skill delegates work to cheaper models for data-heavy phases, keeping the main model (opus) for judgment and the final report.

| Phase | Task | Model | Why |
|-------|------|-------|-----|
| A | Git context, file classification, test mapping | **haiku** | Pure CLI + pattern matching |
| B | Per-file analysis (detection passes) | **sonnet** | Pattern matching on code — intelligence without deep reasoning |
| C | Cross-file review, severity calibration, report | **Main (opus)** | Judgment calls, cross-references, coherent report |

**Threshold**: If the branch has ≤3 CODE files, skip model routing — process everything in the main model. The agent overhead isn't worth it for small reviews.

---

## Operating Constraints

**STRICTLY READ-ONLY**: Do **not** modify, create, or delete any files. Do **not** run destructive commands. Output ONLY a structured analysis report in the conversation.

**No Code Rewrites**: This skill identifies issues and suggests fixes in the report — it does NOT apply them.

## Error Handling

- **Git command failures**: include the exact failing command and stop immediately.
- **File read failures**: skip the file and record it as `Could not analyze: {filename} ({reason})`.
- **Context / token exhaustion**: finish analyzing files already processed, note truncation, proceed to report.
- **Timeout**: prioritize CRITICAL/HIGH checks on remaining files, skip MEDIUM/LOW.

Regardless of failures, always produce a final report listing all files analyzed and all failures.

---

## Execution Phases

### Phase A: Git Context & File Classification + Secrets Pre-Scan (haiku agent)

**Spawn a haiku agent** to gather all git context, classify files, AND run the deterministic secrets pre-scan. The agent runs these commands and returns structured results.

```
Agent(model: "haiku", prompt: "
Run these git commands and return the results in a structured format:

1. Verify git repo: git rev-parse --is-inside-work-tree
2. Detect base branch (try: origin HEAD symbolic-ref, then main, then master)
3. Get current branch: git rev-parse --abbrev-ref HEAD
4. Find merge base: git merge-base {BASE_BRANCH} HEAD
5. List changed files: git diff {MERGE_BASE}...HEAD --name-only
6. Diff stats: git diff {MERGE_BASE}...HEAD --stat
7. Commit log: git log {MERGE_BASE}..HEAD --oneline --no-decorate

Then classify each changed file into categories:
- EXCLUDED: lock files, node_modules, dist, build, .next, min files, binaries, .claude/
- CODE: source files matching {fileExtensions} in {baseDir}, excluding tests and generated
- UI_LIB: files in {generatedDirs}
- TESTS: files matching {testFilePatterns}
- CONFIG: files matching {configFilePatterns}
- DOCS: *.md, *.txt
- STYLES: CSS/SCSS/LESS

For each CODE file, check test coverage by probing candidate test file paths:
1. Same dir: {Base}.test.{ext}, {Base}.spec.{ext}
2. __tests__ sibling
3. Project test root
Report each as: WITH_TESTS / STALE_TESTS / NO_TESTS

8. **Run the deterministic secrets pre-scan** — MANDATORY, runs even on small PRs:
     git diff {MERGE_BASE}...HEAD --unified=0 | bash {SKILL_DIR}/scripts/scan_secrets.sh
   Where {SKILL_DIR} is the absolute path to this skill (the directory containing SKILL.md).
   The script applies the canonical regex catalog from pass 6.10, plus ggshield/gitleaks
   if available on PATH. Output is JSON: {findings:[...], scanners:[...], errors:[...]}.
   Capture the raw JSON verbatim and include it as `secrets_prescan` in your return.
   Do NOT filter, paraphrase, or 'improve' the JSON — Phase C consumes it as the
   AUTHORITATIVE source for the Secrets Detection table and the F-grade gate.

Return as a structured list:
- BASE_BRANCH, BRANCH_NAME, MERGE_BASE
- DIFF_STAT (insertions/deletions)
- COMMIT_LOG
- File list with: path, category, test_status (for CODE files)
- Count of files per category
- secrets_prescan: {findings:[...], scanners:[...], errors:[...]}  ← raw JSON from step 8
")
```

Pass any `$ARGUMENTS` overrides (baseDir, fileExtensions, frameworkPatterns, etc.) to the agent.

**Why a deterministic script instead of LLM-simulated regex**: pass 6.10 listed regex patterns and Phase B sonnet agents were asked to "apply" them, but LLMs are not regex engines — substring-match shapes like `initialPassword: 'foo'` (where `password` appears as a suffix of `initialPassword`) are easy to miss. The script in `scripts/scan_secrets.py` runs real Python `re` against the unified diff, applies the exception list (env lookups, placeholders, `.env.example` files) deterministically, and integrates `ggshield`/`gitleaks` if installed. Phase C still merges in the per-file sonnet findings from pass 6.10 as supplemental, but the script's output is the authoritative gate.

The pre-scan exists because CI-side scanners like GitGuardian will block the push — we want to surface the same findings locally *before* the secret lands on a remote branch.

If CHANGED_FILES is empty, output: "No changes detected between this branch and `{BASE_BRANCH}`." and stop.

If more than 15 CODE files, prioritize by change size (diff stat lines). Note deprioritized files.

### Phase B: Per-File Analysis (sonnet agents, parallel)

For each CODE file (or group of 2-3 small files sharing imports), **spawn a sonnet agent** to analyze it. Launch all agents **in parallel**.

```
Agent(model: "sonnet", prompt: "
You are performing a code review analysis on a single file. Your job is to apply
detection passes and return structured findings — nothing else.

## Context
- Repository: {REPO}
- Branch: {BRANCH_NAME} → {BASE_BRANCH}
- Framework: {frameworkPatterns}
- File: {FILE_PATH} (category: {CATEGORY})
- Focus area: {FOCUS or 'full'}

## Instructions
1. Read the detection passes from: references/detection-passes.md
2. Read the git diff for this file: git diff {MERGE_BASE}...HEAD -- {FILE_PATH}
3. Read the current file content (full file for CODE, diff-only for UI_LIB)
4. Apply ALL applicable detection passes (or only the focused subset if a focus area was specified)
5. For UI_LIB files, only flag CRITICAL and HIGH issues
6. **Pass 6.10 (Hardcoded Secrets) is ALWAYS on** — apply it to this file regardless of its category (CODE / TESTS / CONFIG / UI_LIB / STYLES) and regardless of the focus area. A hardcoded password in a test file is still a leak; GitGuardian does not distinguish, and neither do we. Never whitelist a secret finding to reduce noise.

## Focus Area Mapping (if applicable)
- security → 6.2 Security + 6.6 TOCTOU + 6.8 Data Integrity + 6.10 Secrets
- performance → 6.3 Performance + 6.10 Secrets
- types → 6.4 Type Safety + 6.10 Secrets
- bugs → 6.1 Bug Detection + 6.6 TOCTOU + 6.10 Secrets
- tests → test quality + 6.10 Secrets
- docs → 6.5 Documentation Sync + 6.10 Secrets
- a11y → 6.7 Accessibility + 6.10 Secrets
- race-conditions → 6.6 TOCTOU + 6.10 Secrets
- secrets → 6.10 Secrets only

Note: pass 6.10 appears in every focus mapping — it is the one pass that is never optional. The user cannot afford to miss a leak just because they asked for a narrow review.

## Output Format
Return findings as a numbered list, one per issue:

N. [SEVERITY] {category} — {file}:{line} — {title}
   Description: {what the issue is, referencing actual code}
   Suggestion: {concrete fix direction}

If no issues found, return: 'No findings for {FILE_PATH}'

Important: ONLY reference line numbers you actually see in the diff or file content.
Do NOT invent findings — if the code is clean, say so.
Note any imports from other changed files for cross-reference by the main model.
")
```

**Grouping strategy**: Files that import from each other should be in the same agent when possible (max 3 files per agent). This helps catch intra-group issues without needing opus.

For **TOCTOU/race condition** analysis that spans multiple files (e.g., service reads from DB, controller calls service), the sonnet agent flags the single-file pattern and notes "cross-file verification needed". Opus handles the cross-file judgment in Phase C.

### Phase C: Cross-File Review & Final Report (main model — opus)

After all sonnet agents return, the main model:

1. **Collects all findings** from sonnet agents into a unified list
2. **Merges the Phase A secrets pre-scan with pass-6.10 findings from the per-file agents.**
   - The Phase A `secrets_prescan.findings` is the **authoritative** source — every entry is real (regex matched + exception filter applied) and goes directly into the Secrets Detection table.
   - Per-file sonnet pass-6.10 findings are **supplemental** — they may catch context-aware nuances the regex missed (e.g., a custom DSL where the keyword is non-standard). For each sonnet finding NOT already in `secrets_prescan` (dedup by `{file, line, kind}`), add it to the table only if:
     a) the snippet/description has a concrete literal credential (not a category like "potential leak"), AND
     b) it matches one of the pass 6.10 categories or is clearly equivalent.
     Otherwise drop it as low-signal LLM speculation.
   - Dedup remaining entries by `{file, line, kind}`; on collision, keep the higher severity and prefer `source=ggshield` > `gitleaks` > `regex` > `sonnet` for provenance.
3. **Cross-file analysis** — checks that only opus can do:
   - Race conditions spanning multiple files (e.g., check in controller, act in service)
   - Schema consistency across related endpoints
   - Import chain coherence (types match between producer and consumer)
   - If cross-file issues are found, add them to the findings list
4. **Severity recalibration** — review each finding's severity:
   - Sonnet may over-flag memoization issues (React.memo, useCallback) — downgrade per the rules in detection-passes.md
   - Ambiguous TOCTOU patterns in single-user contexts — downgrade to LOW
   - Patterns that are actually project conventions (check CLAUDE.md) — remove or downgrade
   - **Pass 6.10 (Secrets) findings are NEVER downgraded to MEDIUM/LOW and NEVER removed.** The only allowed recalibration is CRITICAL ↔ HIGH per the test-file nuance in detection-passes.md (inline test literals are HIGH; prod code is CRITICAL; env-var lookups are not flagged at all).
5. **Deduplication** — remove findings that overlap or repeat the same root cause (does not apply to pass 6.10 — each occurrence is reported, then aggregated if ≥3 in one file or ≥5 across PR).
6. **Test coverage summary** — compile from Phase A results
7. **Documentation sync check** — verify docs files in CHANGED_FILES per 6.5.2 rules
8. **Secrets gate** — if the merged Secrets Detection list has **≥1 entry from `secrets_prescan` OR ≥1 entry from sonnet that survived the supplemental filter in step 2**:
   - Set overall grade to **F** regardless of any other signal.
   - Prepend a BLOCKED banner to the report (see report template).
   - Add an entry under "Must Fix (CRITICAL)" per file with the remediation block from detection-passes.md pass 6.10.
   - If `secrets_prescan.errors` is non-empty (script crashed, ggshield timed out), also surface a warning to the user — the gate may have under-reported.
9. **Produce the final report** — read `references/report-template.md` and output the structured Markdown report with:
   - BLOCKED banner (only if step 8 triggered)
   - **Secrets Detection table** (always present; shows "Status: PASS" with 0 rows when clean)
   - Findings table (ordered: CRITICAL > HIGH > MEDIUM > LOW, grouped by file)
   - Zen Principles summary
   - Bug/Security/Performance/Types summary
   - Test coverage table
   - Documentation sync table
   - Overall grade (A-F per grading scale)
   - Recommended actions

### Special Cases

- **Zero findings**: Output a congratulatory report. Grade A. Still show header, test coverage, and grade.
- **Focus area specified**: Only the matching detection passes were applied by sonnet agents. Mark non-analyzed sections as "Not analyzed (focused review on {area})".
- **File path/glob specified**: Only matching files were analyzed. Report shows only those files.
- **UI_LIB files**: Sonnet agents only flagged CRITICAL/HIGH. Note "(UI_LIB — reduced rigor)" in findings.
- **More than 50 findings**: Show all CRITICAL/HIGH/MEDIUM first, then LOW up to 50 total. Add overflow count.

---

## Operating Principles

### Context Efficiency

- **Haiku handles git operations** — raw command output stays in haiku context, not opus
- **Sonnet handles file reading** — file content and diffs stay in sonnet context, not opus
- **Opus sees only findings** — structured summaries, not raw code
- **Prioritize by change size** — files with more changes get more thorough analysis
- **Cap analysis scope** — maximum 15 full file reads across all sonnet agents
- **Skip routing for small PRs** — ≤3 CODE files → everything in main model

### Analysis Integrity

- **NEVER modify files** — this is strictly read-only analysis
- **NEVER hallucinate line numbers** — only reference lines actually read from the diff or file
- **NEVER invent findings** — if the code is clean, say so. A clean report is a valid outcome.
- **Be fair to generated code** — UI_LIB files get reduced scrutiny (except pass 6.10, which always runs)
- **Never whitelist a secret finding to reduce noise** — treat test-file passwords the same as production ones; GitGuardian does. The cost of a false-positive re-read is far less than the cost of a leaked credential.
- **Acknowledge context limits** — if a sonnet agent couldn't fully analyze a file, note it
- **Ground findings in evidence** — quote the problematic code snippet when helpful (for secrets, mask the value with `***` — do not echo the literal back in the report, as the report itself is copied into chat history)
