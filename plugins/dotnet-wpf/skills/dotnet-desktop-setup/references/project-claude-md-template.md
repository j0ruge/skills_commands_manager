# Template: CLAUDE.md do Projeto

Este template e usado no Passo 4 do workflow. Adapte as variaveis {{...}} para o projeto real.
Mantenha abaixo de **300 linhas** — mova detalhes para `.claude/rules/`.

Framework: **WHAT-WHY-HOW** (CodeWithMukesh pattern).

---

## Template

```markdown
# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview (WHAT)

{{PROJECT_NAME}} — {{DESCRICAO_CURTA}}.

**Stack:** {{TECH_STACK}}
**Target Framework:** {{TARGET_FRAMEWORK}}
**UI Framework:** {{UI_FRAMEWORK}} ({{STATUS_MIGRACAO}})

## Build & Test Commands (HOW)

```bash
# Build
dotnet build {{SOLUTION_FILE}}
dotnet build {{SOLUTION_FILE}} -c Release

# Run all tests (xUnit)
dotnet test {{TEST_PROJECT}}

# Run a single test class
dotnet test {{TEST_PROJECT}} --filter "FullyQualifiedName~{{EXAMPLE_TEST_CLASS}}"

# Run a single test method
dotnet test {{TEST_PROJECT}} --filter "FullyQualifiedName~{{EXAMPLE_TEST_CLASS}}.{{EXAMPLE_TEST_METHOD}}"

{{#IF_RELEASE_SCRIPTS}}
# Release packaging
{{RELEASE_COMMANDS}}
{{/IF_RELEASE_SCRIPTS}}
```

## Architecture (WHY)

### Layers

```
┌──────────────────────────────────────┐
│           UI Layer                    │
│  Form*.cs / ViewModel*.cs            │
│  - Controles, dialogs, bindings      │
│  - UNICA camada com System.Windows.* │
├──────────────────────────────────────┤
│           Service Layer               │
│  *Service.cs                          │
│  - Logica de negocio, orquestracao   │
│  - Retorna Result<T>, sem UI         │
├──────────────────────────────────────┤
│           Domain Layer                │
│  POCOs, enums, value objects         │
│  - Sem dependencias de infra ou UI   │
├──────────────────────────────────────┤
│           Infrastructure              │
│  API clients, file I/O, hardware     │
│  - Implementa interfaces do Service  │
└──────────────────────────────────────┘
```

**Dependency direction:** UI → Service → Domain ← Infrastructure

### Key Patterns

{{PATTERNS_DESCRIPTION}}

### Data Flow

{{DATA_FLOW_DESCRIPTION}}

## Solution Projects

| Project | Purpose |
|---------|---------|
{{PROJECT_TABLE}}

## Canonical Code Examples

When implementing new code, follow these existing patterns:

- **New service class:** See `{{CANONICAL_SERVICE_PATH}}`
- **New test class:** See `{{CANONICAL_TEST_PATH}}`
- **New interface:** See `{{CANONICAL_INTERFACE_PATH}}`
{{#IF_DECOUPLING_SPEC}}
- **Decoupling roadmap:** See `{{DECOUPLING_SPEC_PATH}}`
{{/IF_DECOUPLING_SPEC}}

## Conventions

### Naming

{{NAMING_CONVENTIONS}}

### What NOT to Do

{{ANTI_PATTERNS_LIST}}

## Domain Glossary

{{DOMAIN_GLOSSARY}}
```

---

## Como Preencher as Variaveis

### Detectando automaticamente

Muitas variaveis podem ser extraidas do codebase:

| Variavel | Como detectar |
|----------|--------------|
| `{{SOLUTION_FILE}}` | `ls *.sln` na raiz |
| `{{TARGET_FRAMEWORK}}` | `grep TargetFramework *.csproj` no projeto principal |
| `{{TEST_PROJECT}}` | Projeto com `.Tests` no nome |
| `{{PROJECT_TABLE}}` | Parse do .sln — ListSection projetos |
| `{{DOMAIN_GLOSSARY}}` | Secao existente no CLAUDE.md ou termos frequentes no codigo |

### Requer input do usuario

| Variavel | Pergunte |
|----------|----------|
| `{{DESCRICAO_CURTA}}` | "Descreva o projeto em uma frase" |
| `{{PATTERNS_DESCRIPTION}}` | "Quais patterns o projeto usa? (Factory, Repository, CQRS...)" |
| `{{CANONICAL_*_PATH}}` | "Qual arquivo e o melhor exemplo de service/test/interface?" |
| `{{STATUS_MIGRACAO}}` | "A UI esta em migracao? De que para que?" |
| `{{ANTI_PATTERNS_LIST}}` | Combine com resultados da auditoria (Passo 1) |

---

## Melhorando CLAUDE.md Existente

Se o projeto ja tem CLAUDE.md, siga este checklist:

1. [ ] Tem secao de Build & Test com comandos exatos? Se nao, adicione
2. [ ] Tem descricao de arquitetura com camadas? Se nao, adicione
3. [ ] Lista anti-padroes especificos do projeto? Se nao, extraia da auditoria
4. [ ] Referencia codigo canonico? Se nao, identifique os melhores exemplos
5. [ ] Tem glossario de dominio? Se nao, extraia termos tecnicos do codigo
6. [ ] Esta abaixo de 300 linhas? Se nao, mova detalhes para .claude/rules/
7. [ ] Tem secao de convencoes de naming? Se nao, documente o padrao do projeto
8. [ ] Referencias de UI framework correspondem ao .csproj atual? (UseWPF vs UseWindowsForms, nomes de arquivos UI como Form*.cs vs MainWindow.xaml)

Apresente cada adicao como diff para o usuario aprovar.
