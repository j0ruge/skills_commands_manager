# Changelog — `dev-script`

## 0.4.0 — 2026-05-14

Lessons from a session against the LouvorFlow monorepo where the user's `dev.sh` "hung" on every cold start whenever port 8080 was held by a foreign process. The diagnosis exposed a gap in the v0.3.1 skill: it advocated kill-and-reclaim as the *only* strategy for service ports, with no acknowledgment of the scenario where the port owner is something the script can't (or shouldn't) kill.

### Added

- **`references/bash-patterns.md` §"Port discovery — find-next-free with peer coordination"** (new section, placed *before* the existing port-reclaim section so readers see the choice). Covers:
  - `find_available_port()` — iterative bump with `ss -tlnp | grep ":${port} "`, configurable max-tries, non-zero exit on exhaustion so callers can abort with a clear error.
  - `discover_free_ports()` — composes the primitive across multiple service-port variables (`BACKEND_PORT`, `FRONTEND_PORT`, …) and mutates them in place if busy.
  - **Peer-coordination pattern** with per-subshell env vars: `( cd "$DIR" && PORT=$X PEER_URL=…:$Y npm run dev ) &`. Solves two problems at once — env var name collisions (`PORT` is read by Node, Vite, Nest, Next, etc. — all of them) and pollution of the user's interactive shell. Inline subshell vars also win over `dotenv` defaults (`override: false`), so committed `.env` files stay untouched.
  - **Strategy rubric**: discover vs. reclaim — discover when the port owner is unknown/foreign (default for multi-process launchers); reclaim only when the script can prove ownership via stack-specific `pgrep -af` match.
  - **`strictPort: true` synergy** note: counter-intuitively the right combo with pre-flight discovery — discovery picks a confirmed-free port, strictPort enforces the choice instead of letting Vite silently fall forward to 5174 (which would desync proxy + summary banner from the actual bind).
  - **TOCTOU caveat**: small window between discovery and bind, retry-the-sequence is the right mitigation, sentinel sockets are not.

  *Symptom prevented*: launcher silently uses the wrong port for one service while peers target the default, producing CORS / proxy / OIDC redirect-URI failures that look like config bugs rather than port mismatches.

- **`references/pitfalls.md` §"P17 — Foreign port owner + `strictPort` = silent 'script hang'"** — documents the 3-step failure cascade (kill silently fails against foreign owner → Vite/Next strictPort hard-fails → parent `wait` keeps tracking the surviving backend child = visually identical to a hang). Includes the diagnostic recipe: `bash -x` the launcher and look for the gap between the last "service started" log and the `wait` call; cross-check with `ss -tlnp` to find services whose bound PID isn't a child of the launcher.

  *Symptom prevented*: user reports "dev.sh trava no frontend" with no obvious error; 30 minutes of debugging chases the wrong layer (Docker? Vite config? `set -e`?) before the cascade becomes visible.

### Changed

- **`SKILL.md` §"Design Principle 6"** evolved from a single-strategy "Port reclaim has a fallback chain" to a two-strategy "Two port strategies, picked by ownership". Discovery (find-next-free) is the right default for service ports a multi-process launcher coordinates; reclaim (kill-and-reclaim) stays for orphans the script demonstrably owns. Includes the rubric, the failure mode that conflating them produces (P17), and pointers to both bash-patterns sections.
- **`SKILL.md` metadata version 0.3.1 → 0.4.0**, **`.claude-plugin/plugin.json` 0.3.1 → 0.4.0**, **marketplace.json** description expanded with "two-strategy port handling", **keywords** gained `port-discovery`, `find-available-port`, `strict-port`, `peer-coordination`. Triggers list gained `find available port`, `port discovery`, `script hangs`, `strictPort`.

### Not changed / out of scope

- `assets/dev.sh.tmpl` and `assets/dev.ps1.tmpl` — not modified. Discovery isn't universally desirable (some projects genuinely want fixed ports for deterministic dev URLs), and threading both strategies into the template forces every consumer to either ship dead code or commit to one approach. Same policy as v0.3.0's monorepo-regex gotcha: the pattern lives in `references/` with copy-pasteable snippets, the template stays lean. The skill picks the strategy during Phase 1 detection based on detected peer-dependencies (does the frontend proxy to a backend? does the backend's CORS allowlist a specific frontend URL? — those are signals discovery is needed; otherwise reclaim is fine).
- `references/powershell-patterns.md` — PowerShell equivalents (`Get-NetTCPConnection -State Listen` for probing, `Get-Process` for cleanup) will be added in a follow-up if/when a Windows session surfaces a parallel scenario. The bash-side pattern is independently useful and the lesson didn't come from a PowerShell context.
- `references/tls-https-recipe.md` — TLS plumbing unchanged; the new patterns live in the process-management layer.
- `references/idempotency-and-state.md` — idempotency story unchanged; port discovery is orthogonal to state-file drift.

### Verification

- Proven against the LouvorFlow `dev.sh`: with port 8080 occupied by `python3 -m http.server 8080`, the prior `kill_stale_ports` silently failed and `vite` with `strictPort: true` hard-failed while the parent shell stayed in `wait` on the surviving backend — the reported "trava" symptom. After applying discovery + peer-coordination (`PORT=$FRONTEND_PORT` + `API_PORT=$BACKEND_PORT` injected per subshell, plus `APP_WEB_URL=http://localhost:$FRONTEND_PORT` so backend CORS follows), the launcher transparently shifted the frontend to 8081, propagated 8081 to the backend CORS, kept the Vite proxy targeting the correct backend port, and started both services cleanly with the summary banner showing the actual bound ports.

## 0.3.0 — 2026-05-04

Lessons from a session against the JRC `validade_bateria_estoque` LAN-HTTPS stack — three places where the v0.2.0 reference still left enough rope to hang yourself, including one regression that hit four times across separate sessions before the root cause clicked.

### Added

- **`references/bash-patterns.md` §"Gotcha — monorepo path constraints flip the regex ordering"** — when adding monorepo path scoping to the `kill_known_dev_servers` regex, the intuitive `tsx.*packages/backend.*server\.ts` *silently never matches* because the actual cmdline is `node /repo/packages/backend/node_modules/.bin/tsx watch ... src/server.ts` — `packages/backend` appears **before** `tsx`. Recommended pattern is `packages/backend.*server\.ts` (don't anchor to `tsx`). Includes the cmdline reality-check tip: spawn a test process, run the regex against `ps -ef | grep`, only trust the kill function if it actually finds the test PID.

  *Symptom prevented*: 8 zombie `tsx watch` trees from previous sessions surviving for 5 days because every run's `kill_known_dev_servers` was a silent no-op. Each `--reset-zitadel` produced a 401-storm; debugging blamed the wrong layer (mkcert / .env / bootstrap) for 4 sessions before the regex ordering became visible.

- **`references/bash-patterns.md` §"Companion gotcha — `tsx watch` doesn't watch `.env`"** — when the launcher patches `.env` on every boot (the canonical fix for stale-config drift), `tsx watch` keeps the old values in memory because it only watches `src/**`. Documented two fixes: `tsx watch --include=.env` (one-line `package.json` edit, preferred) and "kill the runner before re-spawning" (belt-and-suspenders). Analogous flags listed for `nodemon`, `dotnet watch`, `cargo-watch`.

  *Symptom prevented*: launcher patches `.env` correctly with the new `AUTH_AUDIENCE`, but the running backend keeps the old one in heap → every JWT 401s with no clear error from the launcher's perspective.

- **`references/idempotency-and-state.md` §"Boot-time sanity check inside the app"** — defensive pattern complementing the disk-level idempotency (state file + `.env` patching). The app reads the launcher's source-of-truth file at boot and warns LOUD on divergence. Warn-only, not fail-fast, because in production the file does not exist and the check should be silent. Generic table maps the pattern to non-IdP launcher files (`.dev.script.state` `EXTERNAL_FULL`, `infra/db/connection.json`, `infra/queue/connection.json`) — not Zitadel-specific.

  *Symptom prevented*: the third layer of the 401-storm defense. Disk in sync (state file) + processes in sync (`kill_known_dev_servers`) + heap in sync (this sanity check). Reduces "I edited the .env, why is it still broken?" diagnosis from 30 minutes to 5 seconds.

- **`references/pitfalls.md` §"P16 — Long-lived dev sessions accumulate zombie watchers (silent)"** — index entry that ties the three patterns above together as a 3-layer defense. Includes the smoking-gun detector: `pgrep -af '<runner-pattern>' | wc -l` returning > 1 means the trap is active.

  *Symptom prevented*: same recurrence (4× across 5 days) being misdiagnosed as a different bug each time. Now first-time hits should pattern-match this entry within a session.

### Changed

- **`SKILL.md` metadata version 0.2.0 → 0.3.0**, **`.claude-plugin/plugin.json` 0.2.0 → 0.3.0**, **marketplace.json** description and keywords expanded with `sanity-check`, `runtime-drift`, `tsx-watch`. Triggers list gained `401 storm depois de --reset`, `tsx watch zumbi`, `env stale runtime`, `runtime config drift`, `bootstrap.json sanity check`, `kill_known_dev_servers regex monorepo`, `tsx watch não recarrega .env`.

### Not changed / out of scope

- `assets/dev.sh.tmpl` — both gotchas (regex ordering, `.env` watch) are documented in `references/` with copy-pasteable snippets, not embedded in the template. Threading either into the template would force every consumer to either (a) maintain a stack-specific regex even when single-package projects work fine with `tsx.*src/server\.ts`, or (b) commit to `--include=.env` without considering the cost (binary file detection differs across watchers). Keep the template lean; references guide the case-by-case addition.
- `references/powershell-patterns.md` — both gotchas are Linux/Unix runner-specific. Windows `Get-Process` already finds dev runners by `ProcessName`/`Path` without the cmdline-ordering problem; `dotnet watch` on Windows respects `--watch` flags consistently. No change needed.
- `references/tls-https-recipe.md` — TLS termination unchanged; the new gotchas live in process-management and idempotency layers.

### Verification

- The 3-layer fix proven on the JRC stack: 53× `/oauth/v2/authorize` requests in a 15-second post-login window collapsed to 1× after applying (1) regex fix in `kill_known_dev_servers`, (2) launcher-side `kill` before re-spawn, (3) `auth-sanity` check at backend boot. Login storm pattern eliminated; subsequent `--reset-zitadel` runs come up clean.

## 0.2.0 — 2026-04-30

Lessons from a smoke session against the JRC `validade_bateria_estoque` LAN-HTTPS stack — three places where the v0.1.0 reference drifted from real-world behaviour.

### Added

- **`references/bash-patterns.md` §"Fourth fallback: `pgrep` by command line"** — the existing three-method `kill_port` (`fuser → lsof → ss`) returns empty on hardened kernels (recent Ubuntu, container hosts with `hidepid=2`, sandboxed sessions across PID namespaces), so `kill_port` becomes a silent no-op and zombie backends survive across runs. Added `kill_known_dev_servers()` as a fourth fallback that matches by command line via `pgrep -af`, plus a per-stack pattern table (Express/tsx, NestJS, Vite, dotnet, cargo) and a warning against bare `pgrep -af node`.

  *Symptom prevented*: 4 zombie `tsx watch` trees survived a Ctrl+C on the JRC stack because none of `ss`, `lsof`, or `fuser` could see the PIDs from the same UID across sessions. The next `dev.sh` run failed with `EADDRINUSE` on `:3000`.

- **`references/tls-https-recipe.md` §"Step 5 — Testing the LAN-HTTPS stack with Playwright"** — Playwright suites against `https://<lan-ip>.sslip.io:5443` need two moves: `PLAYWRIGHT_BASE_URL` env override + `ignoreHTTPSErrors` in **both** `use:` and the `globalSetup` browser context (the global setup creates its own context that doesn't inherit `use.ignoreHTTPSErrors`). Documents the failure mode (`net::ERR_CERT_AUTHORITY_INVALID` from the global setup, killing all specs before any body runs) and explains why `NODE_TLS_REJECT_UNAUTHORIZED=0` doesn't help. Plus a side note on logout test ordering invalidating shared `storageState`.

  *Symptom prevented*: 10 minutes of debugging when the global setup fails on the first `page.goto(/login)` against the mkcert-signed Caddy proxy, with an error pointing at the wrong file.

### Changed

- **`references/idempotency-and-state.md` §"Skip work that's already done — carefully"** — rewrote the skip-bootstrap section. The previous version recommended skipping by `EXTERNAL_FULL` for adoption ("4s vs 35s"); this hid drift when other inputs (`OIDC_REDIRECT_URIS`, `OIDC_POST_LOGOUT_URIS`, `OIDC_SCOPES`, `LOGIN_VERSION`) changed without `EXTERNAL_FULL` changing. Now offers two explicit options: **A** always run if the bootstrap is idempotent (treats Zitadel `COMMAND-1m88i` "No changes" as no-op — preferred), or **B** hash *all* inputs into the cache key (acceptable when bootstrap genuinely costs 30s+). The state file becomes a drift detector for destructive changes, not a perf cache.

  *Symptom prevented*: changing `OIDC_POST_LOGOUT_URIS="${WEB_BASE}/"` to `"${WEB_BASE}/login,${WEB_BASE}/"` did nothing because the cache key didn't include the URI list — every logout kept failing with `error=invalid_request post_logout_redirect_uri invalid` until `--reset` (data-destructive) or hand-edit of the cache file.

- **`SKILL.md` metadata version 0.1.0 → 0.2.0**, **`.claude-plugin/plugin.json` 0.1.0 → 0.2.0**, **marketplace.json** description and keywords expanded with `pgrep`/`playwright`/`kill-port` and the new gotchas.

### Not changed / out of scope

- `assets/dev.sh.tmpl` — the new `kill_known_dev_servers` is documented in `references/bash-patterns.md` with a copy-pasteable snippet. Threading it through the template would force every consumer to maintain a stack-pattern regex even when the three-method `kill_port` works fine for them. Keep the template lean; let the references guide the case-by-case addition.
- `references/powershell-patterns.md` — the kernel hidepid issue is Linux-specific. Windows `Get-NetTCPConnection` already returns the PID for the current user without privilege escalation. No change needed.

### Verification

```bash
grep -rn "pgrep -af\|kill_known_dev_servers\|hidepid\|PLAYWRIGHT_BASE_URL\|ignoreHTTPSErrors" \
  plugins/dev-script/skills/dev-script/references/
```

Expected: ≥1 hit per term across `bash-patterns.md`, `tls-https-recipe.md`, `idempotency-and-state.md`.

## 0.1.0 — 2026-04-30

Initial release. Generates `dev.sh` (bash, Linux/macOS) and `dev.ps1` (PowerShell 5.1/7+) launchers tailored to the current project.

### What's in the box

- **`SKILL.md`** — workflow (detect → confirm → pick template → generate → document) plus seven design principles that keep the output predictable across stacks.
- **`references/stack-detection.md`** — the canonical grep-and-read recipe for compose files, monorepo workspaces, frontend dev server, backend dev process, database, IdP, bootstrap scripts, `.env` files, mkcert posture, and existing launchers.
- **`references/bash-patterns.md`** — copy-pasteable idioms: portable script-dir resolution, color logging, `set -euo pipefail`, LAN IP detection, per-component healthchecks (Postgres `pg_isready`, HTTP `/healthz`, bootstrap exit + output verification), three-method port reclaim (`fuser` → `lsof` → `ss`), `setsid` + `kill -- -PGID` cleanup, in-place `.env` patching with `|` delimiter and GNU/BSD sed branching, generated Vite wrapper config, final summary block, `wait` to keep the script alive.
- **`references/powershell-patterns.md`** — idiomatic PowerShell equivalents (not literal ports): `$ErrorActionPreference = 'Stop'` + `Set-StrictMode -Version 3.0` for `set -eu`, `Find-NetRoute` for LAN IP, `Get-NetTCPConnection` + `Stop-Process` for port reclaim, `Register-EngineEvent PowerShell.Exiting` + try/finally for cleanup, `Start-Job` / `Start-ThreadJob` for backgrounding, here-strings (`@"…"@`) instead of heredocs, `[regex]::Replace` for `.env` patching, VT-mode shim for ANSI colors on PS 5.1, plus a bash → PowerShell equivalence cheatsheet.
- **`references/tls-https-recipe.md`** — the four-piece chain that has to align: mkcert → Caddy reverse proxy → Vite/Express/Zitadel internals → backend `NODE_EXTRA_CA_CERTS`. Covers the Linux `network_mode: host` vs macOS/Windows `host.docker.internal` split, Vite 5 `allowedHosts` wrapper, Zitadel TLS triad (`EXTERNALSECURE=true` + `TLS_ENABLED=false` + `--tlsMode external`), and LAN client onboarding (download `rootCA.pem`, install via `mkcert -install`).
- **`references/idempotency-and-state.md`** — what stable vs volatile state means; re-derive `projectId`/`clientId` from `bootstrap.json` on every boot; state file with drift detection that refuses to start if Zitadel volume disagrees with current invocation; `--reset` discipline; gitignore checklist.
- **`references/pitfalls.md`** — fifteen recurring traps with symptom + cause + fix: Vite `allowedHosts`, JWKS over self-signed HTTPS, stale `AUTH_AUDIENCE` after volume reset, Zitadel `externalDomain` persistence, idempotency `400 COMMAND-1m88i "No changes"`, `--tlsMode external`, `crypto.subtle` outside secure contexts, dev rate limiter too tight, port-clear fallback chain, process-group cleanup, bootstrap-output verification, compose `network_mode: host` cross-platform, sed delimiter conflict with URLs, GNU vs BSD sed `-i`, hot-reload mid-bootstrap race.
- **`assets/dev.sh.tmpl`**, **`assets/dev.ps1.tmpl`**, **`assets/Caddyfile.tmpl`** — annotated templates with `<<PLACEHOLDER>>` markers and `<<#IF section>> … <<#END>>` blocks for section-conditional generation.

### Sources

The skill condenses lessons from two real-world JRC `dev.sh` scripts:

- `JRC-Brasil/digital_service_report_api/dev.sh` — multi-backend monorepo with SQL Server externals, used as the baseline for color/prefix patterns, healthcheck loops, and `kill_stale_ports` shape.
- `JRC-Brasil/validade_bateria_estoque/dev.sh` (created in the same session that produced this skill) — Zitadel + Caddy + mkcert HTTPS-on-LAN setup, used as the source for TLS termination, Vite 5 `allowedHosts` wrapper, `NODE_EXTRA_CA_CERTS`, bootstrap idempotency with `COMMAND-1m88i` guard, and state-file drift detection.

Future releases will add: Windows-native testing notes, Tilt comparison, devcontainer interop, and a `scripts/detect-stack.sh` utility that emits the detection summary as JSON for callers that want to drive generation programmatically.
