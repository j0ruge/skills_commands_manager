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

## Skip work that's already done

Some steps are expensive (bootstrap calls a remote API; cert generation calls mkcert). Skip them when the inputs match the previous successful run:

```bash
SKIP_BOOTSTRAP=false
if [[ "$PREV" == "$CURRENT" && -f "$BOOTSTRAP_JSON" ]]; then
  SKIP_BOOTSTRAP=true
fi

if $SKIP_BOOTSTRAP; then
  log_step "Bootstrap — skipping (already up to date for $CURRENT)"
else
  log_step "Bootstrap…"
  # ...
fi
```

This is the difference between "the script takes 4s on a no-op re-run" and "the script takes 35s every time", which silently encourages people to skip the script and run things by hand. Speed matters for adoption.

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
