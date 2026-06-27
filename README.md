<div align="center">

# Chewiesoft Marketplace

*Plugin marketplace for Claude Code and Cursor — CI/CD, code review, deployments, releases, and more.*

[![Plugins](https://img.shields.io/badge/plugins-13-blue?style=flat-square)](#available-plugins)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code%20%7C%20Cursor-blueviolet?style=flat-square)](https://code.claude.com)
[![License](https://img.shields.io/badge/license-Proprietary-red?style=flat-square)](#)

</div>

[Installation](#installation) · [Plugins](#available-plugins) · [Auto-updates](#auto-updates) · [Team Distribution](#team-distribution) · [References](#references)

---

A curated dual-platform plugin marketplace for [Claude Code](https://code.claude.com) and [Cursor](https://cursor.com) by **j0ruge**. Each plugin packages production-ready skills and commands that integrate directly into your workflow — no configuration needed beyond install.

## Platform Compatibility

| Plugin | Claude Code | Cursor | Notes |
|--------|:-----------:|:------:|-------|
| **cicd** | ✓ | ✓ | Skill — works on both platforms without changes |
| **codereview** | ✓ | ✓ | Skills — adapted automatically by the installer |
| **ddd** | ✓ | ✓ | Skill — works on both platforms |
| **deploy** | ✓ | ✓ | Command (Claude Code) / Skill (Cursor) |
| **dev-script** | ✓ | ✓ | Skill — generates `dev.sh` (bash) + `dev.ps1` (PowerShell) per project |
| **dotnet-wpf** | ✓ | ✓ | Skills — works on both platforms |
| **pdf-generation** | ✓ | ✓ | Skill — PDF template design + library selection (pdfmake/pdf-lib/PDFKit/Puppeteer/@react-pdf), modular sections, visual verification |
| **release** | ✓ | ✓ | Command (Claude Code) / Skill (Cursor) |
| **retrofit-skill** | ✓ | ✓ | Command (Claude Code) / Skill (Cursor) |
| **statusline** | ✓ | — | Claude Code only (uses the Claude Code status line API) |
| **ticket** | ✓ | — | Claude Code only (`/ticket` slash command + Jira `acli` + atlassian MCP) |
| **whisper-preprocess** | ✓ | ✓ | Skill — ffmpeg + OpenAI Whisper offline audio→text pipeline (silence removal, voice enhancement, segmentation, multilingual merge); decoupled stable-gain listening copy (no "picotamento") |
| **zitadel-idp** | ✓ | ✓ | Skill — Zitadel self-hosted OIDC integration field guide (bootstrap, JWT, branding, 42 gotchas with proto-aligned v4.15 examples + CD cutover survival kit + Console UI human-user creation pitfalls + production-cutover v0.7.0 (backend `extra_hosts` for hairpin-NAT IdP, 3-layer SPA defense vs RT-reuse session revoke) + smoke-e2e CI v0.8.0 (admin.pat bind mount EACCES cascade into `unique_constraints_pkey`, default password policy 4-class trap, Login UI v2 healthcheck slow on small runners) + real-browser smoke v0.9.0 (seed user grant reconciliation gap on YAML evolution, browser→backend CORS preflight 401 mimicking JWT failure, Playwright self-signed Zitadel recipe) + v2.66→v4 upgrade runbook + API v1→v2 mapping) |
| **wsl-windows-onboarding** | ✓ | ✓ | Skill — onboards a Windows box to WSL2: install the Ubuntu distro + a non-root sudo user, diagnose WSL, install rtk + Claude Code (global rtk hook), migrate projects into the Linux FS (copy→validate→delete, incl. a **tight-disk one-repo-at-a-time** loop for a nearly-full `C:` and the reserved-name `nul`/`\\?\` delete trap, CRLF/filemode "whole tree modified" diagnosis), and set up zsh + the Windows Terminal profile (icon + default) |

## Installation

### Claude Code

```bash
# Add the marketplace (pick one)
/plugin marketplace add j0ruge/skills_commands_manager          # via GitHub
/plugin marketplace add git@github.com:j0ruge/skills_commands_manager.git  # via SSH
```

Then install any plugin:

```bash
/plugin install codereview    # or: cicd, ddd, deploy, dev-script, dotnet-wpf, pdf-generation, release, retrofit-skill, statusline, ticket, whisper-preprocess, zitadel-idp
```

> [!TIP]
> Keep plugins up to date with a single command:
> ```bash
> /plugin marketplace update
> ```

### Cursor

Clone the repo and run the interactive installer:

```bash
git clone git@github.com:j0ruge/skills_commands_manager.git
cd skills_commands_manager
python install.py
```

The installer prompts for platform (Claude Code, Cursor, or Both) and where to place the Cursor skills. It automatically adapts plugin content for Cursor.

> [!IMPORTANT]
> **Cursor has no global skills directory** — only project-local `.cursor/skills/` is auto-loaded by the agent ([Cursor docs](https://cursor.com/docs/skills)). Run `python install.py` from inside each project where you want the skills available, and pick the **Project** option.
>
> The installer also offers a **Staging cache** option that copies the converted skills to `~/.cursor/skills/` as a master copy — handy as a source to mirror into projects, but Cursor itself will not pick those up directly.

## Available Plugins

| Plugin | Version | Category | Description |
|--------|---------|----------|-------------|
| [**cicd**](#cicd) | 2.19.0 | Development | CI/CD troubleshooting for GitHub Actions, Docker, GHCR, and self-hosted runners (systemd-on-host **e containerizado via `myoung34/github-runner`**) — cobre CMD-herdado-zerado, env `LABELS` vs `RUNNER_LABELS`, `EPHEMERAL`+`restart:always` loop, `gpg --dearmor` em buildkit, deploy keys per-repo unique, `.env` leading whitespace + `sed` silenciando, monorepo workspace hoisting diagnosis, vitest jsdom→happy-dom recipe pra msw v2. **(NEW v2.12.0) `troubleshooting-shared.md` §1a** — GHCR `net/http: TLS handshake timeout` no `docker login` do deploy job self-hosted é bug DISTINTO de §1 `unauthorized` (TCP conectou mas handshake não completou — credencial é irrelevante); isolation key é build-and-push em ubuntu-latest passar enquanto deploy em self-hosted falha; causa raiz típica é MTU mismatch em VPN/overlay ou TLS-inspection proxy; **Fix A** bash retry wrapper 3x backoff 10s/20s ao redor de `docker login` (20 linhas, sem nick-fields/retry); **Fix B** `mtu: 1400` em `/etc/docker/daemon.json` + restart. Reference dedicada `cd-pipeline-pitfalls.md` cobre **7 classes** de bugs de cutover/CI prod: (1) VITE/CRA/Next build args bake'd no image, frontend rebuild mandatory; (2) operator clone reconciliando stack stale; (3) `docker compose --profile X run` reconciliando containers de outros services; (4) `compose run --rm` orphan + nginx-proxy upstream poisoning (~50% intermittent 401s); (5) container scripts que escrevem upward de `__dirname` batem ENOENT em prod (Dockerfile só copia `packages/<self>/`) — fix canônico é try/catch best-effort, **v2.11.0 refinement** narrow catch para ENOENT/ENOTDIR e propagar EACCES/ENOSPC/EROFS preserva visibilidade de problemas reais em dev (especialmente importante quando `bootstrap.json` é consumido por sanity check downstream); **v2.11.0 §6** — GHA bind mount uid mismatch: container vendorado roda uid 1000 (Postgres, Zitadel, vários), runner GHA `ubuntu-latest` é uid 1001 com pasta 0755 → EACCES no init/setup, e o estado parcial deixado para trás cascata em erros DIFERENTES nas retries (constraint violation, already-exists), burying the real cause; cura é pre-create do bind mount com `chmod 0777`; **v2.11.0 §7** — `docker compose up -d --wait` espera TODOS os serviços com healthcheck por default; um sibling lento (Next.js/Vite ~90s+ no runner pequeno) estoura `--wait-timeout` da stack inteira; cura é passar service names explícitos no `up --wait` + companion sempre dumpar logs do serviço lento no on-failure (`|| true`) mesmo quando não está no wait. **v2.9.0 §7 self-hosted-runner-docker** — chicken-and-egg de RUNNER_REGISTRATION_TOKEN estática em prod, recovery em 3 passos. **§5b** — multi-job CD exhaust em janela 1h, fix em 2 lugares (GH secret + .env). **(NEW v2.13.0)** monorepo npm-workspaces (lessons 37–40): backend roda via `tsx`, não `node dist/`, quando os pacotes shared exportam TS source (`main: src/index.ts` → `node dist` dá `ERR_MODULE_NOT_FOUND`); `tsc --noEmit` é VAZIO em tsconfig com project references (`files:[]`) → usar `tsc -b --noEmit`; `npm ci -w` escopado quebra com sibling não declarado (usar `npm ci` cheio); `USER node` + named volume novo = `EACCES` sem `mkdir`+`chown` antes do USER. **`cd-pipeline-pitfalls.md §1b`** — injetar secret de RUNTIME no nginx via templates/`envsubst` (contrapartida do build-arg bake'd). **(NEW v2.14.0)** lessons 41–45 (hardening 017): wrapper PID 1 (`npx tsx`/`npm start`) engole SIGTERM → `init: true`; `tsx`/`prisma` em `dependencies` p/ `npm ci --omit=dev` enxugar a imagem de runtime; composite action p/ DRY do CI gate entre `ci.yml` e `cd-staging.yml`; CI só em `pull_request` deixa push direto a branch protegido escapar do gate; descobrir digest de imagem base via `docker buildx imagetools inspect`. **(NEW v2.15.0)** §7 → **migração ACCESS_TOKEN in-place** é o fix DURÁVEL do `runner-registration 404` recorrente (lesson 46): rotacionar token e `EPHEMERAL:false` NÃO curam (entrypoint re-registra a cada start); trocar `RUNNER_TOKEN` → `ACCESS_TOKEN: ${RUNNER_ACCESS_TOKEN:-}` + `RUNNER_SCOPE: repo`, entrypoint aceita ACCESS_TOKEN OU RUNNER_TOKEN, PAT só no `.env` persistente do host; `gh` NÃO cunha PAT (web UI; `gh auth token` escopo `repo` é stopgap); validar PAT e provar a cura com `docker restart`. **(NEW v2.16.0)** §8/§9 (lessons 47–49) — dois crashloops do runner ORTOGONAIS ao token (mordem até em ACCESS_TOKEN): §8 `Runner version vX is deprecated and cannot receive messages` (runner registra/conecta/lista jobs e só então o GitHub recusa — binário de `:latest` nunca re-puxada + auto-update off; `docker compose pull` + ligar auto-update; footgun: `DISABLE_AUTO_UPDATE` desliga com QUALQUER valor não-vazio, até `0` — para LIGAR, remover a var); §9 `registration has been deleted from the server` (reuso de config ressuscita credencial morta — `docker volume rm <config-volume>`, distinto do §6); pinar a imagem do RUNNER por digest sem `compose pull` mensal é contraproducente (exceção à lição 45). **(NEW v2.17.0)** `self-hosted-runner-docker.md §10` (lesson 50) — §7/§8/§9 podem **EMPILHAR** num mesmo runner: um único deploy `queued` exigiu §9 → PAT `401` → §8 **em sequência**, cada fix desmascarando o próximo (o `docker volume rm` do §9 expõe um `ACCESS_TOKEN` expirado, cujo conserto expõe o binário deprecado; a assinatura do log muda a cada camada). Inclui triagem **"ausente vs offline"** (`gh api …/actions/runners` lista offline também → ausência total = registro apagado/token) e a natureza **host-wide** do PAT (um expira → derruba todos os runners do host). **(NEW v2.18.0)** `self-hosted-runner-docker.md §11` (lesson 51) — **detecção proativa** do deploy `queued` silencioso: um job `[self-hosted, <label>]` fica em fila sem ❌/timeout/e-mail (o `timeout-minutes` não conta em fila, só após pickup do runner), então o root-cause §7–§10 passa **semanas** despercebido (site no ar com a imagem velha). Duas camadas em `ubuntu-latest`: **preflight gate** (lista `/actions/runners`, falha o deploy no push se não há runner online com o label — gotcha: `GITHUB_TOKEN` NÃO lista runners, exige PAT `Administration: Read`; no-op sem o secret) + **watchdog** agendado (`actions:read`, alerta deploy preso — gotchas: status de **JOB** não de run, `schedule` só roda do branch default). **(v2.18.1)** §11 refinado: preflight **fail-open em erro de PAT** — com `set -e` + `ONLINE=$(gh api …)` um PAT expirado/rotacionado bloquearia **todo** deploy com msg enganosa "no runner"; usar `if ! ONLINE=$(…)` + `exit 0` no erro de API (fail-closed só com zero runners). + caveat do PAT host-wide reusado (rotação quebra o gate → atualizar o secret junto). **(NEW v2.19.0)** suporte a **backend Django/gunicorn** (`references/django-backend.md`) — auto-roteia Python além de Node/Prisma. Lição central (lesson 52): **`ALLOWED_HOSTS` sem `127.0.0.1`/`localhost` faz o healthcheck INTERNO do container (`GET 127.0.0.1:8000/healthz/`) responder 400 → container nunca fica `healthy` → o `wait-healthy` do CD estoura mesmo com login/pull/migrate verdes** (isolation key: `GET /healthz/ 400` no log). + admin 403 CSRF sob HTTPS atrás de proxy sem `CSRF_TRUSTED_ORIGINS`/`SECURE_PROXY_SSL_HEADER` (a API JWT não precisa); imagem prod = gunicorn + `collectstatic` em build (SECRET_KEY dummy, sem DB) + WhiteNoise `CompressedStaticFilesStorage` (Manifest quebra dev) + HEALTHCHECK via `python -c urllib` (slim sem curl) + migração one-off `manage.py migrate --noinput`; gotchas cross-stack (valem p/ Node também): owner do GHCR em lowercase (`tr '[:upper:]' '[:lower:]'`), pacote GHCR privado por default → `docker exec` no container rodando p/ one-offs (não `compose run`, que re-puxa sem login), `paths-ignore: ['**.md','docs/**']` p/ não redeployar em commit só de doc. |
| [**codereview**](#codereview) | 1.16.0 | Quality | Pre-PR code review with model routing (haiku/sonnet/opus), TOCTOU detection, accessibility, **deterministic hardcoded secrets detection** via Python regex script + optional ggshield/gitleaks (GitGuardian-equivalent, blocks PRs with leaked credentials), and multi-reviewer PR resolver (CodeRabbit, Copilot, Gemini, Codex) with baseline-aware regression testing, **verify-before-trust** validation of reviewer-cited references, and **byte-exact verification** (`od -c` / `xxd`) when reviewers cite NUL bytes, BOM, zero-width chars, or other invisible/control characters — `Read` renders those bytes as plain whitespace and silently induces false-positive verdicts. **v1.12.0** hardens Phase A output discipline (literal return template + `END_OF_PHASE_A_REPORT` end-marker) and adds a mandatory orchestrator-side fallback so the F-grade secrets gate never silently degrades when the haiku agent under-reports (running 9 tool calls but final-messaging only `"results returned above"`). **v1.13.0** adds detection pass 6.5.3 "Contract Drift in Tests" — when the diff modifies an exported constant (`export const X = [...] as const`, Zod/Yup/literal-union schemas) and a test file in the codebase asserts that constant literally (`expect(X).toEqual([...])` / `toStrictEqual` / `toMatchObject` / `deepEqual`), cross-check the asserted shape against the current export and flag mismatches as HIGH (public contract) / MEDIUM (internal). Same release also forces the final report's `### Overall Grade` table and `### Recommended Actions` block to ALWAYS render — even on zero-findings happy path, focus-area runs, or token-tight reviews where the model would otherwise collapse them into prose. **v1.14.0** adds detection pass 6.9 "Dead Code & Unused Symbols" plus a dedicated **parallel Dead Code Sweep agent (Phase B2)** — because the per-file analysis agents each see only one file and structurally cannot tell whether an exported symbol is referenced elsewhere, dead code (unused exports, orphaned files, unreachable code, dead deps) needs a whole-repo reference sweep. It runs a hybrid scope (code morto **introduced or orphaned by this PR** first, then a **capped pre-existing** project-health summary) using the repo's own tooling when present (`knip` / `ts-prune` / `vulture` / `depcheck` / Roslyn / `staticcheck`, read-only) and a grep reference deepsearch otherwise, with strong false-positive guardrails (public API, framework/DI/reflection wiring, non-code references, barrels, test-only utils) and a per-finding Confidence. Dead code is hygiene: MEDIUM/LOW only, **never blocks the PR**, and feeds the new **🧹 Dead Code & Cleanup** report section + Recommended Actions → Consider Fixing. **v1.15.0** calibrates pass 6.9's reading of `knip`/`ts-prune` output with two false-positive guardrails learned from a real run: **over-export** (a symbol used only WITHIN its own file is reported as an "unused export" but isn't dead — recommend dropping the `export`, not deleting it) and **regenerable scaffolding** (shadcn `components/ui/**` / `**/generated/**` surfaced in bulk → keep in Bucket B, capped, never an actionable app finding). **v1.16.0** splits that over-export guardrail into two opposite fixes — pure in-file plumbing → drop the `export`; a symbol that's part of an *exported* type-surface/API (e.g. an interface typing an exported hook's return, like `AuthUser` in `UseAuthReturn`) → keep the `export` and mark `@public`/`@internal`, never delete (dropping it can break `tsc -b`/declaration emit with "uses private name") — and makes the within-file/exported-signature grep a mandatory per-symbol check on every "unused export". |
| [**deploy**](#deploy) | 1.4.0 | Development | Automated staging deployment with pre-flight checks and pipeline monitoring |
| [**release**](#release) | 1.3.0 | Development | GitHub Release creation with categorized notes, multi-stack and monorepo support |
| [**statusline**](#statusline) | 1.5.1 | Customization | Interactive status line setup — cross-platform (Bash + PowerShell), 12 sections incl. 5h/weekly usage limits + PR state, optional effort-level badge |
| [**dotnet-wpf**](#dotnet-wpf) | 1.6.1 | Development | WPF toolkit — project audit, Fluent Design guide (90+ controls, form spacing, height clipping, Grid row separators, multi-column layouts, ContentDialog confirmation for destructive actions), MVVM migration, E2E testing |
| [**ddd**](#ddd) | 0.4.1 | Architecture | Domain-Driven Design toolkit — analyzes codebases for DDD violations, guides strategic design (event storming, context mapping, bounded-context canvas), generates legacy→DDD migration specs. Language-agnostic; synthesizes Evans + Vernon + modular-monolith practice |
| **dev-script** | 0.5.0 | Development | Generates `dev.sh` (bash) + `dev.ps1` (PowerShell) launchers tailored to the current project — detects compose/monorepo/IdP/mkcert, emits idempotent script with healthchecks, **two-strategy port handling** (find-next-free discovery with peer-coordination env vars for foreign-owned service ports / kill-and-reclaim with `pgrep` fallback for own orphans), trap cleanup, HTTPS-on-LAN via mkcert + Caddy when the SPA does OIDC PKCE, Playwright LAN-HTTPS testing recipe, monorepo `kill_known_dev_servers` regex gotcha (path appears before `tsx` in cmdline), `tsx watch --include=.env` so launcher-patched env actually reaches runtime, the boot-time sanity-check pattern (app warns LOUD when runtime config diverges from launcher's source-of-truth file), and **v0.4.0** P17 — foreign port owner + `strictPort: true` silent-hang cascade (kill silently fails → Vite hard-fails → parent `wait` keeps tracking surviving backend = looks like a hang; fix is pre-flight port discovery with peer-coordination env vars instead of trying to kill foreign processes). **v0.5.0** adds three Windows↔WSL migration pitfalls: P18 — CRLF `.env` silently appends `\r` to values read with `grep\|cut` (`docker exec "$name\r"` → `No such container`, healthcheck times out while every log line looks correct; fix is a `tr -d '\r'` read helper); P19 — `node_modules` built on another platform crashes Vite/swc/esbuild with `Failed to load native binding` (missing platform-optional binary; re-install inside the target OS); P20 — `yarn` resolves to Debian's `cmdtest` impostor (`Parsing scenario file …`) when Corepack isn't enabled (`corepack enable` shadows it; resolve the package manager Corepack-aware) |
| **retrofit-skill** | 0.2.2 | Development | Apply non-obvious session lessons to a target skill in two modes — full (marketplace skill: bumps version, updates CHANGELOG/marketplace.json/README, commits and pushes) or lean (local skill in another repo: edits files + CHANGELOG and commits there, no bump or marketplace changes) |
| **pdf-generation** | 1.4.0 | Development | PDF generation design toolkit — analyzes reference templates, recommends libraries (pdfmake/pdf-lib/PDFKit/Puppeteer/@react-pdf), designs modular section architecture with conditional columns, auto-generated observations and revision control. **v1.2.0** adds three production-proven pdfmake pitfalls: cell padding NOT discounted from `widths` (last column silently cuts on A4 with 8+ cols, most painful pdfmake gotcha); Roboto bundled `fi`/`fl`/`ffi` ligatures drop the f (`fiscal`→`fscal`) — **v1.2.1** corrects the cause: pdfkit applies the `liga` substitution but fails to embed the glyph (bundled font is current, not old; confirm via SFNT parse; `@fontsource-variable/*` ships only `.woff2`, unusable by pdfmake); `addFonts()` silently rejects AFM (errors 500 on `getBuffer`). Plus Phase 6 Visual Verification (NON-NEGOTIABLE) — render bugs only surface in the rendered PDF, never in automated tests. **v1.3.0** adds three visual-verification lessons: render/inspect EVERY page — header/footer in `content[]` (vs the `header`/`footer` slots) vanish on page 2+ (invisible in 1-page tests); conditional/optional field absence ≠ bug (populate the data to verify); hash-by-input revision cache doesn't regenerate on layout/code change (bust the cache). **v1.4.0** adds vector-logo (SVG) handling: pdfmake renders SVG natively via `{ svg, width }` (no svg-to-pdfkit dependency — the "pdfmake can't do SVG" belief is wrong); an SVG whose fills come from a `<style>`/class block renders with NO color unless each `class` is inlined to a `fill=` attribute (silent — only the visual render reveals it); ship a small default vector as a `.ts` string constant so it survives `tsc → dist` builds (which don't copy non-`.ts` files) and gitignored runtime asset dirs (which don't exist on fresh deploy) |
| **zitadel-idp** | 0.9.0 | Development | Zitadel `v4.x` self-hosted OIDC integration field guide — captures **42** high-friction quirks with proto-aligned examples verified against raw GitHub Zitadel `v4.15.0` (FirstInstance env placement, volume perms, v1/v2 API split, tenant→orgId mapping, JWT validation over self-signed HTTPS via `NODE_EXTRA_CA_CERTS` + JWKS, `loginV2` instance flag, silent-renew redirect URI byte-match, idempotent bootstrap `No changes` 400, TLS-terminating reverse proxy, secure-context PKCE on LAN, boot-time `signinSilent` recursion, StrictMode closure trap, `post_logout_redirect_uri invalid`, Login UI v1 branding via `privateLabelingSetting` / `custom_login_text` / `LANG-lg4DP`, F5 with `InMemoryWebStorage`, 401 storm post `--reset-zitadel` from `tsx watch` zombies, multi-app YAML refactor regression vs dynamic env, Zitadel v2.66.x `--masterkey` flag fix, **v0.3.0**: Login UI v2 as a separate Next.js container (`zitadel-login`) with reverse-proxy split, API v2 idempotence via deterministic IDs, contextual `orgId` moved from header into body, **v0.4.0**: proto-aligned payloads (CreateApplication discriminator = `oidcConfiguration` top-level com `applicationType` / `developmentMode` internos, NÃO `oidc` com `appType` / `devMode`); per-service `ListResponse` field names (`projects[]` / `projectRoles[]` / `applications[]` / `authorizations[]` vs `result[]`); `CreateAuthorization` exige `organizationId`, Update/Delete usam `id` (não `authorizationId`); Authorization shape nested (`project.id`, `user.id`); `AlreadyExisting` no matcher; **quirk 28** — Login UI v2 auto-provisioning quebrado em v4.15.0 (zitadel/zitadel#8910 + #9293 — `LOGINCLIENT_MACHINE_*` envs causa `unique_constraints_pkey` em `03_default_instance` migration; sem essas envs `zitadel-login` fica em loop `Awaiting file and reading token` eternamente; mitigação Path B `loginV2.required: false`); **v0.5.0 — CD cutover survival kit**: **quirk 29** OIDC `client_id` é o **numeric `clientId` do `oidcConfiguration`** (gerado pelo Zitadel) NÃO o `applicationId` UUID determinístico que você passou em `CreateApplicationRequest` — frontend `VITE_OIDC_CLIENT_ID` wired no UUID retorna `400 Errors.App.NotFound` em todo `/oauth/v2/authorize`; **quirk 30** `ZITADEL_BOOTSTRAP_ENV` (ou qualquer env-driven dev/prod ID selector) silently defaultando pra `dev` em CD cria entidades com IDs do ambiente errado, mismatch silent contra secrets prod, mesmo sintoma `Errors.App.NotFound`; **quirk 31** `ZITADEL_DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED=false` no FirstInstance time quebra a chicken-and-egg dos quirks 25 + 28 — instância nasce com Login UI v1 ativo, operador loga no console post-wipe sem precisar PAT, sem precisar bootstrap rodar primeiro; **quirk 32** nginx-proxy ignora silently containers sem `VIRTUAL_PATH` quando sibling tem `VIRTUAL_PATH=/<algo>` (todas as rotas fora do prefix retornam 404, sintoma é trailing `"-"` upstream nos logs nginx) — fix é declarar `VIRTUAL_PATH=/` + `VIRTUAL_DEST=/` no container "default"; **`ListUsers` per-item field é `userId` não `id`** (proto-confirmed v4.15.0 — code que lê `result[0].id` returns undefined e fallback bogus → `CreateAuthorization` 404 `User could not be found`); **eventstore SQL pra diagnose `password.check.failed`** (`SELECT created_at, event_type FROM eventstore.events2 WHERE aggregate_type='user' AND aggregate_id=...` mostra timeline completa de attempts + change events); **idp-bootstrap Dockerfile pitfalls** (precisa `COPY src/` pra tsx imports + audit do path do YAML em cada release)); **v0.6.0 — Console UI human-user creation pitfalls** (manual operator flow only, NOT triggered by API/bootstrap): **quirk 33** Console v4 "Add Human User" form auto-truncates `Username` to email's local-part on auto-fill — combined with `userLoginMustBeDomain=false` default, `loginName` drops the `@domain` and end users get **"O usuário não pôde ser encontrado" / "User could not be found"** when typing their full email; **quirk 34** `userLoginMustBeDomain=true` (Settings → Domain settings → "Add Organization Domain as suffix to loginnames") **stamps loginNames irreversibly** on existing users, disabling + Reset to Instance default does NOT undo, doubly hostile in self-hosted because org `primaryDomain` auto-generates as `<orgSlug>.<externalDomain>` (not the company email domain) so toggling without a custom domain produces nonsensical or double-suffixed loginNames; **quirk 35** Console "Add Human User" leaves "E-mail Verificado" / "Email verified" **unchecked by default**, first login then stalls on SMTP code prompt that never arrives in self-hosted setups where SMTP is deferred); **v0.7.0 — Production-cutover quirks** (validade_bateria_estoque PR #9): **quirk 36** backend container that validates JWT needs `extra_hosts: idp.<domain>:host-gateway` when IdP is co-located on a VPS with unreliable hairpin NAT — `jose.createRemoteJWKSet` reload after the 600s `cacheMaxAge` TTL silently fails the network fetch, causing **401-storm starting at ~10min uptime** with JWT `iss`/`aud`/`exp`/`kid` all verifiable by hand (third documented cause of "401-storm with apparently-valid JWT" alongside quirks 12 and 13); fix is `extra_hosts` mapping to docker bridge (same path external traffic takes), apply to ANY co-located container (bootstrap, observability, runners); also covers logging tip — use `pino.warn` not `console.error` for `JOSEError` because the same path fires for malformed tokens from clients (log-spam vector at `error` level); **quirk 37** frontend defense-in-depth against 401-storm-revokes-session requires THREE coordinated layers, not just dedupe: **L1** dedupe lives in `ApiClient` with `pendingRenew` instance field cleared in `.finally()` + public `refreshToken()` method shared between 401-retry path AND `addAccessTokenExpiring` handler (provider-level `useRef` dedupe alone leaves the expiring path leaking — same RT used by both sides → Zitadel detects reuse → revokes session); **L2** TanStack Query `retry` predicate filters `ApiError 401` because 401 is not transient (retrying amplifies the storm); **L3** listener for `apiclient:unauthorized` CustomEvent in `<AuthProvider>` with `isAuthRoute()` early-return guard + `state: { returnTo: location.pathname+search+hash }` on `signinRedirect` (without guard a 401 from `/auth/callback` triggers another redirect → loop; without `state.returnTo` user lands on `/` after re-auth instead of where they were); each layer addresses a different race and skipping any one leaves a known leak path. **v0.8.0 — smoke-e2e CI quirks**: **quirk 38** `ZITADEL_FIRSTINSTANCE_PATPATH` bind mount EACCES cascading into misleading `unique_constraints_pkey`; **quirk 39** default password policy 4-class trap (`openssl rand -hex` is lowercase-only, dies with `COMMA-VoaRj`); **quirk 40** `zitadel-login` healthcheck slow on small CI runners. **v0.9.0 — real-browser smoke from sales_quote T150**: **quirk 41** idempotent bootstrap creates initial user grants but does NOT reconcile existing ones when YAML evolves — adding a new app + role leaves pre-existing seed user grants stuck at day-0 `roleKeys`, JWT ships missing the new role, symptom collides with quirks 11/12/13/36/28 family but a brand-new user via the same bootstrap works fine (that asymmetry is the diagnostic); cure is search-then-PUT via Quirk 8 pattern. **Quirk 42** browser SPA → backend Express needs CORS or every preflight `OPTIONS` hits `authJwt` and 401s, mimicking the 401-storm family; key diagnostic asymmetry is `curl -H "Authorization: Bearer <JWT>"` returns 200 (no Origin → no preflight) while the browser fails 100%; MSW/supertest integration tests miss this entirely; cure is minimal CORS middleware as FIRST app-level middleware, short-circuiting OPTIONS with 204 + headers. Plus a new `spa-recipes.md` recipe — **'E2E browser tests (Playwright) against self-signed Zitadel'** — covering `ignoreHTTPSErrors: true` (browser-side counterpart of Quirk 12's `NODE_EXTRA_CA_CERTS`), conditional username fill for `login_hint`-prefilled flows in Login UI v1, and the `storageState`+`InMemoryWebStorage` reuse caveat. References: `migration-v2-to-v4.md` (full upgrade runbook — pre-flight, schema migration, validation matrix, rollback) and `api-v1-to-v2-mapping.md` (Connect protocol mapping). Bundles working `docker-compose.zitadel.yml`, idempotent `bootstrap-zitadel.ts` (annotated with `// v2 equivalent` comments) and `reset-zitadel.sh` |
| **ticket** | 1.0.1 | Development | Jira ticket lifecycle for JRC Brasil projects integrated with Git — `/ticket start \| split \| close \| status`. Per-repo project detection via `.jira-project` (PROJECT/BOARD/BRANCH_PREFIX, optional BASE_BRANCH) — no hardcoded project. Prefers `acli` + atlassian MCP (markdown comments, story-points/sprint custom fields `acli` can't write). **v1.0.0** initial packaging, capturing two production-proven lessons: (1) **transitions are PROJECT-SPECIFIC** — discover via `getTransitionsForJiraIssue` and transition by id (RS: `Em andamento→Aprovação→Finished`; SQ: `Em andamento→Concluído` via id 31, no Aprovação), and `acli --status` matches the DESTINATION STATUS name so `--status "Concluído"` works (the transition name "Itens concluídos" fails) → MCP transition-by-id stays a robust alternative; (2) **base branch is project-specific** (optional `BASE_BRANCH`, default = repo's detected default branch) — don't assume `develop` (SQ/sales_quote uses `main`). **v1.0.1** corrects the acli transition guidance (the v1.0.0 corollary was inverted) |
| **whisper-preprocess** | 1.0.0 | Development | Audio→text pipeline (ffmpeg + OpenAI Whisper), 100% offline — extract, silence-removal, voice enhancement, segmentation, transcription (optional 2-language pass + auto-merge). **v1.0.0** initial packaging of the local skill, capturing the anti-"picotamento" (choppy/pumping voice) lessons proven against a real 65-min recording with a low-volume, impaired (dysarthric) speaker: (1) the listenable `*_enhanced.opus` is now **decoupled** from the transcription chain — it used to inherit `silenceremove` + a fast-release `acompressor` + single-pass dynamic `loudnorm` AGC (three stacked gain-modulation/chopping sources); `build_listenable()` builds the listening copy from the **original** file at 48 kHz with **no silence removal** (continuous audio) and **stable gain only** (slow-release compressor + makeup + true-peak `alimiter`), no dynamic AGC; (2) a 2-pass `loudnorm linear=true` is **not reliable** — on a clipping source it silently reverts to `Normalization Type: Dynamic` (verified via `print_format=summary`), reintroducing the pump; (3) **Opus adds inter-sample overshoot above the limiter ceiling** (a -1.5 dBFS sample limit measured +1.3 dBTP after Opus) so the limiter needs headroom (`--listen-limit 0.6`) to keep the decoded true-peak below 0 dBFS — the old recipe clipped at +0.7 dBFS; (4) gentler `silenceremove` (`detection=rms`, `window=0.025`, `stop_silence=0.5`, `stop_duration=2.0`) helps Whisper on slow/quiet speakers while the -30dB threshold lesson is kept; `afftdn` stays opt-in/off (musical-noise risk, `arnndn` preferred). Listening copy now encoded `-application audio` 48k/64k (was narrowband `voip`) |
| **wsl-windows-onboarding** | 0.2.1 | Development | End-to-end onboarding of a Windows machine to WSL2 — diagnose/enable WSL, install **rtk** (`rtk-ai/rtk`), and safely migrate dev projects from `C:\…\repos` into the Linux filesystem. Built from a real migration and encodes the non-obvious gotchas: Docker users already have WSL2 and the **`docker-desktop` distro is NOT your workspace**; rtk is a **zero-dependency Rust binary** whose installer drops it in `~/.local/bin` but does **not** add it to PATH (the #1 "rtk not found" cause), and **one global install serves every project**; **`git clone` drops gitignored `.env`** so migration uses **rsync** (keep `.git` and `.env`, exclude only rebuildable dirs); `/mnt/c` is slow and `du` over it hangs (use `df`, run rsync in background); **validate by diffing file PATHS not counts** (a `.env` inside `node_modules/psl` is a harmless false positive); **copy → validate → delete**, with the irreversible delete last via PowerShell `Remove-Item`; and after migrating a repo `git status` may show the **whole tree modified with zero untracked files** — a CRLF/LF + filemode artifact (`autocrlf`, `0777` from `/mnt/c`), diagnosed with `git diff --ignore-cr-at-eol --stat` + `core.fileMode=false` and fixed by renormalization, not panic. Bundles `wsl-diagnose.sh` (read-only) and `migrate-repos.sh` (rsync + validation, never deletes). **v0.2.0** adds an optional Phase 4 shell setup (`references/shell-setup.md`, deep-research-validated): zsh + oh-my-zsh, default shell via `chsh` (`wsl.conf` can't set it), the **`~/.bashrc` config doesn't carry to `~/.zshrc`** trap (rtk PATH/aliases must be re-added; Ubuntu's empty `/etc/zsh/zprofile` makes the explicit export required), the Docker `_docker` completion warning fix, and **JetBrains Mono Nerd Font + ligatures** on Windows Terminal (`font.features { liga: 1 }`) |

---

## Plugin Details

<details>
<summary><strong>cicd</strong> — CI/CD Troubleshooting & Configuration</summary>

Unified troubleshooting and pipeline configuration for GitHub Actions, Docker, GHCR, and self-hosted runners. Auto-detects backend (Prisma/Biome) or frontend (Vite) projects and routes to specific references.

| Skill | Description |
|-------|-------------|
| `/cicd` | Troubleshoots and configures CI/CD pipelines — 30+ scenarios, 50+ lessons learned (incl. dedicated `self-hosted-runner-docker.md` reference for `myoung34/github-runner` setups com §7 cobrindo o cenário deadlock-em-prod por `RUNNER_REGISTRATION_TOKEN` estática **+ a migração ACCESS_TOKEN in-place como fix durável (lesson 46)**, **+ §8/§9 (lessons 47–49) cobrindo crashloops ortogonais ao token — versão de binário deprecada e config stale reaproveitada**, e `cd-pipeline-pitfalls.md` cobrindo 5 classes de cutover-prod bugs incluindo upstream pool poisoning por `compose run` orphans e §5 sobre container scripts escrevendo paths fora do WORKDIR — ENOENT mascarado por soft-failure que pinta yellow warning ambiente em todo deploy) |

**Highlights:** project-type detection, tagged troubleshooting (`[S]` shared / `[B]` backend / `[F]` frontend), Jest OOM fixes, Biome 2.x migration, stale Docker image cache handling.

</details>

<details>
<summary><strong>codereview</strong> — Automated Code Review</summary>

Stack-agnostic pre-PR code review built on **The Zen of Python** as a universal analysis framework. Five principles — *readability*, *explicitness*, *simplicity*, *flatness*, and *error handling* — applied as analysis lenses to any codebase. Now with **model routing** for 76-86% Opus token savings.

| Skill | Description |
|-------|-------------|
| `/codereview` | Full pre-PR review — diffs against base branch, severity-rated findings (CRITICAL → LOW), final grade (A-F). Uses haiku for git context, sonnet for per-file analysis, opus for cross-file review and report. |
| `/codereview:coderabbit_pr` | Resolves AI review bot comments (CodeRabbit, Copilot, Gemini, Codex) on a GitHub PR — auto-detects reviewers, creates per-reviewer checklists, triages with severity recalibration, applies fixes, runs regression tests, resolves all GitHub conversations |

**Analysis layers:** Bug Detection · Security · **Secrets Detection** (deterministic regex script + optional ggshield/gitleaks, always-on, blocks grade F) · Performance · Type Safety · Test Coverage · Documentation Sync · Race Conditions (TOCTOU) · Accessibility · Data Integrity

**Model routing:** Haiku (git/CLI) → Sonnet (per-file analysis, parallel) → Opus (cross-file review, report)

**Framework presets:** `react` (default) · `vue` · `angular` · `node` · `dotnet` · `generic`

</details>

<details>
<summary><strong>deploy</strong> — Automated Deployments</summary>

Automated deployment commands for staging and production pipelines via CD.

| Command | Description |
|---------|-------------|
| `/deploy:staging` | Syncs main ↔ develop, merges current branch, pushes to trigger CD Staging pipeline |

**Highlights:** auto-detects branch flow (develop vs feature), pre-flight checks (ESLint, TypeScript, Jest), pipeline monitoring via `gh run watch`.

</details>

<details>
<summary><strong>release</strong> — GitHub Release Automation</summary>

Auto-generates categorized release notes from git history and creates a GitHub Release via `gh` CLI.

| Command | Description |
|---------|-------------|
| `/release:release [VERSION] [--path DIR]` | Generates release notes and creates a GitHub Release |

**Multi-stack:** C#/.NET · Node.js · Go · Rust · Python
**Monorepo:** `--path` filter scopes commits to subdirectories
**Contributors:** resolved via GitHub API with org membership cross-reference

</details>

<details>
<summary><strong>statusline</strong> — Status Line Customization</summary>

Interactive wizard to configure Claude Code's status line — model info, context bar, git branch/PR state, cost, and 5h/weekly usage limits.

| Command | Description |
|---------|-------------|
| `/statusline:setup` | Interactive setup wizard — sections, colors, emojis, separator |

**12 composable sections:** Model name · Context bar · Git branch · Project folder · Session cost · Duration · Lines changed · Token counts · Vim mode · 5h usage window · Weekly usage · PR state

Sections 10-12 (5h/weekly usage limits, PR state) are part of the recommended default set and degrade gracefully — usage limits appear only for Pro/Max subscribers, PR state only when the branch has an open PR.

**Effort-level badge (v1.4.0):** when `effortLevel` is set in `~/.claude/settings.json`, the Model section shows it inline (e.g., `🤖 Opus 4.7 [high]`). Re-read on every invocation — no regeneration needed when you toggle the value.

**Cross-platform:** Bash + PowerShell, no jq dependency, Windows/Git Bash compatible.

</details>

<details>
<summary><strong>dotnet-wpf</strong> — .NET WPF Development Toolkit</summary>

Complete development toolkit for C#/.NET WPF desktop applications — from project setup to E2E testing.

| Skill | Description |
|-------|-------------|
| `/dotnet-wpf:dotnet-desktop-setup` | Configures and audits .NET desktop projects for Claude Code |
| `/dotnet-wpf:dotnet-wpf-design` | Fluent Design guide — layout patterns, typography, 90+ WPF-UI controls catalog, date validation traps, Grid row separators (FORM-004), multi-column form layouts, ContentDialog confirmation for destructive actions (CTRL-008) |
| `/dotnet-wpf:dotnet-wpf-mvvm` | WinForms → WPF MVVM migration with CommunityToolkit.Mvvm and WPF-UI |
| `/dotnet-wpf:dotnet-wpf-e2e-testing` | FlaUI + xUnit E2E testing — Page Objects, AutomationId patterns, CI/CD setup |

</details>

<details>
<summary><strong>dev-script</strong> — Local Dev Stack Launcher Generator</summary>

Generates a single-command development launcher for any project — `dev.sh` (bash, Linux/macOS) and `dev.ps1` (PowerShell 5.1/7+, Windows). Detects the stack (compose files, monorepo workspaces, frontend/backend dev servers, IdP, mkcert posture, existing launcher) and emits an idempotent script that brings up Postgres, the IdP, the backend(s), and the frontend with colored per-service prefixes, per-component healthchecks, **two-strategy port handling** (find-next-free port discovery with per-subshell peer-coordination env vars for ports a foreign process might legitimately own, kill-and-reclaim with `fuser` → `lsof` → `ss` → `pgrep` fallback chain for orphans the script itself spawned), trap cleanup, and HTTPS-on-LAN via mkcert + Caddy when the SPA does OIDC PKCE.

| Skill | Description |
|-------|-------------|
| `/dev-script` | Walks the project, confirms the plan, generates `dev.sh` and/or `dev.ps1`, updates `.gitignore`, prints onboarding for LAN clients |

**What it encodes** (the gotchas painfully learned in JRC projects):

- Vite ≥ 5 `allowedHosts` blocks non-localhost — wrap config without editing `vite.config.ts`
- Node backend can't validate JWKS over self-signed HTTPS without `NODE_EXTRA_CA_CERTS`
- Zitadel persists `externalDomain` on init — drift detection + `--reset` flag
- Bootstrap idempotency vs `400 COMMAND-1m88i "No changes"`
- `--tlsMode external` triad (env vars + start flag) for TLS-terminating proxies
- `crypto.subtle` outside secure contexts → `signinRedirect` silently fails
- Process-group cleanup (`setsid` + `kill -- -PGID`) so Ctrl+C doesn't orphan children
- Re-derive `projectId`/`clientId` from `bootstrap.json` on every boot — never hardcode
- **v0.4.0** Foreign port owner + `strictPort` silent-hang cascade (P17) — `kill_stale_ports` against a process the script can't kill silently fails, downstream Vite with `strictPort: true` hard-fails, parent `wait` keeps tracking surviving children → visually identical to a hang. Fix is port discovery + peer coordination instead of port reclaim
- **v0.5.0** CRLF `.env` reads (P18) — Windows/WSL CRLF appends `\r` to `grep|cut` values, so `docker exec "$name\r"` fails `No such container` and the healthcheck times out while every log line looks correct; fix is a `tr -d '\r'` read helper
- **v0.5.0** Cross-platform `node_modules` (P19) — a tree installed on Windows then run on WSL crashes Vite/swc/esbuild with `Failed to load native binding` (missing platform-optional binary); re-install on the target OS
- **v0.5.0** `yarn`↔`cmdtest` collision (P20) — Corepack off by default → `apt install yarn` installs Debian's `cmdtest` (`Parsing scenario file …`); `corepack enable` shadows the impostor and the script resolves the package manager Corepack-aware

**Cross-platform:** Linux/macOS bash and Windows/cross-platform PowerShell — same flags, same semantics, idiomatic primitives in each.

</details>

<details>
<summary><strong>zitadel-idp</strong> — Zitadel Self-Hosted OIDC Field Guide</summary>

Captures patterns and pitfalls discovered while integrating **Zitadel `v4.x` self-hosted** as the IdP for the JRC Brasil ERP. Read this skill BEFORE drafting Zitadel compose files, writing a Management API bootstrap, validating Zitadel JWTs, customizing the Login UI v1, or wiring an SPA via OIDC PKCE — it averages 1–3 hours saved per integration.

| Skill | Description |
|-------|-------------|
| `zitadel-idp` | Field guide with **42** documented quirks (v4-first with proto-aligned `v4.15.0` examples, v2.66.x masterkey edge case, full v2.66→v4 upgrade runbook, Login UI v2 deploy bug + Path B mitigation, CD cutover survival kit, Console UI human-user creation pitfalls, production 401-storm hairpin NAT + 3-layer SPA defense, smoke-e2e CI plumbing checklist, real-browser smoke E2E gaps — seed user grant reconciliation + CORS preflight 401 + Playwright self-signed Zitadel recipe), drill-down references, and bundled working assets |

**Bundled references** (`references/`): `api-cheatsheet.md`, `api-v1-to-v2-mapping.md` (NEW v0.3.0), `branding.md`, `docker-compose-bootstrap.md`, `migration-v2-to-v4.md` (NEW v0.3.0), `spa-recipes.md`, `tenant-org-mapping.md`, `token-validation.md`, `troubleshooting.md`.

**Bundled assets**: `docker-compose.zitadel.yml` (working FirstInstance + volume perms), `bootstrap-zitadel.ts` (idempotent Management API bootstrap with multi-app `applications[]` and env > YAML > hardcoded precedence for dynamic dev hosts), `scripts/reset-zitadel.sh`.

**Highlights of the gotchas encoded:**
- FirstInstance env placement; v1/v2 API split; tenant → `orgId` mapping
- JWT validation over self-signed HTTPS — `NODE_EXTRA_CA_CERTS`, `createRemoteJWKSet` traps, `tlsMode external`, `x-zitadel-orgid`
- Silent-renew byte-match on redirect URIs; `signinSilent` boot-time recursion; StrictMode + closure `cancelled` flag locking SPA in "Verifying session…"
- `post_logout_redirect_uri invalid`; `InMemoryWebStorage` + F5 trap; `crypto.subtle` PKCE secure-context requirement on LAN
- Login UI v1 branding via `privateLabelingSetting`, `custom_login_text`, `LANG-lg4DP`, `405` on `/assets/v1/orgs/me/policy/label/...`
- Idempotent bootstrap `COMMAND-1m88i "No changes"` and `Org-8nfSr "Private Label Policy has not been changed"`
- 401 storm post `--reset-zitadel` from orphaned `tsx watch` / `nodemon` processes holding stale env+JWKS in heap
- Multi-app YAML refactor: env vars from `dev.sh` must dominate static YAML when LAN host is dynamic (`.sslip.io`)

**Scope**: Zitadel `v4.x` self-hosted, OIDC-only (Login UI v1 primary; Login UI v2 deploy bug + Path B mitigation also covered). Out of scope: Zitadel Cloud, v3, SAML, federation IdPs.

</details>

<details>
<summary><strong>ddd</strong> — Domain-Driven Design Toolkit</summary>

Language-agnostic DDD toolkit that audits a codebase for tactical/strategic violations and guides design. Synthesizes Evans, Vernon and modular-monolith practice.

| Skill | Description |
|-------|-------------|
| `/ddd` | Analyzes the codebase for DDD violations, guides strategic design (event storming, context mapping, bounded-context canvas), and generates legacy→DDD migration specs |

**References:** `bounded-context-canvas.md` (DDD Crew v5), `ddd-crew-process.md` (6-phase canonical sequence: Big Picture → Domain Message Flow → BC Canvas → Context Map → Design Level → ADRs), plus tactical/strategic pattern guides.

</details>

<details>
<summary><strong>retrofit-skill</strong> — Apply Session Lessons to a Skill</summary>

Captures non-obvious lessons from the current session and applies them to a target skill, in one of two modes so the workflow matches where the skill lives.

| Command | Description |
|---------|-------------|
| `/retrofit-skill <skill>` | Lists session lessons, filters to the target skill, previews the diff, then applies it |

**Full mode** (skill published in this marketplace): bumps `plugin.json` + `marketplace.json`, updates CHANGELOG and README, commits and pushes.
**Lean mode** (local skill in another repo, e.g. `<repo>/.claude/skills/<name>/`): edits the files + a CHANGELOG entry and commits in that repo — no version bump or marketplace changes.

</details>

<details>
<summary><strong>pdf-generation</strong> — PDF Template Design Toolkit</summary>

Designs PDF generation from reference templates — maps dynamic vs fixed fields, recommends a library with trade-offs, and architects modular sections with conditional columns and revision control.

| Skill | Description |
|-------|-------------|
| `/pdf-generation` | Analyzes a reference template (PDF/Excel), recommends a library (pdfmake, pdf-lib, PDFKit, Puppeteer, @react-pdf), and designs the section architecture |

**Production-proven pitfalls encoded:** cell padding not discounted from `widths` (last column cut off on A4 with 8+ columns); Roboto `fi`/`fl` ligatures drop the `f`; `addFonts()` rejects AFM; header/footer in `content[]` vanish on page 2+; revision cache stale on layout change; SVG fills from a `<style>` block render blank unless inlined. **Phase 6 Visual Verification (NON-NEGOTIABLE)** — render and inspect every page, not just page 1.

</details>

<details>
<summary><strong>ticket</strong> — Jira Ticket Lifecycle (Claude Code only)</summary>

Jira ticket lifecycle integrated with Git for JRC Brasil projects. Per-repo project detection via a `.jira-project` file (PROJECT/BOARD/BRANCH_PREFIX, optional BASE_BRANCH) — no hardcoded project. Prefers `acli` + the atlassian MCP.

| Command | Description |
|---------|-------------|
| `/ticket start \| split \| close \| status` | Create issues/sub-issues + branches, split work, and close with an auto-generated summary |

**Encoded lessons:** transitions are project-specific (discover via `getTransitionsForJiraIssue`, transition by id; `acli --status` matches the destination status name, not the transition name); the base branch is project-specific (optional `BASE_BRANCH`, don't assume `develop`).

</details>

<details>
<summary><strong>whisper-preprocess</strong> — Offline Audio→Text Pipeline</summary>

Audio preprocessing + transcription pipeline (ffmpeg + OpenAI Whisper), 100% offline — extract, silence removal, voice enhancement, segmentation, and transcription (optional two-language pass + auto-merge).

| Skill | Description |
|-------|-------------|
| `/whisper-preprocess` | Runs the full pipeline from a media file (MKV/MP4/WAV/M4A) to text |

**Anti-"picotamento" lessons** (proven on a 65-min low-volume, dysarthric recording): the listenable `*_enhanced.opus` is decoupled from the transcription chain (stable gain only — no dynamic AGC or silence removal); a 2-pass `loudnorm linear=true` silently reverts to dynamic on clipping sources (compressor + limiter used instead); Opus inter-sample overshoot needs limiter headroom (`--listen-limit 0.6`) to keep the decoded true-peak below 0 dBFS.

</details>

## Auto-updates

For private repo auto-updates at startup, set a GitHub token with `repo` scope:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

> [!IMPORTANT]
> Generate a token at [github.com/settings/tokens](https://github.com/settings/tokens) with the `repo` scope.

## Team Distribution

Projects that clone this repo get automatic marketplace discovery via `.claude/settings.json`. When team members trust the folder, Claude Code prompts them to install the marketplace — no manual setup needed.

## Modo de Utilizacao

### Modo Cursor

Use este modo quando quiser trabalhar com as skills no Cursor (ativacao por contexto).

1. Instale via `python install.py` e escolha `Cursor` ou `Both`.
2. Escolha o destino:
   - `~/.cursor/skills/` (uso pessoal em todos os projetos), ou
   - `.cursor/skills/` (uso compartilhado no projeto).
3. Abra o projeto no Cursor e descreva a tarefa em linguagem natural.
4. O agente aplicara automaticamente a skill mais adequada.

Exemplos de pedidos no chat:

```text
Faz um code review das minhas alteracoes antes do PR.
Resolve os comentarios do CodeRabbit no PR #49.
Deploy para staging da branch atual.
Cria a release 2.1.0 com notas de versao.
```

Observacao: o plugin `statusline` e exclusivo do Claude Code.

### Modo Claude Code

Use este modo quando quiser utilizar comandos e skills diretamente no Claude Code.

1. Adicione o marketplace:

```bash
/plugin marketplace add j0ruge/skills_commands_manager
```

2. Instale os plugins desejados:

```bash
/plugin install cicd
/plugin install codereview
/plugin install ddd
/plugin install deploy
/plugin install dev-script
/plugin install dotnet-wpf
/plugin install pdf-generation
/plugin install release
/plugin install retrofit-skill
/plugin install statusline
/plugin install ticket
/plugin install whisper-preprocess
/plugin install zitadel-idp
```

3. Execute os comandos/skills no Claude Code:

```text
/deploy:staging
/release:release 2.1.0
/statusline:setup
/codereview
/codereview:coderabbit_pr 49
```

Para atualizar plugins instalados:

```bash
/plugin marketplace update
```

## References

### Claude Code

- [Plugin Marketplaces — Claude Code Docs](https://code.claude.com/docs/en/plugin-marketplaces)
- [Plugins Reference — Claude Code Docs](https://code.claude.com/docs/en/plugins-reference)

### Cursor support (used to design `install.py` and the `platforms` field)

- [Skills | Cursor Docs](https://cursor.com/help/customization/skills) — official spec for `.cursor/skills/<name>/SKILL.md` and how the agent triggers skills by description
- [Agent Skills | Cursor Docs](https://cursor.com/docs/skills) — agent-side reference, including the limitation that skills are auto-loaded only from project-local `.cursor/skills/` (no global directory)
- [Subagents, Skills, and Image Generation — Cursor v2.4 changelog](https://cursor.com/changelog/2-4) — release that introduced native SKILL.md support in Cursor
- [Where Are Cursor Skills Stored? Paths & Structure (2026)](https://www.agensi.io/learn/where-are-cursor-skills-stored) — confirms there is no `~/.cursor/skills/` global directory; informed the "Staging cache" rename in the installer
- [How to Use SKILL.md Skills in Cursor (2026 Guide)](https://www.agensi.io/learn/how-to-use-skill-md-in-cursor) — practical guidance on SKILL.md frontmatter and the reload-window step
- [Best practices for coding with agents — Cursor Blog](https://cursor.com/blog/agent-best-practices) — context for the trigger-friendly `cursor_description` strings used in command→skill conversions

---

<div align="center">
Proprietary — <strong>j0ruge</strong>. All rights reserved.
</div>
