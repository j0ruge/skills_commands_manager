# Troubleshooting — Backend (Node.js/Express/Prisma)

Backend-specific troubleshooting scenarios. For shared infrastructure scenarios, see `troubleshooting-shared.md`.

---

## Diagnosis by Exit Code

### Exit 1 — Generic Failure (Test/Lint)

**Common causes:** ESLint warnings with `--max-warnings 0`, Prettier formatting mismatch, Jest test failures, TypeScript compilation errors.

```bash
gh run view <run-id> --log-failed
yarn lint && yarn lint:check && yarn test
```

### Exit 2 — Misuse of Command

**Cause:** Invalid flag or script not found in package.json.

### Exit 127 — Command Not Found

**Cause:** Binary not installed (e.g., `prettier` without devDependency).

```bash
grep "prettier" package.json
yarn add -D prettier
```

### Exit 134 — SIGABRT (OOM)

**Symptom:** `FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory`

```yaml
run: node --max-old-space-size=4096 node_modules/.bin/jest --forceExit
```

### Exit 137 — SIGKILL (OOM Killer)

**Cause:** The operating system killed the process due to excessive memory usage.

**Fix:** Increase runner memory or optimize tests (`--runInBand`).

---

## By Error Message

### `manifest unknown`

**Cause:** Docker image does not exist in the registry (e.g., `bitnami/postgresql:17` discontinued).

```yaml
# BEFORE (does not work)
image: bitnami/postgresql:17
env:
  POSTGRESQL_USERNAME: test_user

# AFTER
image: postgres:17
env:
  POSTGRES_USER: test_user
```

### Zod Validation Error

**3 distinct scenarios:**

1. **In CI (test step) — `invalid_type`:** Variable missing from the `env:` block of the test step.
2. **In deploy (container) — `invalid_type`:** Variable missing from the "Generate .env" step of the CD workflow.
3. **In deploy (container) — `invalid_string`:** Variable present but with invalid format (e.g., URL without `https://`).

**Prevention:** When adding a new variable in Zod (`src/env.ts`), update BOTH: the `env:` block of the tests AND the `printf` of the Generate .env in the CD workflows.

### `EADDRINUSE`

```text
Error: listen EADDRINUSE: address already in use :::3003
```

**Cause:** `server.ts` calls `app.listen()` during tests. See `test-fixes-backend.md` section 4.

### `Cannot find module` (case-sensitivity)

```text
Cannot find module '@repositories/vessel.repository'
```

**Cause:** Import path does not match the actual file case on Linux. See `test-fixes-backend.md` section 1.

### `TS2688` / `TS2724` — Prisma type errors

**Cause:** Incompatibility between Prisma-generated types and TypeScript version.

**Fix:** Add `--skipLibCheck` to the `tsc` command.

### `npx biome check .` fails on non-source files

**Symptom:** Biome reports errors in config files (`biome.jsonc`, `tsconfig.json`, `Dockerfile`, etc.) or in files outside `src/`.

**Cause:** Biome checks all files by default, unlike ESLint which is usually configured for a specific scope.

**Fix:** Configure `files.includes` in `biome.jsonc` to limit the scope:

```jsonc
{
  "files": {
    "includes": ["src/**", "prisma/**"]
  }
}
```

Or fix the reported errors in the config files (empty blocks, `node:` protocol, naming conventions).

### Biome 2.x config error (`unknown key "ignore"`)

**Symptom:** `biome check` fails with a configuration error when migrating to Biome 2.x.

**Cause:** Biome 2.x removed the `files.ignore` key in favor of `files.includes` (inverted logic).

**Fix:** Replace `files.ignore` with `files.includes` in `biome.jsonc`.

### `ERR_CONNECTION_REFUSED` via browser (nginx-proxy OK)

**Symptom:** Browser returns `ERR_CONNECTION_REFUSED`. SSL certificate renews normally. API container is running.

**Cause:** `VIRTUAL_PORT` not defined in `docker-compose.yml`. nginx-proxy uses default port 80, but the API listens on a different port (e.g., 3003).

**Diagnosis:**

```bash
docker exec nginx-proxy cat /etc/nginx/conf.d/default.conf | grep -A 10 "api.dsr"
docker exec service_report_api sh -c "wget -qO- http://localhost:3003/health || curl -s http://localhost:3003"
```

**Fix:** Add `VIRTUAL_PORT: '${API_PORT}'` in the `environment` section of `docker-compose.yml`.

---

### "No pending migrations" but app crashes with missing column/table

**Symptom:** `prisma migrate deploy` reports "No pending migrations to apply" in the CD workflow, but the application container crashes with a database error (e.g., `column "X" does not exist` or `relation "X" does not exist`). The `_prisma_migrations` table shows one fewer migration than the codebase.

**Cause:** On self-hosted runners, `docker run` does **not** auto-pull the image if the tag already exists locally. The migration step ran `docker run ghcr.io/.../api:staging npx prisma migrate deploy` using the **cached old image** (which had N migrations), while the newly built image (N+1 migrations) was already pushed to GHCR but not yet pulled on the runner.

**Diagnosis:**

```bash
# Compare migration count in DB vs codebase
docker exec <db_container> psql -U <user> -d <db> -c "SELECT count(*) FROM _prisma_migrations"
ls prisma/migrations/ | grep -c "^[0-9]"

# Check when the last migration was applied vs CD run time
docker exec <db_container> psql -U <user> -d <db> \
  -c "SELECT migration_name, finished_at FROM _prisma_migrations ORDER BY finished_at DESC LIMIT 3"

# Verify the image digest on the runner vs GHCR
docker inspect ghcr.io/<org>/<image>:staging --format '{{.Id}}'
```

**Fix (workflow):**

Add `docker pull` before `docker run` in the migration step of the CD workflow:

```yaml
- name: Run database migrations
  run: |
    docker pull ghcr.io/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }}
    docker run --rm --network ${{ secrets.NGINX_NETWORK_NAME }} \
      -e DB_URL=${{ secrets.DB_URL }} \
      ghcr.io/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }} \
      npx prisma migrate deploy --schema packages/backend/prisma/schema.prisma
```

**Manual recovery (if already deployed with stale migration):**

```bash
# Pull the correct image and run migration manually
docker pull ghcr.io/<org>/<image>:staging
docker run --rm -e DB_URL=<url> --network <network> \
  ghcr.io/<org>/<image>:staging \
  npx prisma migrate deploy --schema packages/backend/prisma/schema.prisma
```

---

## Monorepo npm workspaces — armadilhas de build/runtime na imagem

Três problemas que só aparecem quando o backend vive num monorepo com workspaces
`@scope/shared-*` (descobertos no `sales_quote`, 2026-06-12).

### `ERR_MODULE_NOT_FOUND` / `ERR_UNKNOWN_FILE_EXTENSION` ao rodar `node dist/index.js`

**Sintoma**: o build (`tsc`) passa, a imagem sobe, mas o processo morre no boot:

```text
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '.../packages/shared/api-types/src/enums.js'
  imported from .../packages/shared/api-types/src/index.ts
```

**Causa**: os pacotes compartilhados exportam **código-fonte TypeScript** —
`"main": "./src/index.ts"` — usando a convenção de import com extensão `.js`
(`export * from "./enums.js"` apontando para `enums.ts`). O `tsc` do backend
**não inlina** workspace deps (preserva o specifier bare `@scope/shared-x`), e o
`node` resolve isso para o `./src/index.ts` do sibling — que ele **não consegue
carregar** (`.ts` não é executável; e o type-stripping nativo do Node não faz o
remapeamento `.js`→`.ts`).

**Fix**: rodar a imagem via **`tsx`** (esbuild) em vez de `node dist/`. É
exatamente como o app roda em dev (`tsx watch`); `tsx` carrega `.ts` e faz o
remapeamento. O estágio runtime mantém o `tsx` (devDep) e o source:

```dockerfile
# runtime stage
COPY --from=builder /app/node_modules ./node_modules   # inclui tsx + Prisma Client gerado
COPY --from=builder /app/packages/backend ./packages/backend
COPY --from=builder /app/packages/shared ./packages/shared   # symlinks de workspace apontam p/ cá
WORKDIR /app/packages/backend
CMD ["npx", "tsx", "src/index.ts"]
```

**Não "consertar"** repontando o `exports`/`main` dos pacotes shared para `dist`
— isso quebra o **frontend**, cujo Vite/bundler consome o source TS desses
mesmos pacotes. O `tsx` no backend é a mudança de menor blast-radius.

> Migrations/seed continuam como one-off do Prisma CLI (`npx prisma migrate
> deploy` / `npx prisma db seed`), que já funcionam — o `db seed` roda
> `tsx prisma/seed.ts` dentro da imagem.

### Vite/Build do frontend falha resolvendo um sibling — `npm ci -w` escopado não basta

Se um workspace **importa um sibling que NÃO declarou** em `dependencies` (resolve
só pelo hoist do npm na raiz), um `npm ci -w @scope/frontend` no Docker **não cria
o symlink** desse sibling → o build falha em resolvê-lo. Ex.: o frontend importa
`@scope/shared-api-types` sem declará-lo. **Fix**: usar `npm ci` **cheio** no
estágio builder (que é descartado — só `dist/` vai à imagem final, então o
tamanho extra é irrelevante). Para imagens onde o runtime é enxuto (backend), aí
sim vale o `npm ci -w <pkg>` escopado — mas só se o `package.json` declara todos
os siblings que usa.

### Container não-root não grava no named volume

Imagens com `USER node` (não-root) que montam um **named volume** novo num path de
escrita (storage de PDFs, uploads) batem `EACCES` na primeira gravação. Docker
inicializa o named volume novo a partir do conteúdo **e da ownership** do path na
imagem; se o dir não existe ou é root-owned, o volume nasce root-owned.

```dockerfile
RUN mkdir -p /app/storage/pdfs && chown -R node:node /app/storage   # ANTES do USER
USER node
```

(Só vale p/ **named volumes** — bind mounts não copiam ownership da imagem.)

### Corolário da imagem `tsx`-runtime: enxugar com `--omit=dev`

A seção acima (e a lesson 37) deixam a imagem rodando via `tsx` e copiando o
`node_modules` **cheio** do builder — o que carrega junto todo o test tooling
(`vitest`, `testcontainers`, `supertest`, `nock`, `typescript`, `@types/*`) pra
imagem de produção: dezenas de MB e superfície de ataque que o runtime não usa.

A pegadinha: você **não pode** simplesmente fazer `npm ci --omit=dev`, porque as
ferramentas que o runtime e os one-offs precisam — **`tsx`** (CMD) e o **Prisma
CLI** (`prisma migrate deploy` / `db seed`) — normalmente vivem em
`devDependencies`. Um `--omit=dev` as removeria e quebraria o boot/migrate.

**Fix**: mover `tsx` e `prisma` de `devDependencies` para `dependencies` no
`package.json` do backend. Aí o estágio runtime instala só produção:

```dockerfile
# builder: install CHEIO (precisa de prisma generate + resolver siblings, lesson 39)
RUN npm ci -w @scope/backend --include-workspace-root=false --omit=dev
#                                                            ^^^^^^^^^^
# Com tsx + prisma em `dependencies`, o --omit=dev mantém runtime/migrate
# funcionando e DESCARTA vitest/testcontainers/supertest/typescript da imagem.
RUN npm run db:generate -w @scope/backend     # Prisma Client (prisma está em deps)
```

Sincronize o lockfile depois de mover as deps: `npm install --package-lock-only`
(reclassifica as árvores de `tsx`/`prisma` como produção; sem isso `npm ci` falha).

**Verificação** (no build real, não só no diff):

```bash
docker build -f packages/backend/Dockerfile -t app:slim .
docker run --rm --entrypoint sh app:slim -c '
  ls /app/node_modules/.bin/tsx /app/node_modules/.bin/prisma   # PRESENTES
  ls -d /app/node_modules/vitest /app/node_modules/testcontainers 2>&1   # ABSENT
'
```

> Nota: `typescript` às vezes permanece como dep de produção transitiva (peer de
> algum pacote) — é minoritário (~22 MB) e não é o test tooling pesado; o ganho
> principal (vitest/testcontainers fora) já vem do `--omit=dev`.

---

## Diagnosis Flow — Backend

```text
Workflow failed
├── Which job?
│   ├── lint → ESLint warnings / Prettier / Biome check
│   ├── test → Check exit code and message
│   │   ├── Exit 134/137 → OOM → increase heap
│   │   ├── Exit 1 → Read Jest log
│   │   │   ├── Cannot find module → case-sensitivity
│   │   │   ├── ZodError invalid_type → missing env var
│   │   │   ├── ZodError invalid_string → URL without https://
│   │   │   ├── EADDRINUSE → guard server.ts
│   │   │   └── Assertion error → data/seed
│   │   └── Exit 127 → missing dependency
│   ├── build-and-push → Dockerfile or GHCR auth
│   └── deploy → Runner offline, compose error, env var, or stale image
│       ├── ZodError invalid_type → missing env var in Generate .env
│       ├── ZodError invalid_string → URL without https://
│       ├── ERR_CONNECTION_REFUSED → VIRTUAL_PORT not defined
│       ├── "No pending migrations" + app crash → stale image cache → docker pull before docker run
│       └── runner offline → systemctl status actions.runner.*
└── Reproduce locally before modifying the workflow
```

---

## Diagnostic Commands

```bash
# Full logs of the failed run
gh run view <run-id> --log-failed

# Logs of a specific job
gh run view <run-id> --log --job <job-id>

# Re-run only failed jobs
gh run rerun <run-id> --failed

# Runner status on the server
sudo systemctl status actions.runner.*
journalctl -u actions.runner.*.service --since "1 hour ago"
```
