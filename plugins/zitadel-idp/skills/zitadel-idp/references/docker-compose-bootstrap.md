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

## §9. Where to go next

- Programmatic configuration: `references/api-cheatsheet.md` (v1) + `references/api-v1-to-v2-mapping.md` (v2)
- Upgrading from v2.66 to v4: `references/migration-v2-to-v4.md`
- Token validation in your backend: `references/token-validation.md`
- Errors during steps above: `references/troubleshooting.md`
