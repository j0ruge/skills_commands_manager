# Changelog — deploy-staging

Formato: [Semantic Versioning](https://semver.org/)

## [1.2.0] - 2026-03-13

### Adicionado

- Detecção automática de cenário: branch atual `develop` vs feature branch
- Fluxo simplificado quando já em `develop`: sincroniza main com `origin/develop` (ff-only), pusha commits locais e pula direto para verificação de pipeline
- Steps 6-8 preservados como fluxo completo para feature branches

### Motivação

Quando o usuário já está em `develop`, os passos de merge de feature branch são desnecessários. O fluxo simplificado evita checkouts e merges redundantes.

---

## [1.1.0] - 2026-03-13

### Adicionado

- Passo pre-flight: `eslint --max-warnings 0`, `tsc --noEmit`, `vitest run` antes do push
- Aborta o fluxo se qualquer verificação local falhar, evitando falhas no pipeline remoto

### Motivação

Deploy `23060872731` falhou por warning ESLint (`react-refresh/only-export-components`) que teria sido pego localmente.

---

## [1.0.0] - 2026-03-13

### Adicionado

- Workflow completo: verificar working tree → fetch → sincronizar main com develop → merge feature → push develop → verificar pipeline
- Sincronização automática de `main` com `origin/develop` via fast-forward
- Verificação de pipeline via `gh run list`
- Notas sobre CD staging (GHCR `:staging`, self-hosted runner)
