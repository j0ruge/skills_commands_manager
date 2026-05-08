# Zitadel — Troubleshooting Lookup Table

Hit an error and want to know what to fix? Search this file. Each row is keyed on the error message Zitadel actually returns.

## Setup / docker-compose errors

### `open /current-dir/admin.pat: permission denied`

**Cause**: `/current-dir` volume is owned by root (left behind by a previous `zitadel-init` run). Zitadel runs as uid 1000 and can't write the PAT file.

**Fix**: tear down volume + chown to 1000:1000:

```bash
docker compose -f docker-compose.zitadel.yml down -v
docker run --rm -v "$(pwd)/zitadel/local:/work" alpine sh -c \
  "rm -rf /work/* /work/.* 2>/dev/null; chown 1000:1000 /work && chmod 0777 /work"
docker compose -f docker-compose.zitadel.yml up -d
```

See `docker-compose-bootstrap.md §2`. Use `scripts/reset-zitadel.sh` for the full sequence.

### `Errors.Instance.Domain.AlreadyExists`

**Cause**: A previous `setup` run partially succeeded — it inserted some events but failed before completion. Re-running fails because the duplicate-detection unique constraint hits the half-inserted records.

**Fix**: there's no recovery. Wipe the Zitadel Postgres volume:

```bash
docker compose -f docker-compose.zitadel.yml down -v
docker compose -f docker-compose.zitadel.yml up -d
```

This is data-destructive — only safe in dev. In production, take a snapshot before running `setup`.

### `setup failed, skipping cleanup` followed by container restart loop

**Cause**: usually permission denied on PAT path (see first row). Confirm by tailing logs:

```bash
docker logs <zitadel-container> 2>&1 | grep -i "setup failed"
```

If the underlying error is something else, address it directly — Zitadel's setup is single-shot and either succeeds or fails the whole boot.

### PAT file never appears at the expected path

**Cause**: most likely `ZITADEL_FIRSTINSTANCE_*` env vars are on the wrong service (`zitadel-init` instead of `zitadel`), so they're ignored. The init container only does schema migrations; setup runs from the main `zitadel` service via `start-from-init`.

**Fix**: see `docker-compose-bootstrap.md §1`. Move all `FIRSTINSTANCE_*` envs to the main `zitadel` service. After fixing, re-run with `down -v` to retry setup cleanly.

## API errors

### Hosted UI returns `{"code":5,"message":"Not Found"}` after `signinRedirect`

**Symptom**: SPA does `signinRedirect`; browser lands at `http://<external-domain>/ui/v2/login/login?authRequest=V2_...` and shows the JSON above. No Zitadel login page is rendered.

**Cause**: The instance feature flag `loginV2.required` defaults to `true` in Zitadel ≥ v3, but Login UI v2 is a **separate Next.js app** (`zitadel/typescript` repo) that you must deploy yourself. The bundled binary only ships Login UI v1 at `/ui/login/`. With the flag on but v2 not deployed, every auth request 404s.

**Fix (recommended — just use v1)**:

```bash
PAT=$(cat <volume>/admin.pat)
curl -sS -X PUT http://<external-domain>/v2/features/instance \
  -H "Authorization: Bearer $PAT" -H 'Content-Type: application/json' \
  -d '{"loginV2":{"required":false}}'
```

Belt-and-braces: also set `loginVersion: {loginV1: {}}` on the OIDC app payload at bootstrap (see `api-cheatsheet.md §"Create OIDC application"`). The app-level flag **alone** does NOT override the instance flag — you must clear the instance flag.

**Fix (alternative — deploy v2)**: stand up the `zitadel/typescript` Login UI container alongside Zitadel. Out of scope for this skill; see upstream docs.

### `/oauth/v2/authorize?...&prompt=none` returns 400 in a loop / SPA stuck on "verifying session…"

**Symptom**: After the first successful login, the SPA's silent-renew iframe (`react-oidc-context` `automaticSilentRenew=true`) requests `/oauth/v2/authorize?...&redirect_uri=.../silent-renew&prompt=none` every ~10s and gets `400`. The protected route oscillates between rendering and showing a "verifying session…" spinner, and authenticated API calls flap between 200 and 401.

**Cause**: The `/silent-renew` redirect URI was never registered in the OIDC app's `redirectUris`. Zitadel rejects any `redirect_uri` that isn't a literal match.

**Fix (now)**:

```bash
PAT=$(cat <volume>/admin.pat); ORG=...; PROJECT=...; APP=...
curl -sS -X PUT http://<external-domain>/management/v1/projects/$PROJECT/apps/$APP/oidc_config \
  -H "Authorization: Bearer $PAT" -H "x-zitadel-orgid: $ORG" -H 'Content-Type: application/json' \
  -d '{"redirectUris":["http://localhost:5173/auth/callback","http://localhost:5173/silent-renew"], ...rest}'
```

**Fix (forever)**: include `/silent-renew` in the `REDIRECT_URIS` constant of your bootstrap script so a fresh re-bootstrap doesn't lose it. See `assets/bootstrap-zitadel.ts`.

### SPA stuck on "Verifying session…" with no IdP-side error — boot-time `signinSilent` recursion

**Symptom**: Different from the loop above (which makes 400s every ~10s). Here the page sits on a loading placeholder forever after F5; the network tab shows a single `/oauth/v2/authorize?prompt=none` that succeeds (302 → callback → 200 on `/silent-renew?code=...`), but the parent never receives the `signinSilentCallback` postMessage. The `signinSilent()` Promise neither resolves nor rejects. Specific to setups where the SPA does its own boot-time `auth.signinSilent()` (typically because `userStore = InMemoryWebStorage` and you want F5 to recover the session).

**Cause**: `<AuthProvider>` (or whatever component invokes `signinSilent`) wraps the entire `<Routes>` tree, including the `/silent-renew` route. When the iframe loads `/silent-renew`, it re-mounts the whole app — including the provider — which triggers another `signinSilent`, which opens another iframe, and so on. The original parent's Promise is never settled because no descendant ever reaches its `signinSilentCallback`.

**Fix**: Skip the boot-time renew when the current route is part of the auth flow (`/login`, `/silent-renew`, `/auth/callback`) AND when the page is itself an iframe (`window.self !== window.top`). Both checks are necessary — the route-name check covers the first iframe load, the iframe check covers cases where the IdP redirects the iframe to a path that isn't in your route table. See `references/spa-recipes.md §"Recipe 1 — Boot-time silent renew with InMemoryWebStorage" §"Trap 1"`.

A second, independent gotcha lives in the same recipe: if you protect the boot useEffect with the textbook `let cancelled = false; return () => { cancelled = true; }` pattern, **React StrictMode breaks it** — the cleanup runs after the first effect, sets `cancelled = true` in the first run's closure, and when the Promise resolves it skips `setBootstrapping(false)`. Same lockup symptom, different cause. Use a ref to gate re-execution and let the state set fire on the second run; do not branch on a closure-scoped `cancelled` flag. See `spa-recipes.md §"Trap 2"`.

### Logout returns `error=invalid_request post_logout_redirect_uri invalid` / SPA lands on `/login?error=invalid_request`

**Symptom**: Clicking "Sign out" / "Sair" on the SPA. Browser navigates to `<idp>/oidc/v1/end_session?id_token_hint=…&post_logout_redirect_uri=…&state=…` and Zitadel responds with a JSON or HTML error page:

```json
{"error":"invalid_request","error_description":"post_logout_redirect_uri invalid"}
```

The user does not return to the SPA — they're stranded on the IdP error screen, or land on `/login?error=invalid_request` if your SPA happens to render the error param.

**Cause**: Same exact-match rule as the silent-renew quirk — Zitadel rejects any `post_logout_redirect_uri` that isn't a literal entry in the OIDC app's `postLogoutRedirectUris`. The most common drift is registering `${WEB_BASE}/` (just the root) at bootstrap time, while the SPA sends `${WEB_BASE}/login` because `VITE_OIDC_POST_LOGOUT_REDIRECT_URI` (or equivalent) was configured to land users on the login page after logout. Trailing-slash mismatches (`/login` vs `/login/`) and scheme/port drift (HTTP/HTTPS, `:5173` vs `:5443` after adding a TLS proxy) cause the same failure.

**Fix (now)**:

```bash
PAT=$(cat <volume>/admin.pat); ORG=...; PROJECT=...; APP=...
# Get current config first so you don't blow away other fields
curl -sS -H "Authorization: Bearer $PAT" -H "x-zitadel-orgid: $ORG" \
  http://<external-domain>/management/v1/projects/$PROJECT/apps/$APP > /tmp/app.json
# Then PUT the merged config including postLogoutRedirectUris
curl -sS -X PUT http://<external-domain>/management/v1/projects/$PROJECT/apps/$APP/oidc_config \
  -H "Authorization: Bearer $PAT" -H "x-zitadel-orgid: $ORG" -H 'Content-Type: application/json' \
  -d '{"redirectUris":["http://localhost:5173/auth/callback","http://localhost:5173/silent-renew"],"postLogoutRedirectUris":["http://localhost:5173/login","http://localhost:5173/"], ...rest}'
```

Register **both** the page-specific URI (`/login`) and the bare root (`/`) — costs nothing and covers any future consumer that defaults to root.

**Fix (forever)**: align the bootstrap constant with what the SPA actually sends. The cleanest convention: the bootstrap script reads `OIDC_POST_LOGOUT_URIS` from env and the launcher (`dev.sh` etc.) sets it to the same value as `VITE_OIDC_POST_LOGOUT_REDIRECT_URI`, comma-joined with the bare root for safety:

```bash
OIDC_POST_LOGOUT_URIS="${WEB_BASE}/login,${WEB_BASE}/"
```

If your launcher previously skipped the bootstrap on re-runs (to "save 30s"), the URI change won't propagate without a `--reset-zitadel`. Either drop the skip optimization (the bootstrap is idempotent and treats `COMMAND-1m88i "No changes"` as a no-op — quirk #14) or extend the skip key beyond just `EXTERNAL_FULL` to include a hash of the OIDC URIs.

### `redirect_uri missing in client configuration` after multi-app refactor regression (quirk 23)

**Symptom**: Login na hosted Login UI funciona normalmente — usuário insere senha, clica em "Entrar". Antes do callback render no SPA, o Zitadel responde:

```
{
  "error": "invalid_request",
  "error_description": "The requested redirect_uri is missing in the client configuration. If you have any questions, you may contact the administrator of the application."
}
```

A URL no browser mostra `redirect_uri=https://192.168.0.X.sslip.io:5443/auth/callback` (host LAN dinâmico do `dev.sh`), mas o `oidc_config` da App no Zitadel só lista `http://localhost:5173/auth/callback` e `https://app.example.com/auth/callback` (hosts do YAML).

**Quando aparece**: Imediatamente após uma refatoração single-app → multi-app YAML. Antes da refatoração, login funcionava com qualquer host LAN (mkcert+proxy reverso). Depois, falha em qualquer host que não seja o canônico do YAML.

**Cause**: O bootstrap refatorado prioriza `applications[].redirectUris` do YAML sobre os env vars `OIDC_REDIRECT_URIS`/`OIDC_POST_LOGOUT_URIS` que o `dev.sh` popula a cada boot com o IP LAN atual. O YAML tem uma lista estática (`localhost:5173`, host de prod); o env do `dev.sh` tem o host real e dinâmico. Como YAML wins, o `oidc_config` no Zitadel ficou registrado só com URIs do YAML; o callback do SPA bate em URI desconhecido pra Zitadel → byte-mismatch (família dos quirks 10 e 18, gatilho diferente).

**Fix canônico — precedência env > YAML > hardcoded fallback:**

```typescript
async function ensureAppFromConfig(orgId, projectId, app) {
  const envRedirects = process.env.OIDC_REDIRECT_URIS;
  const envPostLogout = process.env.OIDC_POST_LOGOUT_URIS;

  // Dev (dev.sh setou env): env DOMINA — ignora YAML para não conflitar
  // com host LAN dinâmico. Em prod o env não é setado, YAML domina.
  const redirects =
    envRedirects !== undefined && envRedirects.trim() !== ''
      ? REDIRECT_URIS_FROM_ENV
      : app.redirectUris.length > 0
        ? app.redirectUris
        : DEFAULT_HARDCODED;

  const postLogout =
    envPostLogout !== undefined && envPostLogout.trim() !== ''
      ? POST_LOGOUT_FROM_ENV
      : app.postLogoutRedirectUris.length > 0
        ? app.postLogoutRedirectUris
        : DEFAULT_HARDCODED;

  return ensureAppByName(orgId, projectId, app.name, redirects, postLogout);
}
```

A ordem é: **env explícito > YAML não-vazio > fallback hardcoded**. Em produção (`cd-production.yml` rodando `--profile bootstrap`) o env não é setado e o YAML domina — comportamento canônico. Em dev (`dev.sh` em LAN HTTPS) o env vence e os hosts dinâmicos são propagados.

**Sincronização**: bootstrap idempotente faz `PUT /oidc_config` no boot do `dev.sh`, então re-rodar `./dev.sh` aplica o fix imediatamente — sem `--reset-zitadel` (quirk 14: `COMMAND-1m88i` no-op continua coberto). Validar nos logs que aparece `[app] synced oidc_config for "<app-name>"` (não `oidc_config sem mudanças`).

**Por que não basta ter o host LAN no YAML**: o IP da LAN muda entre redes (escritório, casa, hotspot do celular). YAML estático nunca acompanha — env-driven é a única solução escalável.

### Backend rejects JWT 401 even though `iss`/`aud`/`exp`/signature are correct

**Symptom**: Token decodes cleanly (`jwt.io` shows valid `iss`, `aud` containing the projectId, `exp` in the future, signature valid against JWKS). Backend still returns `401 "Token inválido"` (or your equivalent error message). Response time is sub-10ms — the validator hasn't even hit JWKS.

**Cause**: Your claim mapper is failing **after** signature validation. Most common reason: it requires `name`, `preferred_username`, `email`, or `urn:zitadel:iam:org:id` and returns `null` when they're absent. **Zitadel access tokens are minimal by default — those claims live in the id_token and `/oidc/v1/userinfo`, not in the access token**, even with `idTokenUserinfoAssertion: true`.

**Fix**: defensive fallbacks in the mapper (see `token-validation.md §"Access token vs ID token"`):

```typescript
const operatorName =
  payload.name ?? payload.preferred_username ?? payload.email ?? payload.sub;
const tenantId =
  payload['urn:zitadel:iam:org:id'] ?? options.defaultTenant ?? '';
```

Don't try to enrich the AT with profile claims — that's not how OAuth/OIDC works. Either accept the minimal AT (recommended) or call userinfo from the backend (extra round-trip per request, generally not worth it).

### 401 storm with apparently-valid JWT — dashboard "flashes", every `/api` call returns 401, then 429

**Symptom**: Right after a successful login, every authenticated SPA request to your backend returns `401`. The user sees the dashboard render briefly, then unmount, then re-render — visually it "flashes". The browser's network tab shows the same three or four queries firing 5–10× per second. Eventually the backend rate-limit (e.g. `express-rate-limit` 120/min) kicks in and replies `429`. The JWT, decoded by hand, looks **perfect**: signature valid, `iss` matches `AUTH_ISSUER`, `aud` array contains the `projectId`, `exp` is hours away.

**The render storm itself is a symptom, not the root cause.** The chain is: backend returns 401 → SPA's axios/fetch wrapper triggers silent renew → renew succeeds (Zitadel issues a new token) → SPA retries → 401 again → silent renew again → React Query refetches all stale queries on every state change → hammer the API. Identifying *why* the backend rejects the token is the actual fix; lifting the rate limit only hides the storm.

**Cause 1 — Self-signed JWKS endpoint and Node OS-level CA**

Most common when running Zitadel behind a reverse proxy with a local cert (mkcert, internal CA) for HTTPS LAN testing. The backend uses `createRemoteJWKSet(new URL(jwksUrl))` (jose) — that's a plain Node `fetch` against `https://<external-domain>/oauth/v2/keys`, which uses the Node TLS stack. Node defaults to the OS trust store and **does not** read the mkcert root unless you tell it to.

When the TLS handshake fails, jose surfaces it as a generic `JWKSNoMatchingKey` / `JWSSignatureVerificationFailed` — *not* "TLS error". Your backend logs show 401s with no useful reason; tracing into jose reveals the JWKS object is empty.

**Fix**: pass the local root CA to Node when starting the backend:

```bash
NODE_EXTRA_CA_CERTS="$(mkcert -CAROOT)/rootCA.pem" node dist/server.js
# or in dev:
NODE_EXTRA_CA_CERTS="$(mkcert -CAROOT)/rootCA.pem" npm run dev
```

Set this in your dev launcher (`dev.sh`, `docker-compose` `environment:`, systemd unit) so the backend always trusts the dev CA when TLS is local. See `token-validation.md §"Trusting a self-signed JWKS endpoint from Node"`.

**Cause 2 — Stale `AUTH_AUDIENCE`/`OIDC_AUDIENCE` after a Zitadel volume reset**

Equally common after `docker compose down -v` or any "reset Zitadel" action. The bootstrap re-runs and writes a **new** `projectId` + `clientId` into `bootstrap.json`. Anything still pointing at the old projectId (backend `.env`, env vars baked into Docker images, CI secrets) starts rejecting every JWT for `aud` mismatch. Same silent 401 storm — no clear error.

**Fix**: never hardcode `OIDC_AUDIENCE` / `OIDC_CLIENT_ID`. Always re-derive from `infra/.../bootstrap.json` at boot. A reliable pattern:

```bash
# In dev.sh / start script — runs on every boot
PROJECT_ID="$(jq -r .projectId bootstrap.json)"
CLIENT_ID="$(jq -r .clientId bootstrap.json)"
sed -i "s|^AUTH_AUDIENCE=.*|AUTH_AUDIENCE=${PROJECT_ID}|"  packages/backend/.env
sed -i "s|^VITE_OIDC_CLIENT_ID=.*|VITE_OIDC_CLIENT_ID=${CLIENT_ID}|" .env.local
```

See `api-cheatsheet.md §"Re-reading bootstrap output after volume reset"`.

**Cause 3 — Stale runtime: bootstrap.json + .env corretos, processo em execução com env+JWKS antigo na heap**

A pegadinha mais sutil dessa família, e a que reaparece toda vez que alguém faz `--reset-zitadel` num ambiente de dev de longa duração. A sequência:

1. Você roda `./dev.sh --reset-zitadel`. Bootstrap regenera `projectId` + `clientId` em `bootstrap.json`. Launcher patcha `AUTH_AUDIENCE` no `.env`. ✅ Tudo certo no disco.
2. **Mas o processo `tsx watch` (ou `node`, `nodemon`, qualquer dev runner) que estava rodando antes do reset não morreu.** `tsx watch` re-restarta em mudanças em `src/**`, não em `.env` — então o env antigo continua na memória.
3. Pior: a JWKS foi baixada na primeira request da sessão anterior e está cacheada em memória pelo `createRemoteJWKSet`. Como `--reset-zitadel` apaga o volume e regenera as **signing keys da instância**, os tokens novos têm `kid` desconhecido pra esse cache.
4. Resultado: 401 storm idêntico ao cause 1/2, mas `bootstrap.json`, `.env` e o disco inteiro estão consistentes. Diff por inspeção visual não acha nada.

Pior ainda em projetos de dev de longa duração: cada sessão que termina sem `Ctrl+C` no `dev.sh` deixa um `tsx watch` órfão no PID space. Acumulam ao longo de dias. No projeto JRC encontramos **8 instâncias paralelas** rodando, das quais 5 com env de bootstraps anteriores. Só uma ia responder pra um dado request — qual? Race.

**Fix em 3 camadas** (defesa em profundidade — esta é a parte que falta na maioria dos guides):

1. **Disco em sincronia**: launcher patcha `AUTH_AUDIENCE` no `.env` a partir do `bootstrap.json` em todo boot (cause 2 já cobre isso).
2. **Processos em sincronia**: launcher mata por padrão de cmdline qualquer dev runner antigo antes de subir o novo. Padrão pgrep robusto, ex.: `pgrep -af 'packages/backend.*server\.ts|vite/bin/vite\.js|\.vite\.config\.lan'`. Atenção ao **ordering** do regex: a cmdline real é `node .../packages/backend/.../tsx watch ... src/server.ts`, então `tsx.*packages/backend` nunca casa (tsx vem depois). Use `packages/backend.*server\.ts`.
3. **Boot-time sanity check no backend**: comparar `AUTH_AUDIENCE` em runtime vs `projectId` em `bootstrap.json` (se acessível) e logar erro explícito em caso de divergência. Warn-only — em prod o `bootstrap.json` não existe e o check é silencioso. Mas em dev o erro vira "[auth-sanity] AUTH_AUDIENCE=X divergente do bootstrap.json (projectId=Y). Pare o backend e re-rode `./dev.sh`." — diagnóstico em 5s em vez de 30min.

**Diagnostic when you can't tell which cause**: turn on `LOG_LEVEL=trace` (or equivalent) on jose and curl the JWKS endpoint from the backend host with `curl --cacert "$(mkcert -CAROOT)/rootCA.pem" https://<external-domain>/oauth/v2/keys`. If curl with the local CA succeeds but the backend can't reach JWKS, it's cause 1. If JWKS works fine and `jwt verify` still fails, decode the live access token and compare its `aud` to `AUTH_AUDIENCE` — mismatch is cause 2 ou 3 (cheque `pgrep -af` da cmdline do dev runner pra ver quantos processos tem rodando — `>1` é cause 3).

### 401 storm starting ~10 min after backend restart, with apparently-valid JWT

**Symptom**: Right after every backend restart, authenticated requests work fine for ~10 minutes. Then, abruptly, *every* `/api` call starts returning `401`. The dashboard, queries, mutations — all of them. Logging out and back in produces a fresh JWT but the new token also fails immediately. Nothing changed about the request shape, the token signature, or the `aud`/`iss`/`exp` — they all still verify by hand. The pattern is **time-correlated to the backend's uptime**, not to anything the user did.

If you let the symptom continue, the SPA's silent-renew machinery starts firing repeatedly, eventually triggering Zitadel's RT reuse detection — which **revokes the entire session**. After that point, even fresh logins die instantly because the new tokens are issued under a session Zitadel just marked as compromised. The error cascade looks like 401-storm-revokes-session (see Recipe in `spa-recipes.md`), but the actual root cause is upstream.

**Cause — Backend container can't reach the JWKS endpoint after the cache TTL expires (Quirk 36)**

`jose.createRemoteJWKSet` caches the JWKS for `cacheMaxAge: 600s` (default 10 minutes). Within that window, every JWT verification reuses the cached keys — no network call, no failure mode. After the TTL, the next `jwtVerify()` triggers a `reload()` that does an ordinary Node `fetch` against `JWKS_URL`. If that fetch fails, jose raises a `JOSEError`, and the validator's catch block throws `InvalidTokenError` → 401.

In single-host self-hosted setups (backend, frontend, Zitadel all on the same VPS), the backend container resolves `idp.<domain>` to the host's **public** IP via DNS. On VPS providers with unreliable hairpin NAT (DNS → external IP → loopback to local nginx-proxy), the reload fetch silently fails — the TCP handshake never completes. The result is the time-correlated symptom: works for the cache window, then 401-storms.

**Diagnose in 60 seconds**:

```bash
# 1. What does the backend resolve?
docker exec <backend> getent hosts idp.<domain>
# Public IP (e.g. 203.0.113.42)  → hairpin NAT path; this is the bug.
# Bridge IP   (e.g. 172.17.0.1)  → host-gateway path; not this cause.

# 2. Can it reach JWKS right now?
docker exec <backend> wget -qO- --timeout=10 https://idp.<domain>/oauth/v2/keys | head -c 200
# Empty / timeout → reachability broken.

# 3. Confirm the JOSE error is firing:
docker logs <backend> --tail 100 | grep '\[auth\] JOSE'
# Any `code=ERR_JOSE_*` line right after the 10-min mark confirms.
```

**Fix — `extra_hosts` mapping the IdP hostname to the docker bridge** (in `docker-compose.prod.yml`, on the backend service):

```yaml
services:
  backend:
    # ...
    extra_hosts:
      - "idp.<domain>:host-gateway"
```

This makes the backend resolve `idp.<domain>` to the docker bridge IP — the same path external traffic takes, where the host's nginx-proxy listens on 443. JWKS reloads succeed indefinitely.

**Apply the same mapping to ANY co-located container that talks to the IdP**: bootstrap/seed containers, observability sidecars, the runner that runs CD jobs, etc. It's a per-service setting in compose — easy to forget on a new container and rediscover the symptom 10 min later.

**Why `warn`, not `error`, in the validator's catch block**: the same `JOSEError` path also fires for malformed tokens from clients (attacker probing, old SPA bundles holding stale tokens, clock skew on the client). Logging at `error` is a log-spam vector; `warn` keeps the diagnostic available without creating noise. See `token-validation.md §"Logging tip"`.

This is the third documented cause of "401-storm with apparently-valid JWT" in this skill — quirks 12 (self-signed JWKS over HTTPS, NODE_EXTRA_CA_CERTS missing), 13 (stale `clientId`/`AUTH_AUDIENCE` after volume reset), and now 36 (backend can't reach JWKS after TTL via hairpin NAT). Same symptom, different network/state layers — the diagnose-in-3-commands ladder above distinguishes them.

### `signinRedirect()` does nothing — clicking "Entrar" / "Login" produces no console error, no navigation, no network request

**Symptom**: SPA's login button is wired to `auth.signinRedirect()` from `react-oidc-context` (or equivalent). Clicking it: nothing happens. No console error, no warning, no redirect. DevTools network tab shows zero new requests after the click. Repeating the click does nothing.

**Cause**: the SPA is hosted at an HTTP origin **other than `localhost`/`127.0.0.1`** (e.g. `http://192.168.0.50:5173`, `http://my-dev-host:5173`). Browsers expose `window.crypto.subtle` only in **secure contexts**. The HTTP-on-localhost exception is just that — an exception for `localhost`/`127.0.0.1`, nothing else. PKCE in `oidc-client-ts` calls `crypto.subtle.digest()` to compute the code challenge; outside a secure context it throws `Crypto.subtle is available only in secure contexts (HTTPS)`.

The reason it's silent: `react-oidc-context`'s typical caller is `void auth.signinRedirect(...)`, which discards the rejected promise. No console log, no error event. The user sees a button that does nothing.

**Fix**: serve the SPA over HTTPS even in dev/LAN setups. The cleanest local recipe: mkcert + reverse proxy (Caddy/NGINX/Traefik) terminating TLS in front of the dev server. Apply the same to your Zitadel external URL and to the backend (mixed-content blocks otherwise — once the SPA is HTTPS, it cannot call HTTP backends). See `docker-compose-bootstrap.md §"TLS terminated by reverse proxy"`.

**Diagnostic**: run this in the SPA's DevTools console — `typeof crypto.subtle` returns `"undefined"` outside a secure context, `"object"` inside one. Confirms the diagnosis in two seconds. To see the actual rejection at runtime, monkey-patch the `signinRedirect` call temporarily: `await auth.signinRedirect(...).catch(e => console.error('SIGN_IN_FAILED', e))`.

### MFA setup re-prompts every login despite `forceMfa: false`

**Symptom**: Login policy has `forceMfa: false`, but every login still shows the "Set up 2-factor authentication" wizard with a "Skip" button. Annoying UX even when users skip.

**Cause**: `MfaInitSkipLifetime` defaults to **30 days**. Even after a user clicks "Skip", Zitadel will re-prompt the next session as soon as the skip lifetime expires.

**Fix (full opt-out for the V0)**:

```bash
PAT=$(cat <volume>/admin.pat); ORG=...
curl -sS -X PUT http://<external-domain>/admin/v1/policies/login \
  -H "Authorization: Bearer $PAT" -H "x-zitadel-orgid: $ORG" -H 'Content-Type: application/json' \
  -d '{"mfaInitSkipLifetime":"0s", ...rest of current policy}'
```

`PUT` requires the full policy body; `GET /admin/v1/policies/login` first to fetch current values, then merge.

**Fix (alternative)**: leave the prompt; users click "Skip" once and the cookie carries them through the lifetime window. Not great UX but zero-config.

### `Instance not found. Make sure you got the domain right.` (with `unable to set instance using origin ...`)

**Cause**: your client is calling Zitadel with a URL that doesn't match `ZITADEL_EXTERNALDOMAIN`. Common when calling `http://127.0.0.1:8080` while external domain is `127.0.0.1.sslip.io`.

**Fix**: use the external domain in your URL: `http://127.0.0.1.sslip.io:8080`. Node's `fetch` strips overrides of the `Host` header. See `docker-compose-bootstrap.md §3`.

### `Organisation doesn't exist (AUTH-Bs7Ds)`

**Cause**: you sent a non-numeric value in `x-zitadel-orgid` (e.g., your domain tenantId `"JRC"` instead of the numeric `370503937624637443`).

**Fix**: build a tenant→orgId translation layer in your adapter. See `tenant-org-mapping.md`.

### `User could not be found (COMMAND-3M9ds)` on `_deactivate` or `_reactivate`

**Cause**: you didn't send `x-zitadel-orgid`. The user lookup is org-scoped even though the path includes the user ID.

**Fix**: add the `x-zitadel-orgid` header on user mutations. Update your `IdentityProvider.deactivateUser(userId, tenantId)` signature to require the tenant — don't let callers forget it.

### `User with state initial can only be deleted not deactivated (COMMAND-ke0fw)`

**Cause**: you created a user without `initialPassword`. Zitadel parks them in state `initial` and won't let you `_deactivate`.

**Fix in production**: complete the user's invitation flow first (they receive a link via SMTP, set password, transition to `active`).

**Fix in tests/seeds**: pass `initialPassword: "..."` when calling `AddHumanUser`. The user is created in `active` state and `_deactivate` works.

### `405 Method Not Allowed` on `/management/v1/users/{userId}/grants/_search`

**Cause**: wrong endpoint. There's a similarly named one that doesn't exist.

**Fix**: use the global path with a userId filter:

```http
POST /management/v1/users/grants/_search
{ "queries": [{ "userIdQuery": { "userId": "${zitadelUserId}" } }] }
```

See `api-cheatsheet.md §"User grants"`.

### `invalid AddOIDCAppRequest.ClockSkew: value must be inside range [0s, 5s]`

**Cause**: You set `clockSkew` higher than 5 seconds when creating an OIDC app. This is a Zitadel limit, not the OIDC standard.

**Fix**: `clockSkew: "5s"` (or less). Note: this is the **Zitadel-side** clock skew tolerance, not your **client-side** one. Your `jose.jwtVerify` can use `clockTolerance: '30s'` independently.

### `invalid AddHumanUserRequest.UserName: value length must be between 1 and 200 runes, inclusive`

**Cause**: missing or empty `userName` in the user creation body.

**Fix**: pass the email (or another unique string ≥1 char) as `userName`:

```json
{
  "userName": "user@example.com",
  "profile": { "firstName": "...", "lastName": "..." },
  "email": { "email": "user@example.com", "isEmailVerified": true }
}
```

Old Zitadel docs sometimes show `givenName`/`familyName` — those are rejected. Use `firstName`/`lastName`.

### `invalid SetUpOrgRequest.User: value is required`

**Cause**: you POSTed to `/admin/v1/orgs/_setup` without a `human` field. That endpoint creates an org **and** an admin user atomically.

**Fix**: use the v2 Connect endpoint that creates an org only (no admin user):

```http
POST /zitadel.org.v2.OrganizationService/AddOrganization
Content-Type: application/json
Authorization: Bearer ${PAT}

{ "name": "JRC" }
```

The IAM_OWNER service account from FirstInstance setup can manage all orgs without per-org admins.

## JWT validation errors

### `JWTClaimValidationFailed: unexpected "aud" claim value`

**Cause**: audience mismatch. Most likely you set `audience = clientId` but Zitadel uses **projectId** as audience.

**Fix**:

```typescript
const { payload } = await jwtVerify(token, jwks, {
  issuer,
  audience: projectId,  // NOT clientId
  clockTolerance: '30s',
});
```

### `JWSSignatureVerificationFailed`

**Causes** (in order of likelihood):

1. Wrong `issuer` URL — must match `iss` in the token literally (including scheme and port).
2. Stale JWKS cache after Zitadel masterkey rotation. Restart your service.
3. Token from a different Zitadel instance (e.g., dev token validated against staging issuer).

**Fix**: log the token's `iss` claim and confirm it matches what your validator expects. Use `jwt.io` or `jose.decodeJwt(token)` (no verification, just decode) to inspect.

### Roles array always empty

**Cause**: one of three flags is missing.

**Fix checklist**:

1. Project has `projectRoleAssertion: true`.
2. OIDC app has `accessTokenRoleAssertion: true` (for access tokens).
3. OIDC app has `idTokenRoleAssertion: true` (for ID tokens).

Update via Console (Project → Settings; App → Token Settings) or API. Roles in existing tokens won't change — users need to log in again to get new tokens with the claims.

### `INVALID_TOKEN: no sub`

**Cause**: token came from `client_credentials` (machine-to-machine) flow, which has no end user. `sub` may be the service account's user ID or absent depending on configuration.

**Fix**: if your endpoint should accept service tokens, relax the `sub` requirement and check role/scope claims instead. If not, this is correct behavior — return 401.

## SMTP / invitation errors

### Invitation emails not arriving

**Causes**:

1. SMTP not configured. Check Zitadel Console → System → SMTP Settings.
2. In dev, no Mailpit container. Add it to compose (see `docker-compose-bootstrap.md §5`).
3. In prod, missing SPF/DKIM. Email lands in spam. Configure DNS for the sender domain.
4. Wrong "from" address. Zitadel rejects sends from non-allowlisted addresses on some SMTP providers (SES, Postmark) until verified.

**Diagnostic**: check Zitadel logs for `mail.send` errors:

```bash
docker logs <zitadel-container> 2>&1 | grep -iE "smtp|mail.send"
```

### "Invitation link expired" too quickly

**Cause**: link TTL on Zitadel side is short (default 1 hour for invites, 30 min for password reset).

**Fix**: configure `DefaultInstance.PasswordReset.TTL` and similar via env or Console. Don't extend beyond 24 hours — older links become a security risk.

## Reverse proxy / TLS termination

### Zitadel won't start (or won't accept traffic) when fronted by a TLS-terminating reverse proxy

**Symptom**: You set `ZITADEL_EXTERNALSECURE=true` and `ZITADEL_TLS_ENABLED=false` so that Caddy/NGINX/Traefik can terminate TLS in front of Zitadel. The container either restart-loops with `unable to start TLS server: ...` / port-bind errors, or it starts but every authenticate request returns 400/500 because the issuer URL in tokens doesn't match what the proxy serves.

**Cause**: those two env vars are necessary but not sufficient. Zitadel also needs the start-flag `--tlsMode external` to tell the binary "TLS is being handled outside, don't try to negotiate it yourself". Without it the binary still attempts a TLS bind on its internal HTTP port, which conflicts with the proxy. The trio is required:

```yaml
services:
  zitadel:
    environment:
      ZITADEL_EXTERNALDOMAIN: my-host.example.com
      ZITADEL_EXTERNALPORT: 443
      ZITADEL_EXTERNALSECURE: "true"
      ZITADEL_TLS_ENABLED: "false"
    command: >-
      start-from-init
      --masterkey ${ZITADEL_MASTERKEY}
      --tlsMode external          # <-- the third leg of the triad
```

`ZITADEL_EXTERNALPORT` should be the **HTTPS** port the proxy listens on (the port end users hit), not the internal Zitadel port. Token issuer URLs are constructed from `EXTERNALDOMAIN:EXTERNALPORT` with the scheme dictated by `EXTERNALSECURE`. Get any of the three wrong and downstream JWT validation explodes (issuer mismatch, audience mismatch, or unreachable JWKS).

See `docker-compose-bootstrap.md §"TLS terminated by reverse proxy"` for a full Caddy + Zitadel example.

## Post-upgrade errors (v2.66 → v4)

These show up specifically after bumping the Zitadel image from v2.66.x to v4.x. The full upgrade procedure (snapshot, schema migration, container split) lives in `references/migration-v2-to-v4.md` — this section is the lookup table for the four most common failure modes during the upgrade window.

### `404 Not Found` on `/ui/v2/login` immediately after the v4 boot

**Symptom**: Stack came up, OIDC discovery works (`/.well-known/openid-configuration` returns 200), JWKS loads, but the SPA's `signinRedirect` lands on `https://${EXTERNALDOMAIN}/ui/v2/login/login?authRequest=...` and gets `404`.

**Cause**: In v4 the Login UI v2 is a **separate Next.js container** (`ghcr.io/zitadel/zitadel-login`) — the binary stopped serving `/ui/v2/login` itself. If your reverse proxy still routes everything to the `zitadel` container (which was correct in v2.66), `/ui/v2/login` 404s because the API container doesn't know that path. This is Quirk 25 in disguise.

**Fix (Path A — recommended for v4 forward)**: add the `zitadel-login` container to compose and update the reverse proxy to route `/ui/v2/login` (Prefix) to it. See `docker-compose-bootstrap.md §8` for the full snippet.

**Fix (Path B — least change)**: turn off the instance flag so `signinRedirect` falls back to Login UI v1 (still bundled in the API container at `/ui/login/`):

```bash
PAT=$(cat zitadel/local/admin.pat)
curl -sS -X PUT https://${EXTERNALDOMAIN}/v2/features/instance \
  -H "Authorization: Bearer $PAT" -H 'Content-Type: application/json' \
  -d '{"loginV2":{"required":false}}'
```

Pick one and stick with it — toggling `loginV2.required` while only some clients have v1 set on their app payload causes intermittent 404s.

### 401 storm right after the v4 boot — JWKS keys regenerated

**Symptom**: Backend returns `401` on every `/api` request immediately after `docker compose up -d` on the v4 image. SPA falls into a silent-renew loop. The JWT from the new login decodes cleanly (signature, iss, aud, exp all look correct).

**Cause**: The v4 image's `setup` phase **may rotate instance signing keys** during the migration. The backend's in-process `createRemoteJWKSet` cache holds the v2.66 public keys; tokens minted post-upgrade are signed with new keys whose `kid` doesn't match anything in the cache. jose surfaces this as `JWSSignatureVerificationFailed` (sometimes wrapped as a generic 401) — same shape as Quirk 12 but a different trigger.

**Fix**: restart the backend after confirming Zitadel logs `setup completed`. The fresh `createRemoteJWKSet` fetches the v4 keys on first verification.

If the storm persists after a backend restart, you've hit one of the other 401-storm causes (Quirk 12: TLS handshake / `NODE_EXTRA_CA_CERTS`; Quirk 13: `AUTH_AUDIENCE` cached from v2.66 doesn't match the v4-regenerated `projectId`). Walk through `troubleshooting.md §"401 storm with apparently-valid JWT"` causes 1, 2, 3 in that order.

### `setup` phase hangs > 5 minutes during the v4 first boot

**Symptom**: `docker logs zitadel` after `docker compose up -d` shows the new container booting, applying migration steps, then long silence. No `setup completed`, no obvious error. Container stays in `health: starting`.

**Causes** (in order of likelihood):

1. **Postgres connection limit reached.** v4's setup runs migrations as multiple short-lived connections; if `max_connections` on Postgres is at default (100) and you have other consumers (backend, dev tools), Zitadel can starve. Check `pg_stat_activity` for queue depth.
2. **Disk full** on the Postgres volume. Migration writes new tables; out of space mid-write leaves the DB inconsistent. `df -h` on the host.
3. **Slow migration on a large events table**. If you have years of v2.66 events (millions of rows), some migration steps (notably re-indexing for v4 query patterns) take 5–30 min. Patience or scale up CPU temporarily.

**Diagnostic**:

```bash
# Tail the migration progress
docker logs zitadel 2>&1 | grep -E "migration|setup" | tail -20

# Compare with what's currently happening on Postgres
docker exec <postgres-ctr> psql -U zitadel -c \
  "SELECT pid, state, query_start, left(query, 100) FROM pg_stat_activity WHERE state = 'active';"
```

**Fix**: address the root cause (raise `max_connections`, free disk, wait). **Do not** restart the container mid-migration — that's how you get into the `Errors.Instance.Domain.AlreadyExists` half-migrated state, which requires a snapshot restore (see `migration-v2-to-v4.md §5`).

### Branding (logo / colors) gone after the upgrade

**Symptom**: Login UI looked branded (red JRC, custom logo) on v2.66; same Login UI on v4 shows the default Zitadel blue/gray. `LabelPolicy` GET still returns the customized values — they're persisted, just not applied.

**Cause**: Two possible drifts:

1. **Asset path migration**. Quirk 21 was a v3→v4 rename — `/assets/v1/orgs/me/policy/label/...` → `/assets/v1/org/policy/label/...`. If you re-uploaded assets between upgrades and used the old path, the upload returned 405 silently (or you didn't upload after the upgrade and the old binary blob is now in a path the v4 binary doesn't read).
2. **`privateLabelingSetting` reset on the project**. Some migration steps reset project-level flags to defaults; the project's `PRIVATE_LABELING_SETTING_ENFORCE_PROJECT_RESOURCE_OWNER_POLICY` may have flipped back to `_UNSPECIFIED`, falling back to the instance label policy (Quirk 19).

**Fix**: re-run your branding bootstrap. The label policy itself usually survives — what needs replaying is the asset upload (Quirk 21 path) and the project flag set (Quirk 19). Both are idempotent. See `branding.md §"Quirk 19"` and `§"Quirk 21"`.

### `zitadel-login` container loops on "Awaiting file and reading token" (Login UI v2 never becomes healthy)

**Symptom**: After deploying the `ghcr.io/zitadel/zitadel-login` container alongside the main `zitadel` server (per Quirk 25's Path A), `docker logs zitadel-login` shows only:

```text
ZITADEL_SERVICE_USER_TOKEN_FILE=/login-client/login-client.pat is set. Awaiting file and reading token.
```

The container never reports healthy. `/ui/v2/login` returns `404` (Caddy / nginx-proxy proxies to a backend that has no HTTP server up yet). The shared `login-client-pat` volume is empty.

**Cause**: Quirk 28. Setting only `ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH` on the `zitadel` server isn't enough — the FirstInstance flow needs an explicit machine user definition (`ZITADEL_FIRSTINSTANCE_ORG_LOGINCLIENT_MACHINE_USERNAME` + `_NAME` + `..._PAT_EXPIRATIONDATE`) for v4 to actually create the user and write the PAT. **But adding those envs causes a different, worse failure** — `03_default_instance` migration hits a unique constraint conflict on the instance domain (zitadel/zitadel#8910 and #9293) and the main `zitadel` server enters a restart loop.

In v4.15.0 there's no env-only configuration that wins both ways. Fix is workaround-shaped:

**Fix A (recommended for fast unblock — Path B of Quirk 25)**: stay on Login UI v1.

1. In your bootstrap, after the admin PAT is read: `PUT /v2/features/instance` with body `{"loginV2": {"required": false}}`. Catch `COMMAND-1m88i` as no-op for re-runs.
2. In OIDC app config (`CreateApplication`/`UpdateApplication`), pin `loginVersion: { loginV1: {} }` defensively at the app level.
3. Apply branding via label policy v1 (still works in v4 — Quirks 19-22). The `zitadel-login` container can stay deployed and idle; it'll be ready when upstream stabilizes.

**Fix B (independent of upstream — provision via bootstrap)**: post-boot, your bootstrap creates the machine user manually.

1. Switch `zitadel-login` from named volume → bind mount, e.g. `./zitadel/local:/login-client:ro`.
2. Drop `ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH` from the `zitadel` server (no auto-write).
3. In the bootstrap script: create the machine user `login-client` via `UserService.v2/AddMachineUser` (or the equivalent in your patch — verify against proto), assign role `IAM_LOGIN_CLIENT` system-wide, generate a PAT, write it to the bind-mounted path (chmod 600).
4. The `zitadel-login` container polls the file path — when it appears, the container becomes healthy.

Track upstream PR #10518 and related issues — when the constraint-duplicate fix lands in a v4.x patch you can use, retire the workaround.

### `Errors.Project.App.AlreadyExisting` (or `Errors.User.AlreadyExisting`) — your idempotency matcher missed it

**Symptom**: Re-running bootstrap fails with `400 failed_precondition` and a body like:

```json
{ "code": "failed_precondition", "message": "Errors.Project.App.AlreadyExisting (PROJECT-lxowmp)" }
```

The first run created the resource fine; the second run was supposed to be idempotent but threw the error to the caller.

**Cause**: your `isAlreadyExists()` helper checks for the substring `'AlreadyExists'` (no `ing`). Zitadel v4 uses both forms in error IDs — `Errors.User.AlreadyExists` **and** `Errors.Project.App.AlreadyExisting` (with the `ing` suffix). The substring `'AlreadyExists'` is **not** a prefix of `'AlreadyExisting'`, so the matcher misses it.

**Fix**: extend the matcher to cover both forms (see `api-v1-to-v2-mapping.md §5`):

```typescript
const ALREADY_EXISTS_MARKERS = [
  '"code":6', 'ALREADY_EXISTS', 'already_exists',
  'already exists', 'AlreadyExists',
  'AlreadyExisting',   // ← v4 also uses this
];
```

This is also the reason your bootstrap appeared to "work the first time" but blew up on the second — the new resource (project app) hit the gerund form on re-create.

### Setup migration `03_default_instance` fails: `duplicate key value violates unique constraint "unique_constraints_pkey"` / `Errors.Instance.Domain.AlreadyExists`

**Symptom**: Fresh `docker compose up -d` (volumes just created), Zitadel container enters restart loop. Logs:

```text
starting migration name=03_default_instance
add unique constraint failed: duplicate key value violates unique constraint "unique_constraints_pkey"
detail: Key (instance_id, unique_type, unique_field)=(, instance_domain, <your-domain>) already exists.
migration failed err.kind=AlreadyExists err.id=V3-DKcYh
setup failed, skipping cleanup
```

`docker compose down -v` + retry doesn't help — every restart of the same DB run replays the same conflict (the partial state from the first attempt is left behind because of `setup failed, skipping cleanup`).

**Cause**: known race / interaction in Zitadel v4 setup ([zitadel/zitadel#8910](https://github.com/zitadel/zitadel/issues/8910), [#9293](https://github.com/zitadel/zitadel/issues/9293), partial fix in PR #10518 — may not be in your patch). The `03_default_instance` migration tries to reserve the instance domain twice in one transaction when both the FirstInstance Human admin and a LoginClient machine user are configured. The classic trigger is adding `ZITADEL_FIRSTINSTANCE_ORG_LOGINCLIENT_MACHINE_USERNAME` (etc.) — see Quirk 28.

**Fix**:

1. Stop the loop: `docker compose down -v` AND `docker volume rm <project>_<volume-name>` (the `down -v` may report the volume removed but the partial state can survive in the DB volume if the container restarted between operations). Confirm with `docker volume ls`.
2. Remove the `ZITADEL_FIRSTINSTANCE_ORG_LOGINCLIENT_MACHINE_*` and `..._PAT_EXPIRATIONDATE` envs from the `zitadel` service. Keep at most `ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH` (which is harmless on its own — see Quirk 28 for what to do about Login UI v2).
3. `docker compose up -d` — setup migrations should now complete on first try.

If the failure persists without those envs, your underlying issue is somewhere else — check `zitadel/zitadel#8910` for the latest comments and pin to a v4.x patch with the fix, or downgrade to a known-good patch.

### Bootstrap fails with `INVALID_ARGUMENT: missing organization_id` after partial v2 refactor

**Symptom**: You upgraded the IdP **and** simultaneously refactored some bootstrap calls from v1 to v2 (Connect protocol). The v1 calls work; the v2 calls fail with `INVALID_ARGUMENT: missing organization_id` even though the bootstrap script sets `x-zitadel-orgid` header globally on its HTTP client.

**Cause**: Quirk 27 — v2 carries org context in the **body** (`organizationId`), not the header. The header is harmless but ignored on v2 calls. You dropped the global header during refactor (or didn't), but didn't add the body field — that's the missing piece.

**Fix**: for each v2 call, ensure the body includes the `organizationId` (or per-resource equivalent — sometimes nested as `org.id` or `resourceOwner`). Check `api-v1-to-v2-mapping.md §3` for the convention. Don't refactor everything at once — keep v1 and v2 calls in the same script and migrate gradually.

### OIDC client_id mismatch — `Errors.App.NotFound` immediately after a clean cutover

**Symptom**: Bootstrap succeeded (log shows `[app] created appId=<uuid> clientId=<numeric>`), the SPA was rebuilt with the right secret, but `/oauth/v2/authorize?client_id=<your-secret>` returns `400 invalid_request "Errors.App.NotFound"`. Login flow dies before the user ever sees the UI.

**Cause**: Quirk 29 — you wired `VITE_OIDC_CLIENT_ID` (or equivalent SPA env) to the deterministic `applicationId` UUID you passed in `CreateApplicationRequest`, but Zitadel auto-generates a separate **numeric `clientId`** (e.g. `371898282416275459`) for OAuth/OIDC. The UUID is the resource handle for v2 admin APIs; only the numeric `clientId` is accepted as `client_id` on the OIDC endpoints.

**Fix**:

1. Confirm the numeric `clientId` from the bootstrap output (`clientId=<numeric>` next to `appId=<uuid>`) or via:
   ```bash
   curl -s -X POST https://${EXTERNALDOMAIN}/zitadel.application.v2.ApplicationService/GetApplication \
     -H "Authorization: Bearer $PAT" -H 'Content-Type: application/json' \
     -d "{\"applicationId\": \"<your-uuid>\"}" | jq '.application.oidcConfiguration.clientId'
   ```
2. Set the SPA secret to the numeric value: `gh secret set VITE_OIDC_CLIENT_ID --env production --body "<numeric>"`.
3. **Trigger a frontend rebuild** — VITE_* are baked at image build time, not runtime.
4. (Optional, recommended for CD) add a workflow step that reads the numeric `clientId` from the bootstrap output and overwrites the secret automatically — avoids the manual step every re-bootstrap.

Backend `AUTH_AUDIENCE` for JWT validation can stay as the deterministic `projectId` — the JWT `aud` claim contains both, and Zitadel emits projectId for backend validation.

### Wrong-environment IDs in prod IdP — bootstrap defaulted to `dev`

**Symptom**: bootstrap succeeded; entities have *dev* deterministic IDs from your YAML (e.g., `applications[].ids.dev`); the frontend secret has *prod* IDs; OIDC authorize returns `Errors.App.NotFound`. Same surface symptom as Quirk 29 but different root cause.

**Cause**: Quirk 30 — your bootstrap script reads an env (e.g., `ZITADEL_BOOTSTRAP_ENV`) to pick which `ids.<env>` block to use, with a silent default to `dev`. The CD pipeline never set the env. Bootstrap log line `[bootstrap] ambiente=dev` confirms it.

**Fix**:

1. Set the env explicitly on the bootstrap container in `docker-compose.prod.yml`:
   ```yaml
   idp-bootstrap:
     environment:
       ZITADEL_BOOTSTRAP_ENV: prod
   ```
2. Wipe the IdP DB volume — wrong-ID entities can't be renamed in place; search-by-name finds them and reuses, perpetuating the mismatch. After wipe + redeploy, FirstInstance + bootstrap recreate everything with the correct prod IDs.
3. (Recommended) update the bootstrap script to **throw** on missing env rather than defaulting — fail loud so this never recurs. Keep dev compat by having `dev.sh` (or your dev launcher) set the env explicitly too.

### "A senha é inválida" / `password.check.failed` despite the env value matching

**Symptom**: `it@jrcbrasil.com` (FirstInstance human admin) can't login. The container env literally has `ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORD=<secret-value>` — verified via `docker inspect <ctr> --format '{{range .Config.Env}}{{println .}}{{end}}'` — and that's exactly what the operator is typing.

**Most common cause**: Zitadel default `passwordChangeRequired=true` forced a password change on first login; operator changed it; current password ≠ secret value. After a volume wipe, FirstInstance recreates the user with the secret value but the operator forgets and tries the *changed* password — or types the secret value correctly but is misled by stale earlier attempts.

**Diagnose** with the eventstore directly (the password event log is the source of truth):

```bash
docker exec <postgres-idp-container> psql -U zitadel -d zitadel -tAc "
  SELECT created_at, event_type
  FROM eventstore.events2
  WHERE aggregate_type = 'user'
    AND aggregate_id = (
      SELECT aggregate_id
      FROM eventstore.events2
      WHERE event_type = 'user.human.added'
        AND payload->>'userName' = 'it@jrcbrasil.com'
      LIMIT 1
    )
  ORDER BY position ASC;"
```

You'll see `user.human.password.check.failed` / `succeeded` events with timestamps, plus any `user.human.password.changed` events that prove a drift between the secret and the actual password.

**Fix**: set `ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORDCHANGEREQUIRED=false` on the `zitadel` service so the secret is the stable source of truth. After a volume wipe + redeploy, the operator logs in with the secret value directly, no forced change.

### `idp-bootstrap` container fails with `ERR_MODULE_NOT_FOUND` for a path under `src/`

**Symptom**: CD bootstrap step exits 1 with:
```
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '/app/packages/idp/src/infrastructure/adapters/zitadel/client/errors' imported from /app/packages/idp/scripts/bootstrap-zitadel.ts
```

**Cause**: the bootstrap script imports from `src/...` at runtime (via `tsx`), but the runtime stage of `packages/idp/Dockerfile` only copies `dist/`, `scripts/`, `prisma/` — `src/` is missing from the image. Compounding bug: the same Dockerfile may also be `COPY`ing a legacy YAML path (e.g., `specs/002-idp-oidc/contracts/zitadel-config.yaml`) instead of the canonical one (e.g., `packages/idp/zitadel-config.yaml`).

**Fix**: add `COPY packages/idp/src packages/idp/src` and `COPY packages/idp/tsconfig.json packages/idp/` in the runtime stage, and audit the YAML COPY line. Verify with: `docker run --rm --entrypoint sh <image> -c 'ls /app/packages/idp/src && ls /config/'`.

## CI / smoke-e2e errors (GHA runner)

The smoke-e2e job that runs Zitadel + bootstrap inside GitHub Actions has its own cluster of pitfalls — none of which manifest in dev (host machine perms / generous timeouts / your own password). When `continue-on-error: true` is set on the job, these can rot for months without anyone noticing because the run-level conclusion stays "success".

### `migration failed name=03_default_instance err.parent="open /current-dir/admin.pat: permission denied"` followed by `unique_constraints_pkey` cascade

**Symptom**: `docker compose up -d --wait` against `infra/docker/docker-compose.zitadel.yml` exits 1 with `dependency failed to start: container docker-zitadel-1 is unhealthy`. The Zitadel logs show TWO failures back-to-back on `restart: always`:

1. **First boot**: `EACCES open /current-dir/admin.pat: permission denied` during `03_default_instance` migration → `setup failed, skipping cleanup`.
2. **Subsequent boots** (the symptom that's actually visible at the bottom of the logs): `duplicate key value violates unique constraint "unique_constraints_pkey" detail: Key (instance_id, unique_type, unique_field)=(, instance_domain, 127.0.0.1.sslip.io) already exists.` — looks like Quirk 28 (#8910 / #9293) but isn't.

**Cause**: Quirk 38 — `ZITADEL_FIRSTINSTANCE_PATPATH=/current-dir/admin.pat` writes to a path inside a host bind mount (`./zitadel/local:/current-dir:rw`). The Zitadel container process runs as **uid 1000** (image default); on a GitHub Actions `ubuntu-latest` runner the host directory is created post-checkout owned by **runner:docker (uid 1001)** with mode `0755`, so uid 1000 can't write — EACCES. The first boot's *partial* setup nevertheless persisted `instance_domain=127.0.0.1.sslip.io` into the eventstore (Zitadel logs `setup failed, skipping cleanup` — it skips cleanup, not the partial state). Every subsequent retry replays the migration with that record already there, so they fail with `unique_constraints_pkey` instead of EACCES — the original cause is buried 30+ lines up in the logs.

**Diagnose**: when you see `unique_constraints_pkey` on `03_default_instance`, **always scroll up to the FIRST migration attempt**. If that one failed with `permission denied` on `admin.pat` (or any other file under `/current-dir/`), you're hitting Quirk 38, not Quirk 28. The cure is different.

**Fix** (CI-only — dev is not affected because the host dir gets your user's perms when `dev.sh` or whatever scaffolds it):

```yaml
# .github/workflows/<your-ci>.yml — step inserted BEFORE `docker compose up`
- name: Pre-create writable bind mount for Zitadel admin.pat
  run: |
    mkdir -p infra/docker/zitadel/local
    chmod 0777 infra/docker/zitadel/local
```

`chmod 0777` is idiomatic for ephemeral CI bind mounts and avoids hardcoding a uid that could shift if the image changes. Don't try to "fix" by `chown 1000:1000` — same effect, more brittle. Don't try to swap to a named volume in CI without also doing it in dev — the `bootstrap.json` artifact (consumed by your auth-sanity check, etc.) lives in that bind mount on the host side, and breaking the dev path to "fix" CI is a regression.

After applying the fix and re-running, you should see Zitadel logs end with `setup completed` + the `ZITADEL` ASCII banner + `server is listening address=[::]:8080` instead of the migration error.

### `Bootstrap fails with COMMAND-VoaRj "Password must contain upper case"` on `AddHumanUser`

**Symptom**: Bootstrap script gets past `[org] created`, `[project] created`, `[role] created`, `[app] created` and then dies on the seed user step:

```text
[bootstrap] FALHOU: Zitadel 400 /zitadel.user.v2.UserService/AddHumanUser:
{"code":"invalid_argument","message":"Password must contain upper case (COMMA-VoaRj)",...}
```

**Cause**: Quirk 39 — Zitadel's default password policy on a fresh instance requires **all four character classes** (uppercase, lowercase, digit, symbol). A common CI shortcut to generate ephemeral passwords is `openssl rand -hex 16` — which only emits lowercase `[0-9a-f]` and trips this rule deterministically. The error code `COMMA-VoaRj` ("password must contain upper case") is the FIRST class missing in `[0-9a-f]`; if you "fix" it by adding only an uppercase prefix you may then trip the next class missing (`COMMA-...` for digit or symbol).

**Fix**: use a structured generator that guarantees all four classes:

```bash
# Bash one-liner — 32-char password that guarantees upper+lower+digit+symbol.
RAND_TAIL="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 28)"
export ZITADEL_SEED_USER_PASSWORD="Aa1!${RAND_TAIL}"
```

The `Aa1!` prefix covers all four classes deterministically; the 28-char alphanum tail brings entropy. Same pattern works for any CI-generated password against a Zitadel-shaped policy. (Don't use `openssl rand -base64` — base64 includes `=` padding and `/+` which Zitadel's default policy may or may not accept depending on version; alphanum + structured prefix is more portable.)

If you've **changed the default policy** on the instance and want CI to mirror it, mirror in the script too — but don't just generate hex and hope for the best.

### `zitadel-login` container never goes Healthy in CI; `up --wait --wait-timeout 120` times out

**Symptom**: stack boots fine, `zitadel-db` Healthy, `zitadel-init` Exited (success), `zitadel` Healthy, then `Container docker-zitadel-login-1 Started` followed by minutes of silence and finally `dependency failed to start: container docker-zitadel-login-1 is unhealthy`. Other services were healthy long before the timeout — only `zitadel-login` (the Login UI v2 Next.js container, image `ghcr.io/zitadel/zitadel-login:vX.Y.Z`) fails to come up in time.

**Cause**: Quirk 40 — `zitadel-login` is a Next.js app whose healthcheck (`wget --spider http://localhost:3000/`) only passes once Next.js has done first-render bootstrap. On a small CI runner (`ubuntu-latest` shared, 2 vCPU) that takes ~90s+ from container start; with the default compose `start_period: 30s` + `interval: 10s × retries: 12` the healthcheck would only abandon at ~210s, but `--wait-timeout 120` cuts it short first. **Bootstrap and integration tests don't actually need Login UI** — `bootstrap-zitadel.ts` reads `login-client.pat` from the named volume populated by the `zitadel` service's FirstInstance setup, and any direct REST hits the `zitadel:8080` API, not the UI. So the wait is pure cost.

**Fix** — scope `--wait` to the services the test actually exercises:

```yaml
- name: Boot Zitadel stack
  run: |
    docker compose -f infra/docker/docker-compose.zitadel.yml up -d --wait --wait-timeout 120 \
      zitadel-db zitadel-init zitadel
```

Compose only waits for the listed services to be healthy; `zitadel-login` and any other slow sibling (`mailpit` — irrelevant unless the test itself opens email) are simply not started. In dev, `./dev.sh` (or whatever scaffolds your local stack) keeps the default `up` so the Login UI is available for browser smoke. If your CI does need Login UI healthy (e.g., a Playwright login spec), bump `--wait-timeout` to ~240s instead — same `wait`, more headroom.

Also add a defensive `docker compose logs zitadel-login` in the on-failure step — without it, when the wait times out you see only `is unhealthy` from the orchestrator, not the Next.js boot output.

## When you don't see your error here

1. Check Zitadel logs first: `docker logs <container> 2>&1 | tail -100`. Most setup errors print at INFO or ERROR level.
2. Check the response body. Zitadel error responses include `code` (gRPC status) and `id` (a stable identifier like `COMMAND-ke0fw`) — search the Zitadel repo for that ID to find the source code raising it.
3. Match the URL pattern against `api-cheatsheet.md` — if you can't find a section that covers your call, you may be hitting a v3-only or pre-release endpoint.
4. Last resort: file an issue at <https://github.com/zitadel/zitadel/issues> with the request URL, response body, and Zitadel version. The maintainers respond fast.
