# Running a role migration across environments

Companion to `api-cheatsheet.md §"Renaming a project role"`, which owns the **API
calls**. This file owns the **operation**: how the new key comes into existence in
the first place, how step 2 stops being a hand-written `PUT` per user, and how you
keep three environments honest while the migration is half-done.

Read it when a role rename (Quirk 48) leaves the API recipe and becomes a runbook
someone else will execute, in an environment you are not looking at.

## Contents

- [1. Declare the role before you create it](#1-declare-the-role-before-you-create-it)
- [2. The field that the schema accepts and the bootstrap never reads](#2-the-field-that-the-schema-accepts-and-the-bootstrap-never-reads)
- [3. Step 2 as a tool, not a curl per user](#3-step-2-as-a-tool-not-a-curl-per-user)
- [4. Reading roles back: not every call has a v2](#4-reading-roles-back-not-every-call-has-a-v2)
- [5. Track state per environment, in the runbook](#5-track-state-per-environment-in-the-runbook)

---

## 1. Declare the role before you create it

The fastest way to unblock yourself mid-migration is the Console, or a one-off
`POST /roles` from a terminal. Both work, and both produce the same durable
problem: the role now exists as **runtime state** rather than as a declaration.

What that costs, concretely:

- a volume reset (`--reset-zitadel`, `down -v`) removes it, and the bootstrap does
  not put it back, because the YAML never mentioned it;
- the other environments do not get it at all — they are provisioned from the same
  YAML, and the YAML does not know;
- nothing is wrong anywhere. No error, no drift report. The environment where you
  did the click keeps working, which is what makes the gap survive.

So the first step of a rename is an edit to the declarative config, not a call:

```yaml
applications:
  - name: quote-web
    roles:
      # Legacy — removed only at the LAST step of the migration, and never
      # before the new key is granted in every environment.
      - key: quote.cotador
        displayName: Cotador
        group: quote
      - key: quote.consultor          # ← the new key, declared first
        displayName: Consultor
        group: quote
```

Then run the bootstrap, in every environment, and let it create the role. The
bootstrap being additive (Quirks 41/46/48) is a virtue here: re-running it is a
no-op, so "did this environment get the role?" is answered by running it again
rather than by remembering.

> The same reasoning applies in reverse at the end. Deleting the role in the
> Console without deleting the YAML entry means the next fresh instance recreates
> it — the migration un-finishes itself, silently. Quirk 48 says this; the point
> here is that both ends of the migration are edits to the **same file**.

### Pair the declaration with an assertion that expires

While the migration runs, the config legitimately carries **both** keys. That is
correct and temporary, and temporary states in config are exactly what outlive
their reason. Give the transition a sensor in the test that parses the real
config:

```ts
const keys = app.roles.map((r) => r.key);
expect(keys).toContain("quote.consultor");
// Legacy: removed at the last step of the migration.
// WHEN THAT HAPPENS, THIS LINE GOES WITH IT.
expect(keys).toContain("quote.cotador");
```

The second assertion has no value as a guarantee — nobody is at risk of deleting
the legacy key by accident. Its value is that it **fails** on the day someone
deletes it on purpose, putting the test file in the same commit as the YAML. Left
implicit, the legacy declaration is the thing that quietly stays forever.

---

## 2. The field that the schema accepts and the bootstrap never reads

**Quirk 50.** A declarative bootstrap grows a config schema, and the schema grows
faster than the code that consumes it. A field like `seedUser.roles` gets declared,
validated (`z.array(z.string().min(1)).default([])`), documented by its own
presence — and never read, because the code still takes that value from an
environment variable written earlier.

This is worse than a missing field. A missing field is a question someone asks. A
field that parses cleanly is an **answer**, and it is wrong:

- the config file reads like the source of truth, and reviewers reasonably treat it
  as one;
- the real source is an env var, whose value lives in the compose file — and there
  is usually more than one compose file;
- so the environment whose compose forgot the var silently falls back to the
  default. Measured: production set `ZITADEL_SEED_USER_ROLE=battery.admin,quote.admin`,
  staging did not set it at all, and staging's seed user was born with
  `battery.admin` alone. Nothing failed. The role simply was not there, and the
  first person to notice was whoever tried to use the second product in staging.

### The fix is precedence, not replacement

Do not make the YAML win outright. The env var is what a running environment uses
*today*, and flipping the source changes behaviour at the next deploy in the one
place you least want a surprise. Resolve with **`env > YAML > default`**:

```ts
export function resolveSeedUserRoles(
  envValue: string | undefined,
  yamlRoles: readonly string[],
): { roles: string[]; origem: 'env' | 'yaml' | 'default' } {
  const fromEnv = (envValue ?? '').split(',').map((r) => r.trim()).filter(Boolean);
  if (fromEnv.length > 0) return { roles: fromEnv, origem: 'env' };
  if (yamlRoles.length > 0) return { roles: [...yamlRoles], origem: 'yaml' };
  return { roles: ['battery.admin'], origem: 'default' };
}
```

Three details are load-bearing:

- **An env that is defined-but-empty is not a choice.** It falls through to the
  YAML. An empty var passes through `envsubst`, compose interpolation and every
  `??` in its path without a complaint — treating `""` as "the operator chose no
  roles" turns a typo into a user with no access and no error.
- **Log which source won.** `[user] seed roles: yaml → battery.admin,quote.admin`
  costs one line and answers the only question anyone will have when the grant
  looks wrong. Precedence is invisible in a compose file.
- **Put the resolver in its own module if your bootstrap script runs on import.**
  A script whose last statement is `main()` cannot be imported by a test without
  executing the whole bootstrap against a live Zitadel. Extract the pure function;
  the test is then free.

### Close the gap with a paired poka-yoke

Reading the field is half the fix. The other half is that a typo in it now reaches
the API instead of being ignored — `CreateAuthorization` rejects a role key that
does not exist, far away from the file that caused it. Validate the cross-reference
where the config is parsed:

```ts
}).superRefine((config, ctx) => {
  const declared = new Set(
    config.applications.flatMap((app) => app.roles.map((r) => r.key)),
  );
  config.seedUser?.roles.forEach((key, i) => {
    if (!declared.has(key)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `seedUser.roles[${i}] = "${key}" is not declared in applications[].roles[].key. `
          + `Declared: ${[...declared].sort().join(', ')}.`,
        path: ['seedUser', 'roles', i],
      });
    }
  });
});
```

Name the offending value and the valid set. A validator that only says "invalid"
sends the reader back to the same file they were already looking at.

> **Generalize the smell, not the field.** `seedUser.roles` is one instance. Any
> time a config schema and a bootstrap are maintained separately, ask of each field:
> *what breaks if I delete it?* If the answer is "nothing", it is not configuration
> — it is a comment that validates.

---

## 3. Step 2 as a tool, not a curl per user

Step 2 of the rename ("grant the new key to everyone who holds the old one") is
where the migration is actually dangerous, and it is the step the API makes
hardest to do safely:

- `roleKeys` **replaces** the set (Quirk 8), so correctness depends on the operator
  having read the current grant and rebuilt the union by hand;
- it is one call per user, so the risk is repeated as many times as there are
  users;
- a grant that loses a role of *another* product does so silently — no error, and
  the person only finds out when the other app 401s.

A runbook can only state this in prose. Turn it into a tool and the property is
enforced instead of requested. The shape that has worked:

```bash
# Dry-run is the DEFAULT. Writing requires --apply.
BOOTSTRAP_ENV=staging npm run grant-role -- \
  --role quote.consultor --when-has quote.admin,quote.cotador

  it@example.com: [battery.admin, quote.admin] → [battery.admin, quote.admin, quote.consultor]
  candidates=1 changed=0 already-had=0 outside-trigger=1
  dry-run — nothing written. Repeat with --apply.
```

Four properties, each one closing a specific way the manual step fails:

1. **Refuse a role that does not exist in the project, before any write.** Read the
   project's roles first and compare. A typo would otherwise create a grant nobody
   can use, and the tool would report success.
2. **Assert `after ⊇ before` immediately before each write.** This is deliberately
   redundant with whatever built the union — redundant because it is the guard that
   survives a future edit to that code. It is also the only check positioned where
   the damage happens.
3. **Dry-run by default; `--apply` to write.** The cheap mistake is writing nothing.
4. **Never call `DeleteAuthorization`, and never send a list shorter than the one
   read.** Step 3 (withdrawal) is a *different* operation with a *different*
   ordering constraint relative to the deploy — a tool that can do both invites
   someone to do both in one pass, which is exactly the outage Quirk 48 describes.

Keep the decision (which grants change, and to what) in a pure function, separate
from the HTTP. It is the part worth testing, and the test that matters is the one
asserting the result still contains everything the input had — sabotage it to
`roleKeys: [newRole]` and that case must go red, or the tool's central promise is
untested.

Parameterize it (`--role`, `--when-has`, environment from env) rather than hardcoding
this migration. The next rename is not hypothetical, and a general tool is the
difference between running it and rewriting it.

---

## 4. Reading roles back: not every call has a v2

**Quirk 49.** Listing a project's roles has **no Connect/v2 equivalent** in
v4.15.0. The path you would guess by analogy —
`/zitadel.management.v1.ManagementService/ListProjectRoles` — returns:

```json
404 {"code":5, "message":"Not Found"}
```

The working call is REST v1, with the project in the **path** and the org in the
**header** (Quirk 27's transition rule: the header is harmless on v2 calls, so an
HTTP helper can set it unconditionally):

```http
POST /management/v1/projects/{projectId}/roles/_search
Authorization: Bearer ${PAT}
x-zitadel-orgid: ${orgId}
{}
```

⚠️ **The failure mode is worse than a 404 in a log.** If this read backs a guard —
*"refuse a role that does not exist"* — then the guard refuses **everything**, for
the wrong reason, while printing a message that looks exactly like it working. A
refusal by the wrong cause is a refusal that lies, and it will keep lying for as
long as nobody tests it with a role that *does* exist.

Which is the general test: exercise a guard's **negative and positive** paths
against a live instance. A guard tested only on the input it should reject cannot
tell you it rejects everything.

> Corollary when you script this: `script | grep` returns **grep's** exit code.
> A sabotage check that reads `$?` through a pipe reports `0` while the script
> exits `1`, and you conclude the guard is broken when it is fine — or the reverse.

---

## 5. Track state per environment, in the runbook

A role migration is one procedure executed three times, days or weeks apart,
possibly by different people. The part that rots is not the steps — it is *which
ones already ran where*. "The migration is pending" is true on day one and still
sitting there, unchanged, after two of three environments are done.

Put a dated table at the top of the runbook and update it as part of doing the work:

```markdown
| Environment | Steps done | When | Pending |
|---|---|---|---|
| local   | 1, 2, 3, 5 | 2026-09-18 | 4, 6, 7 |
| staging | none       | —          | all     |
| prod    | none       | —          | all     |
```

Two habits keep it honest:

- **Prove a step by reading the state back from the API**, not by the tool's output.
  `grant-role` printing `changed=1` says the call was made; the grant fetched
  afterwards says what the IdP actually holds. They differ exactly when it matters.
- **Say what the pending environments are waiting for**, not just that they are
  pending. "staging: needs the alias-aware build deployed (step 6, which precedes
  step 4)" is actionable; "staging: pending" invites someone to run step 4 next.

The runbook is also where drift accumulates, because nothing tests prose. When you
execute a step and find the instructions wrong, fix the page in the same change —
the three most common drifts are: naming a script without naming **which repository**
it lives in (two repos with a `dev.sh` is the normal shape here), telling the
operator to edit a **generated** artifact (a `bootstrap.json` written by the
bootstrap and gitignored — the edit is discarded on the next run), and a note that
was true before the code changed underneath it.
