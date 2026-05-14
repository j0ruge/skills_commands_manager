# Bash patterns — copy-pasteable building blocks

These are the canonical idioms used in JRC `dev.sh` scripts. They handle the long tail of "works on my machine" problems (different distros, different `ss`/`fuser`/`lsof` versions, broken `kill -- -PID`, missing `realpath`).

## Header — strict mode + portable script-dir resolution

```bash
#!/usr/bin/env bash
set -euo pipefail

# Resolve the absolute directory of this script. realpath isn't guaranteed
# (older macOS), so we fall through readlink → POSIX cd/pwd-P.
resolve_script_dir() {
  local src="${BASH_SOURCE[0]}"
  if command -v realpath >/dev/null 2>&1; then
    dirname "$(realpath "$src")"
  elif readlink -f "$src" >/dev/null 2>&1; then
    dirname "$(readlink -f "$src")"
  else
    (cd "$(dirname "$src")" && pwd -P)
  fi
}

DIR="$(resolve_script_dir)"
cd "$DIR"
```

`set -euo pipefail` is non-negotiable — without `pipefail` a failure inside a piped command silently ignored. With these on, every command that can fail will halt the script.

## Color logging — terse, prefix-able

```bash
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "\n${BLUE}==>${NC} $*"; }

# Per-service prefixes — paint each service's stdout a different color
PREFIX_API="${GREEN}[BACKEND]${NC}"
PREFIX_WEB="${BLUE}[WEB]${NC}"
```

When piping a service's stdout through `sed -u "s/^/$(echo -e "$PREFIX_API") /"`, **`-u` (unbuffered) matters** — without it, `sed` buffers in chunks and you see logs in big bursts instead of as they happen.

## Argument parsing

```bash
HOST_OVERRIDE=""
LAN_MODE=true
TLS_MODE=true
RESET=false
DOWN_ON_EXIT=false

usage() { cat <<EOF
Usage: ./dev.sh [OPTIONS]
  --host <ip>      override LAN IP detection
  --no-lan         localhost only (HTTP)
  --no-https       skip TLS (LAN OIDC will fail)
  --reset          drop volatile state (e.g., IdP volume)
  --down           tear down containers on exit
  -h, --help       show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)     HOST_OVERRIDE="$2"; shift 2 ;;
    --no-lan)   LAN_MODE=false; TLS_MODE=false; shift ;;
    --no-https) TLS_MODE=false; shift ;;
    --reset)    RESET=true; shift ;;
    --down)     DOWN_ON_EXIT=true; shift ;;
    -h|--help)  usage; exit 0 ;;
    *) log_error "Unknown option: $1"; usage; exit 1 ;;
  esac
done
```

Generate **only the flags the script actually uses**. Don't ship `--reset` if there's no destructive state.

## LAN IP detection (Linux/macOS)

```bash
detect_lan_ip() {
  local ip=""
  if command -v hostname >/dev/null 2>&1; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"   # Linux
  fi
  if [[ -z "$ip" ]] && command -v ip >/dev/null 2>&1; then
    ip="$(ip -4 -o route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')"
  fi
  if [[ -z "$ip" ]] && command -v ipconfig >/dev/null 2>&1; then
    ip="$(ipconfig getifaddr en0 2>/dev/null)"           # macOS Wi-Fi
    [[ -z "$ip" ]] && ip="$(ipconfig getifaddr en1 2>/dev/null)"
  fi
  echo "$ip"
}
```

`hostname -I` is Linux-only; `ip route get` is GNU iproute2 (Linux); `ipconfig getifaddr en0` is macOS. Order matters — try the cheapest first.

For LAN sharing, derive the external domain via sslip.io: `<LAN_IP>.sslip.io` resolves to `<LAN_IP>` for any DNS client. That gives you a real hostname for the cert without DNS setup.

## Healthchecks (per-component, with timeout)

### Postgres in a docker container

```bash
log_step "Waiting for Postgres…"
for i in $(seq 1 30); do
  if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "$DB_USER" >/dev/null 2>&1; then
    log_info "Postgres ready"
    break
  fi
  sleep 1
  [[ $i -eq 30 ]] && { log_error "Postgres did not become ready"; exit 1; }
done
```

`exec -T` forces no-tty; without it, non-interactive callers (CI, this script under `&`) crash with `the input device is not a TTY`.

### HTTP service

```bash
log_step "Waiting for service at ${BASE_URL}/healthz…"
CURL_OPTS=()
if $TLS_MODE; then CURL_OPTS+=(--cacert "${MKCERT_CAROOT}/rootCA.pem"); fi
for i in $(seq 1 60); do
  if curl -fsS "${CURL_OPTS[@]}" "${BASE_URL}/healthz" >/dev/null 2>&1; then
    log_info "Service ready at ${BASE_URL}"
    break
  fi
  sleep 2
  [[ $i -eq 60 ]] && { log_error "Service did not become ready at ${BASE_URL}"; exit 1; }
done
```

`-f` makes curl exit non-zero on 4xx/5xx (needed for the loop logic). Use `--cacert` when the endpoint is HTTPS with a local CA — without it curl will reject the cert.

### Bootstrap script

```bash
log_step "Bootstrap…"
NODE_EXTRA_CA_CERTS="${MKCERT_CAROOT}/rootCA.pem" \
  ZITADEL_API_URL="${ZITADEL_BASE}" \
  npx tsx packages/idp/scripts/bootstrap-zitadel.ts
test -s infra/.../bootstrap.json || { log_error "Bootstrap did not produce bootstrap.json"; exit 1; }
```

Don't trust exit code alone — verify the expected output file is present and non-empty.

## Port discovery — find-next-free with peer coordination

There are two valid strategies when a service port is busy at boot, and choosing wrong leads to silent failures (see `pitfalls.md` §P17). Pick by ownership:

| Strategy | When the port owner is… | Behavior |
|---|---|---|
| **Reclaim** (next section) | …a previous run of *this* dev script (orphan) — script owns the port | Kill the holder, bind freshly |
| **Discovery** (this section) | …**anything else** the script can't safely assume to own — another project's dev launcher, a system service, a container the user wants to keep, a process from another user | Find the next free port and propagate it to peers |

The discovery strategy is non-destructive and the right default for service ports a multi-process launcher coordinates (backend + frontend + reverse proxy + …). Use reclaim only for ports the script demonstrably opened itself (e.g., a `pgrep -af` match on a stack-specific cmdline pattern).

```bash
# Walk upward from base_port; return the first free port within max_tries.
# Fail with non-zero exit if exhausted, so the caller can abort with a clear error.
find_available_port() {
  local base_port="$1"
  local max_tries="${2:-10}"
  local port="$base_port"
  local attempt=0

  while [[ $attempt -lt $max_tries ]]; do
    if ! ss -tlnp 2>/dev/null | grep -q ":${port} "; then
      echo "$port"
      return 0
    fi
    ((port++))
    ((attempt++))
  done

  return 1
}

# Adjusts service port variables in-place if their default is busy.
discover_free_ports() {
  if ss -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT} "; then
    log_warn "Port ${BACKEND_PORT} (backend) busy — searching alternative…"
    BACKEND_PORT="$(find_available_port "$((BACKEND_PORT + 1))")" \
      || { log_error "No free port for backend."; exit 1; }
    log_warn "Backend will use: ${BACKEND_PORT}"
  fi
  if ss -tlnp 2>/dev/null | grep -q ":${FRONTEND_PORT} "; then
    log_warn "Port ${FRONTEND_PORT} (frontend) busy — searching alternative…"
    FRONTEND_PORT="$(find_available_port "$((FRONTEND_PORT + 1))")" \
      || { log_error "No free port for frontend."; exit 1; }
    log_warn "Frontend will use: ${FRONTEND_PORT}"
  fi
}
```

### Peer coordination — passing the chosen port to dependent services

A discovered port is useless if peers still target the default. Backend at 3001 with Vite proxy hardcoded to 3000 = broken proxy. Frontend at 8081 with backend CORS allowing only 8080 = CORS failures. Propagate the chosen ports via **per-subshell env vars**, not `export` — this avoids two problems at once:

1. **Name collisions**: Node, Vite, Next.js, Nest, etc. all read `process.env.PORT`. A global `export PORT=3001` would also leak into the frontend subshell where it means a different port.
2. **Polluting the user's interactive shell** after the launcher exits.

```bash
# Backend gets its own PORT plus the frontend's URL for CORS.
# Frontend gets its own PORT plus the backend's port for the dev proxy (Vite, Next, etc.).
( cd "$BACKEND_DIR" && \
    PORT="$BACKEND_PORT" \
    APP_WEB_URL="http://localhost:$FRONTEND_PORT" \
    npm run dev 2>&1 | sed -u "s/^/$(echo -e "$PREFIX_BACK") /" ) &
PIDS+=($!)

( cd "$FRONTEND_DIR" && \
    PORT="$FRONTEND_PORT" \
    API_PORT="$BACKEND_PORT" \
    npm run dev 2>&1 | sed -u "s/^/$(echo -e "$PREFIX_FRONT") /" ) &
PIDS+=($!)
```

The exact env var names depend on the stack — read each peer's config (Vite proxy `target`, backend CORS allowlist, OIDC redirect URI, reverse-proxy upstream) and emit one inline assignment per peer-dependency edge. If a service reads its peer's URL/port from a `.env` field, **the inline subshell var wins over the file** (dotenv defaults to `override: false`; Vite reads `process.env.*` directly). That keeps committed `.env` files untouched and the runtime override scoped to the launcher.

### Synergy with `strictPort: true`

Vite's `strictPort: true` (and equivalents like Next.js `--port` without auto-fallback) feels like it conflicts with discovery — actually it's the right combo. Pre-flight discovery picks a port the OS confirms is free; `strictPort` makes Vite bind exactly that port instead of silently falling forward to 5174/8081/etc. on its own. Without strictPort, Vite's silent fallback desynchronizes the launcher's summary banner, the proxy `API_PORT`, and the actual bind — debugging that drift is much harder than letting Vite hard-fail when its assumed port is taken (which can't happen if discovery ran first).

### Race window

There's a small TOCTOU window between `find_available_port` returning a port and the service actually binding it — another process could grab it in between. In practice the launcher is the only thing racing for those ports during local dev, so the risk is negligible. If it bites in a CI matrix or a busy shared host, retry the whole discover-then-spawn sequence (caller-side loop) rather than blocking the port via a sentinel socket — sentinel sockets create their own cleanup problems.

## Port reclaim with a fallback chain

```bash
kill_port() {
  local port="$1"
  local pids=""
  if command -v fuser >/dev/null 2>&1; then
    pids="$(fuser "${port}/tcp" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$' | sort -u || true)"
  fi
  if [[ -z "$pids" ]] && command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  fi
  if [[ -z "$pids" ]]; then
    pids="$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u || true)"
  fi
  for pid in $pids; do
    log_warn "Port $port held by PID $pid — killing…"
    kill "$pid" 2>/dev/null || true
    sleep 1
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
  done
}
```

Why three methods: `ss -p` requires root on some distros to show PIDs; `fuser` may not be installed; `lsof` is the most universal but missing on minimal containers. Falling through covers the realistic environments.

### Fourth fallback: `pgrep` by command line

Even with all three above, there's a real failure mode: hardened kernels (recent Ubuntu, container hosts with `hidepid=2`, some sandboxed sessions) hide PIDs of processes owned by other UIDs **and** sometimes from the same UID across PID namespaces. `ss -p` then returns the listener but no `pid=` token; `lsof` returns empty; `fuser` returns empty. `kill_port` becomes a silent no-op and the next `npm run dev` fails with `EADDRINUSE`. Real-world hit count from the JRC stack: 4 zombie backend trees survived a `dev.sh` Ctrl+C because no port-based tool could see the PIDs.

When the dev stack uses well-known commands (Vite, `tsx watch`, `nest start --watch`, `dotnet watch`), `pgrep -af` finds them by the command line itself — no port lookup required:

```bash
kill_known_dev_servers() {
  # Fallback for kernels where ss/lsof can't see PIDs. Match by command line of
  # the processes the script itself starts; tighten the patterns to your stack
  # to avoid killing unrelated processes (a global `pgrep -af node` is too broad).
  local pids
  pids="$(pgrep -af 'tsx.*src/server\.ts|vite([[:space:]].*--port[[:space:]]+5173|.*\.vite\.config\.lan)' 2>/dev/null \
            | awk '{print $1}' || true)"
  for pid in $pids; do
    log_warn "Stale dev process PID $pid — killing…"
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
    sleep 1
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
  done
}

log_step "Reclaiming dev ports…"
kill_port 3000
kill_port 5173
kill_known_dev_servers   # safety net for kernels that hide PIDs from ss/lsof
```

Run `kill_known_dev_servers` **after** `kill_port` (not instead) — the port path is the cleanest when it works, and only catches what's actually listening on those ports. The pgrep path catches detached children whose port bind already failed (e.g., the second `tsx watch` that lost the EADDRINUSE race but stayed alive holding nothing).

Tune the regex to your stack:

| Process | Pattern fragment |
|---|---|
| Express via `tsx watch` | `tsx.*src/server\.ts` |
| NestJS dev | `nest start --watch` |
| Vite | `vite([[:space:]].*--port[[:space:]]+<PORT>\|.*\.vite\.config\.lan)` |
| `dotnet watch` | `dotnet[[:space:]]+watch` (be careful — kills any dotnet watch on the host) |
| Cargo watch | `cargo-watch` |

Avoid bare `pgrep -af node` or `pgrep -af npm` — they match every Node tool the user has running. Always anchor the pattern to something specific to *this script's* processes (a script path, a specific config file name, a unique CLI flag).

#### Gotcha — monorepo path constraints flip the regex ordering

When the dev stack lives inside a monorepo (`packages/backend`, `apps/web`, `services/api/`), the *intuitive* tightening is to add the package path to the pattern: `tsx.*packages/backend.*server\.ts`. **This silently never matches.** The actual cmdline of a `tsx` process invoked from the monorepo is:

```
node /home/u/repo/packages/backend/node_modules/.bin/tsx watch --env-file=.env src/server.ts
```

`packages/backend` appears **before** `tsx`, not after. The regex `tsx.*packages/backend.*server\.ts` requires the opposite order, never matches, and `kill_known_dev_servers` becomes a silent no-op while looking like it's working — the worst kind of bug because `pgrep -af` returning nothing reads as "nothing to kill" instead of "regex mismatch".

Right pattern for monorepo scoping (don't mention `tsx` at all — pin to the package + entrypoint):

```bash
# Express via tsx watch in monorepo
'packages/backend.*server\.ts'
# NestJS in apps/api
'apps/api.*nest start'
# Vite for a specific config file
'\.vite\.config\.lan|apps/web.*vite\.config'
```

Real-world hit count from JRC: 8 zombie `tsx watch` trees from previous sessions survived months because the regex was wrong; the next `--reset-zitadel` produced a 401-storm because those zombies had stale env+JWKS in the heap. The lesson generalizes: when tightening a pgrep pattern, sanity-check by spawning a test process and running the regex against `ps -ef | grep <test-process>` *before* trusting that `kill_known_dev_servers` does anything.

#### Companion gotcha — `tsx watch` doesn't watch `.env`

When the launcher patches `.env` on every boot (which `dev-script` recommends as the canonical fix for stale-config drift after a reset), **`tsx watch` does not pick up the change** — it only reloads on `src/**` changes by default. Result: `.env` on disk has the new audience/issuer/ID, but the running process keeps the old values in memory. Every API call then 401s with no clear error.

Two fixes, in order of preference:

1. **Make watch include `.env` on the runner**: `tsx watch --include=.env src/server.ts` (analogous flags exist for `nodemon --watch .env`, `dotnet watch --include=.env`, and `cargo-watch -w .env`). One-line fix in `package.json`'s `dev` script.
2. **Kill the runner after patching**: have the launcher run `kill_known_dev_servers` **after** writing the new `.env` and before re-spawning. Belt-and-suspenders if the watcher's include flag is unreliable for binary changes.

Without either, the disk-vs-memory drift survives every "I edited the env, why is it still broken" debugging session.

## Trap-based cleanup

```bash
PIDS=()

cleanup() {
  echo ""
  log_warn "Shutting down…"
  for pid in "${PIDS[@]:-}"; do
    [[ -z "$pid" ]] && continue
    # Process group kill: child shells with `setsid` have their own pgid;
    # `kill -- -PGID` reaches everyone in the group, not just the leader.
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  done
  sleep 1
  for pid in "${PIDS[@]:-}"; do
    [[ -z "$pid" ]] && continue
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
  done

  if $DOWN_ON_EXIT; then
    log_warn "--down: tearing down containers"
    docker compose -f "$COMPOSE" down 2>/dev/null || true
  fi
  log_info "Stopped."
}
trap cleanup EXIT SIGINT SIGTERM
```

The `setsid npm run dev` pattern (start child in a new process group) plus `kill -- -PID` is the only reliable way to kill `npm` and its descendants together. Without `setsid` the child inherits the parent's pgid and `kill -- -$!` ends up SIGTERM'ing the whole script.

## Patching `.env` files in place

```bash
patch_env_kv() {
  local file="$1" key="$2" value="$3"
  if grep -qE "^${key}=" "$file"; then
    # `|` as sed delimiter — `/` collides with URLs.
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    echo "${key}=${value}" >> "$file"
  fi
}

patch_env_kv "$BACKEND_ENV" "AUTH_ISSUER"   "${ZITADEL_BASE}"
patch_env_kv "$BACKEND_ENV" "AUTH_AUDIENCE" "${PROJECT_ID}"
```

`sed -i` differs between GNU (Linux) and BSD (macOS) — the empty-string suffix `sed -i ''` is BSD-only. If the script targets both, use a portable variant:

```bash
# Portable in-place edit
if [[ "$(uname)" == "Darwin" ]]; then
  sed -i '' "s|...|...|" "$file"
else
  sed -i "s|...|...|" "$file"
fi
```

## Generated wrapper config (Vite example)

When the project has `vite.config.ts` and the dev script needs `server.allowedHosts: true` for LAN HTTPS, write a wrapper next to it (gitignored) and pass `--config <wrapper>`:

```bash
cat > "${DIR}/.vite.config.lan.ts" <<'EOF'
// Generated by dev.sh — do not edit by hand
import base from "./vite.config";
import { mergeConfig } from "vite";
export default mergeConfig(base, {
  server: {
    allowedHosts: true,
    hmr: { clientPort: 5443, protocol: "wss", host: process.env.DEV_SH_EXTERNAL ?? "localhost" },
  },
});
EOF

DEV_SH_EXTERNAL="${EXTERNAL_DOMAIN}" \
  npm run dev -- --config .vite.config.lan.ts --host 0.0.0.0 --port 5173 --strictPort
```

`--strictPort` is important — if 5173 is busy, you want a hard fail (so `kill_port` ran first), not a silent fallback to 5174 that breaks the OIDC redirect URI.

## Final summary block

```bash
echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}  ${PROJECT_NAME} — dev mode${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo -e "  ${BLUE}Frontend${NC}   → ${WEB_BASE}"
echo -e "  ${GREEN}Backend${NC}    → ${API_BASE}/api"
[[ -n "${ZITADEL_BASE:-}" ]] && echo -e "  ${MAGENTA}IdP${NC}        → ${ZITADEL_BASE}"
echo ""
echo -e "  Ctrl+C to stop dev servers (containers stay; --down to tear down)."
echo -e "${GREEN}=============================================${NC}"
echo ""

wait
```

`wait` at the end is essential — it keeps the script alive while the background dev servers run. Without it, the script exits immediately and the `trap cleanup` fires, killing everything.
