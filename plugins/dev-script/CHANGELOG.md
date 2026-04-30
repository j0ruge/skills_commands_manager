# Changelog — `dev-script`

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
