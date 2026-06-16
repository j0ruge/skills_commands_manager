# Changelog — cicd (Unificada)

Formato: [Semantic Versioning](https://semver.org/)

## [2.16.0] - 2026-06-15

### Adicionado

- **`references/self-hosted-runner-docker.md` §8 — "Binário do runner deprecado →
  cannot receive messages"** (novo modo de falha). Motivação: incidente no
  `LouvorFlow` (staging) — deploy `queued`, runner em crashloop com
  `RestartCount=50296`, log `Runner version v2.333.0 is deprecated and cannot receive
  messages`. O runner **registrava, conectava e listava jobs** (token/registro OK), e
  só então o GitHub recusava entregar trabalho porque o binário fora deprecado. O skill
  não cobria isso — só §7 (token) e o cenário de "registration deleted". Causa: imagem
  `:latest` baixada uma vez e nunca re-puxada + `DISABLE_AUTO_UPDATE` ligado → binário
  apodrece. Fix imediato `docker compose pull` + recreate; durável = ligar auto-update.
- **§8a — footgun do `DISABLE_AUTO_UPDATE`**: o entrypoint do `myoung34` faz
  `[ -n "${DISABLE_AUTO_UPDATE}" ]`, então **qualquer valor não-vazio (até `"0"`/`"false"`)
  DESLIGA** o auto-update. Para LIGAR é preciso **remover a variável**. Incluído o
  comando de verificação (`docker exec <runner> printenv DISABLE_AUTO_UPDATE`).
- **Caveat à lição 45 (pin por digest)**: pinar a imagem do **runner** por digest é
  contraproducente sem cadência de bump — o GitHub força currency de versão e a versão
  congelada deprecia em ~1–2 meses (cai no §8). Escolha consciente: `:latest`+auto-update
  OU pin+`docker compose pull` mensal.
- **§9 — config-reuse ressuscita credencial morta**: log `Failed to create a session.
  The runner registration has been deleted from the server`. Distinto do §6 (conflito
  de nome ao re-registrar): aqui o reuso de config (`CONFIGURED_ACTIONS_RUNNER_FILES_DIR`
  + named volume) convence o entrypoint de que "já está configurado" e ele reaproveita o
  `.runner` morto. Fix: `docker volume rm <project>_<config-volume>` (limpa estado LOCAL).
- **Nuance à lição 46**: `ACCESS_TOKEN` cura SÓ o §7 (expiry de token) — **não imuniza**
  contra §8 (binário velho) nem §9 (config stale), que são ortogonais ao modelo de
  credencial. Adicionadas linhas no Quick Troubleshooting, lições 47/48/49, e a
  "isolation key" pelos 3 logs (`404 registration`=§7, `registration deleted`=§9,
  `version deprecated`=§8).

## [2.15.0] - 2026-06-15

### Adicionado

- **`references/self-hosted-runner-docker.md` §7 — "Migração ACCESS_TOKEN in-place"**
  (novo recipe, o fix DURÁVEL). Motivação: o §7 (chicken-and-egg do registration
  token estático) **recorreu** no `sales_quote` ("não é a primeira vez") porque o
  skill documentava a migração ACCESS_TOKEN só como opção teórica ("compose
  centralizado"), enquanto o recovery que se usa no incidente é só rotação de token
  — que **não é cura**. Agora há recipe in-place completo: mantém o `runner` no
  compose do produto e troca `RUNNER_TOKEN: ${...}` → `ACCESS_TOKEN:
  ${RUNNER_ACCESS_TOKEN:-}` + `RUNNER_SCOPE: repo`; entrypoint custom passa a
  aceitar `ACCESS_TOKEN` OU `RUNNER_TOKEN`; PAT vive só no `.env` persistente do
  host (nunca GH secret nem no `.env` efêmero do CD); validar o PAT antes de
  recriar e provar a cura com `docker restart` (re-registra sem 404).
- **Callout "STOPGAP, não cura"** antes do "Fix permanente" no §7, com 2 enganos
  comuns desmascarados: (1) **`EPHEMERAL:false` NÃO previne** o crashloop — o
  entrypoint limpa `.runner` e re-registra a cada start, então qualquer restart
  bate no token vencido (visto com RestartCount em milhares); (2) re-rotacionar o
  token compra só ~1h.
- **Calibração pré-recovery** no §7: `gh api runners` vazio ⇒ ephemeral já se
  desregistrou, **sem fantasma** a deletar (passo (b) condicional); e se o job
  `deploy` faz `up`/`pull` ESCOPADO (sem o `runner`), o match secret↔.env é
  irrelevante — o runner roda do `.env` **persistente do operador**, separado do
  `.env` efêmero que o CD gera e apaga (rotacionar a GH secret não conserta o
  runner vivo).
- **Fato operacional**: `gh` **NÃO cunha PAT** (não há API/CLI — só web UI); a
  única credencial gh-only é o token OAuth do login (`gh auth token`, escopo
  `repo`) como **stopgap**, com tradeoff de acoplamento ao login + escopo amplo
  num host com `docker.sock`=root.
- **`SKILL.md`** — lição **46** (§7 recorre / fix durável = ACCESS_TOKEN in-place /
  `gh` não cunha PAT); nova row na Quick Troubleshooting ("deploy queued de novo");
  3 keywords de trigger.

### Por quê

Fechar o loop de recorrência: transformar a migração ACCESS_TOKEN de "opção
mencionada" em recipe executável e marcar explicitamente que o recovery e o
toggling de `EPHEMERAL` são paliativos. Provado no staging do `sales_quote`
(2026-06-15): cutover + `docker restart` re-registrando sem 404.

## [2.14.0] - 2026-06-13

### Adicionado

- **Lessons Learned 41–45 (`SKILL.md`)** — 5 lições do hardening pós code-review da
  feature 017 do `sales_quote` (continuação das 37–40), ausentes da skill:
  - **41 `[S]`** — wrapper como PID 1 no container (`npx tsx …`/`npm start`) não
    repassa SIGTERM → SIGKILL após o grace period, sem shutdown gracioso. Fix:
    `init: true` no compose (ou `tini` no ENTRYPOINT). Cousin de runtime da lesson 37.
  - **42 `[B]`** — corolário da 37: mover `tsx`+`prisma` p/ `dependencies` deixa o
    estágio runtime usar `npm ci --omit=dev` e tirar vitest/testcontainers/supertest
    da imagem, sem quebrar boot/migrate.
  - **43 `[S]`** — CI gate duplicado entre `ci.yml` e o re-gate de `cd-staging.yml`
    → extrair `.github/actions/<gate>/action.yml` (composite). Pegadinhas: checkout
    fica no job chamador; `shell:` obrigatório nos `run:`; nomes de job são contrato.
  - **44 `[S]`** — CI só com trigger `pull_request` deixa push direto a branch
    protegido escapar do gate. Fix: trigger `push:` + branch protection com required
    checks.
  - **45 `[S]`** — descobrir o digest p/ pinar imagem base sem pull cheio:
    `docker buildx imagetools inspect <img> | grep Digest`; aplicar a node/nginx/
    postgres, não só ao runner.
- **`SKILL.md` Quick Troubleshooting** — 2 rows novas (SIGKILL pós grace por wrapper
  PID 1; código entrou sem rodar CI por push direto).
- **`references/cd-pipeline-pitfalls.md` §8** — wrapper PID 1 / SIGTERM / `init: true`.
- **`references/troubleshooting-backend.md`** — corolário "enxugar a imagem
  `tsx`-runtime com `--omit=dev`" (mover tsx/prisma p/ deps + verificação no build).
- **`references/troubleshooting-shared.md` §11** — composite action p/ DRY do CI gate
  (4 pegadinhas: checkout no chamador, `shell:` obrigatório, nomes de job
  contratuais, validar com actionlint).
- **`references/checklist-shared.md` §6** — CI gating: branch protection vs trigger
  `push:` (defesa em profundidade contra push direto).
- **`references/self-hosted-runner-docker.md`** — nota de como descobrir o `@sha256:`
  via `docker buildx imagetools inspect`, generalizada às imagens do app.
- **`SKILL.md` description + `plugin.json` + `marketplace.json`**: bump 2.13.0 →
  2.14.0 + keywords compactas (sem inchar a prose — a description já estava acima do
  alvo enxuto, mesmo critério da 2.13.0).

### Por que minor (não patch)

Só adições (5 lições + §8 + §11 + §6 + 1 corolário + 1 nota). Nenhuma regressão para
consumidores existentes.

## [2.13.0] - 2026-06-12

### Adicionado

- **Lessons Learned 37–40 (`SKILL.md`)** — 4 armadilhas de monorepo npm-workspaces
  descobertas no `sales_quote` (feature 017), ausentes da skill:
  - **37 `[B]`** — backend roda via `tsx`, não `node dist/`, quando os workspaces shared
    exportam TS source (`main: ./src/index.ts`): o `dist` compilado morre com
    `ERR_MODULE_NOT_FOUND`/`ERR_UNKNOWN_FILE_EXTENSION` no `.ts` do sibling. Não repontar
    `exports` p/ `dist` (quebra o Vite do frontend).
  - **38 `[F]`** — `tsc --noEmit` é VAZIO em `tsconfig.json` com project references
    (`files: []`), checa zero arquivos → gate de CI falso; usar `tsc -b --noEmit`.
  - **39 `[B]`** — workspace importa sibling não declarado (só hoist) → `npm ci -w` escopado
    quebra no Docker; usar `npm ci` cheio no builder descartado.
  - **40 `[S]`** — `USER node` + named volume novo = `EACCES`; `mkdir`+`chown` na imagem
    antes do `USER` (volume herda ownership do path).
- **`SKILL.md` Quick Troubleshooting** — 3 rows com sintomas verbatim (`ERR_MODULE_NOT_FOUND`
  em `node dist`, typecheck verde-fake, `EACCES` em named volume).
- **`references/troubleshooting-backend.md`** — seção "Monorepo npm workspaces — armadilhas
  de build/runtime na imagem" (tsx-runtime com snippet Dockerfile + sibling não declarado +
  volume ownership).
- **`references/troubleshooting-frontend.md`** — cenário 9 "CI typecheck passa verde mas erros
  de tipo escapam" (project references + corolário do backlog latente + churn de `*.tsbuildinfo`).
- **`references/cd-pipeline-pitfalls.md` §1b** — a contrapartida do build-time baking: injetar
  um secret de RUNTIME no nginx do frontend via templates/`envsubst` da imagem oficial (sem
  custom entrypoint; `$uri`/`$host` sobrevivem; grep de prova de que o token não está no bundle).
- **`SKILL.md` description + metadata.version**: bump 2.12.0 → 2.13.0 + trigger keywords
  compactas (sem inchar a prose — a description já estava acima do alvo enxuto).
- **`plugin.json`**: bump 2.12.0 → 2.13.0 + keywords novas (`tsx-runtime-monorepo`,
  `node-dist-esm-resolution`, `tsc-b-project-references`, `vacuous-typecheck`,
  `named-volume-ownership`, `nginx-envsubst-runtime-token`).
- **`marketplace.json`**: bump idem.

### Por que minor (não patch)

Só adições (4 lições + 1 seção nova + 1 cenário + §1b). Nenhuma regressão para consumidores
de 2.12.0.

## [2.12.0] - 2026-05-13

### Adicionado

- **`troubleshooting-shared.md` §1a (novo, ~110 linhas) — "`TLS handshake timeout` on GHCR (Self-Hosted Runner)"**: nova classe documentada de falha em `docker login ghcr.io` que é **frequentemente confundida com §1 (`unauthorized`)** mas tem causa raiz oposta. `unauthorized` = TLS completou + GHCR rejeitou credencial (fix: rotacionar PAT). `TLS handshake timeout` = TCP conectou mas handshake nem completou — credencial é irrelevante porque a conexão nem chegou nessa etapa. Cobre:
  - **Distinção operacional vs §1**: cross-link bidirecional entre as duas seções pra forçar o leitor a confirmar qual sintoma realmente bateu.
  - **Isolation key**: workflow típico tem `ci` + `build-and-push` em `ubuntu-latest` e `deploy` em `self-hosted`. Se só o deploy falha, GHCR está saudável — problema é a rede outbound do host runner. Essa assimetria sozinha já elimina causas "GitHub está fora" e foca o diagnóstico no host.
  - **4 causas ranqueadas por probabilidade**: (1) **MTU mismatch** em VPN/overlay drop dos frames de Certificate/CertificateVerify (mais comum); (2) firewall corporativo com TLS inspection lento/incompleto; (3) flake transiente do ghcr.io (raro); (4) Docker daemon com iptables legacy em kernel mais novo.
  - **5 comandos de diagnóstico SSH-na-máquina**: `curl --max-time 15 https://ghcr.io/v2/`, `docker logout && docker login` (reproduz fora do workflow), `ip link show | grep mtu`, `traceroute -T -p 443 ghcr.io`, `env | grep proxy` + `cat /etc/docker/daemon.json`.
  - **Fix A — bash retry wrapper (recomendado, defesa em profundidade)**: snippet completo de step YAML que substitui `docker/login-action@v3` por loop bash com 3 tentativas e backoff 10s/20s. Aplicado apenas no deploy job — build-and-push em ubuntu-latest continua usando a action. Inclui justificativa pra não usar `nick-fields/retry@v3` (overhead pra step única; 20 linhas de bash com `--password-stdin` mantêm a credencial sem hops extras).
  - **Fix B — Docker daemon MTU=1400 (root cause)**: snippet `/etc/docker/daemon.json` + restart. Valor conservador que cobre maioria dos VPN/cloud overlays.
  - **Fix C — proxy explícito**: systemd drop-in pra Docker daemon quando o host está atrás de proxy corporativo com TLS inspection (proxies explícitos tipicamente lidam melhor que intercept transparente).
  - **Árvore de decisão final**: intermitente → Fix A; 100% reproduzível + MTU mismatch confirmado → Fix B; proxy detectado → Fix C.
- **`SKILL.md` Quick Troubleshooting**: row novo `[S]` cobrindo "TLS handshake timeout on docker login" com a isolation key (build OK / deploy fail) e ponteiro pra §1a.
- **`SKILL.md` Lessons Learned**: row #36 condensando o pattern — "GHCR TLS handshake timeout vs unauthorized — não são o mesmo bug".
- **`SKILL.md` description + metadata.version**: bump 2.11.0 → 2.12.0 + descrição estendida + triggers novos (`GHCR TLS handshake timeout`, `docker login retry`, `MTU mismatch`, `TLS inspection proxy`).
- **`plugin.json`**: bump 2.11.0 → 2.12.0 + description estendida + keywords novas (`tls-handshake-timeout`, `docker-login-retry`, `mtu-mismatch`, `tls-inspection-proxy`).
- **`marketplace.json`**: bump idem + description estendida.

### Motivação

Deploy do LouvorFlow CD-staging-backend (2026-05-13) falhou no step `Logging into ghcr.io` do job `deploy` (self-hosted) com `Error: Error response from daemon: Get "https://ghcr.io/v2/": net/http: TLS handshake timeout`. O instinto inicial foi conferir credenciais — porque a seção de GHCR existente na skill só cobria `unauthorized`. Mas TCP conectava (senão seria "dial tcp") e build-and-push em ubuntu-latest passava no mesmo run, isolando a falha no host do runner staging. Custou tempo pra reconhecer que era network-layer (MTU/firewall) e não credencial.

O pattern generaliza: qualquer self-hosted runner em VPN, cloud overlay, ou rede corporativa com TLS inspection eventualmente bate nesse erro, e a skill antes não diferenciava os dois sintomas do GHCR. Codificar a distinção + a isolation key (build OK / deploy fail) + os dois fixes canônicos (retry wrapper imediato, MTU 1400 como root cause) economiza ~30min de investigação errada por incidente. Bonus: o retry wrapper em bash puro elimina a dependência de uma action de terceiros pra um problema cuja solução cabe em 20 linhas, e fica idempotente entre re-runs.

## [2.10.0] - 2026-05-08

### Adicionado

- **`cd-pipeline-pitfalls.md` §5 (novo, ~80 linhas) — "Container script writing output outside WORKDIR — soft-failure that hides forever"**: classe de bug em CD onde um script bake'd no container (Node, Python, Bash) resolve um output path relativo ao próprio `__dirname`/`__file__`/`$(dirname "$0")` que **caminha pra cima na árvore de fontes** (ex.: `__dirname/../../../infra/docker/.../bootstrap.json`). Em dev (host com source tree completo) o path existe e o write funciona; em prod (container com Dockerfile que só copia `packages/<self>/`) o path simplesmente não existe na imagem → `ENOENT` exit 1 **depois** de todas as operações lógicas terem sucesso. CD trata como soft-failure (`continue-on-error: true` + `::warning::`), stack permanece UP, MAS o yellow warning a cada deploy satura visualmente após 2-3 ciclos e operadores param de ler — qualquer warning genuinamente novo passa despercebido. Cobre:
  - **Sintoma canônico**: linha de log `[bootstrap] FALHOU: ENOENT: no such file or directory, open '/app/.../bootstrap.json'` seguida de `##[error]Process completed with exit code 1` e `##[warning]<step> falhou após retry — Stack permanece UP com config anterior`.
  - **Diagnóstico em 60s**: `grep -nE "writeFile|fs\.writeFile|outFile|to_csv|toFile" packages/<offending>/scripts/*.{ts,js,py}` → cruzar com `grep -nE "^COPY |^ADD " packages/<offending>/Dockerfile`. Diff = paths que o script grava E não estão sob nenhum COPY destination = bug.
  - **Fix canônico — best-effort wrap**: `try { writeFileSync(outFile, ...); console.log('OK → ' + outFile); } catch (err) { console.warn('OK (não persistiu summary: ...)'); } console.log(JSON.stringify(result, null, 2))` — em dev comportamento idêntico, em container warn-and-continue exit 0, e o JSON segue dumpado em stdout pra logs do CD capturarem.
  - **4 alternativas com tabela de trade-offs**: `/tmp/` writable, env-driven `process.env.OUTPUT_PATH`, volume bind-mount no compose (vira contrato de deployment), `Dockerfile COPY` da estrutura de pasta vazia (acopla imagem ao layout do source tree).
  - **Princípio sobre soft-failure persistente**: `::warning::` é o tool certo pra steps idempotentes que não devem bloquear deploy, mas se a step pinta yellow em **todo** deploy você já pagou o custo operacional — finishe o fix (best-effort wrap, `::notice::` em vez de `::warning::`, ou determinístico). Persistent yellow é pior que green porque condiciona operador a ignorar o único sinal que CI/CD tem pra "merece um glance".
- **`SKILL.md` Quick Troubleshooting**: row novo `[S]` mapeando "CD step emits yellow `::warning::` on every deploy + ENOENT in script that finished its real work first" → §5.
- **`SKILL.md` description**: append "container scripts writing output paths outside WORKDIR (`__dirname/../../...` ENOENT) being soft-failed forever as ambient yellow warnings" + triggers novos (`ENOENT bootstrap`, `soft-failure yellow warning fatigue`, `container script outside WORKDIR`).
- **`SKILL.md` metadata.version**: drift fix 2.8.0 → 2.10.0 (v2.9.0 não havia bumpado essa metadata).
- **`plugin.json`**: bump 2.9.0 → 2.10.0 + description estendida + keywords novas (`enoent-bootstrap`, `soft-failure-fatigue`, `yellow-warning`).
- **`marketplace.json`**: bump idem + description estendida.

### Motivação

Cutover prod do `validade_bateria_estoque` (2026-05-08): após o destrancar do CD via §7 chicken-and-egg recovery, o primeiro deploy bem-sucedido em ~19h destrancou também a visibilidade dos logs do step `idp-bootstrap` — que vinham falhando soft há semanas com `ENOENT '/app/infra/docker/zitadel/local/bootstrap.json'`. O bug existia desde a feature 005 mas o yellow warning passava despercebido em meio aos warnings legítimos de deprecation (Node.js 20 actions deprecated em todos os jobs). Análise do código revelou o pattern: `bootstrap-zitadel.ts:1099` resolve `outFile = resolve(__dirname, '../../../infra/docker/zitadel/local/bootstrap.json')` — em dev o source tree mounted tem o path, em prod o Dockerfile só copia `packages/idp/` então o path simplesmente não existe na imagem. Todas as operações Zitadel (org/project/app/roles/user/grants/label-policy/custom-texts) completavam ANTES do writeFile, então cada deploy aplicava as mudanças no IdP corretamente — só que falhava cosmeticamente no fim.

PR #10 do `validade_bateria_estoque` aplicou o fix canônico (try/catch best-effort + console.log dumpa o JSON). A lição generaliza além de bootstrap-de-IdP: qualquer script bake'd em container que escreve em path resolvido upward de `__dirname` cai nesse mesmo gotcha — `release-notes-emit`, `migration-summary`, `seed-data-export`, etc. A skill antes não codificava esse pattern, e o trap do soft-failure persistente (yellow warnings que viram ruído ambiente) é um meta-padrão operacional que vale destacar — o `::warning::` é o tool certo pra steps idempotentes, mas se acende em todo deploy o custo operacional já foi pago e o fix deve ser finalizado, não normalizado.

---

## [2.9.0] - 2026-05-07

### Adicionado

- **`self-hosted-runner-docker.md` §7 (novo, ~85 linhas) — "RUNNER_REGISTRATION_TOKEN como GitHub secret estática = chicken-and-egg armadilha"**: classe de falha em produção onde o secret estática consumida pelo workflow CD funciona em regime estável só por **coincidência arquitetural** (`docker compose up` detecta no-diff entre deploys e pula recriação do `runner` service). Qualquer evento que force re-registro — host restart, OOM-killer, network blip + ephemeral runner ciclando, daemon restart, `docker compose down runner` manual — dispara `config.sh` com o token agora vencido (registration tokens vivem ~1h, §5) → 404 em `/actions/runner-registration` → crashloop. A partir daí, deadlock: deploy precisa do runner, runner precisa do deploy pra rotacionar a secret. Cobre:
  - **Diagnóstico canônico** com 3 comandos (gh api `.../actions/runners` vazio/offline + `docker ps` com outros runners UP + `docker logs gh-runner` mostrando 404 `/actions/runner-registration`) — distingue rapidamente do caminho systemd (cuja resposta canônica era `systemctl status actions.runner.*`, irrelevante quando runner é container).
  - **Recovery em 3 passos coordenados que não óbvios**: (a) gerar token novo + atualizar GH secret com **mesmo valor** que vai pro `.env` local (sem o match, próximo `compose up` no deploy detecta diff → recria runner mid-job → mata o próprio job que estava recriando); (b) apagar registro fantasma no GH antes via `gh api -X DELETE` (§6 já cobre o "porquê" — sem isso `--replace` mantém labels antigas); (c) subir runner via `docker compose -p <project> -f <compose> --env-file .env up -d --build --no-deps runner` (NÃO `docker run` — sem labels do compose project, próximo CD `up -d` bate em "Container Conflict: name already in use" e falha; demonstrado no incidente).
  - **Por que (a)+(c) sozinhos não bastam**: docker-run sem compose labels conflita; compose com token diferente do secret recria runner. O match-de-token + labels-de-compose é o que evita o segundo round.
  - **Fix permanente** (2 alternativas, com tradeoffs): (1) token a quente no workflow via `gh api -X POST .../registration-token` usando PAT com escopo `repo` — cada deploy recria runner (precisa `--no-recreate runner` ou mover up do runner pra outro job em `ubuntu-latest`); (2) migrar pro compose centralizado de runners com `ACCESS_TOKEN` (PAT) — alinha com modelo `myoung34` puro, runner some do compose do produto, perde-se rebuild via deploy mas ganha-se estabilidade de semanas.
- **`self-hosted-runner-docker.md` "Sintomas → seção"**: 2 linhas novas — "Deploy queued forever + gh-runner Restarting + log com 404 /actions/runner-registration" → §7; "Após recovery manual, `compose up` falha com `Container gh-runner Conflict: name already in use`" → §7 (apontando pro uso correto de `compose -p <project>`).
- **`SKILL.md` Quick Troubleshooting**: row "Deploy queued indefinitely" enriquecida com bifurcação host-runner vs containerized — antes a solução só apontava `systemctl status actions.runner.*`, irrelevante quando runner é container; agora também cita `docker ps | grep runner` e referencia §7.
- **`SKILL.md` routing trigger pra `self-hosted-runner-docker.md`**: append explícito sobre §7 cobrir o cenário deadlock-em-prod com 3-passos de recovery e o fix permanente.
- **`SKILL.md` Lessons Learned**: novo item #35 (`[S]`) — "RUNNER_REGISTRATION_TOKEN estática é equilíbrio frágil — chicken-and-egg quando quebra".
- **plugin.json**: bump 2.7.0 → 2.9.0 (corrige drift do bump anterior 2.8.0 que não havia atualizado plugin.json) + description estendida com triggers de §7 + keyword nova `registration-token`, `chicken-and-egg`.
- **marketplace.json**: bump 2.8.0 → 2.9.0 + description estendida idem.

### Motivação

Cutover prod do `validade_bateria_estoque` (2026-05-07): após push do fix `useRefreshToken` no frontend (commit `d09ebe0`), CD travou. Diagnóstico inicial sugeriu seguir o caminho canônico ("self-hosted runner offline → `systemctl status`") — mas o runner é conteinerizado via `myoung34/github-runner`, então systemd não tem nada relevante. O `gh-runner` estava em `Restarting (1) 18 seconds ago`, com `docker logs` revelando `404 Not Found` em `POST /actions/runner-registration` ciclando a cada ~30s. Token de registro tinha expirado horas antes (provavelmente após algum evento de re-registro do ephemeral runner que não conseguimos identificar com certeza); secret no GH ficou estática desde o setup inicial.

Recovery foi não-óbvia em 2 frentes que valem ser codificadas: (1) `docker run` direto com token fresco trouxe o runner online E destravou o pickup da queue, mas o **próximo `docker compose up` do deploy bateu em "Container gh-runner Conflict"** porque meu container manual não tinha as labels do compose project `jrc-prod`; (2) bring-up via `docker compose -p jrc-prod -f .../docker-compose.prod.yml --env-file .env up -d --build --no-deps runner` resolveu, MAS só funciona se a GH secret também for atualizada com o mesmo valor — caso contrário o próximo deploy detecta diff e recria o runner mid-job.

A skill antes documentava (em §5) que registration tokens expiram em 1h, mas não articulava o equilíbrio sistêmico do uso como secret estática nem o cenário deadlock-em-prod com runbook de recovery. Operador caía em loop: tentava regenerar token localmente seguindo §5, mas o próximo deploy do CD ainda usava o secret velho do GH e recriava o runner. Documentar essa armadilha + recovery 3-passos foi a lição justificativa do bump minor — antes a skill levava a vários round-trips de tentativa-e-erro, agora cobre o cenário em uma seção dedicada.

---

## [2.8.0] - 2026-05-07

### Adicionado

- **`cd-pipeline-pitfalls.md` §4 (novo, ~80 linhas) — "compose run orphans + reverse-proxy upstream poisoning"**: classe inteira de pegadinha em que um container órfão de `docker compose run --rm` antigo (cujo `--rm` não disparou — CI cancelado, runner OOM, daemon restart, container crash em pre-stop) fica vivo herdando `VIRTUAL_HOST` do serviço. `docker-gen` (nginx-proxy) ou label discoverer (Traefik) o registra no upstream pool junto com o backend saudável. Round-robin manda ~50% das requests pra config stale (image SHA antigo, `AUTH_AUDIENCE` placeholder pré-bootstrap, etc.) → 401 inconsistente em produção, **mesmo com tokens comprovadamente válidos**. Cobre:
  - Três surpresas counter-intuitivas: (a) `--rm` não é à prova de bala; (b) `docker compose up -d --remove-orphans` NÃO remove `*-run-*` (são "mesmo serviço", suffix-hash; orphan policy só cobre serviços removidos do compose); (c) docker-gen registra QUALQUER container com VIRTUAL_HOST, sem distinguir long-running vs one-off.
  - **Diagnóstico canônico de 5 segundos**: 20 hits paralelos com mesmo token sabido válido → split de status codes (e.g., `13 200` + `7 401`) = upstream pool poisoned. Antes de mergulhar em jose/JWKS/aud/iss, rodar este check.
  - **Fix em duas frentes**: (a) `compose run --rm -e VIRTUAL_HOST= -e LETSENCRYPT_HOST= …` invisibiliza one-offs ao discoverer (mesmo se `--rm` falhar, órfão não entra no pool); (b) step pre-rolling em CD que `docker rm -f` em `*-run-*` cobre histórico de runs antigas.
  - Sintomas adjacentes: `docker run` ad-hoc reusando env-file do serviço; daemon restart durante CD deixando múltiplos `prisma migrate` em estados Created/Exited.
- **`cd-pipeline-pitfalls.md` §2 — append "runbook canonical path may not exist on disk"**: em deploys via self-hosted runner, o compose path real é o workspace do runner (`/runner/_work/<org>/<repo>/.../infra/docker/`), regenerado por CD run. Runbooks/ADRs frequentemente referenciam path aspiracional (`/opt/<org>/<project>`) da era de deploy manual que nunca foi criado. Operador SSH-debugging segue o runbook e leva "No such file or directory" — sistema não está quebrado, docs estão. Diagnóstico: `docker inspect <container> --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'`.
- **Tabela "Layer / Refreshed by / Stale until"** ganhou 2 linhas: `nginx-proxy/Traefik upstream pool` (refreshed quando offending container some) e `compose run one-off container` (refreshed por `--rm` no clean exit, indefinidamente se exit não é clean).
- **`SKILL.md` Quick Troubleshooting**: nova entrada `[S]` "~50% das requests autenticadas retornam 401 mesmo com JWT comprovadamente válido" → aponta pra `cd-pipeline-pitfalls.md §4`.
- **`SKILL.md` Lessons Learned**: novo item #34 (`[S]`) — "compose run orphan + nginx-proxy = upstream pool poisoning".
- **`SKILL.md` description**: 6 triggers novos no frontmatter (`intermittent 401`, `split status codes`, `upstream pool stale`, `compose run orphan`, `docker-gen VIRTUAL_HOST`, `runbook canonical path mismatch`).
- **`SKILL.md` routing trigger pra `cd-pipeline-pitfalls.md`**: expandido para mencionar §4 explicitamente, com diagnóstico canônico (20 hits paralelos = split = upstream pool poisoned).

### Motivação

Cutover prod do `validade_bateria_estoque` (feature 006, 2026-05-07): após declarar a feature fechada, usuários começaram a ver "Não foi possível carregar os indicadores: Token inválido" na SPA, em ~50% das chamadas ao backend. Diagnóstico inicial seguiu hipóteses naturais (aud claim mismatch, JWKS rotation, ZitadelClaimsMapper rejeitando token) — todas falsas. JWT decodificado batia perfeitamente: `aud` continha o projectId UUID correto, `iss` correto, `exp` no futuro, signature OK; replay externo via curl retornava 200 consistentemente.

A descoberta veio de hammering: 20 hits paralelos com o mesmo token retornaram 7×200 + 3×401, depois 14×200 + 6×401 — split round-robin. Inspeção do upstream do nginx-proxy revelou DOIS containers no pool de `erp.api.battery.jrcbrasil.com`: o `erp-backend` saudável e um órfão `jrc-prod-backend-run-3ed3a2e9cdb9` (sha-0cae6ba, 41h vivo desde uma execução de `compose run --rm backend npx prisma migrate deploy` em CD anterior cujo `--rm` não disparou). O órfão tinha `AUTH_AUDIENCE=PLACEHOLDER_BEFORE_FIRST_BOOTSTRAP` (default antes do primeiro bootstrap), rejeitando 100% dos tokens.

`docker rm -f` do órfão resolveu na hora; nginx-proxy regenerou config automaticamente. Fix permanente foi adicionado ao CD (`-e VIRTUAL_HOST= -e LETSENCRYPT_HOST=` no migration step + step pre-rolling de cleanup de `*-run-*`).

A pegadinha é genérica — qualquer setup CD que use `nginx-proxy` ou Traefik com label discovery + `compose run` para tarefas one-shot está exposto. A skill antes não cobria essa interação. Sessão gastou ~30min investigando hipóteses de JWT antes do diagnóstico de upstream pool aparecer; o "20 hits paralelos = split" agora é a primeira coisa a tentar quando 401 inconsistente aparece em prod com token válido. Lição justificativa do bump minor.

---

## [2.6.0] - 2026-05-05

### Adicionado

- **Nova reference `self-hosted-runner-docker.md`** (~280 linhas) — guia dedicado ao runner conteinerizado via `myoung34/github-runner`, complementando o conteúdo de runner-via-systemd que já existia em `troubleshooting-shared.md §"Runner Offline"`. Cobre 6 gotchas específicos da imagem com diagnóstico, fix canônico e template completo de Dockerfile + entrypoint + compose:
  - **§1**: `CMD` herdado da imagem base é zerado quando você define `ENTRYPOINT` custom — runner configura, sai com exit 0, restart loop. Fix: restaurar `CMD ["./bin/Runner.Listener", "run", "--startuptype", "service"]`.
  - **§2**: Imagem upstream consome env var `LABELS`, não `RUNNER_LABELS` — runner registra com label `default`, workflows com `runs-on: [self-hosted, production]` não enxergam.
  - **§3**: `EPHEMERAL=true` + `restart: always` entra em loop infinito porque `.runner` / `.credentials` persistem no FS layer entre restarts. Fix: limpar state files no entrypoint custom antes de delegar pro upstream.
  - **§4**: Build com `gpg --dearmor` falha em buildkit non-tty (`cannot open '/dev/tty'`). Fix: usar keyring `.asc` direto via `signed-by=`, eliminando dependência de gnupg.
  - **§5**: Registration tokens são single-use e vencem em 1h — script de bring-up deve regerar imediatamente antes de cada `up -d`.
  - **§6**: Stale runner registrations no GH bloqueiam re-registro limpo — `DELETE /repos/.../actions/runners/<id>` antes de re-registrar com mesmo nome.
- **`troubleshooting-shared.md` cenário 9: GitHub deploy keys per-repo unique (transferRepo)** — deploy key não migra automaticamente em `transferRepo`; tentar adicionar a mesma pubkey no novo repo dá `422 "key is already in use"` sem dizer onde está em uso. Fix: DELETE no antigo + POST no novo, ou gerar nova ed25519.
- **`troubleshooting-shared.md` cenário 10: `.env` com leading whitespace + `sed -i`** — sed silencia (regex `^KEY=` não casa) mas `docker-compose --env-file` strip-a o whitespace ao parsear, então `${KEY}` ainda funciona. Bug aparece só em manutenção via sed/awk. Fix canônico: reescrever `.env` atomicamente via heredoc + validação awk que detecta linha com leading space.
- **`troubleshooting-shared.md §4 "Runner Offline"` expandido**: agora distingue diagnóstico systemd vs container, e aponta para `self-hosted-runner-docker.md` quando o runner está em container com `RestartCount > 0`.
- **`SKILL.md` Routing Table**: nova entrada explícita pra `self-hosted-runner-docker.md` com gatilhos de detecção (presença de `myoung34/github-runner` em Dockerfile/compose, sintomas de loop).
- **`SKILL.md` description**: 9 triggers novos no frontmatter (`myoung34/github-runner`, `gh-runner container`, `Cannot configure the runner`, `runner label default`, `RUNNER_LABELS LABELS env var`, `registration token expired`, `deploy key already in use 422`, `transferRepo deploy key`, `.env leading whitespace sed`).

### Motivação

Feature 005-production-deploy do `validade_bateria_estoque`: bring-up do self-hosted runner conteinerizado em VPS de produção JRC encontrou os 6 gotchas em sequência (algumas combinadas em loops mascarados). Sessão gastou ~1h investigando o "exit 0 sem mensagem de erro" antes de inspecionar o entrypoint upstream e descobrir o `exec "$@"` esperando o CMD herdado. Outras 30min em `Cannot configure the runner` antes de mapear que `restart != recreate` em Docker e `.runner` persiste no FS layer.

Em paralelo, transferRepo `j0ruge/...` → `JRC-Brasil/...` revelou a regra deploy-key-per-repo, e múltiplas regenerações do `.env` durante o ciclo de debug expuseram o bug do leading-whitespace + sed silenciando.

A skill antes só cobria runner via systemd no host (caso clássico) — runner conteinerizado é o caminho recomendado pelos specs JRC desde 005 (FR-022a, R-002 socket-mount), então a lacuna era de cobertura. Progressive disclosure: o cluster grande (6 gotchas + template completo) virou ref própria; os 2 gotchas curtos (deploy key, .env whitespace) entraram em `troubleshooting-shared.md` sem inflar.

---

## [2.5.0] - 2026-05-05

### Adicionado

- Quick Troubleshooting: nova entrada `[S]` para `Cannot find package 'X' imported from /node_modules/<other-pkg>` em monorepo workspace npm
- Quick Troubleshooting: nova entrada `[F]` para vitest com `environment: 'jsdom'` que falha pré-test (`Cannot find package 'jsdom'`) ou em `TypeError: signal AbortSignal` em msw v2 — fix canônico é trocar para `happy-dom`
- Lição #32: devDeps com subtree em versões antigas que conflitam com a raiz não hoistam — npm aninha em `packages/<ws>/node_modules/`, fora do alcance da resolução Node ESM partindo de outras deps hoisted
- Lição #33: vitest 3 + msw v2 + jsdom tem dois bugs latentes (hoisting + `AbortSignal` mismatch); happy-dom resolve ambos
- `troubleshooting-shared.md` cenário 8: hoisting de devDeps com subtree pesado — sintoma `Cannot find package`, diagnóstico via grep no lock (`node_modules/<pkg>` na raiz vs `packages/<ws>/node_modules/<pkg>`), três fixes possíveis (trocar dep, declarar na raiz, regenerar lock)
- `troubleshooting-frontend.md` cenário 8: vitest jsdom → happy-dom como receita para projetos com msw v2 + monorepo workspaces
- `troubleshooting-shared.md` cenário 6: nota refinada sobre cascade fail-fast **multi-nível** — após o primeiro fix revelar bug 2, pode haver bug 3 mascarado por bug 2; recomenda rerun local após cada camada em vez de presumir que o segundo bug é o último

### Motivação

PR #6 do `validade_bateria_estoque`, pós-fix do v2.4.0 (`Missing script: "exec"`), revelou um bug previamente mascarado: `Cannot find package 'jsdom' imported from /node_modules/vitest/...`. Causa não era jsdom faltando — `packages/frontend/package.json` declarava `jsdom@^20.0.3`. O lockfile instalava em `packages/frontend/node_modules/jsdom`, não em `/node_modules/jsdom`, porque jsdom@20 trazia subtree de deps em versões antigas (`agent-base@6`, `cssstyle@2`, `tough-cookie@4`) conflitando com a raiz. vitest hoisted na raiz fazia `import 'jsdom'` partindo de `/node_modules/vitest/...`, subia a árvore via Node ESM resolution, não achava — porque a resolução nunca olha em `packages/<ws>/node_modules/`.

Solução canônica: trocar `jsdom` por `happy-dom`. Subtree leve hoista limpo + happy-dom usa `AbortController` nativo do Node, resolvendo de quebra um segundo bug latente que jsdom escondia (msw v2 + undici nativo validam `signal instanceof AbortSignal` contra a global do Node, não do jsdom). Fix único, dois bugs resolvidos: `npm i -D happy-dom -w <ws>`, `environment: 'happy-dom'` em `vitest.config.ts`. Nesta sessão: 57 pacotes removidos, 5 adicionados, 118/118 testes passando, CI verde em ~1m30s.

Lição cascade multi-nível: v2.4.0 documentava `npm exec` mascarando 44 testes msw/jsdom. Aprendemos agora que esses 44 eram, por sua vez, mascarados POR `jsdom not found`. Cascade em 3 níveis. Refinamos o cenário 6 para sugerir rerun local após cada fix em vez de presumir que o segundo bug revelado é o último.

---

## [2.4.0] - 2026-05-05

### Adicionado

- Quick Troubleshooting: nova entrada `[S]` para `Missing script: "exec"` ao invocar binário em workspace de monorepo npm
- Quick Troubleshooting: nova entrada `[S]` para `ESLint couldn't find an eslint.config.(js|mjs|cjs) file` em workspace que migrou pra ESLint v9
- Lição #30: `npm run -w <ws> exec --` é sintaxe inválida — `exec` é subcomando do `npm`, não script de `package.json`
- Lição #31: ESLint v9 flat config é per-workspace, não herda de siblings
- `troubleshooting-shared.md` cenário 6: causa, occurrences comuns (tsc/playwright/openapi-typescript), fix e nota explícita sobre fail-fast mascarando steps subsequentes
- `troubleshooting-shared.md` cenário 7: snippet de flat config Node-only, diferenças vs config React, e nota sobre hoisting de devDeps em monorepo

### Motivação

PR #6 (`feat(005-production-deploy)`) tinha **8 jobs vermelhos** no CI. Investigando: 6 dos 8 vinham de uma única causa — sintaxe `npm run -w <ws> exec -- <cmd>` em 3 workflows (`ci.yml`, `cd-production.yml`, `frontend-ci.yml`). `npm run exec` busca um script chamado "exec" em `package.json`; não existindo, aborta com `Missing script: "exec"`. A sintaxe correta é `npm exec -w <ws> -- <cmd>` (sem `run`). Os outros 2 jobs falhavam por `ESLint couldn't find an eslint.config.(js|mjs|cjs) file` — workspaces `@validade-bateria/backend` e `@jrc/idp` declaravam `eslint ^9.0.0` sem `eslint.config.js` próprio, contando incorretamente com herança do flat config existente em `packages/frontend/`.

Bonus lição: o `Missing script: "exec"` é **fail-fast** — abortava em segundos no step de Typecheck, **mascarando** falhas pré-existentes nos steps subsequentes (44 testes frontend quebrados por interop msw/jsdom, type errors latentes em `auth-sanity.test.ts`, openapi codegen drift). Ao consertar a sintaxe, esses fails apareceram e foram inicialmente confundidos com regressões. Documentado no cenário 6.

---

## [2.3.0] - 2026-03-25

### Adicionado

- Quick Troubleshooting: nova entrada `[B]` para "Migration reports 'No pending migrations' but app crashes with missing column" (Docker image cache stale)
- Lição #29: `docker run` não faz auto-pull se a tag já existe localmente no self-hosted runner
- `troubleshooting-backend.md`: novo cenário "No pending migrations but app crashes" com diagnóstico, fix no workflow e recovery manual
- `troubleshooting-backend.md`: diagnosis flow atualizado com leaf de stale image cache no branch de deploy
- `checklist-backend.md`: seção 7 agora inclui `docker pull` antes do step de migration

### Motivação

Incidente em produção: CD workflow rodou `docker run ghcr.io/.../api:staging npx prisma migrate deploy` em self-hosted runner que tinha a imagem anterior em cache. O step de migration reportou "no pending migrations" (imagem antiga, N migrations) enquanto o container deployado (imagem nova, N+1 migrations) referenciava uma coluna que ainda não existia. Fix: sempre `docker pull` antes de `docker run` nos steps de migration.

---

## [2.2.0] - 2026-03-18

### Adicionado

- Detecção de projeto Biome: `biome.jsonc` / `biome.json` → **Backend (Biome)** na tabela de detecção
- Variante CI para Backend (Biome): `checkout → install → [prisma generate] → biome check → [test if configured]`
- 2 entradas na Quick Troubleshooting table: `npx biome check .` em arquivos de config e Biome 2.x `unknown key "ignore"`
- Lição #27: Biome verifica todos os arquivos por padrão — scoping com `files.includes`
- Lição #28: Primeiro deploy requer workflows no branch `develop`
- `troubleshooting-backend.md`: 2 cenários de troubleshooting Biome (escopo de arquivos e migração 2.x)
- `checklist-backend.md`: variante Biome na seção de Lint/Format; nota sobre `DATABASE_URL` com `sqlserver://` para MSSQL
- `checklist-backend.md`: seção de testes agora cobre cenário "sem test framework" — pular steps de teste
- `checklist-shared.md`: seção 5 "Primeiro Deploy (Bootstrap)" com checklist e comandos para criar branch `develop`

### Alterado

- Compose path na tabela de deploy agora indica "varia por projeto" em vez de hardcoded `infra/nodejs/`
- Tabela de arquivos do pipeline backend usa paths genéricos (`Dockerfile` ou `infra/*/Dockerfile`)
- Comando de rollback backend usa `<COMPOSE_PATH>` genérico
- `checklist-backend.md`: seção 7 (Workflow CD) inclui verificação de compose path

### Motivação

Deploy de `estimates_api` (npm, Biome, SQL Server/MSSQL, sem testes) para staging revelou 6 gaps na skill v2.1.0 que foi construída a partir de projetos ESLint+Prettier+PostgreSQL+Jest. A skill agora suporta múltiplas variantes de stack backend.

---

## [2.1.0] - 2026-03-16

### Alterado

- GHCR login no deploy padronizado como `docker/login-action@v3` em ambos os projetos (era `[F]`-only, agora `[S]`)
- Tabela "Diferenças no Deploy": backend agora usa `docker/login-action@v3` (antes era "Não necessário")
- `troubleshooting-shared.md`: cenário #1 reescrito — causa raiz atualizada para contexto isolado entre jobs, solução agora recomenda `docker/login-action@v3` sobre `docker login` manual
- `checklist-shared.md`: item GHCR atualizado para recomendar `docker/login-action@v3` com justificativa (logout automático, config isolada, masking)
- `checklist-backend.md`: adicionada seção 7 (Workflow CD) com checklist de login, generate .env, migrations e cleanup

### Motivação

Backend API falhava no Deploy Staging com `denied` no GHCR pull — o job Deploy não tinha login. Padronizado `docker/login-action@v3` nos 4 workflows (API staging/prod + frontend staging/prod). A action é preferível ao `docker login` manual em self-hosted runners por cleanup automático de credenciais.

---

## [2.0.0] - 2026-03-12

### Adicionado

- Skill unificada backend + frontend com progressive disclosure
- Detecção automática de projeto (Prisma → backend, Vite → frontend)
- Quick troubleshooting table unificada com tags `[B]`/`[F]`/`[S]` (21 entradas)
- Tabela de roteamento para 7 arquivos de referência
- Tabela de lições aprendidas unificada (26 lições com tags)
- `references/troubleshooting-shared.md` — 5 cenários de infra compartilhados
- `references/checklist-shared.md` — 4 seções compartilhadas (runner, GHCR, DNS, rede)
- `references/troubleshooting-backend.md` — exit codes, Zod, Prisma, VIRTUAL_PORT, diagnóstico
- `references/checklist-backend.md` — 7 seções (secrets, Zod CI vars, Docker, lint, Jest, build, rede)
- `references/test-fixes-backend.md` — 8 padrões de correção de testes Jest
- `references/troubleshooting-frontend.md` — Vite, SPA, nginx, Alpine, diagnóstico
- `references/checklist-frontend.md` — 6 seções (VITE_* secrets, Dockerfile, compose, CI, CD, build files)
- Comandos úteis com templates por projeto (compose path difere)
- Tabela de arquivos do pipeline separada por projeto

### Removido

- `references/troubleshooting.md` (conteúdo distribuído em troubleshooting-shared/backend/frontend)
- `references/github-actions-checklist.md` (conteúdo distribuído em checklist-shared/backend/frontend)
- `references/test-fixes.md` (renomeado para test-fixes-backend.md)

### Alterado

- SKILL.md agora é entry point fino (~230 linhas) que roteia para referências on-demand
- Conteúdo duplicado entre backend e frontend eliminado via arquivos shared
- Versão: 1.x.0 (separadas) → 2.0.0 (unificada)

---

## Histórico Pré-Unificação

### Frontend (v1.0.0 → v1.1.0)

- **v1.1.0**: 5 lições do deploy real (healthcheck, vite.config.ts, Vitest E2E, treeshake, GHCR login)
- **v1.0.0**: SKILL.md com 10 lições, troubleshooting (9 cenários), checklist (8 seções)

### Backend (v1.0.0 → v1.6.0)

- **v1.6.0**: ERR_SSL_VERSION_OR_CIPHER_MISMATCH, DNS/SSL troubleshooting
- **v1.5.0**: Port mapping desnecessário com nginx-proxy
- **v1.4.0**: VIRTUAL_PORT obrigatório para nginx-proxy
- **v1.3.0**: Secrets com `z.string().url()` devem incluir `https://`
- **v1.2.0**: Variáveis Zod no Generate .env do CD
- **v1.1.0**: GHCR auth sudo/user, rede nginx-proxy variável, lint pré-push, re-trigger
- **v1.0.0**: SKILL.md com 14 lições, troubleshooting (exit codes + 12 cenários), test-fixes (8 padrões), checklist (10 seções)
