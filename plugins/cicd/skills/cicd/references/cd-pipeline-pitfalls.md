# CD Pipeline Pitfalls — Build-time vs Runtime, Operator Clones, `--profile` Side-effects

Three classes of failure that bite hardest in mid-flight cutovers, when the CD pipeline is already in motion and the operator is improvising fixes on the live host. Each costs 15-60 minutes the first time, and the cause is in a different layer than the visible symptom.

---

## §1. Vite/CRA build args are baked at image build time, not runtime

**Symptom**: After a clean cutover, login succeeds (OIDC redirect, callback, code exchange all work), the SPA loads — but every API call returns `404` and the dashboard can't fetch any data. Network tab shows requests going to `https://api.example.com/dashboard/stats` (no `/api` prefix), backend logs show those paths returning 404. Backend `/api/dashboard/stats` responds 401 to unauthenticated curl (route exists with auth required).

**Cause**: VITE_* envs (and `NEXT_PUBLIC_*` for Next, `REACT_APP_*` for CRA) are **inlined into the JavaScript bundle at `vite build` time**, not read from runtime env. The CD workflow's `build-args` block in the frontend job is the source of truth for prod. If `VITE_API_BASE_URL=https://api.example.com` (no `/api`) but the SPA's default in source is `http://localhost:3000/api` (with `/api`), the build args silently drop the prefix in prod.

**The trap**: changing the GH Environment secret (`gh secret set VITE_API_BASE_URL …`) and re-deploying without rebuilding the frontend image is a no-op — the new secret is read at the *next* build, not at runtime. If your CD only re-deploys (pull + `up -d`) without re-building, nothing changes. Empty commit + push triggers a full rebuild.

**Fix**:

1. Audit the SPA source for the default API base URL — particularly whether it has a path component (`/api`, `/api/v1`, etc.).
2. Match the build args in `cd-production.yml` (or equivalent) to that path:
   ```yaml
   build-args: |
     VITE_API_BASE_URL=https://api.example.com/api   # ← NOT just /com
   ```
3. After changing build args or VITE_* secrets, **always rebuild** the frontend image. `gh secret set` alone does not update running pods.
4. Verify the deployed bundle:
   ```bash
   FRONT_JS=$(curl -s https://app.example.com/ | grep -oE '/assets/index-[a-z0-9_-]+\.js' | head -1)
   curl -s "https://app.example.com$FRONT_JS" | grep -oE '"https://api\.example\.com[^"]*"' | sort -u
   ```
   The output should match what you put in build args, prefix and all.

**Why this is treacherous**: in a mid-cutover scenario, you might already have logged into the app and seen "everything works on the surface" — auth, redirect, token exchange. The 404 on data fetches feels like a backend problem (auth token rejected? wrong audience? CORS?), but the network panel shows the SPA hitting the wrong path. Always check what the deployed bundle actually contains before chasing backend hypotheses.

**Adjacent lesson**: the same applies to `VITE_OIDC_CLIENT_ID`, `VITE_OIDC_AUTHORITY`, and any other build-time secret. Updating the secret without rebuild = SPA continues running with the old value. If you change the IdP configuration (regenerated client_id, new authority hostname), the frontend rebuild is mandatory, not optional.

---

## §2. Operator clone of the repo on the deploy host is a footgun

**Symptom**: You're debugging a cutover, SSH'd into the prod host, and run `docker compose -f /home/operator/myproject/infra/docker/docker-compose.prod.yml --profile bootstrap run --rm idp-bootstrap` to retry the bootstrap step manually. Output includes `Container zitadel Recreated` — and suddenly the running stack got rolled back to a previous version.

**Cause**: That repo at `/home/operator/myproject/` is a **stale checkout** from before the latest CD merge (e.g., still has `image: ghcr.io/zitadel/zitadel:v2.66.10` while the live stack is on `v4.15.0`). `docker compose --profile bootstrap run` doesn't run only the profile-tagged service — it reconciles **every service in the compose file** if their actual state differs from the file's spec. With a stale image tag, "differs" means "downgrade running container".

**Why this is a footgun**: in proper CD setups, the source of truth for compose is **the runner workspace** (`actions/checkout` into `/runner/_work/...`), which is fresh per deploy. The operator clone exists for "convenience" — e.g., legacy from a manual-deploy era, or set up so the operator can `cd` and run docker commands without context-switching. But it diverges silently and there's no warning when you use it.

**Fixes**, in order of preference:

1. **Remove the operator clone**. CD does its own checkout. The clone only adds risk. If operator commands need the compose file, mount it into a sidecar `ops` container or write a small `ops.sh` that pulls fresh from main before running.
2. If keeping the clone for read-only inspection, **rename it** to `_archive_<sha>` so it's obviously not "the" compose. You'll never accidentally `docker compose -f` against an `_archive_*` path.
3. **Pin the compose path in compose itself**: the runner workspace path can be standardized (`/runner/_work/<repo>/<repo>/infra/docker/...`). Operators can `docker compose -f <runner-workspace-path>` for read-only `ps` / `logs` queries; reads are safe, writes are not.

**Bonus footgun — runbook canonical path may not exist on disk**: in setups deployed by a self-hosted runner, the *real* compose path is the runner's workspace (`/runner/_work/<org>/<repo>/<repo>/infra/docker/`), regenerated per CD run. Internal docs (runbooks, ADRs) frequently reference an aspirational path like `/opt/<org>/<project>` that was the plan during the manual-deploy era and never got created. SSH-debugging operators read the runbook, `cd /opt/<org>/<project>`, get "No such file or directory", and assume the system is broken. It isn't — the docs are. When auditing a deployed system, run `docker inspect <container> --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'` to find the *actual* working dir, then update the runbook.

**Recovery when it bites**: trigger CD again (empty commit + push) — it'll do a fresh checkout, pull the right images, and reconcile to the correct version. ~3-5 minutes lost, but no manual fixup needed on the host.

**Detection**: when SSH-debugging, always run `git log --oneline -1` in any operator clone before issuing `docker compose` commands against it. If the latest commit isn't main HEAD, the file is stale.

---

## §3. `docker compose --profile X run` reconciles unrelated services

**Symptom** (companion to §2): running `docker compose -f <file> --profile bootstrap run --rm idp-bootstrap` to manually re-run a one-shot job recreates running containers from `<file>`'s spec, even though those containers aren't in profile `bootstrap`. Live stack is briefly disrupted.

**Cause**: `docker compose run` doesn't isolate to profile-tagged services. It loads the full compose file and ensures dependencies are healthy — which means reconciling them if their running spec differs. If the compose file disagrees with what's running (stale source — see §2), you get "fixed" to the stale spec.

**Mitigations**:

1. **Don't run `--profile X run` against a stale compose file.** Source from the runner workspace or a fresh `git pull origin main` first.
2. For read-only one-shot jobs (validation, scans), prefer `docker run` against the published image directly:
   ```bash
   docker run --rm --network <project>_<network> ghcr.io/<org>/idp-bootstrap:latest
   ```
   This bypasses the compose reconciliation entirely.
3. For one-shot jobs that need compose dependencies (the `depends_on` graph), trigger them via a CD workflow step (`workflow_dispatch` or empty commit) instead of running them manually on the host. CD always has the right compose file.

**Why this surfaces in cutovers**: cutovers are exactly when you're tempted to `docker compose run` manually — bootstrap failed, you have the PAT, you want to retry without firing a whole CI/build cycle. That's when the stale-compose footgun hits.

---

## §4. `compose run` orphans + reverse-proxy upstream poisoning

**Symptom**: roughly 50% of authenticated requests to a backend behind nginx-proxy (or Traefik with similar discovery) return 401 with a credible-sounding error like "invalid token" / "audience mismatch", but the JWT is verifiably valid (replaying the *exact same token* via curl from outside returns 200, decoding the JWT shows correct `aud`, `iss`, `exp` is in the future, signature checks against JWKS). Users report intermittent failures; reload sometimes fixes it, sometimes doesn't. Backend logs show 401s with response times all over the map (some <5ms, some 200-400ms — but the slow ones don't correlate with cache misses).

**Cause**: a `docker compose run --rm <service> <one-off-cmd>` from a previous CD run left an orphan container alive. The most common path: `compose run --rm backend npx prisma migrate deploy` — the migration finishes, the `--rm` is supposed to fire, but it doesn't (CI cancelled mid-run, runner OOM, container's pre-stop hook hung, `docker daemon` restarted, etc.). The orphan keeps running. It still has the service's `VIRTUAL_HOST` env (because `compose run` inherits the service's environment by default), so `docker-gen` (or the Traefik label discoverer) registers it in the **upstream pool** for the same hostname as the live backend.

nginx-proxy now round-robins requests between the healthy backend (correct config from the latest deploy) and the orphan (stale config from whenever it was started — `AUTH_AUDIENCE=PLACEHOLDER_BEFORE_FIRST_BOOTSTRAP`, old image SHA, possibly a half-broken state). 50% of requests with valid auth get 200; 50% get 401.

**Three counter-intuitive surprises**:

1. **`docker compose run --rm` is not bulletproof.** The `--rm` flag fires when the container *exits cleanly*. Anything that prevents a clean exit — process crash, `kill -9`, daemon restart, CI workflow cancellation mid-execution — leaves the container behind. Over a project's lifetime, expect at least one orphan per few hundred CD runs.
2. **`docker compose up -d --remove-orphans` does NOT remove these.** The `--remove-orphans` flag removes containers for *services that no longer exist in the compose file*. A `*-backend-run-<hash>` container belongs to the same service `backend` as the live container — just a different one-off invocation, with a hash suffix in the name. Compose treats them as siblings, not orphans.
3. **`docker-gen` registers anything with `VIRTUAL_HOST` set, no service-stability check.** Whether the container is the long-running service container or a one-off `compose run` container is invisible to the discovery layer. As long as the env var is there, into the upstream pool it goes.

**Diagnostic — the canonical 5-second check**: if you suspect this, fire 20 parallel requests with the *same known-valid token*:

```bash
TOKEN="<a fresh valid JWT>"
for i in $(seq 1 20); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Origin: https://app.example.com" \
    https://api.example.com/some-authenticated-endpoint &
done
wait | sort | uniq -c
```

A clean backend returns `20 200`. A poisoned upstream returns a *split* — e.g., `13 200` and `7 401`, or `10 200` and `10 401`. The split ratio matches the round-robin distribution across upstreams. **Inconsistent 401s with a token you've manually verified is valid is the unmistakable signature of upstream pool stale-instance**, not a JWT validation bug. Don't chase jose / aud / iss / JWKS rabbit holes until you've ruled this out.

Then list the upstream pool from inside nginx-proxy:

```bash
docker exec nginx-proxy cat /etc/nginx/conf.d/default.conf \
  | sed -n "/upstream <hostname>/,/^[[:space:]]*}/p"
```

If you see two `server` lines where there should be one (e.g., `# erp-backend` *and* `# jrc-prod-backend-run-3ed3a2e9cdb9`, both pointing at port 3000 on different IPs), that's the smoking gun. Inspect the orphan's env to confirm — usually `AUTH_AUDIENCE`, `DATABASE_URL`, or `IMAGE_TAG`-derived values will be from a stale build.

**Immediate fix**: `docker rm -f <orphan-name>`. nginx-proxy's docker-gen sees the container disappear, regenerates the config, and reloads nginx within a couple seconds. Verify with the parallel-curl check — should now be `20 200`.

**Permanent fix (two-pronged)**:

1. **Invisibilize one-offs to the proxy discoverer.** Override the discovery env vars to empty in every `compose run`:

   ```bash
   docker compose -f <COMPOSE_FILE> run --rm \
     -e VIRTUAL_HOST= \
     -e LETSENCRYPT_HOST= \
     backend npx prisma migrate deploy
   ```

   For Traefik: override the relevant labels (`traefik.enable=false`) instead. Even if the `--rm` later fails to fire, the orphan never enters the upstream pool — the worst case becomes "stale container exists but receives no traffic", which is recoverable without user impact.

2. **Defense-in-depth cleanup step before the rolling update.** `--remove-orphans` won't catch these, so add an explicit step in the CD workflow that runs *before* `up -d`:

   ```yaml
   - name: Remove one-off orphans pre-rolling
     run: |
       orphans=$(docker ps -aq --filter "name=<project-prefix>-.*-run-" 2>/dev/null || true)
       if [ -n "$orphans" ]; then
         echo "Removing one-off orphans: $orphans"
         docker rm -f $orphans
       else
         echo "No one-off orphans found."
       fi
   ```

   Adjust `<project-prefix>` to your compose project name. The pattern `*-run-` matches the `compose run` naming convention. This catches orphans from old runs that pre-date the env override (otherwise you wait for them to time out, which they never do).

**Why this is treacherous**: every layer of the stack reports "healthy". The orphan responds to its own healthcheck (it's a real backend, just with stale config — or a migration container that has long since finished but stayed Up). nginx-proxy's healthchecks pass for the upstream pool. The live backend is fine. The discovery layer is doing exactly what it's designed to do. The only sign anything is wrong is the *statistical* split between 200 and 401 — and on a busy app, that gets lost in the noise unless you specifically look for it.

**Adjacent forms to watch for**:
- `docker compose run` for ad-hoc DB seed, cache warm, or feature flag flip (anything one-shot).
- Operators using `docker run --network <project>_<network>` on a dev machine — same VIRTUAL_HOST inheritance if they reuse the service's env-file.
- Restarted Docker daemon during a long CD run leaving multiple migration containers in `Created` or `Exited` states that are then `docker start`-ed by recovery scripts.

---

## When you don't see your error here

If your CD failure looks layer-mismatched (build vs runtime, file-on-disk vs published-image, secret-set vs secret-baked) — start by listing the layers and tracing what gets refreshed at each:

| Layer | Refreshed by | Stale until |
|---|---|---|
| GH Environment secret | `gh secret set` | next workflow run that reads it |
| `.env` on runner host | CD step "Gerar .env de produção" | every CD deploy |
| Runner workspace `compose.yml` | `actions/checkout` | every CD job |
| Operator clone `compose.yml` | manual `git pull` | until you remember |
| Frontend bundle (VITE_*) | Frontend rebuild step | until rebuild |
| Backend container env | Compose `up -d` | until recreate |
| Running container's image | `docker pull` + `up -d` | until recreate |
| nginx-proxy/Traefik upstream pool | docker-gen / label discoverer | until offending container is removed |
| `compose run` one-off container | `--rm` on clean exit | indefinitely if exit isn't clean |

The answer is usually that two layers disagree and the "freshness boundary" between them is where the bug lives.

---

## §5. Container script writing output outside WORKDIR — soft-failure that hides forever

**Symptom**: A CD step (`bootstrap`, `seed`, `migrate-summary`, `release-notes-emit`, etc.) emits something like:

```text
[bootstrap] FALHOU: ENOENT: no such file or directory, open '/app/infra/docker/zitadel/local/bootstrap.json'
##[error]Process completed with exit code 1.
##[warning]IdP bootstrap falhou após retry — investigar via runbook. Stack permanece UP com config anterior.
```

…but the operations the script was *supposed* to perform — DB rows, IdP entities, role grants, label policy uploads — all completed successfully *before* the error. The CD job is marked `success` (because the offending step has `continue-on-error: true` + a follow-up step that emits `::warning::`), so the stack stays healthy and other deploys piggyback on the same yellow warning. After 2-3 deploys the yellow gradient blends into normal operation visually, and any **new** warning gets missed in the noise.

**Cause**: The script (Node, Python, Bash) resolves an output path relative to its own location (`__dirname`, `__file__`, `$(dirname "$0")`) that walks **upward into the source tree** — e.g.:

```typescript
// packages/idp/scripts/bootstrap-zitadel.ts
const outFile = resolve(__dirname, '../../../infra/docker/zitadel/local/bootstrap.json');
//                                  └─ 3 levels up out of packages/idp/dist/scripts/
//                                     into the monorepo root, then back down into infra/
writeFileSync(outFile, JSON.stringify(result, null, 2));
```

In dev (host with the full source tree mounted or checked-out as cwd) the upward path exists, `writeFileSync` succeeds, everyone is happy. In prod the script runs **inside a Docker container whose Dockerfile only copies `packages/<self>/`** — the upstream paths (`infra/docker/...`, monorepo root, sibling packages) simply don't exist in the image. The `writeFile` fires after every Zitadel/DB operation completed and explodes there.

**Fast diagnosis (60 seconds)**:

```bash
# 1. Find what the script tries to write
grep -nE "writeFile|fs\.writeFile|outFile|to_csv|toFile|with open.*'w'" \
  packages/<offending-package>/scripts/*.{ts,js,py} | head -10

# 2. Check what the Dockerfile actually copies into the image
grep -nE "^COPY |^ADD " packages/<offending-package>/Dockerfile

# 3. Diff: any path the script writes to that's NOT under one of the
#    COPY destinations (or not a runtime-writable mount like /tmp/) is the bug.
```

The diff is usually obvious: the script writes to `../../../infra/...` and the Dockerfile only has `COPY packages/<self>/ ...`. There's no overlap — the path simply doesn't exist in the image.

**Canonical fix — best-effort wrap**:

```typescript
const outFile = resolve(__dirname, '../../../infra/docker/zitadel/local/bootstrap.json');
try {
  writeFileSync(outFile, JSON.stringify(result, null, 2));
  console.log(`[bootstrap] OK → ${outFile}`);
} catch (err) {
  const msg = err instanceof Error ? err.message : String(err);
  console.warn(`[bootstrap] OK (não persistiu summary em ${outFile}: ${msg})`);
}
console.log(JSON.stringify(result, null, 2));  // CD logs already capture the content
```

In dev: identical behavior (path exists → writes succeed). In container: warn, continue, exit 0. The CD step goes back to a clean green status — and now any future yellow warning means **something genuinely new is broken**, instead of being ambient noise.

This is the right shape when persistence is *informational* — the JSON is for operators reading deploy logs or inspecting a dev workspace. The CD log already captures it via the subsequent `console.log(JSON.stringify(...))`.

**Alternatives — when persistence is genuinely required**:

| Approach | When to use | Trade-off |
|---|---|---|
| Writable container path (`/tmp/`, `/var/run/<app>/`) | Need the file for a follow-up step inside the same container, or to `cat` from a pre-stop hook. | File is lost when container exits. |
| Env-driven explicit path (`process.env.OUTPUT_PATH ?? '/tmp/x.json'`) | Want operator to control persistence per-deploy. | Operator has to know the env exists. |
| Volume bind mount in compose | Need the file to survive on the host and be readable by other tooling. | The mount becomes a deployment contract — losing it later breaks bootstrap silently. |
| Add the path to `Dockerfile` `COPY` (only the empty dir) | The script genuinely needs the in-image path to exist (rare). | Couples the image to source-tree layout — every monorepo refactor risks breaking it. |

**Why `continue-on-error: true` + `::warning::` is the trap (and the right tool used wrong)**: it's a great pattern for steps that genuinely *shouldn't* block deploy on non-critical failure (the IdP bootstrap step in the case study above is genuinely idempotent — every Zitadel op completed before the writeFile blew up, so the stack is in the desired state). But because the warning paints yellow on every single deploy, the gradient saturates after a few cycles and operators stop reading it. The signal-to-noise of CD warnings degrades from "investigate" to "expected".

**Rule of thumb**: if a step emits `::warning::` on every deploy, you've already paid the operational cost — finish the fix. Either:
1. Make the step actually exit 0 (best-effort wrap above), OR
2. Change the warning to `::notice::` (lower visual priority, signals "I know this happens"), OR
3. Remove the soft-failure entirely if the underlying operation can be made deterministic.

Persistent yellow is worse than green because it conditions you to ignore the only signal CI/CD has for "things deserving a glance".
