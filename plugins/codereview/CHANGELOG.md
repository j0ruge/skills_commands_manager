# Changelog — codereview

Formato: [Semantic Versioning](https://semver.org/)

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
