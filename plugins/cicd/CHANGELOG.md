# Changelog — cicd (Unificada)

Formato: [Semantic Versioning](https://semver.org/)

## [2.4.0] - 2026-05-05

### Adicionado

- Quick Troubleshooting: nova entrada `[S]` para `Missing script: "exec"` ao invocar binário em workspace de monorepo npm
- Quick Troubleshooting: nova entrada `[S]` para `ESLint couldn't find an eslint.config.(js|mjs|cjs) file` em workspace que migrou pra ESLint v9
- Lição #30: `npm run -w <ws> exec --` é sintaxe inválida — `exec` é subcomando do `npm`, não script de `package.json`
- Lição #31: ESLint v9 flat config é per-workspace, não herda de siblings
- `troubleshooting-shared.md` cenário 6: causa, occurrences comuns (tsc/playwright/openapi-typescript), fix e nota explícita sobre fail-fast mascarando steps subsequentes
- `troubleshooting-shared.md` cenário 7: snippet de flat config Node-only, diferenças vs config React, e nota sobre hoisting de devDeps em monorepo

### Motivação

PR #6 (`feat(005-production-deploy)`) tinha **8 jobs vermelhos** no CI. Investigando: 6 dos 8 vinham de uma única causa — sintaxe `npm run -w <ws> exec -- <cmd>` em 3 workflows (`ci.yml`, `cd-production.yml`, `frontend-ci.yml`). `npm run exec` busca um script chamado "exec" em `package.json`; não existindo, aborta com `Missing script: "exec"`. A sintaxe correta é `npm exec -w <ws> -- <cmd>` (sem `run`). Os outros 2 jobs falhavam por `ESLint couldn't find an eslint.config.(js|mjs|cjs) file` — workspaces `@validade-bateria/backend` e `@jrc/idp` declaravam `eslint ^9.0.0` sem `eslint.config.js` próprio, contando incorretamente com herança do flat config existente em `packages/frontend/`.

Bonus lição: o `Missing script: "exec"` é **fail-fast** — abortava em segundos no step de Typecheck, **mascarando** falhas pré-existentes nos steps subsequentes (44 testes frontend quebrados por interop msw/jsdom, type errors latentes em `auth-sanity.test.ts`, openapi codegen drift). Ao consertar a sintaxe, esses fails apareceram e foram inicialmente confundidos com regressões. Documentado no cenário 6.

---

## [2.3.0] - 2026-03-25

### Adicionado

- Quick Troubleshooting: nova entrada `[B]` para "Migration reports 'No pending migrations' but app crashes with missing column" (Docker image cache stale)
- Lição #29: `docker run` não faz auto-pull se a tag já existe localmente no self-hosted runner
- `troubleshooting-backend.md`: novo cenário "No pending migrations but app crashes" com diagnóstico, fix no workflow e recovery manual
- `troubleshooting-backend.md`: diagnosis flow atualizado com leaf de stale image cache no branch de deploy
- `checklist-backend.md`: seção 7 agora inclui `docker pull` antes do step de migration

### Motivação

Incidente em produção: CD workflow rodou `docker run ghcr.io/.../api:staging npx prisma migrate deploy` em self-hosted runner que tinha a imagem anterior em cache. O step de migration reportou "no pending migrations" (imagem antiga, N migrations) enquanto o container deployado (imagem nova, N+1 migrations) referenciava uma coluna que ainda não existia. Fix: sempre `docker pull` antes de `docker run` nos steps de migration.

---

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
