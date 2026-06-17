# Changelog — `.claude/skills/cicd`

Lessons retrofitted into the skill, dated. Each entry describes **what** changed and **why** (the symptom it would have prevented).

## 2026-06-17 — §10: falhas de runner EMPILHADAS (§9 → PAT 401 → §8) + description enxugada — bump 2.16.0 → 2.17.0

**O quê:** nova seção `references/self-hosted-runner-docker.md §10` + Lição 50 + linhas no Quick Troubleshooting e na tabela "Sintomas → seção". A `description` (SKILL.md + plugin.json + marketplace.json) foi enxugada de ~2440 → ~660 chars (1 frase + diferenciais + `Triggers` compacto).

**Por quê:** incidente no `erp_api` (staging) — um único deploy `queued` exigiu resolver §9, PAT expirado e §8 **em sequência**, cada fix desmascarando o próximo. O `docker volume rm` (§9, config morta) revela um `ACCESS_TOKEN` expirado (`401` / `Invalid configuration provided for token`), **invisível** enquanto o reuso de config nunca exercia o PAT; o PAT novo revela o binário deprecado (§8). A skill já tratava os três como ortogonais/isoláveis-pelo-log, mas não que **empilham** e que a assinatura do log **muda** a cada camada — então parar no primeiro fix declarava resolvido cedo demais. Inclui a triagem **"ausente vs offline"** (`gh api …/actions/runners` lista offline também → ausência total = registro apagado/§9 ou nunca registrou/token) e a natureza **host-wide** do PAT (um expira → derruba todos os runners do host; um PAT novo + `up -d --force-recreate` conserta todos). A description vinha virando um paredão de notas por-versão (~2440 chars) que dilui o triggering e pode ser truncada na lista `/skills`; detalhe migrou para os `references/**` e o README.

## 2026-06-15 — §8/§9: crashloops do runner ortogonais ao token (versão deprecada + config stale) — bump 2.15.0 → 2.16.0

Source: project `LouvorFlow` (staging, `192.168.0.6`). Deploy `queued` indefinidamente,
runner `louvorflow-runner` em crashloop com `RestartCount=50296`. Dois modos de falha
**não cobertos** pelo skill (que só tinha §7/token e §6/nome), e ambos **mordem mesmo em
runners já migrados para `ACCESS_TOKEN`** — desfazendo a impressão (da lição 46) de que
ACCESS_TOKEN seria à prova de balas:

- **§8 — `Runner version vX is deprecated and cannot receive messages`**: o runner
  registra, conecta e chega a "Listening for Jobs"; só então o GitHub recusa entregar
  jobs porque o binário foi deprecado → exit → restart. Causa: imagem `:latest` baixada
  uma vez e nunca re-puxada **+** `DISABLE_AUTO_UPDATE` ligado (nem refresh de imagem nem
  auto-update do binário). Tell: `Up <segundos>` com `RestartCount` milhares; status
  piscando online/offline. Fix imediato `docker compose pull` + `up -d --force-recreate`;
  durável = ligar auto-update. (No incidente: v2.333.0 deprecada → pull trouxe v2.335.1,
  RestartCount voltou a 0, os 2 deploys presos rodaram sozinhos sem `gh run rerun`.)
- **§8a — footgun `DISABLE_AUTO_UPDATE`**: `[ -n "${DISABLE_AUTO_UPDATE}" ]` no entrypoint
  do `myoung34` → QUALQUER valor não-vazio (até `"0"`) desliga. Para LIGAR auto-update,
  REMOVER a variável (não setar `"0"`). Verificar com `printenv DISABLE_AUTO_UPDATE` vazio.
- **Caveat à lição 45**: pinar a imagem do **runner** por digest é contraproducente sem
  cadência de bump — GitHub força currency e a versão congela até deprecar (→ §8). Opções:
  `:latest`+auto-update OU pin+`compose pull` mensal. Lição 45 atualizada com a exceção.
- **§9 — `Failed to create a session. The runner registration has been deleted from the
  server`**: GitHub apaga o registro de runner offline por semanas; com reuso de config
  (`CONFIGURED_ACTIONS_RUNNER_FILES_DIR` + named volume) o entrypoint reaproveita o
  `.runner` morto em vez de re-registrar via PAT. Distinto do §6 (lá há fantasma a deletar
  no GitHub; aqui o registro já sumiu — limpa-se o estado LOCAL: `docker volume rm
  <project>_<config-volume>`).
- **Nuance à lição 46** adicionada: ACCESS_TOKEN cura só o §7; §8/§9 são ortogonais.
- Acrescentadas 3 linhas no Quick Troubleshooting do `SKILL.md`, lições **47/48/49**, e a
  "isolation key" dos 3 crashloops pelo log.

## 2026-06-15 — §7 recorrente: recipe de migração ACCESS_TOKEN in-place (o fix durável) — bump 2.14.0 → 2.15.0

Source: project `sales_quote` (staging, 2º incidente do mesmo §7 — "não é a primeira
vez"). O §7 (chicken-and-egg do `RUNNER_REGISTRATION_TOKEN` estático) voltou a derrubar
o deploy: runner em crashloop `404 runner-registration`, `RestartCount=1397`, deploy
queued sem runner. O recovery documentado (rotacionar token + recriar) destravou, mas é
**paliativo** — e o skill só citava a migração ACCESS_TOKEN como opção teórica, então
ninguém a executava e o problema reincidia. Este retrofit fecha o loop:

- **Novo recipe `references/self-hosted-runner-docker.md` §7 → "Migração ACCESS_TOKEN
  in-place"**: mantém o `runner` no compose do produto; troca `RUNNER_TOKEN: ${...}` →
  `ACCESS_TOKEN: ${RUNNER_ACCESS_TOKEN:-}` + `RUNNER_SCOPE: repo`; entrypoint custom
  passa a aceitar `ACCESS_TOKEN` OU `RUNNER_TOKEN` (antes exigia `RUNNER_TOKEN` sob
  `set -u` → quebrava o modelo PAT). A imagem `myoung34` rebusca um registration token
  fresco a cada start → JIT ephemeral re-registra limpo, §7 deixa de acontecer.
- **Desmascarado que `EPHEMERAL:false` NÃO previne** o crashloop (o entrypoint limpa
  `.runner` e re-registra a cada start) — era uma falsa mitigação que o skill insinuava.
- **`gh` NÃO cunha PAT** (só web UI); `gh auth token` (escopo `repo`) serve de stopgap
  com tradeoff de acoplamento ao login. PAT vive só no `.env` persistente do host.
- **Calibração pré-recovery**: `gh api runners` vazio ⇒ sem fantasma a deletar; deploy
  `up` escopado ⇒ match secret↔.env é irrelevante (runner roda do `.env` persistente do
  operador, não do efêmero do CD).
- **Validação canônica**: validar o PAT com `GH_TOKEN=… gh api .../registration-token`
  ANTES de recriar; **provar a cura** com `docker restart` (re-registra sem 404).
- `SKILL.md`: lição **46** + row na Quick Troubleshooting + 3 keywords de trigger.

**Por quê**: transformar "opção mencionada" em recipe executável e marcar o recovery e o
toggling de `EPHEMERAL` como paliativos — para o §7 parar de reincidir. Provado em staging
do `sales_quote` (cutover + `docker restart` sem 404).

## 2026-06-12 — Monorepo npm-workspace build/runtime traps + `tsc -b` project references — bump 2.12.0 → 2.13.0

Source: project `sales_quote` (feature 017, primeiro CI/CD do repo). Quatro armadilhas
não-óbvias que custaram tempo real, todas ausentes da skill (verificado por grep):

- **Backend não roda como `node dist/` quando workspaces shared exportam TS source.** Os
  pacotes `@sales-quote/shared-*` têm `main: ./src/index.ts` (TS cru, import com extensão
  `.js`). A imagem compilada morria no boot com `ERR_MODULE_NOT_FOUND`/`ERR_UNKNOWN_FILE_EXTENSION`
  no `.ts` do sibling — `tsc` não inlina workspace deps e `node` não carrega `.ts`. Fix:
  rodar a imagem via `tsx src/index.ts` (igual ao dev). Repontar o `exports` do shared p/
  `dist` quebraria o Vite do frontend, então `tsx` é a mudança de menor blast-radius.
- **`tsc --noEmit` é um gate de CI VAZIO** num `tsconfig.json` raiz com project references
  (`files: []` + `references`) — checa zero arquivos, sai 0. O `vite build` (esbuild) também
  não type-checa. Resultado: erros de tipo escapam pra produção com o CI verde. Fix: o script
  de typecheck é `tsc -b --noEmit`. Corolário documentado: introduzir o gate num projeto que
  nunca type-checou revela um backlog de erros latentes (ex.: `@xyflow/react` v12, enum map
  incompleto, fixtures desatualizadas).
- **Workspace importando sibling NÃO declarado** (resolve só por hoist) quebra `npm ci -w`
  escopado no Docker; fix é `npm ci` cheio no builder descartado.
- **`USER node` + named volume novo = `EACCES`** na primeira gravação; Docker herda a
  ownership do path da imagem no volume novo — `mkdir`+`chown` antes do `USER`.

Além disso, a contrapartida de §1 (build-args bake'd): **como injetar um secret de RUNTIME**
no nginx do frontend (token server-side que não pode vazar no bundle) via o mecanismo de
templates/`envsubst` da imagem oficial — `${VAR}` substitui só env vars presentes, então
`$uri`/`$host` do nginx sobrevivem; verificação por grep de que o token NÃO está no bundle.

### Adicionado

- `SKILL.md` — Lessons Learned 37–40 (`[B]` tsx-runtime, `[F]` tsc -b project refs, `[B]`
  undeclared-sibling `npm ci`, `[S]` named-volume ownership) + 3 linhas na Quick
  Troubleshooting (sintomas verbatim: `ERR_MODULE_NOT_FOUND`, typecheck verde-fake, EACCES
  em volume) + trigger keywords compactas (sem inchar a prose da description).
- `references/troubleshooting-backend.md` — seção "Monorepo npm workspaces — armadilhas de
  build/runtime na imagem" (tsx-runtime com Dockerfile, sibling não declarado, volume ownership).
- `references/troubleshooting-frontend.md` — cenário 9 "CI typecheck passa verde mas erros
  escapam" (project references + corolário do backlog + churn de `*.tsbuildinfo`).
- `references/cd-pipeline-pitfalls.md §1b` — runtime-secret via nginx envsubst (contrapartida
  do build-time baking).

### Por que minor (não patch)

Adiciona 4 lições, 3 linhas de troubleshooting, uma seção nova em `troubleshooting-backend.md`,
um cenário em `troubleshooting-frontend.md` e §1b em `cd-pipeline-pitfalls.md`. Só adições —
nenhuma regressão para consumidores de 2.12.0.

## 2026-05-13 — GHCR `TLS handshake timeout` distinguished from `unauthorized` — bump 2.11.0 → 2.12.0

Source: project `LouvorFlow`, CD-staging-backend run from commit `415b345` (2026-05-13). The `deploy` job on `[self-hosted, staging]` failed at the docker login step with `Error: Error response from daemon: Get "https://ghcr.io/v2/": net/http: TLS handshake timeout`. The existing skill only documented the `unauthorized` variant — operator instinct was to rotate the PAT, but credentials were healthy: build-and-push on `ubuntu-latest` in the same workflow run pushed the image successfully. The asymmetry alone proved GHCR was up and the credential was valid; the failure was network-layer on the runner host.

### What changed

- **`troubleshooting-shared.md` §1a (new, ~110 lines)** — full section "`TLS handshake timeout` on GHCR (Self-Hosted Runner)" sitting right next to §1 with bidirectional cross-link so neither symptom can be misdiagnosed as the other again.
  - Explains the TCP-OK / TLS-fail distinction (credentials are irrelevant because the connection never reached the auth phase).
  - Documents the **isolation key**: build-and-push on `ubuntu-latest` passes + deploy on `self-hosted` fails → runner host network, not GHCR.
  - Ranks 4 probable causes (MTU mismatch, TLS-inspection proxy, transient flake, iptables legacy on new kernels).
  - 5 SSH diagnostic commands to run on the runner host.
  - **Fix A** — bash retry wrapper (3 attempts, 10s/20s backoff) drop-in replacement for `docker/login-action@v3` in the deploy job only. 20 lines. Explains why not to add `nick-fields/retry@v3` for a single step.
  - **Fix B** — `mtu: 1400` in `/etc/docker/daemon.json` + restart docker. Root-cause fix when MTU mismatch is confirmed in diagnosis.
  - **Fix C** — explicit HTTPS_PROXY for hosts behind corporate TLS-inspection middleboxes.
  - Decision tree: intermittent → Fix A; reproducible + MTU mismatch → Fix B; proxy detected → Fix C.
- **`SKILL.md` Quick Troubleshooting** — new `[S]` row with the symptom string, the isolation key, and pointer to §1a.
- **`SKILL.md` Lessons Learned** — row #36 "GHCR TLS handshake timeout vs unauthorized — não são o mesmo bug" condensing the distinction.
- **`SKILL.md` description + metadata.version**: bump 2.11.0 → 2.12.0 + extended description + new triggers.
- **`plugin.json` + `marketplace.json`**: version bump + extended description + new keywords (`tls-handshake-timeout`, `docker-login-retry`, `mtu-mismatch`, `tls-inspection-proxy`).

### Why it matters

Any self-hosted runner sitting behind a VPN, cloud overlay, or corporate firewall with TLS inspection eventually hits this. Before this change the skill conflated the two GHCR symptoms under `unauthorized`, sending operators down the credential-rotation path while the real fix was MTU or a retry wrapper. The retry wrapper in pure bash also eliminates a third-party-action dependency for a problem whose solution fits in 20 lines and is idempotent across re-runs. Estimated savings: ~30 minutes per incident, plus future credential-rotation churn avoided.

## 2026-05-08 — Best-effort write narrow catch + GHA bind mount uid mismatch + compose `--wait` scope — bump 2.10.0 → 2.11.0

Source: project `validade_bateria_estoque`, PR #10 (mergeada 2026-05-08, merge commit `13eed8d`). After v2.10.0 documented the ENOENT-bootstrap + soft-failure-yellow-warning trap, a code review on the canonical fix (Copilot, on `bootstrap-zitadel.ts:1106-1112`) pointed out a refinement worth folding back, and the work to bring an `smoke-e2e` CI job from red to green surfaced 2 more unrelated CI patterns that fit this skill's scope.

- **§5 refinement** — the canonical "best-effort wrap" was `try { writeFileSync } catch { warn }`, which silences EVERY error from the write, not just the `ENOENT` expected in the container. Reviewer Copilot pointed out that on a dev machine, EACCES (perms wrong on the bind mount), ENOSPC (disk full), or EROFS (read-only filesystem) are real local problems that should propagate — not be silenced. The pragmatic refinement is to narrow the catch to `ENOENT`/`ENOTDIR` (the expected case in the container) and re-throw everything else. **Why this matters concretely**: in the source project the `bootstrap.json` written by the script is consumed by a backend `auth-sanity.ts` check that compares `AUTH_AUDIENCE` against the project ID — silencing a write failure means the sanity check then operates on a stale or absent file without alarm. The narrow catch preserves the prod fix (ENOENT in container, expected) while keeping the dev signal honest. The same reasoning applies to any best-effort write: silence only the errno you affirmatively expect, not the whole cone of failure modes.

- **§6 — GHA bind mount uid mismatch (NEW)** — The smoke-e2e job in PR #10 boot-failed with `permission denied` on a Postgres-style `chown` and a Zitadel-style `EACCES open admin.pat`. Both have the same root cause: the container process runs as a baked-in non-root uid (commonly **uid 1000** for vendored upstream images), but a `ubuntu-latest` GHA runner checks out the workspace as **uid 1001 (`runner:docker`)** with mode `0755` — the container can't write to the bind-mounted host directory. Dev machines avoid this by accident (Linux user IS uid 1000, or macOS/WSL Docker Desktop shims uid mapping, or `dev.sh` pre-creates the mount with right perms). On a fresh GHA runner none of those apply. **The poisonous cascade**: a partial init that died on EACCES often leaves enough state behind that the *retry* (under `restart: always`) trips a *different* error — a constraint violation on a row written before the EACCES, an "already exists" — burying the real cause unless the operator scrolls up to the FIRST attempt. **Fix**: pre-create the bind mount with `chmod 0777` BEFORE `docker compose up`. Avoids hardcoding a uid that could shift if the image changes. Don't try `chown 1000:1000` (more brittle, and runner may lack permission depending on docker config). Don't try to swap to a named volume in CI without doing it in dev too — bind mounts are commonly load-bearing in dev for inspecting artifacts on the host side.

- **§7 — `docker compose up -d --wait` scope (NEW)** — The same PR #10 smoke-e2e job, after §6 was fixed, started failing because `--wait-timeout 120` ran out while waiting for an unrelated container's slow healthcheck. The compose file mixes "things the test needs" (DB, API, init container) with "things dev needs" (Login UI, mailpit, worker dashboards), and `--wait` waits for **all** of them by default. One slow Next.js / Vite / Webpack-dev-server container — easily 60-90s+ on a small `ubuntu-latest` 2-vCPU shared runner — dominates the timeout for the entire stack even when the tests don't touch it. **Fix**: pass service names explicitly to `up --wait` so compose only waits for those. The companion fix is to **always include the slow services in your on-failure log dump** (`docker compose logs <svc> || true`) even when you don't `--wait` for them — without that, the next time you DO need to debug them you have no visibility. `|| true` matters because `docker compose logs <svc>` fails if the service wasn't started, and the dump step itself shouldn't fail and hide everything else.

These two CI sections (§6 + §7) generalize beyond Zitadel — they apply to any compose file with vendored-uid containers writing to bind mounts, or any compose file where CI scope is narrower than dev scope. The Zitadel-specific symptoms live in the `zitadel-idp` skill's quirks 38-40 (cross-referenced); the generic patterns live here.

### Adicionado

- `references/cd-pipeline-pitfalls.md §5` — refined "Canonical fix" with narrowed catch (ENOENT/ENOTDIR only) + new "Why narrow the catch" paragraph explaining the dev-time signal preservation argument.
- `references/cd-pipeline-pitfalls.md §6` (NEW) — Bind mount uid mismatch on GHA runners. Symptom + cause + fix + diagnosis tell (scroll up to first attempt) + generalization.
- `references/cd-pipeline-pitfalls.md §7` (NEW) — Compose `--wait` scope. Symptom + cause + fix + companion on-failure log dump + generalization.

### Por que minor (não patch)

§5 refinement alone would be a patch, but adding two new sections (§6, §7) covering distinct CI patterns with their own diagnosis tells is substantive enough to warrant a minor. Same magnitude as v2.10.0 (one new section then) — keep the convention.

---

## 2026-05-08 — Container script writing output paths outside WORKDIR — soft-failure that hides forever — bump 2.9.0 → 2.10.0

Source: project `validade_bateria_estoque`, post-§7 recovery (cutover prod 2026-05-08). The §7 chicken-and-egg recovery from v2.9.0 worked exactly as documented (~5min from `0 runners` diagnosis to job picked up), and the first successful deploy in ~19h surfaced **a separate latent bug** that had been hiding behind yellow warnings since feature 005 — the `idp-bootstrap` step exits 1 on every deploy with `ENOENT '/app/infra/docker/zitadel/local/bootstrap.json'`, but `continue-on-error: true` + `::warning::` mark it as soft-failure so the stack stays healthy. Operators stopped reading the yellow warning after a few deploys.

Root cause: `bootstrap-zitadel.ts:1099` resolves `outFile = resolve(__dirname, '../../../infra/docker/zitadel/local/bootstrap.json')` — in dev the source tree mounted/checked-out has the upward path; in prod the Dockerfile only copies `packages/idp/`, so the upstream paths don't exist in the image. Every Zitadel operation (org/project/app/roles/user/grants/label-policy/custom-texts) completes BEFORE the `writeFile`, so each deploy correctly applies IdP state — it just blows up cosmetically at the end.

This generalizes beyond bootstrap-de-IdP: any script bake'd into a container that writes to a path resolved upward from its own location falls into the same gotcha. `release-notes-emit`, `migration-summary`, `seed-data-export`, `audit-log-export` — all candidates for the same pattern.

Captured in **new `cd-pipeline-pitfalls.md` §5** with: canonical symptom (the `[bootstrap] FALHOU: ENOENT` log line + `##[warning]` follow-up), 60-second diagnosis (`grep writeFile/outFile in scripts/` × `grep ^COPY in Dockerfile` = diff = bug), canonical fix (best-effort try/catch wrap + `console.log` of the JSON for CD logs to capture), 4 alternative fixes with trade-offs, and a meta-principle on **persistent yellow warnings being worse than green** — they condition operators to ignore CD's only "look here" signal. The principle generalizes to any step that emits `::warning::` on every deploy: finish the fix instead of normalizing the warning.

Also fixes a **drift in `SKILL.md` `metadata.version`** — was at 2.8.0 since v2.9.0 didn't bump that field; now 2.10.0 in sync with `plugin.json` and `marketplace.json`.



## 2026-05-07 — CD cutover pitfalls: build-time vs runtime, operator clones, `--profile run` side-effects + multi-job token exhaustion — bump 2.6.1 → 2.7.0

Source: project `validade_bateria_estoque`, Onda 3 of feature 006 (cutover prod). The existing skill v2.6.1 covered the runner build-time and registration mechanics solidly, but a real production cutover surfaced **four classes of CD-time pitfalls** that bit during mid-flight debugging — each costing 15-60 minutes the first time and recurring across the day:

- **Multi-job CD exhausts ephemeral runner tokens within the 1h window.** Skill §5 noted "tokens single-use, vencem em 1h" but didn't spell out the **multi-deploy-day failure mode**: `EPHEMERAL=true` runner consumes the token on each job's re-registration, so 4-5 deploys in an hour exhaust it even before the wall-clock TTL expires. Symptom is `gh-runner Restarting (1)` mid-cutover with a job stuck "queued" in CI. Fix requires updating the token in **two places** (GH secret + `.env` on the runner host) plus `docker compose up -d --force-recreate runner` — the GH secret alone doesn't help the running container which already has the stale `.env`. Captured in new §5b.

- **Vite/CRA/Next build args are baked at image build time, not runtime.** Frontend rebuild is mandatory when `VITE_API_BASE_URL`, `VITE_OIDC_CLIENT_ID`, etc. change — `gh secret set` alone does nothing for the running pod until the next build. Compounded by a path-component drift trap: SPA default in source had `/api` suffix, prod build args dropped it, every API call returned 404 even though backend was healthy. Wasted ~30 minutes "is this auth? CORS? token audience?" before opening DevTools network panel and seeing the wrong path. Captured in new `cd-pipeline-pitfalls.md §1`.

- **Operator clone of the repo on the deploy host is a footgun.** A `/home/operator/<project>/` checkout that exists for "convenience" diverges silently from main. Running `docker compose -f <stale-clone>/docker-compose.prod.yml ...` on the host **reconciles every service** to the stale spec — including downgrading running images. Bit during a manual bootstrap retry: `--profile bootstrap run --rm idp-bootstrap` recreated `zitadel` from `v4.15` back to `v2.66` because the operator clone was 3 commits behind. ~15 minutes lost + a re-trigger of CD. Captured in new `cd-pipeline-pitfalls.md §2` (and the recovery: `git log --oneline -1` in any operator clone before issuing compose commands; better — remove the operator clone entirely or rename to `_archive_*`).

- **`docker compose --profile X run` reconciles unrelated services.** Companion to the operator-clone trap: even with the right compose file, `--profile run` doesn't isolate to profile-tagged services. It loads everything and ensures dependency health, which means reconciling sibling containers if their running spec differs from the file. For one-shot jobs against a published image, prefer `docker run` directly bypassing compose; for jobs that need the dependency graph, trigger via CD workflow instead of running manually. Captured in new `cd-pipeline-pitfalls.md §3`.

These are all "layer mismatch" failures: GH secret vs `.env` on host vs running container env vs baked frontend bundle vs running compose vs operator clone. The skill now ends `cd-pipeline-pitfalls.md` with a layer/refresh-boundary table so the operator can rapidly identify which freshness boundary the bug lives at.

### Adicionado

- `references/self-hosted-runner-docker.md §5b` — Multi-job CD token exhaustion (companion to §5's 1h-TTL coverage)
- `references/cd-pipeline-pitfalls.md` (NOVO) — 3 sections covering build-time vs runtime confusion, operator clones, `--profile run` side-effects, plus a layer/refresh-boundary table for rapid diagnosis
- `SKILL.md` — link to new ref in Routing Table + trigger blurb so the skill points at it when the operator describes "secret atualizado mas container com valor antigo" / "compose --profile run derrubou containers" / "operator clone com compose stale"

### Por que minor (não patch)

Adiciona uma referência inteira nova (`cd-pipeline-pitfalls.md`, ~150 linhas) e uma seção substantiva em `self-hosted-runner-docker.md`. Muda como a skill é apresentada (novo "Trigger pra" no SKILL.md routing). Não há regressão pra consumidores em v2.6.1 — só adições.
