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
│   └── deploy → Runner offline, compose error, or env var
│       ├── ZodError invalid_type → missing env var in Generate .env
│       ├── ZodError invalid_string → URL without https://
│       ├── ERR_CONNECTION_REFUSED → VIRTUAL_PORT not defined
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
