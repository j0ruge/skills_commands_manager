# Token Validation — Zitadel JWTs in Node/TypeScript

This reference covers validating Zitadel-issued access tokens in a backend. Examples are TypeScript with `jose`, but the patterns translate directly to other JWT libraries (Go's `oidc/v3`, Java's Spring Security `OAuth2ResourceServer`, Python's `python-jose`).

## Prerequisites at the Zitadel side

Before tokens contain what you expect, the OIDC application must have these flags set (see `api-cheatsheet.md §"Create OIDC application"`):

```json
{
  "accessTokenType": "OIDC_TOKEN_TYPE_JWT",
  "accessTokenRoleAssertion": true,
  "idTokenRoleAssertion": true,
  "idTokenUserinfoAssertion": true
}
```

Without these, your backend will receive opaque tokens (require introspection) or JWTs with no role claims, and you'll spend an hour wondering why authorization always returns 403.

The project itself must also have `projectRoleAssertion: true`.

## Required SPA scopes for the project audience

For the projectId to actually appear in the access token's `aud` claim, the SPA **must request** the scope:

```text
urn:zitadel:iam:org:project:id:<projectId>:aud
```

So a typical Vite SPA env looks like:

```env
VITE_OIDC_SCOPE=openid profile email urn:zitadel:iam:org:project:id:370503956331233283:aud
```

Without the `:aud` scope, `aud` only contains the `clientId` and your backend audience check fails 401 even though everything else is configured correctly. This is the single most common "the token looks fine but backend says 401" cause.

If your SPA needs to be issued tokens for multiple projects (rare), repeat the scope for each projectId. The `aud` claim becomes an array.

## Audience: project ID, not client ID

The audience claim (`aud`) of a Zitadel access token is the **project ID**, not the client ID. This is non-obvious because most OAuth examples online use `client_id` as audience.

```typescript
import { createRemoteJWKSet, jwtVerify } from 'jose';

const issuer = process.env.OIDC_ISSUER!;        // http://127.0.0.1.sslip.io:8080
const audience = process.env.OIDC_AUDIENCE!;    // <projectId>, NOT <clientId>

const jwks = createRemoteJWKSet(new URL('/oauth/v2/keys', issuer));

const { payload } = await jwtVerify(token, jwks, {
  issuer,
  audience,
  clockTolerance: '30s',
});
```

If you set `audience = clientId`, every token verification fails with `JWTClaimValidationFailed: unexpected "aud" claim value`. Match the project ID returned by `bootstrap-zitadel.ts`.

## JWKS caching

`createRemoteJWKSet` caches keys in-process with a default TTL of 30 seconds and the `kid` header is used to look up the right key. Two practical implications:

1. **Reuse the JWKS instance across requests.** Don't create a new one per request — that defeats caching and you'll hit Zitadel's `/oauth/v2/keys` on every JWT verification. Build it once at composition time.
2. **Key rotation is invisible to your code.** When Zitadel rotates the signing key, the next token's `kid` won't match anything cached, so `jose` re-fetches automatically. No code change required, but expect an occasional 100ms blip on the request that triggers re-fetch.

For latency-sensitive services, benchmark the cold-cache JWKS fetch — about 5-15ms in a local docker setup, 50-150ms over WAN.

## Access token vs ID token — what's actually inside

This trips up first-time integrators every single time. **Zitadel access tokens are minimal by design** — they carry just enough to authorize an API call, not to identify the user for display.

Default JWT access token payload from a Zitadel SPA login:

```json
{
  "sub": "370734264657903619",
  "iss": "http://127.0.0.1.sslip.io:8080",
  "aud": ["<clientId>", "<projectId>"],
  "exp": 1777517419,
  "iat": 1777474209,
  "client_id": "<clientId>",
  "urn:zitadel:iam:org:project:roles": { "battery.admin": { "<orgId>": "<orgDomain>" } }
}
```

What you **will not** find here, even with `idTokenUserinfoAssertion: true`:

- `name`, `preferred_username`, `email` — these are scopes for the **id_token** and `/oidc/v1/userinfo`, not the access token.
- `urn:zitadel:iam:org:id` — also id_token-only.
- `urn:zitadel:iam:org:domain:primary` — same.

That's a feature, not a bug: OAuth/OIDC intentionally separate access tokens (authorization) from id tokens (identity). Your backend only sees the bearer (access) token, so design your mapper around that.

**Defensive fallback rules for backend mappers**:

| Field | Primary | Fallback chain |
|-------|---------|----------------|
| `operatorId` | `payload.sub` | (no fallback — reject if missing) |
| `operatorName` | `payload.name` | `preferred_username` → `email` → `payload.sub` |
| `tenantId` | `payload['urn:zitadel:iam:org:id']` | `defaultTenant` env (single-tenant deploys) |
| `roles` | `Object.keys(payload['urn:zitadel:iam:org:project:roles'])` | translate via your ACL table; default `[]` |

If you really need `name`/`email`/`org:id` in the request lifecycle (e.g., for audit logging with display names), call `/oidc/v1/userinfo` with the bearer token from the backend — but expect an extra round-trip per request and cache the result.

## Mapping claims to your `AuthContext`

Zitadel emits two URN-style role claims:

```json
{
  "urn:zitadel:iam:org:project:roles": {
    "battery.operator": { "<orgId>": "<orgDomain>" }
  },
  "urn:zitadel:iam:org:project:<projectId>:roles": { /* same shape */ }
}
```

The first form is generic; the second is project-scoped. Use the generic form unless you're consuming tokens from multiple projects in one service (rare).

The role claim's **value** is a map of `orgId → orgDomain`. The keys of the outer object are the actual roles. Your backend cares about the keys:

```typescript
function rolesFromClaims(payload: JWTPayload): string[] {
  const claim = payload['urn:zitadel:iam:org:project:roles'] as
    | Record<string, Record<string, string>>
    | undefined;
  if (!claim) return [];
  return Object.keys(claim);
}
```

Other useful claims:

| Claim | Meaning |
|-------|---------|
| `sub` | Stable Zitadel user ID. Use this as your operator's external reference. |
| `name` | Display name (when scope `profile` is granted). |
| `email` | Email address (when scope `email` is granted). |
| `preferred_username` | Username (often the email). |
| `urn:zitadel:iam:org:id` | Zitadel **orgId** (numeric). Use to scope queries in your domain. |
| `urn:zitadel:iam:org:domain:primary` | Org's primary domain (e.g., `jrcbrasil.com`). |

## Express middleware pattern

```typescript
import type { Request, Response, NextFunction } from 'express';
import { createRemoteJWKSet, jwtVerify, type JWTPayload } from 'jose';

interface AuthContext {
  id: string;          // sub
  name: string;
  roles: string[];
  tenantId: string;    // your domain tenant id, mapped from orgId
}

declare module 'express-serve-static-core' {
  interface Request { auth?: AuthContext; }
}

export function makeAuthenticate(config: { issuer: string; audience: string }) {
  const jwks = createRemoteJWKSet(new URL('/oauth/v2/keys', config.issuer));

  return async function authenticate(req: Request, res: Response, next: NextFunction) {
    const header = req.headers.authorization;
    if (!header?.startsWith('Bearer ')) {
      return res.status(401).json({ code: 'UNAUTHENTICATED' });
    }
    try {
      const { payload } = await jwtVerify(header.slice(7), jwks, {
        issuer: config.issuer,
        audience: config.audience,
        clockTolerance: '30s',
      });
      if (!payload.sub) {
        return res.status(401).json({ code: 'INVALID_TOKEN', message: 'no sub' });
      }
      req.auth = mapClaimsToAuthContext(payload);
      next();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'invalid token';
      res.status(401).json({ code: 'INVALID_TOKEN', message: msg });
    }
  };
}

function mapClaimsToAuthContext(payload: JWTPayload): AuthContext {
  const rolesClaim = (payload['urn:zitadel:iam:org:project:roles'] ?? {}) as Record<string, unknown>;
  // Filter for valid role-key shape to defend against unexpected claims.
  const roles = Object.keys(rolesClaim).filter((r) => /^[a-z]+\.[a-z_]+$/.test(r));
  const orgId = String(payload['urn:zitadel:iam:org:id'] ?? '');
  return {
    id: String(payload.sub),
    // Defensive fallback chain: AT often lacks profile claims (see §"Access
    // token vs ID token"). Reject the call only on missing `sub`.
    name: String(
      payload.name ?? payload.preferred_username ?? payload.email ?? payload.sub,
    ),
    roles,
    // Same here — `urn:zitadel:iam:org:id` is id_token-only. Single-tenant
    // deploys: fall back to a configured default. Multi-tenant: enrich via
    // userinfo or block the call when org claim is mandatory.
    tenantId: domainTenantFromOrgId(orgId || process.env.DEFAULT_TENANT_ID || ''),
  };
}
```

## Authorization on top of validation

Validation only checks the token is genuine and unexpired. Authorization is "does this user have permission for this action?" — that's a separate middleware.

```typescript
export function requireRole(role: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.auth) return res.status(401).json({ code: 'UNAUTHENTICATED' });
    if (!req.auth.roles.includes(role)) {
      return res.status(403).json({ code: 'FORBIDDEN', message: `Requires ${role}` });
    }
    next();
  };
}

// usage:
app.post('/admin/users', authenticate, requireRole('battery.admin'), handler);
```

## When NOT to use JWT validation — opaque tokens + introspection

JWT access tokens cannot be revoked mid-lifetime: if you deactivate a user, their JWT remains valid until expiry (typically 15-60 min). For applications where instant revocation matters (e.g., financial transactions), use opaque tokens + introspection:

1. Configure the OIDC app with `accessTokenType: OIDC_TOKEN_TYPE_BEARER` (Zitadel's name for opaque).
2. Validate by POSTing the token to `/oauth/v2/introspect` on every request.
3. Cache results for a short TTL (10-30s) to limit Zitadel load.

Tradeoff: faster revocation at the cost of one extra round-trip per request. Most apps choose JWT + short access token lifetime (5-15 min) as a compromise.

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `JWTClaimValidationFailed: aud` | Audience mismatch | Use **projectId**, not clientId |
| `JWSSignatureVerificationFailed` | Wrong issuer URL or stale JWKS cache | Verify `OIDC_ISSUER` matches Zitadel's `iss` claim exactly (incl. scheme/port). Restart service if cache is corrupt. |
| Roles always empty | Project missing `projectRoleAssertion` OR app missing `accessTokenRoleAssertion` | Toggle both flags via API or Console. |
| `INVALID_TOKEN: no sub` | Using a token from `client_credentials` flow without a user | Service-to-service tokens may lack `sub`. Either use machine-user grants or accept tokens without `sub` for these specific endpoints. |
| Tokens expire too soon for UX | Default access token lifetime | Increase `accessTokenLifetime` on the OIDC app (max 24h, but 15-30 min recommended). Use refresh tokens to extend session. |
| 401 with `iss`/`aud`/`exp` correct, mapper returning null | Mapper requires `name`/`preferred_username`/`org:id` not present in AT | Fall back to `sub` for operatorName and `defaultTenant` for tenantId. See §"Access token vs ID token". |
| `aud` only contains `clientId`, audience check fails | Missing `urn:zitadel:iam:org:project:id:<projectId>:aud` scope on the SPA | Add the scope to `VITE_OIDC_SCOPE` (or equivalent) and force users to re-login. |
| 100% of `/api` requests return 401, JWT decoded by hand looks perfect, SPA falls into silent-renew loop and 429 follows | Backend Node can't validate the JWKS endpoint's TLS cert (self-signed/mkcert). `createRemoteJWKSet` fails the handshake before signature check. | Set `NODE_EXTRA_CA_CERTS=$(mkcert -CAROOT)/rootCA.pem` (or your local CA pem) on the backend process. See §"Trusting a self-signed JWKS endpoint from Node" below. |
| 100% 401 right after a Zitadel `down -v` / volume reset, even though bootstrap succeeded | `OIDC_AUDIENCE`/`AUTH_AUDIENCE` in backend env is the **previous** projectId — volume reset regenerated all IDs | Re-derive audience from the fresh `bootstrap.json` on every boot. See `api-cheatsheet.md §"Re-reading bootstrap output after volume reset"`. |

## Trusting a self-signed JWKS endpoint from Node

If your Zitadel instance serves HTTPS with a **self-signed** or **dev CA** cert (typical for LAN testing with mkcert + reverse proxy), Node's `fetch` will reject the TLS handshake before any JWT validation happens. `jose`'s `createRemoteJWKSet(new URL(jwksUrl))` returns an empty key set; the next `jwtVerify` raises a generic `JWSSignatureVerificationFailed` or `JWKSNoMatchingKey`. **The error is not labeled "TLS error"** — that's the trap. Symptom: every authenticated request 401s, JWT decoded by hand looks perfect.

**Fix — pass the local root CA to Node**:

```bash
# Linux/macOS — mkcert default
NODE_EXTRA_CA_CERTS="$(mkcert -CAROOT)/rootCA.pem" node dist/server.js

# Or in package.json scripts (kept in dev launcher, not committed):
NODE_EXTRA_CA_CERTS="/path/to/rootCA.pem" npm run dev
```

`NODE_EXTRA_CA_CERTS` *appends* to the OS bundle, so it's safe in production-shaped images — your real CA chains keep working. Set it in:

- The dev launcher / `dev.sh`
- The `environment:` block of the backend service in your `docker-compose.yml` for staging-like setups
- The `Environment=` directive in systemd units when running on bare-metal dev hosts

**Don't reach for `NODE_TLS_REJECT_UNAUTHORIZED=0`** — it disables certificate validation globally for the process, including any other HTTPS calls (database, third-party APIs). `NODE_EXTRA_CA_CERTS` only adds trust for the specific cert you point at, which is what you want.

**Diagnostic before applying the fix**:

```bash
# From the backend host. Should print a JWKS payload, not a TLS error.
curl --cacert "$(mkcert -CAROOT)/rootCA.pem" "https://<external-domain>/oauth/v2/keys"

# Same call without the CA — should fail with cert verify error if cert is local-only.
curl "https://<external-domain>/oauth/v2/keys"
```

If the first command works and the second errors on cert verification, you've confirmed the cause. The backend's behavior mirrors curl-without-CA.

## Logout / RP-initiated logout

To log a user out across the SPA AND Zitadel session, redirect them to:

```text
${OIDC_ISSUER}/oidc/v1/end_session
  ?id_token_hint=${idToken}
  &post_logout_redirect_uri=${urlEncoded(yourPostLogoutUrl)}
  &client_id=${clientId}
```

The `post_logout_redirect_uri` must match one configured in the OIDC app's `postLogoutRedirectUris` literally (FR-018 in our spec — same exact-match rule as `redirectUris`).

`id_token_hint` is recommended (not strictly required) — it tells Zitadel which session to terminate. Without it, the user may need to confirm logout in the Zitadel UI.

## Network reachability to the IdP from the JWT validator

`createRemoteJWKSet(new URL(jwksUrl))` does an ordinary Node `fetch` against the JWKS URL — at instantiation it doesn't fetch (the constructor is synchronous), but every JWKS reload after `cacheMaxAge` (default `600s` / 10 minutes) does. That fetch must succeed from inside the container running the validator, every time the cache expires.

In single-host self-hosted setups where backend, frontend, and Zitadel all run on the same VPS behind a reverse proxy (nginx-proxy/Caddy/Traefik), the backend container's DNS resolution of `idp.<your-domain>` hits the **public** IP of the host. Some VPS providers — and many bare-metal setups — handle hairpin NAT (DNS → external IP → loopback to the local proxy) inconsistently:

- **Stable hairpin**: backend reaches the proxy, JWKS reloads work indefinitely.
- **Flaky hairpin**: backend can reach the proxy after every restart, but the connection silently fails after a few minutes — when the JWKS cache expires, the reload's TCP handshake never completes, `fetch` times out, `jose` raises a `JOSEError`, the validator throws `InvalidTokenError`, and **every authenticated request returns 401** even though the JWT itself is decoded-perfect (`iss`/`aud`/`exp`/`kid` all valid, the `kid` is verifiably present in the JWKS endpoint when fetched from outside the container).

The pathognomonic symptom is **"backend works for ~10 minutes after restart, then 401-storms forever"**. Pre-fix uptime correlates with the JWKS TTL window — if your backend has been up for >`cacheMaxAge` and starts 401-storming, this is the most likely cause among the three documented in this skill (the others being self-signed JWKS over HTTPS — see "Trusting a self-signed JWKS endpoint" — and stale `clientId`/`AUTH_AUDIENCE` after a Zitadel volume reset).

### Diagnosis (3 commands)

```bash
# 1. What does the backend see when resolving the IdP hostname?
docker exec <backend> getent hosts idp.<your-domain>
# Public IP → hairpin path; bridge IP (172.17.0.1 typically) → host-gateway path.

# 2. Can the backend actually reach the JWKS endpoint right now?
docker exec <backend> wget -qO- --timeout=10 https://idp.<your-domain>/oauth/v2/keys | head -c 200
# Should print a valid JWKS JSON. Empty / error → reachability broken.

# 3. Is the JOSE warning firing in logs?
docker logs <backend> --tail 100 | grep '\[auth\] JOSE'
# Any `code=ERR_JOSE_*` in the warn lines confirms the failure path.
```

### Fix — `extra_hosts` mapping the IdP hostname to the docker bridge

In `docker-compose.prod.yml`, on the backend service:

```yaml
services:
  backend:
    # ...
    extra_hosts:
      - "idp.<your-domain>:host-gateway"
```

This makes the container resolve `idp.<your-domain>` to the docker-bridge IP (where the host's nginx-proxy listens on 443) — the same path external traffic takes — without depending on hairpin NAT. The backend reaches the proxy, the proxy routes to the Zitadel container via the shared `nginx-proxy` network, and JWKS reloads succeed indefinitely.

This pattern applies to **any container that talks to a service co-located on the same host**, not just IdP. Common cases: the bootstrap/seed container, the runner that runs CD jobs, observability sidecars. If you have multiple co-located containers calling the IdP via FQDN, every one of them needs the same `extra_hosts` block — it's a per-service setting, not host-wide.

### Logging tip — emit the JOSE error code via a structured logger, not `console.error`

When the JWKS reload fails (or any non-token-expiry error inside `jwtVerify`), the catch block of your validator is the only place that knows what actually went wrong. Don't swallow it; emit through your structured logger at **`warn` level, not `error`**:

```typescript
if (err instanceof joseErrors.JOSEError) {
  const code = 'code' in err && typeof err.code === 'string' ? err.code : 'n/a';
  this.config.logger?.warn({ code, message: err.message }, '[auth] JOSE error');
  throw new InvalidTokenError('Token inválido', { cause: err });
}
```

Why `warn` and not `error`: `JOSEError` also fires for **malformed tokens from clients** (attacker probing endpoints, old SPA bundles holding stale tokens, clock skew on the client side). If you log every JOSEError as `error`, you've added a log-spam vector in production. `warn` allows operators to filter via `LOG_LEVEL=info` if necessary, while keeping the diagnostic information available when needed.

The `code` field (`ERR_JWS_SIGNATURE_VERIFICATION_FAILED`, `ERR_JWKS_NO_MATCHING_KEY`, `ERR_JOSE_GENERIC`, etc.) is greppable and stable across `jose` minor versions — it's the fast path to triage between "network reached the JWKS but the key is wrong" vs "network never reached the JWKS at all".

## Going further

- API endpoint reference: `references/api-cheatsheet.md`
- Tenant→orgId mapping for the AuthContext: `references/tenant-org-mapping.md`
- Errors during validation: `references/troubleshooting.md`
