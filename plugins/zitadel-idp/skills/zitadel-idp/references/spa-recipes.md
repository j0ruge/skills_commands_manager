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
