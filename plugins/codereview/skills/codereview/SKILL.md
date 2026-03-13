---
name: codereview
metadata:
  version: 1.0.0
description: >
  Automated pre-PR code review. Diffs current branch against main, analyzes all
  changed files, and produces a structured report with severity-rated findings,
  test coverage assessment, and a final grade. Use this skill whenever the user
  asks for code review, pre-PR review, code analysis, quality check, or wants
  to review changes before merging — even if they don't say "codereview" explicitly.
  Triggers: "code review", "pre-PR review", "review my code", "quality check",
  "review changes", "codereview", "check my code", "analyze code", "PR review"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). Valid inputs:

- Empty: full review of all changed files
- Focus area: `seguranca`, `performance`, `types`, `bugs`, `testes`
- File path or glob: review only matching changed files (e.g. `src/components/Quote*`)
- Key-value overrides: `baseDir=app/ fileExtensions=ts,js uiLibReducedRigor=true` (see `references/configuration.md`)

Read `references/configuration.md` for default values and override syntax.

## Goal

Perform a comprehensive, automated code review of all changes in the current branch compared to the base branch. Produce a structured Markdown report with severity-rated findings, test coverage assessment, and a final grade. This replaces manual pre-PR review.

This skill is **stack-agnostic** — defaults target TypeScript/React but all values are configurable.

---

## Operating Constraints

**STRICTLY READ-ONLY**: Do **not** modify, create, or delete any files. Do **not** run destructive commands. Do **not** run formatters, linters, or fixers. Output ONLY a structured analysis report in the conversation.

**No Code Rewrites**: This skill identifies issues and suggests fixes in the report — it does NOT apply them.

## Error Handling

- **Git command failures**: include the exact failing git command in the error message and stop immediately (do not continue to the next step).
- **File read failures**: skip the file and record it as `Could not analyze: {filename} ({reason})` in the final report.
- **Git diff / merge-base / binary file issues**: flag the affected file as `unanalyzable` and continue with the remaining files.
- **Context / memory / token exhaustion**: finish analyzing files already processed, then record `Analysis incomplete due to context limits. {n} files not analyzed.` and proceed to the final report.
- **Timeout**: if analysis is taking too long, prioritize CRITICO/ALTO checks on remaining files, skip MEDIO/BAIXO, and note the truncation in the report.
- **Parsing errors** (malformed source, non-UTF-8 content, etc.): flag the file as `unanalyzable` and continue.

Regardless of which failures occur, always produce a final report that lists:

1. All files successfully analyzed (with their findings).
2. All failures (skipped / unanalyzable files and the reasons).

## Execution Steps

### 1. Gather Git Context

Run these git commands to understand the branch state:

```bash
# Abort early if not inside a git repository
git rev-parse --is-inside-work-tree 2>/dev/null || { echo "Error: not a git repository."; exit 1; }

# Determine base branch: prefer BASE_BRANCH env var, then origin HEAD, then try main/master
BASE_BRANCH="${BASE_BRANCH:-$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')}"
if [ -z "$BASE_BRANCH" ]; then
  if git show-ref --verify --quiet refs/heads/main 2>/dev/null; then
    BASE_BRANCH="main"
  elif git show-ref --verify --quiet refs/heads/master 2>/dev/null; then
    BASE_BRANCH="master"
  else
    echo "Error: could not detect base branch (no main or master found)."; exit 1
  fi
fi

# Current branch name (fail clearly on detached HEAD)
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ -z "$BRANCH_NAME" ] || [ "$BRANCH_NAME" = "HEAD" ]; then
  echo "Error: detached HEAD state — cannot determine current branch."; exit 1
fi

# Prevent reviewing a branch against itself
if [ "$BRANCH_NAME" = "$BASE_BRANCH" ]; then
  echo "Cannot review base branch ($BASE_BRANCH) against itself."; exit 1
fi

# Common ancestor with base branch
MERGE_BASE=$(git merge-base "$BASE_BRANCH" HEAD 2>/dev/null) || { echo "Error: could not find merge base with $BASE_BRANCH (missing remote?)"; exit 1; }

# Files changed (names only)
git diff "$MERGE_BASE"...HEAD --name-only

# Change statistics
git diff "$MERGE_BASE"...HEAD --stat

# Commit log for this branch
git log "$MERGE_BASE"..HEAD --oneline --no-decorate
```

Capture and store:

- `BASE_BRANCH`: configured or auto-detected base branch
- `BRANCH_NAME`: current branch
- `MERGE_BASE`: the ancestor commit hash
- `CHANGED_FILES`: list of changed file paths
- `DIFF_STAT`: insertions/deletions summary
- `COMMIT_LOG`: list of commits on this branch

If `CHANGED_FILES` is empty, output a short message: "No changes detected between this branch and `$BASE_BRANCH`." and stop.

### 2. Filter and Classify Files

**Exclude** these files from analysis (still list them in the report header as "Excluded"):

- `**/package-lock.json`, `**/yarn.lock`, `**/pnpm-lock.yaml`
- `**/node_modules/**`
- `**/dist/**`, `**/build/**`, `**/.next/**`
- `**/*.min.js`, `**/*.min.css`
- Binary files (images, fonts, etc.)
- `**/.claude/**` (command and skill files themselves)
- `**/.claude/skills/**`

**Classify** remaining files into categories using the Configuration values:

| Category | Pattern (uses config values) | Review Rigor |
|----------|-------------------------------|--------------|
| `CODIGO` | `{baseDir}/**/*.{fileExtensions}` — excluding `testFilePatterns` and `generatedDirs` | Full analysis |
| `UI_LIB` | files matching `generatedDirs` (e.g. `src/components/ui/**`) | Reduced rigor when `uiLibReducedRigor=true` — only flag CRITICO/ALTO issues |
| `TESTES` | files matching `testFilePatterns` (e.g. `src/**/*.test.ts`, `src/test/**`) | Test quality analysis |
| `CONFIG` | files matching `configFilePatterns` (e.g. `*.config.*`, `tsconfig*`, `package.json`) | Config-specific checks only |
| `DOCS` | `*.md`, `*.txt` (excluding `.claude/`) | Skip analysis, note in header |
| `STYLES` | files matching `styleFilePatterns` (e.g. `**/*.css`) | Minimal review |

If more than 15 files are classified as `CODIGO` or `TESTES`, prioritize files with the most changes (by diff stat lines changed). Note any deprioritized files in the report.

### 3. Load Context for Analysis

For each file, load the appropriate context:

- **CODIGO / TESTES**: Read the full git diff for the file AND the complete current file content. If the file imports local modules that were also changed, note the relationship.
- **UI_LIB**: Read only the git diff (not full file content).
- **CONFIG**: Read the git diff only.

Use the `Read` tool for file contents and `Bash` with `git diff` for diffs.

When a `CODIGO` file imports types or functions from other changed files, note these cross-file dependencies for coherence analysis.

### 4. Assess Test Coverage

Map each `CODIGO` file to its corresponding test file(s) using the following priority order. Probe each candidate path in order and stop at the first level that yields **at least one existing file**:

| Priority | Candidate pattern (given source `{dir}/{Base}.{ext}`) |
|----------|-------------------------------------------------------|
| 1 (highest) | `{dir}/{Base}.test.{ext}` then `{dir}/{Base}.spec.{ext}` — same directory, same extension |
| 2 | `{dir}/{Base}.test.ts`, `{dir}/{Base}.test.tsx`, `{dir}/{Base}.test.js`, `{dir}/{Base}.test.jsx` — same directory, all extensions |
| 3 | `{dir}/__tests__/{Base}.test.{ext}`, `{dir}/__tests__/{Base}.spec.{ext}` — `__tests__` sibling folder |
| 4 | `{testRoot}/{dir}/{Base}.test.{ext}`, `{testRoot}/{dir}/{Base}.spec.{ext}` — project test root |
| 5 (lowest) | Any file in `CHANGED_FILES` (TESTES category) whose basename matches `{Base}` (case-insensitive) |

**Auto-detect `{testRoot}`**: Check in order:

1. If `vitest.config.*` or `vite.config.*` exists, look for `test.root` or `test.include` paths in the config
2. If `jest.config.*` or `package.json` contains `jest.roots` or `jest.testMatch`, derive the test root
3. Fall back to the first of `src/test/`, `tests/`, `test/`, or `__tests__/` that exists at repo root

**Resolution rules:**

- A **match** at a priority level means one or more candidate paths resolve to real files in the repository.
- Matching stops at the first level that produces at least one match; lower-priority levels are not checked.
- When multiple test files match (e.g. both `.test.ts` and `.test.tsx` exist), treat them as a **single logical match group** — any one of them being in `CHANGED_FILES` satisfies the COM_TESTE condition.

Classify each `CODIGO` file using the matched group:

- **COM_TESTE**: A matching test file group was found AND at least one file in the group was modified in this branch (i.e. appears in `CHANGED_FILES`).
- **TESTE_DESATUALIZADO**: A matching test file group was found but **none** of the files in the group were modified in this branch despite production code changes.
- **SEM_TESTE**: No matching test file found at any priority level.

### 5. Zen Principles Analysis

Apply these 5 principles as analysis lenses to all `CODIGO` files (reduced rigor for `UI_LIB`):

#### 5.1 "Beautiful is better than ugly" & "Readability counts"

- Non-semantic variable/function names (single letters, abbreviations, misleading names)
- Inconsistent formatting within the changed code
- Magic numbers or strings without named constants
- Excessively long functions (>50 lines of logic)
- Missing or misleading JSDoc on exported functions

#### 5.2 "Explicit is better than implicit"

- Missing TypeScript types or using `any`
- Implicit return types on exported functions
- React component props without explicit interface/type
- `useEffect` with missing or incorrect dependency arrays
- Implicit boolean coercion that could mask bugs (e.g., `value && <Component />` where value could be `0`)

#### 5.3 "Simple is better than complex"

- Over-engineered abstractions for simple problems
- Unnecessary indirection (wrapper functions that just forward calls)
- Single Responsibility Principle violations (component doing too much)
- Custom hooks that could be replaced with simpler patterns
- Premature optimization without evidence of need (flag as BAIXO with note: "Consider profiling to confirm benefit before applying")

#### 5.4 "Flat is better than nested"

- Arrow code (>3 levels of nesting)
- Missing guard clauses (early returns)
- Deeply nested ternary operators in JSX
- Callback pyramids (nested `.then()` chains or nested callbacks)
- Complex conditional rendering that could be extracted

#### 5.5 "Errors should never pass silently"

- Empty `catch` blocks or catch with only `console.log`
- Unhandled Promise rejections
- Missing error boundaries for component trees
- API calls without error feedback to the user
- Silent fallbacks that hide bugs (e.g., `value ?? defaultValue` without logging)

### 6. Additional Detection Passes

#### 6.1 Bug Detection

- Potential null/undefined access without checks
- `useEffect` dependency array mismatches (missing deps or unnecessary deps)
- Race conditions in async operations (stale closure, unmounted component updates)
- Direct state mutation (modifying state objects/arrays without creating new references)
- Off-by-one errors in loops or array operations
- Incorrect equality checks (`==` instead of `===`)
- `async` functions that never `await` anything (likely missing await or unnecessary async)

#### 6.2 Security

- XSS vectors: `dangerouslySetInnerHTML`, unescaped user input in DOM
- Exposed secrets, API keys, tokens in code or config
- Hardcoded API URLs or service endpoints (should use environment variables or config)
- `eval()`, `new Function()`, or dynamic code execution
- Insecure data handling (sensitive data in localStorage without encryption)
- Missing input validation/sanitization at system boundaries

#### 6.3 Performance

- Inline object/array/function creation in JSX props (new reference every render)
- Large components that should be split for code-splitting / lazy loading
- Missing `key` props or using array index as `key` in dynamic lists
- **`React.memo` missing** — flag as **MEDIO** only when the component is rendered inside a list or loop, or when prop identity changes are known to cause unnecessary child re-renders. Otherwise flag as **BAIXO** or omit.
- **`useCallback` missing** — flag as **MEDIO** only when the callback is passed as a prop to a memoized child or used in a `useEffect` dependency array and its identity changes provably cause repeated effect execution. Otherwise flag as **BAIXO** or omit.
- **`useMemo` missing** — flag as **MEDIO** only when the computation is demonstrably expensive (>100ms measured, or explicitly identified by profiling). For cheap computations flag as **BAIXO** or omit.
- **All other memoization suggestions** — assign **BAIXO** and include a note: _"Recommend running a profiler before applying this optimization to confirm a measurable benefit."_
- Expensive computations inside render without memoization (apply the `useMemo` criteria above before flagging)

#### 6.4 Type Safety

- Usage of `any` type (explicit or implicit)
- Excessive type assertions (`as Type`) that bypass type checking
- Missing return types on exported functions
- Optional chaining chains longer than 3 levels (`a?.b?.c?.d?.e`)
- Missing discriminated union checks (switch without default/exhaustive check)

### 7. Assign Severities

Each finding gets one severity:

| Severity | Criteria | Action |
|----------|----------|--------|
| **CRITICO** | Security vulnerabilities, data loss risk, crashes in production, exposed secrets | Must fix before merge |
| **ALTO** | Bugs likely to manifest, missing error handling on user-facing flows, `any` on public API | Should fix before merge |
| **MEDIO** | Code smell, minor Zen violations, missing tests for new logic, performance concerns | Recommend fixing |
| **BAIXO** | Style preferences, minor readability improvements, suggestions for future improvement | Optional improvement |

### 8. Produce Structured Report

Read `references/report-template.md` for the full report structure, grading scale, and examples.

Output the Markdown report directly in the conversation following that template.

### 9. Handle Special Cases

- **Zero findings**: Output a congratulatory report. Grade A across all criteria. Still show the header, test coverage table, and grade table.
- **$ARGUMENTS matches a focus area**: Only run the matching detection passes from steps 5-6. Still show full report structure but mark non-analyzed sections as "Not analyzed (focused review on {area})".
- **$ARGUMENTS matches a file path/glob**: Only analyze matching files from the changed files list. Show only those files in the report.
- **UI_LIB files**: Apply only CRITICO and ALTO severity checks. Note in findings: "(UI_LIB - reduced rigor)".
- **More than 50 findings**: Show all CRITICO/ALTO/MEDIO findings first, then as many BAIXO as fit within the 50-finding cap. Add overflow count. Recommend running focused reviews per file.

## Operating Principles

### Context Efficiency

- **Load diffs before full files**: Only read complete file content when the diff suggests deeper analysis is needed
- **Prioritize by change size**: Files with more changes get more thorough analysis
- **Cap analysis scope**: Maximum 15 full file reads to avoid context exhaustion
- **Be specific**: Every finding must reference a specific file and line number from the actual diff

### Analysis Integrity

- **NEVER modify files** — this is strictly read-only analysis
- **NEVER hallucinate line numbers** — only reference lines you actually read from the diff or file
- **NEVER invent findings** — if the code is clean, say so. A clean report is a valid outcome.
- **Be fair to generated code** — UI_LIB files get reduced scrutiny
- **Acknowledge context limits** — if you couldn't fully analyze a file, say so in the report
- **Ground findings in evidence** — quote the problematic code snippet in the finding description when helpful
