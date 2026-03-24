---
description: Syncs main with develop, merges the current branch into develop, and pushes to trigger the CD Staging pipeline.
metadata:
  version: 1.4.0
---

## Deploy to Staging

Automated flow to send the current branch to the staging environment via CD pipeline.
Automatically detects whether the user is on `develop` or a feature branch and adjusts the flow accordingly.

### Prerequisites

- Current branch must have all changes committed (clean working tree)
- `origin/develop` must be reachable
- Push access to `origin/main` and `origin/develop`

### Workflow

1. **Check working tree**

```bash
git status --short
```

If there are uncommitted changes, abort and inform the user.

2. **Pre-flight: lint + typecheck + tests**

Run the same checks that CI executes to avoid pipeline failures:

```bash
npx eslint src/ --max-warnings 0
npx tsc --noEmit
yarn test --watchAll=false
```

If any command fails, abort and inform the user. Do not proceed with push.

3. **Fetch remotes**

```bash
git fetch origin
```

4. **Detect current branch**

```bash
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
```

5. **Detect scenario (develop vs feature branch)**

If the current branch is `develop`, follow the **simplified flow** (step 5a).
Otherwise, follow the **full flow** (steps 6-8).

#### 5a. Develop flow — sync main and push

When already on `develop`, there is no feature branch merge. We only sync
`main` with what is already on the develop remote and then push the local commits.

```bash
git checkout main
git merge origin/develop --ff-only
git push origin main
git checkout develop
git push origin develop
```

If the ff-only merge fails, warn the user that there is divergence on main and abort.

After the push, skip directly to step 9 (verify pipeline).

---

6. **Sync main with develop** (feature branch flow)

```bash
git checkout main
git merge origin/develop --ff-only
git push origin main
```

If the merge fails (non-fast-forward), warn the user that there is divergence and abort.

7. **Merge feature branch into develop**

```bash
git checkout develop
git pull origin develop
git merge $CURRENT_BRANCH
```

If there are conflicts, abort and inform the user.

8. **Push develop to trigger CD staging**

```bash
git push origin develop
```

8a. **Return to working branch**

```bash
git checkout $CURRENT_BRANCH
```

---

9. **Capture the run-id of the triggered pipeline**

Wait a few seconds for the run to appear, then capture the ID:

```bash
gh run list --branch develop --limit 1 --json databaseId,status,name --jq '.[0].databaseId'
```

Store the returned `run-id`.

10. **Monitor pipeline until completion**

```bash
gh run watch <run-id>
```

Wait for the pipeline to complete. Do not consider the deploy finished until the pipeline ends.

11. **Evaluate result**

If the pipeline **fails**:

```bash
gh run view <run-id> --log-failed
```

Display the log of the failed step and report the error to the user with details.

If the pipeline **succeeds**:

Report success to the user with the run link:
`https://github.com/<owner>/<repo>/actions/runs/<run-id>`

**IMPORTANT:** The skill should only consider the work complete when the pipeline finishes successfully. If it fails, investigate and report — do not exit silently.

### Notes

- Pushing to `develop` automatically triggers the `cd-staging.yml` workflow
- The Docker image is built with the `:staging` tag and pushed to GHCR
- The deploy runs on the self-hosted runner with the `staging` label
