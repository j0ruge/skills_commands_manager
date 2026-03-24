# Troubleshooting — Shared Scenarios (Infrastructure)

Infrastructure scenarios that apply to both backend and frontend.

---

## 1. `unauthorized` on GHCR (Self-Hosted Runner)

**Message:**

```text
Error response from daemon: Head "https://ghcr.io/v2/.../manifests/...": unauthorized
```

**Cause:** The Deploy job on the self-hosted runner did not authenticate with GHCR before `docker compose pull`. Each GitHub Actions job has an isolated context — the login performed in the Build & Push job does not persist to the Deploy job.

**Diagnosis:**

```bash
# Check if the deploy job has a login step before the pull
grep -A5 "Login to GHCR" .github/workflows/cd-staging.yml
```

**Fix (workflow — recommended):**

Add `docker/login-action@v3` in the Deploy job, before `docker compose pull`:

```yaml
- name: Login to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

Prefer `docker/login-action@v3` over manual `docker login` because:
- **Automatic logout** in the post-step (cleans up credentials even if the job fails)
- **Isolated config** per job (avoids race conditions in `~/.docker/config.json`)
- **Credential masking** in logs via `@actions/core`

**Alternative fix (manual on the server — for debugging only):**

```bash
echo "$TOKEN" | docker login ghcr.io -u USERNAME --password-stdin
```

---

## 2. `network declared as external, but could not be found`

**Message:**

```text
network <name> declared as external, but could not be found
```

**Cause:** The Docker network name in `docker-compose.yml` (via the `NGINX_NETWORK_NAME` secret) does not match the actual network name created by nginx-proxy. The name depends on the compose directory (e.g., `nginx-proxy_default`, `proxy_default`).

**Diagnosis:**

```bash
docker network ls | grep proxy
```

**Fix:**

```bash
# Find the correct network name
docker network ls | grep proxy

# Update the secret with the correct name
gh secret set NGINX_NETWORK_NAME --env staging --body "correct_network_name"
```

---

## 3. `ERR_SSL_VERSION_OR_CIPHER_MISMATCH`

**Symptom:** The browser returns `ERR_SSL_VERSION_OR_CIPHER_MISMATCH`. `curl -svk` shows `sslv3 alert handshake failure`.

**Cause:** nginx-proxy responds on port 443, but **does not have a valid certificate** for the domain — it serves the default (self-signed) certificate. Let's Encrypt **did not issue** the certificate because the DNS does not point to the server IP.

**Diagnosis:**

```bash
# 1. Check DNS
dig domain +short
# Should resolve to the server IP

# 2. Test TLS handshake
curl -svk https://domain 2>&1 | grep -E "SSL|alert|subject"

# 3. Test port 80 (HTTP-01 challenge)
curl -sv http://domain 2>&1 | head -10
```

**Fix:**

1. **DNS not pointing:** Configure A/CNAME record to the server IP
2. **acme-companion not running:** Check if the `nginx-proxy-acme` container is running
3. **Port 80 blocked:** Open port 80 in the firewall (required for the HTTP-01 challenge)
4. **Certificate pending:** Restart the acme-companion and wait

---

## 4. Runner Offline / Labels Not Found

**Message:**

```text
No runner matching the specified labels was found
```

**Cause:** Self-hosted runner with label `staging` or `production` is not online.

**Diagnosis:**

```bash
# On the runner server
sudo systemctl status actions.runner.*

# Restart if needed
sudo systemctl restart actions.runner.*.service
```

**Monitor queue:**

```bash
gh run list --status queued
gh run list --status in_progress
```

---

## 5. Concurrency Group Blocking Deploys

**Symptom:** Deploy stays "queued" indefinitely.

**Cause:** With `cancel-in-progress: false`, a pending deploy blocks the next one. If the runner is offline, the queue can accumulate.

**Diagnosis:**

```bash
# List pending runs
gh run list --status queued
gh run list --status in_progress

# Cancel blocked run
gh run cancel <run-id>
```

**Prevention:** Monitor via `gh run list` before triggering new deploys.
