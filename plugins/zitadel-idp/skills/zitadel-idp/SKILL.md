---
name: zitadel-idp
description: Self-hosted Zitadel OIDC field guide — bundles working docker-compose, idempotent bootstrap (TS) and reset script, plus 27 documented quirks (FirstInstance, JWT/JWKS over self-signed HTTPS, login UI v1 branding, masterkey-via-flag, post-reset 401 storms, v2.66→v4 upgrade runbook, login UI v2 separate container, API v1→v2 Connect protocol mapping, contextual orgId header→body). Triggers — zitadel, oidc-self-hosted, login UI, silent-renew, JWKS, masterkey, zitadel v4 upgrade, v2.66 to v4, api v1 to v2, connect protocol, login-ui-v2 container, schema migration zitadel.
---

# Zitadel IdP — Field Guide

This skill captures patterns and pitfalls discovered while integrating Zitadel `v4.x` self-hosted as the IdP for the JRC Brasil ERP. It exists to prevent every new project from re-discovering the same eight gotchas the hard way.

**Scope**: Zitadel `v4.x` (latest as of 2026-04) is the default target. v3 differs in a few places (notably no `OrganizationService.AddOrganization` v2 endpoint) — the references flag breaking changes when relevant. **v2.66.x** is also covered for one specific edge case (Quirk 24, masterkey via flag) because legacy stacks still run it; the rest of the skill remains v4-first.

**Out of scope**: Zitadel Cloud (managed), v3 setup, SAML flows, federation IdPs (login with Google/GitHub), Login UI v2 customization. The skill assumes self-hosted, OIDC-only, with the bundled Login UI v1.

## When to use this skill

Read this skill BEFORE you start any of the following — it will save 1-3 hours of debugging on average:

- Drafting a `docker-compose.yml` that includes Zitadel
- Writing a script that programmatically creates Orgs, Projects, Roles, Apps via Management API
- Implementing JWT validation for Zitadel access tokens in any backend (Node/Go/Java/Python)
- Wiring an SPA or mobile app to Zitadel via Auth Code + PKCE
- Diagnosing 401 / 403 / 404 / 400 against Zitadel — including: `Instance not found`, `User with state initial`, `Method Not Allowed`, `Organisation doesn't exist`, `Errors.Instance.Domain.AlreadyExists`, `404 {"code":5,"message":"Not Found"}` na hosted UI, 400 em `/oauth/v2/authorize?prompt=none`, 401 com JWT cujos `iss`/`aud`/`exp` parecem corretos (especialmente atrás de proxy TLS local com cert self-signed), ou 400 `COMMAND-1m88i "No changes"` em bootstrap idempotente
- Wiring an SPA hosted **fora de `localhost`/`127.0.0.1`** (acesso via LAN, IP `.sslip.io`, hostname custom) — exige HTTPS por causa do `crypto.subtle` (PKCE), e o consumer típico de `react-oidc-context` engole a rejeição do `signinRedirect`

If you are merely calling a pre-existing Zitadel deployment from your code, you probably only need `references/token-validation.md` and `references/api-cheatsheet.md`.

## How to use the bundled material

The SKILL.md body intentionally stays short. Drill into the relevant reference based on the immediate task:

| Task | Read |
|------|------|
| Bring up Zitadel locally for the first time | `references/docker-compose-bootstrap.md` + use `assets/docker-compose.zitadel.yml` as starting point |
| Reset a broken local Zitadel | `scripts/reset-zitadel.sh` |
| Programmatically create Org/Project/Roles/App | `references/api-cheatsheet.md` + `assets/bootstrap-zitadel.ts` |
| Validate Zitadel JWT in Node | `references/token-validation.md` |
| Map domain `tenantId` to Zitadel `orgId` | `references/tenant-org-mapping.md` |
| Wire an SPA (React + `react-oidc-context`) — boot-time silent renew, F5 retention, logout flow | `references/spa-recipes.md` |
| Apply org branding to the hosted Login UI v1 (logo, colors, custom texts) | `references/branding.md` |
| Plan a v2.66.x → v4.x upgrade (pre-flight, snapshot, login UI v2 container, validation, rollback) | `references/migration-v2-to-v4.md` |
| Refactor callers from Management API v1 to v2 (Connect protocol, payload diffs, idempotence patterns) | `references/api-v1-to-v2-mapping.md` |
| Hit a confusing error and want a quick lookup | `references/troubleshooting.md` |

The references are designed to be readable in isolation — open the one you need without slogging through the rest.

## The thirty-two quirks (the headline list)

These are the issues that consistently bite first-time Zitadel integrators. Each has a dedicated section in the references; this list is the trigger map so you know which file to open.

1. **`ZITADEL_FIRSTINSTANCE_*` env vars must live on the `zitadel` service, not on `zitadel-init`** — the init container only runs schema migrations; setup (which honors FirstInstance) runs from `start-from-init` on the main service. → `docker-compose-bootstrap.md §1`.

2. **The `/current-dir` volume must be writable by uid 1000** — Zitadel runs as a non-root user. A previous root-owned init leaves the volume unwritable and setup silently fails with `permission denied` in a restart loop. → `docker-compose-bootstrap.md §2`.

3. **`ZITADEL_EXTERNALDOMAIN` is enforced on every request via the `Host` header** — calling `http://127.0.0.1:8080` (the bind port) when external domain is `127.0.0.1.sslip.io` returns `Instance not found`. Node `fetch` does not let you override the `Host` header at runtime — use the URL with the external domain literally. → `docker-compose-bootstrap.md §3`.

4. **`/admin/v1/orgs/_setup` requires a human admin user; use `/zitadel.org.v2.OrganizationService/AddOrganization` to create an org without one** — v2 endpoints accept JSON over Connect protocol. → `api-cheatsheet.md §"Create org"`.

5. **`AddHumanUserRequest` requires `userName` and `profile.firstName`/`lastName` (not `givenName`/`familyName`)** — payload shape changed across versions; v4 also rejects `clockSkew > 5s` on OIDC apps. → `api-cheatsheet.md §"Create human user"` + `§"Create OIDC app"`.

6. **Users created without `initialPassword` enter state `initial` and cannot be `_deactivate`d** — Zitadel rejects with `COMMAND-ke0fw`. In production the user exits this state by completing invite; in tests/seeds set an `initialPassword`. → `troubleshooting.md`.

7. **Domain `tenantId` (stable string like `JRC`) ≠ Zitadel `orgId` (numeric like `370503937624637443`)** — every Management API call needs the numeric `orgId` in `x-zitadel-orgid`. Build a translation layer in your adapter. → `tenant-org-mapping.md`.

8. **User grants search is at `/management/v1/users/grants/_search` (global, filter by `userIdQuery`), not `/management/v1/users/{id}/grants/_search`** — the latter returns `405 Method Not Allowed`. assignRole / revokeRole should be implemented as search-then-PUT/DELETE for idempotency, not POST a fresh grant each time. → `api-cheatsheet.md §"User grants"`.

9. **`loginV2.required=true` is the default instance feature flag in Zitadel ≥ v3, but Login UI v2 is a separate Next.js app you must deploy yourself** — without it, every `/oauth/v2/authorize` redirects to `/ui/v2/login/login` and returns `{"code":5,"message":"Not Found"}`. App-level `loginVersion: {loginV1: {}}` alone does NOT override the instance flag — you must `PUT /v2/features/instance {loginV2: {required: false}}` or deploy v2. → `troubleshooting.md`.

10. **Silent-renew redirect URI must be in the OIDC app's `redirectUris`** — most bootstrap scripts only register `/auth/callback`. Without `/silent-renew`, every `prompt=none` request returns `400` and the SPA loops forever in "verifying session…". Add it at bootstrap time, not after the first failure. → `troubleshooting.md` + `api-cheatsheet.md §"Create OIDC application"`.

11. **JWT access tokens DO NOT carry profile claims** (`name`, `preferred_username`, `email`, `urn:zitadel:iam:org:id`) — those live in the id_token and `/oidc/v1/userinfo` only. Backend mappers that hard-require them silently 401 every request with "Token inválido" even when `iss`/`aud`/`exp` are perfect. Always fall back to `sub` for operatorName and `defaultTenant` for tenantId. → `token-validation.md §"Access token vs ID token"`.

12. **Node backends fetching JWKS over HTTPS with a self-signed cert (mkcert/dev CA) need `NODE_EXTRA_CA_CERTS`** — `createRemoteJWKSet(new URL(jwksUrl))` does a normal Node `fetch`, which uses the OS trust store. With a local CA, the TLS handshake fails before signature check; jose surfaces it as a generic verification error. **Symptom**: 100% of `/api` requests return 401, JWT decoded by hand looks perfect, SPA falls into a silent-renew loop and rate-limit (429) follows. → `token-validation.md §"Trusting a self-signed JWKS endpoint"` + `troubleshooting.md §"401 storm with apparently-valid JWT"`.

13. **Zitadel volume reset (`down -v` / `--reset-zitadel`) regenerates `projectId` and `clientId`** — any backend env (`AUTH_AUDIENCE`/`OIDC_AUDIENCE`/`VITE_OIDC_CLIENT_ID`) cached from a previous bootstrap goes stale silently. Same 401-storm symptom as quirk 12, no clear error. Fix: re-derive from `bootstrap.json` on every boot, never hardcode. → `api-cheatsheet.md §"Re-reading bootstrap output after volume reset"` + `troubleshooting.md §"401 storm with apparently-valid JWT"`.

14. **`PUT /management/v1/projects/{p}/apps/{a}/oidc_config` returns `400 COMMAND-1m88i "No changes"` when the body matches current state** — idempotent bootstrap scripts that always PUT the OIDC config crash on second run unless they catch this code. → `api-cheatsheet.md §"Create OIDC application"` + `assets/bootstrap-zitadel.ts` (idempotent template).

15. **Running Zitadel behind a TLS-terminating reverse proxy (Caddy/NGINX/Traefik) requires THREE settings, not two** — `ZITADEL_EXTERNALSECURE=true` + `ZITADEL_TLS_ENABLED=false` + the start flag `--tlsMode external`. Without `--tlsMode external` the binary still tries to bind a TLS listener on its internal port and refuses traffic. → `docker-compose-bootstrap.md §"TLS terminated by reverse proxy"`.

16. **Browsers expose `crypto.subtle` (used by PKCE in oidc-client-ts) only in secure contexts — `localhost`/`127.0.0.1` are the only HTTP exceptions** — accessing the SPA via LAN IP / `.sslip.io` / custom hostname over HTTP makes `signinRedirect()` throw. `react-oidc-context` callers typically `void` the promise, so the failure is silent — clicking "Entrar" produces no console error, no navigation, no network request. Fix: serve everything via HTTPS even for dev/LAN testing (mkcert + reverse proxy). → `troubleshooting.md §"Entrar / Login button does nothing"`.

17. **F5 with `InMemoryWebStorage` requires a boot-time `signinSilent` — and `<AuthProvider>` wrapping the silent-renew route makes that recursive** — `automaticSilentRenew` only fires on `accessTokenExpiring`, which needs an existing `User`; in-memory storage has no `User` after F5, so the lib never recovers the session even with the IdP cookie alive. The fix is an active `auth.signinSilent()` at boot — but if your provider mounts above the `<Routes>` tree, the iframe loads `/silent-renew`, re-mounts the provider, fires another `signinSilent`, and the parent Promise never settles. **Symptom**: SPA stuck on "Verifying session…" indefinitely with no IdP-side error. Fix requires three guards (route check, iframe check, ref-gated useEffect) and a watchdog `setTimeout` — and crucially, no closure-scoped `cancelled` flag, because StrictMode flips it before the Promise resolves. → `spa-recipes.md §"Recipe 1"` + `troubleshooting.md §"SPA stuck on Verifying session…"`.

18. **`post_logout_redirect_uri` is byte-matched just like `redirect_uri`** — registering `${WEB_BASE}/` while the SPA sends `${WEB_BASE}/login` (a common drift introduced when the SPA's `VITE_OIDC_POST_LOGOUT_REDIRECT_URI` is set to `/login` for UX but the bootstrap registered just the root) makes Zitadel respond with `{"error":"invalid_request","error_description":"post_logout_redirect_uri invalid"}` and the user is stranded. Trailing slash, scheme, and port all matter. Fix: register both URIs the SPA might send, comma-joined: `${WEB_BASE}/login,${WEB_BASE}/`. → `troubleshooting.md §"Logout returns post_logout_redirect_uri invalid"`.

19. **Branding aplicado na org não pinta a Login UI sem `privateLabelingSetting` no projeto** — `POST /management/v1/policies/label` + `_activate` na org JRC retorna 200, GET subsequente confirma `primaryColor: "#ed1c24"`, mas browser em `/ui/login/login` continua azul Zitadel default `#5469d4`. Causa: Zitadel só usa a label policy da org dona do projeto se este tiver `PRIVATE_LABELING_SETTING_ENFORCE_PROJECT_RESOURCE_OWNER_POLICY`. O default `_UNSPECIFIED` cai pra label policy da instância. Fix: setar o flag no payload do `POST/PUT /management/v1/projects/{p}` e checar via GET. → `branding.md §"Quirk 19"`.

20. **POST vs PUT na primeira label policy + dois error IDs distintos pra "no-op"** — `PUT /management/v1/policies/label` quando `policy.isDefault === true` retorna `404 "Private Label Policy not found (Org-0K9dq)"` (precisa POST primeiro pra criar override). Re-runs do bootstrap idempotente disparam `400 "Private Label Policy has not been changed (Org-8nfSr)"` — diferente do `COMMAND-1m88i` genérico (quirk 14). Bootstrap deve: GET prévio → ramificar por `isDefault` → tratar **ambos** error IDs como no-op. → `branding.md §"Quirk 20"`.

21. **Path de assets em Zitadel v4 mudou para `/assets/v1/org/policy/label/...`** — singular `org`, sem `s/me`. O path `/assets/v1/orgs/me/policy/label/logo` que aparece em docs/exemplos antigos do Zitadel v1/v2/v3 retorna **HTTP 405 Method Not Allowed** em v4. Confunde porque parece "endpoint existe mas método errado" — na verdade existe em outro path. Endpoints corretos: `logo`, `logo/dark`, `icon`, `font`. Header `x-zitadel-orgid` continua obrigatório. Multipart com field name `file`. → `branding.md §"Quirk 21"`.

22. **Custom login text usa `/management/v1/text/login/{lang}`, e Zitadel só aceita códigos curtos** — não `/policies/custom_login_text/{lang}` (path antigo, retorna 404). E só aceita `pt`, `en`, `de` etc. — `pt-BR` retorna `400 LANG-lg4DP "Language is not supported"`. Resolução de Accept-Language `pt-BR → pt` é feita server-side. PUT é mergeable: campos não enviados preservam i18n default; pra zerar um campo mande string vazia explícita. → `branding.md §"Quirk 22"`.

23. **Refatoração single-app → multi-app YAML: env vars do `dev.sh` precisam DOMINAR o YAML** — quando você evolui o bootstrap pra ler `applications[].redirectUris` declarativos do YAML, o YAML naturalmente lista hosts canônicos (`localhost:5173`, `app.example.com`). Mas dev workflows com LAN HTTPS (mkcert + proxy reverso, host dinâmico via IP `.sslip.io`) populam `OIDC_REDIRECT_URIS=https://<ip-da-lan>.sslip.io:5443/auth/callback,...` — host que muda a cada IP, **nunca está no YAML**. Se YAML wins, dev login bate em `{"error":"invalid_request","error_description":"The requested redirect_uri is missing in the client configuration"}` no callback do Zitadel. Família dos quirks 10 (silent-renew em redirectUris) e 18 (byte-match), mas o gatilho é diferente: **regressão de refatoração**, não config inicial. Fix canônico: precedência **env > YAML > hardcoded fallback** — env do `dev.sh` (quando setada explicitamente) domina; YAML é fallback de produção (onde env unset, hosts são canônicos). → `troubleshooting.md §"redirect_uri missing in client configuration after multi-app refactor"`.

24. **Zitadel v2.66.x `start-from-init`: env-var `ZITADEL_MASTERKEY` não é lida com confiabilidade — passe via flag CLI** — em v2.66.10 (e potencialmente outras patches da linha 2.66) o subcomando `start-from-init` falha com `panic: No master key provided ... masterkey must either be provided by file path, value or environment variable` mesmo quando `ZITADEL_MASTERKEY` está injetada corretamente no container (validável via `docker inspect <ctr> --format '{{range .Config.Env}}{{println .}}{{end}}'` — 32 chars exatos, sem CR, sem leading whitespace, sem null bytes). Em v4.x o fallback `os.Getenv` funciona; em v2.66 não. **Sintoma**: container em loop de restart com `RestartCount` crescendo, exit 2, e o panic acima a cada ciclo (~60s, devido ao retry policy). Fix canônico: passar `--masterkey ${ZITADEL_MASTERKEY}` no `command:` do compose (a flag tem precedência sobre env). Trade-off: a flag aparece em `docker inspect` e `ps aux`, então o `.env` precisa ser `chmod 600` e o host dedicado/de confiança. Se isso virar problema, migrar para `--masterkeyFile /run/secrets/zitadel_masterkey` + Docker secret. → `docker-compose-bootstrap.md §"Quirk 24 — masterkey via flag em v2.66.x"`.

25. **Login UI v2 em v4 é um container Next.js separado** — diferente de Login UI v1, que vive embutida no binário do Zitadel em `/ui/login/`, a Login UI v2 (`/ui/v2/login`) é servida pela imagem `ghcr.io/zitadel/zitadel-login`. Em v3+ o instance flag `loginV2.required` default é `true` — o `signinRedirect` da SPA cai em `/ui/v2/login` por padrão, e se você só tem o container `zitadel` no compose recebe `404 {"code":5,"message":"Not Found"}`. Duas saídas: (A) deploy do container `zitadel-login` + reverse proxy roteando `/ui/v2/login` → `zitadel-login:3000` e tudo o mais → `zitadel:8080`; (B) `PUT /v2/features/instance {"loginV2":{"required":false}}` e seguir com Login UI v1 indefinidamente. Escolha uma — oscilar entre as duas sem pensar gera 404 esporádicos. → `migration-v2-to-v4.md §3.2-3.3` + `docker-compose-bootstrap.md §8`.

26. **Idempotência em v2 via IDs determinísticos em vez de search-then-create** — em v1 o padrão idiomático era `POST /resource/_search` filtrando por nome → se 0 hits, `POST /resource` (Zitadel gera o ID). Em v2 você pode passar seu próprio `userId`/`applicationId`/`projectId` no body; tentar criar com ID já existente retorna `ALREADY_EXISTS`, que você trata como sucesso. Resultado: 1 round-trip em vez de 2 por recurso. Vale a pena para bootstraps multi-app (5 apps × 2 round-trips × N boots = ruído mensurável em hot-deploy). Pra recursos com nome humano-legível e sem ID estável (`org "JRC"`, `project "ERP-JRC"`), o padrão search-then-create v1 continua válido em v2 também. → `api-v1-to-v2-mapping.md §5`.

27. **Contextual `orgId` mudou de header para body em v2** — v1 exigia `x-zitadel-orgid: 379...` em todo call org-scoped. v2 coloca o equivalente no body, geralmente como `organizationId` (às vezes nested em `org.id` ou `resourceOwner`). Modo de falha mais comum em refactor: dropar o header e esquecer de adicionar o campo no body — symptom é `INVALID_ARGUMENT: missing organization_id`. O header é **inofensivo em calls v2** (ignorado), então durante a transição você pode manter o header setado globalmente no HTTP client sem quebrar nada. → `api-v1-to-v2-mapping.md §3`.

28. **Login UI v2 auto-provisioning is broken in v4.15.0** — the FirstInstance envs that should auto-create the `IAM_LOGIN_CLIENT` service user + write its PAT to a shared volume don't work in v4.15. Two failure modes, no winner: **(A)** setting only `ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH` is a no-op — the server has no service user to create, so the volume stays empty and the `zitadel-login` container loops on stderr `ZITADEL_SERVICE_USER_TOKEN_FILE=/login-client/login-client.pat is set. Awaiting file and reading token.` indefinitely; `/ui/v2/login` returns 404. **(B)** adding the `ZITADEL_FIRSTINSTANCE_ORG_LOGINCLIENT_MACHINE_USERNAME` / `MACHINE_NAME` / `PAT_EXPIRATIONDATE` envs to actually provision the service user causes setup migration `03_default_instance` to fail with `Errors.Instance.Domain.AlreadyExists` / `unique_constraints_pkey` (instance domain reserved twice — Human admin + LoginClient race). Container enters restart loop and never becomes healthy. Tracked in zitadel/zitadel#8910 and #9293; partial fix in PR #10518 may not be in every v4.x patch. **Pragmatic mitigations**: (1) **Path B of Quirk 25** — `PUT /v2/features/instance {"loginV2":{"required":false}}` and pin OIDC apps with `loginVersion: { loginV1: {} }`. Login UI v1 stays default with branding intact via label policy. The `zitadel-login` container can stay deployed (idle, looping benignly) so promoting it is a single config flip when upstream stabilizes. (2) **Provision in bootstrap** — after Zitadel is healthy, your bootstrap creates the machine user `login-client` + role `IAM_LOGIN_CLIENT` + PAT via the regular UserService/AuthorizationService API, then writes the PAT to a bind-mounted file the `zitadel-login` container reads. More work but independent of upstream. → `troubleshooting.md §"zitadel-login: Awaiting file and reading token (forever)"` + `migration-v2-to-v4.md §3.4`.

29. **OIDC `client_id` is the numeric `clientId` from `oidcConfiguration`, NOT the deterministic `applicationId` UUID you supplied** — even when you pass your own `applicationId` (UUID v7) in `CreateApplicationRequest` for idempotency, Zitadel auto-generates a *separate* numeric `clientId` (e.g. `371898282416275459`) for OAuth/OIDC. The `applicationId` is the resource handle for v2 APIs (`UpdateApplication`, `GetApplication`, `DeleteApplication`); the `clientId` is what `/oauth/v2/authorize?client_id=…` requires. Frontend `VITE_OIDC_CLIENT_ID` MUST be the numeric value. **Symptom**: OIDC authorize returns `400 invalid_request "Errors.App.NotFound"` with the UUID; SPA login fails right after a clean cutover even though the bootstrap log shows `[app] created appId=<uuid>`. **Fix in CD**: bootstrap output exposes both (`appId=… clientId=…`); a CD step extracts the numeric `clientId` from `oidcConfiguration` of the bootstrap response and overwrites `VITE_OIDC_CLIENT_ID` (image-rebuild required — VITE_* are baked at build time). Backend `AUTH_AUDIENCE` for JWT validation can be the deterministic `projectId` (it appears in the JWT `aud` claim alongside the clientId). → `troubleshooting.md §"OIDC client_id mismatch — Errors.App.NotFound"`.

30. **`ZITADEL_BOOTSTRAP_ENV`-style env that picks dev-vs-prod deterministic IDs from YAML must be set explicitly in CD — silent default to `dev` is a footgun** — when your bootstrap script has `applications[].ids.dev` and `applications[].ids.prod` blocks and selects between them via `process.env.ZITADEL_BOOTSTRAP_ENV ?? 'dev'`, a CD pipeline that doesn't set the env creates prod entities with **dev IDs**. The frontend secret has prod IDs, so the SPA's `client_id` doesn't match anything in the IdP — same `Errors.App.NotFound` symptom as Quirk 29 but with a different root cause and trickier fix (already-created entities have wrong IDs and must be wiped + recreated). **Mitigations**: (1) require the env at script start, throw on undefined rather than defaulting; (2) set `ZITADEL_BOOTSTRAP_ENV: prod` (or equivalent) explicitly on the bootstrap container in `docker-compose.prod.yml`; (3) document the env in the runbook. → `troubleshooting.md §"Wrong-environment IDs in prod IdP"`.

31. **`ZITADEL_DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED=false` at FirstInstance time breaks the chicken-and-egg of Quirks 25 + 28 in CD cutovers** — when the upstream Login UI v2 auto-provisioning bug (Quirk 28) blocks `/ui/v2/login`, *and* the operator can't login to the console to create the IAM_OWNER PAT manually because the OIDC redirect to `/ui/v2/login` 404s — the cleanest break is to set the feature flag in **DefaultInstance** config (env on the `zitadel` server) so the instance is born with `loginV2.required=false` from boot zero. The OIDC authorize endpoint then redirects to `/ui/login` (v1, embedded in the binary) immediately, no PAT required. Bootstrap's `PUT /v2/features/instance` call against the same flag becomes a no-op idempotency check. **Why this is better than waiting for bootstrap to flip the flag**: bootstrap needs a PAT, PAT requires console login, console login redirects to broken `/ui/v2/login` → without DefaultInstance pre-config, you're stuck. With it, the loop opens at the right place. → `docker-compose-bootstrap.md §"DefaultInstance feature flags pre-config"`.

32. **nginx-proxy: when 2 containers share a `VIRTUAL_HOST` and one declares `VIRTUAL_PATH` while the other doesn't, the no-`VIRTUAL_PATH` container is silently ignored** — only the more-specific path-route is registered in the generated `nginx.conf`. Every request that doesn't match the prefix returns 404 (e.g., `/.well-known/openid-configuration`, `/oauth/v2/*`, `/ui/console`). Symptom in nginx logs: trailing `"-"` upstream means no route was matched. Fix: declare `VIRTUAL_PATH=/` + `VIRTUAL_DEST=/` on the "default" container (the one serving root) so nginx-proxy registers it as a less-specific location alongside the prefix-routed sibling. Discovered when adding the `zitadel-login` container (`VIRTUAL_PATH=/ui/v2/login`) to an `idp.jrcbrasil.com` host that previously had only `zitadel` (no VIRTUAL_PATH). Applies to any nginx-proxy split (e.g., API + admin UI on same host). → `docker-compose-bootstrap.md §"nginx-proxy: split VIRTUAL_HOST + VIRTUAL_PATH"`.

## Migration v2.66 → v4 + API v2

When upgrading from v2.66.x to v4.x and refactoring callers from API v1 to v2:

- **Start with the runbook** in `references/migration-v2-to-v4.md` — pre-flight (Postgres required since v3, advisory A10015), upgrade path (direct v2.66 → v4 OK if Postgres in place — no v3 stop), schema migration runs automatically in the v4 image's `setup` phase, validation matrix, rollback.
- **Use the mapping table** in `references/api-v1-to-v2-mapping.md` — covers all 15 v2 services (Organization, Project, Application, User, Authorization, Action, Feature, Settings, OIDC, IDP, Group, SAML, Session, WebKey, Instance), payload diffs (`firstName/lastName` → `givenName/familyName`, `userName` → `username`, `email.isEmailVerified` → `email.isVerified`, language `pt-BR` → `pt`), and idempotence patterns.
- **Login UI v2 is a separate container** — see Quirk 25 above. Reverse proxy must route `/ui/v2/login` to `zitadel-login:3000`, everything else (including OIDC discovery, OAuth, JWKS) to `zitadel:8080`. Path B (sticking with Login UI v1) is supported — Login UI v1 keeps working at `/ui/login/` indefinitely.
- **Bootstrap idempotence in v2 differs** (Quirk 26) — deterministic IDs in body replace `_search`-then-create round-trip. Existing v1-shaped bootstrap scripts keep working in v4; refactor only when there's a reason.
- **Connect protocol auth is unchanged**: same `Authorization: Bearer <PAT>` header. JSON variant uses `Content-Type: application/json`. Binary variant uses `application/connect+proto` (only if you have a generated client).

## Implementation flow (suggested order)

For a fresh project, this sequence avoids most reordering:

1. Copy `assets/docker-compose.zitadel.yml` and adjust ports / external domain. Read `docker-compose-bootstrap.md §1-3` first — the env layout is non-obvious.
2. `docker compose up -d`, wait for healthy, verify the PAT was written to `<volume>/admin.pat`. If not, see troubleshooting.
3. Copy `assets/bootstrap-zitadel.ts` and run it to create your Org/Project/Roles/App. The script is idempotent — re-runs are safe.
4. Capture the `projectId` and `clientId` from the output JSON. These become `OIDC_AUDIENCE` and the SPA's client_id respectively.
5. In your backend, wire JWT validation per `token-validation.md`. The audience must equal the `projectId`, NOT the `clientId`.
6. In your SPA, configure Auth Code + PKCE pointing at `http://<external-domain>/.well-known/openid-configuration`.
7. Test login end-to-end. If anything 4xx's, jump straight to `troubleshooting.md`.

## What this skill explicitly does NOT cover

- Production hardening (TLS, masterkey rotation, Postgres backup, SMTP) — these are real concerns but vary by environment. Quick pointer: terminate TLS at NGINX/Caddy/Traefik and set `ZITADEL_EXTERNALSECURE=true` + `ZITADEL_TLS_ENABLED=false` + start flag `--tlsMode external` (full triad — see `docker-compose-bootstrap.md §"TLS terminated by reverse proxy"`, quirk 15). Backup the Zitadel Postgres database like any other Postgres.
- v3 → v4 migration. Greenfield projects should start on v4. The skill covers v2.66 → v4 (the supported direct hop when Postgres is already in place — see `migration-v2-to-v4.md`), not v3 as an intermediate stop.
- Federation, SAML, SCIM, Actions, Webhooks. Add them when needed — they are mostly straight reads of the docs once Zitadel is bootstrapped correctly.

## Source of truth

- Local lessons: `docs/zitadel-reference.md §10` (this project's deep-dive).
- Upstream docs: <https://zitadel.com/docs> and the steps file at <https://github.com/zitadel/zitadel/blob/main/cmd/setup/steps.yaml>.
- Working bootstrap reference: `packages/idp/scripts/bootstrap-zitadel.ts` in this project.

When the references in this skill diverge from upstream, trust the upstream docs but raise a note — Zitadel evolves quickly and these references will drift.
