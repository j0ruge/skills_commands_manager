# Self-Hosted Runner — versão dockerizada (myoung34/github-runner)

Esta reference cobre o caso **runner em container** com a imagem `myoung34/github-runner` (FR-022a, R-002 nos specs JRC). Para runner via systemd no host, ver `troubleshooting-shared.md §"Runner Offline"`.

A imagem `myoung34/github-runner` é a fonte mais usada para conteinerizar o runner do GitHub Actions: binário oficial empacotado em Ubuntu, lê config via env vars, suporta JIT/ephemeral, integra com `docker.sock` mount para evitar docker-in-docker. Mas existem 6 pegadinhas que mordem na primeira tentativa de envelopá-la em um Dockerfile customizado para integrar com seu compose de produção.

## Quando usar esta reference

- Você está montando um `infra/docker/runner/Dockerfile` que estende `myoung34/github-runner`.
- Runner em loop infinito de restart, exit 0 ou exit 2, com logs de "Configuring" / "Cannot configure".
- Runner sobe mas o GitHub vê labels erradas (`default` em vez de `production`/`staging`).
- Workflows com `runs-on: [self-hosted, production]` reportam "No runner matching the specified labels".
- Build do Dockerfile do runner falha em `gpg --dearmor` (`cannot open '/dev/tty'`).

## §1. CMD herdado é zerado quando você define ENTRYPOINT

**Sintoma**: runner configura com sucesso (`√ Settings Saved`), aparece online no GitHub por 1-2 segundos, depois exit code 0 e o container reinicia. Loop infinito com `restart: always`. RestartCount cresce sem que nada de errado apareça nos logs — só "Configuring → Settings Saved → fim".

**Causa**: a imagem upstream tem:

```text
ENTRYPOINT ["/entrypoint.sh"]
CMD        ["./bin/Runner.Listener", "run", "--startuptype", "service"]
```

O `/entrypoint.sh` upstream termina com `exec "$@"` — ou seja, espera rodar o `CMD` herdado. Quando seu Dockerfile customizado faz `ENTRYPOINT ["/usr/local/bin/jrc-entrypoint.sh"]`, **o CMD herdado é zerado** (Docker spec: definir ENTRYPOINT reseta CMD se o CMD vinha da imagem base). Resultado: seu entrypoint chama `exec /entrypoint.sh` (sem args), upstream chama `"$@"` que é vazio, processo sai com 0.

**Fix**: restaurar o CMD explicitamente.

```dockerfile
FROM myoung34/github-runner:2.319.1-ubuntu-jammy@sha256:...

# ... seu RUN install + COPY entrypoint ...

ENTRYPOINT ["/usr/local/bin/jrc-entrypoint.sh"]

# Restaurar CMD da imagem base — definir ENTRYPOINT zera CMD herdado.
CMD ["./bin/Runner.Listener", "run", "--startuptype", "service"]
```

**Como confirmar o CMD canônico da versão que você está pinando**:

```bash
docker pull myoung34/github-runner:<sua-tag>
docker inspect myoung34/github-runner:<sua-tag> \
  --format 'CMD={{json .Config.Cmd}} ENTRYPOINT={{json .Config.Entrypoint}}'
```

Se a upstream mudar o CMD em uma versão futura, seu Dockerfile precisa acompanhar.

## §2. Env var de labels é `LABELS`, não `RUNNER_LABELS`

**Sintoma**: runner aparece online no GitHub mas com labels `["self-hosted", "Linux", "X64", "default"]` em vez das suas (`production` etc). Workflows com `runs-on: [self-hosted, production]` reportam "No runner matching the specified labels" — embora o runner exista.

**Causa**: o `/entrypoint.sh` upstream lê `LABELS` (com fallback para `default`):

```bash
_LABELS=${LABELS:-default}
./config.sh ... --labels "${_LABELS}"
```

Não lê `RUNNER_LABELS`. É um nome confuso porque outras envs do upstream usam o prefixo `RUNNER_` (`RUNNER_NAME`, `RUNNER_TOKEN`, `RUNNER_WORKDIR`).

**Fix no compose**:

```yaml
runner:
  environment:
    RUNNER_NAME: jrc-prod-01
    LABELS: production,self-hosted,linux,x64    # ← LABELS, não RUNNER_LABELS
    REPO_URL: https://github.com/JRC-Brasil/<repo>
    RUNNER_TOKEN: ${RUNNER_REGISTRATION_TOKEN}
    EPHEMERAL: "true"
```

**Fix em entrypoint custom** (se você quer aceitar `RUNNER_LABELS` por compatibilidade):

```bash
# Imagem upstream consome LABELS, não RUNNER_LABELS — exporta o alias.
export LABELS="${LABELS:-${RUNNER_LABELS:-default}}"
```

## §3. `EPHEMERAL=true` + `restart: always` = loop infinito

**Sintoma**: depois do primeiro registro com sucesso, container reinicia e acusa:

```text
Cannot configure the runner because it is already configured.
To reconfigure the runner, run 'config.cmd remove' or './config.sh remove' first.
```

Loop infinito. Cada ciclo: nova "Configuring" tentativa → erro → exit → restart.

**Causa**: o `config.sh` do runner escreve `/actions-runner/.runner` + `/actions-runner/.credentials` + `/actions-runner/.credentials_rsaparams` no FS layer do container ao registrar. Esses arquivos **persistem entre restarts** do mesmo container (restart != recreate em Docker). No próximo ciclo, `config.sh` detecta o `.runner` existente e aborta sem reconfigurar.

Com `EPHEMERAL=true`, o agente ainda precisa rodar (não termina sozinho); `restart: always` faria sentido pra resiliência. Mas o loop trava antes do `run.sh` começar.

**Fix no entrypoint custom**: limpar o state residual antes de delegar pro upstream.

```bash
# entrypoint.sh
set -euo pipefail

: "${RUNNER_NAME:?RUNNER_NAME é obrigatório}"
: "${REPO_URL:?REPO_URL é obrigatório}"
: "${RUNNER_TOKEN:?RUNNER_TOKEN é obrigatório}"

# Limpa state residual deixado por ciclos anteriores. Sem isso, o run.sh
# bate em "Cannot configure" se o container reinicia (FS layer persiste).
for f in /actions-runner/.runner \
         /actions-runner/.credentials \
         /actions-runner/.credentials_rsaparams; do
  if [[ -f "$f" ]]; then
    echo "[entrypoint] removendo state residual: $f"
    rm -f "$f"
  fi
done

# ... outras validações ...

exec /entrypoint.sh "$@"
```

**Alternativa mais arquitetural**: trocar `restart: always` por `restart: on-failure` ou nenhum restart, e orquestrar re-up via runner registration token externo. Mas o JIT token expira em 1h, o que torna esse caminho frágil — limpar `.runner` no entrypoint é mais robusto.

## §4. `gpg --dearmor` falha em buildkit não-tty

**Sintoma**: build do Dockerfile falha em:

```text
gpg: cannot open '/dev/tty': No such device or address
curl: (23) Failed writing body
```

Tipicamente em receita do tipo:

```dockerfile
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

**Causa**: buildkit não tem `/dev/tty`. Quando `gnupg` é instalado no mesmo `RUN` (apt-get install gnupg), o setup do pacote pode tocar TTY. `--dearmor` em si não precisa de TTY mas o gpg empacotado dispara um caminho que precisa.

**Fix**: pular o dearmor. APT moderno (Ubuntu 22.04+, Debian 12+) aceita keyring `.asc` direto via `signed-by=`. Reduz dependência (não precisa instalar `gnupg`) e elimina o pipe que falha.

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl jq \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu jammy stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*
```

Funciona idêntico no destino e fica mais simples.

## §5. Registration tokens são single-use e vencem em 1h

**Sintoma**: você gerou o token via `gh api -X POST .../actions/runners/registration-token`, gravou no `.env` ou em GH secret, mas no `up -d --build runner` o registro falha (e às vezes só falha **silenciosamente** — runner registra com label errada).

**Causas combinadas**:

1. Você gerou o token, esperou >1h pra usar (vence).
2. Você fez 2-3 ciclos de debug; cada `up -d` consumiu o token.
3. Você passou o mesmo token para outro runner.

**Hábito correto**: regenerar **imediatamente antes** de cada `up -d` que vai (re-)registrar runner. Em script de bring-up:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO=JRC-Brasil/validade_bateria_estoque
TOK=$(gh api -X POST "/repos/${REPO}/actions/runners/registration-token" --jq '.token')

# Atualiza .env atomicamente (sed in-place falha se a linha tem leading space —
# ver troubleshooting-shared §"Operational gotchas"). Aqui vamos de heredoc:
# (deixei só pra ilustrar — em prática reescreva o .env todo via heredoc)
grep -v "^RUNNER_REGISTRATION_TOKEN=" infra/docker/.env > infra/docker/.env.tmp
echo "RUNNER_REGISTRATION_TOKEN=${TOK}" >> infra/docker/.env.tmp
mv infra/docker/.env.tmp infra/docker/.env
chmod 600 infra/docker/.env

docker compose -f infra/docker/docker-compose.prod.yml up -d --build runner
```

Pra GH secret (consumido em CD que sobe runner remotamente):

```bash
TOK=$(gh api -X POST "/repos/${REPO}/actions/runners/registration-token" --jq '.token')
echo "$TOK" | gh secret set RUNNER_REGISTRATION_TOKEN --env production --repo "$REPO"
# Trigger workflow imediatamente — em <1h
```

## §5b. Multi-job CD em um dia exaure o token mesmo dentro da janela de 1h

`EPHEMERAL=true` significa que **cada job consome o token uma vez** — o runner deregistra ao fim e tenta re-registrar. Se você dispara 4-5 deploys consecutivos (debug iterativo de cutover, hotfixes, retries), o agente reusa o **mesmo** token salvo no `.env`/GH secret a cada ciclo e o GitHub responde `404` no segundo ciclo. Sintoma do container: `gh-runner Restarting (1)`, log:

```text
Http response code: NotFound from 'POST https://api.github.com/actions/runner-registration'
{"message":"Not Found","documentation_url":"https://docs.github.com/rest","status":"404"}
An error occurred: Not configured.
```

**Não é a janela de 1h** — pode acontecer 2 minutos depois do primeiro registro se você já rodou um ephemeral job no meio. CI da GitHub Actions ficou "in_progress → queued" porque o runner não voltou pra pool.

**Fix em mid-flight cutover**: regenerar token + atualizar **dois lugares** (GH secret + arquivo `.env` no host do runner) + force-recreate:

```bash
NEW_TOKEN=$(gh api -X POST "/repos/${REPO}/actions/runners/registration-token" --jq .token)
# (1) GH secret — pra próximas runs do CD
gh secret set RUNNER_REGISTRATION_TOKEN --env production --repo "$REPO" --body "$NEW_TOKEN"
# (2) .env no host do runner — pra recreate funcionar agora
ssh ops@runner-host "sed -i 's|^RUNNER_REGISTRATION_TOKEN=.*|RUNNER_REGISTRATION_TOKEN=$NEW_TOKEN|' /opt/.../infra/docker/.env && docker compose -f /opt/.../docker-compose.prod.yml up -d --force-recreate runner"
```

Ambos passos são necessários: a próxima execução do CD step "Gerar .env de produção" sobrescreve o `.env` com o secret atual; mas o **runner que está running agora** lê o `.env` existente. Sem atualizar os dois, ou o CD deploy do agora falha (env stale), ou o próximo CD falha (secret stale).

**Prevenção** (longa duração): rotacionar o token automaticamente em cada CD via job pre-deploy — `gh api … registration-token` + `printf` no `.env` antes do `up -d`. Caro nas APIs (uma chamada gerenciada por deploy) mas elimina o "queue stuck" intermitente.

## §6. Stale runner registrations no GitHub bloqueiam re-registro limpo

**Sintoma**: você derruba o container, limpa o volume `runner-work`, gera token novo, mas o registro continua dando "A runner exists with the same name" e/ou a label aparece errada (`default` em vez da que você passou).

**Causa**: o GitHub mantém o registro do runner offline mesmo depois do container sumir. Se você usa o mesmo `RUNNER_NAME`, o GH faz "replace" — mas em algumas combinações o replace mantém atributos do antigo (incluindo labels) em vez de aplicar os novos. E se você não tinha `--replace` na chamada do `config.sh`, falha com erro.

**Fix**: deletar o runner antigo via API antes de re-registrar.

```bash
REPO=JRC-Brasil/validade_bateria_estoque
RUNNER_NAME=jrc-prod-01

EXISTING=$(gh api "/repos/${REPO}/actions/runners" \
  --jq ".runners[] | select(.name==\"${RUNNER_NAME}\") | .id")
if [ -n "$EXISTING" ]; then
  gh api -X DELETE "/repos/${REPO}/actions/runners/${EXISTING}"
  echo "(runner ${EXISTING} '${RUNNER_NAME}' deletado)"
fi
# ... agora gere token + up -d ...
```

## Template canônico — Dockerfile + entrypoint

Junta os 6 pontos acima. Use como ponto de partida.

**`infra/docker/runner/Dockerfile`**:

```dockerfile
# syntax=docker/dockerfile:1.7
# Pinned por digest para imutabilidade — atualizar é decisão deliberada.
FROM myoung34/github-runner:2.319.1-ubuntu-jammy@sha256:147a7ee3fe2a2df69251ed12fed7906552b050a91bf0a4ee7b78c7a312cf5bf2

# docker-cli + compose plugin via socket-mount (R-002), sem docker-in-docker.
# Usa keyring .asc direto (evita gpg --dearmor que falha em buildkit non-tty).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl jq \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu jammy stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/jrc-entrypoint.sh
RUN chmod +x /usr/local/bin/jrc-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/jrc-entrypoint.sh"]

# CRÍTICO: definir ENTRYPOINT zera CMD herdado.
# Sem isso, runner configura → exit 0 → restart loop.
CMD ["./bin/Runner.Listener", "run", "--startuptype", "service"]
```

**`infra/docker/runner/entrypoint.sh`**:

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${RUNNER_NAME:?RUNNER_NAME é obrigatório}"
: "${REPO_URL:?REPO_URL é obrigatório}"
: "${RUNNER_TOKEN:?RUNNER_TOKEN é obrigatório}"

# Imagem upstream consome LABELS, não RUNNER_LABELS — exporta alias.
RUNNER_LABELS="${RUNNER_LABELS:-production,self-hosted,linux,x64}"
export LABELS="${LABELS:-$RUNNER_LABELS}"
export RUNNER_LABELS  # mantém disponível para logs/scripts

export EPHEMERAL="${EPHEMERAL:-true}"
export RUNNER_WORKDIR="${RUNNER_WORKDIR:-/runner/_work}"

echo "[entrypoint] runner: name=$RUNNER_NAME labels=$LABELS ephemeral=$EPHEMERAL repo=$REPO_URL"

# Limpa state residual de ciclos anteriores (restart != recreate; FS layer persiste).
for f in /actions-runner/.runner \
         /actions-runner/.credentials \
         /actions-runner/.credentials_rsaparams; do
  if [[ -f "$f" ]]; then
    echo "[entrypoint] removendo state residual: $f"
    rm -f "$f"
  fi
done

# Sanity-check do socket Docker (jobs de deploy precisam dele).
if [[ -S /var/run/docker.sock ]]; then
  if docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
    echo "[entrypoint] Socket Docker OK ($(docker version --format '{{.Server.Version}}'))"
  else
    echo "[entrypoint] AVISO: /var/run/docker.sock presente mas daemon não responde."
  fi
fi

exec /entrypoint.sh "$@"
```

**`docker-compose.prod.yml` (recorte)**:

```yaml
runner:
  build:
    context: ./runner
  container_name: gh-runner
  restart: always
  volumes:
    - "/var/run/docker.sock:/var/run/docker.sock"
    - "runner-work:/runner/_work"
  environment:
    RUNNER_NAME: jrc-prod-01
    LABELS: production,self-hosted,linux,x64       # NÃO RUNNER_LABELS
    REPO_URL: https://github.com/JRC-Brasil/<repo>
    RUNNER_TOKEN: ${RUNNER_REGISTRATION_TOKEN}
    EPHEMERAL: "true"

volumes:
  runner-work:
```

## Sequência de bring-up limpo

Quando algo deu errado e você precisa re-registrar do zero:

```bash
REPO=JRC-Brasil/<repo>
RUNNER_NAME=jrc-prod-01
COMPOSE=infra/docker/docker-compose.prod.yml

# 1. Apagar runner fantasma no GitHub (se existir)
EXISTING=$(gh api "/repos/${REPO}/actions/runners" --jq ".runners[] | select(.name==\"${RUNNER_NAME}\") | .id")
[ -n "$EXISTING" ] && gh api -X DELETE "/repos/${REPO}/actions/runners/${EXISTING}"

# 2. Gerar token novo (vence em 1h)
TOK=$(gh api -X POST "/repos/${REPO}/actions/runners/registration-token" --jq '.token')

# 3. Atualizar .env (heredoc é mais seguro que sed; ver §"Operational gotchas")
grep -v "^RUNNER_REGISTRATION_TOKEN=" infra/docker/.env > infra/docker/.env.tmp
echo "RUNNER_REGISTRATION_TOKEN=${TOK}" >> infra/docker/.env.tmp
mv infra/docker/.env.tmp infra/docker/.env

# 4. Down + drop volume + rebuild + up
docker compose -f "$COMPOSE" down runner
docker volume rm jrc-prod_runner-work 2>/dev/null || true
docker compose -f "$COMPOSE" build --no-cache runner
docker compose -f "$COMPOSE" up -d runner

# 5. Verificar
sleep 15
docker ps --filter name=gh-runner --format "table {{.Names}}\t{{.Status}}"
docker inspect gh-runner --format "RestartCount={{.RestartCount}}"
docker logs --tail 20 gh-runner
gh api "/repos/${REPO}/actions/runners" --jq '.runners[] | {id, name, status, busy, labels: [.labels[].name]}'
```

Esperado: `Up X minutes`, RestartCount=0, log com "Listening for Jobs", status `online` no GH com labels corretas.

## Sintomas → seção

| Sintoma | Vai para |
|---------|----------|
| Loop com exit 0 logo após "Settings Saved" | §1 (CMD) |
| Runner online no GH com label `default` | §2 (LABELS env) |
| "Cannot configure the runner because it is already configured" | §3 (state cleanup) |
| Build falha em `gpg --dearmor` / `cannot open '/dev/tty'` | §4 (use .asc direto) |
| Token consumido / "registration token has expired" | §5 (regenerar imediato) |
| "A runner exists with the same name" / labels antigas mantidas | §6 (DELETE no GH antes) |
