# Report Template

This file defines the full Markdown report structure for the codereview skill.

---

## Report Structure

Output the following Markdown report directly in the conversation:

---

# Code Review: {BRANCH_NAME}

**Branch**: `{BRANCH_NAME}` → `{BASE_BRANCH}`
**Commits**: {number of commits}
**Files Changed**: {total} ({CODIGO}: {n}, UI_LIB: {n}, TESTES: {n}, CONFIG: {n}, Excluded: {n})
**Lines**: +{insertions} / -{deletions}

If `$ARGUMENTS` specified a focus area, note: **Focus**: {focus area}

---

### Findings Table

| # | Severity | Category | File | Line(s) | Finding | Suggested Action |
|---|----------|----------|------|---------|---------|-----------------|
| 1 | CRITICO | Security | src/api/client.ts | 23 | API key hardcoded | Move to environment variable |
| 2 | ALTO | Bug | src/hooks/useQuote.ts | 45-48 | Missing useEffect dep | Add `quoteId` to dependency array |
| ... | | | | | | |

Order by: CRITICO first, then ALTO, MEDIO, BAIXO. Within same severity, group by file.

If more than 50 findings total, show all CRITICO/ALTO/MEDIO findings first, then as many BAIXO findings as fit within the 50-finding cap. Add: "_{n} additional BAIXO findings omitted. Run with specific file path to see all._"

---

### Zen Principles Summary

| Principle | Violations | Worst Severity | Key Example |
|-----------|-----------|----------------|-------------|
| Readability | {n} | ALTO | `src/components/Quote.tsx:34` - magic number |
| Explicit > Implicit | {n} | MEDIO | Missing prop types |
| Simple > Complex | {n} | BAIXO | Over-abstracted hook |
| Flat > Nested | {n} | MEDIO | 4-level ternary |
| Error Handling | {n} | ALTO | Empty catch block |

---

### Bug / Security / Performance / Types Summary

| Category | Findings | CRITICO | ALTO | MEDIO | BAIXO |
|----------|---------|---------|------|-------|-------|
| Bugs | {n} | {n} | {n} | {n} | {n} |
| Security | {n} | {n} | {n} | {n} | {n} |
| Performance | {n} | {n} | {n} | {n} | {n} |
| Type Safety | {n} | {n} | {n} | {n} | {n} |

---

### Test Coverage

| Production File | Test Status | Test File | Notes |
|----------------|------------|-----------|-------|
| src/components/Quote.tsx | COM_TESTE | src/test/Quote.test.tsx | Updated in this branch |
| src/hooks/useCalc.ts | SEM_TESTE | — | New file, needs tests |
| src/utils/format.ts | TESTE_DESATUALIZADO | src/test/format.test.tsx | Test not updated |

**Coverage of changed CODIGO files**: {COM_TESTE}/{Total_CODIGO} files have up-to-date tests ({percentage}%)

> **Formula**: `percentage = Total_CODIGO > 0 ? round((COM_TESTE / Total_CODIGO) × 100) : N/A`
>
> - `COM_TESTE` — count of CODIGO files whose test file exists **and** was updated alongside the production change in this branch.
> - `Total_CODIGO` — total number of files classified as CODIGO in the changed-files list.
> - `TESTE_DESATUALIZADO` files are **excluded** from the numerator (they have a test file but it was not updated, so coverage is considered incomplete).
> - Files classified as TESTE, CONFIG, or UI_LIB are not counted in either numerator or denominator.

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
| **Overall** | **{grade}** | |

## Grading Scale

- **A**: No CRITICO/ALTO findings; at most minor MEDIO/BAIXO items
- **B**: No CRITICO; few ALTO findings that are straightforward to fix
- **C**: No CRITICO; multiple ALTO findings or systemic MEDIO patterns
- **D**: Has CRITICO findings or pervasive ALTO issues
- **F**: Multiple CRITICO findings, security vulnerabilities, or fundamentally broken code

---

### Recommended Actions

**Must Fix (CRITICO)**:

- List each critical finding with file:line and concrete fix instruction

**Should Fix (ALTO)**:

- List each high finding with file:line and suggested approach

**Consider Fixing (MEDIO/BAIXO)**:

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
| 1 | ALTO     | src/utils/pdf/fillPdfWithJson.ts | 45 | Unhandled promise rejection ... |

### Grade: B
```

### Focused run — security only

```bash
/codereview seguranca
```

Non-security detection passes are skipped; the report marks them as "Not analyzed (focused review on seguranca)".

---

## Troubleshooting

- **"Error: not a git repository"** — Run the command from inside the project directory where `.git` is present.
- **"Cannot review base branch against itself"** — Checkout a feature branch before running; the command cannot diff the base branch against itself.
- **"Error: detached HEAD state"** — Attach HEAD to a branch with `git checkout <branch-name>` before running.
- **Report shows 0 changed files** — Ensure at least one commit exists on the current branch that is not yet on the base branch (`git log main..HEAD` should be non-empty).
- **More than 50 findings truncated** — Run focused reviews per area (e.g. `/codereview seguranca`) to narrow scope and surface all findings within the cap.
- **Hallucinated line numbers in report** — This violates Analysis Integrity rules. Re-run the command; if the issue persists, increase context by reading fewer full files and relying on diffs.

---

## Closing Remarks

This specification defines a fully automated, read-only pre-PR code review workflow. The skill diffs the current branch against the base branch, classifies every changed file, runs targeted detection passes across security, performance, type safety, bugs, and test coverage, then emits a structured Markdown report with severity-graded findings and an overall letter grade. The goal is to surface actionable issues before human review so PRs arrive already triaged — reducing review cycles and catching regressions early.
