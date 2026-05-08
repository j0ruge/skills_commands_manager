# Docker Compose Bootstrap — Zitadel v4

This reference covers the surprising parts of standing up Zitadel locally with `docker compose`. The "happy path" examples in the upstream docs work, but several details are easy to miss and they cascade into hard-to-diagnose failures. Each section below explains the **why** so you can adapt rather than copy.

## §1. `ZITADEL_FIRSTINSTANCE_*` env vars belong on the `zitadel` service

The Zitadel image has three relevant subcommands:

| Subcommand | What it does | Honors `FIRSTINSTANCE_*`? |
|------------|--------------|---------------------------|
| `init` | Runs DB schema migrations only | No |
| `setup` | Creates the first instance + admin + service accounts + writes PAT/key files | Yes |
| `start-from-init` | Runs `init` + `setup` + `start` in one process | Yes (during the setup phase) |

A common mistake (visible in some upstream examples) is putting `ZITADEL_FIRSTINSTANCE_*` env vars on the `zitadel-init` container. They are silently ignored there because `init` doesn't perform setup. The PAT file you expected never appears, and the bootstrap script downstream fails with "PAT not found".

**Correct placement** (excerpt from `assets/docker-compose.zitadel.yml`):

```yaml
zitadel:
  image: ghcr.io/zitadel/zitadel:latest
  command: >-
    start-from-init
    --masterkey ${ZITADEL_MASTERKEY:?32 chars exactly}
    --tlsMode disabled
  environment:
    # ... db, externalDomain, etc ...
    ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORDCHANGEREQUIRED: "false"
    ZITADEL_FIRSTINSTANCE_PATPATH: /current-dir/admin.pat
    ZITADEL_FIRSTINSTANCE_ORG_MACHINE_MACHINE_USERNAME: admin-sa
    ZITADEL_FIRSTINSTANCE_ORG_MACHINE_MACHINE_NAME: Admin Service Account
    ZITADEL_FIRSTINSTANCE_ORG_MACHINE_PAT_EXPIRATIONDATE: "2099-12-31T23:59:59Z"
  volumes:
    - ./zitadel/local:/current-dir:rw
```

**Three FirstInstance "PAT" envs exist — pick the right one**:

| Env var | Service account it provisions | Role |
|---------|-------------------------------|------|
| `ZITADEL_FIRSTINSTANCE_PATPATH` | `Org.Machine` | **IAM_OWNER** — full Management API access. Use this for bootstrap scripts. |
| `ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH` | `Org.LoginClient` | IAM_LOGIN_CLIENT — only used by the Login UI v2 (`zitadel-login` container). Cannot create resources. |
| `ZITADEL_FIRSTINSTANCE_MACHINEKEYPATH` | `Org.Machine` | Same as above but writes a JSON RSA key (set `…_MACHINEKEY_TYPE=1`) instead of a PAT. Use when private-key JWT auth is required (production). |

If your bootstrap script returns 401/403 on every Management call despite a valid-looking token, check that you read `admin.pat` (Org.Machine), not `login-client.pat` (Org.LoginClient).

## §2. Volume permissions: chown to uid 1000 before first boot

The Zitadel image runs as a non-root user (uid `1000`). The `/current-dir` volume must be writable by that uid. If a prior `zitadel-init` run created the directory as root, the subsequent `setup` phase fails with `open /current-dir/admin.pat: permission denied` and falls into a restart loop.

The error message is in stderr only and easy to miss because the container keeps restarting. If `docker logs zitadel-1` shows repeated "setup failed" with no PAT file appearing, this is it.

**Fix** (already wired into `scripts/reset-zitadel.sh`):

```bash
docker compose -f docker-compose.zitadel.yml down -v
docker run --rm -v "$(pwd)/zitadel/local:/work" alpine sh -c \
  "rm -rf /work/* /work/.* 2>/dev/null; chown 1000:1000 /work && chmod 0777 /work"
docker compose -f docker-compose.zitadel.yml up -d
```

`down -v` is required: a partial setup leaves orphan events in the Postgres volume. The next attempt fails with `Errors.Instance.Domain.AlreadyExists` (SQL duplicate key) because it tries to insert an instance that's half-there. There is no recoverable state — wipe the DB volume.

The image is **distroless** — no shell, no `ls`, no `cat`. Use a sidecar Alpine container for any volume inspection: `docker run --rm -v <volume>:/x alpine ls -la /x`.

## §3. External domain, Host header, and sslip.io

Zitadel binds to `:8080` inside the container, but it validates the `Host` header on every incoming request against `ZITADEL_EXTERNALDOMAIN`. A request to `http://127.0.0.1:8080` when external domain is `127.0.0.1.sslip.io` returns:

```text
{"code":5,"message":"unable to set instance using origin &{127.0.0.1:8080  http} (ExternalDomain is 127.0.0.1.sslip.io): Instance not found."}
```

Two ways through:

1. **Use the external domain in the URL directly** (preferred). `127.0.0.1.sslip.io` resolves to `127.0.0.1` via the public sslip.io DNS — no /etc/hosts edit needed. Set `ZITADEL_API_URL=http://127.0.0.1.sslip.io:8080` in your client.
2. **Override the Host header**. Tempting, but Node's built-in `fetch` (undici) actively prevents you from setting `Host` — it overwrites it from the URL. Curl with `-H 'Host: ...'` works, but you'll need a custom HTTP agent in Node.

The first approach is one config line; do that.

In production behind a reverse proxy, set `ZITADEL_EXTERNALDOMAIN` to the public hostname. The proxy forwards the original `Host` header to the upstream Zitadel container — that's why proxies need `proxy_set_header Host $host;` in NGINX or equivalent.

## §4. `start-from-init` re-runs setup on every boot — that's fine

Don't be alarmed when you see `setup started` / `setup completed` in the logs on every container start. `setup` is idempotent — it checks events and skips already-applied steps. The only time you need a clean wipe is when setup has previously failed mid-flight (see §2).

## §5. Mailpit / SMTP for invite + recovery flows

Add a Mailpit sidecar in dev so invitation and password-reset emails land somewhere visible:

```yaml
mailpit:
  image: axllent/mailpit:latest
  ports:
    - "1025:1025"   # SMTP
    - "8025:8025"   # Web UI
  networks: [app]
```

Configure Zitadel SMTP via Console (System → SMTP Settings) or programmatically via `/admin/v1/smtp/config`. Point host at `mailpit:1025`, no auth, no TLS in dev.

Production uses Resend / AWS SES / Postmark with SPF + DKIM on the domain. Decide before the invite flow goes to real users — recovery links from a misconfigured-SPF sender will land in spam.

## §6. Verifying the boot worked

After `up -d`, run these three checks before assuming Zitadel is ready:

```bash
# 1. Container healthy (gives setup a chance to finish — usually 20-40 s)
until docker ps --format '{{.Names}}\t{{.Status}}' | grep -q "zitadel.*healthy"; do sleep 3; done

# 2. PAT file exists with non-empty content
test -s zitadel/local/admin.pat && echo "PAT OK" || echo "PAT MISSING — see §1/§2"

# 3. PAT actually works against the Management API
PAT=$(cat zitadel/local/admin.pat)
curl -sf -H "Authorization: Bearer $PAT" \
  http://127.0.0.1.sslip.io:8080/auth/v1/users/me | head
```

If step 3 returns the `admin-sa` user JSON, you are clear to run the bootstrap script. If it returns `Instance not found`, revisit §3.

## §7. TLS terminated by reverse proxy (Caddy / NGINX / Traefik)

For dev-LAN testing or any setup where you don't want Zitadel handling its own TLS, terminate at a reverse proxy. The combination is **three settings, not two** — `EXTERNALSECURE` and `TLS_ENABLED` are necessary but not sufficient. The third leg is the start flag `--tlsMode external`. Without it the binary still tries to negotiate TLS on its internal port and refuses traffic / restart-loops.

The minimal recipe (Caddy in front of Zitadel, both HTTPS-aware):

```yaml
# docker-compose.zitadel.yml — relevant excerpt
services:
  zitadel:
    image: ghcr.io/zitadel/zitadel:latest
    environment:
      ZITADEL_EXTERNALDOMAIN: my-host.example.com   # what end-users hit
      ZITADEL_EXTERNALPORT: 443                     # the HTTPS port the proxy serves
      ZITADEL_EXTERNALSECURE: "true"                # tokens get https:// issuer URLs
      ZITADEL_TLS_ENABLED: "false"                  # Zitadel itself stays plain HTTP
      # ...usual DB/masterkey envs...
    command: >-
      start-from-init
      --masterkey ${ZITADEL_MASTERKEY}
      --tlsMode external                            # the third leg of the triad
    ports:
      - "8080:8080"  # proxied internally; not exposed to end users

  caddy:
    image: caddy:2-alpine
    network_mode: host         # so Caddy can reach localhost:8080 + serve :443
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./certs:/certs:ro
    depends_on:
      zitadel:
        condition: service_healthy
```

`Caddyfile`:

```caddy
my-host.example.com:443 {
  tls /certs/cert.pem /certs/key.pem
  reverse_proxy localhost:8080
}
```

**Pitfalls when adopting this**:

- `ZITADEL_EXTERNALPORT` is the **public HTTPS port** users hit (often 443 in prod, or 8443 / similar in LAN dev), **not** Zitadel's internal port. Token issuer URLs are `<scheme>://<EXTERNALDOMAIN>:<EXTERNALPORT>`; mismatch breaks downstream JWT validation with `iss` errors that point everywhere except here.
- `EXTERNALDOMAIN`/`EXTERNALSECURE`/`EXTERNALPORT` are persisted in the Zitadel database on first init. **Changing any of them later requires `docker compose down -v`** — the volume keeps the original. If you change networks (laptop moving between Wi-Fi / hotspot) and the IP shifts, factor that into your dev launcher.
- Backends that fetch JWKS from `https://<EXTERNALDOMAIN>:<EXTERNALPORT>/oauth/v2/keys` must trust the cert the proxy serves. With mkcert / a local CA, set `NODE_EXTRA_CA_CERTS` on the Node backend (see `token-validation.md §"Trusting a self-signed JWKS endpoint from Node"`). Same applies to any tool (curl, integration tests, bootstrap script over HTTPS).
- For LAN testing, `<LAN_IP>.sslip.io` is a quick win — sslip.io resolves `1.2.3.4.sslip.io` to `1.2.3.4` for any client, so other devices on the network reach the same external URL without DNS setup. Combined with mkcert covering the same hostname, dev clients only need to import the local root CA once.

## §"Quirk 24 — masterkey via flag em v2.66.x"

**Aplica-se a:** Zitadel `v2.66.x` (linha 2.66 inteira, possivelmente 2.x mais antigas — não testei). Em `v4.x` o env-var fallback funciona; **não** aplique este workaround sem necessidade no v4.

**Sintoma**:

```text
panic: No master key provided
caller="cmd/start/start_from_init.go:30"
error="masterkey must either be provided by file path, value or environment variable"
```

Container em loop de restart, `RestartCount` crescendo, exit code 2 a cada ~60s. Log idêntico a cada ciclo.

**O que confunde**: `docker inspect <ctr> --format '{{range .Config.Env}}{{println .}}{{end}}'` mostra a variável presente e correta:

```text
ZITADEL_MASTERKEY=qMnP1D5gM0oclBSJKFmdifWlpfAnTvwR
```

— exatos 32 chars, sem CR/LF, sem leading whitespace, sem null bytes (validável com `xxd`). `docker compose config` também resolve o valor literal corretamente. E mesmo assim `start-from-init` panic'a.

**Causa raiz**: `cmd/key/key.go` em v2.66.x lê `os.Getenv("ZITADEL_MASTERKEY")` como fallback quando a flag CLI `--masterkey` está ausente — mas o caminho de leitura **não é confiável** sob certas combinações de cobra/viper bindings na linha 2.66. (Em v4 o caminho foi reescrito.) Quando isso falha, o erro é genérico ("masterkey must either be provided") e não distingue "ausente" de "presente mas não-lida", o que mata o sinal.

**Fix canônico — passar a masterkey como flag CLI**:

```yaml
zitadel:
  image: ghcr.io/zitadel/zitadel:v2.66.10  # ou outra v2.66.x
  command:
    - start-from-init
    - --masterkey
    - ${ZITADEL_MASTERKEY}
    - --tlsMode
    - external                              # quando atrás de proxy TLS — ver §7
  environment:
    # ZITADEL_MASTERKEY ainda pode ficar aqui (não atrapalha; serve como
    # fonte da interpolação ${...}). A flag tem precedência.
    ZITADEL_MASTERKEY: ${ZITADEL_MASTERKEY}
    # ... DB, externalDomain, etc ...
```

A flag tem precedência sobre env quando ambas existem, então é seguro deixar a env também (útil pra ferramentas que inspecionam o container e esperam a env).

**Trade-off de segurança**: a flag aparece em `docker inspect <ctr>` (campo `Args`/`Cmd`) e em `ps aux` no host. Aceitável quando:

- O `.env` está com `chmod 600` no host (já é boa prática).
- O VPS é dedicado (acesso SSH restrito a operadores).
- Você não tem agentes de inventário de terceiros enviando `docker inspect` para fora.

Se algum desses não for verdade, troque pelo arquivo:

```yaml
command:
  - start-from-init
  - --masterkeyFile
  - /run/secrets/zitadel_masterkey
secrets:
  - zitadel_masterkey
```

E declare o `secrets:` top-level apontando para um arquivo `chmod 400` ou um Docker secret externo.

**Prevenção**: `docker logs <ctr> --tail 5` logo após o primeiro `up -d` — se vir o panic, aplique a flag antes de gastar tempo investigando volume permissions, bytes da env, encoding, etc. (todos esses são red herrings pra esse panic específico em v2.66.)

## §8. Compose v4: login-container + nginx routing (Quirk 25)

**Aplica-se a:** Zitadel `v4.x` quando você quer usar a Login UI v2 (default em v3+) em vez de continuar em v1. Se prefere ficar com Login UI v1 indefinidamente, esta seção não é obrigatória — basta `PUT /v2/features/instance {"loginV2":{"required":false}}` (ver `troubleshooting.md §"Hosted UI returns 404"`) e o resto da skill cobre o caminho.

**Por que esta seção existe:** em v2.66 a Login UI v1 vinha embutida no binário do Zitadel; um único container atendia tudo (`/ui/login/`, `/oauth/v2/*`, `/management/v1/*`, `/v2/*`). Em v4 a Login UI v2 saiu do binário — virou container Next.js separado (`ghcr.io/zitadel/zitadel-login`). Compose precisa subir os dois, e o reverse proxy precisa rotear `/ui/v2/login` (Prefix) pro novo container.

### Compose mínimo

```yaml
services:
  zitadel:
    image: ghcr.io/zitadel/zitadel:v4.15.0
    command:
      - start-from-init
      # masterkey via env funciona em v4 (Quirk 24 era específico de v2.66)
      - --tlsMode
      - external                              # quando atrás de proxy TLS — ver §7
    environment:
      ZITADEL_EXTERNALDOMAIN: ${EXTERNALDOMAIN}
      ZITADEL_EXTERNALPORT: 443
      ZITADEL_EXTERNALSECURE: "true"
      ZITADEL_TLS_ENABLED: "false"
      ZITADEL_DATABASE_POSTGRES_HOST: postgres
      ZITADEL_DATABASE_POSTGRES_DATABASE: zitadel
      ZITADEL_DATABASE_POSTGRES_USER_USERNAME: zitadel
      ZITADEL_DATABASE_POSTGRES_USER_PASSWORD: ${POSTGRES_PASSWORD}
      ZITADEL_DATABASE_POSTGRES_USER_SSL_MODE: disable
      ZITADEL_DATABASE_POSTGRES_ADMIN_USERNAME: zitadel
      ZITADEL_DATABASE_POSTGRES_ADMIN_PASSWORD: ${POSTGRES_PASSWORD}
      ZITADEL_DATABASE_POSTGRES_ADMIN_SSL_MODE: disable
      ZITADEL_MASTERKEY: ${ZITADEL_MASTERKEY}
      # FirstInstance — agora dois PATs (IAM_OWNER + IAM_LOGIN_CLIENT)
      ZITADEL_FIRSTINSTANCE_PATPATH: /current-dir/admin.pat
      ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH: /current-dir/login-client.pat
      ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORDCHANGEREQUIRED: "false"
      ZITADEL_FIRSTINSTANCE_ORG_MACHINE_MACHINE_USERNAME: admin-sa
      ZITADEL_FIRSTINSTANCE_ORG_MACHINE_MACHINE_NAME: Admin Service Account
      ZITADEL_FIRSTINSTANCE_ORG_MACHINE_PAT_EXPIRATIONDATE: "2099-12-31T23:59:59Z"
    volumes:
      - ./zitadel/local:/current-dir:rw
    healthcheck:
      test: ["CMD", "/app/zitadel", "ready", "--config", "/zitadel.yaml"]
      interval: 10s
      timeout: 5s
      retries: 30
    depends_on:
      postgres:
        condition: service_healthy

  zitadel-login:
    image: ghcr.io/zitadel/zitadel-login:v4.15.0
    environment:
      ZITADEL_API_URL: https://${EXTERNALDOMAIN}
      # Token do service account IAM_LOGIN_CLIENT, escrito por FirstInstance
      ZITADEL_SERVICE_USER_TOKEN_FILE: /current-dir/login-client.pat
    volumes:
      - ./zitadel/local:/current-dir:ro
    depends_on:
      zitadel:
        condition: service_healthy

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: zitadel
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: zitadel
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U zitadel"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  postgres-data:
```

**Pontos não-óbvios deste compose:**

- `ZITADEL_FIRSTINSTANCE_LOGINCLIENTPATPATH` é o que **provisiona o PAT do IAM_LOGIN_CLIENT** que o container `zitadel-login` consome. Se a env não existir antes do primeiro boot, FirstInstance não cria o service account, e o container `zitadel-login` falha pra subir com `permission denied` no PAT (que nunca foi escrito). Adicionar a env depois requer `down -v` — o estado de FirstInstance é congelado depois do primeiro setup.
- `zitadel-login` precisa **ler** o PAT do volume compartilhado (`/current-dir:ro`). Não monte com `:rw` — o container não escreve nada lá. Read-only previne corrupção acidental.
- `image: ghcr.io/zitadel/zitadel-login:v4.15.0` deve estar **na mesma versão** que `zitadel`. Versions desalinhadas (login v4.15 contra zitadel v4.14, p.ex.) podem ter API drift sutil — pin ambos no mesmo tag.

### Nginx routing

```nginx
server {
  listen 443 ssl http2;
  server_name idp.example.com;
  # ssl_certificate / ssl_certificate_key conforme seu ACME/let's-encrypt setup

  # Login UI v2 — container Next.js separado
  location /ui/v2/login {
    proxy_pass http://zitadel-login:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  # Tudo o mais — API container (OIDC discovery, /oauth/v2/*, /v2/*,
  # /management/v1/*, /admin/v1/*, /assets/v1/org/*, /ui/login/* (Login UI v1
  # se ainda usar via fallback))
  location / {
    proxy_pass http://zitadel:8080;
    proxy_set_header Host $host;          # Quirk 3 — Zitadel valida Host
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

### Caddy equivalente

```caddy
idp.example.com {
  handle_path /ui/v2/login* {
    reverse_proxy zitadel-login:3000
  }
  reverse_proxy zitadel:8080
}
```

`handle_path` (com asterisco) faz prefix-match, idêntico ao `location /ui/v2/login` do nginx — qualquer sub-path (`/ui/v2/login/login`, `/ui/v2/login/_next/static/...`) cai no container correto.

### Como detectar que o roteamento está OK

```bash
# Login UI v2 deve responder 200 ou 307
curl -sI https://idp.example.com/ui/v2/login | head -1

# OIDC discovery deve servir do container API, não do login
curl -sf https://idp.example.com/.well-known/openid-configuration | jq .issuer
# expect: "https://idp.example.com"

# JWKS deve vir do container API
curl -sf https://idp.example.com/oauth/v2/keys | jq '.keys | length'
# expect: número > 0
```

Se `/.well-known/openid-configuration` retornar 404 mas `/ui/v2/login` retornar 200, seu roteamento está invertido — provavelmente o `location /` veio antes do `location /ui/v2/login` e nginx pegou o match mais geral. Reordenar para que rotas específicas venham primeiro.

### E se eu quiser ficar com Login UI v1?

Path B do `migration-v2-to-v4.md §2`. Não suba o container `zitadel-login`, não faça split de routing — só desligue o flag de instância:

```bash
PAT=$(cat zitadel/local/admin.pat)
curl -sS -X PUT https://${EXTERNALDOMAIN}/v2/features/instance \
  -H "Authorization: Bearer $PAT" -H 'Content-Type: application/json' \
  -d '{"loginV2":{"required":false}}'
```

Login UI v1 continua servida em `/ui/login/` pelo container `zitadel` — mesmo behavior de v2.66. A diferença é que agora você sabe que pode mudar de ideia depois subindo o container `zitadel-login` e revertendo o flag, sem reset.

## §"DefaultInstance feature flags pre-config" (Quirk 31)

When the upstream Login UI v2 auto-provisioning bug (Quirk 28) blocks `/ui/v2/login` *and* the operator can't login to the console to create the IAM_OWNER PAT manually because the OIDC redirect to `/ui/v2/login` 404s, the cleanest break is to set the `loginV2.required` flag in **DefaultInstance** config (an env on the `zitadel` server) so the instance is born with the flag already off:

```yaml
zitadel:
  environment:
    ZITADEL_DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED: "false"
    # ...other FirstInstance envs...
```

This takes effect at first boot (when `setup` phase creates the default instance). The OIDC authorize endpoint then redirects to `/ui/login` (v1, embedded in the binary) immediately — no PAT needed, no chicken-and-egg. Bootstrap's runtime call `PUT /v2/features/instance {"loginV2":{"required":false}}` becomes a no-op idempotency check.

**Why this matters in CI/CD cutovers**: in a fresh-volume cutover, the `bootstrap` service user (and its PAT in `ZITADEL_PAT` secret) doesn't exist yet — the wipe killed the previous one. Bootstrap fails 401. Operator must login to console to create a new PAT — but console redirects through the broken `/ui/v2/login`. With `DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED=false`, the loop opens at the right place: console works on `/ui/login` v1, operator creates PAT, updates secret, bootstrap re-runs successfully.

Other DefaultInstance feature flags follow the same pattern: `ZITADEL_DEFAULTINSTANCE_FEATURES_<FLAG_NAME>_<FIELD>=<value>`. Useful when you need a feature-flag baseline different from upstream defaults across all your environments.

## §"nginx-proxy: split VIRTUAL_HOST + VIRTUAL_PATH" (Quirk 32)

When you put two containers behind the same `VIRTUAL_HOST` and split traffic by path (e.g., `zitadel-login` on `VIRTUAL_PATH=/ui/v2/login` for the modern Login UI, plus `zitadel` on root for everything else), nginx-proxy will silently ignore the container that doesn't declare a `VIRTUAL_PATH`. Only the more-specific path gets a `location {…}` block in the generated `nginx.conf`; everything else returns 404.

Symptoms:

- `curl https://idp.example.com/.well-known/openid-configuration` → 404
- `curl -sI /ui/console` → 404
- `nginx-proxy` access log shows trailing `"-"` upstream (no route matched, e.g., `"GET /.well-known/openid-configuration HTTP/2.0" 404 153 "-" "curl/8.5.0" "-"`)

Fix — declare `VIRTUAL_PATH=/` + `VIRTUAL_DEST=/` on the "default" container too, so nginx-proxy registers both as siblings:

```yaml
zitadel:
  environment:
    VIRTUAL_HOST: idp.example.com
    VIRTUAL_PATH: /                    # NEW — required when sibling has VIRTUAL_PATH
    VIRTUAL_DEST: /                    # NEW — strip nothing, pass-through
    VIRTUAL_PORT: 8080
    VIRTUAL_PROTO: http

zitadel-login:
  environment:
    VIRTUAL_HOST: idp.example.com
    VIRTUAL_PATH: /ui/v2/login
    VIRTUAL_DEST: /
    VIRTUAL_PORT: "3000"
```

General nginx-proxy quirk — applies to any split (API + admin UI on same host, public site + RPC endpoint, etc.). The single-container "no VIRTUAL_PATH" pattern works only as long as **no sibling** introduces a VIRTUAL_PATH for that host.

## §"Idp-bootstrap Dockerfile: `src/` + canonical YAML path"

When packaging your bootstrap script (`bootstrap-zitadel.ts` style) into a Docker image, two pitfalls bite hard in CD:

1. **`tsx` imports under `src/` need the source available at runtime** — `bootstrap-zitadel.ts` typically imports helpers from `../src/infrastructure/...` (zod schemas, error matchers, Connect/v2 client wrappers). If your runtime stage only copies `dist/` (the compiled tsc output) plus `scripts/`, the runtime path doesn't exist and Node throws `ERR_MODULE_NOT_FOUND` *immediately* on script start. Fix: add `COPY packages/idp/src packages/idp/src` (and `COPY packages/idp/tsconfig.json packages/idp/`) in the runtime stage.

2. **YAML path drift across feature releases** — the canonical config path may move between releases (e.g., `specs/002-idp-oidc/contracts/zitadel-config.yaml` → `packages/idp/zitadel-config.yaml`). Dockerfile `COPY` lines hardcode the source path. Audit on every YAML restructure. The bake-into-image pattern (vs. bind mount) avoids the runtime path-resolution problem but trades it for a build-time path-drift problem.

Verify both with:

```bash
docker run --rm --entrypoint sh <image> -c 'ls /app/packages/idp/src; ls /config/zitadel-config.yaml'
```

## §"PASSWORDCHANGEREQUIRED for CI/CD reproducibility"

Already mentioned in §1 (FirstInstance env table), but the **why for CI/CD** is worth calling out: without `ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORDCHANGEREQUIRED=false`, the operator's first console login is forced into a password change. Result: the value in `ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORD` secret no longer matches the actual password. After any volume wipe (cutover, disaster recovery), FirstInstance recreates the user *with the stale secret value*, the operator tries the changed password (their muscle memory) and gets `password.check.failed`, debugging session ensues. Setting CHANGEREQUIRED=false makes the secret the immutable source of truth — wipe + redeploy + login-with-secret-value just works, every time.

## §"Smoke-e2e plumbing checklist for GHA"

Bringing a long-disabled smoke-e2e job back to green tends to expose 4-5 layers of unrelated breakage that have rotted under `continue-on-error: true`. The order below is the order failures surface — fix one, the next becomes visible. Each item links to the underlying quirk in `troubleshooting.md` where applicable.

1. **Pre-create the Zitadel bind mount with `chmod 0777`** (Quirk 38). Without this, the `admin.pat` write in `03_default_instance` migration fails with EACCES and cascades into a misleading `unique_constraints_pkey` error.

   ```yaml
   - name: Pre-create writable bind mount for Zitadel admin.pat
     run: |
       mkdir -p infra/docker/zitadel/local
       chmod 0777 infra/docker/zitadel/local
   ```

2. **Scope `docker compose up --wait` to the services you actually exercise** (Quirk 40). Listing only `zitadel-db zitadel-init zitadel` skips the slow Login UI v2 Next.js healthcheck, which doesn't matter for bootstrap or REST integration tests.

   ```yaml
   - name: Boot Zitadel stack
     run: |
       docker compose -f infra/docker/docker-compose.zitadel.yml up -d --wait --wait-timeout 120 \
         zitadel-db zitadel-init zitadel
   ```

3. **Use a structured password generator for the seed user** (Quirk 39). `openssl rand -hex` is lowercase-only and trips the default 4-class policy; prefix with `Aa1!` to guarantee upper/lower/digit/symbol.

   ```yaml
   - name: Bootstrap Zitadel
     working-directory: packages/idp
     run: |
       RAND_TAIL="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 28)"
       export ZITADEL_SEED_USER_PASSWORD="Aa1!${RAND_TAIL}"
       npx tsx scripts/bootstrap-zitadel.ts
   ```

4. **Apply Prisma (or your ORM's) migrations to the ephemeral Postgres** before integration tests. `prisma generate` produces `_generated/client` (otherwise vitest collect dies with `ERR_MODULE_NOT_FOUND`); `prisma migrate deploy` against the test DB gives the schema (otherwise SELECTs hit `relation does not exist`):

   ```yaml
   - name: Prisma generate
     env:
       DATABASE_URL: postgresql://ci@localhost:5432/ci?schema=idp  # parseable; generate doesn't connect
     run: npm run prisma:generate --workspace=@your/idp
   - name: Apply Prisma migrations to ephemeral Postgres
     working-directory: packages/idp
     env:
       DATABASE_URL: postgresql://postgres@localhost:5432/jrc?schema=idp
     run: npx prisma migrate deploy
   ```

5. **Capture the bootstrap output into `$GITHUB_ENV`** so integration tests with `envReady()` guards actually run instead of silently skipping. The `bootstrap.json` written by the script after the `chmod 0777` from step 1 is now host-readable; pull `projectId` and the path to `admin.pat`:

   ```yaml
   - name: Capture Zitadel envs from bootstrap output
     run: |
       PROJECT_ID="$(jq -r '.projectId' infra/docker/zitadel/local/bootstrap.json)"
       {
         echo "ZITADEL_API_URL=http://127.0.0.1.sslip.io:8080"
         echo "ZITADEL_PROJECT_ID=${PROJECT_ID}"
         echo "OIDC_AUDIENCE=${PROJECT_ID}"
         echo "ZITADEL_PAT_FILE=${GITHUB_WORKSPACE}/infra/docker/zitadel/local/admin.pat"
       } >> "$GITHUB_ENV"
   ```

6. **Always dump container logs in the on-failure step** — `up --wait` only reports `is unhealthy` to stdout; the actual reason (EACCES, password policy, slow render) lives in `docker compose logs <service>`. Include `zitadel-login` in the dump even when you don't `--wait` for it, so future debug attempts have visibility:

   ```yaml
   - name: Show Zitadel stack logs (on failure)
     if: failure()
     run: |
       docker compose -f infra/docker/docker-compose.zitadel.yml ps
       for svc in zitadel zitadel-init zitadel-db zitadel-login; do
         echo "=== $svc ==="
         docker compose -f infra/docker/docker-compose.zitadel.yml logs --no-color --tail=200 "$svc" || true
       done
   ```

**Order matters**: don't try to fix step 4 (Prisma) before step 1 (bind mount perms). The earlier failure masks every later layer until it's resolved — debugging step 4 against a Zitadel that crashed during boot is wasted effort.

**`continue-on-error: true` is a trap when these layers rot together**: the run-level conclusion stays "success" even though the smoke job is silently red. Either commit to keeping the job green (and add issue tracking with a clock when it goes red) or accept that the job is purely informational and move tests that genuinely matter into the `build` job's blocking pipeline.

## §9. Where to go next

- Programmatic configuration: `references/api-cheatsheet.md` (v1) + `references/api-v1-to-v2-mapping.md` (v2)
- Upgrading from v2.66 to v4: `references/migration-v2-to-v4.md`
- Token validation in your backend: `references/token-validation.md`
- Errors during steps above: `references/troubleshooting.md`
