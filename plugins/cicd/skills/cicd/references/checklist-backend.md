# Checklist Pré-Deploy — Backend (Node.js/Express/Prisma)

Para seções compartilhadas (runner, GHCR, DNS/SSL, rede base), ver `checklist-shared.md`.

---

## 1. GitHub Environment Secrets (12 por environment)

- [ ] `DATABASE_URL` — connection string com prefixo correto: `postgres://` para PostgreSQL (não `postgresql://`), `sqlserver://` para MSSQL/SQL Server
- [ ] `JWT_SECRET` — gerar com `openssl rand -hex 32`
- [ ] `GOOGLE_CLIENT_ID` — OAuth2 client ID do Google Cloud Console
- [ ] `GOOGLE_CLIENT_SECRET` — OAuth2 client secret
- [ ] `API_PORT` — porta da aplicação (ex: `3003`)
- [ ] `NODE_ENV` — `staging` ou `production`
- [ ] `HOST_API` — `0.0.0.0` (para aceitar conexões externas no container)
- [ ] `NGINX_NETWORK_NAME` — verificar com `docker network ls | grep proxy`
- [ ] `GOOGLE_REDIRECT` — OAuth2 redirect URI (deve incluir `https://`)
- [ ] `WEB_URL` — URL do frontend (deve incluir `https://`)
- [ ] `FINDVESSEL_API` — URL da API VesselFinder (deve incluir `https://`)
- [ ] `VIRTUAL_HOST` — subdomínio para nginx-proxy routing

## 2. Env Vars para Testes (CI — Zod validation)

Todas as variáveis que `src/env.ts` (Zod) valida devem estar no step de teste:

```yaml
env:
  DATABASE_URL: postgres://test_user:test_password@localhost:5432/test_db  # ou sqlserver://... para MSSQL
  API_PORT: 3003
  JWT_SECRET: ci-test-jwt-secret
  NODE_ENV: test
  HOST_API: localhost
  WEB_URL: http://localhost:3000
  FINDVESSEL_API: http://localhost:4000
  GOOGLE_CLIENT_ID: test-client-id
  GOOGLE_CLIENT_SECRET: test-client-secret
  GOOGLE_REDIRECT: http://localhost:3000/auth/callback
```

> **Importante:** Para PostgreSQL, `DATABASE_URL` deve usar prefixo `postgres://`, não `postgresql://`. Para MSSQL/SQL Server, usar `sqlserver://`.

## 3. Docker Image Compatibility

- [ ] Service container usa imagem oficial (ex: `postgres:17`, não `bitnami/postgresql:17`)
- [ ] Env vars do container correspondem à imagem (ex: `POSTGRES_USER`, não `POSTGRESQL_USERNAME`)
- [ ] Health check command é compatível (ex: `pg_isready -U test_user -d test_db`)

## 4. Lint / Format

### Variante ESLint + Prettier (projetos sem `biome.jsonc`)

- [ ] Sem warnings pendentes com `--max-warnings 0`
- [ ] `prettier` em `devDependencies` (não apenas os plugins)
- [ ] `yarn lint:check` passa sem erros

### Variante Biome (projetos com `biome.jsonc`)

- [ ] `npx biome check .` passa sem erros
- [ ] `files.includes` configurado em `biome.jsonc` se necessário para limitar escopo (ex: `["src/**"]`)
- [ ] Sem erros em arquivos de config (Biome verifica todos os arquivos por padrão)

## 5. Testes

> **Se o projeto NÃO tem test framework configurado** (nem Jest, nem Vitest), pular steps de teste no CI e CD. Não adicionar steps de teste vazios ou placeholders.

### Variante Jest (projetos com Jest configurado)

- [ ] `node --max-old-space-size=4096` configurado para evitar OOM
- [ ] `--forceExit` para garantir que Jest termina
- [ ] Todos os imports com case correto (Linux é case-sensitive)
- [ ] `jest.mock()` paths com case correto
- [ ] `server.ts` não inicia listener quando `NODE_ENV=test`
- [ ] Testes de integração inserem seed data em `beforeAll`
- [ ] Sem `continue-on-error` nos steps de teste

## 6. Build

- [ ] `tsc` com `--skipLibCheck` (compatibilidade Prisma client)
- [ ] `prisma generate` executado antes do build
- [ ] Path aliases resolvidos via `tsc-alias` (script `build_prod`)

## 7. Workflow CD Staging/Production

- [ ] `docker/login-action@v3` no job `build-and-push` com `GITHUB_TOKEN`
- [ ] `docker/login-action@v3` no job `deploy` antes do `docker compose pull`
- [ ] Generate .env com todos os secrets do environment
- [ ] `prisma migrate deploy` antes do `docker compose up`
- [ ] Compose path correto para o projeto (ex: `infra/nodejs/`, `infra/`, etc.)
- [ ] `docker image prune -f` no cleanup
- [ ] Cleanup .env com `if: always()`
- [ ] Permissions: `packages: write, contents: read`

## 8. Rede nginx-proxy (Backend-Específico)

- [ ] `VIRTUAL_PORT: '${API_PORT}'` no docker-compose.yml (obrigatório quando `API_PORT` ≠ 80)
- [ ] Sem `ports:` no compose de staging/produção (nginx-proxy roteia internamente)
