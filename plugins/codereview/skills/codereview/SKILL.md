---
name: codereview
metadata:
  version: 1.14.0
description: "Pre-PR review with severity grading and tiered model routing. Detects TOCTOU races, accessibility gaps, hardcoded secrets, docs/OpenAPI drift, contract drift in tests, and dead code via a parallel whole-repo sweep (unused exports, orphaned files, unreachable code). Report carries an Overall Grade table + Recommended Actions. Stack-agnostic, TypeScript/React defaults. Triggers — code review, pre-PR, secrets scan, accessibility audit, contract drift, dead code, code health."
---

## User Input

```text
$ARGUMENTS
```

Read the user input before proceeding (if not empty). Valid inputs:

- Empty: full review of all changed files
- Focus area: `security`, `performance`, `types`, `bugs`, `tests`, `docs`, `a11y`, `race-conditions`, `dead-code`
- File path or glob: review only matching changed files
- Key-value overrides: `baseDir=app/ fileExtensions=ts,js` (see `references/configuration.md`)

Defaults are `baseDir=src/`, `fileExtensions=ts,tsx`, `frameworkPatterns=react`, tests `**/*.{test,spec}.{ts,tsx}` and `**/test/**`, UI_LIB `src/components/ui/**`, `prisma/**`, `**/generated/**`, CONFIG `*.config.*`, `tsconfig*`, `.env*`, `package.json`. Read `references/configuration.md` only when `$ARGUMENTS` carries `key=value` overrides or the stack is not TypeScript/React — it holds the override syntax and the presets (Python, Vue, Node, .NET).

## Goal

Perform a comprehensive, automated code review of all changes in the current branch compared to the base branch. Produce a structured Markdown report with severity-rated findings, test coverage assessment, and a final grade.

This skill is **stack-agnostic**. Defaults target TypeScript/React but all values are configurable. Set `frameworkPatterns=dotnet` for C#/.NET projects.

---

## Model Routing Strategy

This skill delegates the data-heavy per-file phase to cheaper agents and keeps judgment and the final report in the main model — whichever model the session is running.

| Phase | Task | Runs in | Why |
|-------|------|---------|-----|
| A | Git context, file classification, test mapping, secrets pre-scan | **inline** (main session) | Fixed commands with one right answer — nothing to delegate |
| B | Per-file analysis (detection passes) | **sonnet** agents, in parallel | Pattern matching on code — intelligence without deep reasoning |
| C | Cross-file review, severity calibration, report | **Main model** | Judgment calls, cross-references, coherent report |

**Threshold**: If the branch has ≤3 CODE files, skip model routing — run Phase B inline too. The agent overhead isn't worth it for small reviews.

**The `model` field on every Agent call is what makes the routing real.** An Agent call without `model` inherits the main model, and the same per-file analysis is then billed at the main model's rates — 2.5× to 5× Sonnet's — for the same findings. Pass `model: "sonnet"` on every Phase B and B2 call, and read the model back in the report's Cost footprint line.

---

## Operating Constraints

**Read-only.** This skill identifies issues and suggests fixes in the report; it does not apply them. Don't modify, create, or delete files, and don't run destructive commands — everything it runs (git, grep, the secrets script, dead-code tooling) is a pure read. The only output is the structured report in the conversation.

## Error Handling

- **Git command failures**: include the exact failing command and stop immediately.
- **File read failures**: skip the file and record it as `Could not analyze: {filename} ({reason})`.
- **Context / token exhaustion**: finish analyzing files already processed, note truncation, proceed to report.
- **Timeout**: prioritize CRITICAL/HIGH checks on remaining files, skip MEDIUM/LOW.

Regardless of failures, always produce a final report listing all files analyzed and all failures.

---

## Execution Phases

### Phase A: Git Context, File Classification & Secrets Pre-Scan (inline, main session)

Every step here is mechanical — a fixed command with one right answer — so it runs inline in the main session, not in an agent. An agent in the middle only adds variation, latency and the chance of a silently dropped field, and the one field that must never be dropped is the secrets pre-scan: without its JSON the F-grade gate goes blind. The outputs are small (file names, stats, a one-line log), so keeping them in the main context costs little.

Apply any `$ARGUMENTS` overrides (baseDir, fileExtensions, frameworkPatterns, etc.) before classifying, then run the commands as Bash calls, in parallel where independent, and keep the raw outputs. Three Bash turns cover steps 1–8: (1) steps 1–3, with base-branch detection as a single fallback chain in one command; (2) step 4; (3) steps 5–8 as parallel calls in one message. Every extra orchestrator turn is a main-model round-trip over the whole session context, so batch what is independent instead of issuing one call per step:

1. Verify git repo:  `git rev-parse --is-inside-work-tree`
2. Detect base branch (try: origin HEAD symbolic-ref, then main, then master)
3. Current branch: `git rev-parse --abbrev-ref HEAD`
4. Merge base:  `git merge-base {BASE_BRANCH} HEAD`
5. Changed files: `git diff {MERGE_BASE}...HEAD --name-only`
6. Diff stats:  `git diff {MERGE_BASE}...HEAD --stat`
7. Commit log:  `git log {MERGE_BASE}..HEAD --oneline --no-decorate`
8. Secrets pre-scan — runs on every review, whatever its size or focus:
   `git diff {MERGE_BASE}...HEAD --unified=0 | bash {SKILL_DIR}/scripts/scan_secrets.sh`
   where `{SKILL_DIR}` is the absolute path of the directory containing this SKILL.md. The script applies the regex catalog from pass 6.10, plus ggshield/gitleaks when they are on PATH, and prints JSON: `{findings:[...], scanners:[...], errors:[...]}`. Keep that JSON verbatim as `SECRETS_PRESCAN` — Phase C consumes it as the authoritative source for the Secrets Detection table and the F-grade gate. If the script crashes or prints anything other than JSON, the scan did not run: warn the user and re-run it. An absent payload is never "scan returned clean".

Classify each changed file:
- EXCLUDED: lock files, node_modules, dist, build, .next, min files, binaries, .claude/
- CODE: source files matching {fileExtensions} in {baseDir}, excluding tests and generated
- UI_LIB: files in {generatedDirs}
- TESTS: files matching {testFilePatterns}
- CONFIG: files matching {configFilePatterns}
- DOCS: *.md, *.txt
- STYLES: CSS/SCSS/LESS

For each CODE file, check test coverage by probing candidate test file paths — same dir (`{Base}.test.{ext}`, `{Base}.spec.{ext}`), a `__tests__` sibling, then the project test root — and record it as WITH_TESTS / STALE_TESTS / NO_TESTS. Probe all CODE files in one shell loop (one Bash call that prints `path|status` per file), not one call per file.

Phase A hands Phases B and C: BASE_BRANCH, BRANCH_NAME, MERGE_BASE, DIFF_STAT, COMMIT_LOG, the FILES list (path, category, test_status), COUNTS per category, and SECRETS_PRESCAN.

**Why the secrets scan is a script**: LLMs are not regex engines — substring-match shapes like `initialPassword: 'foo'` (where `password` appears as a suffix of `initialPassword`) are easy to miss when a model applies a pattern by eye. `scripts/scan_secrets.py` runs real Python `re` against the unified diff, applies the exception list (env lookups, placeholders, `.env.example` files) deterministically, and integrates `ggshield`/`gitleaks` if installed. Phase C still merges the per-file agents' pass-6.10 findings as supplemental, but the script's output is the authoritative gate.

The pre-scan exists because CI-side scanners like GitGuardian will block the push — we want to surface the same findings locally *before* the secret lands on a remote branch.

If CHANGED_FILES is empty, output: "No changes detected between this branch and `{BASE_BRANCH}`." and stop.

If more than 15 CODE files, prioritize by change size (diff stat lines). Note deprioritized files.

### Phase B: Per-File Analysis (sonnet agents, parallel)

For each CODE file (or group of 2-3 small files sharing imports), **spawn a sonnet agent** to analyze it. Launch all agents **in parallel**, in one message.

The agent's instructions live in `{SKILL_DIR}/references/per-file-agent.md` and the agent reads them itself, so every agent gets the same contract and the orchestrator emits only the launch prompt below — placeholders filled, nothing added (no extra themes, no framing, no reproduction requests: a finding that needs reproducing comes back marked as such and is reproduced after the report), nothing removed. `model: "sonnet"` goes on every call.

```
Agent(model: "sonnet", prompt: "
Start with ONE batch of parallel tool calls: Read {SKILL_DIR}/references/per-file-agent.md,
Read {SKILL_DIR}/references/detection-passes.md, run `git diff {MERGE_BASE}...HEAD -- {FILE_PATH}`,
and Read {FILE_PATH}. Then follow per-file-agent.md exactly — it carries your instructions,
scope and output format.

- Repository: {REPO}
- Branch: {BRANCH_NAME} → {BASE_BRANCH}
- Merge base: {MERGE_BASE}
- Framework: {frameworkPatterns}
- File: {FILE_PATH} (category: {CATEGORY})   — one line per file in the group
- Focus area: {FOCUS or 'full'}
- Skill dir: {SKILL_DIR}
")
```

The agent returns a numbered findings list (`N. [SEVERITY] {category} — {file}:{line} — {title}`, with Description and Suggestion), or `No findings for {FILE_PATH}`, and ends with `Tool calls: … | Files read in full: …` and `END_OF_FILE_REVIEW`.

**Grouping strategy**: Files that import from each other should be in the same agent when possible (max 3 files per agent). This helps catch intra-group issues without needing the main model.

For **TOCTOU/race condition** analysis that spans multiple files (e.g., service reads from DB, controller calls service), the sonnet agent flags the single-file pattern and notes "cross-file verification needed". Phase C handles the cross-file judgment.

### Phase B2: Dead Code Sweep (sonnet agent, parallel)

Spawn **one dedicated agent** for pass 6.9 (Dead Code & Unused Symbols), launched **in the same parallel batch** as the Phase B per-file agents. It is a separate agent — not one of the per-file ones — because dead-code detection is a **whole-repo reference-graph** question: a per-file agent sees only its one file and cannot tell whether an exported symbol is referenced anywhere else. This agent has the changed-file list, the diff, and grep/tooling access to the entire repo.

**When to run it:**
- **Full review** (empty `$ARGUMENTS`) → run it.
- **Bucket B is opt-in.** The repo-wide pass over pre-existing dead code (tooling such as `knip`/`ts-prune`/`vulture`, capped) runs only on focus `dead-code` or with `sweep=full` in `$ARGUMENTS`; every other run gets Bucket A alone — what this PR introduced or orphaned. Bucket B was the expensive part of the sweep and none of it belongs to the PR under review; the report says in one line how to get it.
- Focus `dead-code` → run it (and skip the per-file passes — this is the only analysis).
- Focus `bugs` → run it (dead code often masks or accompanies bugs).
- Narrow focuses (`security`, `a11y`, `types`, `performance`, `docs`, `tests`, `race-conditions`) → **skip it.** Unlike pass 6.10 (secrets), dead code is hygiene, not a gate — it is not always-on, and surfacing it during a focused security review is noise.
- **≤3 CODE files** (model routing skipped) → run the sweep **inline in the main model** instead of spawning an agent.

> **Output discipline** — the orchestrator sees only the agent's **final assistant message**; its grep/tool outputs are not propagated. The final message is the return template from `sweep-agent.md`, filled in — not "done" or "scan complete".

Its instructions live in `{SKILL_DIR}/references/sweep-agent.md` (the two buckets, the guardrails, the return template ending in `END_OF_DEAD_CODE_SWEEP`); the launch prompt is the block below, placeholders filled.

```
Agent(model: "sonnet", prompt: "
Start with ONE batch of parallel tool calls: Read {SKILL_DIR}/references/sweep-agent.md,
Read {SKILL_DIR}/references/detection-passes.md (pass 6.9), and run `git diff {MERGE_BASE}...HEAD`.
Then follow sweep-agent.md exactly — it carries the two buckets, the guardrails and the
return template.

- Repository root: {REPO}
- Branch: {BRANCH_NAME} → {BASE_BRANCH}
- Merge base: {MERGE_BASE}
- Framework: {frameworkPatterns}
- Changed CODE/CONFIG files: {LIST_OF_CHANGED_FILES}
- Focus area: {FOCUS or 'full'}
- Sweep: {full | pr}   — `full` only when `$ARGUMENTS` carries `sweep=full`
- Skill dir: {SKILL_DIR}
")
```

If the agent under-reports (response missing `END_OF_DEAD_CODE_SWEEP`, or a bare status sentence), the orchestrator re-runs the grep deepsearch inline in the main session for the changed files — but unlike the secrets gate, an absent dead-code result is **non-blocking**: note "dead-code sweep incomplete" in the report and proceed.

### Phase C: Cross-File Review & Final Report (main model)

After all sonnet agents return, the main model:

1. **Collects all findings** from sonnet agents into a unified list. A per-file message without its `END_OF_FILE_REVIEW` line is partial: keep what it reports and mark the file `partially analyzed` in the report
2. **Merges the Phase A secrets pre-scan with pass-6.10 findings from the per-file agents.**
   - The Phase A `secrets_prescan.findings` is the **authoritative** source — every entry is real (regex matched + exception filter applied) and goes directly into the Secrets Detection table.
   - Per-file sonnet pass-6.10 findings are **supplemental** — they may catch context-aware nuances the regex missed (e.g., a custom DSL where the keyword is non-standard). For each sonnet finding NOT already in `secrets_prescan` (dedup by `{file, line, kind}`), add it to the table only if:
     a) the snippet/description has a concrete literal credential (not a category like "potential leak"), AND
     b) it matches one of the pass 6.10 categories or is clearly equivalent.
     Otherwise drop it as low-signal LLM speculation.
   - Dedup remaining entries by `{file, line, kind}`; on collision, keep the higher severity and prefer `source=ggshield` > `gitleaks` > `regex` > `sonnet` for provenance.
3. **Cross-file analysis** — checks that need the whole picture, so only the main model can do them:
   - Race conditions spanning multiple files (e.g., check in controller, act in service)
   - Schema consistency across related endpoints
   - Import chain coherence (types match between producer and consumer)
   - If cross-file issues are found, add them to the findings list
4. **Severity recalibration** — review each finding's severity:
   - Per-file agents may over-flag memoization issues (React.memo, useCallback) — downgrade per the rules in detection-passes.md
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
9. **Merge dead-code findings** — fold the Phase B2 Dead Code Sweep output (Bucket A = introduced/orphaned by this PR; Bucket B = pre-existing, capped — present only on `dead-code` focus or `sweep=full`) into the report. Calibration rules:
   - Dead code is **MEDIUM/LOW only** — never promote to HIGH/CRITICAL, and it **never** affects the secrets gate or forces grade F.
   - Honor the agent's per-finding **Confidence**: drop or footnote Low-confidence items that the guardrails couldn't clear (e.g. an unreferenced library export — external consumers are invisible to repo grep).
   - Keep Bucket B a **capped summary** labeled "pre-existing (not introduced by this PR)" so it doesn't drown the PR-relevant Bucket A findings. When the sweep reports `BUCKET_B: skipped`, render the one-line note from the template instead of a table.
   - If the sweep was skipped (narrow focus) or under-reported, note that in the Dead Code section rather than omitting it.
10. **Produce the final report** — read `references/report-template.md` and output the structured Markdown report with:
   - BLOCKED banner (only if step 8 triggered)
   - **Secrets Detection table** (always present; shows "Status: PASS" with 0 rows when clean)
   - Findings table (ordered: CRITICAL > HIGH > MEDIUM > LOW, grouped by file)
   - Zen Principles summary
   - Bug/Security/Performance/Types summary
   - Test coverage table
   - Documentation sync table
   - **🧹 Dead Code & Cleanup section** (when the sweep ran — Bucket A primary, Bucket B as a capped pre-existing summary when it was on; dead-code findings also feed Recommended Actions → Consider Fixing and the Code Quality grade rationale)
   - **Overall Grade table** (always present — see below)
   - Recommended actions (always present, even when empty — show "_None._" under each bucket)
   - **Cost footprint** line (always present, the last line of the report — the shape is in the template)

**The report ends with the Overall Grade table, the Recommended Actions block and the one-line Cost footprint, in every run.** They are the summary the human reads first to triage; a report without them cannot be acted on, however good the findings above it are. Render both in full even when there is little to say: with zero findings, every row gets grade `A` and rationale `clean` or `—`; in a focus-area run every row is still present, and the non-analyzed ones get grade `—` with rationale `Not analyzed (focused review on {area})`; when the context budget is tight, keep the table and use terse one-word rationales (`clean`, `3 HIGH`, `n/a`) rather than collapsing it into prose. `references/report-template.md` carries the exact shape of both sections, and of the `### 🛑 Secrets Detection` section from step 8.

### Special Cases

- **Zero findings**: Output a congratulatory report. Grade A. Still show header, test coverage, and grade.
- **Focus area specified**: Only the matching detection passes were applied by sonnet agents. Mark non-analyzed sections as "Not analyzed (focused review on {area})".
- **File path/glob specified**: Only matching files were analyzed. Report shows only those files.
- **UI_LIB files**: Sonnet agents only flagged CRITICAL/HIGH. Note "(UI_LIB — reduced rigor)" in findings.
- **More than 50 findings**: Show all CRITICAL/HIGH/MEDIUM first, then LOW up to 50 total. Add overflow count.

---

## Operating Principles

### Context Efficiency

- **Phase A runs inline** — its outputs are small (file names, stats, a one-line log) and Phase C needs them anyway
- **Per-file agents handle file reading** — file content and diffs stay in the agents' context, not the main model's
- **The main model sees only findings** — structured summaries, not raw code
- **Prioritize by change size** — files with more changes get more thorough analysis
- **Cap analysis scope** — maximum 15 full file reads across all sonnet agents
- **Skip routing for small PRs** — ≤3 CODE files → everything in main model
- **Measure, don't guess** — the report's last line says how many agents ran, on which model, how many tool calls each made and whether the sweep ran. Compare it with `/cost` (or the harness's per-session cost log) before and after any change to this skill; a change without that pair of numbers is a guess

### Analysis Integrity

- **Read-only** — the review changes nothing; it reports
- **Line numbers come from the diff or file actually read** — a line the reader can't find discredits the whole report
- **A clean report is a valid outcome** — if the code is clean, say so rather than inventing findings
- **Be fair to generated code** — UI_LIB files get reduced scrutiny (except pass 6.10, which always runs)
- **Never whitelist a secret finding to reduce noise** — treat test-file passwords the same as production ones; GitGuardian does. The cost of a false-positive re-read is far less than the cost of a leaked credential.
- **Acknowledge context limits** — if a sonnet agent couldn't fully analyze a file, note it
- **Ground findings in evidence** — quote the problematic code snippet when helpful (for secrets, mask the value with `***` — do not echo the literal back in the report, as the report itself is copied into chat history)
