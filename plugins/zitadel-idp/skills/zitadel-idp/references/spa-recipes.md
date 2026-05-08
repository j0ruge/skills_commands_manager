# SPA Recipes — `react-oidc-context` + Zitadel patterns

This file collects working SPA wiring recipes that the upstream `react-oidc-context` and `oidc-client-ts` docs hint at but don't show end-to-end. Each one is here because we hit it in production and the obvious-looking implementation failed in a non-obvious way.

## Recipe 1 — Boot-time silent renew with `InMemoryWebStorage`

### When to use

You have an SPA with `userStore = InMemoryWebStorage()` (deliberate, to avoid persisting tokens in `localStorage`/`sessionStorage` and close the XSS exfil vector) and you want **F5 to keep the user signed in** by leveraging the IdP's session cookie. The `automaticSilentRenew: true` flag of `oidc-client-ts` will not solve this on its own — read on for why.

### Why the obvious thing fails

`automaticSilentRenew` only fires on the `accessTokenExpiring` event, which only fires when the `UserManager` already has a `User` with a known expiration. In-memory storage means F5 wipes the `User`; the `UserManager` boots into "no user" and just sits there. From the user's perspective, F5 = forced re-login, even though the IdP cookie is alive and would happily issue a new token via `/oauth/v2/authorize?prompt=none`.

The fix is to actively call `auth.signinSilent()` once at boot, right after the lib finishes its own initialization. That triggers the hidden iframe → IdP cookie → new authorization code → `User` rehydrated. The catch: doing this naively breaks in **at least three** different ways.

### The three traps

#### Trap 1 — Iframe recursion when `<AuthProvider>` wraps the silent-renew route

Most SPAs mount `<AuthProvider>` once at the root, around the entire `<Routes>` tree. That's correct for everything except `signinSilent`, because the iframe that `signinSilent` opens loads `/silent-renew` (the SPA's own route) — which re-mounts the *whole tree*, including `<AuthProvider>`, which fires *another* `signinSilent`, opening another iframe, infinitely.

Symptom: the parent UI sits forever in "Verifying session…", network tab shows iframe traffic that never completes the handshake, the parent `signinSilent` Promise never resolves.

Guard: skip boot-time silent renew when the current pathname is an auth-flow route, **and** when the page is itself running inside an iframe.

```typescript
function isAuthRoute(): boolean {
  if (typeof window === "undefined") return false;
  const path = window.location.pathname;
  return path === "/login" || path === "/silent-renew" || path === "/auth/callback";
}

function isInIframe(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.self !== window.top;
  } catch {
    // Cross-origin frame: `window.top` throws SecurityError — treat as iframe.
    return true;
  }
}
```

`/login` is in the list because if the user lands there directly, the form needs to mount. Holding the tree in a placeholder while `signinSilent` runs (and almost certainly fails with `interaction_required`) just delays the form for no benefit.

#### Trap 2 — StrictMode + closure `cancelled` flag = perpetual lockup

The textbook React pattern for "do an async thing in `useEffect` and protect against the component unmounting" is:

```typescript
useEffect(() => {
  let cancelled = false;
  void asyncThing().finally(() => {
    if (!cancelled) setSomething();
  });
  return () => { cancelled = true; };
}, []);
```

In StrictMode (which dev mode runs by default), React mounts → cleanup → mounts again to verify your effect is idempotent. With the pattern above:

1. **First run**: `cancelled = false`, fires `asyncThing()`, returns cleanup.
2. **Cleanup**: sets `cancelled = true` (in the closure of the *first run*).
3. **Second run**: gated by your `attempted` ref → returns early without firing a new Promise.
4. **The first run's Promise eventually resolves** → `.finally` checks `if (!cancelled)`, which reads the closure of the first run → `false` → `setSomething()` **never fires**.

The component is mounted (the second run is the live one), but the state update is skipped because the first closure thinks it was unmounted. Lockup.

Fix: do **not** use a `cancelled` flag when a ref already gates re-execution. Let `setBootstrapping(false)` run; the worst case is a no-op set on a still-mounted component (React 18+ no longer warns on unmounted-set in production builds anyway).

#### Trap 3 — `signinSilent` can hang silently in some setups

Even with `silentRequestTimeoutInSeconds` set on the `UserManagerSettings`, the iframe can sit in a state where the IdP redirected it somewhere unexpected (login form, an error page, a CSP-blocked frame) and `oidc-client-ts` never fires the `_signinSilentCallback` postMessage. The Promise neither resolves nor rejects. Watchdog timeout is mandatory.

```typescript
const SILENT_RENEW_BOOT_TIMEOUT_MS = 5000;

const timeoutId = setTimeout(() => setBootstrapping(false), SILENT_RENEW_BOOT_TIMEOUT_MS);
void auth.signinSilent()
  .catch(() => null)            // login_required is normal here
  .finally(() => {
    clearTimeout(timeoutId);
    setBootstrapping(false);
  });
```

If the Promise resolves first, the timeout is cleared and `setBootstrapping(false)` fires once. If the timeout fires first, the UI unblocks and `<ProtectedRoute>` redirects to `/login` as it would for any other unauthenticated user.

### The full recipe

```tsx
// AuthProvider.tsx
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  AuthProvider as OidcAuthProvider,
  useAuth as useOidcAuth,
} from "react-oidc-context";
import { buildOidcConfig } from "./oidcConfig";
import { SessionResolving } from "@/components/SessionResolving";

const SILENT_RENEW_BOOT_TIMEOUT_MS = 5000;

function isAuthRoute(): boolean { /* see Trap 1 */ }
function isInIframe(): boolean { /* see Trap 1 */ }

function ApiTokenBridge({ children }: { children: ReactNode }) {
  const auth = useOidcAuth();
  const [bootstrapping, setBootstrapping] = useState(true);
  const attempted = useRef(false);

  useEffect(() => {
    if (attempted.current) return;
    if (auth.isLoading) return;        // wait for the lib's own init
    attempted.current = true;

    if (auth.user || auth.error) {
      setBootstrapping(false);
      return;
    }
    if (isAuthRoute() || isInIframe()) {
      setBootstrapping(false);
      return;
    }

    const timeoutId = setTimeout(() => setBootstrapping(false), SILENT_RENEW_BOOT_TIMEOUT_MS);
    void auth.signinSilent()
      .catch(() => null)
      .finally(() => {
        clearTimeout(timeoutId);
        setBootstrapping(false);
      });
    // No `cancelled` flag — see Trap 2.
  }, [auth.isLoading, auth.user, auth.error, auth]);

  if (bootstrapping) return <SessionResolving />;
  return <>{children}</>;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const config = useMemo(() => buildOidcConfig(), []);
  return (
    <OidcAuthProvider {...config}>
      <ApiTokenBridge>{children}</ApiTokenBridge>
    </OidcAuthProvider>
  );
}
```

`<SessionResolving />` is whatever placeholder you want — the same one `<ProtectedRoute>` uses for its `isLoading` branch is a good DRY choice. Returning `null` works too, but a "Verifying session…" message is friendlier than a flash of blank.

### What this buys you

| Scenario | Before | After |
|---|---|---|
| User logs in, then F5 on `/dashboard` | Booted to `/login`, has to type credentials again | Sees "Verifying session…" for ~300-800ms, lands back on `/dashboard` |
| User opens a fresh tab while another tab is logged in | Same — forced re-login | IdP cookie is shared across tabs → silent renew restores immediately |
| Cookie expired or user logged out elsewhere | Same — lands on `/login` | Same — `signinSilent` rejects with `login_required`, UI unblocks, `<ProtectedRoute>` redirects |
| `/silent-renew` iframe loads | Recursion (if you forgot the route guard) | Skipped immediately; native handler fires `signinSilentCallback` |

### Validation

A Playwright spec along these lines blocks the regression:

```typescript
test("F5 keeps session via boot-time silent renew", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Dashboard/i })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: /Dashboard/i })).toBeVisible({ timeout: 15_000 });
  await expect(page).not.toHaveURL(/\/login(\?|$)/);
});
```

Run with `E2E_LIVE=1` against the live stack — pure-mock specs can't exercise the IdP cookie path that this recipe relies on.

---

## Recipe — Defense in depth against 401-storm-revokes-session

### What problem this solves

Zitadel has refresh-token rotation with reuse detection enabled by default — the moment two requests use the same RT, Zitadel **revokes the entire session**, invalidating every AT and RT issued under it. Re-login creates a fresh session, but if the underlying root cause persists, a new storm revokes that too → infinite loop where the user can't stay logged in.

Three independent races feed into this cascade:

1. **Concurrent 401 retries**: a dashboard with N parallel queries that all 401 simultaneously each calls `signinSilent` → N RT uses → reuse detected.
2. **Expiring-event vs 401-retry race**: `addAccessTokenExpiring` fires ~60s before token expiry and calls `signinSilent` directly, while a request that already got 401 also calls `signinSilent` via the API client — two callers, same RT.
3. **TanStack Query retry amplification**: a query that fails with 401 retries by default (3× in v5), and each retry hits the same 401 path because the user genuinely needs re-auth, not a retry. N queries × 3 retries = 4× amplification of the storm before the silent-renew machinery even gets started.

A single dedupe at the provider level (`useRef<Promise>` inside the AuthProvider) handles only race #1, leaves #2 and #3 unchecked, and is fragile against test harnesses that mount the provider twice.

The fix is three coordinated layers. Skipping any one of them leaves a known leak path.

### Layer 1 — Dedupe lives in the API client, expose `refreshToken()` public

The `ApiClient` instance owns the in-flight Promise. Both the 401-retry path (internal) and the expiring-event handler (external) go through `apiClient.refreshToken()` — so they coalesce into one `/oauth/v2/token` call regardless of how many concurrent callers there are.

```typescript
class ApiClient {
  private getAccessToken: AccessTokenProvider = () => null;
  private renewSilently: SilentRenewer = async () => null;
  /** Promise da chamada de silent renew em voo. Garante que N callers
   *  concorrentes (request 401 retry, addAccessTokenExpiring handler)
   *  compartilhem uma única chamada ao IdP — evita reuso de RT que faz
   *  Zitadel revogar a sessão. Limpa em `.finally()` da própria Promise. */
  private pendingRenew: Promise<string | null> | null = null;

  setSilentRenewer(renewer: SilentRenewer): void {
    this.renewSilently = renewer;
  }

  /**
   * Dispara silent renew de forma deduplicada. Callers em paralelo
   * compartilham a mesma Promise — uma única chamada a /oauth/v2/token.
   * Resolve com o novo access_token ou `null` se o renew falhar.
   */
  refreshToken(): Promise<string | null> {
    return this.dedupedRenew();
  }

  // ... existing request() with the 401 retry block calling this.dedupedRenew() ...

  private dedupedRenew(): Promise<string | null> {
    if (this.pendingRenew) return this.pendingRenew;
    const promise = this.renewSilently().finally(() => {
      this.pendingRenew = null;
    });
    this.pendingRenew = promise;
    return promise;
  }
}
```

Inside `request`, the 401-retry block calls `this.dedupedRenew()` directly (bypassing the public method to avoid a needless extra hop). External callers (the AuthProvider) call `apiClient.refreshToken()`.

**Why instance field, not module-level**: tests construct fresh `new ApiClient()` instances per `describe` block — module-level state would leak across tests. Instance field also survives if the AuthProvider is mounted twice (rare but possible: Storybook decorators, integration test harnesses).

The provider's `setSilentRenewer` becomes a thin closure with no dedupe of its own:

```typescript
useEffect(() => {
  apiClient.setAccessTokenProvider(() => authRef.current.user?.access_token ?? null);
  apiClient.setSilentRenewer(async (): Promise<string | null> => {
    try {
      const renewed = await authRef.current.signinSilent();
      return renewed?.access_token ?? null;
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn("[auth] silent renew falhou:", err);
      }
      return null;
    }
  });
}, []);
```

The expiring-event handler now goes through `apiClient.refreshToken()` instead of `signinSilent` directly:

```typescript
useEffect(() => {
  const handleExpiring = (): void => {
    void apiClient.refreshToken();
  };
  return auth.events?.addAccessTokenExpiring(handleExpiring);
}, [auth.events]);
```

This is the load-bearing piece: **same Promise** is shared between the proactive expiring path and the reactive 401-retry path, so they coalesce instead of racing.

### Layer 2 — TanStack Query `retry` predicate filters 401

```typescript
import { ApiError } from "@/lib/api/client";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 401 is not transient — the user needs re-auth, not retry. Retrying
      // amplifies the storm by N requests/refresh attempts. Other errors
      // keep 1 retry (2 attempts total — paridade com `retry: 1` anterior;
      // lib default seria 3 mas mantemos o limite anterior).
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status === 401) return false;
        return failureCount < 1;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});
```

Note on TanStack Query semantics: `failureCount` is the predicate's input, evaluated **before** the increment that follows a successful retry decision. So `failureCount < 1` means: 1st failure → predicate sees 0 → `0 < 1` true → retry; 2nd failure → predicate sees 1 → `1 < 1` false → stop. That gives 1 retry / 2 total attempts — same as the old `retry: 1` shorthand. Use `failureCount < 2` for 2 retries, etc. Don't write a comment that says "default retry behavior" — once you supply a predicate there is no implicit default, and the explicit number reads clearly.

### Layer 3 — `apiclient:unauthorized` listener with route guard + state.returnTo

When silent renew fails *after* a 401 (the user is genuinely out of session — IdP cookie expired, session was revoked elsewhere, RT was rotated by another tab and lost), the API client dispatches a `CustomEvent("apiclient:unauthorized")` on `window`. The provider listens and reacts.

```typescript
import { API_UNAUTHORIZED_EVENT } from "@/lib/api/client";

useEffect(() => {
  const handleUnauthorized = (): void => {
    // Em rotas do flow de auth (`/login`, `/auth/callback`, `/silent-renew`)
    // um 401 vindo do apiClient não deve disparar outro `signinRedirect` —
    // o flow já está em curso e disparar de novo é loop.
    if (isAuthRoute()) return;
    // Preserva o path atual via state.returnTo — `<AuthCallback>` lê
    // state.returnTo após o callback e navega de volta.
    const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    void authRef.current.signinRedirect({ state: { returnTo } }).catch(() => {
      /* fallback silencioso — se o redirect falhar, deixa <ProtectedRoute>
         pegar no próximo render via auth.user === null. */
    });
  };
  window.addEventListener(API_UNAUTHORIZED_EVENT, handleUnauthorized);
  return () => window.removeEventListener(API_UNAUTHORIZED_EVENT, handleUnauthorized);
}, []);
```

The `isAuthRoute()` guard is critical: without it, a 401 emitted by `/auth/callback` (audience mismatch, IdP downtime mid-flow) triggers `signinRedirect` → IdP rejects → 401 → redirect → loop. Same helper used in Recipe 1 for the boot-time silent renew works here verbatim.

The `state.returnTo` shape must match what your `<AuthCallback>` reads — typical pattern is `(state as { returnTo?: unknown }).returnTo` after `isSafeReturnTo()` validation. Drift between dispatch and read is silent: the user re-authenticates and lands on `/` instead of where they were.

### What this buys you

| Scenario | Before (only L1 in provider, no L2/L3) | After (all 3 layers) |
|---|---|---|
| Dashboard with 3 parallel queries 401 simultaneously | 3 silent renews → potentially 3 RT uses → revoke | 1 deduped renew, all 3 queries retry with the new token |
| Expiring event fires while a 401-retry is in flight | 2 silent renews via different code paths → revoke | Same Promise, coalesces, 1 RT use |
| Query 401s after silent renew already failed | Retries 3× by default → 3× amplifies the storm | Predicate returns false on 401 → query fails fast |
| Silent renew fails (IdP down mid-flow), 401 from `/auth/callback` | `signinRedirect` loop | Guard early-returns; user sees the broken callback page once, can retry |
| User navigates away, then re-auth | Lands on `/` after callback | Lands back on the original page via `state.returnTo` |

### Validation

A Playwright spec that drives 3 concurrent fetches against an endpoint that 401s once and then 200s catches L1 + L2:

```typescript
test("concurrent 401s deduplicate silent renew (no RT reuse)", async ({ page }) => {
  // Pre-condition: backend has a "force-401-once" middleware (test-only flag).
  // The test triggers 3 parallel queries, all of which 401 first then succeed
  // after a single token refresh.
  let tokenRefreshCalls = 0;
  await page.route("**/oauth/v2/token", async (route) => {
    tokenRefreshCalls++;
    await route.continue();
  });
  await page.goto("/dashboard?force-401-once=1");
  await expect(page.getByRole("heading", { name: /Dashboard/i })).toBeVisible({ timeout: 10_000 });
  expect(tokenRefreshCalls).toBe(1); // not 3
});
```

L3 is harder to test in isolation (requires the IdP cookie to be invalidated mid-session); a manual smoke covers it: invalidate the session via Console (`Sessions → Terminate`) while the SPA is open, then perform any authenticated action — the SPA should redirect to `/login` with the path preserved in `state.returnTo`, and after re-auth land back where you were.

### Why all three layers, not just one

Each layer addresses a different race:

- **L1 alone** (only the dedupe at API client) leaves L2 unblocked: TanStack still retries 401s, multiplying the request volume that hits the dedupe — works correctly but wastes traffic and slows the user-visible recovery.
- **L2 alone** (only the retry filter) leaves L1 unblocked: even without retries, the proactive `addAccessTokenExpiring` event still races the next user-initiated 401-retry.
- **L3 alone** (only the listener) is the catch-all when the other two failed; without L1 + L2, you reach L3 every storm and the user sees `/login` constantly.

The three together make the SPA recover gracefully from a 401 storm whether the cause is transient (network blip), persistent (IdP misconfiguration — see quirk 36 about backend missing `extra_hosts` for the IdP), or downstream (session revoked by another tab).
