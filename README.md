<div align="center">

# Chewiesoft Marketplace

*Plugin marketplace for Claude Code and Cursor — CI/CD, code review, deployments, releases, and more.*

[![Plugins](https://img.shields.io/badge/plugins-8-blue?style=flat-square)](#available-plugins)
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
| **release** | ✓ | ✓ | Command (Claude Code) / Skill (Cursor) |
| **retrofit-skill** | ✓ | ✓ | Command (Claude Code) / Skill (Cursor) |
| **statusline** | ✓ | — | Claude Code only (uses the Claude Code status line API) |
| **zitadel-idp** | ✓ | ✓ | Skill — Zitadel self-hosted OIDC integration field guide (bootstrap, JWT, branding, 32 gotchas with proto-aligned v4.15 examples + CD cutover survival kit (BOOTSTRAP_ENV default, OIDC client_id numeric vs UUID, DefaultInstance feature flags, nginx-proxy VIRTUAL_PATH gotcha) + v2.66→v4 upgrade runbook + API v1→v2 mapping) |

## Installation

### Claude Code

```bash
# Add the marketplace (pick one)
/plugin marketplace add j0ruge/skills_commands_manager          # via GitHub
/plugin marketplace add git@github.com:j0ruge/skills_commands_manager.git  # via SSH
```

Then install any plugin:

```bash
/plugin install codereview    # or: cicd, deploy, release, statusline, dotnet-wpf, ddd, retrofit-skill
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
| [**cicd**](#cicd) | 2.9.0 | Development | CI/CD troubleshooting for GitHub Actions, Docker, GHCR, and self-hosted runners (systemd-on-host **e containerizado via `myoung34/github-runner`**) — cobre CMD-herdado-zerado, env `LABELS` vs `RUNNER_LABELS`, `EPHEMERAL`+`restart:always` loop, `gpg --dearmor` em buildkit, deploy keys per-repo unique, `.env` leading whitespace + `sed` silenciando, monorepo workspace hoisting diagnosis, vitest jsdom→happy-dom recipe pra msw v2. Reference dedicada `cd-pipeline-pitfalls.md` cobre 4 classes de bugs de cutover prod: (1) VITE/CRA/Next build args bake'd no image, **frontend rebuild mandatory** quando secret muda, trap do prefixo `/api` que diverge entre default e build args (sintoma é 404 em todas chamadas API após login funcionar); (2) operator clone do repo no host de deploy reconciliando running stack pra spec stale via `docker compose -f` (+ runbook canonical path que não existe quando deploy é via runner workspace); (3) `docker compose --profile X run` reconciliando containers de outros services; (4) `compose run --rm` orphan + nginx-proxy/Traefik upstream poisoning — one-off cuja `--rm` falha (CI cancel / OOM / daemon restart) herda `VIRTUAL_HOST` do serviço e é registrado no upstream pool pelo docker-gen, round-robin manda ~50% das requests pra config stale, sintoma é 401 inconsistente em prod com JWT comprovadamente válido. Inclui o diagnóstico canônico de 5 segundos (20 hits paralelos com mesmo token = split de status codes = pool poisoned) antes de mergulhar em jose/JWKS/aud/iss. **(NEW v2.9.0) `self-hosted-runner-docker.md` §7** — `secrets.RUNNER_REGISTRATION_TOKEN` estática é equilíbrio frágil que vira chicken-and-egg em prod (deploy queued sem runner, runner não sobe sem deploy). Recovery em 3 passos coordenados: rotacionar GH secret + apagar registro fantasma + bring-up via `compose -p <project> up -d --no-deps runner` (não `docker run`, que falta labels compose e bate em conflict no próximo CD `up`). Inclui ladder de diagnóstico p/ runner conteinerizado offline e fix permanente (token a quente no workflow OU PAT no compose centralizado). Também §5b em `self-hosted-runner-docker.md` — multi-job CD exaure ephemeral token mesmo dentro da janela de 1h, fix exige update em **dois** lugares (GH secret + `.env` no host) |
| [**codereview**](#codereview) | 1.10.0 | Quality | Pre-PR code review with model routing (haiku/sonnet/opus), TOCTOU detection, accessibility, **deterministic hardcoded secrets detection** via Python regex script + optional ggshield/gitleaks (GitGuardian-equivalent, blocks PRs with leaked credentials), and multi-reviewer PR resolver (CodeRabbit, Copilot, Gemini, Codex) with baseline-aware regression testing and **verify-before-trust** validation of reviewer-cited references |
| [**deploy**](#deploy) | 1.4.0 | Development | Automated staging deployment with pre-flight checks and pipeline monitoring |
| [**release**](#release) | 1.3.0 | Development | GitHub Release creation with categorized notes, multi-stack and monorepo support |
| [**statusline**](#statusline) | 1.4.0 | Customization | Interactive status line setup — cross-platform (Bash + PowerShell), 9 sections + optional effort-level badge |
| [**dotnet-wpf**](#dotnet-wpf) | 1.6.0 | Development | WPF toolkit — project audit, Fluent Design guide (90+ controls, form spacing, height clipping, Grid row separators, multi-column layouts, ContentDialog confirmation for destructive actions), MVVM migration, E2E testing |
| **ddd** | 0.3.0 | Architecture | Domain-Driven Design toolkit — codebase analysis, strategic design (event storming, context mapping), legacy → DDD conversion specs |
| **dev-script** | 0.3.0 | Development | Generates `dev.sh` (bash) + `dev.ps1` (PowerShell) launchers tailored to the current project — detects compose/monorepo/IdP/mkcert, emits idempotent script with healthchecks, port reclaim (with `pgrep` fallback for kernels that hide PIDs from `ss`/`lsof`), trap cleanup, HTTPS-on-LAN via mkcert + Caddy when the SPA does OIDC PKCE, Playwright LAN-HTTPS testing recipe, monorepo `kill_known_dev_servers` regex gotcha (path appears before `tsx` in cmdline), `tsx watch --include=.env` so launcher-patched env actually reaches runtime, and the boot-time sanity-check pattern (app warns LOUD when runtime config diverges from launcher's source-of-truth file) |
| **retrofit-skill** | 0.1.0 | Development | Apply non-obvious session lessons to a target skill in this marketplace — bumps version, updates CHANGELOG, marketplace.json and README, commits and pushes |
| **zitadel-idp** | 0.5.0 | Development | Zitadel `v4.x` self-hosted OIDC integration field guide — captures **32** high-friction quirks with proto-aligned examples verified against raw GitHub Zitadel `v4.15.0` (FirstInstance env placement, volume perms, v1/v2 API split, tenant→orgId mapping, JWT validation over self-signed HTTPS via `NODE_EXTRA_CA_CERTS` + JWKS, `loginV2` instance flag, silent-renew redirect URI byte-match, idempotent bootstrap `No changes` 400, TLS-terminating reverse proxy, secure-context PKCE on LAN, boot-time `signinSilent` recursion, StrictMode closure trap, `post_logout_redirect_uri invalid`, Login UI v1 branding via `privateLabelingSetting` / `custom_login_text` / `LANG-lg4DP`, F5 with `InMemoryWebStorage`, 401 storm post `--reset-zitadel` from `tsx watch` zombies, multi-app YAML refactor regression vs dynamic env, Zitadel v2.66.x `--masterkey` flag fix, **v0.3.0**: Login UI v2 as a separate Next.js container (`zitadel-login`) with reverse-proxy split, API v2 idempotence via deterministic IDs, contextual `orgId` moved from header into body, **v0.4.0**: proto-aligned payloads (CreateApplication discriminator = `oidcConfiguration` top-level com `applicationType` / `developmentMode` internos, NÃO `oidc` com `appType` / `devMode`); per-service `ListResponse` field names (`projects[]` / `projectRoles[]` / `applications[]` / `authorizations[]` vs `result[]`); `CreateAuthorization` exige `organizationId`, Update/Delete usam `id` (não `authorizationId`); Authorization shape nested (`project.id`, `user.id`); `AlreadyExisting` no matcher; **quirk 28** — Login UI v2 auto-provisioning quebrado em v4.15.0 (zitadel/zitadel#8910 + #9293 — `LOGINCLIENT_MACHINE_*` envs causa `unique_constraints_pkey` em `03_default_instance` migration; sem essas envs `zitadel-login` fica em loop `Awaiting file and reading token` eternamente; mitigação Path B `loginV2.required: false`); **v0.5.0 — CD cutover survival kit**: **quirk 29** OIDC `client_id` é o **numeric `clientId` do `oidcConfiguration`** (gerado pelo Zitadel) NÃO o `applicationId` UUID determinístico que você passou em `CreateApplicationRequest` — frontend `VITE_OIDC_CLIENT_ID` wired no UUID retorna `400 Errors.App.NotFound` em todo `/oauth/v2/authorize`; **quirk 30** `ZITADEL_BOOTSTRAP_ENV` (ou qualquer env-driven dev/prod ID selector) silently defaultando pra `dev` em CD cria entidades com IDs do ambiente errado, mismatch silent contra secrets prod, mesmo sintoma `Errors.App.NotFound`; **quirk 31** `ZITADEL_DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED=false` no FirstInstance time quebra a chicken-and-egg dos quirks 25 + 28 — instância nasce com Login UI v1 ativo, operador loga no console post-wipe sem precisar PAT, sem precisar bootstrap rodar primeiro; **quirk 32** nginx-proxy ignora silently containers sem `VIRTUAL_PATH` quando sibling tem `VIRTUAL_PATH=/<algo>` (todas as rotas fora do prefix retornam 404, sintoma é trailing `"-"` upstream nos logs nginx) — fix é declarar `VIRTUAL_PATH=/` + `VIRTUAL_DEST=/` no container "default"; **`ListUsers` per-item field é `userId` não `id`** (proto-confirmed v4.15.0 — code que lê `result[0].id` returns undefined e fallback bogus → `CreateAuthorization` 404 `User could not be found`); **eventstore SQL pra diagnose `password.check.failed`** (`SELECT created_at, event_type FROM eventstore.events2 WHERE aggregate_type='user' AND aggregate_id=...` mostra timeline completa de attempts + change events); **idp-bootstrap Dockerfile pitfalls** (precisa `COPY src/` pra tsx imports + audit do path do YAML em cada release)). References: `migration-v2-to-v4.md` (full upgrade runbook — pre-flight, schema migration, validation matrix, rollback) and `api-v1-to-v2-mapping.md` (Connect protocol mapping). Bundles working `docker-compose.zitadel.yml`, idempotent `bootstrap-zitadel.ts` (annotated with `// v2 equivalent` comments) and `reset-zitadel.sh` |

---

## Plugin Details

<details>
<summary><strong>cicd</strong> — CI/CD Troubleshooting & Configuration</summary>

Unified troubleshooting and pipeline configuration for GitHub Actions, Docker, GHCR, and self-hosted runners. Auto-detects backend (Prisma/Biome) or frontend (Vite) projects and routes to specific references.

| Skill | Description |
|-------|-------------|
| `/cicd` | Troubleshoots and configures CI/CD pipelines — 30+ scenarios, 35+ lessons learned (incl. dedicated `self-hosted-runner-docker.md` reference for `myoung34/github-runner` setups com §7 cobrindo o cenário deadlock-em-prod por `RUNNER_REGISTRATION_TOKEN` estática, e `cd-pipeline-pitfalls.md` cobrindo 4 classes de cutover-prod bugs incluindo upstream pool poisoning por `compose run` orphans) |

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

Interactive wizard to configure Claude Code's status line — model info, context bar, git branch, cost tracking, and more.

| Command | Description |
|---------|-------------|
| `/statusline:setup` | Interactive setup wizard — sections, colors, emojis, separator |

**9 composable sections:** Model name · Context bar · Git branch · Project folder · Session cost · Duration · Lines changed · Token counts · Vim mode

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

Generates a single-command development launcher for any project — `dev.sh` (bash, Linux/macOS) and `dev.ps1` (PowerShell 5.1/7+, Windows). Detects the stack (compose files, monorepo workspaces, frontend/backend dev servers, IdP, mkcert posture, existing launcher) and emits an idempotent script that brings up Postgres, the IdP, the backend(s), and the frontend with colored per-service prefixes, per-component healthchecks, robust port reclaim (`fuser` → `lsof` → `ss`), trap cleanup, and HTTPS-on-LAN via mkcert + Caddy when the SPA does OIDC PKCE.

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

**Cross-platform:** Linux/macOS bash and Windows/cross-platform PowerShell — same flags, same semantics, idiomatic primitives in each.

</details>

<details>
<summary><strong>zitadel-idp</strong> — Zitadel Self-Hosted OIDC Field Guide</summary>

Captures patterns and pitfalls discovered while integrating **Zitadel `v4.x` self-hosted** as the IdP for the JRC Brasil ERP. Read this skill BEFORE drafting Zitadel compose files, writing a Management API bootstrap, validating Zitadel JWTs, customizing the Login UI v1, or wiring an SPA via OIDC PKCE — it averages 1–3 hours saved per integration.

| Skill | Description |
|-------|-------------|
| `zitadel-idp` | Field guide with **32** documented quirks (v4-first with proto-aligned `v4.15.0` examples, v2.66.x masterkey edge case, full v2.66→v4 upgrade runbook, Login UI v2 deploy bug + Path B mitigation), drill-down references, and bundled working assets |

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

**Scope**: Zitadel `v4.x` self-hosted, OIDC-only, Login UI v1. Out of scope: Zitadel Cloud, v3, SAML, federation IdPs, Login UI v2.

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
/plugin install dotnet-wpf
/plugin install release
/plugin install retrofit-skill
/plugin install statusline
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
