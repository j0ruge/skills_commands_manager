---
name: cicd
metadata:
  version: 2.12.0
description: GitHub Actions / Docker / GHCR pipeline troubleshooting and config — auto-routes backend (Prisma/Biome) vs frontend (Vite). Covers self-hosted runners (systemd and containerized via myoung34), reverse-proxy upstream poisoning by `compose run` orphans, RUNNER_REGISTRATION_TOKEN chicken-and-egg deadlock recovery, container scripts writing output paths outside WORKDIR (`__dirname/../../...` ENOENT) being soft-failed forever as ambient yellow warnings (with errno-narrow catch refinement to preserve dev visibility of EACCES/ENOSPC/EROFS), GHA bind mount uid mismatch (vendored container uid 1000 vs runner uid 1001 + 0755 → EACCES with poisonous cascade in retries), and `docker compose up --wait` scoping to avoid one slow Next.js/Vite healthcheck stalling the whole stack. v2.12.0: §1a `troubleshooting-shared.md` — GHCR `net/http: TLS handshake timeout` no self-hosted runner (NÃO é o mesmo bug que `unauthorized`); isolation key é build-and-push em ubuntu-latest passar enquanto deploy em self-hosted falha; fix imediato é bash retry wrapper (3x, backoff 10s/20s) ao redor de `docker login` no deploy job; fix root é `mtu: 1400` em `/etc/docker/daemon.json` quando o host está em VPN/overlay com MTU reduzido que dropa Certificate frames. Triggers — CI/CD, GitHub Actions, workflow failing, GHCR auth, GHCR TLS handshake timeout, self-hosted runner, deploy keys, intermittent 401, split status codes, upstream pool stale, compose run orphan, docker-gen VIRTUAL_HOST, runbook canonical path mismatch, registration token expirado, gh-runner crashloop, chicken-and-egg, ENOENT bootstrap, soft-failure yellow warning fatigue, container script outside WORKDIR, GHA bind mount EACCES, container uid 1000 vs runner uid 1001, compose --wait scope, smoke-e2e timeout, docker login retry, MTU mismatch, TLS inspection proxy.
---

# CI/CD Skill — GitHub Actions, Docker & GHCR (Unified)

Skill for troubleshooting and configuring CI/CD pipelines. Detects the project type and routes to specific references.

---

## Project Detection

| Indicator                   | Project               |
| --------------------------- | --------------------- |
| `prisma/schema.prisma`      | **Backend**           |
| `biome.jsonc` / `biome.json`| **Backend (Biome)**   |
| `vite.config.ts`            | **Frontend**          |

> **Linter detection:** If the project has `biome.jsonc` (or `biome.json`), it uses Biome for lint/format. Otherwise, it assumes ESLint+Prettier. Biome projects do NOT use ESLint or Prettier.

> Check the project type before consulting references. Scenarios marked `[S]` are shared, `[B]` backend-only, `[F]` frontend-only.

---

## Workflow Overview

Both projects use **3 separate workflows** with identical triggers:

| Workflow          | File                | Trigger                  | Runners                                     |
| ----------------- | ------------------- | ------------------------ | ------------------------------------------- |
| **CI**            | `ci.yml`            | PR → `develop` or `main` | `ubuntu-latest`                             |
| **CD Staging**    | `cd-staging.yml`    | Push → `develop`         | `ubuntu-latest` + `self-hosted, staging`    |
| **CD Production** | `cd-production.yml` | Tag `v*`                 | `ubuntu-latest` + `self-hosted, production` |

### CI Differences

```text
Backend (ESLint):  checkout → install → prisma generate → lint → prettier → migrate → test (Jest)
Backend (Biome):   checkout → install → [prisma generate] → biome check → [test if configured]
Frontend:          checkout → install → lint → typecheck → test (Vitest)
```

> **Note:** `[prisma generate]` and `[test]` are optional — they depend on whether the project has Prisma and a configured test framework, respectively. Projects without a test framework (e.g., `estimates_api`) skip the test step in CI and CD.

### Deploy Differences

| Aspect               | Backend                                    | Frontend                                      |
| -------------------- | ------------------------------------------ | --------------------------------------------- |
| Build-args           | Does not need `environment:` in build job  | `environment:` required (VITE_* secrets)      |
| Image                | Generic (same for all envs)                | Environment-specific (VITE_* embedded in JS)  |
| Migration            | `prisma migrate deploy` before `up`        | No migration                                  |
| `VIRTUAL_PORT`       | Required (`API_PORT` ≠ 80)                | Not needed (nginx = port 80)                  |
| GHCR login on deploy | `docker/login-action@v3` before pull       | `docker/login-action@v3` before pull          |
| Prune                | `docker image prune -f`                    | `docker image prune -f --filter "label=..."`  |
| Compose path         | Varies by project (e.g., `infra/nodejs/`, `infra/`) | `infra/dsr_web/docker-compose.yml`            |

### Concurrency & Auth

- **CI:** `ci-${{ github.ref }}` with `cancel-in-progress: true`
- **CD:** `deploy-{staging|production}-<project>` with `cancel-in-progress: false`
- **GHCR:** `GITHUB_TOKEN` (automatic) via `docker/login-action@v3` — no PAT

---

## Quick Troubleshooting

| Tag   | Symptom                                                | Probable Cause                                       | Solution                                                                              |
| ----- | ------------------------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `[S]` | `unauthorized` on docker pull (self-hosted)            | Docker login in different context (sudo vs user)     | `docker login ghcr.io` in the same context that runs the pull                         |
| `[S]` | `Get "https://ghcr.io/v2/": net/http: TLS handshake timeout` on `docker login` (self-hosted runner; `build-and-push` on `ubuntu-latest` passes — only `deploy` fails) | Network-layer issue on the runner host (NOT credentials): MTU mismatch on VPN/overlay drops large TLS Certificate frames, or corporate TLS-inspection proxy stalls handshake | `troubleshooting-shared.md` §1a — Fix A: bash retry wrapper around `docker login` in the deploy job (3 attempts, 10s/20s backoff) absorbs transient flake; Fix B: lower Docker daemon MTU to `1400` in `/etc/docker/daemon.json` and restart docker on the runner host |
| `[S]` | `network declared as external, but could not be found` | Incorrect nginx-proxy network name in secret         | `docker network ls \| grep proxy` and fix `NGINX_NETWORK_NAME`                        |
| `[S]` | `ERR_SSL_VERSION_OR_CIPHER_MISMATCH`                   | DNS does not point to the server                     | `dig domain +short` should resolve to the server IP                                   |
| `[S]` | Deploy queued indefinitely                             | Self-hosted runner offline                           | `systemctl status actions.runner.*` on the server (host runner) **OR** `docker ps \| grep runner` (containerized — see `self-hosted-runner-docker.md` §7 if in `Restarting` with `404 /actions/runner-registration`) |
| `[S]` | CD step emits yellow `::warning::` on every deploy ("ENOENT" or similar in a script that finished its real work first) | Script writes output path resolved upward from `__dirname` — exists in dev source tree, missing in container image (Dockerfile only copies `packages/<self>/`); `continue-on-error: true` masks indefinitely | `cd-pipeline-pitfalls.md` §5 — wrap the write in try/catch best-effort and emit the artifact via `console.log` so CD logs capture it |
| `[S]` | Deploy blocked                                         | Concurrency group with previous run                  | Wait or cancel previous run via `gh run cancel`                                       |
| `[S]` | `--max-warnings 0` fails in ESLint                     | Pre-existing warnings                                | Fix warnings or use `eslint-disable`                                                  |
| `[B]` | `manifest unknown` in service container                | Discontinued Docker image                            | Switch to official image (e.g., `postgres:17`)                                        |
| `[B]` | Zod validation error on boot                           | Missing env vars in CI or in Generate .env           | Compare `src/env.ts` with `env:` block of tests and `printf` in CD                    |
| `[B]` | `ZodError invalid_string`                              | Secret URL missing `https://` protocol               | Check secret format                                                                   |
| `[B]` | Tests pass locally, fail in CI                         | Case-sensitivity in imports (Linux)                  | Fix file or import case                                                               |
| `[B]` | `FATAL ERROR: heap limit` / Exit 134                   | Jest OOM                                             | `node --max-old-space-size=4096`                                                      |
| `[B]` | `EADDRINUSE` in tests                                  | `server.ts` calls `app.listen()` in test             | Guard `NODE_ENV !== 'test'`                                                           |
| `[B]` | `ERR_CONNECTION_REFUSED` (nginx-proxy OK)              | `VIRTUAL_PORT` not defined in compose                | Add `VIRTUAL_PORT: '${API_PORT}'`                                                     |
| `[B]` | `tsc` type errors (Prisma client)                      | `--skipLibCheck` missing                             | Add `--skipLibCheck` to `tsc`                                                         |
| `[F]` | Blank page (SPA doesn't load)                          | Missing VITE_* or `vite.config.ts` absent            | Check ARGs in Dockerfile and build-args in workflow                                   |
| `[F]` | `VITE_API_URL` = `undefined` in JS                     | VITE_* not passed as build-arg                       | Check `build-args` in `docker/build-push-action`                                      |
| `[F]` | 404 on React Router routes                             | nginx `try_files` not configured                     | `try_files $uri $uri/ /index.html` in nginx.conf                                     |
| `[F]` | `Cannot access 'X' before initialization`              | `treeshake.moduleSideEffects` + circular chunks      | Remove `treeshake` and `manualChunks` from vite.config.ts                             |
| `[F]` | Container `unhealthy` (healthcheck fails)              | Alpine resolves `localhost` as IPv6                  | Use `127.0.0.1` in healthcheck                                                       |
| `[F]` | Vitest collecting Playwright E2E tests                 | `vitest.config.ts` without `e2e/` exclude            | Add `exclude: ['e2e/**']`                                                             |
| `[B]` | `npx biome check .` fails on config files              | Biome checks all files by default                    | Use `files.includes` in `biome.jsonc` to scope or fix the config files                |
| `[B]` | Biome 2.x config error (`unknown key "ignore"`)       | Biome 2.x removed `ignore` in favor of `includes`   | Use `files.includes` instead of `files.ignore` in `biome.jsonc`                       |
| `[B]` | Migration reports "No pending migrations" but app crashes with missing column | Stale Docker image cache on self-hosted runner (`docker run` does not pull if tag exists locally) | `docker pull` the image before `docker run` in the migration step |
| `[F]` | Container nginx returns 403                            | dist/ empty or not copied                            | Check `npm run build` and `COPY --from=build` in Dockerfile                           |
| `[S]` | `Missing script: "exec"` ao rodar tsc/playwright/openapi-typescript em workspace | Sintaxe inválida `npm run -w <ws> exec -- <cmd>` (não existe script `exec`; `exec` é subcomando de `npm`, não script de `package.json`) | Substituir por `npm exec -w <ws> -- <cmd>` |
| `[S]` | `ESLint couldn't find an eslint.config.(js\|mjs\|cjs) file` em workspace de monorepo | ESLint v9 removeu auto-detect de `.eslintrc.*`; flat config existe em outro workspace e **não** se propaga | Criar `eslint.config.js` por workspace que rode `eslint`. Pacotes Node-only: `globals.node`, sem `eslint-plugin-react-hooks` / `react-refresh` |
| `[S]` | `Cannot find package 'X' imported from /node_modules/<other-pkg>` em monorepo | devDep tem subtree em versões antigas que conflita com a raiz → npm aninha em `packages/<ws>/node_modules/X`; outras deps hoisted não acham via Node ESM resolution | Trocar por dep com subtree compatível (ex.: jsdom→happy-dom), OU declarar a dep no `package.json` raiz para forçar hoist, OU `overrides` para dedup das transitive deps conflitantes |
| `[F]` | Vitest pré-test fail (`Cannot find package 'jsdom'`) ou `TypeError: signal AbortSignal` em msw v2 | jsdom@20 não hoista em monorepo (subtree pesado) + injeta `AbortController` próprio incompatível com undici nativo do Node usado pelo msw v2 | Trocar para `happy-dom`: `npm i -D happy-dom -w <ws>` e `environment: 'happy-dom'` em `vitest.config.ts`. Subtree leve hoista limpo + AbortController nativo |

---

## Routing Table — Detailed References

| Problem Category                                          | Reference                                    |
| --------------------------------------------------------- | -------------------------------------------- |
| Shared infra (GHCR, network, SSL, runner via systemd)     | `references/troubleshooting-shared.md`       |
| **Self-hosted runner conteinerizado (myoung34/github-runner)** | `references/self-hosted-runner-docker.md`    |
| Shared checklist (runner, GHCR, DNS)                      | `references/checklist-shared.md`             |
| Backend troubleshooting (Zod, Prisma, Jest)               | `references/troubleshooting-backend.md`      |
| Backend checklist (secrets, tests, build)                 | `references/checklist-backend.md`            |
| Jest test fix patterns                                    | `references/test-fixes-backend.md`           |
| Frontend troubleshooting (Vite, SPA, nginx)               | `references/troubleshooting-frontend.md`     |
| Frontend checklist (VITE_*, Dockerfile, CD)               | `references/checklist-frontend.md`           |
| **CD pipeline pitfalls (build-time vs runtime, operator clones, `--profile run` reconcile, `compose run` orphans poisoning reverse-proxy upstream)** | `references/cd-pipeline-pitfalls.md` |

> **Trigger pra `cd-pipeline-pitfalls.md`**: você está num cutover de produção (ou hotfix) e o sintoma envolve uma divergência entre camadas — secret atualizado mas container ainda com valor antigo, frontend buildado contra URL errada, manual `docker compose run` derrubando containers de outros serviços, OU **401 inconsistente em produção com token sabido válido** (split entre 200/401 sob hits paralelos). Sintomas-chave: (§1) SPA com 404 em todas as chamadas API após login funcionar — VITE_* base URL drift; (§2) "operator clone" do repo no host com versão stale do compose, ou path canônico do runbook não existe no host (deploy real é via runner workspace); (§3) `docker compose --profile X run` derrubando containers running; (§4) `compose run` orphan herdou `VIRTUAL_HOST` do serviço e foi registrado no upstream pool do nginx-proxy/Traefik — round-robin manda ~50% das requests pra container stale com config velha. Diagnóstico canônico §4: 20 hits paralelos com mesmo token → split de status codes = upstream pool poisoned.

> **Trigger pra `self-hosted-runner-docker.md`**: presença de `infra/docker/runner/Dockerfile` (ou similar) com `FROM myoung34/github-runner` no projeto, OU `docker-compose.*.yml` com serviço cujo `image:`/`build:` referencia esse runner conteinerizado. Sintomas-chave: container em loop de restart com exit 0/2, logs com "Configuring → Settings Saved → fim", "Cannot configure the runner because it is already configured", build falhando em `gpg --dearmor`, ou `gh api .../actions/runners` mostrando label `default` em vez da configurada. **§7 cobre o cenário deadlock-em-prod**: deploy queued + `gh-runner` em `Restarting` + log `404 /actions/runner-registration` = `secrets.RUNNER_REGISTRATION_TOKEN` estática expirou e o equilíbrio "compose detecta no-diff e não recria" quebrou (host restart, OOM, ephemeral ciclando). Recovery exige 3 passos coordenados: rotacionar GH secret + deletar registro fantasma + subir runner via `compose -p <project> up -d --no-deps runner` (não `docker run` — sem labels compose, próximo CD `up` conflita). Fix permanente: token gerado a quente no workflow OU migrar pro compose centralizado de runners com `ACCESS_TOKEN` (PAT).

---

## Lessons Learned (Summary)

| # | Tag   | Lesson | Context |
|---|-------|--------|---------|
| 1 | `[S]` | GHCR auth: sudo vs user context | `~/.docker/config.json` is per-user |
| 2 | `[S]` | nginx-proxy network name varies by installation | Check with `docker network ls` |
| 3 | `[S]` | Secret URLs must include `https://` | Zod `z.string().url()` rejects without protocol |
| 4 | `[S]` | Port mapping unnecessary with nginx-proxy | No `ports:` in staging/prod compose |
| 5 | `[S]` | DNS must point to the server IP | Let's Encrypt needs HTTP-01 challenge |
| 6 | `[S]` | Concurrency groups block deploys | `cancel-in-progress: false` queues |
| 7 | `[S]` | Lint locally before pushing to develop | Push triggers CD; errors waste cycles |
| 8 | `[S]` | Re-trigger without `workflow_dispatch` | `gh run rerun` or `git commit --allow-empty` |
| 9 | `[B]` | `bitnami/postgresql` image discontinued | Use `postgres:17` with `POSTGRES_USER` |
| 10 | `[B]` | `--skipLibCheck` required in build | Prisma client generates conflicting types |
| 11 | `[B]` | Prettier not installed as dependency | Must be an explicit devDependency |
| 12 | `[B]` | Zod validation fails in CI | All vars from `src/env.ts` in the test step |
| 13 | `[B]` | `DATABASE_URL` with wrong prefix | Project's Zod requires `postgres://` |
| 14 | `[B]` | Zod vars in Generate .env of CD | Update CI and CD when adding a var in Zod |
| 15 | `[B]` | `VIRTUAL_PORT` required for port ≠ 80 | nginx-proxy default is 80 |
| 16 | `[B]` | `continue-on-error` is a workaround | Use only temporarily |
| 17 | `[B]` | `server.ts` guard for `NODE_ENV=test` | Prevents `EADDRINUSE` in tests |
| 18 | `[F]` | VITE_* are build-time, not runtime | Env vars in the nginx container have no effect |
| 19 | `[F]` | Docker image is environment-specific | Staging and prod are different images |
| 20 | `[F]` | `build-and-push` needs `environment:` | To access VITE_* secrets as build-args |
| 21 | `[F]` | No `VIRTUAL_PORT` for nginx | nginx listens on port 80 (default) |
| 22 | `[F]` | Healthcheck Alpine: `127.0.0.1` | `localhost` may resolve to `::1` (IPv6) |
| 23 | `[F]` | `vite.config.ts` must be versioned | Without it, bundle without React plugin → blank page |
| 24 | `[F]` | Vitest collecting Playwright E2E tests | `vitest.config.ts` with `exclude: ['e2e/**']` |
| 25 | `[F]` | `treeshake.moduleSideEffects` + circular chunks | Remove custom treeshake and manualChunks |
| 26 | `[S]` | GHCR login required in deploy job | `docker/login-action@v3` before pull (both projects) |
| 27 | `[B]` | Biome checks all files by default | Use `files.includes` in `biome.jsonc` to limit scope to `src/` or fix config files |
| 28 | `[S]` | First deploy requires workflows on `develop` branch | CD Staging triggers on push to `develop` — workflows must be on that branch before the first push |
| 29 | `[B]` | `docker run` does not auto-pull if the tag exists locally on self-hosted runners | Always `docker pull <image>` before `docker run <image>` in migration steps — stale cache causes "no pending migrations" while the app expects new schema |
| 30 | `[S]` | `npm run -w <ws> exec --` é sintaxe inválida em monorepo npm | `exec` não é script de `package.json`; usar `npm exec -w <ws> -- <cmd>`. Falha cedo (`Missing script: "exec"`) e mascara steps subsequentes |
| 31 | `[S]` | ESLint v9 flat config é per-workspace, não herda | Cada workspace que rode `eslint` precisa do próprio `eslint.config.{js,mjs,cjs}` — bump pra v9 num workspace não dá config aos siblings |
| 32 | `[S]` | devDep com subtree em versões antigas não hoista em monorepo npm | npm aninha o subtree em `packages/<ws>/node_modules/X`, fora do alcance da resolução Node ESM partindo de outra dep hoisted. Diagnóstico: comparar `node_modules/X` (raiz) vs `packages/<ws>/node_modules/X` no lock |
| 33 | `[F]` | vitest 3 + msw v2 + jsdom esconde 2 bugs latentes | Hoisting (jsdom@20 não hoista) + AbortSignal mismatch (jsdom injeta primitivas próprias incompatíveis com undici nativo). `happy-dom` resolve ambos: subtree leve hoista limpo + AbortController nativo do Node |
| 34 | `[S]` | `compose run --rm` orphan + nginx-proxy = upstream pool poisoning | One-off `compose run` herda `VIRTUAL_HOST` do serviço; se `--rm` falha (CI cancel / OOM / daemon restart), órfão fica registrado pelo docker-gen no upstream pool e recebe round-robin com config stale. `up -d --remove-orphans` NÃO cobre (mesmo serviço, suffix-hash). Fix: `-e VIRTUAL_HOST= -e LETSENCRYPT_HOST=` no `compose run` + step pre-rolling `docker rm -f` em `*-run-*`. Diagnóstico: 20 hits paralelos = split de status codes |
| 35 | `[S]` | `secrets.RUNNER_REGISTRATION_TOKEN` estática é equilíbrio frágil — chicken-and-egg quando quebra | Registration tokens vencem em 1h; design só funciona porque `compose up` detecta no-diff entre deploys e pula recriação do `runner` service. Qualquer evento que force re-registro (host restart, OOM, ephemeral ciclando) → `config.sh` com token vencido → 404 → crashloop. Deploy fica queued sem runner, runner não sobe sem deploy. Recovery: rotacionar GH secret + apagar registro fantasma + subir via `compose -p <project> up -d --no-deps runner` (mesmo token e labels match). Fix permanente: token a quente no workflow OU PAT no compose centralizado |
| 36 | `[S]` | GHCR `TLS handshake timeout` vs `unauthorized` — não são o mesmo bug | `unauthorized` = TLS completou, credencial rejeitada (rotacionar PAT). `TLS handshake timeout` = TCP conectou mas handshake não completou — credencial é irrelevante. Isolation key: se `build-and-push` em `ubuntu-latest` passa mas `deploy` em `self-hosted` falha, GHCR está saudável → problema é rede do host runner (MTU em VPN/overlay drops Certificate frames; ou proxy corporativo de TLS inspection). Fix imediato: bash retry wrapper no step de login (3x, backoff 10s/20s) — absorve flake transiente. Fix root: `mtu: 1400` em `/etc/docker/daemon.json` + restart docker. `docker/login-action@v3` não tem retry nativo |
| `[S]` | ~50% das requests autenticadas retornam 401 mesmo com JWT comprovadamente válido (200 quando replay direto via curl) | Container órfão de `compose run --rm` antigo (ex.: `prisma migrate deploy` que não disparou `--rm` por CI cancelado / OOM) ainda Up, herdou `VIRTUAL_HOST` do serviço, registrado pelo docker-gen no upstream pool do nginx-proxy. Round-robin envia ~50% pra config stale. Confirmação: 20 hits paralelos com mesmo token → split de status codes. Ver `cd-pipeline-pitfalls.md §4` |

---

## Useful Commands

```bash
# View workflow status
gh run list --limit 5

# View logs of a specific run
gh run view <run-id> --log-failed

# Re-run a failed workflow
gh run rerun <run-id>

# List secrets of an environment
gh secret list --env staging

# Check images on GHCR
gh api orgs/JRC-Brasil/packages/container/<PACKAGE_NAME>/versions
```

### Backend

```bash
# Manual rollback (compose path varies by project)
export IMAGE_TAG=<previous-tag>
docker compose -f <COMPOSE_PATH>/docker-compose.yml pull
docker compose -f <COMPOSE_PATH>/docker-compose.yml up -d --force-recreate
```

### Frontend

```bash
# Manual rollback
export IMAGE_TAG=<previous-tag>
docker compose -f infra/dsr_web/docker-compose.yml pull
docker compose -f infra/dsr_web/docker-compose.yml up -d --force-recreate

# Check VITE_* embedded in JS
docker exec service_report_web sh -c "grep -r 'jrcbrasil' /usr/share/nginx/html/assets/*.js | head -5"
```

---

## Pipeline Files

### Backend

| File                                  | Description                             |
| ------------------------------------- | --------------------------------------- |
| `.github/workflows/ci.yml`            | CI pipeline (lint + test) for PRs       |
| `.github/workflows/cd-staging.yml`    | CD pipeline for staging (push develop)  |
| `.github/workflows/cd-production.yml` | CD pipeline for production (tags v\*)   |
| `Dockerfile` or `infra/*/Dockerfile`  | Multi-stage build (path varies by project) |
| `infra/*/docker-compose.yml`          | Compose with GHCR image (path varies)   |
| `src/env.ts`                          | Zod validation of env vars              |

### Frontend

| File                                  | Description                             |
| ------------------------------------- | --------------------------------------- |
| `.github/workflows/ci.yml`            | CI pipeline (lint + typecheck + test)   |
| `.github/workflows/cd-staging.yml`    | CD pipeline for staging (push develop)  |
| `.github/workflows/cd-production.yml` | CD pipeline for production (tags v\*)   |
| `infra/dsr_web/Dockerfile`            | Multi-stage build (node + nginx)        |
| `infra/dsr_web/docker-compose.yml`    | Compose with GHCR image                 |
| `infra/dsr_web/nginx.conf`            | nginx config (SPA try_files)            |
