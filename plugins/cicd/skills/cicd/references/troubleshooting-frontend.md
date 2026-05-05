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

### 8. Vitest com `environment: 'jsdom'` falha pré-test ou em `signal AbortSignal`

**Symptom A — pré-test fail (CI / monorepo):**

```text
Error: Cannot find package 'jsdom' imported from
  /home/runner/work/.../node_modules/vitest/dist/chunks/index.<hash>.js

Test Files (N)  Tests no tests  Errors N errors
```

Nenhum teste roda. Vitest aborta no setup do environment.

**Symptom B — falha em runtime durante testes (qualquer ambiente):**

```text
TypeError: RequestInit: Expected signal ("AbortSignal {}") to be an instance of AbortSignal.
  at @mswjs/interceptors/src/utils/fetchUtils.ts:<line>
  at <YourApiClient>.request (src/lib/api/client.ts:<line>)
```

Acontece em testes que usam `fetch(..., { signal })` mockado por msw v2.

**Cause (dois bugs em um setup):**

1. **Hoisting (Symptom A):** `jsdom@20` traz subtree de deps em versões antigas (`agent-base@6`, `cssstyle@2`, `tough-cookie@4`) que conflitam com a raiz do monorepo. npm aninha o subtree todo em `packages/<ws>/node_modules/jsdom`, não em `/node_modules/jsdom`. vitest hoisted na raiz não consegue encontrar — resolução Node ESM partindo de `/node_modules/vitest/...` nunca olha em `packages/<ws>/node_modules/`. Ver `troubleshooting-shared.md` cenário 8 para o mecanismo geral.
2. **AbortSignal mismatch (Symptom B):** jsdom injeta seu próprio `AbortController`/`AbortSignal` em `globalThis`. msw v2 (`@mswjs/interceptors`) intercepta `fetch` e usa undici nativo do Node para construir o `Request`. undici valida `signal instanceof AbortSignal` contra a global do **Node nativo**, não do jsdom → `TypeError`.

**Fix canônico (resolve as duas causas com uma troca):**

Substituir `jsdom` por `happy-dom`. happy-dom (a) tem subtree leve sem deps em versões antigas → hoista limpo para `/node_modules/happy-dom` → vitest acha; (b) **não substitui** primitivas globais — usa `AbortController`/`AbortSignal` nativos do Node → undici aceita o signal.

```bash
# 1. Trocar dep
npm uninstall -w <ws> jsdom
npm install -D -w <ws> happy-dom

# 2. Editar vitest.config.ts no workspace
#    environment: "jsdom"  →  environment: "happy-dom"

# 3. Regenerar lock + verificar
npm install
npm run test -w <ws>
```

**Compatibilidade:** happy-dom suporta `window`, `document`, `matchMedia`, eventos DOM, MutationObserver, e a API básica que `@testing-library/react`, `@testing-library/jest-dom` e a maioria dos testes React precisa. Diverge do jsdom em algumas APIs raras de layout/rendering (canvas, getComputedStyle complexo, Range/Selection, document.fonts) — **antes de trocar**, grep nos testes:

```bash
grep -rE 'document\.fonts|getComputedStyle|scrollIntoView|HTMLCanvas|createRange|Selection|MutationObserver|IntersectionObserver|ResizeObserver' src/**/*.test.*
```

Se nenhum match (caso típico em apps React com Testing Library), troca é segura. Se houver match, ajuste o teste ou polifila a API antes de trocar.

**Verificação local pós-troca:**

```bash
npm exec -w <ws> -- vitest run --coverage
# Esperado:
# - sem "Cannot find package 'jsdom'"
# - sem "TypeError: signal AbortSignal"
# - todos os testes passando (ou só os esperados falhando)
```

**Quando NÃO trocar:** se a base de testes depende fortemente de APIs jsdom-only (canvas image diff, layout testing, complexa medição de DOM), avaliar polyfill em `setup.ts` substituindo `globalThis.AbortController` pelo nativo do Node antes do msw carregar — resolve só o Symptom B, não o A. Para Symptom A nesse caso: declarar `jsdom` como devDep da raiz para forçar hoist.

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
