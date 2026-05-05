# Troubleshooting — Shared Scenarios (Infrastructure)

Infrastructure scenarios that apply to both backend and frontend.

---

## 1. `unauthorized` on GHCR (Self-Hosted Runner)

**Message:**

```text
Error response from daemon: Head "https://ghcr.io/v2/.../manifests/...": unauthorized
```

**Cause:** The Deploy job on the self-hosted runner did not authenticate with GHCR before `docker compose pull`. Each GitHub Actions job has an isolated context — the login performed in the Build & Push job does not persist to the Deploy job.

**Diagnosis:**

```bash
# Check if the deploy job has a login step before the pull
grep -A5 "Login to GHCR" .github/workflows/cd-staging.yml
```

**Fix (workflow — recommended):**

Add `docker/login-action@v3` in the Deploy job, before `docker compose pull`:

```yaml
- name: Login to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

Prefer `docker/login-action@v3` over manual `docker login` because:
- **Automatic logout** in the post-step (cleans up credentials even if the job fails)
- **Isolated config** per job (avoids race conditions in `~/.docker/config.json`)
- **Credential masking** in logs via `@actions/core`

**Alternative fix (manual on the server — for debugging only):**

```bash
echo "$TOKEN" | docker login ghcr.io -u USERNAME --password-stdin
```

---

## 2. `network declared as external, but could not be found`

**Message:**

```text
network <name> declared as external, but could not be found
```

**Cause:** The Docker network name in `docker-compose.yml` (via the `NGINX_NETWORK_NAME` secret) does not match the actual network name created by nginx-proxy. The name depends on the compose directory (e.g., `nginx-proxy_default`, `proxy_default`).

**Diagnosis:**

```bash
docker network ls | grep proxy
```

**Fix:**

```bash
# Find the correct network name
docker network ls | grep proxy

# Update the secret with the correct name
gh secret set NGINX_NETWORK_NAME --env staging --body "correct_network_name"
```

---

## 3. `ERR_SSL_VERSION_OR_CIPHER_MISMATCH`

**Symptom:** The browser returns `ERR_SSL_VERSION_OR_CIPHER_MISMATCH`. `curl -svk` shows `sslv3 alert handshake failure`.

**Cause:** nginx-proxy responds on port 443, but **does not have a valid certificate** for the domain — it serves the default (self-signed) certificate. Let's Encrypt **did not issue** the certificate because the DNS does not point to the server IP.

**Diagnosis:**

```bash
# 1. Check DNS
dig domain +short
# Should resolve to the server IP

# 2. Test TLS handshake
curl -svk https://domain 2>&1 | grep -E "SSL|alert|subject"

# 3. Test port 80 (HTTP-01 challenge)
curl -sv http://domain 2>&1 | head -10
```

**Fix:**

1. **DNS not pointing:** Configure A/CNAME record to the server IP
2. **acme-companion not running:** Check if the `nginx-proxy-acme` container is running
3. **Port 80 blocked:** Open port 80 in the firewall (required for the HTTP-01 challenge)
4. **Certificate pending:** Restart the acme-companion and wait

---

## 4. Runner Offline / Labels Not Found

**Message:**

```text
No runner matching the specified labels was found
```

**Cause:** Self-hosted runner with label `staging` or `production` is not online.

**Diagnosis:**

```bash
# On the runner server
sudo systemctl status actions.runner.*

# Restart if needed
sudo systemctl restart actions.runner.*.service
```

**Monitor queue:**

```bash
gh run list --status queued
gh run list --status in_progress
```

---

## 5. Concurrency Group Blocking Deploys

**Symptom:** Deploy stays "queued" indefinitely.

**Cause:** With `cancel-in-progress: false`, a pending deploy blocks the next one. If the runner is offline, the queue can accumulate.

**Diagnosis:**

```bash
# List pending runs
gh run list --status queued
gh run list --status in_progress

# Cancel blocked run
gh run cancel <run-id>
```

**Prevention:** Monitor via `gh run list` before triggering new deploys.

---

## 6. `Missing script: "exec"` em workspace de monorepo npm

**Symptom:** Step de CI que invoca um binário hoisted/devDep de um workspace falha em segundos com:

```text
npm error Missing script: "exec"
npm error workspace @<org>/<pkg>@<ver>
##[error]Process completed with exit code 1.
```

**Cause:** Sintaxe `npm run -w <ws> exec -- <cmd>` está errada. `npm run` só executa scripts declarados em `package.json` do workspace. Como nenhum workspace define `"exec"`, o npm aborta antes de qualquer outra coisa. `exec` é **subcomando** do `npm` (`npm exec`), não um script.

**Common occurrences:**

- `npm run -w @pkg/frontend exec -- tsc --noEmit`
- `npm run -w @pkg/frontend exec -- openapi-typescript ...`
- `npm run -w @pkg/frontend exec -- playwright install --with-deps chromium`
- `npm run -w @pkg/backend exec -- tsc --noEmit`

**Fix:** Trocar `npm run -w <ws> exec --` por `npm exec -w <ws> --`:

```yaml
# ❌ Antes (Missing script: "exec")
- run: npm run -w @pkg/frontend exec -- tsc --noEmit

# ✅ Depois
- run: npm exec -w @pkg/frontend -- tsc --noEmit
```

**Why this is dangerous beyond the obvious:** o erro é **fail-fast** — todos os steps subsequentes do job (test, build, etc.) não rodam. Falhas latentes nos steps escondidos (test broken, codegen drift, type errors em test files) **só aparecem depois** que esse fix é aplicado. Ao consertar a sintaxe, antecipe que outros vermelhos podem surgir — não são regressões, eram pré-existentes mascarados.

**Verificação local:**

```bash
npm exec -w <ws> -- tsc --version
npm exec -w <ws> -- playwright --version
```

---

## 7. `ESLint couldn't find an eslint.config.(js|mjs|cjs) file`

**Symptom:** Step `Lint` de um workspace falha com:

```text
Oops! Something went wrong! :(
ESLint: 9.x.x
ESLint couldn't find an eslint.config.(js|mjs|cjs) file.
```

**Cause:** ESLint v9 removeu o auto-detect de `.eslintrc.*` (legacy config). Em monorepo, ter `eslint.config.js` em **um** workspace (ex.: `packages/frontend`) **não** propaga aos siblings (`packages/backend`, `packages/idp`). Cada workspace que rode `eslint` precisa do próprio flat config.

**Anti-pattern comum:** equipe migra um pacote pra ESLint v9, esquece dos outros. CI passa naquele e quebra silenciosamente nos demais até alguém olhar logs.

**Fix:** criar `eslint.config.js` em cada workspace. Pacotes Node-only (backend, IdP, scripts) usam variante sem React:

```js
// packages/<node-pkg>/eslint.config.js
import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "src/**/_generated/**", "node_modules"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.ts"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.node },
    },
    rules: {
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
);
```

**Diferenças vs config de frontend (React):**

- Sem `eslint-plugin-react-hooks` / `eslint-plugin-react-refresh`.
- `globals.node` em vez de `globals.browser`.
- `files: ["**/*.ts"]` em vez de `**/*.{ts,tsx}`.

**Hoisting:** `@eslint/js`, `globals`, `typescript-eslint` instalados como devDeps em **um** workspace ficam hoisted no `node_modules` da raiz e resolvem nos siblings sem reinstalar. Para extração futura para repo próprio, declare explicitamente: `npm install -D @eslint/js globals typescript-eslint -w <ws>`.

**Verificação local:**

```bash
npm run lint -w <ws>   # deve sair com exit 0 (warnings ok)
```
