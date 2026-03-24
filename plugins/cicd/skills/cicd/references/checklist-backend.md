# Pre-Deploy Checklist — Backend (Node.js/Express/Prisma)

For shared sections (runner, GHCR, DNS/SSL, base networking), see `checklist-shared.md`.

---

## 1. GitHub Environment Secrets (12 per environment)

- [ ] `DATABASE_URL` — connection string with the correct prefix: `postgres://` for PostgreSQL (not `postgresql://`), `sqlserver://` for MSSQL/SQL Server
- [ ] `JWT_SECRET` — generate with `openssl rand -hex 32`
- [ ] `GOOGLE_CLIENT_ID` — OAuth2 client ID from the Google Cloud Console
- [ ] `GOOGLE_CLIENT_SECRET` — OAuth2 client secret
- [ ] `API_PORT` — application port (e.g., `3003`)
- [ ] `NODE_ENV` — `staging` or `production`
- [ ] `HOST_API` — `0.0.0.0` (to accept external connections in the container)
- [ ] `NGINX_NETWORK_NAME` — verify with `docker network ls | grep proxy`
- [ ] `GOOGLE_REDIRECT` — OAuth2 redirect URI (must include `https://`)
- [ ] `WEB_URL` — frontend URL (must include `https://`)
- [ ] `FINDVESSEL_API` — VesselFinder API URL (must include `https://`)
- [ ] `VIRTUAL_HOST` — subdomain for nginx-proxy routing

## 2. Env Vars for Tests (CI — Zod validation)

All variables that `src/env.ts` (Zod) validates must be present in the test step:

```yaml
env:
  DATABASE_URL: postgres://test_user:test_password@localhost:5432/test_db  # or sqlserver://... for MSSQL
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

> **Important:** For PostgreSQL, `DATABASE_URL` must use the `postgres://` prefix, not `postgresql://`. For MSSQL/SQL Server, use `sqlserver://`.

## 3. Docker Image Compatibility

- [ ] Service container uses the official image (e.g., `postgres:17`, not `bitnami/postgresql:17`)
- [ ] Container env vars match the image (e.g., `POSTGRES_USER`, not `POSTGRESQL_USERNAME`)
- [ ] Health check command is compatible (e.g., `pg_isready -U test_user -d test_db`)

## 4. Lint / Format

### ESLint + Prettier variant (projects without `biome.jsonc`)

- [ ] No pending warnings with `--max-warnings 0`
- [ ] `prettier` in `devDependencies` (not just the plugins)
- [ ] `yarn lint:check` passes without errors

### Biome variant (projects with `biome.jsonc`)

- [ ] `npx biome check .` passes without errors
- [ ] `files.includes` configured in `biome.jsonc` if needed to limit scope (e.g., `["src/**"]`)
- [ ] No errors in config files (Biome checks all files by default)

## 5. Tests

> **If the project does NOT have a test framework configured** (neither Jest nor Vitest), skip test steps in CI and CD. Do not add empty or placeholder test steps.

### Jest variant (projects with Jest configured)

- [ ] `node --max-old-space-size=4096` configured to prevent OOM
- [ ] `--forceExit` to ensure Jest terminates
- [ ] All imports with correct case (Linux is case-sensitive)
- [ ] `jest.mock()` paths with correct case
- [ ] `server.ts` does not start the listener when `NODE_ENV=test`
- [ ] Integration tests insert seed data in `beforeAll`
- [ ] No `continue-on-error` in test steps

## 6. Build

- [ ] `tsc` with `--skipLibCheck` (Prisma client compatibility)
- [ ] `prisma generate` executed before the build
- [ ] Path aliases resolved via `tsc-alias` (`build_prod` script)

## 7. CD Staging/Production Workflow

- [ ] `docker/login-action@v3` in the `build-and-push` job with `GITHUB_TOKEN`
- [ ] `docker/login-action@v3` in the `deploy` job before `docker compose pull`
- [ ] Generate .env with all environment secrets
- [ ] `prisma migrate deploy` before `docker compose up`
- [ ] Correct compose path for the project (e.g., `infra/nodejs/`, `infra/`, etc.)
- [ ] `docker image prune -f` in cleanup
- [ ] Cleanup .env with `if: always()`
- [ ] Permissions: `packages: write, contents: read`

## 8. nginx-proxy Network (Backend-Specific)

- [ ] `VIRTUAL_PORT: '${API_PORT}'` in docker-compose.yml (required when `API_PORT` is not 80)
- [ ] No `ports:` in the staging/production compose (nginx-proxy routes internally)
