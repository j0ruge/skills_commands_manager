<div align="center">

# Chewiesoft Marketplace

*Plugin marketplace for Claude Code and Cursor — CI/CD, code review, deployments, releases, and more.*

[![Plugins](https://img.shields.io/badge/plugins-16-blue?style=flat-square)](#available-plugins)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code%20%7C%20Cursor-blueviolet?style=flat-square)](https://code.claude.com)
[![License](https://img.shields.io/badge/license-Proprietary-red?style=flat-square)](#)

</div>

[Installation](#installation) · [Plugins](#available-plugins) · [Auto-updates](#auto-updates) · [Team Distribution](#team-distribution) · [References](#references)

---

A curated dual-platform plugin marketplace for [Claude Code](https://code.claude.com) and [Cursor](https://cursor.com) by **j0ruge**. Each plugin packages production-ready skills and commands that integrate directly into your workflow — no configuration needed beyond install.

## Platform Compatibility

| Plugin | Claude Code | Cursor | Notes |
|--------|:-----------:|:------:|-------|
| **ansible-docker-backup-restore** | ✓ | ✓ | Skill — backup + restore of Dockerized services via Ansible, with a read-only backup-freshness check |
| **cicd** | ✓ | ✓ | Skill — works on both platforms without changes |
| **codereview** | ✓ | ✓ | Skills — adapted automatically by the installer |
| **ddd** | ✓ | ✓ | Skill — works on both platforms |
| **deploy** | ✓ | ✓ | Command (Claude Code) / Skill (Cursor) |
| **dev-script** | ✓ | ✓ | Skill — generates `dev.sh` (bash) + `dev.ps1` (PowerShell) per project |
| **dotnet-wpf** | ✓ | ✓ | Skills — works on both platforms |
| **kaizen-software** | ✓ | ✓ | Skill — Kaizen (continuous improvement) methodology for planning, implementing and maintaining software, plus teaching material; verifies by artifact, not by the tool's label |
| **pdf-generation** | ✓ | ✓ | Skill — PDF template design + library selection (pdfmake/pdf-lib/PDFKit/Puppeteer/@react-pdf), modular sections, visual verification |
| **release** | ✓ | ✓ | Command (Claude Code) / Skill (Cursor) |
| **retrofit-skill** | ✓ | ✓ | Command (Claude Code) / Skill (Cursor) |
| **statusline** | ✓ | — | Claude Code only (uses the Claude Code status line API) |
| **ticket** | ✓ | — | Claude Code only (`/ticket` slash command + Jira `acli` + atlassian MCP) |
| **whisper-preprocess** | ✓ | ✓ | Skill — ffmpeg + OpenAI Whisper offline audio→text pipeline (silence removal, voice enhancement, segmentation, multilingual merge); decoupled stable-gain listening copy (no "picotamento") |
| **zitadel-idp** | ✓ | ✓ | Skill — Zitadel self-hosted OIDC integration field guide (bootstrap, JWT, branding, 47 gotchas with proto-aligned v4.15 examples + CD cutover survival kit + Console UI human-user creation pitfalls + production-cutover v0.7.0 (backend `extra_hosts` for hairpin-NAT IdP, 3-layer SPA defense vs RT-reuse session revoke) + smoke-e2e CI v0.8.0 (admin.pat bind mount EACCES cascade into `unique_constraints_pkey`, default password policy 4-class trap, Login UI v2 healthcheck slow on small runners) + real-browser smoke v0.9.0 (seed user grant reconciliation gap on YAML evolution, browser→backend CORS preflight 401 mimicking JWT failure, Playwright self-signed Zitadel recipe) + admin-console `Failed to fetch` mixed-content v0.10.0 (`api` http vs `issuer` https from `--tlsMode disabled`; recreate, don't `docker start`) + v2.66→v4 upgrade runbook + API v1→v2 mapping) |
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
/plugin install codereview    # or: ansible-docker-backup-restore, cicd, ddd, deploy, dev-script, dotnet-wpf, kaizen-software, pdf-generation, release, retrofit-skill, statusline, ticket, whisper-preprocess, wsl-windows-onboarding, zitadel-idp
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
| [**cicd**](#cicd) | 2.26.0 | Development | CI/CD troubleshooting for GitHub Actions, Docker, GHCR, and self-hosted runners (systemd-on-host **e containerizado via `myoung34/github-runner`**) — cobre CMD-herdado-zerado, env `LABELS` vs `RUNNER_LABELS`, `EPHEMERAL`+`restart:always` loop, `gpg --dearmor` em buildkit, deploy keys per-repo unique, `.env` leading whitespace + `sed` silenciando, monorepo workspace hoisting diagnosis, vitest jsdom→happy-dom recipe pra msw v2. **(NEW v2.12.0) `troubleshooting-shared.md` §1a** — GHCR `net/http: TLS handshake timeout` no `docker login` do deploy job self-hosted é bug DISTINTO de §1 `unauthorized` (TCP conectou mas handshake não completou — credencial é irrelevante); isolation key é build-and-push em ubuntu-latest passar enquanto deploy em self-hosted falha; causa raiz típica é MTU mismatch em VPN/overlay ou TLS-inspection proxy; **Fix A** bash retry wrapper 3x backoff 10s/20s ao redor de `docker login` (20 linhas, sem nick-fields/retry); **Fix B** `mtu: 1400` em `/etc/docker/daemon.json` + restart. Reference dedicada `cd-pipeline-pitfalls.md` cobre **7 classes** de bugs de cutover/CI prod: (1) VITE/CRA/Next build args bake'd no image, frontend rebuild mandatory; (2) operator clone reconciliando stack stale; (3) `docker compose --profile X run` reconciliando containers de outros services; (4) `compose run --rm` orphan + nginx-proxy upstream poisoning (~50% intermittent 401s); (5) container scripts que escrevem upward de `__dirname` batem ENOENT em prod (Dockerfile só copia `packages/<self>/`) — fix canônico é try/catch best-effort, **v2.11.0 refinement** narrow catch para ENOENT/ENOTDIR e propagar EACCES/ENOSPC/EROFS preserva visibilidade de problemas reais em dev (especialmente importante quando `bootstrap.json` é consumido por sanity check downstream); **v2.11.0 §6** — GHA bind mount uid mismatch: container vendorado roda uid 1000 (Postgres, Zitadel, vários), runner GHA `ubuntu-latest` é uid 1001 com pasta 0755 → EACCES no init/setup, e o estado parcial deixado para trás cascata em erros DIFERENTES nas retries (constraint violation, already-exists), burying the real cause; cura é pre-create do bind mount com `chmod 0777`; **v2.11.0 §7** — `docker compose up -d --wait` espera TODOS os serviços com healthcheck por default; um sibling lento (Next.js/Vite ~90s+ no runner pequeno) estoura `--wait-timeout` da stack inteira; cura é passar service names explícitos no `up --wait` + companion sempre dumpar logs do serviço lento no on-failure (`|| true`) mesmo quando não está no wait. **v2.9.0 §7 self-hosted-runner-docker** — chicken-and-egg de RUNNER_REGISTRATION_TOKEN estática em prod, recovery em 3 passos. **§5b** — multi-job CD exhaust em janela 1h, fix em 2 lugares (GH secret + .env). **(NEW v2.13.0)** monorepo npm-workspaces (lessons 37–40): backend roda via `tsx`, não `node dist/`, quando os pacotes shared exportam TS source (`main: src/index.ts` → `node dist` dá `ERR_MODULE_NOT_FOUND`); `tsc --noEmit` é VAZIO em tsconfig com project references (`files:[]`) → usar `tsc -b --noEmit`; `npm ci -w` escopado quebra com sibling não declarado (usar `npm ci` cheio); `USER node` + named volume novo = `EACCES` sem `mkdir`+`chown` antes do USER. **`cd-pipeline-pitfalls.md §1b`** — injetar secret de RUNTIME no nginx via templates/`envsubst` (contrapartida do build-arg bake'd). **(NEW v2.14.0)** lessons 41–45 (hardening 017): wrapper PID 1 (`npx tsx`/`npm start`) engole SIGTERM → `init: true`; `tsx`/`prisma` em `dependencies` p/ `npm ci --omit=dev` enxugar a imagem de runtime; composite action p/ DRY do CI gate entre `ci.yml` e `cd-staging.yml`; CI só em `pull_request` deixa push direto a branch protegido escapar do gate; descobrir digest de imagem base via `docker buildx imagetools inspect`. **(NEW v2.15.0)** §7 → **migração ACCESS_TOKEN in-place** é o fix DURÁVEL do `runner-registration 404` recorrente (lesson 46): rotacionar token e `EPHEMERAL:false` NÃO curam (entrypoint re-registra a cada start); trocar `RUNNER_TOKEN` → `ACCESS_TOKEN: ${RUNNER_ACCESS_TOKEN:-}` + `RUNNER_SCOPE: repo`, entrypoint aceita ACCESS_TOKEN OU RUNNER_TOKEN, PAT só no `.env` persistente do host; `gh` NÃO cunha PAT (web UI; `gh auth token` escopo `repo` é stopgap); validar PAT e provar a cura com `docker restart`. **(NEW v2.16.0)** §8/§9 (lessons 47–49) — dois crashloops do runner ORTOGONAIS ao token (mordem até em ACCESS_TOKEN): §8 `Runner version vX is deprecated and cannot receive messages` (runner registra/conecta/lista jobs e só então o GitHub recusa — binário de `:latest` nunca re-puxada + auto-update off; `docker compose pull` + ligar auto-update; footgun: `DISABLE_AUTO_UPDATE` desliga com QUALQUER valor não-vazio, até `0` — para LIGAR, remover a var); §9 `registration has been deleted from the server` (reuso de config ressuscita credencial morta — `docker volume rm <config-volume>`, distinto do §6); pinar a imagem do RUNNER por digest sem `compose pull` mensal é contraproducente (exceção à lição 45). **(NEW v2.17.0)** `self-hosted-runner-docker.md §10` (lesson 50) — §7/§8/§9 podem **EMPILHAR** num mesmo runner: um único deploy `queued` exigiu §9 → PAT `401` → §8 **em sequência**, cada fix desmascarando o próximo (o `docker volume rm` do §9 expõe um `ACCESS_TOKEN` expirado, cujo conserto expõe o binário deprecado; a assinatura do log muda a cada camada). Inclui triagem **"ausente vs offline"** (`gh api …/actions/runners` lista offline também → ausência total = registro apagado/token) e a natureza **host-wide** do PAT (um expira → derruba todos os runners do host). **(NEW v2.18.0)** `self-hosted-runner-docker.md §11` (lesson 51) — **detecção proativa** do deploy `queued` silencioso: um job `[self-hosted, <label>]` fica em fila sem ❌/timeout/e-mail (o `timeout-minutes` não conta em fila, só após pickup do runner), então o root-cause §7–§10 passa **semanas** despercebido (site no ar com a imagem velha). Duas camadas em `ubuntu-latest`: **preflight gate** (lista `/actions/runners`, falha o deploy no push se não há runner online com o label — gotcha: `GITHUB_TOKEN` NÃO lista runners, exige PAT `Administration: Read`; no-op sem o secret) + **watchdog** agendado (`actions:read`, alerta deploy preso — gotchas: status de **JOB** não de run, `schedule` só roda do branch default). **(v2.18.1)** §11 refinado: preflight **fail-open em erro de PAT** — com `set -e` + `ONLINE=$(gh api …)` um PAT expirado/rotacionado bloquearia **todo** deploy com msg enganosa "no runner"; usar `if ! ONLINE=$(…)` + `exit 0` no erro de API (fail-closed só com zero runners). + caveat do PAT host-wide reusado (rotação quebra o gate → atualizar o secret junto). **(NEW v2.19.0)** suporte a **backend Django/gunicorn** (`references/django-backend.md`) — auto-roteia Python além de Node/Prisma. Lição central (lesson 52): **`ALLOWED_HOSTS` sem `127.0.0.1`/`localhost` faz o healthcheck INTERNO do container (`GET 127.0.0.1:8000/healthz/`) responder 400 → container nunca fica `healthy` → o `wait-healthy` do CD estoura mesmo com login/pull/migrate verdes** (isolation key: `GET /healthz/ 400` no log). + admin 403 CSRF sob HTTPS atrás de proxy sem `CSRF_TRUSTED_ORIGINS`/`SECURE_PROXY_SSL_HEADER` (a API JWT não precisa); imagem prod = gunicorn + `collectstatic` em build (SECRET_KEY dummy, sem DB) + WhiteNoise `CompressedStaticFilesStorage` (Manifest quebra dev) + HEALTHCHECK via `python -c urllib` (slim sem curl) + migração one-off `manage.py migrate --noinput`; gotchas cross-stack (valem p/ Node também): owner do GHCR em lowercase (`tr '[:upper:]' '[:lower:]'`), pacote GHCR privado por default → `docker exec` no container rodando p/ one-offs (não `compose run`, que re-puxa sem login), `paths-ignore: ['**.md','docs/**']` p/ não redeployar em commit só de doc. **(NEW v2.19.1)** `self-hosted-runner-docker.md §10a` (lesson 58) — **PAT-401 standalone**: o "fix durável" §7 (migrar p/ PAT dedicado) TEM PRAZO — o PAT gravado no `.env` é ele próprio expirável e **recai no PAT-401 na cadência de vencimento** (visto RECORRER ~1 mês depois; log `curl (22) 401` / `Invalid configuration provided for token` ao `Obtaining the token`, DISTINTO do `404` do §7). No modelo **per-produto** (cada app com seu `runner`+`.env` em `infra/*/`) é **isolado a um runner** — os outros do host seguem UP (o "host-wide" do §10 vale só p/ compose centralizado). Recovery-higiene: o log do runner já é prova definitiva (NÃO re-extraia+`curl`e o secret — casa com exfiltração e um classifier de agente bloqueia); valide o PAT candidato via `gh api …/registration-token` (sessão do gh, sem tocar no secret cru) e grave via **stdin**; fix DURÁVEL de fato = PAT **sem expiração** ou lembrete/cron de rotação. **(NEW v2.20.0)** eixo novo: **prova de deploy**. Duas CORREÇÕES do que a skill ensinava errado — (a) `troubleshooting-shared.md` §3 afirmava que cert self-signed = "LE não emitiu porque o DNS não aponta"; num 1º deploy de produção real os certs **já existiam havia uma hora** e a falha do smoke era **transitória** (o `up -d` recria containers, o docker-gen reconfigura o nginx-proxy e o vhost cai no cert default na janela de reload) — agora a seção tem 3a/3b e um discriminador que vem antes: ler o cert com `openssl s_client … | openssl x509 -noout -issuer -dates`, LE + `notBefore` anterior ao deploy = transiente → `gh run rerun --failed`; (b) os blocos de rollback do SKILL.md terminavam em `up -d --force-recreate`, que só prova que o Docker aceitou o pedido — agora capturam tag imutável e **re-smokam**. Reference nova **`cd-verification-and-rollback.md`** (lessons 59–67): rollback só com `sha-*` (`latest` foi re-apontada por este mesmo deploy); `if: success()` é gate de bom tempo e não roda no deploy que falhou — posicioná-lo **depois** do rollback marca o run vermelho SEM derrubar a app; gate de backup tem de olhar o **artefato** (`gzip -t` + contar `COPY` + registro conhecido), porque um `postgres-backup` ficou **3 meses `healthy` sem gerar um único dump** (o healthcheck observa a porta HTTP de status, não o arquivo) e o banco desprotegido era o do IdP que autenticava todo o resto do host; `prodrigestivill/postgres-backup-local` só faz fan-out de CSV em `POSTGRES_DB`; `vars.X` resolve org → repo → environment; e **ausência de sinal não é prova** — dispare uma sonda deliberada antes de ler captura de log vazia como "sem erros". `cd-pipeline-pitfalls.md` ganha **§1c** (merge **fast-forward** gera o MESMO `GITHUB_SHA` → a tag `sha-*` colide e o build de produção **sobrescreve a imagem de staging** no registry; staging passa a servir produção sem ninguém tocar nele → sufixo de ambiente na tag) e **§1d** (`20-envsubst-on-templates.sh` varre o diretório INTEIRO: snippet de `add_header` em `templates/` vira config de nível `http` e deixa órfão o `include` dos `location` → drop-in próprio entre 20 e 30; e var ausente num `add_header` gera CSP com origem **vazia** — válida, `nginx -t` passa, container `healthy`, smoke verde, e o browser bloqueia API e IdP sem nunca citar CSP). **v2.21.0** adds Actions minute economics — the GitHub billing model rounds **each job up to the minute**, so shaving seconds off a short job saves nothing and parallelising into two jobs *adds* a minute; the lever is moving work to self-hosted runners you already pay for (`references/ci-cost-minutes.md`). **v2.21.1** fixes a triggering hazard that shipped with it: the new clause reached `plugin.json`/`marketplace.json` but not `SKILL.md`, so the description differed by file (620 vs 756 chars) and whether the skill fired depended on which file the harness read. Now one mirrored text at 473 chars, inside the 500 cap. **v2.22.0** adds the other half of that advice — `references/self-hosted-job-migration.md`, what actually breaks when you move a billed job onto a self-hosted runner. Measured over five CI runs: the pre-flight list ranked the risk wrong (`services:` needing Docker, billed as "most likely failure point", passed first try), while three unnamed traps bit — `setup-node` with `cache: 'yarn'` **invoking the yarn binary** the hosted image gave for free (`Unable to locate executable file: yarn`, before any install); `P1001`/refused against a service container that is `healthy` (its healthcheck runs *inside* it, and a containerized runner's `127.0.0.1` is not the host where `-p` published); and `container:`, the obvious fix, failing to start on an outdated runner (`exec: "/__e/node24/bin/node": no such file`). The cure is a **discover-don't-assume** step that probes the bridge gateway (read from `/proc/net/route`, since `ip` is absent) and exports `DATABASE_URL` via `$GITHUB_ENV`. Also new: `ci-cost-minutes.md` §5 — the quota/billing block, whose signature (job `failure` with **zero steps**, empty `runner_name`, ~3s, and `log not found`) reads as a broken build; the message lives only in the check-run **annotations**. That reframes the cost lever: self-hosted bypasses the quota, so moving the CI gate there stops being a saving and becomes what makes the gate **exist**. And a correction to what the skill taught: `paths-ignore` on `pull_request` evaluates the **entire PR diff** (`base...head`), not the push — a docs-only commit still triggers CI on a code-touching PR. **v2.23.0** answers the two questions the `cd-production` migration raised: run `ci`/`build-and-push` on the runner you have already **proven** (staging) and keep only `deploy` on the org-level production runner you cannot even list (`403`) — the image goes to GHCR, production only pulls; and a tag-triggered workflow takes effect only at the **tagged commit**, so merge before cutting the tag (`self-hosted-job-migration.md` §5b). **v2.24.0** covers what happens *after* the runner works — §1–§5b assume the job breaks because the runner lacks something, but on a real migration the runner took the job first try and the **repository** was what was red: 5 tests and an ESLint error accumulated during the quota block, all surfacing in the PR that only meant to change `runs-on`. New §6–§9: the two-PR triage (pipeline PR stays red, honestly — it reveals the debt, it did not create it) plus proving the breakage is pre-existing before you claim it, and the correction that cost an investigation — of those 5, **3 were test setup contradicting its own assertion** (one impossible to satisfy), because tests written during the blind window never ran either; a gitignored `.env` making 9 modules `throw` at import and killing the whole suite (signature: the same error across unrelated files, naming a *module*); a committed `.snap` recording a rendered `href` from `import.meta.env`, so those vars have exactly one acceptable value while the message says only `Snapshot mismatched`; and the subtlest — a **gate job changes meaning when it migrates**: a `preflight` moved onto `[self-hosted, staging]` still passes but goes tautological (offline runner ⇒ it queues too, the very silence it existed to break), while a production preflight running on the *staging* runner keeps its fail-fast, and the scheduled watchdog **stays hosted** even under the block. **v2.25.0** adds the trap on the other side of the `paths-ignore` advice: a push that changes **no files at all** — which is exactly what creating an environment branch from an existing commit is — matches the filter *vacuously* and triggers nothing. Measured: `staging` was cut, the merge was correct, the self-hosted runner was online, and no deploy ever ran, while the silence read as a successful one. `git commit --allow-empty` falls into the same hole (it is the natural reflex, and it does not work here), and GitHub’s own docs do not cover the case, so confirm it with `gh run list`, not by reading. The fix is a `workflow_dispatch` valve, with the ordering detail that decides whether it exists when you need it: GitHub reads the workflow **from the ref**, so it must already be in the commit the branch points at (`ci-cost-minutes.md` §3b, lesson 81). v2.26.0 prompt audit: origin-project names (hosts, images, containers, `JRC-Brasil/…` repos) become placeholders across checklists, troubleshooting and the runner runbook; the pinned runner version resolves to the current release (GitHub refuses deprecated binaries); version-relative phrasing ("this reference used to say", "measured on 01/09") is gone; lessons 8/57/68/81 and both trigger blocks agree on `paths-ignore` semantics; description trimmed to 8 triggers |
| [**codereview**](#codereview) | 1.18.0 | Quality | Pre-PR code review with tiered model routing, TOCTOU detection, accessibility, **deterministic hardcoded secrets detection** via Python regex script + optional ggshield/gitleaks (GitGuardian-equivalent, blocks PRs with leaked credentials), and multi-reviewer PR resolver (CodeRabbit, Copilot, Gemini, Codex) with baseline-aware regression testing, **verify-before-trust** validation of reviewer-cited references, and **byte-exact verification** (`od -c` / `xxd`) when reviewers cite NUL bytes, BOM, zero-width chars, or other invisible/control characters — `Read` renders those bytes as plain whitespace and silently induces false-positive verdicts. **v1.12.0** hardens Phase A output discipline (literal return template + `END_OF_PHASE_A_REPORT` end-marker) and adds a mandatory orchestrator-side fallback so the F-grade secrets gate never silently degrades when the haiku agent under-reports (running 9 tool calls but final-messaging only `"results returned above"`). **v1.13.0** adds detection pass 6.5.3 "Contract Drift in Tests" — when the diff modifies an exported constant (`export const X = [...] as const`, Zod/Yup/literal-union schemas) and a test file in the codebase asserts that constant literally (`expect(X).toEqual([...])` / `toStrictEqual` / `toMatchObject` / `deepEqual`), cross-check the asserted shape against the current export and flag mismatches as HIGH (public contract) / MEDIUM (internal). Same release also forces the final report's `### Overall Grade` table and `### Recommended Actions` block to ALWAYS render — even on zero-findings happy path, focus-area runs, or token-tight reviews where the model would otherwise collapse them into prose. **v1.14.0** adds detection pass 6.9 "Dead Code & Unused Symbols" plus a dedicated **parallel Dead Code Sweep agent (Phase B2)** — because the per-file analysis agents each see only one file and structurally cannot tell whether an exported symbol is referenced elsewhere, dead code (unused exports, orphaned files, unreachable code, dead deps) needs a whole-repo reference sweep. It runs a hybrid scope (code morto **introduced or orphaned by this PR** first, then a **capped pre-existing** project-health summary) using the repo's own tooling when present (`knip` / `ts-prune` / `vulture` / `depcheck` / Roslyn / `staticcheck`, read-only) and a grep reference deepsearch otherwise, with strong false-positive guardrails (public API, framework/DI/reflection wiring, non-code references, barrels, test-only utils) and a per-finding Confidence. Dead code is hygiene: MEDIUM/LOW only, **never blocks the PR**, and feeds the new **🧹 Dead Code & Cleanup** report section + Recommended Actions → Consider Fixing. **v1.15.0** calibrates pass 6.9's reading of `knip`/`ts-prune` output with two false-positive guardrails learned from a real run: **over-export** (a symbol used only WITHIN its own file is reported as an "unused export" but isn't dead — recommend dropping the `export`, not deleting it) and **regenerable scaffolding** (shadcn `components/ui/**` / `**/generated/**` surfaced in bulk → keep in Bucket B, capped, never an actionable app finding). **v1.16.0** splits that over-export guardrail into two opposite fixes — pure in-file plumbing → drop the `export`; a symbol that's part of an *exported* type-surface/API (e.g. an interface typing an exported hook's return, like `AuthUser` in `UseAuthReturn`) → keep the `export` and mark `@public`/`@internal`, never delete (dropping it can break `tsc -b`/declaration emit with "uses private name") — and makes the within-file/exported-signature grep a mandatory per-symbol check on every "unused export". **v1.17.0** makes `coderabbit_pr`'s mechanical phases deterministic and self-cleaning: reviewer detection, comment extraction and thread resolution now run inline as fixed `gh api`/`--jq`/GraphQL commands instead of prose-prompted subagents (a delegated batch that silently skips a thread is indistinguishable from a clean run), with Phase 5 ending on an `unresolved: 0` assertion that gates completion; extraction is separated from interpretation via a `--jq` projection that drops `diff_hunk`/URLs before they reach any context (delegating to sonnet only above a size threshold) and encodes two non-obvious traps — `.line // .original_line` (null once a comment's diff goes stale) and `select(.body != "")` (empty approval bodies became phantom findings); a new **Phase 6** deletes the `{reviewer}-review.md` checklists on the success path, since a stale checklist from an earlier PR is read by the cross-reviewer check as if it were current (opt out with `--keep-checklists`). Also fixes two real defects: fixes were applied to whatever branch was checked out rather than the PR's `headRefName` (silently landing them on unrelated work), and a reviewer that never ran — e.g. Copilot returning "unable to review — quota limit" — was recorded as "approved without issues", burying a coverage gap. **v1.17.1** closes four coherence defects that a live run of v1.17.0 exposed: the zero-findings checklist is no longer written just for Phase 6 to delete moments later (the determination goes into the final report unless `--keep-checklists` is passed); the "no review comments → stop" error no longer collides with Phase 2's zero-findings path (stop means *no bot posted anything at all* — a reviewer that posted but found nothing, or reported it could not run, must still be reported); Phase 4 is skipped when Phase 3 changed no files, since a before/after comparison with no "after" only burns minutes and makes pre-existing failures look like this run caused them; and Phase 6's cleanup drops its hardcoded filename list plus an unexecutable "plus any {bot-login}-review.md" comment in favour of matching the header this skill writes — which covers unknown reviewers while leaving unrelated project docs like `security-review.md` untouched, where a bare `rm -f *-review.md` would not. **v1.18.0** prompt audit against current models: Phase A (git context, classification, secrets pre-scan) now runs inline instead of in a haiku agent — the fixed commands have one right answer and the agent only added variance and a silently dropped field; 28 of 32 caps-emphasis lines dialed back, the four-way "Forbidden" block for the final sections became one paragraph with the reason, the sales-quote incident left the reference. coderabbit_pr 3.6.0: reviewer registry corrected by measurement (Copilot posts under two logins, the Codex logins did not exist), version-relative phrasing and PR archaeology removed, the pre-fix test baseline placed where it actually runs |
| [**deploy**](#deploy) | 2.2.0 | Development | Promoção para staging (e daí para produção) pelo pipeline de CD que o repo realmente tem. **(v2.0.0 — correção crítica)** A topologia de branches deixa de ser presumida: a versão anterior cravava "push em `develop` dispara o cd-staging" e ainda fazia `git push origin main` para "sincronizar" — num repo com a cadeia `develop → staging → main` isso dispara o **cd-production**, ou seja, deployava produção reportando "staging". Agora o Step 0 lê o `on.push.branches` de cada workflow, monta o mapa branch → pipeline, exige identificar qual branch é gatilho de produção e só empurra a branch-alvo. Junto: pre-flight derivado do lockfile/`package.json` em vez de `yarn`/`eslint src/` hardcoded (que viravam no-op silencioso em npm/monorepo, e `tsc --noEmit` é no-op em tsconfig solution-style → `tsc -b`); gate de CI verde conferindo o `headSha` do commit promovido; promoção por PR com **merge commit** (squash em branch de ambiente cria divergência sobre conteúdo idêntico na promoção seguinte); e sensores de conteúdo exclusivo do alvo + `git diff -- .github/workflows/`, que responde qual pipeline vai rodar quando a promoção altera os próprios workflows. **(v2.1.0)** Step 0b lê o `runs-on` do `cd-*.yml` **no commit promovido**: job hospedado sob bloqueio de cobrança do Actions nunca inicia (assinatura: zero steps, `runner_name` vazio, `log not found`; mensagem só nas annotations) — promover só é seguro se o pipeline-alvo rodar em self-hosted, e se a própria promoção move os jobs para lá é esse push que revive o CD. Junto: PR em conflito não tem run de `pull_request` (checar `mergeable` antes de esperar o verde); a dívida de lint que o alvo traz vira o seu gate; `paths-ignore` explica run ausente em promoção só de docs; e Step 7 prova o deploy pelo dado (`migrate status` no banco-alvo, `docker inspect … Created` × horário do run, HTTP no hostname) em vez de confiar no verde. **(v2.1.1)** O Step 7 passa a ensinar a **ler** os dois campos do `docker inspect`, não só o `Created`: um `Config.Image` **sem prefixo de registry** (`dsr-web:latest` em vez de `ghcr.io/<org>/<img>:staging`) significa que o container foi buildado à mão no host e o pipeline **nunca** entregou ali — medido num caso real em que "container up + hostname 200" foi lido por semanas como pipeline funcionando. E o Step 4 passa a **contar** o backlog: com o CD parado, o primeiro deploy verde não é incremental (15 commits *e* a troca da imagem feita à mão por uma de pipeline nunca executada ali — duas novidades no mesmo instante, impossíveis de separar se algo quebrar). **(v2.2.0)** O Step 7 passa a separar falha **transitória** de falha real: `ERROR: unknown blob` no push ao GHCR — medido *depois* de todas as camadas subirem — não se conserta re-promovendo (isso só gera outro merge commit na branch de ambiente), e sim com `gh run rerun --failed`, que reaproveita o **mesmo run id**, então `gh run watch` e os comandos de prova seguem valendo e o `gh run list` não mostra run novo. Antes de reexecutar, provar pelo `docker inspect … {{.Created}}` que o ambiente ficou intacto: **qual passo falhou decide se o rerun é neutro** — falha em build-and-push é anterior ao deploy, falha em smoke/cleanup é posterior e **redeploya**; e duas falhas iguais no mesmo passo deixam de ser transitórias. Junto, o Step 4 ganha o alvo de rollback para ambiente que só publica tag **móvel** (`:staging` é re-apontada pelo próprio deploy, então depois de promover não sobra nome para a imagem anterior): marcá-la antes do push, o que sobrevive ao `docker image prune -f` do próprio deploy porque prune sem `-a` só remove imagem *dangling*. |
| [**cors**](#cors) | 1.0.1 | Development | Diagnóstico e configuração de **CORS** — o erro que mente sobre a própria causa. A espinha é o método: o `catch` do app embrulha CORS num "falha de rede" e o **curl não reproduz o bloqueio** (ele prova alcance, não permissão — `200` no curl com o browser bloqueado é a *assinatura* de uma falha de CORS, não uma contradição), então o primeiro passo é decidir **qual dos três portões** barrou: CORS, CSP `connect-src` ou mixed content — os três falham idênticos no JS. Traz triagem em um minuto (3 comandos), tabela sintoma→causa com a mensagem literal do Chrome, e uma sonda para colar no console que distingue os portões em uma execução (`cors: THROW` + `nocors: type=opaque` = é CORS; ambos THROW = não é). `configuracao.md` cobre por stack, priorizando o que quebra em produção e não em dev: nginx `add_header` sem `always` (o `500` legítimo chega sem headers e o console **culpa o CORS**), `if` que não herda header, ausência de wildcard de subdomínio no protocolo (daí `map`), ordem do `cors()` antes da auth no Express (preflight não carrega credencial — autenticá-lo é sempre erro), `CSRF_TRUSTED_ORIGINS` do Django que **não é** CORS, ordem de filtro do Spring Security, `allow_origins=["*"]` + `allow_credentials` silenciosamente degradado no FastAPI, e o `Vary: Origin` que nem todo CDN respeita. `seguranca.md` é enfática porque afrouxar é a correção mais rápida e algumas formas são a vulnerabilidade: refletir a origem sem allowlist é **pior que `*`** (funciona com credenciais), `null` na allowlist é explorável via `<iframe sandbox>`, `endsWith`/`includes`/regex sem âncora têm bypass conhecido — e fecha com o que CORS **não** faz (não é auth, não é anti-CSRF, não torna API privada). `casos-limite.md` cobre preflight que não pode redirecionar nem ser autenticado, `Expose-Headers` (paginação e `Content-Disposition` "só quebram em produção"), o **Local Network Access do Chrome 142** (público → localhost por permissão do usuário, substituindo o PNA — parece CORS e não é), e o que só parece CORS: WebSocket, canvas *tainted*, fontes, SSE. v1.0.1 prompt audit: the measured case in `diagnostico.md` keeps its literal Chrome strings and both lessons but loses the internal staging hostnames and the date; the description gets its missing accents |
| [**release**](#release) | 1.3.0 | Development | GitHub Release creation with categorized notes, multi-stack and monorepo support |
| [**statusline**](#statusline) | 1.5.2 | Customization | Interactive status line setup — cross-platform (Bash + PowerShell), 12 sections incl. 5h/weekly usage limits + PR state, optional effort-level badge |
| [**dotnet-wpf**](#dotnet-wpf) | 1.7.0 | Development | WPF toolkit — project audit, Fluent Design guide (90+ controls, form spacing, height clipping, Grid row separators, multi-column layouts, ContentDialog confirmation for destructive actions), MVVM migration, E2E testing v1.7.0 prompt audit across the four skills: the Passo 8 hooks JSON used a non-existent `PreCommit` event and an invalid shape (fixed; pre-commit tests go to a git hook), the mvvm references still registered ViewModels as Transient against the body's own memory-leak rule (aligned to Singleton), a pointer to a non-existent spec now points at the sibling e2e skill, the design skill drops its inline changelog and fixes brush names, origin-project residue (VDAControls, VDRDataAnalyzer, MMSI) is neutralised and caps-emphasis dialed back |
| [**ddd**](#ddd) | 0.4.2 | Architecture | Domain-Driven Design toolkit — analyzes codebases for DDD violations, guides strategic design (event storming, context mapping, bounded-context canvas), generates legacy→DDD migration specs. Language-agnostic; synthesizes Evans + Vernon + modular-monolith practice v0.4.2 prompt audit: the author's e-mail and the JRC brand leave the distributed code examples (→ example.com / Acme), the "out of scope (v0.4.0)" section stops being a diff against a version the model never saw, the sub-agent template drops its numeric word cap, and three caps go back to normal register |
| **dev-script** | 0.5.3 | Development | Generates `dev.sh` (bash) + `dev.ps1` (PowerShell) launchers tailored to the current project — detects compose/monorepo/IdP/mkcert, emits idempotent script with healthchecks, **two-strategy port handling** (find-next-free discovery with peer-coordination env vars for foreign-owned service ports / kill-and-reclaim with `pgrep` fallback for own orphans), trap cleanup, HTTPS-on-LAN via mkcert + Caddy when the SPA does OIDC PKCE, Playwright LAN-HTTPS testing recipe, monorepo `kill_known_dev_servers` regex gotcha (path appears before `tsx` in cmdline), `tsx watch --include=.env` so launcher-patched env actually reaches runtime, the boot-time sanity-check pattern (app warns LOUD when runtime config diverges from launcher's source-of-truth file), and **v0.4.0** P17 — foreign port owner + `strictPort: true` silent-hang cascade (kill silently fails → Vite hard-fails → parent `wait` keeps tracking surviving backend = looks like a hang; fix is pre-flight port discovery with peer-coordination env vars instead of trying to kill foreign processes). **v0.5.0** adds three Windows↔WSL migration pitfalls: P18 — CRLF `.env` silently appends `\r` to values read with `grep\|cut` (`docker exec "$name\r"` → `No such container`, healthcheck times out while every log line looks correct; fix is a `tr -d '\r'` read helper); P19 — `node_modules` built on another platform crashes Vite/swc/esbuild with `Failed to load native binding` (missing platform-optional binary; re-install inside the target OS); P20 — `yarn` resolves to Debian's `cmdtest` impostor (`Parsing scenario file …`) when Corepack isn't enabled (`corepack enable` shadows it; resolve the package manager Corepack-aware) v0.5.3 prompt audit: incident tallies and "bit us" archaeology leave the pitfalls (the rules stay, in the present tense), numeric output caps (5–10 bullets, 10–15 lines) become qualitative, a false ordering constraint and a CVE placeholder are gone, description trimmed to 8 triggers |
| **retrofit-skill** | 0.3.0 | Development | Apply non-obvious session lessons to a target skill in two modes — full (marketplace skill: bumps version, updates CHANGELOG/marketplace.json/README, commits and pushes) or lean (local skill in another repo: edits files + CHANGELOG and commits there, no bump or marketplace changes) **v0.3.0** turns "run the validator" into an actual gate: it runs **before** the commit, its WARNINGS are blocking for the skill being touched (a warning that never fails becomes background noise — 7 plugins drifted to as much as 871 chars under one), README version bumps stop being conditional (a bump *always* changes it; that "if" is how a stale 2.20.0 survived), and a snippet re-reads all four places instead of trusting that the edit landed. Also warns that `git checkout` on the shared `marketplace.json` takes your real edits with it. |
| **pdf-generation** | 1.6.1 | Development | PDF generation design toolkit — analyzes reference templates, recommends libraries (pdfmake/pdf-lib/PDFKit/Puppeteer/@react-pdf), designs modular section architecture with conditional columns, auto-generated observations and revision control. **v1.2.0** adds three production-proven pdfmake pitfalls: cell padding NOT discounted from `widths` (last column silently cuts on A4 with 8+ cols, most painful pdfmake gotcha); Roboto bundled `fi`/`fl`/`ffi` ligatures drop the f (`fiscal`→`fscal`) — **v1.2.1** corrects the cause: pdfkit applies the `liga` substitution but fails to embed the glyph (bundled font is current, not old; confirm via SFNT parse; `@fontsource-variable/*` ships only `.woff2`, unusable by pdfmake); `addFonts()` silently rejects AFM (errors 500 on `getBuffer`). Plus Phase 6 Visual Verification — render bugs only surface in the rendered PDF, never in automated tests. **v1.3.0** adds three visual-verification lessons: render/inspect EVERY page — header/footer in `content[]` (vs the `header`/`footer` slots) vanish on page 2+ (invisible in 1-page tests); conditional/optional field absence ≠ bug (populate the data to verify); hash-by-input revision cache doesn't regenerate on layout/code change (bust the cache). **v1.4.0** adds vector-logo (SVG) handling: pdfmake renders SVG natively via `{ svg, width }` (no svg-to-pdfkit dependency — the "pdfmake can't do SVG" belief is wrong); an SVG whose fills come from a `<style>`/class block renders with NO color unless each `class` is inlined to a `fill=` attribute (silent — only the visual render reveals it); ship a small default vector as a `.ts` string constant so it survives `tsc → dist` builds (which don't copy non-`.ts` files) and gitignored runtime asset dirs (which don't exist on fresh deploy). **v1.6.0** adds two table-width patterns and one pitfall: declare the unit (`R$`/`%`) once in the column header or a caption, never in every cell (the trade is asymmetric — a header that wraps costs one line per page, a cell that wraps breaks every row); measure glyph widths with `fontkit` (already transitive via `pdfmake → pdfkit`) instead of guess-and-re-render; and a `"*"` column **grows past the page** when a cell holds an unbreakable token (serial-number list, URL) — same symptom as the padding pitfall but `widths` are correct, and it fails only on *some* data rows. The trigger is not description length: 84 chars with spaces render fine, 48 chars without spaces overflow by 110pt, so a "long description" stress case does not reproduce it v1.6.1 prompt audit: the undated npm-downloads row (now off by 1.5–8× and inverting the ranking) leaves the library matrix, the pointer to a non-existent `pdf-intelligent-forms` skill is gone, and "(NON-NEGOTIABLE)"/"MUST" return to normal register with their reasons intact |
| **zitadel-idp** | 0.12.0 | Development | Zitadel `v4.x` self-hosted OIDC integration field guide — captures **47** high-friction quirks with proto-aligned examples verified against raw GitHub Zitadel `v4.15.0` (FirstInstance env placement, volume perms, v1/v2 API split, tenant→orgId mapping, JWT validation over self-signed HTTPS via `NODE_EXTRA_CA_CERTS` + JWKS, `loginV2` instance flag, silent-renew redirect URI byte-match, idempotent bootstrap `No changes` 400, TLS-terminating reverse proxy, secure-context PKCE on LAN, boot-time `signinSilent` recursion, StrictMode closure trap, `post_logout_redirect_uri invalid`, Login UI v1 branding via `privateLabelingSetting` / `custom_login_text` / `LANG-lg4DP`, F5 with `InMemoryWebStorage`, 401 storm post `--reset-zitadel` from `tsx watch` zombies, multi-app YAML refactor regression vs dynamic env, Zitadel v2.66.x `--masterkey` flag fix, **v0.3.0**: Login UI v2 as a separate Next.js container (`zitadel-login`) with reverse-proxy split, API v2 idempotence via deterministic IDs, contextual `orgId` moved from header into body, **v0.4.0**: proto-aligned payloads (CreateApplication discriminator = `oidcConfiguration` top-level com `applicationType` / `developmentMode` internos, NÃO `oidc` com `appType` / `devMode`); per-service `ListResponse` field names (`projects[]` / `projectRoles[]` / `applications[]` / `authorizations[]` vs `result[]`); `CreateAuthorization` exige `organizationId`, Update/Delete usam `id` (não `authorizationId`); Authorization shape nested (`project.id`, `user.id`); `AlreadyExisting` no matcher; **quirk 28** — Login UI v2 auto-provisioning quebrado em v4.15.0 (zitadel/zitadel#8910 + #9293 — `LOGINCLIENT_MACHINE_*` envs causa `unique_constraints_pkey` em `03_default_instance` migration; sem essas envs `zitadel-login` fica em loop `Awaiting file and reading token` eternamente; mitigação Path B `loginV2.required: false`); **v0.5.0 — CD cutover survival kit**: **quirk 29** OIDC `client_id` é o **numeric `clientId` do `oidcConfiguration`** (gerado pelo Zitadel) NÃO o `applicationId` UUID determinístico que você passou em `CreateApplicationRequest` — frontend `VITE_OIDC_CLIENT_ID` wired no UUID retorna `400 Errors.App.NotFound` em todo `/oauth/v2/authorize`; **quirk 30** `ZITADEL_BOOTSTRAP_ENV` (ou qualquer env-driven dev/prod ID selector) silently defaultando pra `dev` em CD cria entidades com IDs do ambiente errado, mismatch silent contra secrets prod, mesmo sintoma `Errors.App.NotFound`; **quirk 31** `ZITADEL_DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED=false` no FirstInstance time quebra a chicken-and-egg dos quirks 25 + 28 — instância nasce com Login UI v1 ativo, operador loga no console post-wipe sem precisar PAT, sem precisar bootstrap rodar primeiro; **quirk 32** nginx-proxy ignora silently containers sem `VIRTUAL_PATH` quando sibling tem `VIRTUAL_PATH=/<algo>` (todas as rotas fora do prefix retornam 404, sintoma é trailing `"-"` upstream nos logs nginx) — fix é declarar `VIRTUAL_PATH=/` + `VIRTUAL_DEST=/` no container "default"; **`ListUsers` per-item field é `userId` não `id`** (proto-confirmed v4.15.0 — code que lê `result[0].id` returns undefined e fallback bogus → `CreateAuthorization` 404 `User could not be found`); **eventstore SQL pra diagnose `password.check.failed`** (`SELECT created_at, event_type FROM eventstore.events2 WHERE aggregate_type='user' AND aggregate_id=...` mostra timeline completa de attempts + change events); **idp-bootstrap Dockerfile pitfalls** (precisa `COPY src/` pra tsx imports + audit do path do YAML em cada release)); **v0.6.0 — Console UI human-user creation pitfalls** (manual operator flow only, NOT triggered by API/bootstrap): **quirk 33** Console v4 "Add Human User" form auto-truncates `Username` to email's local-part on auto-fill — combined with `userLoginMustBeDomain=false` default, `loginName` drops the `@domain` and end users get **"O usuário não pôde ser encontrado" / "User could not be found"** when typing their full email; **quirk 34** `userLoginMustBeDomain=true` (Settings → Domain settings → "Add Organization Domain as suffix to loginnames") **stamps loginNames irreversibly** on existing users, disabling + Reset to Instance default does NOT undo, doubly hostile in self-hosted because org `primaryDomain` auto-generates as `<orgSlug>.<externalDomain>` (not the company email domain) so toggling without a custom domain produces nonsensical or double-suffixed loginNames; **quirk 35** Console "Add Human User" leaves "E-mail Verificado" / "Email verified" **unchecked by default**, first login then stalls on SMTP code prompt that never arrives in self-hosted setups where SMTP is deferred); **v0.7.0 — Production-cutover quirks** (validade_bateria_estoque PR #9): **quirk 36** backend container that validates JWT needs `extra_hosts: idp.<domain>:host-gateway` when IdP is co-located on a VPS with unreliable hairpin NAT — `jose.createRemoteJWKSet` reload after the 600s `cacheMaxAge` TTL silently fails the network fetch, causing **401-storm starting at ~10min uptime** with JWT `iss`/`aud`/`exp`/`kid` all verifiable by hand (third documented cause of "401-storm with apparently-valid JWT" alongside quirks 12 and 13); fix is `extra_hosts` mapping to docker bridge (same path external traffic takes), apply to ANY co-located container (bootstrap, observability, runners); also covers logging tip — use `pino.warn` not `console.error` for `JOSEError` because the same path fires for malformed tokens from clients (log-spam vector at `error` level); **quirk 37** frontend defense-in-depth against 401-storm-revokes-session requires THREE coordinated layers, not just dedupe: **L1** dedupe lives in `ApiClient` with `pendingRenew` instance field cleared in `.finally()` + public `refreshToken()` method shared between 401-retry path AND `addAccessTokenExpiring` handler (provider-level `useRef` dedupe alone leaves the expiring path leaking — same RT used by both sides → Zitadel detects reuse → revokes session); **L2** TanStack Query `retry` predicate filters `ApiError 401` because 401 is not transient (retrying amplifies the storm); **L3** listener for `apiclient:unauthorized` CustomEvent in `<AuthProvider>` with `isAuthRoute()` early-return guard + `state: { returnTo: location.pathname+search+hash }` on `signinRedirect` (without guard a 401 from `/auth/callback` triggers another redirect → loop; without `state.returnTo` user lands on `/` after re-auth instead of where they were); each layer addresses a different race and skipping any one leaves a known leak path. **v0.8.0 — smoke-e2e CI quirks**: **quirk 38** `ZITADEL_FIRSTINSTANCE_PATPATH` bind mount EACCES cascading into misleading `unique_constraints_pkey`; **quirk 39** default password policy 4-class trap (`openssl rand -hex` is lowercase-only, dies with `COMMA-VoaRj`); **quirk 40** `zitadel-login` healthcheck slow on small CI runners. **v0.9.0 — real-browser smoke from sales_quote T150**: **quirk 41** idempotent bootstrap creates initial user grants but does NOT reconcile existing ones when YAML evolves — adding a new app + role leaves pre-existing seed user grants stuck at day-0 `roleKeys`, JWT ships missing the new role, symptom collides with quirks 11/12/13/36/28 family but a brand-new user via the same bootstrap works fine (that asymmetry is the diagnostic); cure is search-then-PUT via Quirk 8 pattern. **Quirk 42** browser SPA → backend Express needs CORS or every preflight `OPTIONS` hits `authJwt` and 401s, mimicking the 401-storm family; key diagnostic asymmetry is `curl -H "Authorization: Bearer <JWT>"` returns 200 (no Origin → no preflight) while the browser fails 100%; MSW/supertest integration tests miss this entirely; cure is minimal CORS middleware as FIRST app-level middleware, short-circuiting OPTIONS with 204 + headers. Plus a new `spa-recipes.md` recipe — **'E2E browser tests (Playwright) against self-signed Zitadel'** — covering `ignoreHTTPSErrors: true` (browser-side counterpart of Quirk 12's `NODE_EXTRA_CA_CERTS`), conditional username fill for `login_hint`-prefilled flows in Login UI v1, and the `storageState`+`InMemoryWebStorage` reuse caveat. **v0.10.0 — admin-console mixed-content** (quirk 43): Zitadel's own Console shows `[unknown] Failed to fetch` when the generated `environment.json` renders `api: http://` while `issuer: https://` — mixed content on the HTTPS page; root cause is `--tlsMode disabled` (the binary doesn't trust the proxy's `X-Forwarded-Proto`), compounded by `docker start` reviving a stale container's create-time args; cure is the full Quirk 15 triad + `up -d --force-recreate` (never `docker start`). References: `migration-v2-to-v4.md` (full upgrade runbook — pre-flight, schema migration, validation matrix, rollback) and `api-v1-to-v2-mapping.md` (Connect protocol mapping). Bundles working `docker-compose.zitadel.yml`, idempotent `bootstrap-zitadel.ts` (annotated with `// v2 equivalent` comments) and `reset-zitadel.sh`. **(NEW v0.11.0)** quirks **44–47**, de um cutover de produção real: **44** provar `client_id` + `redirect_uri` **sem credencial nenhuma** — montar a URL do `authorization_endpoint` com PKCE S256 (vetor de teste da RFC 7636; o fluxo nunca é completado) e conferir `302 → /ui/login/login?authRequestID=…`, porque toda verificação de client que a skill tinha exige PAT, o que as torna inúteis no pré-cutover de um ambiente novo; **45** grepar a config OIDC no bundle **servido** (não o de dentro do container — o servido também pega container stale no upstream pool), já que "o secret está setado" e "o bundle contém o valor" são afirmações diferentes e o sintoma da divergência é só "o login não completa"; **46** `ZITADEL_SEED_USER_ROLE` como **lista** quando duas apps dividem o Zitadel — o `CreateAuthorization` grava a lista literal e o `UpdateAuthorization` faz união, então o defeito fica **dormente** até alguém recriar o IdP do zero; **47** + reference nova `multi-instance-and-user-migration.md` — o que precisa divergir entre duas instâncias (token cruzado dá `JWSSignatureVerificationFailed`, que se lê como rotação de chave) e a **assimetria da migração de usuários**: importar hash é suportado (`AddHumanUser`), extrair da origem **não** é (vive no eventstore). Junto: contraparte **positiva** do quirk 36 em `token-validation.md` (o 401-storm é tardio por construção — TTL de ~600s —, então smoke verde em T+30s não diz nada, e um `/health/ready` que devolve `jwks: ok` de cache que nunca revalida mente durante o storm inteiro). v0.12.0 prompt audit: installation-specific data (an operator e-mail, LAN IP, `idp.jrcbrasil.com`) replaced by placeholders, "47 documented quirks" becomes a catalogue that does not age in the trigger text, quirks 38–42/44/45 shrink back to trigger paragraphs with their recipes living in the references (44 and 45 gain sections there), and "Source of truth" points at the skill's own assets instead of another project's files |
| **ticket** | 1.3.0 | Development | Jira ticket lifecycle for JRC Brasil projects integrated with Git — `/ticket start \| split \| close \| status`. Per-repo project detection via `.jira-project` (PROJECT/BOARD/BRANCH_PREFIX, optional BASE_BRANCH) — no hardcoded project. Prefers `acli` + atlassian MCP. **v1.0.0** initial packaging, capturing two production-proven lessons: (1) **transitions are PROJECT-SPECIFIC** — discover via `getTransitionsForJiraIssue` and transition by id (RS: `Em andamento→Aprovação→Finished`; SQ: `Em andamento→Concluído` via id 31, no Aprovação), and `acli --status` matches the DESTINATION STATUS name so `--status "Concluído"` works (the transition name "Itens concluídos" fails) → MCP transition-by-id stays a robust alternative; (2) **base branch is project-specific** (optional `BASE_BRANCH`, default = repo's detected default branch) — don't assume either `main` or `develop` — **detect** it (v1.1.1 corrected a stale claim here: SQ/sales_quote uses `develop`). **v1.0.1** corrects the acli transition guidance (the v1.0.0 corollary was inverted). **v1.1.0** fixes cards landing in the backlog without points: new issues are now **born inside the active sprint** via `acli workitem create --from-json` with `additionalAttributes` (custom fields on create need no MCP — validated on SQ), because the old create-then-edit path silently failed whenever the MCP wasn't authenticated. Adds a mandatory **read-back** after writing sprint/score (plus `sprint list-workitems` as independent proof), field-ID **discovery** via `--fields "*all"` (a plain `--json` returns 5 fields and no custom ones), fallbacks for "no active sprint" (wrong `$BOARD`, JQL `sprint in openSprints()`, kanban boards), and the measured `acli` asymmetry — `create --from-json` accepts `additionalAttributes`, `edit --from-json` rejects it, so an **existing** issue has no non-MCP path. Also documents two traps: sprint id is a **plain number** (`405`, not `{"id": 405}`), and the active sprint is the one with `state: active` **regardless of a past `endDate`**. MCP endpoint migrated from the retired HTTP+SSE (`/v1/sse`, EOL 30-Jun-2026) to Streamable HTTP (`/v1/mcp`), with `/v1/mcp/authv2` noted as the variant that answers with OAuth `resource_metadata` discovery. **v1.2.0** attacks one failure class — **the skill's own verification steps were the thing failing**, always toward the side that looks safe: `acli` prints `✗ Failure` yet **exits 0**; `--assignee` with an e-mail is refused because the session's `userEmail` isn't the Jira account (use `@me`, or accountId via REST); `sprint list-workitems` **paginates (~30)** so a fresh card falls off page 1 and reads as "not in the sprint" (replaced by JQL); and `git pull … | tail` inside an `&&` returns `tail`'s exit, so the branch is born from an unverified base (now measured with `git rev-list --left-right --count`). Two of these had been measured 17 days earlier and re-charged on SQ-107. Adds **fixVersion** end to end — REST-only (`acli` neither writes nor reads it, returning `[]` over a stored value), single-call `POST /rest/api/3/issue` carrying fixVersion + sprint + points + ADF, and the warning that Jira's `released` flag is **not** a release sensor (SQ's 0.7.1 read `unreleased` while live in production — check `origin/main`, not the metadata). Read-back is now **per field**, because the sensor differs by field. `open`/`abrir` alias `start` **v1.3.0** closes the gap the ADF guidance left open: the skill said to build ADF with a script and warned that malformed payloads are refused **without naming the node** — but the script errs too. A helper handed `"strong"` (a string) where it expected a list iterated it character by character, emitting `{"type":"s"}`, `{"type":"t"}`…; the JSON stayed syntactically valid, `json.tool` passed, and Jira answered a **silent 400**. Adds a ~10-line pre-POST sweep that walks the document and fails naming the offending marks (the only accepted ones being `strong`/`em`/`code`/`link`/`strike`/`underline`), a recipe to repair an already-built payload instead of rebuilding it, and the next suspect when the sweep comes back clean — a node `type` outside the table (`bold` for `strong`, `italic` for `em`). |
| **whisper-preprocess** | 1.1.0 | Development | Audio→text pipeline (ffmpeg + OpenAI Whisper), 100% offline — extract, silence-removal, voice enhancement, segmentation, transcription (optional 2-language pass + auto-merge). **v1.0.0** initial packaging of the local skill, capturing the anti-"picotamento" (choppy/pumping voice) lessons proven against a real 65-min recording with a low-volume, impaired (dysarthric) speaker: (1) the listenable `*_enhanced.opus` is now **decoupled** from the transcription chain — it used to inherit `silenceremove` + a fast-release `acompressor` + single-pass dynamic `loudnorm` AGC (three stacked gain-modulation/chopping sources); `build_listenable()` builds the listening copy from the **original** file at 48 kHz with **no silence removal** (continuous audio) and **stable gain only** (slow-release compressor + makeup + true-peak `alimiter`), no dynamic AGC; (2) a 2-pass `loudnorm linear=true` is **not reliable** — on a clipping source it silently reverts to `Normalization Type: Dynamic` (verified via `print_format=summary`), reintroducing the pump; (3) **Opus adds inter-sample overshoot above the limiter ceiling** (a -1.5 dBFS sample limit measured +1.3 dBTP after Opus) so the limiter needs headroom (`--listen-limit 0.6`) to keep the decoded true-peak below 0 dBFS — the old recipe clipped at +0.7 dBFS; (4) gentler `silenceremove` (`detection=rms`, `window=0.025`, `stop_silence=0.5`, `stop_duration=2.0`) helps Whisper on slow/quiet speakers while the -30dB threshold lesson is kept; `afftdn` stays opt-in/off (musical-noise risk, `arnndn` preferred). Listening copy now encoded `-application audio` 48k/64k (was narrowband `voip`) v1.1.0 prompt audit: the instructions now say to copy both scripts (the bilingual merge imports `merge_passes` and silently produced no merged transcript with only one file), lesson #9 is rewritten in the present tense instead of as a session changelog, "NEVER use afftdn" is scoped to the transcription path (the script has `--denoise`), and the troubleshooting table drops its "old/fixed" archaeology |
| **ansible-docker-backup-restore** | 1.3.2 | Development | Backup and restore of a Linux server's Docker services with Ansible. Restore half: the silent compose-project-name trap (wrong prefix ⇒ brand-new empty volume, containers up, no error), an 8-step anti-overwrite guard that never deletes before the replacement is on disk and verified, SQL-dump guards that count rows instead of trusting schema presence, and a reverse-proxy/TLS gate — a config directory that is a volume survives a disk swap while a sibling that is not one dies, leaving an orphan directive that takes down **every** HTTPS vhost on the host the moment a container claims the domain. Backup half: the four ways a nightly backup dies without a sound — `ignore_errors` + `no_log` on the same task, the same root cause on a task *without* `ignore_errors` (aborts the play, looks like slowness), `set -euo pipefail` meeting `tar` rc=1 on a live database datadir (alphabetical volume order makes it look intermittent), and a fixed path that stopped existing after a restore. Ships a read-only freshness check (gaps in the date sequence, one dump per database, undersized dumps, volume coverage, retention arithmetic vs real free space). **v1.1.0** adds the edges found bringing a sibling server that *never had a backup* online, with three stacked blockers: the SSH push path is a per-host prerequisite that can silently not exist (verify from *each* client, don't generalize) and must be granted least-privilege (a dedicated `rrsync -wo` key proven to open no shell, so the backup host can't become a lateral-movement pivot); a preflight that checks `docker ps` vs the inventory **both ways** (running-but-undeclared DB is dumped by no one and errors nowhere); bind mounts escape `docker volume ls` (DB dumps present gives false coverage while a bind-mounted datadir is missed); `delegate_to` on a shared `authorized_keys` from parallel hosts races (`throttle: 1`); and history rewrites can't scrub a weak password equal to a public identifier — only rotation can. **v1.2.0** adds the lessons from a service everyone believed restored for four days that was in fact broken in two places, both of which passed a green playbook: a restored MySQL datadir carries each user's **authentication plugin**, not just the password, so `caching_sha2_password` refuses old clients (`DBD::mysql`, older `mysqli`, old JDBC) with the entirely correct password — and the compose flag `--default-authentication-plugin` does *not* fix it, since it only governs users created after it; the failure shows in one client and not another (the PHP UI stayed up while the Perl agent endpoint was down for a week), so verify **every entry plane**, because the one still standing masks the one that fell; proof-of-content is promoted from advice to role contract (`verify_body_contains`, empty by default) after the very domain cited in the reference spent four more days serving the web server's default page; a log error pointing at teardown code (`rollback`, `finally`, a destructor) is usually the error handler failing on top of the real fault, which is typically **suppressed by default** — raise verbosity before theorizing, and revert it in the same script; and `lineinfile` whose `regexp` matches nothing silently **appends** the line at end of file, landing outside every config block, inert, and reports `changed`. **(NEW v1.3.0)** o achado veio de fora, num deploy de produção de outro produto no mesmo host: o container de backup do ERP e do IdP estava `unhealthy` desde 06/05/2026 e **nunca havia gerado um único dump** — três meses. **§1.1 tamanho é proxy fraco**: a skill parava na heurística `-size -1k` ("um dump que é só a mensagem de erro tem poucos bytes"), que pega o caso grosseiro e deixa passar o inverso — **um dump só com o schema é grande, bem formado e inútil para restaurar**; três perguntas em ordem de custo (`gzip -t`, contar blocos `COPY`, e **um registro conhecido**, a única que distingue "dump válido" de "dump DESTE banco"). **§1.2 o healthcheck de container de backup mede a coisa errada**: essas imagens observam a porta HTTP de status que elas próprias expõem, não o artefato, então o container fica genuinamente `healthy` enquanto o `pg_dump` falha todas as noites (no caso real, lista CSV em `POSTGRES_HOST`/`POSTGRES_USER`, onde o valor é literal → `pg_dump` autenticando com o usuário `erp,zitadel`; a imagem só faz fan-out de lista em `POSTGRES_DB`). **`provas-que-nao-mentem.md` §4b — a ausência de sinal também não prova nada**: o arquivo cobria só o gêmeo oposto (§1 "um 301 não prova nada", §4 "um 200 também pode mentir"), e vazio é produzido por dois mundos indistinguíveis — nada aconteceu, ou o instrumento nunca esteve vivo; cura é provocar um positivo que você mesmo causou. `check-backup-freshness.sh` ganha `gzip -t` e detecção de dump schema-only; Gate 2 ganha um passo. v1.3.2 prompt audit: an installation's user names (`erp,zitadel`) become placeholders in the silent-failure example (the probe showed the model repeating them on other hosts), and the "how this section aged" paragraph turns into the lesson itself; scripts and assets untouched |
| **kaizen-software** | 1.3.0 | Development | Kaizen (continuous improvement) methodology for planning, implementing and maintaining software — and for teaching Kaizen to the team. Drives the three phases through PDCA (plan sliced into small verifiable increments, jidoka "stop the line" during implementation, 5 whys + 5S during maintenance) and keeps a `KAIZEN_LOG.md` as the team's institutional memory. **v1.0.0** initial packaging of the local skill: the description was rewritten to fit the `/skills` budget (the original ~1000-char one, opening with "use SEMPRE", risked being dropped silently — which disables the trigger it was trying to strengthen), and the Kaizen Log template gained the two subsections that real use proved most consulted — "Desperdícios evitados (cortes conscientes)" (a deliberate cut reads as an oversight six months later, and someone reopens a scope that was rejected for good reason) and "O que aprendemos" (the technical gotcha the next person would otherwise rediscover). Defers to repo conventions: where refactoring without an explicit request is forbidden, the boy-scout rule becomes a logged opportunity, not an edit **v1.1.0** names the idea that three separate findings in one real session turned out to share: `Rótulo ≠ artefato` — a tool's label describes the process, and the process can be fine while the thing that should exist does not (a backup container reporting `healthy` before it ever produced a dump; `PR MERGED` describing what the PR consumed, not what the branch holds now). The same defect showed up inside the log itself, so the `Padronizado em` field now has to be verified against the file it names — it is the one line that asserts something about the world outside the log. Poka-yoke gains its most common failure mode (a home-made probe that measures a proxy alarms falsely and teaches the operator to ignore it, so sabotage it on purpose and check both states), and phase 3 gains **Ações irreversíveis**: when an increment cannot be reverted, ordering does the work reversibility used to — slice so the reversible step runs first and surprises surface while they still cost a check **v1.2.0** poka-yoke enters the operational flow, not just the teaching glossary: a standardization ladder (error-proofing > template/script > written rule) in principle 6, the "which poka-yoke makes this error impossible?" question in phases 1–3 and in the 5-whys countermeasure field; plus a prompt audit against current models (description consolidated to 8 triggers, a caps word and a domain leak removed) **v1.3.0** seven more Kaizen concepts become operational steps instead of glossary entries: yokoten (spread the root cause fix to every neighbour), andon (stop visibly, never fix in silence), Ishikawa when the 5 whys branch, mura/muri in the waste hunt, a decision rule for kaikaku, the 8th waste (unused talent/knowledge) and gemba without a ticket |
| **wsl-windows-onboarding** | 0.4.2 | Development | End-to-end onboarding of a Windows machine to WSL2 — diagnose/enable WSL, install **rtk** (`rtk-ai/rtk`), and safely migrate dev projects from `C:\…\repos` into the Linux filesystem. Built from a real migration and encodes the non-obvious gotchas: Docker users already have WSL2 and the **`docker-desktop` distro is NOT your workspace**; rtk is a **zero-dependency Rust binary** whose installer drops it in `~/.local/bin` but does **not** add it to PATH (the #1 "rtk not found" cause), and **one global install serves every project**; **`git clone` drops gitignored `.env`** so migration uses **rsync** (keep `.git` and `.env`, exclude only rebuildable dirs); `/mnt/c` is slow and `du` over it hangs (use `df`, run rsync in background); **validate by diffing file PATHS not counts** (a `.env` inside `node_modules/psl` is a harmless false positive); **copy → validate → delete**, with the irreversible delete last via PowerShell `Remove-Item`; and after migrating a repo `git status` may show the **whole tree modified with zero untracked files** — a CRLF/LF + filemode artifact (`autocrlf`, `0777` from `/mnt/c`), diagnosed with `git diff --ignore-cr-at-eol --stat` + `core.fileMode=false` and fixed by renormalization, not panic. Bundles `wsl-diagnose.sh` (read-only) and `migrate-repos.sh` (rsync + validation, never deletes). **v0.2.0** adds an optional Phase 4 shell setup (`references/shell-setup.md`, deep-research-validated): zsh + oh-my-zsh, default shell via `chsh` (`wsl.conf` can't set it), the **`~/.bashrc` config doesn't carry to `~/.zshrc`** trap (rtk PATH/aliases must be re-added; Ubuntu's empty `/etc/zsh/zprofile` makes the explicit export required), the Docker `_docker` completion warning fix, and **JetBrains Mono Nerd Font + ligatures** on Windows Terminal (`font.features { liga: 1 }`) v0.4.2 prompt audit: source-path discovery no longer assumes the author's `source\repos` layout, the "on current WSL" claim becomes "use the name exactly as `wsl --list --online` prints it", "150 files" becomes whole-tree, and a CRITICAL heading returns to normal register |

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
<summary><strong>cors</strong> — Cross-Origin Resource Sharing</summary>

Diagnóstico e configuração de CORS, organizado em torno de um fato: **o sintoma mente**. O `catch` do app traduz o bloqueio para "serviço indisponível", e o `curl` — que não implementa a same-origin policy — devolve `200` alegremente. Nasceu de uma sessão real em que essas duas mentiras juntas custaram duas tentativas antes de alguém abrir o console.

| Skill | Description |
|-------|-------------|
| `/cors` | Decide qual portão barrou (CORS × CSP `connect-src` × mixed content), lê a mensagem literal do Chrome, e dá a receita por stack (nginx, Express, Django, Spring, FastAPI, CDN/API Gateway) |

**Highlights:** triagem em 3 comandos · sonda de console que separa os portões em uma execução · `add_header` sem `always` fazendo um `500` legítimo virar "erro de CORS" · preflight que não pode redirecionar nem ser autenticado · `Vary: Origin` e cache poisoning em CDN · reflexão de origem, `null` e bypass de regex · Local Network Access do Chrome 142 · checklist de fechamento.

</details>

<details>
<summary><strong>codereview</strong> — Automated Code Review</summary>

Stack-agnostic pre-PR code review built on **The Zen of Python** as a universal analysis framework. Five principles — *readability*, *explicitness*, *simplicity*, *flatness*, and *error handling* — applied as analysis lenses to any codebase. Now with **model routing** for 76-86% Opus token savings.

| Skill | Description |
|-------|-------------|
| `/codereview` | Full pre-PR review — diffs against base branch, severity-rated findings (CRITICAL → LOW), final grade (A-F). Gathers git context inline, uses sonnet for per-file analysis and the main model for cross-file review and report; was: haiku for git context, sonnet for per-file analysis, opus for cross-file review and report. |
| `/codereview:coderabbit_pr` | Resolves AI review bot comments (CodeRabbit, Copilot, Gemini, Codex) on a GitHub PR — auto-detects reviewers, creates per-reviewer checklists, triages with severity recalibration, applies fixes, runs regression tests, resolves all GitHub conversations |

**Analysis layers:** Bug Detection · Security · **Secrets Detection** (deterministic regex script + optional ggshield/gitleaks, always-on, blocks grade F) · Performance · Type Safety · Test Coverage · Documentation Sync · Race Conditions (TOCTOU) · Accessibility · Data Integrity

**Model routing:** inline (git/CLI, secrets pre-scan) → Sonnet (per-file analysis, parallel) → main model (cross-file review, report)

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
| `zitadel-idp` | Field guide with **47** documented quirks (v4-first with proto-aligned `v4.15.0` examples, v2.66.x masterkey edge case, full v2.66→v4 upgrade runbook, Login UI v2 deploy bug + Path B mitigation, CD cutover survival kit, Console UI human-user creation pitfalls, production 401-storm hairpin NAT + 3-layer SPA defense, smoke-e2e CI plumbing checklist, real-browser smoke E2E gaps — seed user grant reconciliation + CORS preflight 401 + Playwright self-signed Zitadel recipe), drill-down references, and bundled working assets |

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

**Production-proven pitfalls encoded:** cell padding not discounted from `widths` (last column cut off on A4 with 8+ columns); Roboto `fi`/`fl` ligatures drop the `f`; `addFonts()` rejects AFM; header/footer in `content[]` vanish on page 2+; revision cache stale on layout change; SVG fills from a `<style>` block render blank unless inlined. **Phase 6 Visual Verification** — render and inspect every page, not just page 1.

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
<summary><strong>kaizen-software</strong> — Kaizen (Continuous Improvement) for Software</summary>

Kaizen methodology applied to the three phases of a software's life — planning, implementation and maintenance — with PDCA as the backbone, plus material for teaching Kaizen to the team (history, vocabulary, training script).

| Skill | Description |
|-------|-------------|
| `/kaizen-software` | Plans features as small verifiable increments, keeps defects from moving forward during implementation (jidoka), and drives maintenance through 5 whys + 5S — logging every closed cycle in `KAIZEN_LOG.md` |

**Fits into the repo instead of replacing it:** Kaizen artifacts map onto the ones the project already has (architectural decisions → ADRs, opportunities/debt → `TODO.md` or backlog, recurring gotchas → the project runbook, history → `CHANGELOG.md`). Where the project forbids refactoring without an explicit request, the boy-scout rule becomes a logged opportunity rather than an edit — a finding never authorizes a change.

**References:** `desperdicios.md` (the 7 wastes translated to software, with detection questions, plus mura/muri), `kaizen-conceitos.md` (history, vocabulary, teaching script for onboarding or a board presentation), `templates.md` (PDCA plan, Kaizen Log, 5 whys, retrospective).

</details>

<details>
<summary><strong>whisper-preprocess</strong> — Offline Audio→Text Pipeline</summary>

Audio preprocessing + transcription pipeline (ffmpeg + OpenAI Whisper), 100% offline — extract, silence removal, voice enhancement, segmentation, and transcription (optional two-language pass + auto-merge).

| Skill | Description |
|-------|-------------|
| `/whisper-preprocess` | Runs the full pipeline from a media file (MKV/MP4/WAV/M4A) to text |

**Anti-"picotamento" lessons** (proven on a 65-min low-volume, dysarthric recording): the listenable `*_enhanced.opus` is decoupled from the transcription chain (stable gain only — no dynamic AGC or silence removal); a 2-pass `loudnorm linear=true` silently reverts to dynamic on clipping sources (compressor + limiter used instead); Opus inter-sample overshoot needs limiter headroom (`--listen-limit 0.6`) to keep the decoded true-peak below 0 dBFS.

</details>

<details>
<summary><strong>ansible-docker-backup-restore</strong> — Backup & Restore of Dockerized Services via Ansible</summary>

Field guide for recovering a Linux server's Docker services from backup, and for keeping the backup that protects them actually alive. Both halves live in one skill because the incident that closes the loop is born on the seam: a restore renamed a container, the backup inventory did not follow in the same commit, and the nightly backup stopped completing — for days, with no alert.

| Skill | Description |
|-------|-------------|
| `ansible-docker-backup-restore` | 11 inviolable rules, a routing table into 7 references, and two mandatory gates — audit the vhost before any `VIRTUAL_HOST`, and no restore is done until the backup ran end to end with `failed=0` |

**Highlights:** silent compose-project-name trap (wrong prefix creates an empty volume and the service comes up clean); 8-step anti-overwrite guard that fetches and verifies the replacement before deleting anything; `find` returning `files: []` on an unreadable path being read as "empty, safe to overwrite"; generic service key becoming a shared-network DNS alias that resolves round-robin between two different databases; certificate PEMs surviving without the ACME client state; the four silent-death patterns of a backup pipeline; and a read-only `check-backup-freshness.sh` that flags gaps in the date sequence — the cheapest signal there is, and the one that would have caught the original incident on day one.

**Agnostic by construction:** no server, domain, container, volume or network address from any specific environment — the real cases are told by mechanism, with placeholders.

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
/plugin install ansible-docker-backup-restore
/plugin install cicd
/plugin install codereview
/plugin install ddd
/plugin install deploy
/plugin install dev-script
/plugin install dotnet-wpf
/plugin install kaizen-software
/plugin install pdf-generation
/plugin install release
/plugin install retrofit-skill
/plugin install statusline
/plugin install ticket
/plugin install whisper-preprocess
/plugin install wsl-windows-onboarding
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
