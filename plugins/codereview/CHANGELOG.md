# Changelog — codereview

Formato: [Semantic Versioning](https://semver.org/)

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
