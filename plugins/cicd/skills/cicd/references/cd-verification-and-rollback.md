# CD Verification & Rollback — Making a Deploy Prove Itself

A deploy pipeline is a chain of claims: "the image built", "the containers are healthy",
"the app serves traffic", "the backup runs". Each claim is only worth the sensor behind
it, and the failures collected here share one shape — **the sensor said yes while the
thing it stood for was false**, or the sensor never ran at all and its silence read as
success.

These bite on cutovers and first production deploys, where there is no previous good
state to fall back on and nobody has yet learned what "normal" looks like.

---

## §1. Capture the rollback tag from immutable tags only

**Symptom**: a deploy fails, the automatic rollback "succeeds", and the broken version
is still being served.

**Cause**: the rollback captured `latest` (or `staging`, or any moving tag) as the
"previous" version. Those tags are mutable, and **this very deploy just re-pointed them
at the image that is breaking**. Rolling back to `latest` rolls back to the failure.

**Fix**: capture the tag actually being served by the running container, and accept it
only if it is immutable:

```bash
prev_tag="$(docker inspect --format '{{.Config.Image}}' <container> 2>/dev/null | awk -F: '{print $NF}' || true)"
case "$prev_tag" in
  sha-*) ;;            # immutable, usable
  *) prev_tag="" ;;    # latest / staging / empty → not a rollback target
esac
echo "previous_tag=${prev_tag:-unknown}" >> "$GITHUB_OUTPUT"
```

**First deploy has no previous version, and that is fine** — `previous_tag=unknown`, the
rollback step is skipped by its own condition. What is *not* fine is being quiet about
it: say so in `$GITHUB_STEP_SUMMARY`, because "rollback skipped" and "rollback ran" look
identical in a red run, and the operator needs to know that recovery is manual this time.

**Corollary**: this only works if your build publishes immutable `sha-<short>` tags
alongside the moving ones. If your scheme is `:staging` / `:latest` only (see
`checklist-shared.md` §2), you have no rollback target at all — fix the tagging first.

---

## §2. A rollback that isn't re-smoked proves nothing

**Symptom**: the run is red, the log says "rollback complete", and production is down.
You find out from a user.

**Cause**: the rollback step ends at `docker compose up -d`. `up -d` returning 0 means
Docker accepted the request — not that the previous image booted, passed its healthcheck,
and answered traffic. A rollback that restores service and one that doesn't are
**indistinguishable** at that point.

**Fix**: after the rollback `up -d`, wait for healthy and run the same smoke you ran for
the forward deploy. If it fails, escalate loudly — this is the worst state the pipeline
can be in, and it must not be reported as a successful recovery:

```bash
# ...wait-healthy loop over the app services first...
if ! curl -fsS --max-time 10 https://api.example.com/health/ready | grep -q '"status":"ok"' \
   || ! curl -fsS --max-time 10 -o /dev/null -w '%{http_code}' https://app.example.com/ | grep -q '^200$'; then
  echo "::error::ROLLBACK DID NOT RESTORE SERVICE — production is down."
  docker compose -f "$COMPOSE_FILE" ps
  exit 1
fi
echo "::warning::Rollback complete and RE-SMOKED: the previous version is serving."
```

Note the asymmetry: a successful rollback is a `::warning::` (the deploy still failed,
somebody must look), a failed rollback is an `::error::` with an explicit "production is
down".

**Migrations are not rolled back.** `prisma migrate deploy` (and `manage.py migrate`) have
no down step, so the previous image runs against the newer schema. Additive migrations
survive this; destructive ones don't. That asymmetry is an argument for keeping
migrations additive in the deploy path, and for documenting the manual `migrate resolve`
route in your runbook.

---

## §3. `if: success()` never runs after a red step — order your gates deliberately

**Symptom**: the deploy failed on smoke, and the backup gate you added "to be safe" simply
isn't in the log. It never ran, on the exact deploy where you most wanted the extra check.

**Cause**: step conditions are evaluated against the job status so far. `if: success()`
is false once any earlier step failed. This is correct behaviour, but it means a gate
written that way is a **fair-weather gate**: it verifies only the deploys that were
already fine.

**Fix**: decide what each gate should do to the run, and place it accordingly.

| You want | Condition | Placement |
| --- | --- | --- |
| Verify only a healthy deploy | `if: success()` | anywhere after the smoke |
| Always clean up | `if: always()` | last |
| React to failure | `if: failure()` | after the step that can fail |
| **Mark the run red without taking the app down** | `if: success()` | **after** the rollback step |

That last row is the non-obvious one. Putting a secondary gate (backup health, metrics
scrape, license check) **after** the rollback step means the rollback's `if: failure()`
has already been evaluated by the time you get there. A failure in your gate then turns
the run red **without** triggering a rollback of a perfectly healthy application. That is
usually the semantics you want: *the app is up, the backup is not, and somebody needs to
act* — rolling the app back would fix nothing and cause an outage.

---

## §4. A backup gate must check the artifact, not the container's health

**Symptom**: the backup container has been `healthy` for months. There are no dumps.

**Cause**: the healthcheck watches something adjacent to the job — typically an HTTP
status port the image exposes — not the file the job is supposed to produce. The
container is genuinely healthy: the web server inside it is running. The `pg_dump` inside
it has failed every night since installation, and nothing in the system disagrees.

Seen in the wild: three months, zero dumps, `healthy` the whole time. The database being
silently unprotected was the one belonging to the identity provider that authenticated
every other service on the host.

**Fix**: gate on the artifact, and prove it has *content*:

```bash
docker exec <backup-container> /backup.sh          # force a cycle, don't wait for cron
docker exec <backup-container> ls -lh /backups/last/

# 1. Integrity: is it a valid gzip at all?
gzip -t /backups/last/<db>-latest.sql.gz && echo "gzip OK"

# 2. Content: does it contain DATA, not just schema?
gzip -dc /backups/last/<db>-latest.sql.gz | grep -c '^COPY public'

# 3. Truth: is a record you KNOW exists actually in there?
gzip -dc /backups/last/<db>-latest.sql.gz | grep -c '<a known value>'
```

Size alone is a weak proxy — a dump containing only `CREATE TABLE` statements is large,
well-formed, and useless for recovery. `COPY` count separates schema from data.

**Why the gate belongs in CD at all**: a nightly cron failure is invisible by
construction — nobody watches a job that produces nothing. Attaching a health assertion
to the deploy means the question "is this database backed up?" gets asked on a schedule
somebody actually reads. Combine with §3: place it after the rollback so a broken backup
turns the run red without taking the app down.

---

## §5. `prodrigestivill/postgres-backup-local` accepts a CSV list only in `POSTGRES_DB`

**Symptom**: multi-database backup container is `unhealthy` (or quietly failing) and
`pg_dump` logs an authentication error naming a user that doesn't exist — something like
`role "erp,zitadel" does not exist`.

**Cause**: the image supports backing up several databases by taking a comma-separated
list in **`POSTGRES_DB`**, against **one** host, user and password. Passing lists in
`POSTGRES_HOST` / `POSTGRES_USER` / `POSTGRES_PASSWORD` does not fan out — the values are
used literally, so the whole comma-joined string becomes the username.

**Fix**: one service per cluster/credential, each with its own `POSTGRES_HOST`,
`POSTGRES_USER`, `POSTGRES_PASSWORD`, and a CSV `POSTGRES_DB` only if those databases
share that one credential.

**Adjacent trap — image version**: the backup image tag pins the `pg_dump` version. A
`pg_dump` older than the server refuses to dump (`server version mismatch`), so a Postgres
17 cluster needs `…:17-alpine`, not `16-alpine`. This fails loudly, unlike the CSV trap,
but it fails *nightly and unwatched*, which amounts to the same thing.

---

## §6. Prove the sensor before trusting its silence

**Symptom**: you tail logs during a verification window, the capture file is empty, and
you report "no errors".

**Cause**: an empty capture is produced by two different worlds — *nothing bad happened*,
and *the capture was never running*. A broken pipe, an SSH session that died, a `grep`
pattern that matches nothing, a `docker logs --since` that resolved to the wrong window:
all of them look exactly like a clean run.

**Fix**: fire a deliberate probe and confirm it lands, before drawing any conclusion from
the absence of output:

```bash
# capture is supposedly running and filtering for 4xx/5xx
curl -s -o /dev/null "https://api.example.com/zz-probe-$$"   # a 404 you caused on purpose
sleep 5
grep -c "zz-probe-$$" "$CAPTURE_FILE"    # 0 → your sensor is dead, not your service clean
```

The same reasoning applies to any negative assertion in CD: a log dump step that prints
nothing, a `find` that returns no stale files, a grep for secrets that finds none. Ask
"would this have shown me a positive?" before believing the negative.

**Related**: `cd-pipeline-pitfalls.md` §5 covers the mirror image — a step that emits a
warning and is ignored because `continue-on-error` masks it.

---

## §7. `${{ vars.X }}` resolves at repository level too, not just environment

**Symptom**: a workflow references `${{ vars.SOMETHING }}`, the environment's variable
list is empty, and you conclude the deploy is missing a configuration value.

**Cause**: `vars` (like `secrets`) resolves through a hierarchy — organization →
repository → environment, with the most specific winning. A variable documented as
"set on the `production` environment" may in fact live at repository level and work
perfectly.

**Fix**: check both before declaring a blocker:

```bash
gh api repos/<owner>/<repo>/actions/variables --jq '.variables[] | "\(.name)=\(.value)"'
gh api repos/<owner>/<repo>/environments/<env>/variables --jq '.variables[] | "\(.name)=\(.value)"'
```

The practical consequence is the reverse too: a repository-level variable is shared by
*every* environment. That is right for something like a shared docker network name, and
wrong for anything that must differ between staging and production — put those on the
environment, where they can diverge.

---

## Symptoms → section

| Symptom | Section |
| --- | --- |
| Rollback "succeeded" but the broken version is still served | §1 |
| Rollback ran and production is down anyway | §2 |
| `previous_tag=unknown` on a first deploy | §1 |
| A gate you added never appears in the log of a failed deploy | §3 |
| Backup container `healthy` for months, no dumps exist | §4 |
| `pg_dump` authenticating as a comma-joined username | §5 |
| `pg_dump: server version mismatch` in the backup container | §5 |
| Empty log capture / no-output check reported as "clean" | §6 |
| `vars.X` looks unset because the environment list is empty | §7 |
