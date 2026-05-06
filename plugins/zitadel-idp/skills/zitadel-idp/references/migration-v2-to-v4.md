# Zitadel v2.66 → v4 — upgrade runbook (self-hosted)

This is the operational playbook for upgrading a self-hosted Zitadel instance from the **v2.66.x** line (the last release before the major-version reset) to the **v4.x** line, in a single hop. It complements `docker-compose-bootstrap.md` (which covers steady-state config) and `api-v1-to-v2-mapping.md` (which covers refactoring callers from API v1 to v2 — orthogonal to this upgrade, but usually paired).

**Tenets**:

- Treat upgrade as **stateful migration**, not deploy. Take the snapshot.
- The new image is the migrator: `setup` runs automatically on first boot of v4 and applies pending schema steps.
- **Login UI v2 is a separate Next.js container in v4** — the binary no longer ships a `/ui/v2/login` UI. Compose must change.
- Rollback exists, but it's "restore snapshot + boot old tag" — there is no in-place downgrade.

## §1. Pre-flight checklist

Run through every item before touching the running stack:

- [ ] **Postgres in place, version 14+**. Required since v3 (advisory [A10015](https://zitadel.com/docs/support/advisory/a10015) deprecated CockroachDB). If your stack still runs Cockroach, do that migration FIRST in v2.66, then upgrade — don't combine both jumps.
- [ ] **Masterkey known and persisted**. Same masterkey from v2.66 must be available to v4 — otherwise the encrypted columns can't be read. Print it once, store in a password manager / Docker secret. Reminder: in v2.66.x you may have it as `--masterkey` flag (Quirk 24 in `docker-compose-bootstrap.md`); in v4 the env var fallback works again — the flag becomes optional.
- [ ] **Backup**: `pg_dump` of the Zitadel database **and** a tarball of any host-mounted volume that holds PAT files / generated keys (`/current-dir`, `/var/zitadel/...`).
- [ ] **Note the env triad**: current `ZITADEL_EXTERNALDOMAIN`, `ZITADEL_EXTERNALPORT`, `ZITADEL_EXTERNALSECURE`, plus `TLS_ENABLED` and the `--tlsMode` flag if behind a TLS-terminating proxy (Quirk 15). These persist in the DB on first init — changing them on v4 boot triggers `ExternalDomain changed` migrations.
- [ ] **Inventory of API v1 callers** in your stack (bootstrap scripts, admin tooling, custom dashboards). They will keep working in v4 — v1 is not removed — but you'll want the list when planning the v1 → v2 refactor (separate work; see `api-v1-to-v2-mapping.md`).
- [ ] **Maintenance window or quiet period**. First boot of v4 takes 30–120 s longer than steady state because the `setup` phase applies pending schema migrations. Issue resolution is also harder under load.

## §2. Upgrade path

**Direct v2.66.x → v4.x is supported when Postgres is already in use.** No v3 stop required — schema migrations from the v2 line are applied incrementally during the v4 image's `setup` phase. This is the default behavior of `start-from-init`: it runs `init` (DB schema) + `setup` (applies pending migration steps + provisions any missing FirstInstance state) + `start`.

Two architectural changes in v4 that matter for compose:

1. **Login UI v2 is a separate Next.js container** — image `ghcr.io/zitadel/zitadel-login`. The legacy bundled Login UI v1 is still served at `/ui/login/` by the API container, but the **default instance flag `loginV2.required` is `true`** since v3, so all `signinRedirect` calls land on `/ui/v2/login` — which 404s if you didn't add the new container. You have two paths:
   - **Path A (recommended for greenfield v4)**: deploy `zitadel-login` and route `/ui/v2/login` to it.
   - **Path B (least change for an upgrade)**: keep using v1 by setting `loginV2.required: false` via `PUT /v2/features/instance`. Same as Quirk 9 / `troubleshooting.md §"Hosted UI returns 404"`. Either is fine — pick once and don't oscillate.
2. **`ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH`** writes a PAT for the IAM_LOGIN_CLIENT service account. This service account is what the `zitadel-login` container uses to talk back to the API — set it up before adding the new container, or login UI v2 will fail to boot.

If you've been pinning `ghcr.io/zitadel/zitadel:v2.66.10` (the typical case), bump to a specific v4.x patch — e.g., `ghcr.io/zitadel/zitadel:v4.15.0`. Avoid `:latest` in production: it floats and re-runs schema migrations on every pull.

## §3. Step-by-step

### 3.1. Snapshot

```bash
# Database
docker exec -t <postgres-ctr> pg_dump -U zitadel zitadel > zitadel-pre-v4.sql

# Stop the stack so file-system snapshots are consistent
docker compose down

# Volume tarball (adjust the volume name to match your compose project)
tar czf zitadel-volumes.tgz \
  /var/lib/docker/volumes/<stack>_zitadel-data \
  /var/lib/docker/volumes/<stack>_postgres-data
```

Store both files **off the host**. Restoring on the same host after a corrupt-disk scenario is the wrong test of your backup.

### 3.2. Update compose

Two edits in `docker-compose.yml` (or whichever file holds the Zitadel stack — see `docker-compose-bootstrap.md §8` for a full v4 example):

```yaml
services:
  zitadel:
    image: ghcr.io/zitadel/zitadel:v4.15.0   # was: v2.66.10
    command:
      - start-from-init
      # In v4 the env-var fallback works — drop --masterkey if you only had it
      # for the v2.66 quirk (Quirk 24). It's harmless to leave but redundant.
      - --tlsMode
      - external                               # keep if behind a TLS proxy

  zitadel-login:                               # NEW in v4 if you go Path A
    image: ghcr.io/zitadel/zitadel-login:v4.15.0
    environment:
      ZITADEL_API_URL: https://${EXTERNALDOMAIN}
      ZITADEL_SERVICE_USER_TOKEN_FILE: /current-dir/login-client.pat
    volumes:
      - ./zitadel/local:/current-dir:ro
    depends_on:
      zitadel:
        condition: service_healthy
```

If your reverse proxy is the front door, add a location block routing `/ui/v2/login` to the new container — see §3.3.

### 3.3. Reverse-proxy routing (Path A only)

`/ui/v2/login` (Prefix) → `zitadel-login:3000`. **Everything else** → `zitadel:8080` (including `/.well-known/openid-configuration`, `/oauth/v2/*`, `/v2/...`, `/management/v1/...`, `/admin/v1/...`).

NGINX example:

```nginx
location /ui/v2/login {
  proxy_pass http://zitadel-login:3000;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}

location / {
  proxy_pass http://zitadel:8080;
  proxy_set_header Host $host;          # see Quirk 3 — Zitadel validates Host
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}
```

Caddy:

```caddy
${EXTERNALDOMAIN}:443 {
  tls /certs/cert.pem /certs/key.pem
  handle_path /ui/v2/login* {
    reverse_proxy zitadel-login:3000
  }
  reverse_proxy zitadel:8080
}
```

### 3.4. Boot v4

```bash
docker compose up -d zitadel zitadel-login
docker logs -f <zitadel-ctr>
```

Watch for `setup completed` (or equivalent — wording shifts release to release). Don't expose the container externally before this line appears; `setup` is single-shot and a half-applied migration is the worst-case state. If the log goes silent without `setup completed`, see §5 (Validation matrix).

### 3.5. Smoke test

```bash
# 1. OIDC discovery resolves and the issuer matches your external domain
curl -sf https://${EXTERNALDOMAIN}/.well-known/openid-configuration | jq .issuer

# 2. JWKS endpoint serves keys
curl -sf https://${EXTERNALDOMAIN}/oauth/v2/keys | jq '.keys | length'

# 3. (Path A) Login UI v2 renders
curl -sI https://${EXTERNALDOMAIN}/ui/v2/login | head -1
# expect: HTTP/2 200 (or 307 redirect to a sub-path that returns 200)

# 4. (Path B) Disable v2 flag if you're sticking with Login UI v1
PAT=$(cat zitadel/local/admin.pat)
curl -sS -X PUT https://${EXTERNALDOMAIN}/v2/features/instance \
  -H "Authorization: Bearer $PAT" -H 'Content-Type: application/json' \
  -d '{"loginV2":{"required":false}}'
```

### 3.6. Re-run bootstrap

The bootstrap script that worked against v2.66 should work unchanged against v4 — Management API v1 is preserved. Re-run it; it's idempotent, so this should be a no-op for existing org/project/app/roles. Confirm output:

```text
[org] reusing "JRC" id=370...
[project] reusing "ERP-JRC" id=...
[role] reuse battery.operator
[role] reuse battery.admin
[app] reuse "battery-lifecycle-web" id=...
```

If you see `[app] created` instead of `[app] reuse`, something deleted the app during migration — investigate before proceeding (likely a corrupted events table; restore from snapshot). If you see `[label-policy] sem mudanças (no-op)` (or your equivalent), the branding survived the upgrade — Quirk 19/20 territory.

### 3.6.1. ⚠️ Login UI v2 deploy in v4.15.0 — auto-provisioning is broken

If you're picking Path A (deploy `zitadel-login` container as the default authn UI), be aware of the bug captured in Quirk 28 before designing your compose:

- The "happy path" envs `ZITADEL_FIRSTINSTANCE_ORG_LOGINCLIENT_MACHINE_USERNAME` + `_NAME` + `..._PAT_EXPIRATIONDATE` would tell FirstInstance to provision the `IAM_LOGIN_CLIENT` service user and write its PAT to the path you set with `ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH`. **In v4.15.0 those envs trigger zitadel/zitadel#8910 / #9293** — the `03_default_instance` migration tries to reserve the instance domain twice and fails with `unique_constraints_pkey` duplicate. The container enters a restart loop that doesn't recover. PR #10518 is the upstream fix; verify against your patch before assuming it works.
- Setting only `LOGINCLIENTPATPATH` without the `MACHINE_*`/`PAT_EXPIRATIONDATE` envs is a no-op — no service user gets created, the PAT is never written, and `zitadel-login` loops forever on `Awaiting file and reading token`. `/ui/v2/login` returns 404 indefinitely.

If your patch has the fix, great — use the full env set. If not, **default to Path B** (`PUT /v2/features/instance {"loginV2":{"required":false}}`) for this upgrade and revisit Login UI v2 promotion once upstream stabilizes. Login UI v1 with branding via label policy (Quirks 19-22) is a fully supported configuration in v4.

The `zitadel-login` container can be deployed regardless of which path you take — under Path B it stays idle (looping benignly waiting for a PAT) and is a single config flip away from being usable when you're ready. There's no harm in keeping it deployed as long as the routing you add to `/ui/v2/login` doesn't accidentally become the default flow before the PAT exists.

→ `troubleshooting.md` entries `"zitadel-login: Awaiting file"` and `"03_default_instance unique_constraints_pkey"`.

### 3.7. App-level smoke

- Backend: re-derive `AUTH_AUDIENCE` (= projectId) and `OIDC_ISSUER` from the bootstrap output (`api-cheatsheet.md §"Re-reading bootstrap output"`). Restart so `createRemoteJWKSet` re-fetches against the new instance keys (Quirk 12 / 13).
- SPA: clear browser session storage. Log in fresh — silent renew should fire transparently.
- Tail backend logs for 401 storms. If you see them, jump to `troubleshooting.md §"Post-upgrade errors"`.

## §4. Validation matrix

| Symptom | Likely cause | Fix |
|---|---|---|
| `404` on `/ui/v2/login` | Path A: reverse proxy not routing to `zitadel-login` container | Add the location block from §3.3 |
| `404` on `/ui/v2/login` | Path B: `loginV2.required` still `true` | `PUT /v2/features/instance {"loginV2":{"required":false}}` (§3.5) |
| `setup` phase hangs > 5 min | Postgres connection limit or disk full | `docker logs zitadel \| grep "migration X applied"` — if no progress, check Postgres `pg_stat_activity` and disk |
| 401 storm post-upgrade with apparently-valid JWT | JWKS cache stale on backend side (instance signing keys regenerated) | Restart backend (clears `createRemoteJWKSet`); see Quirk 12 / 13 |
| `aud` mismatch on every JWT | `AUTH_AUDIENCE` cached from v2.66 doesn't match v4-regenerated `projectId` | Re-derive from `bootstrap.json` (`api-cheatsheet.md §"Re-reading bootstrap output"`) |
| Old branding lost | LabelPolicy schema unchanged but asset URL path may have shifted | Re-run Quirk 21 fix (`branding.md`) |
| `permission denied` on `/current-dir/login-client.pat` (Path A) | New PAT not provisioned because `ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH` env wasn't set before first boot | Stop, set the env, `docker compose down -v` (DESTRUCTIVE — use only if you have the snapshot from §3.1), boot again |
| `zitadel-login` container loops on `Awaiting file and reading token` (Path A) | Quirk 28: only `LOGINCLIENTPATPATH` set; no service user created, PAT never written | Adopt Path B (`loginV2.required=false`) for this upgrade; treat Login UI v2 promotion as a separate task |
| `03_default_instance` migration fails with `unique_constraints_pkey` / `Errors.Instance.Domain.AlreadyExists` | Quirk 28: `LOGINCLIENT_MACHINE_*` envs added on top of the Human admin defaults trigger zitadel/zitadel#8910 / #9293 | Remove the `LOGINCLIENT_MACHINE_*` envs, `down -v`, retry; track PR #10518 |
| Bootstrap fails with `Errors.<resource>.AlreadyExisting` on second run | Idempotency matcher only checks `'AlreadyExists'` (no `ing`) | Extend matcher to cover `AlreadyExisting` too — see `api-v1-to-v2-mapping.md §5` |
| `findApp` / `findProject` returns null even though resource exists | Wrong response field name — code reads `result[]` but v2 uses `applications[]` / `projects[]` | See `api-v1-to-v2-mapping.md §2.1` for the per-service response field table |
| `400 invalid_argument: CreateApplicationRequest.ApplicationType: value is required` | OIDC config sent under `oidc` instead of `oidcConfiguration`, OR wrapped in `applicationType: { oidc: ... }` | Top-level `oidcConfiguration: {...}` (no wrapper). Inner field is `applicationType` (not `appType`); `developmentMode` (not `devMode`). See `api-v1-to-v2-mapping.md §"CreateApplication"` |
| `CreateAuthorizationRequest.OrganizationId: value length must be between 1 and 200 runes` | Forgot the body field `organizationId` (REQUIRED in v4 — proto validate.rules) | Add `organizationId: orgIdThatOwnsProject` to the body. Update/Delete take field `id`, not `authorizationId`. |
| `panic: No master key provided` after v4 boot | Masterkey didn't reach the new container | Re-check env / secret. In v4 the env-var path is reliable (Quirk 24 was v2.66-specific) — if it still panics, file a bug. |
| Bootstrap script fails with `INVALID_ARGUMENT: missing organization_id` | You partially refactored a call to v2 Connect protocol but kept the v1 header convention (Quirk 27) | Move `orgId` from `x-zitadel-orgid` header to `organizationId` in body. See `api-v1-to-v2-mapping.md §"Contextual info"`. |

## §5. Rollback

Rollback is restore-from-snapshot. There is no in-place downgrade.

```bash
docker compose down -v          # DESTRUCTIVE — wipes the broken v4 state
# Restore snapshot
psql -U zitadel -d zitadel < zitadel-pre-v4.sql
tar xzf zitadel-volumes.tgz -C /
# Pin compose back to v2.66.10
sed -i 's|zitadel:v4.15.0|zitadel:v2.66.10|' docker-compose.yml
# Remove the zitadel-login service if you added it
# Boot
docker compose up -d zitadel
# Re-run bootstrap (idempotent)
node packages/idp/scripts/bootstrap-zitadel.ts
```

After a rollback, **do not** re-attempt the upgrade until the failure root cause is understood. Repeating the same upgrade with the same broken state produces the same failure.

## §6. After the upgrade

Things that become available in v4 but didn't exist in v2.66:

- **Login UI v2** as a polished default. If you went Path B, plan a follow-up to migrate. The upgrade itself doesn't pressure you — Login UI v1 keeps working at `/ui/login/` indefinitely.
- **Connect protocol** for v2 services — `POST /zitadel.<svc>.v2.<Method>`. Same auth, JSON body. Use it for new bootstrap code (`api-v1-to-v2-mapping.md`).
- **`/v2/users/human` REST endpoint** (consolidated user creation), **AuthorizationService** (replaces the `_search` round-trip for grants), **ApplicationService** (single `CreateApplication` covers OIDC/SAML/API).

None of these are required — your v1-shaped bootstrap continues to work. Refactor when there's a reason (multi-app, multi-system, or a v1 endpoint you actually need that's missing or awkward).

## §7. Where to go next

- v1 → v2 endpoint refactor: `references/api-v1-to-v2-mapping.md`.
- Compose v4 with login-container + nginx: `references/docker-compose-bootstrap.md §8`.
- Post-upgrade error patterns (the 4 symptoms above expanded with diagnostics): `references/troubleshooting.md §"Post-upgrade errors (v2.66 → v4)"`.
- Branding survives upgrades but the asset path can drift: `references/branding.md` (Quirks 19–22).
