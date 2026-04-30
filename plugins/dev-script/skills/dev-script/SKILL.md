---
name: dev-script
metadata:
  version: 0.1.0
description: >
  Generates a single-command development launcher (`dev.sh` for Linux/macOS,
  `dev.ps1` for Windows) tailored to the current project. Detects the stack
  (Docker Compose services, monorepo workspaces, frontend dev server, backend
  process, IdP, database, bootstrap scripts, mkcert availability) and emits a
  script that brings up everything with colored per-service prefixes,
  per-component healthchecks, robust port reclaim, trap-based cleanup,
  idempotent re-runs, and — when the stack involves an OIDC IdP or LAN sharing
  — HTTPS termination via mkcert + Caddy so PKCE works outside `localhost`.
  Use this skill PROACTIVELY whenever the user asks for: "dev.sh", "dev.ps1",
  "dev script", "single command to bring everything up", "compose this project
  for local dev", "share my dev environment on the LAN", "reproducible local
  start", "boot the whole stack", "let teammates test from their machine",
  or when the user is staring at a project that needs `docker compose up` +
  `npm run dev` in two or more terminals and wants it down to one. Trigger
  even when the user doesn't say "dev.sh" but is clearly asking for a single
  entrypoint that orchestrates Postgres/SQL Server, an IdP (Zitadel/Keycloak),
  one or more APIs, and a frontend dev server. Triggers: "dev.sh", "dev.ps1",
  "dev script", "subir tudo", "levantar a infra dev", "compartilhar dev na
  LAN", "monta o ambiente local", "script que sobe tudo", "boot the stack",
  "local dev orchestrator", "dev launcher", "powershell dev script".
---

# dev.script — Local Dev Stack Launcher Generator

This skill produces a **single executable** (`dev.sh` for Linux/macOS, `dev.ps1` for Windows) that brings up the entire local development stack of the current project — containers, databases, APIs, frontend, IdP, and any bootstrap step — in one command. The generated script is **idempotent**, fails loudly with actionable messages, and cleans up after itself on Ctrl+C.

It is not a generic init: each script is **shaped by what was detected in the project**. Sections that don't apply (e.g., TLS termination when there's no IdP) are not emitted, so the result stays minimal and readable.

## When to invoke this skill

Use it whenever the user wants any of these outcomes — even if they don't say "dev.sh":

- "Bring up the whole stack with one command"
- "Make this work for new contributors / teammates"
- "Let someone on my LAN hit the running app"
- "Replace this 4-step `docker compose up` + `cd ... && npm run dev` ritual"
- "Add a `dev.ps1` for the Windows folks on the team"
- "We need an idempotent local boot — fresh clone should just work"

If the project already has a `dev.sh` / `dev.ps1`, default to **improving** it (read it first, propose a diff) rather than overwriting blindly. Confirm with the user before replacing existing infrastructure.

## Workflow

The skill works in five short phases. Don't skip phases — each one feeds the next.

### Phase 1 — Detect the stack (read before write)

Walk the project tree and identify, in this order:

1. **Compose files** — `docker-compose.yml`, `infra/docker/*.yml`, `infra/postgres/*.yml`, `compose.*.yml`. Note services, ports, healthcheck blocks, volumes. Compose is the source of truth for what containerized infra exists.
2. **Monorepo layout** — `package.json` `workspaces`, `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`. Identify each workspace's role from its own `package.json` (`scripts.dev`, `scripts.start`, declared deps).
3. **Frontend dev server** — Vite (`vite.config.*`), Next (`next.config.*`), Astro, SvelteKit, Nuxt. Capture the configured `port` and any `host` setting. **Read the config; do not modify it.**
4. **Backend dev process** — `tsx watch`, `nest start --watch`, `dotnet watch`, `air` (Go), `cargo watch`. Capture port from `.env`/`.env.example` (`PORT=`).
5. **Database** — Postgres (most common), SQL Server (JRC ERP/EST), MySQL, Mongo. Determine reachability path: docker container vs. external. For external (e.g. SQL Server in another datacenter), the script should ping/probe but not try to start it.
6. **IdP** — Zitadel, Keycloak, Auth0 (cloud). For self-hosted Zitadel/Keycloak, this is the strongest signal that LAN HTTPS will be needed (PKCE requires secure context).
7. **Bootstrap scripts** — `scripts/bootstrap-*.ts`, `infra/.../init/`. These run after containers are healthy. Capture them — they typically generate IDs that downstream services depend on.
8. **`.env` files** — `.env`, `.env.example`, `.env.local`, `packages/*/.env`. List every key the dev script will need to read or patch.
9. **mkcert / TLS posture** — `command -v mkcert` plus any existing `infra/certs/` folder. If mkcert is installed and the user wants LAN access, that's the recipe.
10. **Existing dev script** — read `dev.sh` / `dev.ps1` / `Makefile` / `Justfile` / `Taskfile.yml` if present. Improve, don't replace.

**Read references/stack-detection.md** for the exact patterns and grep recipes.

### Phase 2 — Confirm the plan with the user

Before writing anything, **state the plan in 5–10 bullets**:

- "I'll generate `dev.sh` (or `dev.ps1`) that does X, Y, Z."
- "Sections included: Postgres healthcheck, Zitadel + Caddy TLS, backend with `NODE_EXTRA_CA_CERTS`, Vite via `--config` wrapper, frontend bootstrap of `VITE_OIDC_CLIENT_ID` from `bootstrap.json`."
- "Sections **not** included: <thing>, because <reason>."
- "Flags: `--no-lan`, `--no-https`, `--reset`, `--down`, `--host <ip>`."
- "Files I'll create: `dev.sh`, `infra/caddy/Caddyfile`, `.gitignore` updates."
- "Files I won't touch: `vite.config.ts`, `packages/backend/src/server.ts` — all customization via env/CLI/wrapper config."

Wait for the user to confirm or redirect. **Big tip**: people often forget about a Windows or macOS teammate. Ask explicitly: "Do you also need `dev.ps1` for Windows?" — if yes, both scripts share the same logic and you'll write them in lockstep.

### Phase 3 — Pick the right templates

The skill bundles two parallel templates:

- `assets/dev.sh.tmpl` — bash, target Linux/macOS, default for most JRC projects.
- `assets/dev.ps1.tmpl` — PowerShell ≥ 5.1 / pwsh 7+, target Windows; also runs on Linux/macOS via pwsh.

Both templates are **annotated with `<<…>>` placeholders** — substitute them based on Phase 1 detection. Both are **section-conditional**: cut TLS/Caddy if the project has no IdP and the user said "no LAN sharing"; cut the bootstrap re-derivation block if there's no `bootstrap.json` source. Smaller is better.

The PowerShell template is **not** a literal port — it uses idiomatic PowerShell (`Get-NetTCPConnection`, `Stop-Process`, `Register-EngineEvent` for cleanup, `$ErrorActionPreference = 'Stop'` for `set -e` semantics). Read `references/powershell-patterns.md` for the equivalences before substituting.

### Phase 4 — Generate the script(s)

Write the script(s) to the project root, plus any sidecar files (`infra/caddy/Caddyfile`, `infra/docker/docker-compose.<idp>.override.yml.tmpl` if generated at runtime, etc.). Make `dev.sh` executable (`chmod +x`).

**Always update `.gitignore`** for runtime artifacts the script creates: state files, generated overrides, mkcert-bootstrapped `infra/certs/`, the auto-generated Vite config wrapper. Spell these out in `.gitignore` so the user doesn't accidentally commit them.

**Always include a sanity check at the top**: a `bash -n` / `pwsh -NoProfile -Command "{ . ./dev.ps1 }"` syntax check note, or run it yourself before handing back.

### Phase 5 — Document the entrypoint

After writing, summarize for the user:

- What `./dev.sh` (or `pwsh dev.ps1`) does — 4–6 lines.
- The flags and when each one matters.
- Pitfalls the script protects against (e.g., "If your LAN IP changes between runs, the Zitadel volume already encodes the old `externalDomain` — re-run with `--reset` to nuke it").
- One-line "first-run instructions" for new contributors (clone → `./dev.sh`).

If you added LAN HTTPS, also mention that LAN clients need to install the mkcert root CA (`mkcert -install` on the client, or import `rootCA.pem` manually) — without that step, every browser will show a certificate warning.

## Design principles (apply to every generated script)

These keep the output predictable and prevent the long tail of stack-specific bugs.

### 1. Don't modify the project's source-controlled config files

Do not edit `vite.config.ts`, `next.config.js`, `packages/<pkg>/src/server.ts`, etc. All customization rides on:

- **Env variables** (`PORT`, `HOST`, `NODE_EXTRA_CA_CERTS`, `AUTH_AUDIENCE`, …)
- **CLI flags** (`vite --host 0.0.0.0`, `dotnet run --urls`, …)
- **Wrapper config files** generated by the script and gitignored (e.g., `.vite.config.lan.ts` that does `mergeConfig(base, { server: { allowedHosts: true } })`)

Why: the dev script must coexist with CI, prod builds, and other contributors' workflows that consume the same config files. Mutating them is a leaking abstraction.

### 2. Be section-conditional, not feature-flag-heavy

If the detected stack has no IdP, the generated `dev.sh` should **not** contain a `--no-https` flag, mkcert plumbing, or Caddy override — just omit those sections entirely. Flags and dead code are debt; future-you reading the script should see only what runs.

### 3. Idempotent re-runs are the point

Re-running the script should converge, not diverge. Patterns from `references/idempotency-and-state.md`:

- Always re-derive volatile IDs (`projectId`, `clientId`) from the bootstrap output — never hardcode in `.env` files committed to the repo.
- Persist a state file (`.dev.script.state` or similar) capturing values that, if changed, require a destructive reset (e.g., Zitadel `externalDomain`). Compare against current invocation; abort with a clear message if reset is required, suggesting the precise flag.
- Skip the bootstrap step when state matches and the bootstrap output is already present.

### 4. Healthchecks per-component, not blanket sleeps

A `sleep 30` between `docker compose up` and the next step is a smell. Each component has its own readiness signal:

- **Postgres**: `pg_isready -U <user>` inside the container.
- **HTTP service**: `curl -fsS <base-url>/health` (or `/healthz`, or `/debug/ready` for Zitadel).
- **Bootstrap script**: exit code 0 + presence of expected output file (e.g., `bootstrap.json`).

Spinlock with a timeout (max 30–60s, then fail with the exact URL/command that wasn't responding). See `references/bash-patterns.md` and `references/powershell-patterns.md` for the canonical loops.

### 5. Cleanup must be loud and complete

`trap cleanup EXIT SIGINT SIGTERM` (bash) / `Register-EngineEvent PowerShell.Exiting` + try/finally (PS). Cleanup kills the dev servers (process group: `kill -- "-$pgid"` in bash) and **only optionally** the containers (gated behind `--down` because most users want containers persisted across re-runs).

The corollary: **never leave orphans**. If the script started 3 child processes, all 3 must die when the user hits Ctrl+C. Pid-array tracking + group-kill handles this — the alternative (`pkill -f vite`) is fragile.

### 6. Port reclaim has a fallback chain

`fuser → lsof → ss` (or `Get-NetTCPConnection` on Windows). Different distros and container setups expose port-to-pid resolution differently; one method failing should fall through to the next. Without this fallback, the script silently leaves a stale process on the port and users see "port already in use" at start.

### 7. LAN access ⇒ HTTPS

If the user wants other devices on the network to test, **the script must generate HTTPS via mkcert + a reverse proxy**. PKCE in OIDC SPAs uses `crypto.subtle`, which the browser only exposes in secure contexts; `localhost` and `127.0.0.1` are exceptions, but the LAN IP is not. Without HTTPS, clicking "Sign in" in the SPA does nothing — silently. See `references/tls-https-recipe.md` for the canonical mkcert + Caddy + Vite/Express plumbing.

## Pitfalls to encode in every script

These are not exotic edge cases — they are the bugs that bit us in JRC projects. Read `references/pitfalls.md` for the full list with symptoms; the highlights:

- **Vite ≥ 5 blocks non-localhost hosts** by default. Generate a `.vite.config.lan.ts` wrapper with `server.allowedHosts: true` and run Vite with `--config <wrapper>` — don't ask the user to edit `vite.config.ts`.
- **Node backend can't validate JWKS over self-signed HTTPS** unless `NODE_EXTRA_CA_CERTS=$(mkcert -CAROOT)/rootCA.pem` is on the process. Inject it at the script level.
- **Zitadel persists `externalDomain` on first init**. Changing IPs requires `docker compose down -v`. Detect drift via state file; refuse to start with a wrong-domain volume; require an explicit `--reset` flag.
- **`PUT /oidc_config` returns `400 COMMAND-1m88i "No changes"`** when the bootstrap re-runs with identical config. Wrap the bootstrap step in a guard that catches this and treats it as no-op.
- **Backend rate limiters are too tight for dev**: a render storm in StrictMode plus React Query refetches blows past 120 req/min easily. Temporarily set `RATE_LIMIT_PER_MINUTE=0` in dev (and document it).
- **PowerShell ANSI color output** needs `$PSStyle.OutputRendering = 'Ansi'` on PS 7.x or `Enable-VTMode` shim on 5.1. The PowerShell template handles this in its preamble.

## References — when to read what

| If you need… | Read… |
|---|---|
| The exact things to grep/read in the project | `references/stack-detection.md` |
| Bash idioms for healthchecks, port kill, trap, color logs | `references/bash-patterns.md` |
| PowerShell equivalents (idiomatic, not literal ports) | `references/powershell-patterns.md` |
| The full mkcert + Caddy + Vite + backend wiring | `references/tls-https-recipe.md` |
| State file format, drift detection, re-run discipline | `references/idempotency-and-state.md` |
| The recurring traps that bit JRC projects | `references/pitfalls.md` |

## Templates — `assets/`

- `assets/dev.sh.tmpl` — bash template with `<<PLACEHOLDER>>` markers + section comments showing what to keep/cut by stack.
- `assets/dev.ps1.tmpl` — PowerShell counterpart with idiomatic equivalents.
- `assets/Caddyfile.tmpl` — minimal reverse-proxy with TLS termination, three-port pattern (web/api/idp).

Substitute placeholders by detection results from Phase 1; cut entire `<<#IF …>> … <<#END>>` blocks for absent components. The templates are **starting points**, not final output — read them, adapt them, omit what doesn't apply.

## Out of scope

- **Production orchestration** — this is dev only. Use Tilt, Skaffold, k8s manifests, or Compose profiles for staging/prod.
- **Devcontainers / VS Code remote** — different audience; skill could be added later but not bundled here.
- **CI pipelines** — `dev.sh` is for human-driven local dev. CI uses the same compose files but with different invocation.
- **Tunneling (ngrok / Cloudflare Tunnel)** — orthogonal to this skill. If the user wants public access (vs LAN), point them at `cloudflared` separately.

## Closing the loop

After generating the script, ask the user to **run it once** in their environment and report any rough edges. The first real run is where stack-detection misses surface (a port already in use, an env var the user has locally that the script overwrites, a bootstrap script that needs a flag the skill didn't infer). Iterate based on that feedback before declaring done.
