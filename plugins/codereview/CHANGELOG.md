# Changelog — codereview

Formato: [Semantic Versioning](https://semver.org/)

## [1.9.0] - 2026-05-05

### Changed (coderabbit_pr v3.1.0 → v3.2.0 — baseline-aware regression testing)

- **New Phase 4.0 "Capture Pre-Fix Baseline"** — instructs the skill to run the project's test command BEFORE applying any review fixes, saving pass/fail counts and the list of failing test names as a baseline. Without this, Phase 4.2 can't tell "regression caused by my fix" from "pre-existing latent unmasked by my fix".
- **Phase 4.2 expanded into a 5-way comparison** against the baseline: all-pass, same-failures-as-baseline (don't fix), new-failures (fix), fewer-failures (note but don't claim), mixed (separate). Each branch has explicit instructions about what to do.
- **Anti-silencing rule** added explicitly to 4.2: do NOT use `it.skip`, `if: false` on workflow steps, or `continue-on-error: true` to make CI green. Document and defer.
- **Operating Principle "Discipline"** gained a new bullet: "Don't expand scope to fix latent bugs — pre-existing test failures unmasked by your fixes are NOT yours to fix. Document and open follow-up issue."

### Why

PR #6 on `validade_bateria_estoque` had 8 red CI jobs. The root cause for 6 of them was a single broken `npm run -w <ws> exec --` syntax in 3 workflows — a fail-fast error that aborted in seconds at the Typecheck step, **masking** all subsequent steps. After the fix unblocked CI, **44 frontend tests started failing** with msw/jsdom AbortSignal interop errors, and 2 backend type errors appeared in `auth-sanity.test.ts`. These were ALL pre-existing — the `npm run … exec` failure was hiding them.

Without baseline awareness, Phase 4 of `coderabbit_pr` would treat these 44+2 failures as "caused by the applied fixes" and either (a) try to fix them (scope explosion: msw/jsdom interop is a non-trivial test infrastructure rabbit hole) or (b) silence them (which the skill explicitly should never do). The correct triage is: capture baseline before any fix, distinguish unmasked-latent from caused-by-edit, document the latent, fix only the caused-by-edit, push.

This generalizes beyond CI cascades: any regression-detection workflow needs a baseline to be honest. Without it, the question "did my change break X?" collapses into "is X broken?" — and the answer is often "yes, but not because of you".

### Migration notes

- No breaking changes. Skill still resolves PR comments end-to-end.
- New mandatory step at start of Phase 4 adds ~30s for typical projects (one extra `npm test` run). For PRs with `--skip-tests`, Phase 4 is skipped entirely as before.
- Existing checklists that don't include a "Pre-existing latent failures" subsection are still valid; the skill will add one when applicable.

## [1.8.0] - 2026-04-28

### Changed (codereview v1.8.0 — deterministic secret scanning replaces LLM-simulated regex)

- **New `scripts/scan_secrets.py` + `scripts/scan_secrets.sh` wrapper** — Phase A haiku agent now runs a real Python regex pass against the unified diff. Catalog from pass 6.10 is encoded as `re.compile` patterns with deterministic exception filtering (env-var lookups, placeholder values, `.env.example`/`.env.sample`/`.env.template` paths). When `ggshield` or `gitleaks` are on `PATH`, the script invokes them too and merges results (dedup by `{file, line, kind}`).
- **Phase A agent prompt now explicitly invokes the script** as numbered step 8 — captures the JSON output as `secrets_prescan` field in the structured return. Previously the prompt asked the agent to "apply" the regex catalog mentally; in practice substring shapes like `initialPassword: '<literal>'` (where `password` is a suffix of the keyword) were missed because LLMs aren't regex engines.
- **Phase C merge logic inverted** — `secrets_prescan` from Phase A is the **authoritative** source for the Secrets Detection table and the F-grade gate. Sonnet pass-6.10 findings are now treated as supplemental (context-aware nuance only); they're added to the table only if they reference a concrete literal credential AND match a pass 6.10 category. This eliminates LLM speculation as a gate-trigger while keeping it useful for edge cases regex can't see.
- **`detection-passes.md` corrected** — removed the false claim "this skill is read-only prose produced by LLM agents — it can't shell out to `ggshield`". The skill IS read-only (no `Edit`/`Write`/destructive git ops) but `Bash` invocations of pure scanners are perfectly compatible with that constraint and were always available. Replaced with a section pointing to the script as the single executable source of truth, with a note that the conceptual catalog and the script must be kept in sync (no automated guard yet).
- **Severity nuance preserved in script** — test-file inline literals stay HIGH (not CRITICAL) per pass 6.10 rules; multi-occurrence escalation (3+ in one file or 5+ across PR) still upgrades to CRITICAL. All exception logic (env lookups, placeholders, template files) ported faithfully from the conceptual catalog.

### Why

After PR #2 on `validade_bateria_estoque` (`feat(002-idp-oidc): IdP OIDC via Zitadel`) was blocked by GitGuardian with **3 Generic Password findings** (2 in test integration files at `initialPassword: '<literal>'` shape, 1 false-positive in a docker-compose env-var substitution), the user pointed out that v1.7.0 should have caught these locally before push. Investigation found three distinct gaps:

1. **Phase A pre-scan was a phantom step** — `SKILL.md` had a paragraph saying "the haiku agent runs a fast regex pre-scan" but the actual agent prompt code block never instructed the agent to do this. The pre-scan never ran.
2. **LLM-simulated regex is unreliable** — sonnet agents were asked to mentally apply the regex catalog from `detection-passes.md`. Substring shapes like `initialPassword: '...'` (where `password` is the suffix of `initialPassword`) were missed because the LLM "saw" the field name, not the regex match. False-negative rate was high enough on real-world test fixtures to defeat the purpose.
3. **`detection-passes.md` falsely claimed the skill couldn't shell out** — citing "read-only prose" as the reason. But read-only proibits Edit/Write/destructive git, not pure scanner invocations. The skill could have been running `ggshield secret scan path` or `grep -nE` since v1.0.

The v1.8.0 fix replaces LLM regex simulation with a real Python regex pass, enforced via an explicit numbered step in the haiku prompt. Verification against the actual PR #2 diff (`git diff a8551d2~1..6039813`) catches all 3 GitGuardian findings (and bonus catches a fourth `const SECRET = '<literal>'` that GitGuardian missed).

### Migration notes

- No breaking changes for users who don't customize the skill. Existing invocations like `/codereview` or `/codereview security` work identically; the only difference is the secrets pass actually fires now.
- If you wrote custom skills extending or wrapping this one, the haiku agent's structured return now includes `secrets_prescan: {findings, scanners, errors}`. Old fields (`BASE_BRANCH`, `BRANCH_NAME`, etc.) are unchanged.
- `scripts/scan_secrets.py` requires Python 3.8+ (uses dataclasses + walrus-free syntax for compatibility). No external deps; works in any environment that already has `python3`.

## [1.7.0] - 2026-04-18

### Added (codereview v1.7.0 — hardcoded secrets detection)

- **New pass 6.10 "Hardcoded Secrets Detection"** in `references/detection-passes.md` — explicit regex-based detection for generic passwords, JWT/Bearer, PEM keys, AWS/GCP/GitHub/Slack/Stripe tokens, `.env`-shaped assignments, and credentialed connection strings. Approximates what a dedicated CI scanner (GitGuardian, gitleaks, trufflehog) would reject.
- **Always applied to ALL file categories** — CODE, TESTS, CONFIG, UI_LIB, STYLES. Previously pass 6.2 was vague and `TESTS` files had reduced scrutiny; in practice test-file password literals are one of the most common leak shapes.
- **Always on regardless of focus area** — pass 6.10 runs even when the user asks for `/codereview performance` or `/codereview types`. A leaked credential is the one finding a user cannot afford to miss, so focus flags never silence it.
- **Phase A haiku pre-scan** — haiku agent now runs a fast regex sweep across the full raw diff (`git diff ${MERGE_BASE}...HEAD`) independent of file classification, catching secrets that land in `EXCLUDED`/`DOCS`/`CONFIG` files that per-file analysis would otherwise skip.
- **Anti-false-positive rules** — env-var lookups (`process.env.X`, `import.meta.env.X`, `config.get(...)`, `os.environ[...]`, `ConfigurationManager.AppSettings[...]`), placeholders (`"CHANGE_ME"`, `"xxx"`, `"<your-key-here>"`, empty string, null), and `.env.example`/`.env.sample`/`.env.template` placeholder values are explicitly not flagged.
- **Test-file nuance** — inline test literals (`password: "test123"`) flagged as HIGH (not CRITICAL) since they're less dangerous than prod keys but still rejected by CI scanners; literals pulled from `fixtures/` modules or `process.env.TEST_*` are not flagged.
- **Multi-occurrence aggregation** — 3+ matches in one file or 5+ across a PR collapse to a single aggregate finding with count and line ranges, escalated to CRITICAL. Signals systemic leaks rather than drowning the report.
- **New "Secrets Detection" table** in `references/report-template.md`, rendered before the Findings Table, with masked snippets (`***`), severity column, and Status (PASS/BLOCKED). Always present — shows `PASS` with 0 rows on clean branches to confirm the pass ran.
- **BLOCKED banner + forced grade F** — any pass 6.10 finding forces overall grade to F and prepends a banner linking to [GitGuardian secrets-API-management best practices](https://blog.gitguardian.com/secrets-api-management/). The Grading Scale is updated to reflect this.
- **Full remediation block** — every pass 6.10 finding now includes the four GitGuardian-recommended remediation steps (understand blast radius → env var / secret manager → rotate → rewrite history) plus the recommendation to install `ggshield pre-commit` for durable local defense. Previously the report said only "move to environment variable", which is necessary but insufficient once the secret is already in git history.
- **Masking rule** — findings show the literal masked as `***` rather than echoing the raw credential back into chat history.
- **Trigger phrases expanded** — `"secret detection"`, `"hardcoded credentials"`, `"gitguardian"`, `"ggshield"`, `"leaked password"`, `"api key"`, `"check for secrets"` now trigger the skill.

### Why

PR #5 on `eb-analytics` (`feat(server): cloud sync backend`) was blocked by GitGuardian with **11 Generic Password findings** across two commits (`f0bc35a`, `7257978`): 8 in `auth.test.ts`, 2 in `concurrency.test.ts`, 1 in `server.ts`. The previous pass 6.2 treated "exposed secrets" as a single vague bullet and gave `TESTS` files reduced scrutiny — exactly where most leaks lived. CodeRabbit passed the same PR clean; secret detection is a distinct domain and deserves a dedicated pass with concrete patterns, always-on enforcement, and blocking severity. Aligns with GitGuardian's best practices: use secrets managers, never commit credentials, install `ggshield` as a pre-commit hook, and when a leak happens rotate first and rewrite history second.

## [1.6.0] - 2026-04-12

### Changed (codereview v1.6.0 — model routing)

- **Model routing for token efficiency**: skill now delegates work to cheaper models
  - Haiku agent: git context, file classification, test coverage mapping (pure CLI + pattern matching)
  - Sonnet agents (parallel): per-file analysis using detection passes (pattern matching on code)
  - Opus (main model): cross-file review, severity recalibration, final report production
  - Auto-skip for small PRs (≤3 CODE files) — runs everything in main model
- **Detection passes extracted to reference file**: Steps 5-6 (~350 lines of detection patterns) moved from SKILL.md to `references/detection-passes.md`, keeping SKILL.md as a lean orchestrator (~200 lines)
  - Sonnet agents load only the detection passes + file content in their context
  - Opus receives only structured findings, not raw code — 76-86% less opus tokens
- **Parallel per-file analysis**: each CODE file analyzed independently in its own sonnet agent, enabling parallel execution for faster reviews
- **Cross-file analysis preserved in opus**: race conditions spanning multiple files, schema consistency, and import chain coherence still analyzed by the main model

### Estimated token savings

| PR Size | Before (all Opus) | After (mixed) | Opus Savings |
|---------|-------------------|---------------|--------------|
| Small (3 files) | ~85K | ~20K opus + 50K sonnet/haiku | ~76% |
| Medium (8 files) | ~150K | ~25K opus + 128K sonnet/haiku | ~83% |
| Large (15 files) | ~210K | ~30K opus + 212K sonnet/haiku | ~86% |

## [1.5.0] - 2026-04-12

### Changed (coderabbit_pr v3.0.0 → resolve_pr_reviews)

- **Multi-reviewer support**: now auto-detects and processes CodeRabbit, Copilot, Gemini Code Assist, and Codex reviews on a PR
  - Each reviewer gets its own checklist file (`coderabbit-review.md`, `copilot-review.md`, `gemini-review.md`, `codex-review.md`)
  - Unknown reviewers are handled with a generic parser and `{bot-login}-review.md`
  - New `--reviewer <name>` flag to process only a specific reviewer
- **Model routing for token efficiency**: skill now delegates work to appropriate model tiers
  - Haiku agents: GitHub API calls, data fetching, thread resolution (mechanical tasks)
  - Sonnet agents: comment parsing, code fix execution (pattern matching tasks)
  - Opus (main model): analysis verdicts, spec verification (judgment calls)
  - Auto-skip routing for small PRs (<5 comments) — overhead not worth it
- **Improved analysis quality**: verdicts now check project specs/docs before marking "not applicable"
  - Prevents false fixes on by-design decisions documented in specs
  - "Not applicable" entries now include spec/doc reference
- **Better large-output handling**: sonnet agents absorb 30-50KB+ API responses in their own context and return only structured summaries, keeping the main opus context clean
- **Deduplication improvements**: cross-reviewer dedup, root-cause linking ("Related to item #N")
- **New `references/reviewer-registry.md`**: extensible registry of bot logins, parsing rules, and output file names
- **Severity recalibration**: opus model reassesses reviewer-assigned severities during Phase 3 analysis based on actual code impact (e.g., Copilot defaults everything to MEDIUM but a broken feature flow is HIGH)
- **Cross-reviewer deduplication with audit trail**: items already fixed by another reviewer's round are marked "Already fixed — see {reviewer}-review.md #{N}" instead of re-analyzing
- **Empty reviewer handling**: reviewers with zero findings (e.g., Gemini approval-only) get a minimal `{reviewer}-review.md` for audit completeness

## [1.4.0] - 2026-04-05

### Added

- Detection pass 6.6 Race Conditions & TOCTOU (Time-of-Check to Time-of-Use)
  - Database check-then-act (findUnique + update without atomic claim)
  - Read-modify-write on numeric fields (lost updates)
  - Business rules enforced only in app code (bypass via concurrency)
  - Read outside transaction, write inside (stale data)
  - File system check-then-act (exists then read/write)
  - Cache thundering herd (miss + compute without coalescing)
  - `references/toctou-patterns.md` — full pattern catalog with code examples
- Detection pass 6.7 Accessibility
  - Icon-only buttons without aria-label
  - Form buttons without type="button" (implicit submit)
  - Interactive elements without keyboard support
  - Images without alt text
- Detection pass 6.8 Data Integrity & Schema Safety
  - Cascade delete risks on user/tenant entities
  - Missing database indexes on junction tables
  - URL fields accepting dangerous protocols (javascript:, data:)
  - Inconsistent validation schemas across endpoints
  - Test fakes/mocks missing fields from production schema
- Focus areas `a11y` and `race-conditions` for targeted reviews
- `security` focus now includes 6.6 Race Conditions and 6.8 URL/cascade checks
- `bugs` focus now includes 6.6 Race Conditions

### Changed (coderabbit_pr v2.0.0)

- Fixed parsing of "outside-diff-range" comments from CodeRabbit review body
  - Now correctly extracts findings from `<details><summary>` blocks in review body
  - Previously only inline diff comments were detected (2-5 items); now captures all 20-30+ items
- Added Phase 5: Resolve GitHub Conversations
  - Uses GraphQL API to fetch and resolve all unresolved review threads
  - Resolves threads from all reviewers (CodeRabbit, Gemini, Copilot, etc.)
  - Reports resolution count in checklist
- Improved severity mapping to handle both emoji and text markers
- Added deduplication between inline and review body findings

## [1.3.0] - 2026-03-28

### Added

- Detection pass 6.5 Documentation Sync & Docstring Coverage
  - 6.5.1 Docstring coverage: verifica JSDoc/XML doc/docstrings em funcoes novas/modificadas, detecta idioma se projeto especifica (PT-BR, etc.)
  - 6.5.2 Project documentation sync: verifica se README, OpenAPI, rules, CLAUDE.md e MEMORY.md foram atualizados junto com o codigo
- Focus area `docs` para revisar apenas documentacao
- Suporte a docstrings de Go e Shell scripts
- Grade "Documentation" no relatorio final
- Secao Documentation Sync no report-template.md

### Changed

- Agnostico de linguagem para deteccao de docstrings (TS/JS, C#/.NET, Python, Go, Shell)
- Step 9 agora mapeia focus areas para passes especificos explicitamente

## [1.2.0] - 2026-03-25

### Added

- `dotnet` as `frameworkPatterns` option for C#/.NET projects (WPF, WinForms, ASP.NET, Console)
- .NET-specific checks: `async void`, `IDisposable`, `MessageBox` in service classes, `public static` mutable, `new HttpClient()`, `Thread.Sleep()`, SQL injection, MVVM violations
- .NET file exclusions: `bin/`, `obj/`, `*.Designer.cs`, `*.g.cs`
- .NET test file mapping: `{ProjectName}.Tests/{Base}Tests.cs` patterns
- .NET test root auto-detection via `.csproj` references to xUnit/NUnit/MSTest
- .NET override examples in configuration.md
- .NET report example in report-template.md
- `dotnet test` command detection in coderabbit_pr skill

### Changed

- Zen Principles (§5) and Detection Passes (§6) refactored into universal + framework-conditional blocks
- All React/TypeScript-specific checks now conditional on `frameworkPatterns=react|vue|angular|node`
- Backward compatible: default behavior unchanged when no `frameworkPatterns` override is specified

## [1.1.0] - 2026-03-23

### Adicionado

- Nova sub-skill `coderabbit_pr` — extrai comentarios do CodeRabbit de um PR, cria checklist estruturado, verifica e corrige cada item, e roda testes de regressao
- Mapeamento de severidades CodeRabbit (🔴🟠🟡🔵) para CRITICO/ALTO/MEDIO/BAIXO
- Suporte a `--dry-run` (somente verificacao) e `--skip-tests`
- `references/checklist-template.md` — template do arquivo de checklist gerado
- Deteccao automatica de comando de teste (npm/cargo/pytest/go/make)

## [1.0.0] - 2026-03-13

### Adicionado

- Skill de code review automatizado pré-PR inspirado no Zen of Python (PEP 20)
- Análise de diffs com severidades CRITICO/ALTO/MEDIO/BAIXO
- 5 princípios Zen como lentes de análise (readability, explicit, simple, flat, error handling)
- Passes de detecção: bugs, segurança, performance, type safety
- Avaliação de cobertura de testes (COM_TESTE / TESTE_DESATUALIZADO / SEM_TESTE)
- Nota final por letra (A-F) com critérios por categoria
- Stack-agnostic com defaults TypeScript/React configuráveis
- `references/report-template.md` — template completo do relatório
- `references/configuration.md` — valores default e sintaxe de override

---

## Histórico Pré-Marketplace

A skill existia como v2.0.0 informal no repositório `digital_service_report_frontend` (sem disciplina semver). O histórico abaixo documenta a evolução antes da publicação no marketplace.

- **v2.0.0** (2026-03-10): Reescrita completa — classificação de arquivos por categoria, progressive disclosure via references, override de configuração stack-agnostic, grading scale A-F, cap de 50 findings
- **v1.0.0** (2026-03): Versão inicial com análise básica de diffs e relatório estruturado
