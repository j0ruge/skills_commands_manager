# Changelog — `.claude/skills/cicd`

Lessons retrofitted into the skill, dated. Each entry describes **what** changed and **why** (the symptom it would have prevented).

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
