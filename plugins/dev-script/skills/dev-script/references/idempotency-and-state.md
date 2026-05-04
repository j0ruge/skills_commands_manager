# Idempotency and state — the discipline of re-runs

A dev launcher is run dozens of times a day. If running it twice doesn't converge to the same state, it's broken. This file lays out the patterns that keep the script honest.

## The two kinds of state

**Stable state** is what the user keeps between runs intentionally — the Zitadel database (users, projects), the Postgres data volume, the bootstrap output (`bootstrap.json`), generated certs.

**Volatile state** is what the script regenerates on each invocation — `.env.local` (frontend), patches to `packages/backend/.env`, the Caddyfile, the compose override file, the wrapper Vite config.

The discipline: **never blur the line**. Volatile state lives in gitignored files; stable state lives in named volumes / version-controlled bootstrap outputs / mkcert paths.

## Re-derive volatile IDs every boot — never hardcode

The IdP's `projectId` and `clientId` change every time its volume resets. If `packages/backend/.env` has

```text
AUTH_AUDIENCE=370503956331233283
```

…hardcoded from a previous bootstrap, the next reset breaks every JWT validation silently (401 storm, no clear error). The fix:

1. Bootstrap script writes its outputs to a known path: `infra/.../bootstrap.json`.
2. The dev launcher reads from that JSON on every boot:

   ```bash
   PROJECT_ID="$(jq -r .projectId infra/.../bootstrap.json)"
   CLIENT_ID="$(jq -r .clientId  infra/.../bootstrap.json)"
   patch_env_kv packages/backend/.env AUTH_AUDIENCE       "$PROJECT_ID"
   patch_env_kv .env.local           VITE_OIDC_CLIENT_ID "$CLIENT_ID"
   ```

3. The boot summary prints what was patched: `AUTH_AUDIENCE=<id> (from bootstrap.json)`.

The script becomes self-correcting: any drift the user introduced manually (or any reset they did) is fixed on the next run.

## State file — detect destructive drift early

Some changes need a destructive reset. Example: Zitadel persists `externalDomain`/`externalSecure`/`externalPort` in its database on first init. If the user moves laptops between Wi-Fi networks (LAN IP changes) and re-runs the script, the cert and Caddyfile update fine — but the Zitadel volume still believes the old IP, and tokens it issues will have the wrong `iss`.

Encode this in a state file written next to the script:

```bash
STATE_FILE=".dev.script.state"

# Read previous run's identity
PREV=""
[[ -f "$STATE_FILE" ]] && PREV="$(grep -E '^EXTERNAL_FULL=' "$STATE_FILE" | cut -d= -f2-)"

# Compose current run's identity (the things that, if changed, require reset)
CURRENT="${SCHEME}://${EXTERNAL_DOMAIN}:${IDP_PORT}"

# Check the volume — if it doesn't exist yet, no drift to worry about
HAS_VOLUME="$(docker volume ls --format '{{.Name}}' | grep -E '<idp>-pgdata$' | head -1 || true)"

if $RESET; then
  log_warn "--reset: dropping IdP volume…"
  docker compose -f "$IDP_COMPOSE" down -v 2>/dev/null || true
  PREV=""
elif [[ -n "$PREV" && "$PREV" != "$CURRENT" && -n "$HAS_VOLUME" ]]; then
  log_error "IdP was initialized with $PREV; switching to $CURRENT requires a reset."
  log_error "Run: ./dev.sh --reset   (this drops users, secrets, and PATs)"
  exit 1
fi

# Persist for next run
{ echo "EXTERNAL_FULL=$CURRENT"; echo "HOST=$HOST"; echo "TLS=$TLS_MODE"; } > "$STATE_FILE"
```

What this buys you:

- A stranger running the script sees an actionable error: "your previous setup was X, you're trying Y, do `--reset`".
- The `--reset` flag is gated behind explicit user intent — destructive actions never happen surprise.
- The state file is gitignored; it captures only this machine's last invocation.

## Skip work that's already done — carefully

Some steps are expensive (bootstrap calls a remote API; cert generation calls mkcert). Skipping them on no-op re-runs is great for adoption — "the script takes 4s vs. 35s every time" is the difference between "I always run it" and "I run things by hand because the script is slow."

### The naive skip — and why it bit us

The obvious cache key is "the externally-visible identity changed":

```bash
SKIP_BOOTSTRAP=false
if [[ "$PREV_EXTERNAL" == "$CURRENT_EXTERNAL" && -f "$BOOTSTRAP_JSON" ]]; then
  SKIP_BOOTSTRAP=true
fi
```

This works when `EXTERNAL_FULL` (scheme + domain + port) is the only thing that affects the bootstrap output. It **breaks silently** the moment any other input changes — typically the redirect / post-logout URIs, the OIDC scope list, or the login version flag. The script re-runs successfully, the user thinks the change propagated, and the IdP keeps the old config. Real-world hit: changing `OIDC_POST_LOGOUT_URIS="${WEB_BASE}/"` to `"${WEB_BASE}/login,${WEB_BASE}/"` did nothing because the cache key didn't include the URI list — every logout kept failing with `error=invalid_request post_logout_redirect_uri invalid` until someone ran `--reset` (data-destructive) or hand-edited the cache file.

### The fix — pick one of two

**Option A (preferred for IdP bootstraps): always run, rely on idempotency.**

If the bootstrap is itself idempotent — search-then-create, treats "no changes" 4xx as no-op (Zitadel's `COMMAND-1m88i`, see `pitfalls.md`) — then **always run it**. The cost is a few seconds of API calls; the benefit is no drift class of bug ever exists. The state file becomes purely a drift detector for *destructive* changes (Zitadel volume already initialized with a different `EXTERNALDOMAIN` — re-init not allowed without volume drop), not a performance optimization.

```bash
log_step "Bootstrap (idempotent)…"
env "${BOOTSTRAP_ENV[@]}" \
  ZITADEL_API_URL="${ZITADEL_BASE}" \
  OIDC_REDIRECT_URIS="${WEB_BASE}/auth/callback,${WEB_BASE}/silent-renew" \
  OIDC_POST_LOGOUT_URIS="${WEB_BASE}/login,${WEB_BASE}/" \
  npx tsx scripts/bootstrap-zitadel.ts
```

**Option B: hash all the inputs into the cache key.**

If the bootstrap is genuinely expensive (think 30s+ of API calls) and you really want the skip, include every input the bootstrap reads into the key — not just `EXTERNAL_FULL`:

```bash
INPUT_HASH="$(printf '%s\n' \
    "$EXTERNAL_FULL" \
    "$OIDC_REDIRECT_URIS" \
    "$OIDC_POST_LOGOUT_URIS" \
    "$OIDC_SCOPES" \
    "$LOGIN_VERSION" \
  | sha256sum | cut -d' ' -f1)"

if [[ "$PREV_INPUT_HASH" == "$INPUT_HASH" && -f "$BOOTSTRAP_JSON" ]]; then
  SKIP_BOOTSTRAP=true
fi
```

Persist `INPUT_HASH` alongside `EXTERNAL_FULL` in the state file. Any bootstrap input change invalidates the cache automatically.

### Recommendation

Default to **option A** unless you measure the bootstrap actually taking 30+ seconds. The "skip if EXTERNAL_FULL matches" optimization looks innocent but turns the bootstrap into write-only state — no signal to the user that their env change didn't take effect. Option B is fine when the cost is real, but the bug class returns the moment someone adds a new input and forgets to extend the hash.

Cert generation has the same shape but a much smaller surface — the inputs are just the SAN list, and a sidecar file (`infra/certs/.names`) comparing the previous SAN list to the current one is enough.

## Idempotent updates to remote state

Idempotency rules also apply when the script talks to a remote API:

- **Search-then-create**, not always-create. POST `/users/_search?username=alice@…` first; only POST `/users` if the result is empty.
- **Catch "no changes" 4xx as no-op**. Some APIs (Zitadel notably) return 400 on PUTs that would result in no diff. Wrap those calls and treat the specific error code as success.
- **Capture and re-emit IDs**, never re-derive from name. If the bootstrap creates an Org, the next run should look it up by name, not assume the previous ID.

Reference for the JRC Zitadel pattern: see the consumer's `bootstrap-zitadel.ts` and the `zitadel-idp` skill's `api-cheatsheet.md §"Re-reading bootstrap output after volume reset"`.

## Files generated on every run (gitignored)

These should always be in `.gitignore`:

```text
# dev script artifacts
.dev.script.state
infra/docker/docker-compose.*.override.yml
infra/certs/
infra/caddy/Caddyfile
.vite.config.lan.ts
public/dev-rootCA.pem
.env.local
```

Adapt the names to whatever the script actually generates. The point: a fresh clone should regenerate all of these on the first `./dev.sh` run, and a `git status` after running should show no tracked files modified.

## Failure mode: partial run

If the script crashes mid-execution (e.g., docker daemon isn't running), the state file should reflect what's true, not what was attempted. Update the state file **only after the bootstrap+config phase succeeds** — at the end of the "everything ready to run dev servers" point. That way a crash leaves no stale state for the next run to disagree with.

## What `--reset` should actually do

Implementations vary, but the JRC convention:

- **`--reset`** drops the **most volatile** stable state — the IdP volume, the cert names file, the state file. It does **not** touch the application database (Postgres data); that's a separate `--purge-db` if needed.
- Always print what's about to be deleted **before** deleting, so the user can Ctrl+C if they didn't mean it.
- Encourage the user to run with `--reset` only when the state-mismatch error tells them to. Don't make it the default `clean` step — accidental data loss is a real risk.

## Boot-time sanity check inside the app

The state file + `.env` patching together cover **disk-level** drift. There's a third layer that prevents the worst class of regression: the running app process picks up its `.env` once at boot and keeps it in memory. If the launcher patches `.env` between sessions but the process from a previous session is still alive (orphan watcher, attached terminal, `nohup`), the runtime keeps the old values. Every request fails with no clear error from the launcher's perspective — disk and source-of-truth file agree, only the heap is stale.

The defensive pattern: **the app reads the launcher's source-of-truth file at boot and warns LOUD on divergence**.

```typescript
// packages/backend/src/config/sanity.ts
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Compares runtime env against the launcher-generated source-of-truth file.
 * Warn-only: in production the file does not exist and the check is silent.
 * In dev, divergence means "kill this process and re-run the launcher".
 */
export function checkConfigSanity(env: { AUTH_AUDIENCE: string }): void {
  const path = resolve(process.cwd(), '../../infra/.../bootstrap.json');
  if (!existsSync(path)) return;
  const truth = JSON.parse(readFileSync(path, 'utf8')) as { projectId?: string };
  if (truth.projectId && env.AUTH_AUDIENCE !== truth.projectId) {
    console.error(
      `[sanity] AUTH_AUDIENCE=${env.AUTH_AUDIENCE} but bootstrap.json says ${truth.projectId}. ` +
      `Stop this process and re-run ./dev.sh — your runtime is stale.`,
    );
  }
}
```

Call it once at boot, after env validation:

```typescript
const env = loadEnv();
checkConfigSanity(env);
const app = await compose(env);
```

**Why warn-only, not fail-fast.** In production `bootstrap.json` doesn't exist; the check is a silent no-op. In dev, fail-fast turns a transient drift into a hard outage every time the launcher runs slightly out of order. The loud log is enough — the operator sees it in the next request and knows the answer in 5 seconds instead of 30 minutes. If your team prefers fail-fast, gate it behind `NODE_ENV !== 'production'` *and* file existence.

This pattern is generic — it applies to any launcher-generated source-of-truth file:

| Launcher file | Runtime check |
|---|---|
| Zitadel `bootstrap.json` | `AUTH_AUDIENCE === projectId` |
| `.dev.script.state` (`EXTERNAL_FULL`) | `BASE_URL === EXTERNAL_FULL` |
| `infra/db/connection.json` | `DATABASE_URL` host:port matches |
| `infra/queue/connection.json` | `QUEUE_URL` matches |

The check pays for itself the first time someone hits "but I edited the .env and restarted the launcher, why is it still broken?" — the answer is usually "you have a stale process from a previous session", and the sanity log says so.
