---
name: codereview
metadata:
  version: 1.11.0
description: Pre-PR review with severity grading and model routing (haiku/sonnet/opus). Detects TOCTOU races, accessibility gaps, hardcoded secrets (GitGuardian-equivalent regex), docs/OpenAPI sync, contract drift in tests (exported const grew without its assertion updated), and **dead code** via a parallel whole-repo sweep — unused exports, orphaned files, unreachable code (knip/ts-prune/vulture or grep) — with cleanup recs. Final report always includes the Overall Grade table + Recommended Actions. Stack-agnostic with TypeScript/React defaults, dotnet preset. Triggers — code review, pre-PR, secrets scan, accessibility audit, contract drift, dead code, unused exports, cleanup, code health.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). Valid inputs:

- Empty: full review of all changed files
- Focus area: `security`, `performance`, `types`, `bugs`, `tests`, `docs`, `a11y`, `race-conditions`, `dead-code`
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

**Spawn a haiku agent** to gather all git context, classify files, AND run the deterministic secrets pre-scan.

> **Output discipline — read this carefully before writing the prompt.**
> The orchestrator only sees the agent's **final assistant message**. Tool-call
> outputs (bash, git, scripts) are visible to the agent **but not propagated to
> the caller**. If the agent ends with "done", "results above", or any other
> meta-statement instead of the raw data, the orchestrator gets nothing — and
> the secrets gate silently degrades because `secrets_prescan` never arrives.
>
> This has happened in practice with shorter / busier agent runs: the agent
> performs all 8 steps via tool calls, but the final message is a status
> summary instead of the data. To prevent that, the prompt below uses a
> **literal return template** the agent fills in, and pairs it with an
> orchestrator-side fallback (below the prompt).

```text
Agent(model: "haiku", prompt: "
Run these git commands and return the results VERBATIM in the template at
the bottom. Tool outputs you produce are NOT visible to the caller — only
your final assistant message is. Therefore your final message MUST contain
the raw command outputs filled into the template. Do NOT summarize. Do NOT
say 'done' or 'results above'. Paste the actual bytes.

1. Verify git repo:  git rev-parse --is-inside-work-tree
2. Detect base branch (try: origin HEAD symbolic-ref, then main, then master)
3. Get current branch: git rev-parse --abbrev-ref HEAD
4. Find merge base:  git merge-base {BASE_BRANCH} HEAD
5. List changed files: git diff {MERGE_BASE}...HEAD --name-only
6. Diff stats:       git diff {MERGE_BASE}...HEAD --stat
7. Commit log:       git log {MERGE_BASE}..HEAD --oneline --no-decorate

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
   Capture the raw JSON verbatim under SECRETS_PRESCAN below.
   Do NOT filter, paraphrase, or 'improve' the JSON — Phase C consumes it as the
   AUTHORITATIVE source for the Secrets Detection table and the F-grade gate.

## RETURN TEMPLATE — paste your final message in this exact shape

BASE_BRANCH: <name>
BRANCH_NAME: <name>
MERGE_BASE:  <sha>

DIFF_STAT:
<paste full `git diff --stat` output here>

COMMIT_LOG:
<paste full `git log ... --oneline` output here>

FILES:
- path: <relative path>
  category: CODE | UI_LIB | TESTS | CONFIG | DOCS | STYLES | EXCLUDED
  test_status: WITH_TESTS | STALE_TESTS | NO_TESTS    (only for CODE)
- ...

COUNTS:
  CODE: N
  UI_LIB: N
  TESTS: N
  CONFIG: N
  DOCS: N
  STYLES: N
  EXCLUDED: N

SECRETS_PRESCAN:
<paste the raw JSON output of scan_secrets.sh here, verbatim, including the
braces; if the script crashed, paste {\"findings\":[],\"scanners\":[],\"errors\":[\"<message>\"]}>

END_OF_PHASE_A_REPORT
")
```

Pass any `$ARGUMENTS` overrides (baseDir, fileExtensions, frameworkPatterns, etc.) to the agent.

**Orchestrator-side fallback (MANDATORY):** Before consuming the agent's
response, validate that it actually contains the data. If **any** of the
following is true, the agent under-reported and the orchestrator MUST
re-execute the data-gathering steps itself in the main session:

- The response is shorter than ~500 characters.
- The response does not contain the literal string `SECRETS_PRESCAN:`.
- The response does not contain `END_OF_PHASE_A_REPORT`.
- The response is a status sentence ("done", "complete", "results above",
  "structured results returned", etc.) without the template fields.

In any of those cases, run the eight steps in the main session as Bash
calls (in parallel where independent), capture the outputs directly, and
pipe the diff through `scan_secrets.sh` yourself. **Never** skip the
secrets pre-scan because the agent forgot to include it — the F-grade
gate depends on a real JSON payload existing, and an absent payload must
be treated as "scan did not run" (warn the user and re-run), not as
"scan returned clean".

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

### Phase B2: Dead Code Sweep (sonnet agent, parallel)

Spawn **one dedicated agent** for pass 6.9 (Dead Code & Unused Symbols), launched **in the same parallel batch** as the Phase B per-file agents. It is a separate agent — not one of the per-file ones — because dead-code detection is a **whole-repo reference-graph** question: a per-file agent sees only its one file and cannot tell whether an exported symbol is referenced anywhere else. This agent has the changed-file list, the diff, and grep/tooling access to the entire repo.

**When to run it:**
- **Full review** (empty `$ARGUMENTS`) → run it.
- Focus `dead-code` → run it (and skip the per-file passes — this is the only analysis).
- Focus `bugs` → run it (dead code often masks or accompanies bugs).
- Narrow focuses (`security`, `a11y`, `types`, `performance`, `docs`, `tests`, `race-conditions`) → **skip it.** Unlike pass 6.10 (secrets), dead code is hygiene, not a gate — it is not always-on, and surfacing it during a focused security review is noise.
- **≤3 CODE files** (model routing skipped) → run the sweep **inline in the main model** instead of spawning an agent.

> **Output discipline** — same rule as Phase A/B: the orchestrator sees only the agent's **final assistant message**. Its grep/tool outputs are not propagated. The final message MUST contain the structured findings filled into the template below — not "done" or "scan complete".

```
Agent(model: "sonnet", prompt: "
You are performing a whole-repo DEAD CODE sweep for a pre-PR review. You RECOMMEND
cleanup only — never modify or delete anything. All commands you run must be read-only.

## Context
- Repository root: {REPO}
- Branch: {BRANCH_NAME} → {BASE_BRANCH}
- Merge base: {MERGE_BASE}
- Framework: {frameworkPatterns}
- Changed CODE/CONFIG files: {LIST_OF_CHANGED_FILES}

## Instructions
1. Read pass 6.9 from: references/detection-passes.md — apply its detection categories,
   deepsearch method, opportunistic tooling, and (critically) the false-positive guardrails.
2. Get the diff for context: git diff {MERGE_BASE}...HEAD
3. Build two buckets:
   - BUCKET A (introduced/orphaned by THIS PR): symbols/files the diff ADDED that nothing
     references yet, and symbols/files the diff ORPHANED (last caller/import removed). For
     each candidate, grep the WHOLE repo (excluding the defining file) for references —
     including non-code files (HTML/JSX templates, JSON/YAML config, SQL, route manifests,
     DI registration, .env). Zero refs + not public-API + not framework/dynamically-wired
     → flag.
   - BUCKET B (pre-existing, opportunistic): if any dead-code tooling is runnable
     (npx knip / npx ts-prune / npx depcheck / vulture / ruff / dotnet build warnings /
     deadcode / staticcheck), run it READ-ONLY and collect repo-wide dead code NOT touched
     by this PR. CAP this bucket at ~10 highest-impact entries + a total count. If no
     tooling is available, say so and leave Bucket B with only what the grep deepsearch
     surfaced.
4. Apply the guardrails before flagging anything: public API surface, framework/dynamic
   wiring (routes, DI, decorators, reflection, dynamic import, string-keyed registries,
   ORM entities, serialization, test discovery), references in non-code files, barrels/
   re-exports, test-only utilities, conditional compilation, just-added scaffolding.
   Each finding gets a Confidence (High/Medium/Low) reflecting how many guardrails it cleared.
5. Severity: MEDIUM only for diff-orphaned items or whole orphaned files; LOW for everything
   else. NEVER CRITICAL/HIGH. This pass never blocks the PR.

## RETURN TEMPLATE — your final message must be in this exact shape

TOOLING_AVAILABLE: <comma-separated tools you ran, or 'none — grep deepsearch only'>

BUCKET_A (introduced/orphaned by this PR):
- symbol_or_file: <name>
  kind: unused-export | orphaned-file | unreachable | unused-import | unused-local | unused-dependency | diff-orphaned
  location: <path>:<line>
  severity: MEDIUM | LOW
  confidence: High | Medium | Low
  recommendation: <one-line cleanup>
- ... (or 'none')

BUCKET_B (pre-existing, capped):
- symbol_or_file: <name>
  kind: <...>
  location: <path>:<line>
  severity: LOW
  confidence: <...>
  recommendation: <one-line cleanup>
- ... (or 'none')
TOTAL_PREEXISTING: <N>   (full count before the cap, if a tool reported more)

END_OF_DEAD_CODE_SWEEP
")
```

If the agent under-reports (response missing `END_OF_DEAD_CODE_SWEEP`, or a bare status sentence), the orchestrator re-runs the grep deepsearch inline in the main session for the changed files — but unlike the secrets gate, an absent dead-code result is **non-blocking**: note "dead-code sweep incomplete" in the report and proceed.

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
9. **Merge dead-code findings** — fold the Phase B2 Dead Code Sweep output (Bucket A = introduced/orphaned by this PR; Bucket B = pre-existing, capped) into the report. Calibration rules:
   - Dead code is **MEDIUM/LOW only** — never promote to HIGH/CRITICAL, and it **never** affects the secrets gate or forces grade F.
   - Honor the agent's per-finding **Confidence**: drop or footnote Low-confidence items that the guardrails couldn't clear (e.g. an unreferenced library export — external consumers are invisible to repo grep).
   - Keep Bucket B a **capped summary** labeled "pre-existing (not introduced by this PR)" so it doesn't drown the PR-relevant Bucket A findings.
   - If the sweep was skipped (narrow focus) or under-reported, note that in the Dead Code section rather than omitting it.
10. **Produce the final report** — read `references/report-template.md` and output the structured Markdown report with:
   - BLOCKED banner (only if step 8 triggered)
   - **Secrets Detection table** (always present; shows "Status: PASS" with 0 rows when clean)
   - Findings table (ordered: CRITICAL > HIGH > MEDIUM > LOW, grouped by file)
   - Zen Principles summary
   - Bug/Security/Performance/Types summary
   - Test coverage table
   - Documentation sync table
   - **🧹 Dead Code & Cleanup section** (when the sweep ran — Bucket A primary, Bucket B as a capped pre-existing summary; dead-code findings also feed Recommended Actions → Consider Fixing and the Code Quality grade rationale)
   - **Overall Grade table** (ALWAYS present; see "Mandatory final sections" below)
   - Recommended actions (ALWAYS present, even when empty — show "_None._" under each bucket)

**Mandatory final sections — must NEVER be omitted, truncated, or replaced by prose:**

The report MUST end with the **Overall Grade table** followed by the **Recommended Actions** block. These two sections are the user-facing summary — without them, the rest of the report is unactionable. Common failure modes to defend against:

1. **Token pressure**: when context is tight, the model may "summarize in prose" instead of rendering the full grade table. Forbidden — even under tight context, emit the table with terse one-word rationales (`"clean"`, `"3 HIGH"`, `"n/a"`).
2. **Zero-findings happy path**: when no findings exist, the model may skip straight to "looks good, grade A" without the table. Forbidden — render every row, fill grade column with `A` and rationale `—` or `clean`.
3. **Focus-area run**: when `$ARGUMENTS` specified a focus area, the model may render only the focused row. Forbidden — render every row; non-analyzed rows get grade `—` with rationale `Not analyzed (focused review on {area})`.
4. **Long-running review with many findings**: when the Findings table is large, the model may stop after listing findings. Forbidden — the grade table is the entry point the human reads first; without it the report cannot be triaged.

Before finishing the response, self-check that the response contains both `### Overall Grade` and `### Recommended Actions` headers exactly once each. If either is missing, append it before returning. Same self-check applies to the `### 🛑 Secrets Detection` section already covered in step 8.

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
