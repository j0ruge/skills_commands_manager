# Self-Hosted Runner — versão dockerizada (myoung34/github-runner)

Esta reference cobre o caso **runner em container** com a imagem `myoung34/github-runner` (FR-022a, R-002 nos specs JRC). Para runner via systemd no host, ver `troubleshooting-shared.md §"Runner Offline"`.

A imagem `myoung34/github-runner` é a fonte mais usada para conteinerizar o runner do GitHub Actions: binário oficial empacotado em Ubuntu, lê config via env vars, suporta JIT/ephemeral, integra com `docker.sock` mount para evitar docker-in-docker. Mas existem 6 pegadinhas que mordem na primeira tentativa de envelopá-la em um Dockerfile customizado para integrar com seu compose de produção.

## Quando usar esta reference

- Você está montando um `infra/docker/runner/Dockerfile` que estende `myoung34/github-runner`.
- Runner em loop infinito de restart, exit 0 ou exit 2, com logs de "Configuring" / "Cannot configure".
- Runner sobe mas o GitHub vê labels erradas (`default` em vez de `production`/`staging`).
- Workflows com `runs-on: [self-hosted, production]` reportam "No runner matching the specified labels".
- Build do Dockerfile do runner falha em `gpg --dearmor` (`cannot open '/dev/tty'`).
- Runner conecta e lista jobs mas o log diz `Runner version vX is deprecated and cannot receive messages` (§8).
- Log repete `Failed to create a session. The runner registration has been deleted from the server` (§9).
- `DISABLE_AUTO_UPDATE: "0"` não ligou o auto-update, ou runner pinado por digest deprecou meses depois (§8a).

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

> **Como descobrir o `@sha256:` (e aplicar às imagens do app também).** O pin por
> digest acima não é só para o runner — vale para `node`, `nginx`, `postgres` nos
> Dockerfiles/compose do app: uma tag flutuante (`node:22-alpine`, `postgres:17`)
> re-resolve para um build diferente a cada rebuild → imagem não reprodutível.
> Para resolver o digest **sem baixar a imagem** (lê só o manifest do registry):
>
> ```bash
> docker buildx imagetools inspect node:22-alpine | grep Digest
> # Digest: sha256:9385cd9f3001dfc3431e8ead12c43e9e1f87cc1b9b5c6cfd0f73865d405b27c4
> ```
>
> Depois fixe tag + digest (a tag legível fica para humanos; o digest garante a
> imutabilidade): `FROM node:22-alpine@sha256:…` no Dockerfile, ou
> `image: postgres:17@sha256:…` no compose. Atualizar o digest passa a ser uma
> decisão deliberada (re-rodar o `imagetools inspect`), não um drift silencioso.

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

## §7. `RUNNER_REGISTRATION_TOKEN` como GitHub secret estática = chicken-and-egg armadilha

**Sintoma**: deploy fica em `queued` indefinidamente. `gh api .../actions/runners` retorna `{"total_count": 0}` ou o runner correto está com `status: offline`. No host, `docker ps` mostra `gh-runner` em **`Restarting (1) X seconds ago`** (outros runners do mesmo host estão UP). `docker logs gh-runner` revela:

```text
# Authentication
Http response code: NotFound from 'POST https://api.github.com/actions/runner-registration'
{"message":"Not Found","status":"404"}
An error occurred: Not configured. Run config.(sh/cmd) to configure the runner.
```

E o pior: você não consegue fazer um deploy pra rotacionar o token, porque o deploy precisa do runner. Catch-22 em produção.

**Causa**: `secrets.RUNNER_REGISTRATION_TOKEN` é uma **GH secret estática** consumida pelo workflow CD via `printf 'RUNNER_REGISTRATION_TOKEN=%s\n' "$TOK" >> infra/docker/.env`. Registration tokens expiram em ~1h (§5). Em regime estável, o setup funciona porque:

1. Compose detecta **no-diff** entre deploys (mesmo valor de env → não recria service `runner`).
2. Runner já registrado continua vivo entre deploys, mesmo com token vencido — o token só é consumido no `config.sh`, não na operação contínua.

**Quando o equilíbrio quebra**: qualquer evento que force re-registro do runner — host restart, network blip + ephemeral runner reciclando, OOM-killer, daemon restart, alguém apertou `docker compose down runner` — dispara `config.sh` com o token agora vencido → 404 → crashloop. A partir daí: deploy queue → sem runner → não roda → secret não rotaciona → deadlock.

**Diagnóstico — ladder canônico (3 segundos cada)**:

```bash
# 1. Há runner registrado?
gh api "/repos/${REPO}/actions/runners" --jq '.runners[] | {name, status, busy}'
# Vazio ou status:offline + busy:false → suspeite §7.

# 2. Outros runners no host estão UP? (isola problema do runner específico)
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -i runner

# 3. Logs do runner que deveria estar online
docker logs --tail 30 gh-runner 2>&1 | grep -E 'Http response|Not Found|expired|Configuring'
# `404 Not Found em /actions/runner-registration` confirma token vencido.
```

**Recovery sem perder o slot do CD em curso** — sequência de **3 passos coordenados**:

```bash
REPO=JRC-Brasil/<repo>
COMPOSE_HOST=/tmp/cd-bootstrap/docker     # diretório de bring-up no host
PROJECT=<seu-compose-project>             # ex.: jrc-prod, deve bater com o do CD

# (a) Token novo + ATUALIZAR a GH secret com o MESMO valor que vai pro .env local.
# Sem esse match, próximo `compose up` no deploy detecta diff → recria runner
# mid-job → mata o próprio job que estava recriando.
TOK=$(gh api -X POST "/repos/${REPO}/actions/runners/registration-token" --jq '.token')
echo "$TOK" | gh secret set RUNNER_REGISTRATION_TOKEN --repo "$REPO" --env production
echo "$TOK" | gh secret set RUNNER_REGISTRATION_TOKEN --repo "$REPO"  # repo-level fallback

# (b) Apagar registro fantasma no GH ANTES de re-registrar (§6).
#     PULE este passo se `gh api runners` veio VAZIO — o ephemeral já se
#     desregistrou e não há fantasma; só faz sentido se houver entrada `offline`.
EXISTING=$(gh api "/repos/${REPO}/actions/runners" \
  --jq '.runners[]? | select(.name=="<runner-name>") | .id')
[ -n "$EXISTING" ] && gh api -X DELETE "/repos/${REPO}/actions/runners/${EXISTING}"

# (c) Subir runner via COMPOSE — não `docker run` direto.
# `docker run` cria container sem labels do compose project; próximo CD `up -d`
# bate em "Container gh-runner Conflict: name already in use" e falha.
# `-p $PROJECT` adota o compose project existente; `--no-deps` isola só o runner.
ssh host "mkdir -p $COMPOSE_HOST"
rsync -az infra/docker/ host:$COMPOSE_HOST/
ssh host "docker stop gh-runner 2>/dev/null; docker rm gh-runner 2>/dev/null
  cat > $COMPOSE_HOST/.env <<EOF
RUNNER_REGISTRATION_TOKEN=$TOK
EOF
  chmod 600 $COMPOSE_HOST/.env
  cd $COMPOSE_HOST
  docker compose -p $PROJECT -f docker-compose.prod.yml --env-file .env \
    up -d --build --no-deps runner
  sleep 8 && docker logs --tail 10 gh-runner | grep -E 'Listening|Settings Saved'"

# Confirmar labels do compose batem com as do CD:
ssh host "docker inspect gh-runner --format \
  '{{index .Config.Labels \"com.docker.compose.project\"}} :: {{index .Config.Labels \"com.docker.compose.service\"}}'"
# Esperado: <PROJECT> :: runner

# Re-trigger o deploy stuck:
gh run rerun <run-id> --failed
```

Após (c), o próximo `docker compose up -d` do CD vê o runner **com labels corretas E mesma RUNNER_TOKEN do .env** → no-diff → não recria → job sobrevive.

**Por que só "passos (a)+(c)" não bastam**: se você atualizar o secret mas trazer o runner via `docker run`, faltam labels compose; se trouxer via compose mas com token diferente do secret, no próximo deploy o `compose up` recria. O match-de-token + labels-de-compose é o que evita o segundo round de chicken-and-egg.

> **⚠️ Este recovery é STOPGAP, não cura — e por isso RECORRE.** Enquanto a
> credencial do runner for um *registration token* (vence ~1h), todo re-registro
> futuro repete o 404. Dois enganos que NÃO resolvem:
> - **`EPHEMERAL: "false"`** (tornar o runner "reutilizável/persistente") **não
>   previne** o crashloop: se o entrypoint custom limpa `.runner` e re-registra a
>   cada start (§3), QUALQUER restart do container dispara `config.sh` com o token
>   vencido. Visto recorrer com `RestartCount` em milhares mesmo com `EPHEMERAL:false`.
> - **Re-rotacionar o token** compra só mais ~1h. Para parar de vez → migre para
>   ACCESS_TOKEN (logo abaixo).
>
> **Antes do recovery, calibre 2 coisas no SEU pipeline:**
> - **`gh api runners` veio vazio?** O runner ephemeral já se desregistrou por
>   inteiro — então **não há fantasma** a deletar; pule o passo (b). A lista só
>   traz uma entrada `offline` se o runner morreu sem desregistrar.
> - **O job `deploy` faz `compose up` do service `runner`?** Se o `up`/`pull` do
>   CD é ESCOPADO aos services de imagem (`up -d frontend backend postgres`) e
>   NÃO toca o runner, então o trap "recriar runner mid-job" não existe e o
>   match secret↔.env do passo (a) é **IRRELEVANTE** — o runner roda de um `.env`
>   **PERSISTENTE do operador** (ex.: `/opt/<proj>/infra/staging/.env`), SEPARADO
>   do `.env` efêmero que o CD gera no workspace e apaga ao fim (logo: rotacionar a
>   GH secret NÃO conserta o runner vivo). Nesse caso o recovery é só: editar a
>   linha do token no `.env` persistente do host + `compose -p <proj> up -d
>   --no-deps --force-recreate runner`.

### Migração ACCESS_TOKEN in-place — o fix durável (recomendado)

Mantém o `runner` no compose do produto (não precisa centralizá-lo); só troca a
credencial de *registration token* (expira ~1h) por um **PAT**, que a imagem
`myoung34` usa para gerar um registration token FRESCO a cada start. O JIT
ephemeral passa a re-registrar limpo e o §7 deixa de acontecer. Provado no
staging do `sales_quote` (2026-06): `docker restart` re-registra sem 404.

**1. Criar o PAT — `gh` NÃO cunha PAT.** Não existe endpoint de API/CLI para
criar Personal Access Token (clássico ou fine-grained); só a **web UI**
(`github.com/settings/tokens`). As únicas credenciais que o `gh` produz sozinho
são: (a) o próprio token OAuth do login — `gh auth token` — que serve como
`ACCESS_TOKEN` SE tiver escopo `repo`, mas **acopla o runner ao login do operador**
(re-auth/revoke quebra o runner) e é mais amplo (`workflow`/`gist`/`read:org`)
num host com `docker.sock`=root → use só como **stopgap**; e (b) um registration
token (vence 1h — é o próprio problema). Durabilidade real = **PAT dedicado**
(clássico escopo `repo`, ou fine-grained 1-repo com `Administration: R/W`).

**2. Compose** — trocar a credencial e fixar o escopo:

```yaml
runner:
  environment:
    RUNNER_SCOPE: repo                      # exigido p/ ACCESS_TOKEN gerar token via API
    ACCESS_TOKEN: ${RUNNER_ACCESS_TOKEN:-}  # PAT; o default vazio `:-` é CRÍTICO
    # ...sem RUNNER_TOKEN...
```

O `:-` (default vazio) evita que comandos `docker compose` do CD — que parseiam
o arquivo inteiro mas NÃO sobem o runner (deploy escopado) — falhem por var
não-setada.

**3. Entrypoint custom** — se ele EXIGE `RUNNER_TOKEN` (`: "${RUNNER_TOKEN:?}"`
sob `set -u`), o modelo ACCESS_TOKEN quebra cedo. Aceite QUALQUER das duas:

```bash
if [[ -z "${ACCESS_TOKEN:-}" && -z "${RUNNER_TOKEN:-}" ]]; then
  echo "defina ACCESS_TOKEN (PAT, durável) ou RUNNER_TOKEN (registration, 1h)" >&2
  exit 1
fi
```

**4. Onde vive o PAT** — SÓ no `.env` PERSISTENTE do host do runner; **nunca**
como GH secret nem no `.env` que o CD gera (se o deploy não sobe o runner, ele
não precisa da credencial). Remova o `RUNNER_REGISTRATION_TOKEN` morto do step
"Gerar .env" do CD.

**5. Cutover + validação**:

```bash
# (a) valida o PAT ANTES de recriar — se gera registration token, o escopo está OK:
GH_TOKEN=<PAT> gh api -X POST "/repos/${REPO}/actions/runners/registration-token" --jq .token >/dev/null && echo "PAT OK"
# (b) grava no .env persistente do host (token via stdin → fora de `ps`/sshd args):
printf 'RUNNER_ACCESS_TOKEN=%s\n' "$PAT" | ssh host '
  ENVF=/opt/<proj>/infra/staging/.env; L=$(cat)
  grep -vE "^(RUNNER_ACCESS_TOKEN|RUNNER_REGISTRATION_TOKEN)=" "$ENVF" > "$ENVF.tmp" || true
  printf "%s\n" "$L" >> "$ENVF.tmp"; mv "$ENVF.tmp" "$ENVF"; chmod 600 "$ENVF"'
# (c) rebuild+recria SÓ o runner (entrypoint mudou → precisa de --build):
ssh host 'cd /opt/<proj>/infra/staging && docker compose -p <proj> up -d --build --no-deps --force-recreate runner'
# (d) PROVA de durabilidade — reinicie e confirme re-registro limpo (sem 404):
ssh host 'docker restart <runner>; sleep 14; docker logs --tail 8 <runner> | grep -E "Listening|404"'
# Esperado: "Listening for Jobs"; RestartCount sobe mas fica online — antes daria 404.
```

O passo (d) é o que **prova** que a migração curou de fato (vs só afirmar) —
ele reproduz exatamente o evento (restart) que antes levava ao crashloop.

**Outras variantes do fix permanente** (quando a migração in-place não encaixa —
ex.: você quer o runner FORA do compose do produto, ou um token a quente por deploy):

1. **Token gerado a quente no workflow**. No `cd-production.yml`, substituir o consumo de `secrets.RUNNER_REGISTRATION_TOKEN` por:

   ```yaml
   - name: Gerar registration token fresco
     env:
       GH_TOKEN: ${{ secrets.RUNNER_PROVISIONING_PAT }}  # PAT com escopo `repo`
     run: |
       TOK=$(gh api -X POST \
         "/repos/${{ github.repository }}/actions/runners/registration-token" \
         --jq '.token')
       printf 'RUNNER_REGISTRATION_TOKEN=%s\n' "$TOK" >> infra/docker/.env
   ```

   Cada deploy gera token novo. `compose up` SEMPRE vai detectar diff e recriar o `runner` service — o que mata o job em execução. Mitigação: `docker compose up -d --no-recreate runner` no comando do deploy, ou mover o `up` do runner pra **outro job** que roda em `ubuntu-latest` (sem self-hosted) e SSH no host.

2. **Migrar pro compose centralizado de runners com PAT** (modelo `myoung34` puro). Em `/home/<user>/runners/infra/runners/docker-compose.yml`, declarar service com `ACCESS_TOKEN: ${ACCESS_TOKEN}` (PAT) em vez de `RUNNER_TOKEN`. A imagem regenera registration tokens dinamicamente. Não há mais `runner` service no compose do produto — runner é infra do host, não da aplicação. CD perde a capacidade de rebuild do runner via deploy, mas ganha estabilidade de semanas (e elimina o secret expirável). É o modelo que outros 4+ runners JRC usam estavelmente.

Pra rodar uma análise comparativa antes de decidir:

```bash
# Quantos runners você tem nesse host?
docker ps --format '{{.Names}}\t{{.Status}}' | grep -i runner
# Se a maioria já usa myoung34 com ACCESS_TOKEN → migrar é alinhamento;
# se é só esse runner → token-quente no workflow tem menos blast radius.
```

## §8. Binário do runner deprecado → "cannot receive messages" (crashloop independente do token)

**Sintoma**: deploy `queued` para sempre; no host, `docker ps` mostra o runner **`Up <segundos>` mas com `RestartCount` na casa dos milhares** (o tell de crashloop — não está "down", está ciclando). `docker logs` revela:

```text
√ Connected to GitHub
Current runner version: '2.333.0'
2026-xx-xx: Listening for Jobs
An error occurred: Runner version v2.333.0 is deprecated and cannot receive messages.
```

O runner **registra e conecta com sucesso** (não é problema de token nem de registro), chega a "Listening for Jobs", e então o GitHub **recusa entregar jobs** porque a versão do binário foi deprecada → o agente sai → o container reinicia → loop. No GitHub o `status` pode piscar entre `online`/`offline` conforme cicla.

**Causa**: a imagem (tipicamente `myoung34/github-runner:latest`) foi baixada **uma vez** e nunca re-puxada, **e** `DISABLE_AUTO_UPDATE` está ligado — então o binário não se auto-atualiza e apodrece. O GitHub deprecia versões antigas do runner periodicamente e passa a recusá-las. É o pior-dos-dois: nem refresh de imagem, nem auto-update do binário. (Provável gatilho de origem do offline que depois leva ao §9.)

> **Isolation key — §8 vs §7 vs §9**: os três dão "deploy queued + runner crashloop", mas o log os separa em 3 segundos:
> - `404 .../actions/runner-registration` + `Not configured` → **§7** (registration token vencido).
> - `registration has been deleted from the server` → **§9** (config stale reaproveitada).
> - `Runner version vX is deprecated and cannot receive messages` → **§8** (binário velho). Conectou e listou jobs antes de morrer — prova que credencial/registro estão OK.

**Fix imediato** (no host, no diretório do compose):

```bash
docker compose pull                       # imagem fresca = binário de runner atual
docker compose up -d --force-recreate
sleep 14
docker logs --tail 10 <runner> | grep -E 'Current runner version|Listening for Jobs|deprecated'
# Esperado: versão nova, "Listening for Jobs", SEM "deprecated". RestartCount volta a 0.
```

**Fix durável — ligar o auto-update (recomendado)**. Ver §8a. Com auto-update o binário se atualiza em runtime e o §8 deixa de recorrer; `docker compose pull` periódico vira só cinto-e-suspensório.

### §8a. `DISABLE_AUTO_UPDATE` é footgun: qualquer valor não-vazio (até `"0"`) desliga

O entrypoint do `myoung34` faz `[ -n "${DISABLE_AUTO_UPDATE}" ]` → **qualquer string não-vazia ativa o `--disableupdate`**, inclusive `"0"` e `"false"`. Para **LIGAR** o auto-update é preciso **REMOVER a variável** do compose, não setá-la como `"0"`:

```yaml
runner:
  environment:
    ACCESS_TOKEN: ${RUNNER_ACCESS_TOKEN:-}
    # NÃO definir DISABLE_AUTO_UPDATE — presença de QUALQUER valor desliga o auto-update.
    # Sem a var, o binário se auto-atualiza quando o GitHub exige (evita o §8).
```

Aplicar exige recriar o container (a env é lida no start): `docker compose up -d --force-recreate <runner>`. Confirmar que sumiu de fato: `docker exec <runner> printenv DISABLE_AUTO_UPDATE` deve **não** retornar nada.

> **Corolário — caveat à lição 45 (pin por digest)**: pinar a imagem do **runner** por digest é **contraproducente sem cadência de bump**. A lição 45 vale para `node`/`nginx`/`postgres` (imutabilidade desejável), mas o GitHub **força currency de versão** do runner — um digest congelado garante que, em 1–2 meses, a versão fica deprecada e cai no §8. Para o runner, escolha conscientemente: (a) `:latest` + auto-update ligado (sempre atual, menos reproduzível), OU (b) pin por digest + **cron/rotina mensal de `docker compose pull`**. Não pine sem o (b).

## §9. Config-reuse ressuscita credencial morta após o GitHub apagar o registro

**Sintoma**: `RestartCount` alto; `docker logs` repete:

```text
Failed to create a session. The runner registration has been deleted from the server,
please re-configure. Runner registrations are automatically deleted for runners that
have not connected to the service recently.
...
Runner reusage is enabled / The runner has already been configured /
Reusage is enabled. Storing data to /home/runner/config/<repo>
```

**Causa**: o GitHub **apaga o registro server-side** de runners offline por tempo demais (semanas). Com `CONFIGURED_ACTIONS_RUNNER_FILES_DIR` apontando para um **named volume** (reuso de config ligado), o entrypoint encontra o `.runner`/`.credentials` persistidos, decide "já está configurado" e **reaproveita a credencial morta** em vez de re-registrar com o PAT → a sessão falha → crashloop.

**Distinto do §6**: o §6 é conflito de **nome** ao tentar re-registrar (precisa `DELETE` no GitHub antes). O §9 é o oposto — o runner **nem tenta** re-registrar porque o reuso o convence de que está configurado; o registro já sumiu do lado do GitHub (nada a deletar). Fix é **limpar o estado local**, não o remoto:

```bash
docker compose down
docker volume rm <project>_<config-volume>     # ex.: louvorflow-runners_runner-config-louvorflow
docker compose up -d                            # config.sh fresco → re-registra via ACCESS_TOKEN
```

> **ACCESS_TOKEN não é imune (nuance à lição 46)**: migrar para `ACCESS_TOKEN` (PAT) cura o **§7** (expiry de registration token), mas **não** o §8 (binário velho) nem o §9 (config stale reaproveitada) — são modos ortogonais ao modelo de credencial. Um runner em ACCESS_TOKEN ainda crashloopa por versão deprecada e por config morta reaproveitada. Não assuma que ACCESS_TOKEN = à prova de balas.

## Sintomas → seção

| Sintoma | Vai para |
|---------|----------|
| Loop com exit 0 logo após "Settings Saved" | §1 (CMD) |
| Runner online no GH com label `default` | §2 (LABELS env) |
| "Cannot configure the runner because it is already configured" | §3 (state cleanup) |
| Build falha em `gpg --dearmor` / `cannot open '/dev/tty'` | §4 (use .asc direto) |
| Token consumido / "registration token has expired" | §5 (regenerar imediato) |
| "A runner exists with the same name" / labels antigas mantidas | §6 (DELETE no GH antes) |
| Deploy queued forever + `gh-runner` Restarting + log com `404 /actions/runner-registration` | §7 (chicken-and-egg) |
| Após recovery manual, `compose up` falha com `Container gh-runner Conflict: name already in use` | §7 (use `compose -p <project> up`, não `docker run`) |
| O §7 já recorreu / quero parar de vez (o recovery não cura) | §7 → Migração ACCESS_TOKEN in-place |
| `EPHEMERAL:false` não impediu o crashloop de token | §7 (não é mitigação — entrypoint re-registra a cada start; migre p/ ACCESS_TOKEN) |
| "É a primeira vez que `gh` não cria meu PAT?" / automatizar criação de PAT | §7 → in-place (PAT é só web UI; `gh auth token` serve de stopgap) |
| `Runner version vX is deprecated and cannot receive messages` (conectou e listou jobs antes de morrer) | §8 (binário velho — `compose pull` + ligar auto-update) |
| Liguei `DISABLE_AUTO_UPDATE: "0"` esperando ATIVAR o auto-update e não ativou | §8a (qualquer valor não-vazio desliga — REMOVER a var) |
| Pinei o runner por digest e meses depois caiu em crashloop de versão | §8a (caveat à lição 45 — runner precisa de currency; `:latest`+auto-update ou pin+bump mensal) |
| `Failed to create a session. The runner registration has been deleted from the server` | §9 (config stale reaproveitada — `docker volume rm <config-volume>`) |
