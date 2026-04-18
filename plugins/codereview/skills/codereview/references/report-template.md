# Report Template

This file defines the full Markdown report structure for the codereview skill.

---

## Report Structure

Output the following Markdown report directly in the conversation:

---

# Code Review: {BRANCH_NAME}

**Branch**: `{BRANCH_NAME}` → `{BASE_BRANCH}`
**Commits**: {number of commits}
**Files Changed**: {total} (CODE: {n}, UI_LIB: {n}, TESTS: {n}, CONFIG: {n}, Excluded: {n})
**Lines**: +{insertions} / -{deletions}

If `$ARGUMENTS` specified a focus area, note: **Focus**: {focus area}

**If the Secrets Detection table below has ≥1 row**, prepend this banner to the entire report (before the H1) and do not remove it:

```markdown
> 🛑 **BLOCKED — Hardcoded secrets detected.** GitGuardian / ggshield / gitleaks would also reject this branch. Do not push as-is: remediate the rows in the Secrets Detection table first. See [GitGuardian best practices](https://blog.gitguardian.com/secrets-api-management/).
```

---

### 🛑 Secrets Detection

Always render this section, even when clean (this tells the user the pass ran). The `Snippet` column must show the literal with the secret value masked (`***`) — never echo the raw credential back, because this report is shared in chat history.

| # | File | Line | Kind | Snippet (masked) | Severity | Remediation |
|---|------|------|------|------------------|----------|-------------|
| 1 | server/test/auth.test.ts | 30 | Generic Password | `password: "***"` | HIGH | 1) env var  2) rotate  3) rewrite history |
| 2 | server/src/server.ts | 49 | Generic Password | `secret: "***"` | CRITICAL | 1) env var  2) rotate  3) rewrite history |

**Status**: `PASS` (0 rows) / `BLOCKED` (≥1 row).

When Status is `BLOCKED`:
- Overall grade is forced to **F** regardless of anything else in the report.
- Each row must appear again under "Must Fix (CRITICAL)" with the full remediation block from `references/detection-passes.md` pass 6.10 (env var + rotate + rewrite history + install ggshield pre-commit).
- If multiple rows share the same file and kind, collapse them into a single row `Lines: 30, 53, 62, ...` and note the count.

---

### Findings Table

| # | Severity | Category | File | Line(s) | Finding | Suggested Action |
|---|----------|----------|------|---------|---------|-----------------|
| 1 | CRITICAL | Security | src/api/client.ts | 23 | API key hardcoded | Move to environment variable |
| 2 | HIGH | Bug | src/hooks/useQuote.ts | 45-48 | Missing useEffect dep | Add `quoteId` to dependency array |
| ... | | | | | | |

Order by: CRITICAL first, then HIGH, MEDIUM, LOW. Within same severity, group by file.

If more than 50 findings total, show all CRITICAL/HIGH/MEDIUM findings first, then as many LOW findings as fit within the 50-finding cap. Add: "_{n} additional LOW findings omitted. Run with specific file path to see all._"

---

### Zen Principles Summary

| Principle | Violations | Worst Severity | Key Example |
|-----------|-----------|----------------|-------------|
| Readability | {n} | HIGH | `src/components/Quote.tsx:34` - magic number |
| Explicit > Implicit | {n} | MEDIUM | Missing prop types |
| Simple > Complex | {n} | LOW | Over-abstracted hook |
| Flat > Nested | {n} | MEDIUM | 4-level ternary |
| Error Handling | {n} | HIGH | Empty catch block |

---

### Bug / Security / Performance / Types Summary

| Category | Findings | CRITICAL | HIGH | MEDIUM | LOW |
|----------|---------|----------|------|--------|-----|
| Bugs | {n} | {n} | {n} | {n} | {n} |
| Security | {n} | {n} | {n} | {n} | {n} |
| **Secrets (pass 6.10)** | {n} | {n} | {n} | 0 | 0 |
| Performance | {n} | {n} | {n} | {n} | {n} |
| Type Safety | {n} | {n} | {n} | {n} | {n} |
| Documentation | {n} | {n} | {n} | {n} | {n} |

> Secrets never carry MEDIUM/LOW severity. They are either CRITICAL (prod code, config, or credentialed connection strings) or HIGH (inline test-file literals). Env-var lookups are not counted at all.

---

### Test Coverage

| Production File | Test Status | Test File | Notes |
|----------------|------------|-----------|-------|
| src/components/Quote.tsx | WITH_TESTS | src/test/Quote.test.tsx | Updated in this branch |
| src/hooks/useCalc.ts | NO_TESTS | — | New file, needs tests |
| src/utils/format.ts | STALE_TESTS | src/test/format.test.tsx | Test not updated |

**Coverage of changed CODE files**: {WITH_TESTS}/{Total_CODE} files have up-to-date tests ({percentage}%)

> **Formula**: `percentage = Total_CODE > 0 ? round((WITH_TESTS / Total_CODE) * 100) : N/A`
>
> - `WITH_TESTS` — count of CODE files whose test file exists **and** was updated alongside the production change in this branch.
> - `Total_CODE` — total number of files classified as CODE in the changed-files list.
> - `STALE_TESTS` files are **excluded** from the numerator (they have a test file but it was not updated, so coverage is considered incomplete).
> - Files classified as TESTS, CONFIG, or UI_LIB are not counted in either numerator or denominator.

---

### Documentation Sync

| Area | Status | File | Notes |
|------|--------|------|-------|
| Docstrings | OK / MISSING | src/services/foo.ts | 3 exported functions without JSDoc |
| OpenAPI | OK / STALE | docs/openapi.json | New endpoint not documented |
| README | OK / STALE | README.md | New feature not in features list |
| Backend Rules | OK / STALE | .claude/rules/backend-api.md | Model count outdated |
| Frontend Rules | OK / N/A | .claude/rules/frontend-react.md | — |
| CLAUDE.md | OK / N/A | CLAUDE.md | — |
| MEMORY.md | OK / N/A | MEMORY.md | — |

**Docstring coverage of changed CODE files**: {WITH_DOCS}/{Total_changed_functions} functions/methods have up-to-date documentation ({percentage}%)

> Only count functions/methods/classes that are new or modified in this branch.
> A function counts as "documented" if it has a JSDoc/XML doc/docstring that matches its current behavior.
> If the project specifies a documentation language (e.g., PT-BR), docstrings in the wrong language count as MISSING.

---

### Overall Grade

Rate each criterion A through F:

| Criterion | Grade | Rationale |
|-----------|-------|-----------|
| Code Quality (Zen) | | |
| Type Safety | | |
| Error Handling | | |
| Security | | |
| Performance | | |
| Test Coverage | | |
| Documentation | | |
| **Overall** | **{grade}** | |

## Grading Scale

- **A**: No CRITICAL/HIGH findings; at most minor MEDIUM/LOW items; Secrets Detection `PASS`.
- **B**: No CRITICAL; few HIGH findings that are straightforward to fix; Secrets Detection `PASS`.
- **C**: No CRITICAL; multiple HIGH findings or systemic MEDIUM patterns; Secrets Detection `PASS`.
- **D**: Has CRITICAL findings or pervasive HIGH issues; Secrets Detection `PASS`.
- **F**: Multiple CRITICAL findings, security vulnerabilities, fundamentally broken code, **or any row in the Secrets Detection table**. One leaked credential is enough — no exceptions, no "but it's only a test password".

---

### Recommended Actions

**Must Fix (CRITICAL)**:

- List each critical finding with file:line and concrete fix instruction

**Should Fix (HIGH)**:

- List each high finding with file:line and suggested approach

**Consider Fixing (MEDIUM/LOW)**:

- Brief summary of improvements, grouped by theme

---

## Examples

### Minimal run — full review

```bash
# From inside the feature branch
/codereview
```

**Expected output (excerpt)**:

```text
# Code Review: feature/my-feature

**Branch**: `feature/my-feature` → `main`
Files changed: 4 | Insertions: 87 | Deletions: 23

### Findings Summary
| # | Severity | File | Line | Description |
|---|----------|------|------|-------------|
| 1 | HIGH     | src/utils/pdf/fillPdfWithJson.ts | 45 | Unhandled promise rejection ... |

### Grade: B
```

### .NET project — minimal run

```bash
/codereview fileExtensions=cs frameworkPatterns=dotnet
```

**Expected output (excerpt)**:

```text
# Code Review: 001-licencemanager-decoupling

**Branch**: `001-licencemanager-decoupling` → `master`
Files changed: 6 | Insertions: 320 | Deletions: 45

### Findings Summary
| # | Severity | File | Line | Description |
|---|----------|------|------|-------------|
| 1 | HIGH     | LicenseService.cs | 67 | IDisposable RSACryptoServiceProvider not wrapped in `using` |
| 2 | MEDIUM   | MainWindowViewModel.cs | 112 | File dialog in ViewModel — consider abstracting behind interface |

### Grade: B
```

### Focused run — security only

```bash
/codereview security
```

Non-security detection passes are skipped; the report marks them as "Not analyzed (focused review on security)".

---

## Troubleshooting

- **"Error: not a git repository"** — Run the command from inside the project directory where `.git` is present.
- **"Cannot review base branch against itself"** — Checkout a feature branch before running; the command cannot diff the base branch against itself.
- **"Error: detached HEAD state"** — Attach HEAD to a branch with `git checkout <branch-name>` before running.
- **Report shows 0 changed files** — Ensure at least one commit exists on the current branch that is not yet on the base branch (`git log main..HEAD` should be non-empty).
- **More than 50 findings truncated** — Run focused reviews per area (e.g. `/codereview security`) to narrow scope and surface all findings within the cap.
- **Hallucinated line numbers in report** — This violates Analysis Integrity rules. Re-run the command; if the issue persists, increase context by reading fewer full files and relying on diffs.

---

## Closing Remarks

This specification defines a fully automated, read-only pre-PR code review workflow. The skill diffs the current branch against the base branch, classifies every changed file, runs targeted detection passes across security, performance, type safety, bugs, and test coverage, then emits a structured Markdown report with severity-graded findings and an overall letter grade. The goal is to surface actionable issues before human review so PRs arrive already triaged — reducing review cycles and catching regressions early.
