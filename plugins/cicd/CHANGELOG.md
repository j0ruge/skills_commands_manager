# Changelog — cicd (Unificada)

Formato: [Semantic Versioning](https://semver.org/)

## [2.2.0] - 2026-03-18

### Adicionado

- Detecção de projeto Biome: `biome.jsonc` / `biome.json` → **Backend (Biome)** na tabela de detecção
- Variante CI para Backend (Biome): `checkout → install → [prisma generate] → biome check → [test if configured]`
- 2 entradas na Quick Troubleshooting table: `npx biome check .` em arquivos de config e Biome 2.x `unknown key "ignore"`
- Lição #27: Biome verifica todos os arquivos por padrão — scoping com `files.includes`
- Lição #28: Primeiro deploy requer workflows no branch `develop`
- `troubleshooting-backend.md`: 2 cenários de troubleshooting Biome (escopo de arquivos e migração 2.x)
- `checklist-backend.md`: variante Biome na seção de Lint/Format; nota sobre `DATABASE_URL` com `sqlserver://` para MSSQL
- `checklist-backend.md`: seção de testes agora cobre cenário "sem test framework" — pular steps de teste
- `checklist-shared.md`: seção 5 "Primeiro Deploy (Bootstrap)" com checklist e comandos para criar branch `develop`

### Alterado

- Compose path na tabela de deploy agora indica "varia por projeto" em vez de hardcoded `infra/nodejs/`
- Tabela de arquivos do pipeline backend usa paths genéricos (`Dockerfile` ou `infra/*/Dockerfile`)
- Comando de rollback backend usa `<COMPOSE_PATH>` genérico
- `checklist-backend.md`: seção 7 (Workflow CD) inclui verificação de compose path
- Versão: 2.1.0 → 2.2.0

### Motivação

Deploy de `estimates_api` (npm, Biome, SQL Server/MSSQL, sem testes) para staging revelou 6 gaps na skill v2.1.0 que foi construída a partir de projetos ESLint+Prettier+PostgreSQL+Jest. A skill agora suporta múltiplas variantes de stack backend.

---

## [2.1.0] - 2026-03-16

### Alterado

- GHCR login no deploy padronizado como `docker/login-action@v3` em ambos os projetos (era `[F]`-only, agora `[S]`)
- Tabela "Diferenças no Deploy": backend agora usa `docker/login-action@v3` (antes era "Não necessário")
- `troubleshooting-shared.md`: cenário #1 reescrito — causa raiz atualizada para contexto isolado entre jobs, solução agora recomenda `docker/login-action@v3` sobre `docker login` manual
- `checklist-shared.md`: item GHCR atualizado para recomendar `docker/login-action@v3` com justificativa (logout automático, config isolada, masking)
- `checklist-backend.md`: adicionada seção 7 (Workflow CD) com checklist de login, generate .env, migrations e cleanup

### Motivação

Backend API falhava no Deploy Staging com `denied` no GHCR pull — o job Deploy não tinha login. Padronizado `docker/login-action@v3` nos 4 workflows (API staging/prod + frontend staging/prod). A action é preferível ao `docker login` manual em self-hosted runners por cleanup automático de credenciais.

---

## [2.0.0] - 2026-03-12

### Adicionado

- Skill unificada backend + frontend com progressive disclosure
- Detecção automática de projeto (Prisma → backend, Vite → frontend)
- Quick troubleshooting table unificada com tags `[B]`/`[F]`/`[S]` (21 entradas)
- Tabela de roteamento para 7 arquivos de referência
- Tabela de lições aprendidas unificada (26 lições com tags)
- `references/troubleshooting-shared.md` — 5 cenários de infra compartilhados
- `references/checklist-shared.md` — 4 seções compartilhadas (runner, GHCR, DNS, rede)
- `references/troubleshooting-backend.md` — exit codes, Zod, Prisma, VIRTUAL_PORT, diagnóstico
- `references/checklist-backend.md` — 7 seções (secrets, Zod CI vars, Docker, lint, Jest, build, rede)
- `references/test-fixes-backend.md` — 8 padrões de correção de testes Jest
- `references/troubleshooting-frontend.md` — Vite, SPA, nginx, Alpine, diagnóstico
- `references/checklist-frontend.md` — 6 seções (VITE_* secrets, Dockerfile, compose, CI, CD, build files)
- Comandos úteis com templates por projeto (compose path difere)
- Tabela de arquivos do pipeline separada por projeto

### Removido

- `references/troubleshooting.md` (conteúdo distribuído em troubleshooting-shared/backend/frontend)
- `references/github-actions-checklist.md` (conteúdo distribuído em checklist-shared/backend/frontend)
- `references/test-fixes.md` (renomeado para test-fixes-backend.md)

### Alterado

- SKILL.md agora é entry point fino (~230 linhas) que roteia para referências on-demand
- Conteúdo duplicado entre backend e frontend eliminado via arquivos shared
- Versão: 1.x.0 (separadas) → 2.0.0 (unificada)

---

## Histórico Pré-Unificação

### Frontend (v1.0.0 → v1.1.0)

- **v1.1.0**: 5 lições do deploy real (healthcheck, vite.config.ts, Vitest E2E, treeshake, GHCR login)
- **v1.0.0**: SKILL.md com 10 lições, troubleshooting (9 cenários), checklist (8 seções)

### Backend (v1.0.0 → v1.6.0)

- **v1.6.0**: ERR_SSL_VERSION_OR_CIPHER_MISMATCH, DNS/SSL troubleshooting
- **v1.5.0**: Port mapping desnecessário com nginx-proxy
- **v1.4.0**: VIRTUAL_PORT obrigatório para nginx-proxy
- **v1.3.0**: Secrets com `z.string().url()` devem incluir `https://`
- **v1.2.0**: Variáveis Zod no Generate .env do CD
- **v1.1.0**: GHCR auth sudo/user, rede nginx-proxy variável, lint pré-push, re-trigger
- **v1.0.0**: SKILL.md com 14 lições, troubleshooting (exit codes + 12 cenários), test-fixes (8 padrões), checklist (10 seções)
