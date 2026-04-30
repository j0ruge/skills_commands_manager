# Stack detection — what to grep, what to read

The quality of the generated `dev.sh`/`dev.ps1` depends on what you find in the project before writing. This file lists the canonical signals and where to find them. **Read; don't run anything yet.**

## Order of inspection (from coarse to fine)

### 1. Top-level layout

```bash
ls -la <project-root>
cat <project-root>/README.md | head -80         # human description of the stack
test -f .gitignore && head -50 .gitignore       # tells you what's runtime-only
```

Look for: monorepo signals (`packages/`, `apps/`, `services/`), an existing dev launcher (`dev.sh`, `dev.ps1`, `Makefile`, `Justfile`, `Taskfile.yml`), `infra/` or `deploy/` directories.

### 2. Compose files

```bash
find . -maxdepth 4 -name "docker-compose*.yml" -not -path "*/node_modules/*"
find . -maxdepth 4 -name "compose.*.yml" -not -path "*/node_modules/*"
```

For each compose file: list `services`, their `image`, exposed `ports`, `healthcheck` blocks, declared `volumes`. The compose file is the source of truth for containerized infra. Note services that are **profile-gated** (`profiles: ["bootstrap"]`) — those don't start by default and the dev script may need `--profile`.

### 3. Monorepo workspaces

```bash
jq -r '.workspaces // empty' package.json 2>/dev/null
test -f pnpm-workspace.yaml && cat pnpm-workspace.yaml
test -f turbo.json && jq '.pipeline | keys' turbo.json
test -f nx.json && jq '.tasksRunnerOptions' nx.json
```

For each workspace, read its `package.json`:

```bash
for ws in packages/*; do
  test -f "$ws/package.json" || continue
  echo "== $ws =="
  jq '.name, .scripts.dev, .scripts.start, .dependencies' "$ws/package.json"
done
```

Identify the **purpose** of each workspace: backend (has `express`/`@nestjs/core`/`fastify`), frontend (has `vite`/`next`), library (no `dev` script), tooling (e.g., a bootstrap-only package).

### 4. Frontend dev server

```bash
find . -maxdepth 5 -name "vite.config.*" -not -path "*/node_modules/*"
find . -maxdepth 5 -name "next.config.*" -not -path "*/node_modules/*"
find . -maxdepth 5 -name "astro.config.*" -not -path "*/node_modules/*"
find . -maxdepth 5 -name "svelte.config.*" -not -path "*/node_modules/*"
```

Read the file. Capture: `server.port`, `server.host`, `server.https`. Also check the workspace's `package.json` `scripts.dev` for explicit `--port`/`--host` flags. **Don't modify the config file.**

### 5. Backend dev process

For each backend workspace:

- `scripts.dev` in `package.json` (e.g., `tsx watch --env-file=.env src/server.ts`).
- `.env` / `.env.example`: capture `PORT`, `HOST`, `DATABASE_URL`, `AUTH_*`, `CORS_*`.
- For .NET: `dotnet watch run` with `Properties/launchSettings.json` exposing the URL.
- For Go: `air` config + `cmd/.../main.go`.
- For Rust: `cargo watch -x run` + `Cargo.toml`.

### 6. Database

Look in compose first (`postgres`, `mysql`, `mariadb`, `mongo`, `mssql/server`). For external DBs (the JRC pattern with SQL Server hosted elsewhere): the backend `.env`'s `DATABASE_URL` will point to a non-local host. The dev script can `ping`/`tcping` to check reachability without trying to start anything.

```bash
grep -hE '^DATABASE_URL=' packages/*/.env*
```

### 7. IdP

Strongest signal: a compose service named `zitadel`/`keycloak` or a `packages/idp/`, `infra/idp/`, `auth/` directory. Secondary: `react-oidc-context` / `oidc-client-ts` / `@auth0/auth0-spa-js` in the frontend's `package.json`.

If self-hosted IdP **and** the user wants LAN access, the script will need:

- TLS termination via mkcert + Caddy (or NGINX/Traefik).
- `NODE_EXTRA_CA_CERTS` injected into the backend.
- `--tlsMode external` (Zitadel) or equivalent for whichever IdP.
- A bootstrap step (Zitadel: see the consumer's `bootstrap-zitadel.ts`).

### 8. Bootstrap scripts

```bash
find . -maxdepth 5 -path "*/scripts/bootstrap*" -not -path "*/node_modules/*"
find . -maxdepth 5 -name "bootstrap-*.ts" -not -path "*/node_modules/*"
find . -maxdepth 5 -path "*/init/*" -not -path "*/node_modules/*"
```

Read each — capture: required env vars, output file (e.g., `bootstrap.json`), output IDs the dev script will need to inject downstream. The bootstrap output is **volatile**: it changes every time its source (e.g., a Zitadel volume) is reset. The dev script must re-derive from this file on every boot — not hardcode.

### 9. `.env` files

```bash
find . -maxdepth 4 -name ".env*" -not -path "*/node_modules/*" | xargs -I{} sh -c 'echo "=== {} ==="; cat "{}"'
```

For each `.env.example`: list every key. The dev script's job is to materialize a working `.env` (or `.env.local`) that matches the runtime invocation — not to enumerate every env you might want, but to **patch the keys that the script's choices imply** (e.g., `AUTH_ISSUER` becomes `https://...:8443` when TLS is on).

### 10. mkcert / TLS posture

```bash
command -v mkcert
mkcert -CAROOT 2>/dev/null
test -d infra/certs && ls infra/certs/
```

Whether mkcert is installed determines whether the script can self-bootstrap TLS. If absent, the script either (a) installs it via the OS package manager — risky, ask first — or (b) falls back to `--no-https` and warns that LAN access from non-localhost will fail PKCE.

### 11. Existing dev launcher

```bash
test -f dev.sh && cat dev.sh | head -100
test -f dev.ps1 && cat dev.ps1 | head -100
test -f Makefile && grep -E '^[a-zA-Z_-]+:' Makefile
test -f Justfile && cat Justfile
```

If any of these exists, the user's intent is probably "improve" or "port to PowerShell", not "replace". Read first; propose a diff; confirm before overwriting.

## Output of detection — a quick summary

After running through the list, produce a 10–15 line summary for the user:

```text
Stack detected:
  - Postgres 16 (compose: docker-compose.yml :5432)
  - Zitadel v4 (compose: infra/docker/docker-compose.zitadel.yml :8080)
  - Backend: packages/backend, tsx watch :3000, depends on Postgres + Zitadel
  - Frontend: Vite 5 :5173, OIDC PKCE via oidc-client-ts
  - Bootstrap: packages/idp/scripts/bootstrap-zitadel.ts, writes bootstrap.json
  - Existing launcher: none
  - mkcert: installed (CAROOT: ~/.local/share/mkcert)

Implications:
  - LAN access is possible via mkcert + Caddy reverse proxy (HTTPS-on-LAN)
  - Backend needs NODE_EXTRA_CA_CERTS for JWKS validation
  - Bootstrap output (bootstrap.json) must drive AUTH_AUDIENCE + VITE_OIDC_CLIENT_ID

Proposed dev.sh sections: <list>
```

The user reads this and either confirms or redirects. **Don't write the script before this confirmation step.**
