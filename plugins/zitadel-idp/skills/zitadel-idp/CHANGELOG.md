# Changelog — `.claude/skills/zitadel-idp`

Lessons retrofitted into the skill, dated. Each entry describes **what** changed and **why** (the symptom it would have prevented).

## 2026-05-06 — Migration v2.66 → v4 + API v1 → v2 playbook (3 quirks + 2 references) — bump 0.2.1 → 0.3.0

Source: projeto `validade_bateria_estoque`, missão "Zitadel v2.66.10 → v4.15.0 + API v2 (Connect protocol)" (memory: "Feature 006 pending"; prod travado por mismatch entre script bootstrap v4-shaped e instância pinned em v2.66.10 — login end-to-end bloqueado em produção). A skill atual cobria v4 muito bem (24 quirks) e v2.66.x num único quirk (#24, masterkey), mas tinha duas lacunas críticas pra missão de upgrade: (a) **nenhum runbook operacional** de como fazer o jump v2.66 → v4 (snapshot, schema migration, login-UI split, validation, rollback), e (b) **mapping API v1→v2 só implícito** — espalhado em comentários e quirks isolados, sem tabela única que cubra as 13 chamadas v1 do bootstrap real. Skill nesta release ganha as duas references novas + 3 quirks pra os modos de falha mais traiçoeiros do upgrade (Login UI v2 como container separado, idempotência via deterministic IDs, orgId header→body).

### Adicionado

- **L25 — Login UI v2 separate Next.js container** (`SKILL.md` quirk 25, `references/docker-compose-bootstrap.md` §8 nova "Compose v4: login-container + nginx routing", `references/migration-v2-to-v4.md` §3.2-3.3, `references/troubleshooting.md` §"Post-upgrade errors" entry "404 Not Found on /ui/v2/login").
  *Sintoma evitado*: pós-upgrade pra v4, SPA redireciona pra `https://idp/ui/v2/login` e recebe `404 {"code":5,"message":"Not Found"}`. Em v2.66 a Login UI v1 vinha embutida no binário; em v4 a Login UI v2 saiu pra container separado (`ghcr.io/zitadel/zitadel-login`). Reverse proxy precisa rotear `/ui/v2/login` (Prefix) → `zitadel-login:3000`, todo o resto → `zitadel:8080`. Path B alternativo: `PUT /v2/features/instance {"loginV2":{"required":false}}` e seguir com Login UI v1 indefinidamente. Skill agora tem snippet compose pronto, snippet nginx + Caddy, validation cURL, e documenta a env nova `ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH` que provisiona o PAT do IAM_LOGIN_CLIENT (precisa estar no compose ANTES do primeiro boot — adicionar depois exige `down -v`).

- **L26 — API v2 idempotence via deterministic IDs** (`SKILL.md` quirk 26, `references/api-v1-to-v2-mapping.md` §5 "Idempotence patterns").
  *Sintoma evitado*: bootstrap v2-shaped fazendo round-trip `_search` antes de cada create, mantendo o mesmo número de chamadas que a v1 (overhead em multi-app boot). Em v2 você pode passar seu próprio `userId`/`applicationId`/`projectId` no body; tentar criar com ID já existente retorna `ALREADY_EXISTS`, que você trata como sucesso → 1 round-trip em vez de 2 por recurso. Pra recursos com nome humano-legível e sem ID estável (`org "JRC"`, `project "ERP-JRC"`), search-then-create v1 continua válido em v2 também. Skill explica quando aplicar cada padrão e dá exemplo TypeScript completo.

- **L27 — Contextual `orgId` moved from header (`x-zitadel-orgid`) to body (`organizationId`)** (`SKILL.md` quirk 27, `references/api-v1-to-v2-mapping.md` §3 "Contextual info", `references/troubleshooting.md` §"Post-upgrade errors" entry "Bootstrap fails with INVALID_ARGUMENT: missing organization_id").
  *Sintoma evitado*: refactor parcial v1→v2 onde alguém dropa o header global `x-zitadel-orgid` mas esquece de adicionar `organizationId` no body do call v2 — modo de falha tipicamente silencioso (header é ignorado em v2, então quem só leu doc não fica claro o que mudou). Sintoma é `INVALID_ARGUMENT: missing organization_id` (ou per-resource equivalent) só nos calls refatorados, enquanto v1 calls no mesmo script continuam funcionando. Skill agora documenta que o header é **inofensivo em v2** — pode manter setado globalmente no HTTP client durante a transição.

- **NOVO `references/migration-v2-to-v4.md`** — runbook completo de upgrade self-hosted: §1 pre-flight checklist (Postgres 14+, masterkey, snapshot, env triad, inventário de callers v1, maintenance window), §2 upgrade path (direct v2.66 → v4 OK quando Postgres já em uso — advisory A10015 satisfeita; sem v3 stop), §3 step-by-step (snapshot, update compose com novo container `zitadel-login`, reverse-proxy routing, boot, smoke test 4 cURL, re-run bootstrap idempotente, app-level smoke), §4 validation matrix (8 sintomas × causas × fixes), §5 rollback (restore from snapshot — não há in-place downgrade), §6 features novas que ficam disponíveis pós-upgrade (Login UI v2, Connect protocol, AuthorizationService, /v2/users/human REST), §7 ponteiros pra references vizinhas.

- **NOVO `references/api-v1-to-v2-mapping.md`** — mapping table cobrindo as 13 chamadas v1 reais do `bootstrap-zitadel.ts` do projeto JRC (Organization, Project, Application, User, Authorization, Settings, Action, Feature services). §1 path prefixes (Connect JSON / binary, REST `/v2/`, legacy v1, OIDC standards), §2 service mapping com 19 linhas (v1 → v2 service → v2 path), §3 contextual info header→body (Quirk 27 explained), §4 body-shape changes (`firstName/lastName` → `givenName/familyName`, `userName` → `username`, `email.isEmailVerified` → `email.isVerified`, `pt-BR` → `pt`, `apps/oidc` → `CreateApplication` com discriminator + nested `oidc` config), §5 idempotence patterns (deterministic IDs vs search-then-create), §6 lista do que ainda é v1-only em v4.15 (`SystemService`, alguns reads avançados), §7 auth unchanged, §8 migration checklist per-caller, §9 ponteiros.

### Mudado

- `SKILL.md` headline "the twenty-four quirks" → **"the twenty-seven quirks"**; `description` do frontmatter expandida com triggers novos (`zitadel v4 upgrade`, `v2.66 to v4`, `api v1 to v2`, `connect protocol`, `login-ui-v2 container`, `schema migration zitadel`); nova seção "Migration v2.66 → v4 + API v2" (logo após "Implementation flow"); seção "What this skill does NOT cover" agora aponta `migration-v2-to-v4.md` em vez de simplesmente listar v3→v4 como out-of-scope (caminho v2.66→v4 está coberto). Tabela "How to use the bundled material" ganha 2 linhas novas (planning upgrade + refactoring v1→v2).
- `references/api-cheatsheet.md` — intro nova logo no topo direcionando código novo pra `api-v1-to-v2-mapping.md` (ainda mantém os snippets v1 pra paste-able cURL e idempotência conhecida); seção "v3 → v4 breaking changes" agora aponta `migration-v2-to-v4.md §2`; nova seção "v2.66 → v4 upgrade?" curta no fim, redirecionando upgrade work pra runbook.
- `references/docker-compose-bootstrap.md` — nova §8 "Compose v4: login-container + nginx routing (Quirk 25)" com compose mínimo completo (zitadel + zitadel-login + postgres healthcheck), nginx + Caddy snippets, smoke cURL, e detalhe sobre `ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH` (precisa estar no compose ANTES do primeiro boot); §"Where to go next" renumerada pra §9 e ganha ponteiros pra `migration-v2-to-v4.md` + `api-v1-to-v2-mapping.md`.
- `references/troubleshooting.md` — nova seção "Post-upgrade errors (v2.66 → v4)" com 5 entries (404 em /ui/v2/login, 401 storm pós-upgrade por JWKS rotation, setup hang > 5min, branding sumiu, INVALID_ARGUMENT missing organization_id em refactor parcial). Cada entry com sintoma + causa + fix + ponteiros pras quirks vizinhas (12, 13, 19, 21, 25, 27).
- `assets/bootstrap-zitadel.ts` — comentários `// v2 equivalent: POST /zitadel.<svc>.v2.<Method>` ao lado de cada uma das 6 chamadas v1 funcionais do template (`findOrg`, `findProject`, `ensureProject`, `ensureRoles` com 2 endpoints, `findApp`, `ensureApp`). Sem refator funcional — quem usa o template pra v2.66 segue valendo; quem migrar pra v2 tem o mapping inline.

### Não mudado / fora de escopo

- Reescrever `bootstrap-zitadel.ts` do projeto `validade_bateria_estoque` para API v2 — responsabilidade da spec da feature 006, separada deste retrofit.
- Mudar `infra/docker/docker-compose.prod.yml` do projeto de v2.66 para v4 — PR separado, gated por testes; este retrofit só fornece o playbook.
- Cobertura de SAML / SCIM / Federation — continua out-of-scope da skill (decisão consciente desde a v0.1.0).
- Test cases / evals automatizados pra skill — sem evals hoje; iteração futura se o usuário pedir.
- `references/spa-recipes.md`, `references/tenant-org-mapping.md`, `references/token-validation.md`, `references/branding.md` — sem mudança nesta release. OIDC/OAuth endpoints (`/oauth/v2/*`, `/oidc/v1/userinfo`, `/.well-known/openid-configuration`) **não mudam** entre v2.66 e v4, então o SPA + JWT validation code continua valendo idêntico após o upgrade.

### Verificação

```bash
grep -rn "v2.66.*v4\|migration-v2-to-v4\|api-v1-to-v2-mapping\|zitadel-login\|loginV2.*container\|organizationId.*body\|ALREADY_EXISTS.*deterministic" \
  plugins/zitadel-idp/skills/zitadel-idp/
```

Esperado: ≥1 hit em cada termo, distribuídos por SKILL.md, references/migration-v2-to-v4.md, references/api-v1-to-v2-mapping.md, references/docker-compose-bootstrap.md §8, references/troubleshooting.md, references/api-cheatsheet.md, e assets/bootstrap-zitadel.ts.

Bump consistente em 3 lugares:

- `plugins/zitadel-idp/.claude-plugin/plugin.json` → `"version": "0.3.0"`
- `.claude-plugin/marketplace.json` linha `zitadel-idp` → `"version": "0.3.0"`
- `README.md` raiz tabela "Available Plugins" → `0.3.0` + count "27 quirks"

---

## 2026-05-05 — Zitadel v2.66.x masterkey via flag CLI (1 lição) — bump 0.1.0 → 0.2.0

Source: feature 005-production-deploy bootstrap em VPS de produção. Stack rodando `ghcr.io/zitadel/zitadel:v2.66.10` entrou em loop de restart com `panic: No master key provided` (exit 2, RestartCount=135 antes do diagnóstico). Verificação cruzada confirmou que `ZITADEL_MASTERKEY` estava corretamente injetada no container (32 chars exatos, sem CR/whitespace/null bytes, validado via `docker inspect | xxd`), e mesmo assim `start-from-init` ignorava a env. Em v4.x — coberto pelo grosso da skill — o fallback `os.Getenv` funciona; em v2.66.x não. Skill estava silenciosa sobre v2.x e o asset `docker-compose.zitadel.yml` por acidente já usa `--masterkey ${...}` no `command:` (legado de iteração anterior), mas não documentava **por quê** isso é obrigatório em v2.66 — ficava como "convenção". 1h+ de debug perdido investigando volume permissions, bytes da env, encoding, antes de cair na ficha.

### Adicionado

- **L23 — Zitadel v2.66.x: env-var `ZITADEL_MASTERKEY` não é lida com confiabilidade pelo `start-from-init`; passar via flag CLI** (`SKILL.md` quirk 24, `references/docker-compose-bootstrap.md` novo §"Quirk 24 — masterkey via flag em v2.66.x").
  *Sintoma evitado*: container Zitadel em loop de restart com `panic: No master key provided / masterkey must either be provided by file path, value or environment variable`, exit code 2 a cada ~60s, mensagem idêntica a cada ciclo. `docker inspect` mostra a env presente e correta, `docker compose config` resolve o literal — mas o panic continua. Causa raiz no path cobra/viper de v2.66 (em v4 foi reescrito). Fix canônico: flag CLI tem precedência sobre env, então `command: [start-from-init, --masterkey, ${ZITADEL_MASTERKEY}, --tlsMode, external]`. Trade-off documentado: flag aparece em `docker inspect` e `ps aux`, então `.env` chmod 600 + VPS dedicado; se não for o caso, migrar para `--masterkeyFile` + Docker secret. Prevenção: `docker logs <ctr> --tail 5` logo após primeiro `up -d` para detectar o panic e aplicar a flag antes de perder tempo com red herrings (volume perms, byte encoding, etc).

### Mudado

- `SKILL.md` headline "the twenty-three quirks" → **"the twenty-four quirks"**.
- `SKILL.md` scope: nota explícita de que v2.66.x está coberto **só** pelo Quirk 24 (masterkey); resto da skill segue v4-first. Isso evita que alguém olhe a skill e pense que ela cobre v2 inteiro.
- `description` do frontmatter ganha 5 triggers novos: `Zitadel v2.66 No master key provided`, `ZITADEL_MASTERKEY env ignored`, `start-from-init masterkey flag`, `panic No master key provided`, `masterkey must either be provided`.

---

## 2026-05-04 — Multi-app YAML refactor: env > YAML precedence (1 lição)

Source: feature 005-production-deploy (refactor T301 do `bootstrap-zitadel.ts` para suportar `applications[]` declarativo no mesmo Project ERP-JRC). Após o merge, login em LAN HTTPS via `dev.sh` quebrou imediatamente com `{"error":"invalid_request","error_description":"The requested redirect_uri is missing in the client configuration"}` no callback do Zitadel. Bug introduzido na **própria sessão** que adicionou multi-app — caso prototípico de "regressão de refatoração" que o asset bundled da skill ainda não previa.

### Adicionado

- **L22 — Multi-app YAML refactor: env vars do `dev.sh` precisam DOMINAR o YAML** (`SKILL.md` quirk 23, `references/troubleshooting.md` novo §"redirect_uri missing in client configuration after multi-app refactor regression", `references/api-cheatsheet.md` nota na seção "Create OIDC application", `assets/bootstrap-zitadel.ts` comentário-aviso forward-looking).
  *Sintoma evitado*: quando você refatora um bootstrap single-app para ler `applications[].redirectUris` declarativos, a tendência natural é "YAML é a fonte da verdade — wins sempre". Errado para dev workflows com LAN HTTPS dinâmico (mkcert + proxy reverso): o `dev.sh` injeta `OIDC_REDIRECT_URIS=https://<ip-da-lan>.sslip.io:5443/auth/callback,...` a cada boot com IP que muda entre redes (escritório/casa/hotspot). YAML estático **nunca acompanha** esse host dinâmico. Família dos quirks 10 (silent-renew em redirectUris) e 18 (byte-match), mas o gatilho é diferente — não é config inicial, é regressão de refatoração. Fix canônico: **env explícito > YAML não-vazio > hardcoded fallback**. Em produção env é unset, YAML domina (hosts canônicos); em dev env vence (hosts dinâmicos).

### Mudado

- `SKILL.md` headline "the twenty-two quirks" → **"the twenty-three quirks"**; description e triggers expandidos com `redirect_uri missing in client configuration`, `multi-app YAML override env`, `applications redirectUris`, `bootstrap idempotente multi-app`.
- `assets/bootstrap-zitadel.ts` ganha comentário forward-looking no bloco `REDIRECT_URIS` alertando o futuro mantenedor sobre a precedência correta antes de evoluir para multi-app — sem mudar o código (asset segue single-app). Quem evoluir o asset para multi-app precisa ler troubleshooting.md §"redirect_uri missing — multi-app refactor" antes.
- `references/api-cheatsheet.md` ganha um bullet na seção "Create OIDC application" linkando para o novo §troubleshooting — apontador rápido para quem está desenhando um bootstrap multi-app pela primeira vez.

---

## 2026-05-04 — Branding da Login UI v1 + reforço da pegadinha 13 (5 lições)

Source: sessão de aplicação da identidade visual JRC (logo, vermelho `#ed1c24`, textos PT-BR) à hosted Login UI v1 do Zitadel v4.14.0, validada via Playwright. Mesma sessão hit pela 4ª vez no projeto o "401 storm pós `--reset-zitadel`" — só que dessa vez a causa raiz foi processo `tsx watch` zumbi com env+JWKS antigos na heap (não o `.env` em disco), revelando lacuna na quirk 13 existente.

### Adicionado

- **L17 — `privateLabelingSetting` no projeto é o gatilho silencioso da branding** (`SKILL.md` quirk 19, `references/branding.md` novo §"Quirk 19").
  *Sintoma evitado*: 30min debugando "branding aplicado mas tela ainda azul Zitadel". A label policy da org é salva e ativada perfeitamente, mas o Zitadel só a usa pra renderizar a Login UI se o **projeto** OIDC tiver `PRIVATE_LABELING_SETTING_ENFORCE_PROJECT_RESOURCE_OWNER_POLICY` — sem o flag, cai pra label policy default da instância. Fix: setar no `POST/PUT /management/v1/projects/{p}` e verificar via GET.

- **L18 — POST vs PUT na primeira label policy + 2 error IDs distintos pra "no-op"** (`SKILL.md` quirk 20, `references/branding.md` §"Quirk 20").
  *Sintoma evitado*: `PUT /management/v1/policies/label` retorna `404 "Private Label Policy not found (Org-0K9dq)"` na primeira execução (org ainda usa default da instância). Re-runs do bootstrap idempotente disparam `400 "Private Label Policy has not been changed (Org-8nfSr)"` — diferente do `COMMAND-1m88i` genérico. Fix: GET prévio → ramificar por `policy.isDefault` → POST se default, PUT senão; tratar **ambos** error IDs como no-op.

- **L19 — Path de assets em Zitadel v4 mudou para `/assets/v1/org/policy/label/...`** (`SKILL.md` quirk 21, `references/branding.md` §"Quirk 21").
  *Sintoma evitado*: `POST /assets/v1/orgs/me/policy/label/logo` (path que aparece em docs/exemplos antigos do v1/v2/v3) retorna **HTTP 405 Method Not Allowed** em v4 — confunde porque parece "endpoint existe mas método errado". Fix: usar singular `org` sem `s/me`. Endpoints corretos: `logo`, `logo/dark`, `icon`, `font`, todos via POST multipart com header `x-zitadel-orgid`.

- **L20 — Custom login text em `/management/v1/text/login/{lang}` + só códigos curtos** (`SKILL.md` quirk 22, `references/branding.md` §"Quirk 22").
  *Sintoma evitado*: `PUT /management/v1/policies/custom_login_text/{lang}` (path antigo) retorna 404; `PUT .../text/login/pt-BR` retorna `400 LANG-lg4DP "Language is not supported"`. Zitadel só aceita ISO 639-1 curto (`pt`, `en`, `de`); resolução `pt-BR → pt` é server-side. PUT é **mergeable** (campos não enviados preservam i18n default), não replace.

- **L21 — Quirk 13 reforçada: `.env` corrigido + `bootstrap.json` regenerado NÃO basta** (`references/troubleshooting.md` §"401 storm with apparently-valid JWT" ganha "Cause 3").
  *Sintoma evitado*: 401 storm pós `--reset-zitadel` que retorna mesmo após sincronizar `.env` com `bootstrap.json`. Causa: processos `tsx watch` antigos mantêm env+JWKS antigos na heap; `tsx watch` re-restarta em `src/**`, não em `.env`. Sessões longas acumulam: nesta encontrei **8 instâncias paralelas** do backend, das quais 5 com env de bootstraps anteriores. Fix em 3 camadas: (1) launcher patcha `.env` em todo boot (já cobre cause 2), (2) launcher mata por padrão de cmdline qualquer dev runner antigo antes de subir o novo (cuidado com regex: a cmdline real é `node .../packages/backend/.../tsx watch ...`, então padrão `tsx.*packages/backend` nunca casa — use `packages/backend.*server\.ts`), (3) backend faz boot-time sanity check comparando `AUTH_AUDIENCE` vs `bootstrap.json.projectId`.

### Mudado

- `SKILL.md` headline "the eighteen quirks" → **"the twenty-two quirks"**; description e triggers expandidos com `LabelPolicy`, `PRIVATE_LABELING_SETTING`, `Org-0K9dq`, `Org-8nfSr`, `LANG-lg4DP`, `label policy não aparece`, `login UI azul Zitadel`, `branding Zitadel`, `customizar tela de login Zitadel`, `Powered by Zitadel disable`, `tela piscando depois do login`, `401 storm depois de --reset-zitadel`, `tsx watch zumbi`. Tabela "How to use" ganha linha "Apply org branding to the hosted Login UI v1 → `references/branding.md`".
- `references/troubleshooting.md` §"401 storm with apparently-valid JWT" ganha **Cause 3** (stale runtime: processo dev runner com env+JWKS antigos na heap), distinta de Cause 1 (JWKS TLS) e Cause 2 (`.env` stale). Diagnóstico final ganha hint pra `pgrep -af` da cmdline do dev runner.

### Não mudado / fora de escopo

- `assets/bootstrap-zitadel.ts` — segue como template mínimo. As 4 funções de branding (`ensureLabelPolicy`, `ensureLabelAssets`, `ensureCustomTexts`, `ensureProject` com sync do `privateLabelingSetting`) vivem em `packages/idp/scripts/bootstrap-zitadel.ts` no projeto JRC, referenciadas como exemplo no fim de `branding.md`.
- `references/api-cheatsheet.md` — não duplico endpoints de branding lá; aponto pra `branding.md` ao invés.
- Nenhum bump de versão / push externo: skill é inline neste repo (a skill `retrofit-skill` é hardcoded pra `skills_commands_manager` e não se aplica).

### Verificação

- Login completo pela tela do Zitadel mostra logo JRC vermelho centralizado, fundo `#fbf9f8`, sem watermark "Desenvolvido por Zitadel", textos PT-BR ("Entrar", "E-mail corporativo", "Continuar") — capturado via Playwright em `/oauth/v2/authorize?...&prompt=none`.
- Bootstrap idempotente confirmado em re-runs (logs `[label-policy] sem mudanças (no-op)` via `Org-8nfSr`).
- 401 storm: 53× `/oauth/v2/authorize` em 15s reduzido a 1× após fix das 3 camadas (regex consertado em `dev.sh::kill_known_dev_servers`, audience patch idempotente em `dev.sh`, boot-time sanity check em `packages/backend/src/config/auth-sanity.ts`).

## 2026-04-30 — Boot-time silent renew + SPA recipe (F5 stuck + logout broken)

Source: sessão de smoke pós-LAN-HTTPS — bug "F5 expulsa o usuário" (boot-time `signinSilent` ausente para `InMemoryWebStorage`) e bug "Logout devolve `?error=invalid_request post_logout_redirect_uri invalid`". Diagnóstico via Playwright capturando network + console em `https://192.168.0.1.sslip.io:5443/`.

### Adicionado

- **L13 — Boot-time `signinSilent` recipe para SPAs com `InMemoryWebStorage`** (`SKILL.md` quirk 17, `references/spa-recipes.md` §"Recipe 1" novo, `references/troubleshooting.md` §"SPA stuck on Verifying session… with no IdP-side error").
  *Sintoma evitado*: F5 numa rota autenticada expulsa o usuário pra `/login` mesmo com o cookie de sessão do IdP vivo. `automaticSilentRenew=true` da lib só dispara em `accessTokenExpiring`, que requer `User` ativo — in-memory storage zera no F5 → silent renew nunca dispara → `<ProtectedRoute>` redireciona. Fix: `useEffect` no `<AuthProvider>` que dispara `auth.signinSilent()` uma única vez no boot, segura a árvore num placeholder até resolver/falhar.

- **L14 — `<AuthProvider>` envolvendo `/silent-renew` causa recursão infinita de iframe** (`SKILL.md` quirk 17, `references/spa-recipes.md` §"Trap 1", `references/troubleshooting.md` §"SPA stuck on Verifying session…").
  *Sintoma evitado*: depois de adicionar o boot-time `signinSilent` (L13), a UI fica eternamente em "Verificando sessão…" porque o iframe que `signinSilent` cria carrega `/silent-renew`, que re-monta `<AuthProvider>`, que dispara outro `signinSilent`, infinito. Fix: dois guards no `useEffect` — `isAuthRoute()` (`/login`, `/silent-renew`, `/auth/callback`) e `isInIframe()` (`window.self !== window.top`).

- **L15 — StrictMode + closure `cancelled` flag em `useEffect` com Promise = lockup perpétuo** (`SKILL.md` quirk 17, `references/spa-recipes.md` §"Trap 2", `references/troubleshooting.md` §"SPA stuck on Verifying session…" parágrafo final).
  *Sintoma evitado*: o padrão idiomático "let cancelled = false; return () => { cancelled = true; }" trava em StrictMode — cleanup da 1ª run seta `cancelled=true` na closure 1; 2ª run pula pelo ref → quando a Promise da 1ª run resolve, `if (!cancelled)` é falso → `setBootstrapping(false)` nunca dispara. Fix: NÃO usar `cancelled` flag quando um ref já gateia re-execução; deixar o setState rodar mesmo na 2ª run.

- **L16 — `post_logout_redirect_uri` byte-match: registrar `/` mas SPA mandar `/login` quebra logout** (`SKILL.md` quirk 18, `references/troubleshooting.md` §"Logout returns post_logout_redirect_uri invalid").
  *Sintoma evitado*: clicar Sair retorna `{"error":"invalid_request","error_description":"post_logout_redirect_uri invalid"}` e o usuário fica preso na tela de erro do IdP. Mesmo princípio do `redirect_uri` (quirk #10), mas em logout — drift comum porque `VITE_OIDC_POST_LOGOUT_REDIRECT_URI` é `/login` para UX, e o bootstrap registrou só o root. Fix: registrar ambas as URIs comma-joined (`${WEB_BASE}/login,${WEB_BASE}/`), e dropar otimizações de skip-bootstrap que mascaram drift dessa env (a idempotência do `COMMAND-1m88i` torna o re-run barato — quirk #14).

### Mudado

- `SKILL.md` headline "the sixteen quirks" → **"the eighteen quirks"**; description e triggers expandidos com `boot-time signinSilent`, `F5 perde sessão`, `post_logout_redirect_uri invalid`, `StrictMode signinSilent`, `InMemoryWebStorage refresh`, `iframe silent renew recursion`. Tabela "How to use" ganha linha "Wire an SPA — boot-time silent renew, F5 retention, logout flow → `references/spa-recipes.md`".
- `references/troubleshooting.md` ganha 2 entradas novas dedicadas (boot-time `signinSilent` recursion + logout `invalid_request`), distintas do quirk #10 (que cobre a outra forma do "stuck on verifying session" — silent-renew URI ausente em `redirectUris`).

### Não mudado / fora de escopo

- `assets/bootstrap-zitadel.ts` — o `OIDC_POST_LOGOUT_URIS` continua parametrizado por env; o asset bundled segue como template mínimo. O caso desta sessão é de **launcher** (dev.sh/dev.ps1) registrando o valor errado, não do template do bootstrap em si.
- `references/docker-compose-bootstrap.md` — sem mudança.
- Nenhum bump de versão / push externo: skill é inline neste repo.

### Verificação

```bash
grep -rn "boot-time signinSilent\|isAuthRoute\|isInIframe\|StrictMode\|post_logout_redirect_uri invalid" .claude/skills/zitadel-idp/
```

Esperado: ≥1 hit em cada termo, distribuídos por `SKILL.md`, `references/spa-recipes.md` e `references/troubleshooting.md`.

## 2026-04-30 — LAN HTTPS (mkcert + Caddy) revelou 5 pegadinhas novas

Source: sessão `dev.sh` LAN-share — debugar "Entrar não faz nada" pela LAN, e depois "Dashboard pisca + HTTP 429" após login. Diagnóstico via Playwright + decode do JWT na sessionStorage + log do backend.

### Adicionado

- **L8 — Backend Node não confia no JWKS HTTPS com cert local (mkcert/CA dev)** (`SKILL.md` quirk 12, `references/token-validation.md` §"Trusting a self-signed JWKS endpoint from Node", `references/troubleshooting.md` §"401 storm with apparently-valid JWT" cause 1, tabela "Common pitfalls" linha nova).
  *Sintoma evitado*: 100% dos `/api` voltam 401 mesmo com JWT decodificado mostrando `iss`/`aud`/`exp` perfeitos. SPA entra em loop de silent renew → React Query refetcha tudo a cada render → estoura rate-limit (429). Backend `createRemoteJWKSet` falha o handshake TLS antes de validar a assinatura, e jose envelopa em `JWSSignatureVerificationFailed` genérico. Fix: `NODE_EXTRA_CA_CERTS=$(mkcert -CAROOT)/rootCA.pem` no env do backend.

- **L9 — `--reset-zitadel` regenera `projectId`/`clientId`; envs com valor antigo viram lixo silencioso** (`SKILL.md` quirk 13, `references/api-cheatsheet.md` §"Re-reading bootstrap output after volume reset", `references/troubleshooting.md` §"401 storm with apparently-valid JWT" cause 2, tabela "Common pitfalls" linha nova).
  *Sintoma evitado*: idêntico ao L8 (401 storm), mas a causa é audience drift, não TLS. `OIDC_AUDIENCE` em `.env` cacheado de bootstrap anterior não bate com `aud` do token novo. Fix: re-derivar `projectId`/`clientId` de `bootstrap.json` em todo boot, nunca hardcode.

- **L10 — `PUT /oidc_config` retorna `400 COMMAND-1m88i "No changes"` quando o body é idêntico ao estado atual** (`SKILL.md` quirk 14, `references/api-cheatsheet.md` §"Create OIDC application" snippet `try/catch` idempotente).
  *Sintoma evitado*: 2ª run do `bootstrap-zitadel.ts` quebra com 400 enganoso. Mesmo padrão aparece em outros endpoints de update (login policy, password policy, SMTP). Fix: tratar `COMMAND-1m88i` como no-op no `try/catch`.

- **L11 — Trio obrigatório para TLS-terminação por proxy reverso** (`SKILL.md` quirk 15, `references/docker-compose-bootstrap.md` §7 "TLS terminated by reverse proxy", `references/troubleshooting.md` §"Zitadel won't start when fronted by a TLS-terminating reverse proxy", `assets/docker-compose.zitadel.yml` comentário sobre `--tlsMode`).
  *Sintoma evitado*: container restart-loop ou 400/500 em todo authenticate. Skill antes citava só `EXTERNALSECURE=true` + `TLS_ENABLED=false` — falta a flag de start `--tlsMode external`. Sem ela o binário ainda tenta bind TLS interno.

- **L12 — `crypto.subtle` (PKCE) só existe em secure contexts; localhost/127.0.0.1 são única exceção HTTP** (`SKILL.md` quirk 16, `references/troubleshooting.md` §"signinRedirect() does nothing — clicking Entrar / Login button produces no console error").
  *Sintoma evitado*: clicar "Entrar" em SPA hospedado em `http://192.168.x.x:5173` não faz nada — sem erro no console, sem nav, sem network. `react-oidc-context` faz `void auth.signinRedirect(...)` e engole a rejeição. Fix: HTTPS para SPA + Zitadel + backend mesmo em LAN dev (mkcert + reverse proxy).

### Mudado

- `SKILL.md` headline "the eleven quirks" → **"the sixteen quirks"**; description e triggers expandidos com `NODE_EXTRA_CA_CERTS`, `tlsMode external`, `COMMAND-1m88i`, `crypto.subtle secure context`, `signinRedirect silent fail`. Tabela "When to use" inclui linha "Wiring an SPA fora de localhost/127.0.0.1".
- "What this skill explicitly does NOT cover" agora cita o trio completo (env + flag) ao apontar para reverse-proxy TLS, em vez de só `EXTERNALSECURE`/`TLS_ENABLED`.
- `references/token-validation.md` "Common pitfalls" ganha 2 linhas (TLS local, audience drift pós-reset).

### Não mudado / fora de escopo

- `assets/bootstrap-zitadel.ts` — o fix `try/catch COMMAND-1m88i` e o `ensureSeedUser` ficaram nos scripts do projeto consumidor (`packages/idp/scripts/bootstrap-zitadel.ts`); o asset bundled da skill continua como template mínimo. Considerar portar nas próximas iterações se mais consumidores aparecerem.
- `references/docker-compose-bootstrap.md` §1–§3 — pegadinhas dessa sessão são todas pós-boot (TLS triade, JWKS trust, audience drift); compose default continua válido.

## 2026-04-29 — Smoke test do `003-frontend-wiring` revelou 7 pegadinhas novas

Source: sessão de smoke manual + Playwright capture do JWT após login real, exposta no plano `analise-as-specs-e-noble-chipmunk.md` rounds 2 e 3.

### Adicionado

- **L1 — `loginV2.required` instance feature** (`troubleshooting.md` §"Hosted UI returns 404", `SKILL.md` quirk 9, `api-cheatsheet.md` §"Login policy tweaks", `assets/docker-compose.zitadel.yml` cabeçalho).
  *Sintoma evitado*: 404 `{"code":5,"message":"Not Found"}` em `/ui/v2/login/login` após `signinRedirect`. App-level `loginVersion: {loginV1: {}}` sozinho não resolve — precisa também `PUT /v2/features/instance {loginV2:{required:false}}`.

- **L2 — Silent-renew redirect URI obrigatório** (`troubleshooting.md` §"silent renew 400 loop", `SKILL.md` quirk 10, `api-cheatsheet.md` §"Create OIDC application" quirks list, `assets/bootstrap-zitadel.ts` REDIRECT_URIS default).
  *Sintoma evitado*: SPA preso em "verifying session…" / 400 em `/oauth/v2/authorize?prompt=none` cada ~10s.

- **L3 — Scope `urn:zitadel:iam:org:project:id:{projectId}:aud`** (`token-validation.md` §"Required SPA scopes for the project audience", tabela "Common pitfalls" linha nova).
  *Sintoma evitado*: 401 com token aparentemente válido — sem essa scope, o `aud` carrega só o clientId, e o backend rejeita por audience mismatch.

- **L4 — Access token vs ID token: claims de profile não estão no AT** (`SKILL.md` quirk 11, `token-validation.md` §"Access token vs ID token — what's actually inside" + atualização do `mapClaimsToAuthContext` exemplo, `troubleshooting.md` §"Backend rejeita JWT 401 mesmo com iss/aud/exp corretos", tabela "Common pitfalls" linha nova).
  *Sintoma evitado*: backend retorna 401 "Token inválido" silenciosamente porque o mapper exige `name`/`preferred_username`/`org:id` que não estão no AT (estão só no id_token). Fallbacks defensivos: `name → preferred_username → email → sub` e `org:id → defaultTenant`.

- **L5 — ACL parity entre backend e frontend** (`tenant-org-mapping.md` §"ACL parity: backend ↔ frontend").
  *Sintoma evitado*: UI esconde botões de admin para usuário com role `battery.admin` no token porque o SPA filtrava só roles canônicas (`battery:admin`). Princípio: token bypass-a o backend → SPA precisa duplicar a tradução `battery.admin → battery:admin/writer/reader`.

- **L6 — Seed de admin user** (`api-cheatsheet.md` §"Seed an admin user", TODO em `assets/bootstrap-zitadel.ts`).
  *Sintoma evitado*: smoke test impossível de rodar porque o bootstrap só cria org/project/role/app — falta combo pronto `POST /v2/users/human` + `POST /management/v1/users/{id}/grants`.

- **L7 — `MfaInitSkipLifetime` re-prompt** (`troubleshooting.md` §"MFA setup re-prompts", `api-cheatsheet.md` §"Login policy tweaks" subseção).
  *Sintoma evitado*: tela "Configuração de 2 fatores" aparece todo login mesmo com `forceMfa: false`, porque o default skip lifetime é 30 dias.

### Mudado

- `SKILL.md` headline "the eight quirks" → **"the eleven quirks"**; description e triggers expandidos para mencionar `loginV2`, silent-renew, JWT sem profile claims; tabela "When to use" inclui linha "Diagnosing 401/400/404 contra Zitadel".
- `assets/bootstrap-zitadel.ts`: REDIRECT_URIS default agora inclui `silent-renew`; OIDC app payload agora seta `loginVersion: {loginV1: {}}`.
- `assets/docker-compose.zitadel.yml`: comentário-cabeçalho explicando que `loginV2.required` não tem env var (precisa post-boot via API).

### Não mudado / fora de escopo

- `references/docker-compose-bootstrap.md` — pegadinhas dessa sessão são todas pós-boot (instance flag, app config, claim mapping); compose continua válido.
- `scripts/reset-zitadel.sh` — sem mudança.
- Nenhum bump de versão / push externo: a skill é inline neste repo, sem `plugin.json` ou `marketplace.json`.

### Verificação

```bash
grep -rn "loginV2\|silent-renew\|preferred_username.*sub\|MfaInitSkipLifetime\|ACL parity" .claude/skills/zitadel-idp/
```

Esperado: ≥1 hit em cada termo, distribuídos pelos arquivos acima.
