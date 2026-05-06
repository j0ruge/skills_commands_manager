# Changelog — cicd (Unificada)

Formato: [Semantic Versioning](https://semver.org/)

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
