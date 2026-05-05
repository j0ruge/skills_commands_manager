# Zitadel Management API — Cheatsheet (v4)

This is a working reference for the REST endpoints we actually use in a typical IdP integration: org/project/role/app provisioning, user management, and grant lifecycle. Each section gives the exact path, method, body shape, and the gotcha that bit us when we first wrote it.

All examples assume:

- `ZITADEL_API_URL=http://127.0.0.1.sslip.io:8080` (use the external domain literally — see `docker-compose-bootstrap.md §3`).
- A bearer token from an IAM_OWNER service account (the PAT at `/current-dir/admin.pat`, see `docker-compose-bootstrap.md §1`).
- `Content-Type: application/json` on all mutating calls.

```http
Authorization: Bearer ${PAT}
Content-Type: application/json
```

When operating on resources scoped to an org, also send:

```http
x-zitadel-orgid: <numeric orgId, NOT the domain tenantId>
```

See `tenant-org-mapping.md` for why this distinction matters.

---

## API surface — three coexisting families

Zitadel has been migrating from v1 (legacy, gRPC + REST gateway) to v2 (gRPC-Connect with native JSON). Both are live and you'll mix them. Quick guide:

| Path prefix | When to use |
|-------------|-------------|
| `/admin/v1/...` | Instance-level operations (search orgs, configure SMTP, audit log retention). |
| `/management/v1/...` | Most org-scoped operations: projects, roles, apps, users, grants. |
| `/auth/v1/...` | Authenticated user's own resources (`/users/me`, change own password). |
| `/zitadel.<service>.v2.<Service>/<Method>` | v2 Connect-protocol RPCs. Use them when v1 forces you into awkward flows (notably `OrganizationService.AddOrganization` to create an org without a human admin). Same auth headers, same JSON content type. |
| `/v2/...` | v2 REST transcoding. Some services expose this; coverage is uneven. When in doubt try the Connect path first. |

The OpenAPI / proto definitions are at <https://zitadel.com/docs/apis/introduction>.

---

## Create an organization

**Trap**: `POST /admin/v1/orgs/_setup` requires a `human` admin user in the body — it's a guided onboarding flow that creates org + admin in one step. If you already have an instance-level service account (which you do after FirstInstance setup), you do NOT want to create another admin per org. Use the v2 endpoint instead.

```http
POST /zitadel.org.v2.OrganizationService/AddOrganization
Authorization: Bearer ${PAT}
Content-Type: application/json

{ "name": "JRC" }
```

Response:

```json
{
  "details": { "sequence": "4", "changeDate": "...", "resourceOwner": "370503937624637443" },
  "organizationId": "370503937624637443"
}
```

Save `organizationId` — it's the value you'll send in `x-zitadel-orgid` for everything else.

To find an existing org by name (idempotent bootstrap):

```http
POST /admin/v1/orgs/_search
Content-Type: application/json

{ "queries": [{ "nameQuery": { "name": "JRC", "method": "TEXT_QUERY_METHOD_EQUALS" } }] }
```

---

## Create a project

```http
POST /management/v1/projects
x-zitadel-orgid: ${orgId}

{
  "name": "ERP-JRC",
  "projectRoleAssertion": true,
  "projectRoleCheck": false,
  "hasProjectCheck": false
}
```

`projectRoleAssertion: true` is what makes role claims appear in the access token (`urn:zitadel:iam:org:project:roles`). Without it, your backend's role-based authorization will receive empty role lists.

Search by name:

```http
POST /management/v1/projects/_search
x-zitadel-orgid: ${orgId}

{ "queries": [{ "nameQuery": { "name": "ERP-JRC", "method": "PROJECT_NAME_QUERY_METHOD_EQUALS" } }] }
```

Note the `method` enum is `PROJECT_NAME_QUERY_METHOD_EQUALS`, not `TEXT_QUERY_METHOD_EQUALS`. Each search endpoint defines its own enum — copy from the docs, don't guess.

---

## Create project roles

```http
POST /management/v1/projects/{projectId}/roles
x-zitadel-orgid: ${orgId}

{ "roleKey": "battery.operator", "displayName": "Operator", "group": "battery" }
```

`roleKey` is what appears in JWT claims. Pick a stable convention (we use `<context>.<role>` like `battery.operator`, `battery.admin`) and validate it in your backend with a regex — otherwise typos will yield silent role-assignment failures.

List existing roles:

```http
POST /management/v1/projects/{projectId}/roles/_search
x-zitadel-orgid: ${orgId}

{}
```

---

## Create an OIDC application

This is the most quirk-laden endpoint. Use it for SPAs (PKCE), backends (client credentials), and native apps. The fields differ per `appType`.

**SPA with PKCE** (typical Auth Code + PKCE flow):

```http
POST /management/v1/projects/{projectId}/apps/oidc
x-zitadel-orgid: ${orgId}

{
  "name": "battery-lifecycle-web",
  "redirectUris": [
    "http://localhost:5173/auth/callback",
    "http://localhost:5173/silent-renew"
  ],
  "responseTypes": ["OIDC_RESPONSE_TYPE_CODE"],
  "grantTypes": ["OIDC_GRANT_TYPE_AUTHORIZATION_CODE", "OIDC_GRANT_TYPE_REFRESH_TOKEN"],
  "appType": "OIDC_APP_TYPE_USER_AGENT",
  "authMethodType": "OIDC_AUTH_METHOD_TYPE_NONE",
  "postLogoutRedirectUris": ["http://localhost:5173/login", "http://localhost:5173/"],
  "version": "OIDC_VERSION_1_0",
  "devMode": true,
  "accessTokenType": "OIDC_TOKEN_TYPE_JWT",
  "accessTokenRoleAssertion": true,
  "idTokenRoleAssertion": true,
  "idTokenUserinfoAssertion": true,
  "clockSkew": "5s",
  "loginVersion": { "loginV1": {} }
}
```

**Quirks**:

- `clockSkew` is bounded `[0s, 5s]`. Anything larger returns `400 invalid AddOIDCAppRequest.ClockSkew`. Don't confuse this with the **client-side** `clockTolerance` you pass to `jose.jwtVerify` (that one is your backend's tolerance for clock drift while validating tokens — typically 30s).
- `accessTokenType: OIDC_TOKEN_TYPE_JWT` makes access tokens JWTs that you can verify locally with the JWKS. The default is opaque tokens that require introspection. JWT is faster (no roundtrip) but cannot be revoked mid-lifetime — pick deliberately.
- `accessTokenRoleAssertion: true` is required for role claims to ride in the access token. Without it your backend will see no roles even though they're correctly assigned.
- `redirectUris` are matched **literally** (FR-018 in our spec). `http://localhost:5173/cb` ≠ `http://localhost:5173/cb/`. Get this right or login redirects fail with cryptic errors.
- **Always include the silent-renew URI** (`/silent-renew` in `react-oidc-context`, equivalents elsewhere). Without it, every `automaticSilentRenew` request returns `400` and your SPA loops forever in "verifying session…". Adding it after the fact requires a `PUT /management/v1/projects/{p}/apps/{a}/oidc_config`. → `troubleshooting.md` for the full diagnostic.
- `loginVersion: {loginV1: {}}` pins the OIDC client to the bundled Login UI v1. **Note**: this alone does NOT defeat the instance-level `loginV2.required` flag — see `troubleshooting.md §"Hosted UI returns 404"` for the instance-feature fix that you almost certainly also need.
- **Multi-app refactor caveat (quirk 23)**: se você evolui o bootstrap para ler `applications[].redirectUris` de um YAML declarativo, **env vars `OIDC_REDIRECT_URIS` / `OIDC_POST_LOGOUT_URIS` precisam DOMINAR o YAML** quando setadas — o `dev.sh` (LAN HTTPS) injeta hosts dinâmicos por IP que nunca estão no YAML estático. Ordem correta: `env explícito > YAML não-vazio > fallback hardcoded`. Em produção env é unset, YAML domina; em dev env vence. Sintoma se invertido: `redirect_uri missing in client configuration` no callback do Zitadel. → `troubleshooting.md §"redirect_uri missing in client configuration after multi-app refactor regression"`.
- **Idempotent re-runs of the bootstrap break** if you `PUT /management/v1/projects/{p}/apps/{a}/oidc_config` with a body that matches current state. Zitadel returns `400 COMMAND-1m88i {"message":"No changes"}`. Catch it as a no-op:

  ```typescript
  try {
    await api(`/management/v1/projects/${projectId}/apps/${appId}/oidc_config`, {
      method: 'PUT',
      body: JSON.stringify(oidcConfigPayload()),
    });
  } catch (err) {
    if (err instanceof Error && err.message.includes('COMMAND-1m88i')) {
      // No changes — already in sync. Idempotent no-op.
    } else {
      throw err;
    }
  }
  ```

  Without this guard, every second run of `bootstrap-zitadel.ts` halts with a misleading 400. The same `COMMAND-1m88i` pattern shows up on other "update" endpoints (login policy, password policy, SMTP) — the same try/catch idiom applies.

**SPA tip**: pass the user's email as `extraQueryParams.login_hint` on `signinRedirect` — Zitadel uses it to pre-fill (or skip) the username step, eliminating the "type your email twice" UX. Library-specific:

```typescript
// react-oidc-context
oidc.signinRedirect({ extraQueryParams: { login_hint: email } });
```

Response includes the `appId`, `clientId`, and (for confidential apps) a `clientSecret` shown ONCE.

Search by name:

```http
POST /management/v1/projects/{projectId}/apps/_search
x-zitadel-orgid: ${orgId}

{ "queries": [{ "nameQuery": { "name": "battery-lifecycle-web", "method": "APP_NAME_QUERY_METHOD_EQUALS" } }] }
```

---

## Create a human user

```http
POST /management/v1/users/human
x-zitadel-orgid: ${orgId}

{
  "userName": "user@example.com",
  "profile": {
    "firstName": "Given",
    "lastName": "Family",
    "displayName": "Given Family",
    "preferredLanguage": "pt-BR"
  },
  "email": { "email": "user@example.com", "isEmailVerified": true },
  "initialPassword": "OptionalForBootstrap-2026!"
}
```

**Quirks**:

- The body uses `profile.firstName` / `profile.lastName`. Older Zitadel docs and SDKs sometimes show `givenName` / `familyName` — those are rejected with `400`.
- `userName` must be present and ≥1 char. Using the email as username is conventional and avoids collisions.
- `email.isEmailVerified` defaults to `false`. If false, the user will be required to verify before logging in (which means hitting the SMTP-sent link).
- **`initialPassword` is the difference between user state `active` vs `initial`**. Without it, the user lands in state `initial` — and any attempt to `_deactivate` returns `404 COMMAND-ke0fw "User with state initial can only be deleted not deactivated"`. In production omit it (operator goes through invite flow); in tests/seeds set it explicitly.

Deactivate / reactivate:

```http
POST /management/v1/users/{userId}/_deactivate
x-zitadel-orgid: ${orgId}

{}
```

```http
POST /management/v1/users/{userId}/_reactivate
x-zitadel-orgid: ${orgId}

{}
```

---

## Seed an admin user (bootstrap-time)

Most bootstrap scripts (including `assets/bootstrap-zitadel.ts`) create org/project/roles/app but **do not** seed any human user. The Zitadel FirstInstance admin (`zitadel-admin@zitadel.<external-domain>`) exists but typically has no grant on your project — so you can't smoke-test login until you create a real user.

Run this two-step combo manually (or wrap it in your bootstrap):

```bash
PAT=$(cat <volume>/admin.pat)
ORG=<orgId>          # from bootstrap.json
PROJECT=<projectId>  # from bootstrap.json

# 1) Create the human user
CREATE=$(curl -sS -X POST "http://<external-domain>/v2/users/human" \
  -H "Authorization: Bearer $PAT" -H "x-zitadel-orgid: $ORG" -H 'Content-Type: application/json' \
  -d '{
    "username": "admin@example.com",
    "profile": {"givenName":"Admin","familyName":"Example","displayName":"Admin Example","preferredLanguage":"pt-BR"},
    "email": {"email":"admin@example.com","isVerified":true},
    "password": {"password":"ChangeMe-2026!","changeRequired":false}
  }')
USERID=$(echo "$CREATE" | sed -n 's/.*"userId":"\([^"]*\)".*/\1/p')

# 2) Grant the project role
curl -sS -X POST "http://<external-domain>/management/v1/users/$USERID/grants" \
  -H "Authorization: Bearer $PAT" -H "x-zitadel-orgid: $ORG" -H 'Content-Type: application/json' \
  -d "{\"projectId\":\"$PROJECT\",\"roleKeys\":[\"battery.admin\"]}"
```

**Notes**:

- `/v2/users/human` (v2 REST) accepts `givenName`/`familyName` (not `firstName`/`lastName` — that's the v1 `/management/v1/users/human` shape, see §"Create a human user"). The two endpoints have different field names; pick one consistently.
- `email.isVerified: true` is required if you want the user to log in immediately without an SMTP-sent verification link.
- `password.changeRequired: false` skips the forced password-change wizard on first login. Useful for dev seeds; **never** for production users.
- Whitelist policies (e.g., `enforce-jrc-email-whitelist`) intercept this call. If the user creation 422s, check your `pre_creation_user` Action.

---

## Re-reading bootstrap output after volume reset

A `docker compose down -v` (or any "reset Zitadel" workflow) wipes the IdP database and the next boot regenerates **all** numeric IDs: `orgId`, `projectId`, `clientId`, even `appId`. Anything in your stack that cached the old IDs starts misbehaving silently — most painfully, JWT validation on the backend fails 100% with `aud` mismatch, and the SPA goes into a silent-renew storm (see `troubleshooting.md §"401 storm with apparently-valid JWT"`).

**The rule**: never hardcode IDs from the bootstrap output anywhere. Always re-derive on every boot.

The bootstrap script writes a JSON like this each run (the actual path varies — search where your CI / dev script invokes the bootstrap):

```json
{
  "orgId": "370883099636006915",
  "projectId": "370883099736670211",
  "appId": "370883099988328451",
  "clientId": "370883099988393987",
  "redirectUris": ["..."]
}
```

Pipe it into your dev launcher / deploy step before starting the backend or the frontend dev server:

```bash
JSON="infra/docker/zitadel/local/bootstrap.json"
PROJECT_ID="$(jq -r .projectId "$JSON")"
CLIENT_ID="$(jq -r .clientId "$JSON")"

# Backend — audience MUST be the projectId, not the clientId
sed -i "s|^AUTH_AUDIENCE=.*|AUTH_AUDIENCE=${PROJECT_ID}|" packages/backend/.env
sed -i "s|^OIDC_AUDIENCE=.*|OIDC_AUDIENCE=${PROJECT_ID}|" packages/backend/.env

# SPA
sed -i "s|^VITE_OIDC_CLIENT_ID=.*|VITE_OIDC_CLIENT_ID=${CLIENT_ID}|" .env.local
```

Equivalent in Docker Compose:

```yaml
services:
  backend:
    environment:
      AUTH_AUDIENCE: ${PROJECT_ID:?run scripts/load-bootstrap.sh first}
```

…paired with a `scripts/load-bootstrap.sh` that exports the values from the JSON before `docker compose up`.

**What invalidates on every reset** (if you cache any of these, refresh them):

| Field | Used by |
|-------|---------|
| `projectId` | Backend `AUTH_AUDIENCE` / `OIDC_AUDIENCE`; ID-token `aud` check; project-scoped grant calls |
| `clientId` | SPA `VITE_OIDC_CLIENT_ID`; the OIDC `client_id` query parameter |
| `appId` | Management API calls that update OIDC config (e.g. `PUT /apps/{appId}/oidc_config`) |
| `orgId` | Every Management API request (`x-zitadel-orgid` header) |

The PAT under `<volume>/admin.pat` also rotates on reset — anything that reads it must re-read after each boot, not just at process start.

---

## Login policy tweaks (instance-wide UX)

Two flags you'll likely want to override from defaults:

### `mfaInitSkipLifetime: "0s"` — disable the MFA setup re-prompt

Default is **30 days**: even with `forceMfa: false`, Zitadel re-asks every user to set up MFA when their last "Skip" expires. Set to `0s` to skip permanently (or use a number to extend the silence window).

```bash
PAT=$(cat <volume>/admin.pat); ORG=<orgId>
# 1) Fetch current policy (PUT requires the full body)
curl -sS "http://<external-domain>/admin/v1/policies/login" \
  -H "Authorization: Bearer $PAT" -H "x-zitadel-orgid: $ORG"

# 2) PUT with the merged change
curl -sS -X PUT "http://<external-domain>/admin/v1/policies/login" \
  -H "Authorization: Bearer $PAT" -H "x-zitadel-orgid: $ORG" -H 'Content-Type: application/json' \
  -d '{ ...current values..., "mfaInitSkipLifetime":"0s" }'
```

### `loginV2.required: false` — use the bundled Login UI v1

This is an **instance feature**, not a login policy. Default `true` in newer Zitadel, but Login UI v2 needs a separate Next.js deployment. See `troubleshooting.md §"Hosted UI returns 404"` for the full diagnostic and fix.

```bash
curl -sS -X PUT "http://<external-domain>/v2/features/instance" \
  -H "Authorization: Bearer $PAT" -H 'Content-Type: application/json' \
  -d '{"loginV2":{"required":false}}'
```

---

## User grants (assign / revoke project roles)

This is the single biggest endpoint trap. There are TWO paths that look like they should both work:

| Path | Status |
|------|--------|
| `POST /management/v1/users/{userId}/grants/_search` | ❌ `405 Method Not Allowed` |
| `POST /management/v1/users/grants/_search` | ✅ Works — pass userId via query filter |

Use the global path with a `userIdQuery` filter:

```http
POST /management/v1/users/grants/_search
x-zitadel-orgid: ${orgId}

{ "queries": [{ "userIdQuery": { "userId": "${zitadelUserId}" } }] }
```

Response: `{ "result": [{ "id": "grantId", "projectId": "...", "roleKeys": ["..."] }] }`.

A user has at most one grant per project per org. Implement assign/revoke as **search-then-update**:

1. Search for an existing grant on `(userId, projectId)`.
2. If exists: PUT to update `roleKeys` (union for assign, set-minus for revoke).
3. If not exists: POST a fresh grant (assign only).
4. If revoking and `roleKeys` would become empty: DELETE the grant.

Endpoints:

```http
POST   /management/v1/users/{userId}/grants                    # create grant
PUT    /management/v1/users/{userId}/grants/{grantId}          # update roleKeys
DELETE /management/v1/users/{userId}/grants/{grantId}          # remove grant
```

Body for create:

```json
{ "projectId": "${projectId}", "roleKeys": ["battery.operator"] }
```

Body for update:

```json
{ "roleKeys": ["battery.operator", "battery.admin"] }
```

Why this matters: a naive implementation that POSTs a new grant on every assign produces duplicate grants which Zitadel **rejects** (the second call returns `ALREADY_EXISTS`). Search-then-update is required for idempotency.

---

## Working bootstrap reference

The full idempotent bootstrap script for Org/Project/Roles/App is at `assets/bootstrap-zitadel.ts`. It implements all the patterns in this cheatsheet. Copy it into a new project's `scripts/` directory and adjust the constants at the top.

---

## Rate limiting and pagination

- Search endpoints take optional `query: { offset, limit, asc }` for pagination. Default limit is 100; max varies by endpoint (often 1000).
- There's no published rate limit on self-hosted, but be defensive: in bootstrap scripts, single-thread the operations rather than parallelizing — the events pipeline can fall behind on bursts.

---

## v3 → v4 breaking changes worth knowing

- `OrganizationService.AddOrganization` (v2 Connect) was added in v3 and remains in v4. If you target v3 clusters, also test that endpoint exists.
- The Login UI v2 (`zitadel-login` Next.js container) was promoted in v4 and uses `IAM_LOGIN_CLIENT` role. The v1 login UI is still bundled in the binary at `/ui/login/`.
- Some response field names migrated from `id` to `<resource>Id` (e.g., `appId`, `organizationId`). Read the actual response, don't assume.

---

## Going further

- Token validation patterns in your backend: `references/token-validation.md`.
- Mapping domain `tenantId` to numeric `orgId`: `references/tenant-org-mapping.md`.
- Stuck on an error: `references/troubleshooting.md`.
