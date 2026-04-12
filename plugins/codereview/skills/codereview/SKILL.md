---
name: codereview
metadata:
  version: 1.6.0
description: >
  Automated pre-PR code review. Diffs current branch against main, analyzes all
  changed files, and produces a structured report with severity-rated findings,
  test coverage assessment, documentation sync verification, and a final grade.
  Checks docstring coverage, OpenAPI/README/rules sync, race conditions (TOCTOU),
  accessibility, data integrity, and code quality. Uses model routing to optimize
  token usage: lightweight models for git context and file reading, full-power
  model for cross-file analysis and final report.
  Use this skill whenever the user asks for code review, pre-PR review, code
  analysis, quality check, documentation check, security review, accessibility
  audit, or wants to review changes before merging — even if they don't say
  "codereview" explicitly.
  Triggers: "code review", "pre-PR review", "review my code", "quality check",
  "review changes", "codereview", "check my code", "analyze code", "PR review",
  "check docs", "documentation review", "security review", "accessibility check",
  "race condition", "toctou"
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

### Phase A: Git Context & File Classification (haiku agent)

**Spawn a haiku agent** to gather all git context and classify files. The agent runs these commands and returns structured results.

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

Return as a structured list:
- BASE_BRANCH, BRANCH_NAME, MERGE_BASE
- DIFF_STAT (insertions/deletions)
- COMMIT_LOG
- File list with: path, category, test_status (for CODE files)
- Count of files per category
")
```

Pass any `$ARGUMENTS` overrides (baseDir, fileExtensions, frameworkPatterns, etc.) to the agent.

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

## Focus Area Mapping (if applicable)
- security → 6.2 Security + 6.6 TOCTOU + 6.8 Data Integrity
- performance → 6.3 Performance
- types → 6.4 Type Safety
- bugs → 6.1 Bug Detection + 6.6 TOCTOU
- tests → test quality only
- docs → 6.5 Documentation Sync
- a11y → 6.7 Accessibility
- race-conditions → 6.6 TOCTOU only

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
2. **Cross-file analysis** — checks that only opus can do:
   - Race conditions spanning multiple files (e.g., check in controller, act in service)
   - Schema consistency across related endpoints
   - Import chain coherence (types match between producer and consumer)
   - If cross-file issues are found, add them to the findings list
3. **Severity recalibration** — review each finding's severity:
   - Sonnet may over-flag memoization issues (React.memo, useCallback) — downgrade per the rules in detection-passes.md
   - Ambiguous TOCTOU patterns in single-user contexts — downgrade to LOW
   - Patterns that are actually project conventions (check CLAUDE.md) — remove or downgrade
4. **Deduplication** — remove findings that overlap or repeat the same root cause
5. **Test coverage summary** — compile from Phase A results
6. **Documentation sync check** — verify docs files in CHANGED_FILES per 6.5.2 rules
7. **Produce the final report** — read `references/report-template.md` and output the structured Markdown report with:
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
- **Be fair to generated code** — UI_LIB files get reduced scrutiny
- **Acknowledge context limits** — if a sonnet agent couldn't fully analyze a file, note it
- **Ground findings in evidence** — quote the problematic code snippet when helpful
