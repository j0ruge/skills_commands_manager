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

**Cause:** Self-hosted runner with label `staging` or `production` is not online — **or** registrou online mas com a label errada (sintoma sutil: o runner aparece em `gh api .../actions/runners` mas com `["self-hosted","Linux","X64","default"]` em vez da label esperada).

**Diagnosis (runner via systemd no host):**

```bash
# On the runner server
sudo systemctl status actions.runner.*

# Restart if needed
sudo systemctl restart actions.runner.*.service
```

**Diagnosis (runner conteinerizado — `myoung34/github-runner`):**

```bash
docker ps --filter name=gh-runner --format "table {{.Names}}\t{{.Status}}"
docker inspect gh-runner --format "RestartCount={{.RestartCount}} ExitCode={{.State.ExitCode}}"
docker logs --tail 30 gh-runner
gh api /repos/<owner>/<repo>/actions/runners \
  --jq '.runners[] | {id, name, status, busy, labels: [.labels[].name]}'
```

Se `RestartCount > 0` e logs em loop com "Configuring → Settings Saved → fim" ou "Cannot configure the runner because it is already configured", **vá direto para `references/self-hosted-runner-docker.md`** — cobre os 6 gotchas específicos da imagem (CMD herdado zerado, env var `LABELS` vs `RUNNER_LABELS`, state residual em FS layer, `gpg --dearmor` em buildkit, registration token single-use, registros stale no GH).

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

**Cascade pode ter múltiplos níveis:** o segundo bug que aparece após o fix pode, por sua vez, estar mascarando um terceiro. No PR #6 que motivou este cenário, a cadeia foi: `Missing script: "exec"` (bug 1) mascarava `Cannot find package 'jsdom'` (bug 2) que mascarava `TypeError: signal AbortSignal` da interop msw v2 + undici (bug 3). Cada fix revelava o próximo. **Após cada fix, rode a suite localmente** antes de declarar vitória — não presuma que o segundo bug é o último.

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

---

## 8. `Cannot find package 'X' imported from /node_modules/<other-pkg>` em monorepo workspace

**Symptom:** CI ou execução local de uma ferramenta hoisted (vitest, eslint, tsc, qualquer binário na raiz do monorepo) falha com:

```text
Error: Cannot find package 'X' imported from
  <repo>/node_modules/<other-pkg>/dist/chunks/...

Test Files (N)  Tests no tests  Errors N errors
```

`X` é uma devDep declarada em `packages/<ws>/package.json` mas que falha resolver via Node ESM partindo de outra dep que está hoisted na raiz.

**Cause:** npm workspaces faz hoist de devDeps por padrão para `/node_modules/<pkg>` — mas só quando o subtree de transitive deps é compatível com a raiz. Quando `X` traz deps em versões antigas (ex.: `agent-base@6`, `cssstyle@2`, `tough-cookie@4`) que conflitam com versões já resolvidas na raiz, npm aninha o subtree inteiro em `packages/<ws>/node_modules/X` para evitar conflito.

A consequência: outra dep que está hoisted (ex.: vitest na raiz) faz `import 'X'` partindo de `/node_modules/<other-pkg>/...`. Resolução Node ESM sobe a árvore: `/node_modules/<other-pkg>/node_modules/X` ❌ → `/node_modules/X` ❌ → fail. **Nunca olha em `packages/<ws>/node_modules/`**, porque isso não está no caminho do importador.

**Diagnosis:**

```bash
# Confirma que X está aninhado, não hoisted
node -e "const l=require('./package-lock.json').packages; \
  console.log('node_modules/X (raiz):', !!l['node_modules/X']); \
  console.log('packages/<ws>/node_modules/X:', !!l['packages/<ws>/node_modules/X']);"

# Output esperado em caso do bug:
# node_modules/X (raiz): false
# packages/<ws>/node_modules/X: true

# Confirma que <other-pkg> está hoisted (importador)
node -e "console.log(require.resolve('<other-pkg>'))"
# Deve printar /node_modules/<other-pkg>/...
```

**Fixes (em ordem de preferência):**

1. **Trocar `X` por uma dep com subtree compatível** — mais limpo, resolve a causa raiz. Exemplo do PR que motivou esta entrada: trocar `jsdom@20` (subtree pesado) por `happy-dom@20` (subtree leve, dedupa) num monorepo com vitest. Ver `troubleshooting-frontend.md` cenário 8.

2. **Declarar `X` como devDep na raiz** — força hoist para `/node_modules/X`. Útil quando trocar a dep não é viável. Cuidado: muda a árvore de instalação — rode `npm install` e revise o diff do `package-lock.json`.

3. **`overrides` no package.json raiz** — força versões específicas das transitive deps que estão conflitando, permitindo dedup. Mais cirúrgico mas frágil:

   ```json
   {
     "overrides": {
       "agent-base": "^7.0.0",
       "cssstyle": "^4.0.0"
     }
   }
   ```

4. **Polyfill no setup do importador** — última opção, frágil. Por exemplo, se o importador é vitest e `X` é jsdom, polifilar o que jsdom traria em `setup.ts`. Resolve o sintoma, não a causa.

**Verificação pós-fix:**

```bash
npm install
npm ls X
# Esperado: X aparece deduped na raiz, não em packages/<ws>/

# E o comando que falhava agora roda:
npm run test -w <ws>
```

**Por que isso é dangeroso de diagnosticar:** o erro `Cannot find package 'X'` aponta para `<other-pkg>` no stack trace, não para a workspace que declarou `X`. Sem o passo de comparar `node_modules/X` vs `packages/<ws>/node_modules/X` no lock, parece bug do `<other-pkg>` ou versão errada de `X`. A causa real (hoisting frustrado) só aparece via inspeção do lock.

---

## 9. GitHub deploy keys são per-repo unique (transferRepo)

**Sintoma**: depois de transferir um repo (`old-org/repo` → `new-org/repo`), o servidor que clonava via deploy key não consegue mais clonar (`Permission denied (publickey)`). Você tenta adicionar a mesma chave SSH no novo repo via UI ou API:

```text
422 {"message":"Validation Failed","errors":[{"resource":"PublicKey","code":"custom","field":"key","message":"key is already in use"}]}
```

**Causa**: GitHub deploy keys são **per-repo unique**. A mesma `ssh-ed25519 ...` pubkey só pode estar registrada em um repo por vez. Transferir o repo NÃO migra automaticamente os deploy keys — eles ficam no repo-fantasma de origem e bloqueiam re-uso.

**Fix**: deletar a key no repo antigo, depois adicionar no novo.

```bash
# 1. Listar keys no repo antigo (ainda existe se foi transferRepo, ou se você cuidou de redirect)
gh api /repos/<old-owner>/<repo>/keys

# 2. Pegar id da chave que você quer migrar e deletar
gh api -X DELETE /repos/<old-owner>/<repo>/keys/<id>

# 3. Re-adicionar no repo novo
PUBKEY=$(ssh <host> 'cat ~/.ssh/<keyname>.pub')
gh api -X POST /repos/<new-owner>/<repo>/keys \
  -f title='<descrição>' -f "key=${PUBKEY}" -F read_only=true
```

**Variante "esqueci de salvar a privada"**: se o repo antigo desapareceu (foi deletado, não transferido) e a chave ficou órfã, gerar uma nova ed25519 no servidor é mais rápido do que tentar recuperar — `ssh-keygen -t ed25519 -f ~/.ssh/<keyname> -N ""` e adicionar a `.pub` resultante.

**Por que é fácil errar**: a UI do GitHub no repo novo aceita "Add deploy key", você cola, ele aceita o título, e só no Save é que aparece o 422 — sem indicar onde a chave está em uso. A API é mais explícita ("key is already in use") mas continua sem listar o repo conflitante. A correção é sempre "DELETE no antigo + POST no novo", sem atalho.

---

## 10. Operational gotchas — `.env` com leading whitespace + `sed -i`

**Sintoma**: você reescreveu uma linha do `.env` com `sed -i 's|^KEY=.*|KEY=newvalue|' .env`, o sed não retornou erro, mas a validação subsequente diz que `KEY` continua vazia / com valor antigo.

```bash
$ sed -i 's|^RUNNER_REGISTRATION_TOKEN=.*|RUNNER_REGISTRATION_TOKEN=ABC123|' infra/docker/.env
$ awk -F= 'NF>=2 {print $1"=("length(substr($0,index($0,"=")+1))" chars)"}' infra/docker/.env
 RUNNER_REGISTRATION_TOKEN=(0 chars)    # ← sed silenciou
```

**Causa**: o arquivo tem leading whitespace nas linhas (`  KEY=value` em vez de `KEY=value`). O regex `^KEY=` não casa porque não há `K` na coluna 0. Mas — e essa é a parte traiçoeira — `docker compose --env-file` **strip-a leading whitespace ao parsear**, então `${KEY}` em interpolações continua funcionando. O bug só aparece em ferramentas que fazem regex line-anchored sobre o arquivo bruto.

**Fontes comuns de leading whitespace**:

- Editor de YAML que reformata bloco indentado quando o usuário cola num heredoc dentro de YAML.
- Heredoc com `<<-` vs `<<` (o `<<-` strip-a só tabs, não spaces).
- Cópia de tutorial markdown onde o code block tinha indentação de lista (`- env:\n  KEY=value`).

**Fix canônico — reescrever o `.env` atomicamente via heredoc**:

```bash
cat > infra/docker/.env <<'ENV_EOF'
IMAGE_TAG=latest
POSTGRES_PASSWORD=...
RUNNER_REGISTRATION_TOKEN=$TOK
ENV_EOF
chmod 600 infra/docker/.env
```

**Validação rápida** (verifica que cada linha começa em coluna 0):

```bash
awk -F= '
  /^[[:space:]]/ {print "LEADING WHITESPACE: "$0; exit 1}
  NF>=2 {print $1"=("length(substr($0,index($0,"=")+1))" chars)"}
' infra/docker/.env
```

Se `LEADING WHITESPACE` aparece em qualquer linha, reescreva o arquivo do zero — sed não vai te ajudar.

**Por que isso confunde**: aplicações que usam o `.env` (docker-compose, dotenv-cli, vite, etc.) toleram o whitespace e funcionam. Você "vê" o secret carregando no container e assume que o arquivo está OK. Só percebe quando precisa fazer manutenção via sed/awk e o regex não casa, ou quando uma ferramenta mais estrita (alguns parsers Go/Rust) recusa ler.
