# API v1 → v2 mapping (Zitadel v4.x)

This is a working reference for refactoring callers (bootstrap scripts, admin tooling, integration glue) from the legacy Management API v1 to the v2 service surface that ships with Zitadel v4. Both APIs coexist — v1 is not removed, just no longer the recommended target for new code.

**The point of v2 is not "newer is better" — it's resource-based, contextually self-describing, and consolidates per-resource-type instead of per-use-case.** Some operations have v1 + v2 equivalents you can pick from; some are still v1-only. Migrate where it's clean, leave the rest.

For the actual upgrade procedure (image bump, schema migration, login UI split), see `migration-v2-to-v4.md`. This file is about **callers**, not the IdP itself.

## §1. Path prefixes (v4.x)

| Surface | Path | When |
|---|---|---|
| **v2 Connect (JSON)** | `POST /zitadel.<service>.v2.<Method>` with `Content-Type: application/json` | Default for new code. Body is JSON, response is JSON. |
| **v2 Connect (binary)** | Same path with `Content-Type: application/connect+proto` | When you have a generated client for the proto. Same wire endpoints. |
| **v2 REST** | `/v2/...` (e.g., `/v2/users/human`, `/v2/features/instance`) | Some services expose a REST transcoding. Coverage is uneven; when in doubt, use the Connect path. |
| **v1 REST (legacy)** | `/admin/v1/...`, `/management/v1/...`, `/auth/v1/...` | Still works in v4. Don't remove what you have unless you're actively rewriting. |
| **v1 gRPC (legacy)** | `/zitadel.management.v1.ManagementService/...`, `/zitadel.admin.v1.AdminService/...` | Same as above, gRPC variant. |
| **OIDC / OAuth / SAML** | `/oauth/v2/...`, `/oidc/v1/userinfo`, `/.well-known/openid-configuration`, `/saml/v2/...` | Standards endpoints; **unchanged across the v2 upgrade**. Your SPA / token validation code does not need to move. |

`/v2beta/` exists for backward compatibility from beta releases — treat as v2 for new code, but prefer the stable `/v2/` path or Connect when both are documented for the same operation.

## §2. Service mapping (covers the 13 v1 calls in `bootstrap-zitadel.ts`)

The table below is anchored on the actual calls in `assets/bootstrap-zitadel.ts` (and the typical `packages/idp/scripts/bootstrap-zitadel.ts` in consumer projects). Each row gives v1 path → v2 service → v2 path.

| Operation | v1 (legacy) | v2 service | v2 path (Connect, default) |
|---|---|---|---|
| Search orgs by name | `POST /admin/v1/orgs/_search` | `OrganizationService` | `POST /zitadel.org.v2.OrganizationService/ListOrganizations` |
| Create org (no human admin) | `POST /zitadel.org.v2.OrganizationService/AddOrganization` *(already v2)* | `OrganizationService` | unchanged |
| Read login policy | `GET /admin/v1/policies/login` | `SettingsService` | `POST /zitadel.settings.v2.SettingsService/GetLoginSettings` |
| Update login policy | `PUT /admin/v1/policies/login` | `SettingsService` | `POST /zitadel.settings.v2.SettingsService/SetLoginSettings` |
| Read SMTP | `GET /admin/v1/smtp/` | `SettingsService` | `POST /zitadel.settings.v2.SettingsService/GetSMTPConfig` |
| Search projects by name | `POST /management/v1/projects/_search` | `ProjectService` | `POST /zitadel.project.v2.ProjectService/ListProjects` |
| Create project | `POST /management/v1/projects` | `ProjectService` | `POST /zitadel.project.v2.ProjectService/CreateProject` |
| Search project roles | `POST /management/v1/projects/{p}/roles/_search` | `ProjectService` | `POST /zitadel.project.v2.ProjectService/ListProjectRoles` |
| Add project role | `POST /management/v1/projects/{p}/roles` | `ProjectService` | `POST /zitadel.project.v2.ProjectService/AddProjectRole` |
| Search apps in project | `POST /management/v1/projects/{p}/apps/_search` | `ApplicationService` | `POST /zitadel.application.v2.ApplicationService/ListApplications` |
| Create OIDC app | `POST /management/v1/projects/{p}/apps/oidc` | `ApplicationService` | `POST /zitadel.application.v2.ApplicationService/CreateApplication` (`type=OIDC` in body) |
| Update OIDC app config | `PUT /management/v1/projects/{p}/apps/{a}/oidc_config` | `ApplicationService` | `POST /zitadel.application.v2.ApplicationService/UpdateApplication` |
| Search human users | `POST /management/v1/users/_search` | `UserService` | `POST /zitadel.user.v2.UserService/ListUsers` |
| Create human user | `POST /management/v1/users/human` | `UserService` | `POST /v2/users/human` (REST) **or** `POST /zitadel.user.v2.UserService/AddHumanUser` |
| Search user grants | `POST /management/v1/users/grants/_search` | `AuthorizationService` | `POST /zitadel.authorization.v2.AuthorizationService/ListAuthorizations` |
| Create user grant | `POST /management/v1/users/{u}/grants` | `AuthorizationService` | `POST /zitadel.authorization.v2.AuthorizationService/CreateAuthorization` |
| Set instance feature flag | `PUT /v2/features/instance` *(already v2 REST)* | `FeatureService` | `POST /zitadel.feature.v2.FeatureService/SetInstanceFeatures` (Connect equivalent) |
| Create action target | `POST /v2/actions/targets` *(already v2 REST)* | `ActionService` | `POST /zitadel.action.v2.ActionService/CreateTarget` (Connect equivalent) |

Notes:

- `Application.CreateApplication` in v2 is a single endpoint that creates OIDC, SAML, or API apps; the request body discriminates by type field. v1 had three separate paths (`/apps/oidc`, `/apps/saml`, `/apps/api`).
- `AuthorizationService` replaces the v1 grant endpoints — note the rename from "grant" to "authorization" in path/method names. The semantics are identical.
- The v2 search methods often just take a flat filter object instead of v1's `queries: [{ <filterTypeQuery>: {...} }]` wrapper. Read the response carefully.

### §2.1. List\* response field names — non-uniform across services (v4.15 verified)

When porting code from v1 (which reliably used `result[]` everywhere) to v2, the JSON response field for the list of items is **per-service** — and the camelCase form differs from what you might guess. Wrong field name = silent `undefined` → `find()` returns `null` → "create" path runs, hits `ALREADY_EXISTS`, and the bootstrap fails on re-runs.

| Service / Method | proto field | JSON (camelCase) |
|---|---|---|
| `OrganizationService.ListOrganizations` | `result` | **`result`** |
| `UserService.ListUsers` | `result` | **`result`** |
| `ProjectService.ListProjects` | `projects` | **`projects`** |
| `ProjectService.ListProjectRoles` | `project_roles` | **`projectRoles`** |
| `ApplicationService.ListApplications` | `applications` | **`applications`** |
| `AuthorizationService.ListAuthorizations` | `authorizations` | **`authorizations`** |

Verified against `proto/zitadel/<svc>/v2/<svc>_service.proto` at tag `v4.15.0`. When in doubt, hit the proto on raw GitHub.

### §2.2. List\* request shapes — `filters[]` is the only path

`ListProjectsRequest`, `ListApplicationsRequest`, `ListAuthorizationsRequest` and similar **do not accept top-level `projectId` / `organizationId` / `userId` fields**. Those are silently dropped if you send them — the server returns the unfiltered list. You must wrap the filter in the service's `<Resource>SearchFilter` `oneof` inside `filters: []`.

Each `<Resource>SearchFilter` is a oneof — exactly one branch must be set per filter object. Filters AND together. Some inner branch names are non-uniform:

| Service | Filter wrapper | Common branches (camelCase JSON) |
|---|---|---|
| `ProjectSearchFilter` | `filters[]` | `projectNameFilter` (inner field is `projectName`, not `name`); `inProjectIdsFilter`; `organizationIdFilter` |
| `ApplicationSearchFilter` | `filters[]` | `projectIdFilter` (inner `projectId`); `nameFilter` (inner `name` — note the bare name, not `applicationNameFilter`); `stateFilter`; `typeFilter`; `clientIdFilter`; `entityIdFilter` |
| `AuthorizationSearchFilter` | `filters[]` | exists in proto but inner branch names not canonical here — fall back to client-side filter when in doubt |
| `UserSearchQuery` (still v1-style!) | `queries[]` | `userNameQuery` etc. — `UserService` kept the v1 wrapper in v4.15 |
| `OrganizationService.ListOrganizations` | `queries[]` | same as User — kept the v1 wrapper |

**Pragmatic fallback**: when proto field names are unstable across patches or you can't verify them quickly, **list all + filter client-side in JS**. Project / app counts in typical bootstraps are tiny (1-5), so the cost is negligible and the resulting code stays robust to upstream proto renames.

### §2.3. Single-resource response field names — `*Id`, not `id`

The new v2 `Project` and `Application` messages use the resource-typed ID name in the field, not the bare `id`:

| Object | proto / JSON field for the unique ID |
|---|---|
| `Project` | `project_id` / **`projectId`** |
| `Application` | `application_id` / **`applicationId`** |
| `Application.oidcConfiguration` (oneof branch) | `oidc_configuration` / **`oidcConfiguration`** (NOT `oidc` or `oidcConfig`) |
| `Authorization` | `id` (kept short here — but `project`, `user`, `roles` are nested objects, see §1.13) |

Verified against `proto/zitadel/application/v2/application.proto` and `proto/zitadel/project/v2/query.proto` at tag `v4.15.0`. Classic v1 used `id` universally; v2 spelled it out. Code that reads `existing.id` from a v1-shaped consumer silently breaks against v2.

## §3. Contextual info (header → body)

This is the single most disruptive change for refactor work, and the source of Quirk 27.

**v1** carried org context in the header:

```http
POST /management/v1/projects HTTP/1.1
Authorization: Bearer ${PAT}
Content-Type: application/json
x-zitadel-orgid: 370883099636006915

{ "name": "ERP-JRC" }
```

**v2** carries it in the body, named per resource (most commonly `organizationId`, sometimes nested as `org.id` or `resourceOwner`):

```http
POST /zitadel.project.v2.ProjectService/CreateProject HTTP/1.1
Authorization: Bearer ${PAT}
Content-Type: application/json

{
  "organizationId": "370883099636006915",
  "name": "ERP-JRC"
}
```

**Common refactor failure mode**: dropping the header but forgetting to add the body field. Symptom is `INVALID_ARGUMENT: missing organization_id` (or per-resource equivalent). When you see that, grep your refactored code for the call site — the field is missing, not the auth.

The header is **harmless on v2 calls** (ignored). You can leave `x-zitadel-orgid` set globally on your HTTP client during the transition without breaking v2 calls — useful when v1 and v2 calls share the same client.

## §4. Body-shape changes worth flagging

A few v1 → v2 payload diffs that are easy to miss:

### `AddHumanUser` — `firstName/lastName` → `givenName/familyName`

```diff
# v1 — POST /management/v1/users/human
- {
-   "userName": "user@example.com",
-   "profile": {
-     "firstName": "Given",
-     "lastName": "Family",
-     "preferredLanguage": "pt-BR"
-   },
-   "email": { "email": "...", "isEmailVerified": true },
-   "initialPassword": "..."
- }

# v2 — POST /v2/users/human (or Connect AddHumanUser)
+ {
+   "userId": "<your-deterministic-id>",
+   "username": "user@example.com",
+   "profile": {
+     "givenName": "Given",
+     "familyName": "Family",
+     "preferredLanguage": "pt"
+   },
+   "email": { "email": "...", "isVerified": true },
+   "password": { "password": "...", "changeRequired": false }
+ }
```

Field renames worth singling out:

- `firstName` → `givenName`, `lastName` → `familyName`
- `userName` → `username` (lower-case n)
- `email.isEmailVerified` → `email.isVerified`
- `initialPassword` → `password.{ password, changeRequired }` (object now)
- `preferredLanguage`: `pt-BR` (v1 accepted) → `pt` (v2 only accepts ISO-639-1 short codes — same as Quirk 22 for custom_login_text). If you pass `pt-BR` you'll get `400 LANG-...`.

### `CreateApplication` (replaces `apps/oidc`) — discriminator + nested config (v4.15 verified)

This one bites. Three traps in a row:

1. **The discriminator JSON field is `oidcConfiguration`, not `oidc`.** Proto in v4.15 has `oneof application_type { CreateOIDCApplicationRequest oidc_configuration = 4; ... }`. The standard protojson serialization of a oneof emits **only the selected branch field** at the top level (no wrapper field with the oneof name). The branch is named `oidc_configuration` → camelCase JSON is `oidcConfiguration`.
2. **Server error names the oneof, not the branch.** If you forget to set any branch, you get `400 invalid_argument: invalid CreateApplicationRequest.ApplicationType: value is required`. The `ApplicationType` is the proto oneof name — not a JSON field. Tempting trap: respond by wrapping `{ "applicationType": { "oidc": {...} } }` (which would be a literal proto field at the request level if it existed — it doesn't). That payload also fails. The fix is to set `oidcConfiguration` directly at the top level.
3. **Inner field names are not the v1 short names.** Inside `oidcConfiguration` the OIDC fields use the proto canonical names: `applicationType` (NOT `appType`) and `developmentMode` (NOT `devMode`). v1 REST accepted `appType`/`devMode` for years; v2 Connect/JSON does not.

```diff
# v1 — POST /management/v1/projects/{p}/apps/oidc
- {
-   "name": "battery-lifecycle-web",
-   "redirectUris": [...],
-   "grantTypes": ["OIDC_GRANT_TYPE_AUTHORIZATION_CODE", ...],
-   "appType": "OIDC_APP_TYPE_USER_AGENT",
-   "devMode": false,
-   ...
- }

# v2 — POST /zitadel.application.v2.ApplicationService/CreateApplication
+ {
+   "projectId": "<projectId>",
+   "applicationId": "<your-deterministic-uuid>",
+   "name": "battery-lifecycle-web",
+   "oidcConfiguration": {                     // ← proto: `oidc_configuration`, NOT `oidc`
+     "redirectUris": [...],
+     "postLogoutRedirectUris": [...],
+     "grantTypes": ["OIDC_GRANT_TYPE_AUTHORIZATION_CODE", "OIDC_GRANT_TYPE_REFRESH_TOKEN"],
+     "responseTypes": ["OIDC_RESPONSE_TYPE_CODE"],
+     "applicationType": "OIDC_APP_TYPE_USER_AGENT",   // ← NOT `appType`
+     "authMethodType": "OIDC_AUTH_METHOD_TYPE_NONE",
+     "version": "OIDC_VERSION_1_0",
+     "developmentMode": false,                        // ← NOT `devMode`
+     "accessTokenType": "OIDC_TOKEN_TYPE_JWT",
+     "accessTokenRoleAssertion": true,
+     "idTokenRoleAssertion": true,
+     "idTokenUserinfoAssertion": true,
+     "clockSkew": "5s"
+   }
+ }
```

SAML / API equivalents nest under `samlConfiguration` / `apiConfiguration` respectively. Mutually exclusive — exactly one branch per request.

The response mirrors the discriminator: `CreateApplicationResponse` is `{ applicationId, oidcConfiguration: { clientId, clientSecret? }, ... }`. Some patches return the response with `oidcConfiguration` empty/missing — when that happens, follow up with `GetApplication { applicationId }` (note: no `projectId` in the v2 GetApplication request body — silently dropped) which returns `{ application: { applicationId, oidcConfiguration: { clientId } } }`.

`UpdateApplication` follows the same shape (`{ projectId, applicationId, oidcConfiguration: {...} }`) — `COMMAND-1m88i` no-op trap from Quirk 14 still applies.

### `AuthorizationService` (replaces `users/grants`) — Create requires `organizationId`; Update/Delete take `id`

Subtle gotchas in v4.15:

- `CreateAuthorizationRequest` requires **`organizationId`** alongside `userId`/`projectId` (REQUIRED in proto — `validate.rules.string.min_len: 1`). It's the org that **owns the project**, which may differ from the user's own org. Forgetting it: `400 invalid_argument: CreateAuthorizationRequest.OrganizationId: value length must be between 1 and 200 runes`.
- `UpdateAuthorizationRequest` and `DeleteAuthorizationRequest` take the field **`id`**, not `authorizationId`. The Create response returns `{ id }` (also bare), so you read `id` from create and pass `id` into update/delete.
- The `Authorization` shape returned by `ListAuthorizations` is **nested**, not flat: `{ id, project: { id, name, organizationId }, organization: { id, name }, user: { id, preferredLoginName, ... }, roles: [{ key, displayName }], state }`. Code that reads `a.userId`, `a.projectId`, `a.roleKeys` (the v1 flat shape) silently sees `undefined` and "no match found".

```typescript
// Create
await connect('/zitadel.authorization.v2.AuthorizationService/CreateAuthorization', {
  userId,
  projectId,
  organizationId: orgIdThatOwnsProject,        // ← REQUIRED
  roleKeys: ['battery.admin'],
});
// → { id: '371...', creationDate: '...' }

// Update
await connect('/zitadel.authorization.v2.AuthorizationService/UpdateAuthorization', {
  id: existing.id,                              // ← `id`, NOT `authorizationId`
  roleKeys: ['battery.admin', 'battery.operator'],
});

// List + match (client-side, see §2.2)
const res = await connect('.../ListAuthorizations', {});
const found = res.authorizations?.find(           // ← `authorizations`, NOT `result`
  (a) => a.user?.id === userId && a.project?.id === projectId,
);
```

## §5. Idempotence patterns

v1 and v2 imply different idempotence styles. v1 was search-then-create; v2 prefers deterministic IDs.

| Style | v1 pattern | v2 pattern |
|---|---|---|
| **Resources with stable name** (org "JRC", project "ERP-JRC") | `POST /resource/_search` filtered by name; if 0 hits → `POST /resource` | Same — search first, then create. v2 lets you pass an `organizationId` you generated, but for human-readable resources the name-search pattern is still common. |
| **Resources with deterministic ID** (users by UUIDv4, project apps by deterministic UUID) | Couldn't supply own ID — Zitadel generated it; you read it back. | Supply your own `userId` / `applicationId` in the body. Duplicate ID returns `ALREADY_EXISTS` error code; treat as success. **No round-trip required.** |
| **Update-or-create idempotent PUT** | `PUT /resource/{id}` — Zitadel returns `400 COMMAND-1m88i "No changes"` when body matches state (Quirk 14). | Same `COMMAND-1m88i` returns from `Update*` methods. Catch and treat as no-op. The error code is preserved across v1/v2. |

**`AlreadyExists` matcher needs to also catch `AlreadyExisting` (with `ing`).** Zitadel v4 sometimes uses the gerund form in error IDs — observed cases include `Errors.Project.App.AlreadyExisting` (when re-running CreateApplication with a name that already exists in the project) and `Errors.User.AlreadyExisting`. A naive substring matcher that checks only `'AlreadyExists'` will miss these and bubble the error to the bootstrap as a fatal. Cover both:

```typescript
const ALREADY_EXISTS_MARKERS = [
  '"code":6',
  'ALREADY_EXISTS',
  'already_exists',
  'already exists',
  'AlreadyExists',
  'AlreadyExisting',   // ← v4 also uses this form
];
```

**Concrete example** — creating an OIDC app idempotently in v2:

```typescript
// Generate a deterministic ID once for this project's app — store in YAML/.env
const appId = '01HXG...';   // v7 UUID, persisted

try {
  await connect('/zitadel.application.v2.ApplicationService/CreateApplication', {
    projectId,
    applicationId: appId,
    name: 'battery-lifecycle-web',
    oidc: { redirectUris, /* ... */ },
  });
} catch (err) {
  if (isAlreadyExists(err)) {
    // Re-run path: app already exists — fall through to update
  } else {
    throw err;
  }
}

// Always reconcile config (will no-op if unchanged)
try {
  await connect('/zitadel.application.v2.ApplicationService/UpdateApplication', {
    projectId,
    applicationId: appId,
    oidc: { redirectUris, /* ... */ },
  });
} catch (err) {
  if (isNoChanges(err)) {
    // Quirk 14 — body matches current state. No-op.
  } else {
    throw err;
  }
}
```

This pattern saves a `_search` round-trip on every bootstrap re-run. For a 5-app multi-system bootstrap, that's 5 fewer round-trips per boot — meaningful when bootstrapping is part of a hot deploy path.

## §6. What's still v1-only (as of v4.15)

This list shrinks over time — re-check upstream when you plan migration work.

- **`SystemService`** (`/system/v1/...`): instance lifecycle, multi-instance management. Not yet ported to v2. Most consumers don't hit this — it's for Zitadel-as-a-service operators.
- **`AuthService.GetMyUser` / `/auth/v1/users/me`** flow has a v2 replacement (`UserService.GetUserByID` with the caller's user ID). Both work; v1 is shorter.
- **Some advanced read endpoints**: bulk import (`/admin/v1/import`), org-scoped configs that don't have a v2 SettingsService method yet.

When the v2 endpoint exists but is described as `_v2beta_`, treat as production-usable — Zitadel uses the `/v2beta/` prefix during stabilization windows.

Source of truth: <https://zitadel.com/docs/apis/migration_v1_to_v2>. If a service appears there but not here, this file is out of date — bump the skill version.

## §7. Auth — unchanged across v1/v2

This is the one easy part of the migration:

- **PAT**: `Authorization: Bearer <PAT>` works for all v1 + v2 + Connect endpoints with the same scopes. The IAM_OWNER PAT from FirstInstance setup (`/current-dir/admin.pat`) is sufficient for everything in this guide.
- **Service account JWT**: same. Works as v1, works as v2.
- **Connect protocol JSON**: just `Content-Type: application/json` plus the bearer header. No additional Connect-specific headers required.
- **Connect protocol binary**: `Content-Type: application/connect+proto`. Use only if you have a generated client.

## §8. Migration checklist (per caller / script)

Practical sequence when refactoring a single caller from v1 to v2:

1. **Locate the call**. Note the v1 path, the headers (especially `x-zitadel-orgid`), and the body shape.
2. **Find the v2 mapping** in §2 above. If absent, check upstream — the operation may not be ported yet.
3. **Move context to body**: drop `x-zitadel-orgid` from this call's headers, add `organizationId` (or per-resource equivalent) to the body. Don't drop the header globally — other v1 calls in the same client still need it.
4. **Apply field renames** from §4 (most commonly user profile names, email verification flag, language code).
5. **Decide idempotence strategy**: keep search-then-create (safe) or move to deterministic-ID + ALREADY_EXISTS (one round-trip less). For bootstrap scripts that run on every deploy, the latter pays off.
6. **Run, observe, compare**: idempotence-wise the bootstrap output should be identical (same orgs/projects/users post-migration). The wire diff is the only change. If v1 and v2 versions return different IDs / different state, something else changed — dig in before declaring success.
7. **Don't refactor everything**. v1 keeps working in v4; mixing v1 and v2 calls in the same script is fine (they share the same auth and state). Refactor calls that benefit (deterministic IDs, multi-app, new resource types); leave what works.

## §9. Going further

- Upgrade procedure (image bump + schema migration): `references/migration-v2-to-v4.md`.
- Working v1 endpoints with payload examples: `references/api-cheatsheet.md` (v1 reference; intro now points here for v2 work).
- Idempotence Quirk 14 (`COMMAND-1m88i "No changes"`) — same in v1 and v2: `references/api-cheatsheet.md §"Create OIDC application"`.
- Bootstrap script with v1 calls annotated with v2 equivalents: `assets/bootstrap-zitadel.ts`.
