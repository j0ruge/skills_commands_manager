# TLS / HTTPS recipe — mkcert + Caddy + the consumer plumbing

When the dev script needs to serve to a non-localhost client (LAN, sslip.io, custom hostname), HTTP doesn't cut it. Browsers expose `crypto.subtle` only in **secure contexts**, and PKCE depends on it. The localhost/127.0.0.1 exception is the only HTTP exception.

This file is the canonical recipe to make HTTPS work in dev without buying a real cert. It covers **all four** pieces that have to align:

1. The cert itself (mkcert).
2. The TLS-terminating reverse proxy (Caddy) and its config.
3. The dev servers behind the proxy (Vite, Express, Zitadel).
4. The Node backend that has to validate JWTs whose JWKS is served over the local cert (`NODE_EXTRA_CA_CERTS`).

Skip any one and the chain breaks.

## When to apply this recipe

Apply when **all** of these hold:

- The user wants devices other than the dev box to access the SPA.
- The SPA does OIDC PKCE (or any flow that calls `crypto.subtle`).
- The user accepts asking LAN clients to install a local root CA once.

Skip if:

- The script is localhost-only.
- The SPA has no OIDC and no other PKCE-like need.
- The user explicitly prefers a tunnel (ngrok / cloudflared) — different recipe, not covered here.

## Step 1 — mkcert

mkcert manages a local root CA and signs leaf certs for arbitrary names. It's the easiest dev-CA setup that exists. The dev script should:

- **Check** `command -v mkcert` and abort with an actionable message if missing (`brew install mkcert` / `winget install FiloSottile.mkcert` / `apt install mkcert`).
- **Idempotently install** the root CA on the dev host: `mkcert -CAROOT` returns the path; if `rootCA.pem` is missing, run `mkcert -install` (will prompt for sudo on Linux/macOS to write to the system trust store).
- **Generate the leaf cert** for all names the proxy will serve:

  ```bash
  mkcert -cert-file infra/certs/dev.pem -key-file infra/certs/dev.key \
    "${EXTERNAL_DOMAIN}" "${HOST}" localhost 127.0.0.1
  ```

  Where `EXTERNAL_DOMAIN` is `<LAN_IP>.sslip.io` (covers any LAN client that hits the dev box's IP) and `HOST` is the bare LAN IP. Add `localhost` and `127.0.0.1` so the cert keeps working when the same dev hits it locally without proxy chain hopping.

- **Track which names the cert was minted for** in a sidecar file (`infra/certs/.names`). On re-run, compare to current names; regenerate if the network changed.

- **Copy `rootCA.pem` somewhere the SPA serves** (e.g., `public/dev-rootCA.pem`) so LAN clients can `curl -k https://<host>:<port>/dev-rootCA.pem` and import it. The first hit needs `-k` because trust isn't established yet — that's a one-time bootstrap on each client.

## Step 2 — Caddy reverse proxy

Caddy is a single static binary, has the cleanest config syntax for dev TLS, and handles HTTP/2 + HTTP/3 by default. The config the dev script generates:

```caddy
{
  auto_https off       # we provide certs explicitly; don't try Let's Encrypt
  admin off            # no admin endpoint listening (avoids :2019 conflict)
}

<EXTERNAL_DOMAIN>:<WEB_PORT> {
  tls /certs/dev.pem /certs/dev.key
  reverse_proxy localhost:<WEB_INTERNAL_PORT>
}

<EXTERNAL_DOMAIN>:<API_PORT> {
  tls /certs/dev.pem /certs/dev.key
  reverse_proxy localhost:<API_INTERNAL_PORT>
}

<EXTERNAL_DOMAIN>:<IDP_PORT> {
  tls /certs/dev.pem /certs/dev.key
  reverse_proxy localhost:<IDP_INTERNAL_PORT>
}
```

Default port mapping for the JRC pattern:

| Service | Internal (HTTP) | External (HTTPS via Caddy) |
|---|---|---|
| Web (Vite) | 5173 | 5443 |
| Backend (Express) | 3000 | 3443 |
| IdP (Zitadel) | 8080 | 8443 |

The 5443/3443/8443 choice is arbitrary but mnemonic (HTTPS-ish). Pick whatever is free — the dev script's `kill_port` should clear them before Caddy starts.

### Running Caddy in docker with `network_mode: host`

`network_mode: host` lets Caddy reach `localhost:5173` (host's loopback) without docker-network gymnastics, and lets it bind the public ports directly. Linux-only; on macOS/Windows you need `host.docker.internal` and `extra_hosts: ["host.docker.internal:host-gateway"]`.

```yaml
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    network_mode: host                          # Linux
    volumes:
      - ./infra/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - ./infra/certs:/certs:ro
```

If the dev script targets non-Linux too, generate a different compose snippet:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    ports: ["5443:5443", "3443:3443", "8443:8443"]
    extra_hosts: ["host.docker.internal:host-gateway"]
    volumes:
      - ./infra/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - ./infra/certs:/certs:ro
```

…and rewrite the Caddyfile `reverse_proxy` lines to use `host.docker.internal:5173` instead of `localhost:5173`.

## Step 3a — Vite ≥ 5 needs `allowedHosts: true`

Vite 5 added a host-allowlist defense (CVE-2025-XXXXX-class). Out of the box it returns

```text
Blocked request. This host ("<LAN_IP>.sslip.io") is not allowed.
To allow this host, add "<LAN_IP>.sslip.io" to `server.allowedHosts` in vite.config.js.
```

…to every request that doesn't match localhost. You **don't want to edit `vite.config.ts`** (it's source-controlled, used by CI and prod builds). Instead, the dev script writes a wrapper config and runs Vite with `--config <wrapper>`:

```typescript
// .vite.config.lan.ts — generated by dev script, gitignored
import base from "./vite.config";
import { mergeConfig } from "vite";

export default mergeConfig(base, {
  server: {
    allowedHosts: true,                                 // accept any host
    hmr: {
      clientPort: 5443,                                 // HMR over WSS via Caddy
      protocol: "wss",
      host: process.env.DEV_SH_EXTERNAL ?? "localhost",
    },
  },
});
```

Run with:

```bash
DEV_SH_EXTERNAL="${EXTERNAL_DOMAIN}" \
  npm run dev -- --config .vite.config.lan.ts --host 0.0.0.0 --port 5173 --strictPort
```

`--strictPort` is non-negotiable: if 5173 is busy and Vite falls back to 5174, the OIDC redirect URI mismatches and login breaks. Hard-fail is correct.

## Step 3b — Backend Express stays HTTP

The backend doesn't terminate TLS — Caddy does. Run it on plain HTTP `:3000`. The HTTPS facing the world (`https://<external>:3443`) is provided by Caddy proxying to `localhost:3000`. CORS on the backend should accept the **HTTPS** origin:

```bash
patch_env_kv "$BACKEND_ENV" "CORS_ORIGINS" "${WEB_BASE}"   # https://<external>:5443
```

## Step 3c — Zitadel needs the TLS triad

Three settings move together when Zitadel is behind a TLS-terminating proxy:

```yaml
services:
  zitadel:
    environment:
      ZITADEL_EXTERNALDOMAIN: ${EXTERNAL_DOMAIN}
      ZITADEL_EXTERNALPORT: 8443                # the public HTTPS port the proxy serves
      ZITADEL_EXTERNALSECURE: "true"            # tokens get https:// issuer URLs
      ZITADEL_TLS_ENABLED: "false"              # Zitadel itself stays HTTP
    command: >-
      start-from-init
      --masterkey ${ZITADEL_MASTERKEY}
      --tlsMode external                        # required — without it the binary tries TLS itself
```

`ZITADEL_EXTERNALDOMAIN`, `ZITADEL_EXTERNALPORT`, `ZITADEL_EXTERNALSECURE` are persisted in the Zitadel database on first init. Changing any later requires `docker compose down -v` (volume drop) — the dev script must encode this and require an explicit `--reset` to confirm.

`--tlsMode external` is the trap that bites everyone the first time: the env vars look sufficient, but without the start flag the binary still attempts a TLS bind and refuses traffic.

## Step 4 — Node backend trusting the local CA

The backend validates JWTs by fetching the IdP's JWKS over HTTPS (`https://<external>:8443/oauth/v2/keys`). Node's `fetch` (used by `jose.createRemoteJWKSet`) checks the OS trust store and **does not** know about mkcert's root CA out of the box. Result: TLS handshake fails before any signature check; jose surfaces it as `JWKSNoMatchingKey` or `JWSSignatureVerificationFailed` — **not** a TLS error message. Symptom: 100% of `/api` requests return 401, JWT decoded by hand looks perfect, the SPA falls into a silent-renew loop, rate-limit (429) follows.

The fix is one env var:

```bash
NODE_EXTRA_CA_CERTS="$(mkcert -CAROOT)/rootCA.pem" npm run dev
```

`NODE_EXTRA_CA_CERTS` *appends* to the OS bundle — safe to leave on always, including in production-shaped images. Set it on:

- The dev script's invocation of `npm run dev` for the backend.
- The dev script's invocation of the bootstrap script (it also fetches over HTTPS).
- Any test runner that hits the IdP's HTTPS endpoint.

**Don't** use `NODE_TLS_REJECT_UNAUTHORIZED=0` — it disables cert validation globally for the process, including any other HTTPS calls (database SSL, third-party APIs). `NODE_EXTRA_CA_CERTS` only adds trust for the specific cert; that's what you want.

### Diagnostic

If the backend keeps 401-storming, run on the dev host:

```bash
# Should print a JWKS payload, not a TLS error.
curl --cacert "$(mkcert -CAROOT)/rootCA.pem" "https://<external>:8443/oauth/v2/keys"

# Same call without the CA — should fail with cert verify error if cert is local-only.
curl "https://<external>:8443/oauth/v2/keys"
```

If the first command works and the second errors on cert verification, you've confirmed it: backend is missing `NODE_EXTRA_CA_CERTS`.

## Step 5 — Testing the LAN-HTTPS stack with Playwright

If the project has a Playwright suite, pointing it at the LAN-HTTPS stack the dev script just brought up takes **two** moves — missing either makes the suite fail before any spec body runs.

**Move 1**: accept the env var override and ignore HTTPS errors when the base URL is HTTPS:

```typescript
// playwright.config.ts
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";
const IS_HTTPS = BASE_URL.startsWith("https://");

export default defineConfig({
  use: {
    baseURL: BASE_URL,
    ignoreHTTPSErrors: IS_HTTPS,    // mkcert root isn't in Chromium's trust store
    // …
  },
  // The auto-started webServer doesn't make sense in LAN mode (the dev script
  // already runs Vite). Disable it when BASE_URL is HTTPS.
  webServer: IS_HTTPS ? undefined : {
    command: "npm run dev:e2e",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
  },
});
```

**Move 2**: mirror `ignoreHTTPSErrors` in the global setup. The setup creates its own browser context for the login flow, and that context **does not** inherit `use.ignoreHTTPSErrors`:

```typescript
// e2e/global-setup.ts
async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use.baseURL ?? "http://localhost:5173";
  const browser = await chromium.launch();
  const context = await browser.newContext({
    ignoreHTTPSErrors: baseURL.startsWith("https://"),   // <-- mandatory for LAN HTTPS
  });
  const page = await context.newPage();
  await page.goto(`${baseURL}/login`);
  // …login + storageState save…
}
```

Without move 2, the global setup hits `net::ERR_CERT_AUTHORITY_INVALID` on the first `page.goto` and every spec is skipped before it starts. The error message names a different file than the actual problem, so it eats 10 minutes of debugging the first time.

Run the suite:

```bash
PLAYWRIGHT_BASE_URL=https://${EXTERNAL_DOMAIN}:${WEB_PORT} \
  E2E_LIVE=1 \
  PLAYWRIGHT_TEST_USER_PASSWORD='…' \
  npx playwright test
```

`NODE_TLS_REJECT_UNAUTHORIZED=0` is **not** an alternative for `ignoreHTTPSErrors` here — Playwright's browser contexts don't read it. You'd be disabling Node's TLS check while the browser-level check still rejects.

### Test isolation note: logout invalidates `storageState`

Specs that exercise the logout flow tear down the IdP session for the cookie stored in `storageState`. The storage state file is shared across tests in a describe; any test that runs *after* the logout test inherits a dead session and fails before reaching its assertions. Order logout-related specs **last** in the describe (or use a per-test fresh storage state) — this is a generic Playwright pitfall, not a TLS-specific one, but it surfaces hard the moment the LAN-HTTPS suite has a real logout test.

## LAN client onboarding — what to tell users

LAN clients (other devs' laptops, phones, tablets) need the mkcert root CA installed once. The dev script should print onboarding instructions in the final summary:

```text
HTTPS via mkcert — clients must trust the local root CA:
  rootCA on this machine: <MKCERT_CAROOT>/rootCA.pem
  download:               <WEB_BASE>/dev-rootCA.pem  (use curl -k or accept the cert warning the first time)
  install on client:      'mkcert -install' (after copying rootCA.pem to ~/.local/share/mkcert/),
                          or import rootCA.pem into the client's trust store manually.
```

Phones can scan a QR code containing the URL, install via the OS profile mechanism. Each platform has its own UI for "trust this certificate"; outside scope here.

## Cross-platform note (PowerShell hosts)

mkcert and Caddy both have Windows builds. The recipe is identical on Windows except:

- `mkcert -install` writes to the Windows Certificate Store; works without elevation for the user store.
- Caddy can run as a Windows service or via `caddy.exe run` directly; for dev, `caddy.exe run --config Caddyfile` is fine.
- `network_mode: host` in compose **does not work on Windows** — use the `extra_hosts: ["host.docker.internal:host-gateway"]` variant and proxy to `host.docker.internal:5173` etc.
