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

## §6a. When you prove a sensor by BREAKING the code, the sabotage is the probe — and it can fail to land

**Symptom**: you sabotage a file to confirm a linter/test actually catches the defect, the
tool exits 0, and you conclude the sensor is blind. You then write that conclusion down —
in a commit message, a review reply, a lessons file — and it is false.

**Cause**: §6 above is about a probe that never ran. This is the same failure one layer
in: the *edit* never happened. The scripted edits people reach for here fail **silently**
when the pattern misses:

| Edit method | Pattern doesn't match | Silent? |
| --- | --- | --- |
| Python `str.replace(a, b)` | returns the string **unchanged** | **yes** — no exception, no return code |
| `sed -i 's/a/b/'` | leaves the file unchanged, exits **0** | **yes** |
| `patch` / `git apply` | rejects with a non-zero exit | no |

A multi-line pattern assembled from memory is the common way to miss: an intervening
comment line, a different indent, a line you thought was adjacent and isn't. The two
transcripts are byte-identical — *"I ran the sensor over the sabotaged code and it
passed"* — and only one of them is true.

This is worse than a wasted check. You publish a claim that a tool is blind when it is
not, and the next person trusts it and skips the guard.

**Fix — assert the sabotage landed, in both directions:**

```bash
python3 - <<'EOF'
s = open(path).read()
assert PATTERN in s, "pattern did not match — the sabotage never applied"
open(path, 'w').write(s.replace(PATTERN, BROKEN, 1))
EOF
grep -n "<the defect>" "$path"     # must print the line you just injected
<the sensor>; echo "exit=$?"       # must be non-zero
git checkout -- "$path"
<the sensor>; echo "exit=$?"       # must be zero again
```

Measured 2026-09-22: a sabotage meant to show `actionlint` ignoring
`${{ }}` inside a shell comment never applied — the replace pattern skipped an intervening
comment line. `actionlint` ran against the **original** file and exited 0, and that was
recorded as "the sensor is blind". Re-run with the assertion in place: exit 1,
`expression: potentially untrusted`, with line:column. The tool had been right all along
(it is the same detection `cd-pipeline-pitfalls.md` §9 relies on).

**Rule of thumb**: a green sensor over code you *believe* is sabotaged proves nothing
until you have seen the defect in the file. Prefer `sed`+`grep` verification or a tool
that fails loudly (`git apply`) over a silent string replace.

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

## §8. `cmd | tail` throws the exit code away — and `PIPESTATUS` does not exist in zsh

**Symptom**: a pre-flight or gate script prints `EXIT_TEST=` — empty, neither `0` nor a
number — and the run is reported as passing. Or worse: it prints nothing about the exit
status at all, and whoever reads the output assumes green because no failure was printed.

**Cause**: two separate faults that usually arrive together.

A pipeline's exit status is the status of its **last** command. So `npm test | tail -25`
exits with the status of `tail`, which is `0` no matter how the tests went. Piping a gate
to `tail`/`head`/`grep` to keep the log short silently converts every failure into a pass.

The reflex fix is `${PIPESTATUS[0]}` — and that is a **bash** array. In zsh the equivalent
is `$pipestatus`, and it is **1-indexed**, so `${pipestatus[1]}` is the first command.
Referencing `${PIPESTATUS[0]}` under zsh does not error: it expands to the empty string.
The gate then assigns `EXIT_TEST=` and every later comparison operates on nothing.

This matters beyond a developer's laptop. CI `run:` steps default to bash on GitHub
Actions, but the same gate run locally as a pre-flight — by a human, or by an agent whose
shell is zsh — silently stops measuring. The local filter that was supposed to catch the
failure before CI becomes decorative, and the discrepancy is invisible because both
transcripts look identical.

**Fix**: do not read the exit status through a pipe at all. Redirect to a file and read
`$?` directly — portable across shells, and it keeps the full log for when you need it:

```bash
npm run test      > test.log 2>&1; echo "EXIT_TEST=$?"  > exits.txt
npm run lint      > lint.log 2>&1; echo "EXIT_LINT=$?" >> exits.txt
npm run typecheck > tsc.log  2>&1; echo "EXIT_TSC=$?"  >> exits.txt
cat exits.txt          # three real numbers, or the gate is lying to you
```

If you genuinely need the pipe, set `set -o pipefail` (bash and zsh both honour it) so the
pipeline adopts the first non-zero status, instead of reaching for a `PIPESTATUS` spelling
that differs between the two shells.

**How to tell you have this bug**: the value is *empty*, not wrong — so a check for
"non-zero" never fires. Grep your own output for an assignment with nothing after the `=`:

```bash
grep -E 'EXIT_[A-Z]+=$' exits.txt && echo "the gate measured nothing"
```

**Related**: this is §6 applied to the gate command itself — the sensor was silent because
it never ran, not because the thing it watches is clean. Ask the same question: *would
this have shown me a positive?* A gate that cannot print a non-zero is not a gate.

---

## §9. Passo one-shot cujo produto é ESTADO: o smoke prova que o serviço responde, não que o passo escreveu

**Symptom**: o CD fica verde de ponta a ponta — pré-condições, `healthy`, o
passo de provisionamento, o smoke — e a coisa que o deploy existia para fazer
não aconteceu. Ninguém percebe no dia; percebe-se quando alguém tenta usar o que
deveria ter sido criado.

**Cause**: os deploys que este runbook trata normalmente entregam um **serviço**,
e o smoke certo para serviço é "ele responde pelo caminho do usuário". Mas
certos passos entregam **estado**: um bootstrap de IdP que cria papéis, um seed
que insere linhas de catálogo, uma migration de dados que converte colunas. Para
esses, "o serviço responde" é verdadeiro **antes e depois** do passo — inclusive
quando ele não fez nada.

Agrava que esses passos são idempotentes por desenho, e idempotência tem
vocabulário próprio (`reuse`, `already exists`, `no changes`, `skipped`) que é
**indistinguível** entre dois mundos opostos: *"já estava certo"* e *"eu li uma
declaração velha e concordei com ela"*. O log mais tranquilizador do pipeline é
justamente o que não distingue o sucesso do vazio.

Mesma família do §4 (backup `healthy` sem um dump) e do §6 (provar o sensor
antes de confiar no silêncio): o sinal observa algo **adjacente** ao trabalho.

**Fix — asseverar o estado, e de preferência a partir da declaração**:

- **A asserção nasce do input.** Se o passo é dirigido por um arquivo
  declarativo (YAML, JSON, uma lista), o pós-teste é: *cada item declarado
  existe depois?* Isso pega tanto o passo que não rodou quanto o que rodou
  contra uma declaração velha (`cd-pipeline-pitfalls.md §10`).
- **A saída do próprio passo costuma bastar**, e é mais barata que consultar o
  banco: um bootstrap que imprime `created X` / `reuse X` por item permite
  cruzar a lista impressa com a declarada, sem credencial nova nem acesso ao
  datastore.
- **Se for consultar o estado, prefira o caminho sem segredo.** Ler a projeção
  ou a tabela direto no container do banco não exige token, não expira e não
  precisa de rede — e não some quando alguém rotaciona um PAT.

**A pergunta que generaliza**: *este passo produz um serviço ou um fato?* Se
produz fato, o gate tem de olhar o fato. Um smoke a mais sobre o endpoint não
compensa a ausência dessa pergunta.

Medido em 2026-09-18 (IdP JRC): quatro passos verdes enquanto o bootstrap não
criava papel nenhum; quem desmentiu foi um `SELECT` na projeção de papéis,
rodado à mão **depois**, por desconfiança — não pelo pipeline.

## §10. `migrate deploy` green does not say WHICH role the application runs as

**Symptom**: migrations apply, the container is `healthy`, the smoke passes — and the
append-only guarantee you wrote a migration for is not in force. Nothing anywhere is red.

**Cause**: a schema with `REVOKE UPDATE/DELETE` on audit tables needs **two** database
identities, and the deploy carries both:

| Who | Role | Why |
| --- | --- | --- |
| `prisma migrate deploy` / `migrate` / `alembic upgrade`, and the seed | the **owner** | it creates tables, roles and grants — the restricted role cannot |
| the running application | the **restricted** role | the REVOKE is enforced by the database, not by the use case |

Swapping them is worse than omitting one. Run migrations as the restricted role and they
fail loudly, which is fine. Run the **application** as the owner and everything works —
the REVOKE becomes decorative at runtime and survives only inside the integration test,
where the fixture happens to connect correctly. The audit trail is rewritable and every
signal says healthy.

**Fix — prove the role from the database, after the smoke has opened the pool:**

```bash
docker compose -p "$PROJECT" -f "$COMPOSE_FILE" exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U <owner> -d <db> -tAc \
  "SELECT DISTINCT usename FROM pg_stat_activity
   WHERE datname='<db>' AND backend_type='client backend';"
```

Assert **both halves**: the restricted role is present, and the owner is **absent**. Only
the first is the obvious check, and alone it passes while a second connection pool runs as
the owner.

Order matters and is easy to get wrong: the check must run **after** something opened the
pool. A readiness endpoint that touches the database is the cheapest trigger — before any
query, `pg_stat_activity` is legitimately empty and the assertion fails for the wrong
reason.

**Related**: if the migration creates the application role without a password (the right
call — migrations are versioned and run in every environment, so they must not carry
secrets), the deploy needs an explicit `ALTER ROLE ... PASSWORD` step **between** the
migration and `up -d`. Skip it and the first boot is a crashloop that reads like a broken
image. Feed that SQL through **stdin**, never `-c` or an argument: command arguments show
up in `ps`, in the runner log and in the transcript.

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
| A gate prints `EXIT_X=` with nothing after the `=` | §8 |
| `cmd \| tail` reports success on a failing test suite | §8 |
| Green deploy whose provisioning step (bootstrap/seed/data migration) did nothing | §9 |
| Idempotent step logging `reuse`/`already exists` for everything — and it is a stale input | §9 |
| A linter/test passes over code you believe you sabotaged | §6a |
| Migrations green, container healthy, and an append-only REVOKE is not in force | §10 |
| App cannot authenticate with a password that works in `psql` | §10, and `cd-pipeline-pitfalls.md` §11 |
