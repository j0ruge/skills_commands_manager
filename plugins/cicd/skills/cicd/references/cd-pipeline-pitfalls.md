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

The answer is usually that two layers disagree and the "freshness boundary" between them is where the bug lives.
