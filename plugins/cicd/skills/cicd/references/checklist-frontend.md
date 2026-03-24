# Pre-Deploy Checklist — Frontend (React/Vite/nginx)

For shared sections (runner, GHCR, DNS/SSL, base networking), see `checklist-shared.md`.

---

## 1. GitHub Environment Secrets (13 per environment)

**Build-time (VITE_* — 11 secrets):**

- [ ] `VITE_API_URL` — main API URL (with `https://`)
- [ ] `VITE_API_AUTH` — authentication API URL (with `https://`)
- [ ] `VITE_API_PORT` — API port
- [ ] `VITE_HOST_WEB` — frontend hostname
- [ ] `VITE_PORT_WEB` — frontend port
- [ ] `VITE_GOOGLE_CLIENT_ID` — Google OAuth client ID
- [ ] `VITE_GOOGLE_DRIVE_LINK` — Google Drive link
- [ ] `VITE_DOCUMENTATION_LINK` — documentation link
- [ ] `VITE_API_ESTIMATES` — Estimates API URL (with `https://`)
- [ ] `VITE_API_FENIX` — Fenix API URL (with `https://`)
- [ ] `VITE_NODE_ENV` — `staging` or `production`

**Deploy-time (2 secrets):**

- [ ] `NGINX_NETWORK_NAME` — verify with `docker network ls | grep proxy`
- [ ] `VIRTUAL_HOST` — subdomain for nginx-proxy

## 2. Multi-Stage Dockerfile

- [ ] Build stage: `node:22-alpine`
- [ ] ARG for each VITE_* (11 ARGs)
- [ ] `yarn install --frozen-lockfile`
- [ ] `npm run build` (tsc + vite build)
- [ ] Runtime stage: `nginx:alpine`
- [ ] `COPY --from=build /app/dist /usr/share/nginx/html`
- [ ] `COPY infra/dsr_web/nginx.conf /etc/nginx/nginx.conf`

## 3. Docker Compose (staging/production)

- [ ] `image: ghcr.io/jrc-brasil/digital_service_report_frontend:${IMAGE_TAG}`
- [ ] `container_name: service_report_web`
- [ ] No `ports:` (nginx-proxy routes internally)
- [ ] No `env_file:` (VITE_* are already in the JS)
- [ ] No `VIRTUAL_PORT` (nginx = port 80 = default)
- [ ] `VIRTUAL_HOST` and `LETSENCRYPT_HOST` in environment
- [ ] `nginx-proxy` network external with `name: ${NGINX_NETWORK_NAME}`
- [ ] `healthcheck` with wget on `http://127.0.0.1:80/index.html` (not `localhost`)
- [ ] `restart: unless-stopped`

## 4. CI Workflow (`ci.yml`)

- [ ] Trigger: `pull_request` on `develop` and `main`
- [ ] Jobs: `lint`, `typecheck`, `test`
- [ ] Node.js 22.15.0 via `actions/setup-node@v4`
- [ ] `yarn install --frozen-lockfile`
- [ ] ESLint with `--max-warnings 0`
- [ ] TypeScript with `tsc --noEmit`
- [ ] Vitest with `npx vitest run`
- [ ] `timeout-minutes: 10` on all jobs
- [ ] Concurrency: `ci-${{ github.ref }}` with `cancel-in-progress: true`

## 5. CD Staging/Production Workflow

- [ ] `build-and-push` job with `environment:` (required to access VITE_* secrets)
- [ ] `docker/login-action@v3` with `GITHUB_TOKEN`
- [ ] `docker/build-push-action@v6` with `build-args` (11 VITE_*)
- [ ] `timeout-minutes` on all jobs (CI: 10, build: 15, deploy: 10)
- [ ] GHCR login in the deploy job (`docker/login-action@v3`) — before the pull
- [ ] Generate .env with `NGINX_NETWORK_NAME`, `VIRTUAL_HOST`, `IMAGE_TAG`
- [ ] `docker compose pull && docker compose up -d --force-recreate`
- [ ] `docker image prune -f --filter "label=org.opencontainers.image.source=..."` — filter by label
- [ ] Cleanup .env with `if: always()`
- [ ] Permissions: `packages: write, contents: read`

**Staging:** Tag `:staging`, deploy on `[self-hosted, staging]`
**Production:** Tags `:${{ github.ref_name }}` + `:latest`, deploy on `[self-hosted, production]`

## 6. Versioned Build Files

- [ ] `vite.config.ts` in git (not in `.gitignore`) — without it, the build generates a bundle without the React plugin, resulting in a blank page
- [ ] `vitest.config.ts` in git with `exclude: ['e2e/**']` — without it, Vitest collects Playwright tests
