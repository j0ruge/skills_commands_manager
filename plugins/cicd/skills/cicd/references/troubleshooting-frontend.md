# Troubleshooting — Frontend (React/Vite/nginx)

Frontend-specific troubleshooting scenarios. For shared infrastructure scenarios, see `troubleshooting-shared.md`.

---

## Detailed Scenarios

### 1. Blank Page (SPA does not load)

**Symptom**: Browser shows a blank page with no network errors.

**Diagnosis:**

```bash
# Check if dist/ has content
docker exec service_report_web ls -la /usr/share/nginx/html/

# Check if index.html references the correct assets
docker exec service_report_web cat /usr/share/nginx/html/index.html

# Check if VITE_* are embedded
docker exec service_report_web sh -c "grep -r 'VITE_' /usr/share/nginx/html/assets/*.js | head -5"
```

**Common causes:**

1. VITE_* were not passed as `build-args` in the `docker/build-push-action`. The `vite build` completed without error, but `import.meta.env.VITE_API_URL` is `undefined`.
2. `vite.config.ts` missing from git (e.g., added to `.gitignore`). Without the file, `vite build` runs without the React plugin, generating a bundle that renders nothing.

**Solution:** Verify that all 11 ARGs are in the Dockerfile, that the workflow passes each one via `build-args:`, and that `vite.config.ts` is versioned.

---

### 2. Failing API Calls (CORS, wrong URL)

**Symptom:** App loads but API calls fail.

**Diagnosis:**

```bash
docker exec service_report_web sh -c "grep -o 'https://[^\"]*jrcbrasil[^\"]*' /usr/share/nginx/html/assets/*.js | sort -u"
```

**Cause:** VITE_API_URL points to the wrong environment (staging vs production) or does not include the `https://` protocol.

**Solution:** Check and fix the `VITE_API_URL` secret in the correct GitHub environment.

---

### 3. 404 on React Router Routes

**Symptom:** Route `/reports` returns 404 when accessed directly (not via SPA navigation).

**Cause:** nginx does not have `try_files $uri $uri/ /index.html` configured.

**Solution:** Check `infra/dsr_web/nginx.conf`:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

---

### 4. `Cannot access 'X' before initialization` (Runtime)

**Symptom:** App loads the HTML but JavaScript fails with `Cannot access 'X' before initialization` or `ReferenceError`.

**Diagnosis:**

```bash
grep -n 'treeshake\|manualChunks\|moduleSideEffects' vite.config.ts
```

**Cause:** `treeshake.moduleSideEffects: false` in `vite.config.ts` combined with `manualChunks` that group modules with circular dependencies.

**Solution:** Remove custom `treeshake` and `manualChunks` from `vite.config.ts`. Rollup/Vite's default treeshaking is sufficient.

---

### 5. `unhealthy` Container — Healthcheck Fails on Alpine

**Symptom:** `docker ps` shows the container as `unhealthy` but nginx is running.

**Diagnosis:**

```bash
docker inspect service_report_web --format '{{json .State.Health}}' | jq .
# Test with explicit IPv4
docker exec service_report_web wget -qO- http://127.0.0.1:80/index.html | head -5
# Compare with localhost (may fail)
docker exec service_report_web wget -qO- http://localhost:80/index.html | head -5
```

**Cause:** On Alpine images, `localhost` can resolve to `::1` (IPv6). If nginx only listens on IPv4, the healthcheck fails.

**Solution:** Use `127.0.0.1` instead of `localhost` in the healthcheck:

```yaml
healthcheck:
  test: ["CMD", "wget", "-qO-", "http://127.0.0.1:80/index.html"]
```

---

### 6. Vitest Collecting Playwright E2E Tests

**Symptom:** CI fails with Playwright import errors or unexpected tests being executed.

**Diagnosis:**

```bash
npx vitest run --reporter=verbose 2>&1 | grep "e2e/"
```

**Cause:** Without explicit configuration, Vitest collects all `*.test.ts` / `*.spec.ts`, including those in `e2e/`.

**Solution:** Create or update `vitest.config.ts` with exclude:

```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    exclude: ['e2e/**', 'node_modules/**'],
  },
})
```

---

### 7. nginx Container 403 — Empty dist/

**Symptom:** nginx returns 403 Forbidden.

**Cause:** The `dist/` directory was not copied or is empty in the image.

**Diagnosis:**

```bash
docker exec service_report_web ls -la /usr/share/nginx/html/
```

**Solution:** Verify that `npm run build` generates `dist/` in the Dockerfile and that the `COPY --from=build` is correct.

---

## Diagnosis Flow — Frontend

```text
Pipeline failed?
├── Which job?
│   ├── CI (lint/typecheck/test)
│   │   ├── ESLint failed? → --max-warnings 0 with existing warnings
│   │   ├── tsc --noEmit failed? → Type errors
│   │   └── Vitest failed?
│   │       ├── Specific test → verify locally
│   │       └── Collecting E2E tests? → vitest.config.ts with exclude
│   │
│   ├── Build-and-push
│   │   ├── Docker build failed?
│   │   │   ├── yarn install failed → check yarn.lock
│   │   │   ├── npm run build failed → check tsc and vite build
│   │   │   └── Missing ARG → check build-args in the workflow
│   │   └── Docker push failed? → GHCR auth (permissions: packages: write)
│   │
│   └── Deploy
│       ├── Container unhealthy? → localhost IPv6 on Alpine → use 127.0.0.1
│       ├── Container started but app does not work?
│       │   ├── Blank page → missing VITE_* or vite.config.ts absent
│       │   ├── Cannot access 'X' before initialization → treeshake / circular
│       │   ├── 404 on routes → nginx try_files
│       │   ├── 403 Forbidden → empty dist/
│       │   └── API calls failing → incorrect VITE_API_URL
│       └── SSL? → ERR_SSL → DNS not pointing (see troubleshooting-shared.md)
└── Reproduce locally before modifying the workflow
```

---

## Diagnostic Commands

```bash
# Container status
docker ps --filter name=service_report_web

# Container logs
docker logs service_report_web --tail 50

# Check the image used
docker inspect service_report_web --format '{{.Config.Image}}'

# Check healthcheck
docker inspect service_report_web --format '{{json .State.Health}}' | jq .

# Test nginx (use 127.0.0.1, not localhost)
docker exec service_report_web wget -qO- http://127.0.0.1:80/index.html | head -5

# Check embedded VITE_* in JS
docker exec service_report_web sh -c "grep -r 'jrcbrasil' /usr/share/nginx/html/assets/*.js | head -5"
```
