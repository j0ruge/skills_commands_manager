# Shared Checklist — CI/CD Infrastructure

Shared sections between backend and frontend for new environment configuration.

---

## 1. Self-Hosted Runner

- [ ] Runner installed and running as a service: `sudo systemctl status actions.runner.*`
- [ ] Runner with the correct label: `staging` or `production`
- [ ] Runner appears as "Online" in GitHub > Settings > Actions > Runners
- [ ] Docker installed and accessible by the runner user
- [ ] Runner user in the `docker` group (avoids sudo/user issues)
- [ ] Runner user has permission for `docker compose`
- [ ] Labels verified in GitHub > Settings > Actions > Runners
- [ ] GHCR login in the deploy job via `docker/login-action@v3` before `docker compose pull` (automatic logout in post-step, config isolated per job — prefer over manual `docker login` on self-hosted runners)

**Runner installation:**

```bash
mkdir -p /opt/actions-runner && cd /opt/actions-runner
curl -o actions-runner-linux-x64-2.321.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz
tar xzf actions-runner-linux-x64-2.321.0.tar.gz
./config.sh --url https://github.com/JRC-Brasil --token <ORG_TOKEN> --labels <staging|production>
sudo ./svc.sh install && sudo ./svc.sh start
```

---

## 2. GHCR / Images

- [ ] Package visibility is **Private** (inherited from the repo)
- [ ] `GITHUB_TOKEN` has `packages: write` permission in the workflow
- [ ] Correct image tags: `staging` for develop, `v*` + `latest` for production

Verify at: `github.com/orgs/JRC-Brasil/packages`

---

## 3. DNS and SSL

- [ ] Domain DNS resolves to the server IP: `dig domain +short`
- [ ] Port 80 externally accessible (Let's Encrypt HTTP-01 challenge)
- [ ] nginx-proxy + acme-companion running on the server
- [ ] SSL certificate via Let's Encrypt (`LETSENCRYPT_HOST` configured)

---

## 4. nginx-proxy Network (Base)

- [ ] nginx-proxy Docker network exists on the server: `docker network ls | grep proxy`
- [ ] nginx-proxy container is running
- [ ] `VIRTUAL_HOST` configured in DNS (or `/etc/hosts` for testing)
- [ ] `NGINX_NETWORK_NAME` secret matches the exact network name

---

## 5. First Deploy (Bootstrap)

When the repository is new and has never been deployed to staging:

- [ ] Workflows (`.github/workflows/ci.yml`, `cd-staging.yml`, `cd-production.yml`) are committed and pushed
- [ ] Branch `develop` exists on the remote: `git ls-remote --heads origin develop`
- [ ] Workflows are present in the `develop` branch (CD Staging triggers on push to `develop` — if the workflows are not in that branch, the pipeline will not fire)
- [ ] After the first push to `develop`, verify: `gh run list --limit 5` (requires [GitHub CLI](https://cli.github.com/) installed and authenticated, or check via web under Actions)
- [ ] If the pipeline did not fire, check that the `.github/workflows/*.yml` files are in the `develop` branch

**Typical bootstrap:**

```bash
# If develop does not exist yet
git checkout -b develop
git push -u origin develop

# If develop already exists but does not have the workflows
git checkout develop
git merge main  # brings the workflows from main (or master, as applicable)
git push
```

> **Note:** If you create the workflows in `main` and merge into `develop`, the workflows will be in both branches. CD Staging only fires when there is a push to `develop`.
