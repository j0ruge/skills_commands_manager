---
name: cicd
metadata:
  version: 2.2.0
description: |
  Troubleshooting e configuração de pipelines CI/CD com GitHub Actions, Docker, GHCR e self-hosted runners.
  Skill unificada — detecta automaticamente backend (Prisma) ou frontend (Vite) e roteia para referências específicas.
  Triggers: "CI/CD", "pipeline", "GitHub Actions", "workflow", "CI failing", "build failed",
  "deploy", "staging", "production", "docker build", "GHCR", "self-hosted runner",
  "gh run", "workflow dispatch", "secrets", "environment secrets"
---

# CI/CD Skill — GitHub Actions, Docker & GHCR (Unificada)

Skill para troubleshooting e configuração de pipelines CI/CD. Detecta o tipo de projeto e roteia para referências específicas.

---

## Detecção de Projeto

| Indicador                   | Projeto               |
| --------------------------- | --------------------- |
| `prisma/schema.prisma`      | **Backend**           |
| `biome.jsonc` / `biome.json`| **Backend (Biome)**   |
| `vite.config.ts`            | **Frontend**          |

> **Linter detection:** Se o projeto tem `biome.jsonc` (ou `biome.json`), usa Biome para lint/format. Caso contrário, assume ESLint+Prettier. Projetos Biome NÃO usam ESLint nem Prettier.

> Verificar qual projeto antes de consultar referências. Cenários marcados `[S]` são compartilhados, `[B]` backend-only, `[F]` frontend-only.

---

## Workflow Overview

Ambos os projetos usam **3 workflows separados** com triggers idênticos:

| Workflow          | Arquivo             | Trigger                  | Runners                                     |
| ----------------- | ------------------- | ------------------------ | ------------------------------------------- |
| **CI**            | `ci.yml`            | PR → `develop` ou `main` | `ubuntu-latest`                             |
| **CD Staging**    | `cd-staging.yml`    | Push → `develop`         | `ubuntu-latest` + `self-hosted, staging`    |
| **CD Production** | `cd-production.yml` | Tag `v*`                 | `ubuntu-latest` + `self-hosted, production` |

### Diferenças no CI

```text
Backend (ESLint):  checkout → install → prisma generate → lint → prettier → migrate → test (Jest)
Backend (Biome):   checkout → install → [prisma generate] → biome check → [test if configured]
Frontend:          checkout → install → lint → typecheck → test (Vitest)
```

> **Nota:** `[prisma generate]` e `[test]` são opcionais — dependem do projeto ter Prisma e um test framework configurado, respectivamente. Projetos sem test framework (ex: `estimates_api`) pulam o step de teste no CI e CD.

### Diferenças no Deploy

| Aspecto              | Backend                                    | Frontend                                      |
| -------------------- | ------------------------------------------ | --------------------------------------------- |
| Build-args           | Não precisa de `environment:` no build job | `environment:` obrigatório (VITE_* secrets)   |
| Imagem               | Genérica (mesma para todos os envs)        | Environment-specific (VITE_* embeddadas no JS)|
| Migration            | `prisma migrate deploy` antes do `up`      | Sem migration                                 |
| `VIRTUAL_PORT`       | Obrigatório (`API_PORT` ≠ 80)             | Não necessário (nginx = porta 80)             |
| GHCR login no deploy | `docker/login-action@v3` antes do pull     | `docker/login-action@v3` antes do pull        |
| Prune                | `docker image prune -f`                    | `docker image prune -f --filter "label=..."`  |
| Compose path         | Varia por projeto (ex: `infra/nodejs/`, `infra/`) | `infra/dsr_web/docker-compose.yml`            |

### Concurrency & Auth

- **CI:** `ci-${{ github.ref }}` com `cancel-in-progress: true`
- **CD:** `deploy-{staging|production}-<project>` com `cancel-in-progress: false`
- **GHCR:** `GITHUB_TOKEN` (automático) via `docker/login-action@v3` — sem PAT

---

## Quick Troubleshooting

| Tag   | Sintoma                                                | Causa Provável                                       | Solução                                                                               |
| ----- | ------------------------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `[S]` | `unauthorized` no docker pull (self-hosted)            | Docker login em contexto diferente (sudo vs user)    | `docker login ghcr.io` no mesmo contexto que executa o pull                           |
| `[S]` | `network declared as external, but could not be found` | Nome da rede nginx-proxy incorreto no secret         | `docker network ls \| grep proxy` e corrigir `NGINX_NETWORK_NAME`                     |
| `[S]` | `ERR_SSL_VERSION_OR_CIPHER_MISMATCH`                   | DNS não aponta para o servidor                       | `dig dominio +short` deve resolver para o IP do servidor                              |
| `[S]` | Deploy queued indefinidamente                          | Self-hosted runner offline                           | `systemctl status actions.runner.*` no servidor                                       |
| `[S]` | Deploy blocked                                         | Concurrency group com run anterior                   | Aguardar ou cancelar run anterior via `gh run cancel`                                 |
| `[S]` | `--max-warnings 0` falha no ESLint                     | Warnings pré-existentes                              | Corrigir warnings ou usar `eslint-disable`                                            |
| `[B]` | `manifest unknown` no service container                | Imagem Docker descontinuada                          | Trocar para imagem oficial (ex: `postgres:17`)                                        |
| `[B]` | Zod validation error no boot                           | Env vars faltantes no CI ou no Generate .env         | Comparar `src/env.ts` com bloco `env:` dos testes e `printf` do CD                   |
| `[B]` | `ZodError invalid_string`                              | Secret URL sem protocolo `https://`                  | Verificar formato do secret                                                           |
| `[B]` | Testes passam local, falham no CI                      | Case-sensitivity em imports (Linux)                  | Corrigir case do arquivo ou import                                                    |
| `[B]` | `FATAL ERROR: heap limit` / Exit 134                   | Jest OOM                                             | `node --max-old-space-size=4096`                                                      |
| `[B]` | `EADDRINUSE` nos testes                                | `server.ts` chama `app.listen()` em test             | Guard `NODE_ENV !== 'test'`                                                           |
| `[B]` | `ERR_CONNECTION_REFUSED` (nginx-proxy OK)              | `VIRTUAL_PORT` não definido no compose               | Adicionar `VIRTUAL_PORT: '${API_PORT}'`                                               |
| `[B]` | Erros de tipo `tsc` (Prisma client)                    | `--skipLibCheck` ausente                             | Adicionar `--skipLibCheck` ao `tsc`                                                   |
| `[F]` | Página em branco (SPA não carrega)                     | VITE_* faltando ou `vite.config.ts` ausente          | Verificar ARGs no Dockerfile e build-args no workflow                                 |
| `[F]` | `VITE_API_URL` = `undefined` no JS                     | VITE_* não passadas como build-arg                   | Verificar `build-args` no `docker/build-push-action`                                  |
| `[F]` | 404 em rotas do React Router                           | nginx `try_files` não configurado                    | `try_files $uri $uri/ /index.html` no nginx.conf                                     |
| `[F]` | `Cannot access 'X' before initialization`              | `treeshake.moduleSideEffects` + circular chunks      | Remover `treeshake` e `manualChunks` do vite.config.ts                                |
| `[F]` | Container `unhealthy` (healthcheck falha)              | Alpine resolve `localhost` como IPv6                 | Usar `127.0.0.1` no healthcheck                                                      |
| `[F]` | Vitest coletando testes E2E Playwright                 | `vitest.config.ts` sem exclude de `e2e/`             | Adicionar `exclude: ['e2e/**']`                                                       |
| `[B]` | `npx biome check .` falha em arquivos de config        | Biome verifica todos os arquivos por padrão          | Usar `files.includes` em `biome.jsonc` para escopo ou corrigir os arquivos            |
| `[B]` | Biome 2.x config error (`unknown key "ignore"`)       | Biome 2.x removeu `ignore` em favor de `includes`   | Usar `files.includes` em vez de `files.ignore` no `biome.jsonc`                       |
| `[F]` | Container nginx retorna 403                            | dist/ vazio ou não copiado                           | Verificar `npm run build` e `COPY --from=build` no Dockerfile                         |

---

## Tabela de Roteamento — Referências Detalhadas

| Categoria do Problema                         | Referência                                   |
| --------------------------------------------- | -------------------------------------------- |
| Infra compartilhada (GHCR, rede, SSL, runner) | `references/troubleshooting-shared.md`       |
| Checklist compartilhado (runner, GHCR, DNS)   | `references/checklist-shared.md`             |
| Troubleshooting backend (Zod, Prisma, Jest)   | `references/troubleshooting-backend.md`      |
| Checklist backend (secrets, testes, build)     | `references/checklist-backend.md`            |
| Padrões de correção de testes Jest            | `references/test-fixes-backend.md`           |
| Troubleshooting frontend (Vite, SPA, nginx)   | `references/troubleshooting-frontend.md`     |
| Checklist frontend (VITE_*, Dockerfile, CD)   | `references/checklist-frontend.md`           |

---

## Lições Aprendidas (Resumo)

| # | Tag   | Lição | Contexto |
|---|-------|-------|----------|
| 1 | `[S]` | GHCR auth: contexto sudo vs user | `~/.docker/config.json` é per-user |
| 2 | `[S]` | Nome da rede nginx-proxy varia por instalação | Verificar com `docker network ls` |
| 3 | `[S]` | Secrets URL devem incluir `https://` | Zod `z.string().url()` rejeita sem protocolo |
| 4 | `[S]` | Port mapping desnecessário com nginx-proxy | Sem `ports:` no compose de staging/prod |
| 5 | `[S]` | DNS deve apontar para o IP do servidor | Let's Encrypt precisa de HTTP-01 challenge |
| 6 | `[S]` | Concurrency groups bloqueiam deploys | `cancel-in-progress: false` enfileira |
| 7 | `[S]` | Lint local antes de push para develop | Push dispara CD; erros desperdiçam ciclos |
| 8 | `[S]` | Re-trigger sem `workflow_dispatch` | `gh run rerun` ou `git commit --allow-empty` |
| 9 | `[B]` | Imagem `bitnami/postgresql` descontinuada | Usar `postgres:17` com `POSTGRES_USER` |
| 10 | `[B]` | `--skipLibCheck` necessário no build | Prisma client gera tipos conflitantes |
| 11 | `[B]` | Prettier não instalado como dependência | Precisa ser devDependency explícita |
| 12 | `[B]` | Validação Zod falha no CI | Todas as vars do `src/env.ts` no step de teste |
| 13 | `[B]` | `DATABASE_URL` com prefixo errado | Zod do projeto exige `postgres://` |
| 14 | `[B]` | Vars Zod no Generate .env do CD | Atualizar CI e CD ao adicionar var no Zod |
| 15 | `[B]` | `VIRTUAL_PORT` obrigatório para porta ≠ 80 | nginx-proxy default é 80 |
| 16 | `[B]` | `continue-on-error` é paliativo | Usar apenas temporariamente |
| 17 | `[B]` | `server.ts` guard para `NODE_ENV=test` | Evita `EADDRINUSE` nos testes |
| 18 | `[F]` | VITE_* são build-time, não runtime | Env vars no container nginx não têm efeito |
| 19 | `[F]` | Imagem Docker é environment-specific | Staging e prod são imagens diferentes |
| 20 | `[F]` | `build-and-push` precisa de `environment:` | Para acessar VITE_* secrets como build-args |
| 21 | `[F]` | Sem `VIRTUAL_PORT` para nginx | nginx escuta na porta 80 (default) |
| 22 | `[F]` | Healthcheck Alpine: `127.0.0.1` | `localhost` pode resolver para `::1` (IPv6) |
| 23 | `[F]` | `vite.config.ts` deve estar versionado | Sem ele, bundle sem plugin React → página branca |
| 24 | `[F]` | Vitest coletando testes E2E Playwright | `vitest.config.ts` com `exclude: ['e2e/**']` |
| 25 | `[F]` | `treeshake.moduleSideEffects` + circular chunks | Remover treeshake e manualChunks customizados |
| 26 | `[S]` | GHCR login necessário no deploy job | `docker/login-action@v3` antes do pull (ambos os projetos) |
| 27 | `[B]` | Biome verifica todos os arquivos por padrão | Usar `files.includes` em `biome.jsonc` para limitar escopo ao `src/` ou corrigir arquivos de config |
| 28 | `[S]` | Primeiro deploy requer workflows no branch `develop` | CD Staging triggera em push para `develop` — workflows devem estar nesse branch antes do primeiro push |

---

## Comandos Úteis

```bash
# Ver status dos workflows
gh run list --limit 5

# Ver logs de um run específico
gh run view <run-id> --log-failed

# Re-executar um workflow falhado
gh run rerun <run-id>

# Listar secrets de um environment
gh secret list --env staging

# Verificar imagens no GHCR
gh api orgs/JRC-Brasil/packages/container/<PACKAGE_NAME>/versions
```

### Backend

```bash
# Rollback manual (path do compose varia por projeto)
export IMAGE_TAG=<tag-anterior>
docker compose -f <COMPOSE_PATH>/docker-compose.yml pull
docker compose -f <COMPOSE_PATH>/docker-compose.yml up -d --force-recreate
```

### Frontend

```bash
# Rollback manual
export IMAGE_TAG=<tag-anterior>
docker compose -f infra/dsr_web/docker-compose.yml pull
docker compose -f infra/dsr_web/docker-compose.yml up -d --force-recreate

# Verificar VITE_* embeddadas no JS
docker exec service_report_web sh -c "grep -r 'jrcbrasil' /usr/share/nginx/html/assets/*.js | head -5"
```

---

## Arquivos do Pipeline

### Backend

| Arquivo                               | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| `.github/workflows/ci.yml`            | Pipeline CI (lint + test) para PRs      |
| `.github/workflows/cd-staging.yml`    | Pipeline CD para staging (push develop) |
| `.github/workflows/cd-production.yml` | Pipeline CD para produção (tags v\*)    |
| `Dockerfile` ou `infra/*/Dockerfile`  | Multi-stage build (path varia por projeto) |
| `infra/*/docker-compose.yml`          | Compose com imagem GHCR (path varia)   |
| `src/env.ts`                          | Validação Zod de env vars               |

### Frontend

| Arquivo                               | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| `.github/workflows/ci.yml`            | Pipeline CI (lint + typecheck + test)   |
| `.github/workflows/cd-staging.yml`    | Pipeline CD para staging (push develop) |
| `.github/workflows/cd-production.yml` | Pipeline CD para produção (tags v\*)    |
| `infra/dsr_web/Dockerfile`            | Multi-stage build (node + nginx)        |
| `infra/dsr_web/docker-compose.yml`    | Compose com imagem GHCR                 |
| `infra/dsr_web/nginx.conf`            | nginx config (SPA try_files)            |
