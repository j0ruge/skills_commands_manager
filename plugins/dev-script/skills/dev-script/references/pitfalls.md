# Pitfalls — the recurring traps to encode in every script

These are the bugs that bit JRC projects (Zitadel/Battery Lifecycle, DSR Ecosystem) and cost real hours to diagnose. The dev script must protect against them — either by setting things up correctly the first time, or by surfacing the failure mode loudly when conditions change.

## P1 — Vite ≥ 5 blocks non-localhost hosts

**Symptom**: Site works on `http://localhost:5173` but `https://<lan-ip>.sslip.io:5443` returns

```text
Blocked request. This host ("...") is not allowed.
To allow this host, add "..." to `server.allowedHosts` in vite.config.js.
```

**Cause**: Vite 5 added a host-allowlist defense. The default is localhost-only.

**Fix in the dev script**: do **not** edit `vite.config.ts` (that's in source control). Generate a wrapper next to it:

```typescript
// .vite.config.lan.ts — gitignored
import base from "./vite.config";
import { mergeConfig } from "vite";
export default mergeConfig(base, {
  server: { allowedHosts: true, hmr: { /* see tls-https-recipe */ } },
});
```

Run with `--config .vite.config.lan.ts`. See `tls-https-recipe.md §"Step 3a"`.

## P2 — Backend Node can't validate JWKS over HTTPS with a self-signed cert

**Symptom**: 100% of authenticated `/api` requests return 401. JWT decoded by hand looks perfect (`iss`, `aud`, `exp` all good). Frontend silent-renew goes into a loop. Backend rate limit (e.g., 120/min) eventually returns 429.

**Cause**: `createRemoteJWKSet(new URL(jwksUrl))` (jose) does a regular Node `fetch`. Node uses the OS trust store, which doesn't know the mkcert root CA. TLS handshake fails before signature check; jose surfaces it as a generic `JWKSNoMatchingKey` / `JWSSignatureVerificationFailed` — **not** a TLS error.

**Fix in the dev script**:

```bash
NODE_EXTRA_CA_CERTS="$(mkcert -CAROOT)/rootCA.pem" npm run dev
```

Inject the env on the backend launch and the bootstrap script invocation. See `tls-https-recipe.md §"Step 4"`.

## P3 — Stale `AUTH_AUDIENCE` after IdP volume reset

**Symptom**: Same 401 storm as P2, but no TLS issue — JWKS fetches fine. JWT's `aud` is `370883…` and the backend expects `370503…`.

**Cause**: The IdP regenerated `projectId` on volume reset. Backend `.env` still has the previous one.

**Fix in the dev script**: re-derive on every boot from the bootstrap output JSON:

```bash
PROJECT_ID="$(jq -r .projectId infra/.../bootstrap.json)"
patch_env_kv packages/backend/.env AUTH_AUDIENCE "$PROJECT_ID"
```

Never hardcode the audience in the committed `.env`. See `idempotency-and-state.md §"Re-derive volatile IDs every boot"`.

## P4 — Zitadel persists `externalDomain` on init

**Symptom**: User moves laptop between networks; LAN IP changes. Re-running the dev script: certs and Caddyfile regenerate fine, but Zitadel-issued tokens have `iss = http://<old-ip>.sslip.io:8443`. Every JWT validation fails with `iss` mismatch.

**Cause**: `ZITADEL_EXTERNALDOMAIN`, `ZITADEL_EXTERNALPORT`, `ZITADEL_EXTERNALSECURE` are persisted in the Zitadel database on first init. Restarting the container with new env vars **does not** update them.

**Fix in the dev script**: state-file drift detection (see `idempotency-and-state.md §"State file"`). Refuse to start if the IdP volume exists and the persisted external URL doesn't match the current one. Require `--reset` to acknowledge the destructive step.

## P5 — Bootstrap idempotency: `400 COMMAND-1m88i "No changes"`

**Symptom**: First `./dev.sh` works. Second `./dev.sh` halts at the bootstrap step with

```text
Zitadel 400 PUT /management/v1/projects/{p}/apps/{a}/oidc_config:
{"code":9,"message":"No changes (COMMAND-1m88i)"}
```

**Cause**: Zitadel rejects PUTs whose body matches the current state. An idempotent bootstrap that always PUTs the OIDC config trips on this.

**Fix in the bootstrap script** (the dev script invokes it but doesn't fix it; the bootstrap itself needs the guard):

```typescript
try {
  await api(`/management/v1/projects/${pid}/apps/${aid}/oidc_config`, {
    method: 'PUT', body: JSON.stringify(payload),
  });
} catch (err) {
  if (err instanceof Error && err.message.includes('COMMAND-1m88i')) {
    // No changes — already in sync. Idempotent no-op.
  } else {
    throw err;
  }
}
```

Same idiom for login policy, password policy, SMTP — any "update" endpoint in Zitadel can return this code.

## P6 — `--tlsMode external` flag missing on Zitadel start

**Symptom**: Zitadel container restart-loops with TLS bind errors, even though `ZITADEL_TLS_ENABLED=false` and `ZITADEL_EXTERNALSECURE=true`.

**Cause**: The two env vars are necessary but not sufficient. The start command also needs `--tlsMode external`. Without it the binary still tries to bind a TLS listener.

**Fix in the dev script** (when generating the compose override):

```yaml
services:
  zitadel:
    command: >-
      start-from-init
      --masterkey ${ZITADEL_MASTERKEY}
      --tlsMode external
```

## P7 — `crypto.subtle` unavailable outside secure contexts

**Symptom**: SPA login button does nothing — no console error, no network request, no navigation. Clicking again: still nothing.

**Cause**: `oidc-client-ts` PKCE calls `crypto.subtle.digest()` to compute the code challenge. Browsers expose `crypto.subtle` only in secure contexts. `localhost`/`127.0.0.1` are exceptions; any other HTTP origin is not. Worse: `react-oidc-context` callers typically `void auth.signinRedirect(...)`, swallowing the rejection.

**Fix in the dev script**: serve everything over HTTPS even for LAN dev. See `tls-https-recipe.md`.

**Diagnostic the dev script can ship in its README**: tell the user to run `typeof crypto.subtle` in the SPA's DevTools console — `"undefined"` means insecure context. Pair it with `await auth.signinRedirect(...).catch(e => console.error(e))` to surface the silent rejection.

## P8 — Backend rate limiter too tight for dev

**Symptom**: Dashboard "flashes" / re-renders rapidly; eventually shows `HTTP 429` toasts everywhere.

**Cause**: Express + `express-rate-limit` defaults to 120 req/min. React StrictMode (mounts twice in dev) + React Query refetches + one of the JWT/audience pitfalls above + silent-renew loop = blow past 120/min in seconds.

**Fix in the dev script**: temporarily disable the rate limiter for dev:

```bash
patch_env_kv packages/backend/.env RATE_LIMIT_PER_MINUTE 0
```

Document this in the boot summary so it's not a surprise to anyone who reads the env.

## P9 — Multiple stale dev servers holding ports

**Symptom**: Backend startup fails with `Error: listen EADDRINUSE: address already in use :::3000`. Vite logs `Port 5173 is already in use`. The dev script's own `kill_port` "succeeded" but the port stayed held.

**Cause**: Two paths:

1. `ss -tlnp` doesn't show PIDs for processes you don't own (or without root). The script's port-clearing fell back to a method that returned no PIDs.
2. A stale `npm run dev` from a previous shell session still has the port. A `pkill -f vite` killed only one of several `tsx watch` orphans.

**Fix in the dev script**: chain three port-clear methods (`fuser` → `lsof` → `ss`) so something works on every distro. After clearing, **verify** the port is free before spawning the dev server. See `bash-patterns.md §"Port reclaim with a fallback chain"`.

## P10 — Background processes orphaned after Ctrl+C

**Symptom**: User hits Ctrl+C; the script prints "Stopped." but `ps -ef | grep tsx` shows the backend still running. Re-running the script then fails on EADDRINUSE.

**Cause**: `kill $!` reaches the shell of `npm run dev`, not its children (`tsx`, `node`). The npm shell exits but tsx keeps running until it loses its parent and inherits init.

**Fix in the dev script**:

- Start each service with `setsid` so it has its own process group.
- Track `$!` (which is the leader's PID = pgid).
- Kill the **group**, not the leader: `kill -- "-$pid"`.

```bash
( cd packages/backend; setsid npm run dev 2>&1 | sed -u "..." ) &
PIDS+=($!)

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT SIGINT SIGTERM
```

## P11 — Bootstrap script writes to stdout but not the expected file

**Symptom**: Dev script's `if [[ -f bootstrap.json ]]` check fails; the script proceeds without re-deriving IDs; subsequent JWT validation breaks.

**Cause**: Bootstrap script logs the JSON to stdout but doesn't write to disk. The dev script's check passed semantics ("script exited 0") but missed that the side effect didn't happen.

**Fix in the dev script**: verify the **expected output** is present, not just the exit code:

```bash
npx tsx scripts/bootstrap.ts
test -s infra/.../bootstrap.json || { log_error "Bootstrap did not produce bootstrap.json"; exit 1; }
```

## P12 — Compose `network_mode: host` on macOS/Windows

**Symptom**: Caddy proxies via `localhost:5173` work fine on Linux, fail on macOS/Windows because Docker Desktop's "host network" mode is limited (or disabled).

**Cause**: `network_mode: host` is a Linux primitive. Docker Desktop has a partial implementation behind a feature flag.

**Fix in the dev script**: detect the OS and emit a different compose snippet:

```bash
case "$(uname -s)" in
  Linux*)
    echo 'network_mode: host'
    ;;
  Darwin*|MINGW*|CYGWIN*)
    echo 'extra_hosts: ["host.docker.internal:host-gateway"]'
    echo 'ports: ["5443:5443", "3443:3443", "8443:8443"]'
    ;;
esac
```

…and make the Caddyfile reverse-proxy to `host.docker.internal:5173` instead of `localhost:5173` on non-Linux.

## P13 — `.env` patcher uses `/` as sed delimiter and breaks on URLs

**Symptom**: After running the dev script, the backend `.env` has corrupt values like `AUTH_ISSUER=https://...` mangled into something like `AUTH_ISSUER=httpsX//...`.

**Cause**: The classic `sed -i "s/^${KEY}=.*/${KEY}=${VALUE}/"` uses `/` as the delimiter, but the value contains `https://...` with slashes. sed gets confused.

**Fix**: use `|` (or any rare character) as the delimiter:

```bash
sed -i "s|^${KEY}=.*|${KEY}=${VALUE}|" "$FILE"
```

## P14 — `sed -i` portability between GNU and BSD

**Symptom**: Dev script works on Linux CI, fails on a contributor's macOS with `sed: -i: No such file or directory`.

**Cause**: BSD sed (macOS) requires an explicit empty argument: `sed -i '' "..."`. GNU sed (Linux) treats that empty string as a script.

**Fix**: choose a portable approach (use awk / use a temp file + mv) or branch on `uname -s`:

```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
  sed -i '' "$EXPR" "$FILE"
else
  sed -i "$EXPR" "$FILE"
fi
```

Linux-only scripts can ignore this; cross-platform scripts must handle it.

## P15 — Hot reload restart while bootstrap running

**Symptom**: tsx watch (or similar) restarts the backend mid-bootstrap because a file changed; the bootstrap step crashes with "ECONNREFUSED" against the still-restarting backend.

**Cause**: Bootstrap calls `localhost:3000` while the backend is in the middle of its own startup sequence. Race condition.

**Fix in the dev script**: make the bootstrap a **one-shot script that runs before** any dev servers start, **not** an in-process step of the backend. The dev script orchestrates the order: containers up → bootstrap → dev servers up.

## P16 — Long-lived dev sessions accumulate zombie watchers (silent)

**Symptom**: Months into a project, `pgrep -af tsx` (or equivalent) returns 5–10 instances of the dev runner, all bound to the same port, with stale env from previous bootstraps in their heap. Next `--reset-zitadel` (or any source-of-truth change) produces a 401-storm because *one* of those zombies wins the race for an incoming request and validates JWT against ancient JWKS.

**Cause** (compound, all real):
- Closing a terminal without Ctrl+C on the dev launcher leaves the spawned `tsx watch`/`vite`/`dotnet watch` orphaned. `setsid` decouples them from the shell session, so the OS doesn't reap them.
- The launcher's `kill_known_dev_servers` regex is wrong (the gotcha in `bash-patterns.md`), so reclamation is a silent no-op.
- The runner process doesn't watch `.env`, so even when the launcher patches the env on the next boot, in-memory state stays old.

**Fix in 3 layers** (defense in depth — none alone is sufficient):

1. **Disk in sync**: launcher patches `.env` every boot from the source-of-truth file (covered in §"Skip work that's already done — carefully").
2. **Processes in sync**: `kill_known_dev_servers` with a regex that actually matches your stack's cmdline (see `bash-patterns.md` §"Fourth fallback" + the monorepo gotcha).
3. **Heap in sync**: app boot-time sanity check that compares runtime env to source-of-truth file and warns LOUD on divergence (see `idempotency-and-state.md` §"Boot-time sanity check inside the app").

Real-world hit count from JRC: 4 sessions over 5 days, each spending 15-60 minutes diagnosing "I reset the IdP and now nothing works", every time blaming a different layer (mkcert cert? .env? bootstrap?). The 3-layer defense was the only thing that broke the cycle — any single layer continued to fail because the other two leaked state across runs.

**How to detect the trap**: if your project hits the same 401-storm symptom twice across separate sessions, stop debugging the symptom and run `pgrep -af '<your-runner-pattern>' | wc -l`. Anything > 1 is the smoking gun.

## P17 — Foreign port owner + `strictPort` = silent "script hang"

**Symptom**: User reports `./dev.sh` "hangs forever" on first run. Terminal shows the Vite line ending in `Port 8080 is in use by another process` followed by nothing. Ctrl+C does eventually quit. `ps -ef` shows the backend is happily running on its port — only the frontend never came up. The script is not actually stuck on any operation; it's stuck on `wait`.

**Cause** (3-step cascade):

1. The launcher's `kill_port`/`kill_stale_ports` runs against 8080. The port is held by **someone else's** legitimate process — a coworker's dev server, a Docker container the user wants to keep, a system service. `kill` either silently fails (different UID, missing capability) or the holder ignores `SIGTERM`. The port-clear function logs success or stays quiet and returns.
2. Vite spawns with `strictPort: true` (correct setting for prod-like dev, see `bash-patterns.md` §"Synergy with `strictPort: true`"), tries to bind 8080, fails fast, exits with an error. The Vite subshell terminates.
3. The launcher's `wait` is still tracking the backend PID, which is alive and well. From the parent's perspective nothing has changed — it just sits at `wait` indefinitely. Visually identical to a hang.

The cascade is invisible because each step looks like it "worked": kill returned (silently), Vite reported the error to its own stdout but the parent didn't propagate the failure, `wait` is doing exactly what it was asked.

**Fix in the dev script**: don't try to reclaim service ports owned by foreign processes — discover an alternative instead. See `bash-patterns.md` §"Port discovery — find-next-free with peer coordination". The rubric: reclaim is for orphans the script itself spawned (pgrep-matchable to your stack); discovery is for service ports where the owner is unknown. With pre-flight discovery, step 1 above is replaced by "port busy → use 8081 instead", peers are notified via subshell env vars (so the Vite proxy / backend CORS land on the right port), and step 2 never triggers.

**Detecting the trap without fixing it first**: run the launcher under `bash -x` and look for the gap between the last "service started" log line and the `wait` call. If there's no error in between but one of the services never appears in `ss -tlnp`, the cascade is in flight. Also: if your launcher prints a summary banner with port numbers, but `ss -tlnp` shows one of those ports bound by a PID that isn't a child of the launcher, the corresponding service silently lost the bind race.
