---
description: Promote code to staging (and on to production) through the repo's real CD pipeline. Derives the trigger branch from the workflow's `on.push.branches` instead of assuming — pushing the wrong branch can deploy production by accident. Waits for CI green on the source commit, promotes by PR merge commit, then watches the run to completion. Triggers — deploy staging, promote to staging, subir para staging, CD pipeline, cd-staging, promover para produção.
metadata:
  version: 2.0.0
---

## Deploy to Staging

Promote the current work to the staging environment through whatever CD pipeline
the repository actually has.

**Read this before anything else.** A deploy command is one `git push` away from
shipping to production. Branch names carry no universal meaning: in one repo
`develop` triggers staging and `main` is just kept in sync; in another the chain
is `develop → staging → main`, where pushing `main` deploys to real users. An
earlier version of this command hardcoded the first topology, so running it in a
repo of the second kind would have deployed **production** while reporting
"staging". That is the failure this workflow exists to prevent.

So the first step is never `git push` — it is reading the workflows to learn
which branch triggers what. Everything else follows from that map.

### Step 0 — Discover the topology (never assume it)

Print the trigger block of every workflow and build the branch → pipeline map:

```bash
for f in .github/workflows/*.y*ml; do
  echo "── $f"
  awk '/^on:/{flag=1} flag{print} /^permissions:|^env:|^jobs:/{if(flag) exit}' "$f" | head -12
  echo
done
```

Read the output and write down, explicitly:

| Branch | Workflow it triggers | Environment |
|---|---|---|
| e.g. `staging` | `cd-staging.yml` | staging |
| e.g. `main` | `cd-production.yml` | **production** |

Two things to settle before moving on:

- **Which branch is the staging trigger?** That is your `TARGET`. Your current
  branch (usually `develop`, sometimes a feature branch) is the `SOURCE`.
- **Which branch is a production trigger?** Mark it. You must not push it in
  this flow, and if `TARGET` turns out to equal it, stop and tell the user —
  what they asked for and what would happen have diverged.

If no workflow listens to a push at all (deploys are manual, or on tags), say so
and stop. Inventing a push target is how a repo gets deployed sideways.

A useful confirmation, since workflow headers usually state the intent in prose:

```bash
head -12 .github/workflows/cd-*.y*ml
```

### Step 1 — Working tree must be clean

```bash
git status --short
```

Uncommitted changes mean the thing you are about to deploy is not the thing you
tested. Abort and tell the user what is dirty.

### Step 2 — Pre-flight, derived from the repo

The old version of this command hardcoded `yarn test --watchAll=false` and
`npx eslint src/`, which silently did nothing in repos using npm, pnpm, a
different lint scope, or a monorepo. Detect instead:

```bash
ls package-lock.json yarn.lock pnpm-lock.yaml 2>/dev/null   # package manager
node -e "console.log(Object.keys(require('./package.json').scripts||{}).join(' '))"
```

Run the scripts that exist (`lint`, `typecheck`, `test`), with the matching
runner. Two traps worth knowing:

- **Monorepos**: the root script often fans out to workspaces
  (`npm run test --workspaces`), while `typecheck` may only exist per workspace
  (`npm run typecheck --workspace=packages/backend`). A root command that finds
  no script exits 0 and looks like a pass.
- **`tsc --noEmit` can be a no-op.** In a solution-style `tsconfig.json`
  (`"files": []` with project references) it type-checks nothing. Use
  `tsc -b --noEmit` there.

Pre-flight is a fast local filter, not the gate. The gate is Step 3.

### Step 3 — Wait for CI green on the exact commit being promoted

Local checks and CI are not the same thing: CI runs integration suites,
containers and matrix jobs your laptop skips. Promoting while CI is still
running means finding out in the deploy what a cheap wait would have told you.

```bash
SOURCE=$(git rev-parse --abbrev-ref HEAD)
git fetch origin
gh run list --branch "$SOURCE" --limit 5 \
  --json databaseId,name,status,conclusion,headSha \
  --jq '.[] | "\(.databaseId) \(.name) \(.status)/\(.conclusion // "—") @\(.headSha[0:7])"'
```

Match the run's `headSha` against the commit you are promoting — a green run on
an older commit proves nothing about this one. If it is still running:

```bash
gh run watch <run-id> --exit-status --interval 20
```

Red CI stops the promotion.

### Step 4 — Sensors: what moves, and does it move the pipeline itself?

```bash
# Content this promotion carries (source → target)
git log --no-merges origin/$TARGET..origin/$SOURCE --oneline

# Content that exists ONLY on the target — the one that bites
git log --no-merges origin/$SOURCE..origin/$TARGET --oneline

# Does the promotion modify the CD workflows themselves?
git diff origin/$TARGET origin/$SOURCE --name-only -- .github/workflows/
```

How to read the second one: environment branches accumulate **merge commits**
from previous promotions, and `--no-merges` filters those out. Empty output is
the healthy case — the target has no content of its own and the merge is clean.
Real commits there mean someone committed straight to the environment branch. Do
not force past it: merge the target **back** into the source first (a merge
commit, not a squash), then promote. Squashing that reconciliation rewrites the
shared history and guarantees the same conflict returns on the next promotion.

The third command answers a question people forget to ask: if the promotion
changes `cd-*.yml`, which pipeline is about to run — the old one or the new one?
GitHub uses the workflow file **from the pushed commit**, so a change to the
staging workflow takes effect in this very run, while a change to the production
workflow only lands as a file and takes effect on the next promotion to
production. Say which case you are in, so nobody is surprised either way.

### Step 5 — Promote with a merge commit, via PR

For long-lived environment branches, promote with a **merge commit**, and prefer
a PR so the promotion leaves an artifact someone can read later:

```bash
gh pr create --base "$TARGET" --head "$SOURCE" \
  --title "Release: promote $SOURCE → $TARGET" --body-file <notes>
gh pr merge <number> --merge          # --merge, NOT --squash
```

Squash is wrong here specifically because environment branches are long-lived:
it creates a commit that shares no ancestry with the source, so the next
promotion sees the two branches as divergent and conflicts on content that is
actually identical.

If the repo's convention is a direct push instead of a PR, follow the
convention — check how previous promotions were made (`git log --merges
origin/$TARGET -5`) rather than imposing one.

Whatever the mechanism: **push only `$TARGET`.** Do not "sync" the production
branch as a side effect. If the user wants production, that is a separate,
explicit promotion (see below), not a step tucked inside a staging deploy.

### Step 6 — Watch the pipeline on the target branch

The run appears on the branch that received the push — `$TARGET`, not the source
branch. (The old version of this command looked on `develop` unconditionally and
would have reported on the wrong pipeline.)

```bash
sleep 10
gh run list --branch "$TARGET" --limit 3 \
  --json databaseId,name,status,conclusion,headSha \
  --jq '.[] | "\(.databaseId) \(.name) \(.status)/\(.conclusion // "—") @\(.headSha[0:7])"'
gh run watch <run-id> --exit-status --interval 20
```

### Step 7 — Report the outcome honestly

On failure, show the failing step and say the deploy did not happen:

```bash
gh run view <run-id> --log-failed
```

On success, report the run URL and — this is the part worth stating explicitly —
**which environment is now serving the new code**. A pipeline that ends green
having skipped its smoke step is not the same as a verified deploy; check that
the smoke/health step actually ran rather than being skipped.

The work is complete only when the pipeline finishes successfully. Do not exit
silently on failure.

### Promoting to production

Same procedure, one step further along the chain: `SOURCE` becomes the staging
branch, `TARGET` becomes the branch whose push triggers the production workflow.
Two differences that matter:

- **Ask first.** Staging is reversible in practice; production is visible to
  real users. Confirm explicitly, even if the user asked for "deploy" in general
  terms earlier in the conversation.
- **Workflow changes cross over here.** Edits to `cd-production.yml` that rode
  along in an earlier promotion are inert until this merge — the production
  pipeline that runs is the one in the commit you are pushing now.

### Notes

- The image tag and the runner label come from the workflow, not from this
  command — read them there if the user asks.
- `gh pr merge` sometimes merges successfully and then fails while updating the
  local checkout, which reads as "the merge failed". Confirm with
  `gh pr view <n> --json state,mergeCommit` before retrying, or you will try to
  merge something already merged.
- After a squash merge, `git branch -d` refuses with "not fully merged" even
  when every change is integrated — it tests ancestry, and squash breaks it. The
  sensor that actually settles it is content: `git diff <target> <branch>` empty
  means nothing was left behind.
