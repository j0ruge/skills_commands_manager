# Changelog — zitadel-idp

## [0.11.1] — 2026-08-26

Higiene de `description`, sem mudança de comportamento: o texto tinha **670 chars**,
acima do cap de 500 do `CLAUDE.md`. A `description` é a superfície de triggering — é só
por ela que o Claude decide invocar a skill —, e descrição longa demais dilui o sinal e
pode ser **cortada em silêncio** na lista `/skills`, piorando justamente o que ela deveria
melhorar.

### Changed

- **Description encurtada de 670 para 476 chars**, espelhada nos três arquivos
  (`SKILL.md`, `plugin.json`, `marketplace.json`). Encurtada **em vez de somada**: o que
  saiu foi as checagens pré-cutover sem credencial (authorize probe, SPA bundle grep), instâncias prod+staging e migração de usuários — detalhe que continua no corpo da skill, onde é útil de fato.
  Os sinais de disparo (o que a skill faz + os diferenciais que a distinguem das vizinhas)
  foram preservados.

## [0.11.0] — 2026-08-08

Lições de um cutover de produção real (segundo Zitadel, aplicação nova no mesmo IdP).
Quirks **44–47**; a headline passa de "forty-three" para "forty-seven".

### Added

- **Quirk 44 — provar `client_id` + `redirect_uri` SEM credencial.** **O quê**: montar a
  URL do `authorization_endpoint` com PKCE S256 e conferir que a resposta é `302` para
  `/ui/login/login?authRequestID=…`. **Por quê**: toda verificação de client que a skill
  tinha exige PAT (`GetApplication`, Console), o que as torna inúteis no único momento em
  que mais se precisa delas — o check pré-cutover num ambiente novo, onde ninguém logou
  ainda e nenhum PAT foi cunhado para aquela instância. O Zitadel valida o client e casa o
  redirect **antes** de renderizar qualquer coisa, então o redirect para o login é a prova.
  Usa o vetor de teste da RFC 7636 como `code_challenge` (o fluxo nunca é completado, logo
  não precisa de verifier).
- **Quirk 45 — conferir a config OIDC no bundle SERVIDO.** **O quê**: baixar o
  `/assets/index-*.js` do host público e grepar authority, `client_id`, redirect e API
  base. **Por quê**: a skill já dizia 2× que `VITE_*` é build-time, mas "o secret está
  setado" e "o bundle contém o valor" são afirmações diferentes — build anterior ao
  secret, layer cacheada, rebuild que não houve, ou tag que resolveu para o build de outro
  ambiente produzem um bundle divergente, e o sintoma é só "o login não completa". Grepar
  o bundle **servido** (não o de dentro do container) também pega container stale ainda
  registrado no upstream pool do proxy. Fecha o par com o 44: o 45 prova que o SPA *pede*
  os valores certos, o 44 que o IdP os *aceita*.
- **Quirk 46 — `ZITADEL_SEED_USER_ROLE` como LISTA quando duas apps dividem o Zitadel.**
  **O quê**: cravar só a role da app nova faz a app antiga perder o admin. **Por quê**: o
  `CreateAuthorization` grava a lista **literal**, enquanto o `UpdateAuthorization` faz
  **união** — então numa instância existente tudo parece certo e o defeito fica dormente
  até alguém recriar o Zitadel do zero, que é exatamente quando não se quer descobri-lo.
  Distinto do quirk 41, que é o problema adjacente numa instância viva.
- **Quirk 47 + `references/multi-instance-and-user-migration.md`** (novo). **O quê**: o que
  precisa divergir entre duas instâncias (issuer, JWKS, `projectId`/audience, `clientId`,
  PAT — e o que **pode** coincidir: o `applicationId`, que é seu handle e não do OAuth), e
  a assimetria da migração de usuários. **Por quê**: token de uma instância validado
  contra a outra dá `JWSSignatureVerificationFailed`, que se lê como problema de rotação de
  chave (quirks 12/13/36) e manda a investigação para o lugar errado. E a migração é
  lopsided: `AddHumanUser` aceita `hashedPassword`, mas **não existe API que devolva o hash
  da origem** — ele vive no eventstore e ler de lá depende de esquema interno que a própria
  migração v2.66→v4 reescreve. Caminho de baixo risco: recriar contas com
  `changeRequired: true`, lembrando que **grants não viajam com o usuário**.

### Changed

- **`token-validation.md` ganha a contraparte POSITIVA do quirk 36.** Tudo que existia era
  diagnóstico de falha, executado depois da tempestade começar. O storm é tardio por
  construção (TTL do JWKS ~600s), e é isso que torna um smoke verde em T+30s irrelevante
  para essa falha — a nova seção dá os dois sinais conferidos **depois** da janela, com o
  aviso de que um `/health/ready` que devolve `jwks: ok` de um valor cacheado que nunca
  revalida mente durante o storm inteiro.
- **Quirk 30**: corolário de três ambientes (`ids.staging` ao lado de dev/prod torna o
  footgun do default silencioso pior — dois de três ambientes ficam errados) e o registro
  explícito de que o `clientId` numérico **não é recuperável do YAML**; ele existe só no
  log do bootstrap e no arquivo de saída, que passa a ser artefato, não linha de log.
- **`keywords` de `plugin.json` e `marketplace.json` sincronizados** — estavam divergentes
  **antes** deste retrofit (51 vs 57 entradas).
- `description` reescrita mantendo a ordem de grandeza (643 → 670 chars): troca
  `smoke-e2e CI`, `Login UI v1/v2` e `console Failed to fetch` dos triggers por
  *pre-cutover check*, *client_id mismatch* e *user migration* — o traço novo precisava de
  superfície de disparo, e a description não podia crescer para isso.

## [0.10.0] — 2026-07-15

### Added

- Quirk 43 — o Console admin do próprio Zitadel mostra "[unknown] Failed to fetch" quando o
  `environment.json` gerado traz `api: http://` enquanto `issuer: https://` (mixed content na
  página HTTPS). O `issuer` vem da config de instância persistida (fica https); o `api` é
  computado por-request e só sai https quando o binário confia no `X-Forwarded-Proto` do proxy,
  i.e. sob `--tlsMode external` — é o sintoma facing-Console do triad incompleto do quirk 15.
  Armadilha composta: `docker start`/`restart` revive os `Args`/env de **criação** do container
  (não relê o compose), então um container criado do compose base (`--tlsMode disabled`) fica
  quebrado mesmo depois de adicionar o override; a cura é `up -d --force-recreate`, nunca
  `docker start`. Nova entry em `troubleshooting.md §Reverse proxy / TLS` + bullet de pitfall
  no `docker-compose-bootstrap.md §7`.
- Descrição do plugin/marketplace/SKILL.md **enxugada e espelhada** (~660 chars, padrão
  `Triggers —`): os paredões append-only das versões anteriores diluíam o sinal de triggering;
  o detalhe versionado permanece no README + neste CHANGELOG.

## [0.9.0] — 2026-05-18

### Added

- Primeiro smoke real-browser do loop SPA↔backend↔Zitadel (sales_quote T150) expôs dois
  pitfalls novos. Quirk 41 — o bootstrap idempotente cria os grants do usuário inicial mas
  NÃO reconcilia os já existentes quando o YAML evolui (um usuário seed pré-existente fica
  com os `roleKeys` do dia-0 e o JWT sai sem o novo papel; um usuário novo pelo mesmo
  bootstrap funciona — a assimetria é o diagnóstico); cura é search-then-PUT (padrão do
  quirk 8). Quirk 42 — a SPA no navegador → Express precisa de CORS, senão todo preflight
  `OPTIONS` cai no `authJwt` e retorna 401 (mimetiza a família 401-storm; `curl` com Bearer
  passa porque não dispara preflight, e testes MSW/supertest não emitem preflight real);
  cura é um middleware CORS mínimo como PRIMEIRO middleware, encurtando `OPTIONS` com 204.
- `spa-recipes.md` — receita "E2E browser tests (Playwright) contra Zitadel self-signed"
  (`ignoreHTTPSErrors`, fill condicional de username em `login_hint`, caveat de
  `storageState` + `InMemoryWebStorage`).

## [0.8.0] — 2026-05-08

### Added

- Três quirks de smoke-e2e em CI (validade_bateria_estoque PR #10). Quirk 38 — bind mount
  de `ZITADEL_FIRSTINSTANCE_PATPATH` com EACCES no runner GHA (uid 1000 vs 1001 + 0755)
  cascateia num `unique_constraints_pkey` enganoso; cura é `mkdir -p && chmod 0777` ANTES
  do `docker compose up`. Quirk 39 — a política de senha padrão exige as 4 classes de
  caractere; `openssl rand -hex` é lowercase-only e falha no AddHumanUser (use prefixo
  estruturado `Aa1!` + cauda alfanumérica). Quirk 40 — `zitadel-login` (Login UI v2)
  precisa de ~90s+ pro primeiro healthcheck em runners pequenos, estourando `up --wait`
  da stack inteira; cura é escopar o `--wait` a `zitadel-db zitadel-init zitadel`.
- Checklist "Smoke-e2e plumbing for GHA".
