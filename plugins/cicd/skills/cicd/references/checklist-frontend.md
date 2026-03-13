# Checklist Pré-Deploy — Frontend (React/Vite/nginx)

Para seções compartilhadas (runner, GHCR, DNS/SSL, rede base), ver `checklist-shared.md`.

---

## 1. GitHub Environment Secrets (13 por environment)

**Build-time (VITE_* — 11 secrets):**

- [ ] `VITE_API_URL` — URL da API principal (com `https://`)
- [ ] `VITE_API_AUTH` — URL da API de autenticação (com `https://`)
- [ ] `VITE_API_PORT` — Porta da API
- [ ] `VITE_HOST_WEB` — Hostname do frontend
- [ ] `VITE_PORT_WEB` — Porta do frontend
- [ ] `VITE_GOOGLE_CLIENT_ID` — Google OAuth client ID
- [ ] `VITE_GOOGLE_DRIVE_LINK` — Link do Google Drive
- [ ] `VITE_DOCUMENTATION_LINK` — Link da documentação
- [ ] `VITE_API_ESTIMATES` — URL da API Estimates (com `https://`)
- [ ] `VITE_API_FENIX` — URL da API Fenix (com `https://`)
- [ ] `VITE_NODE_ENV` — `staging` ou `production`

**Deploy-time (2 secrets):**

- [ ] `NGINX_NETWORK_NAME` — verificar com `docker network ls | grep proxy`
- [ ] `VIRTUAL_HOST` — subdomínio para nginx-proxy

## 2. Dockerfile Multi-Stage

- [ ] Build stage: `node:22-alpine`
- [ ] ARG para cada VITE_* (11 ARGs)
- [ ] `yarn install --frozen-lockfile`
- [ ] `npm run build` (tsc + vite build)
- [ ] Runtime stage: `nginx:alpine`
- [ ] `COPY --from=build /app/dist /usr/share/nginx/html`
- [ ] `COPY infra/dsr_web/nginx.conf /etc/nginx/nginx.conf`

## 3. Docker Compose (staging/produção)

- [ ] `image: ghcr.io/jrc-brasil/digital_service_report_frontend:${IMAGE_TAG}`
- [ ] `container_name: service_report_web`
- [ ] Sem `ports:` (nginx-proxy roteia internamente)
- [ ] Sem `env_file:` (VITE_* já estão no JS)
- [ ] Sem `VIRTUAL_PORT` (nginx = porta 80 = default)
- [ ] `VIRTUAL_HOST` e `LETSENCRYPT_HOST` no environment
- [ ] Rede `nginx-proxy` external com `name: ${NGINX_NETWORK_NAME}`
- [ ] `healthcheck` com wget no `http://127.0.0.1:80/index.html` (não `localhost`)
- [ ] `restart: unless-stopped`

## 4. Workflow CI (`ci.yml`)

- [ ] Trigger: `pull_request` em `develop` e `main`
- [ ] Jobs: `lint`, `typecheck`, `test`
- [ ] Node.js 22.15.0 via `actions/setup-node@v4`
- [ ] `yarn install --frozen-lockfile`
- [ ] ESLint com `--max-warnings 0`
- [ ] TypeScript com `tsc --noEmit`
- [ ] Vitest com `npx vitest run`
- [ ] `timeout-minutes: 10` em todos os jobs
- [ ] Concurrency: `ci-${{ github.ref }}` com `cancel-in-progress: true`

## 5. Workflow CD Staging/Production

- [ ] Job `build-and-push` com `environment:` (necessário para acessar VITE_* secrets)
- [ ] `docker/login-action@v3` com `GITHUB_TOKEN`
- [ ] `docker/build-push-action@v6` com `build-args` (11 VITE_*)
- [ ] `timeout-minutes` em todos os jobs (CI: 10, build: 15, deploy: 10)
- [ ] GHCR login no deploy job (`docker/login-action@v3`) — antes do pull
- [ ] Generate .env com `NGINX_NETWORK_NAME`, `VIRTUAL_HOST`, `IMAGE_TAG`
- [ ] `docker compose pull && docker compose up -d --force-recreate`
- [ ] `docker image prune -f --filter "label=org.opencontainers.image.source=..."` — filtrar por label
- [ ] Cleanup .env com `if: always()`
- [ ] Permissions: `packages: write, contents: read`

**Staging:** Tag `:staging`, deploy em `[self-hosted, staging]`
**Production:** Tags `:${{ github.ref_name }}` + `:latest`, deploy em `[self-hosted, production]`

## 6. Arquivos de Build Versionados

- [ ] `vite.config.ts` no git (não no `.gitignore`) — sem ele, build gera bundle sem plugin React → página branca
- [ ] `vitest.config.ts` no git com `exclude: ['e2e/**']` — sem ele, Vitest coleta testes Playwright
