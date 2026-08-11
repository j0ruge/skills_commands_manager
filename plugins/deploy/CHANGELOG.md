# Changelog — deploy

Formato: [Semantic Versioning](https://semver.org/)

## [2.0.0] - 2026-08-10

### Corrigido (CRÍTICO — a skill podia deployar produção achando que ia para staging)

- **A topologia de branches deixa de ser presumida e passa a ser descoberta.** A
  versão anterior afirmava que push em `develop` dispara o `cd-staging.yml` e
  mandava `git checkout main && git merge origin/develop --ff-only && git push
  origin main` para "sincronizar". Isso vale no repo onde a skill nasceu — que
  não tem branch `staging` —, mas num repo com a cadeia `develop → staging →
  main` os dois passos estão errados **e o segundo é destrutivo**: `cd-staging`
  escuta `staging`, e push em `main` dispara `cd-production`. Seguir a skill
  deployaria **produção** enquanto reportava "staging".
- Novo **Step 0 — Discover the topology**: lê o bloco `on:` de cada workflow,
  monta o mapa branch → pipeline e exige identificar qual branch é gatilho de
  **produção** antes de qualquer push. Aborta se o alvo de staging coincidir
  com ele.
- **A skill só empurra a branch-alvo.** O `git push origin main` embutido no
  fluxo de staging morreu. Produção virou promoção separada e explícita, com
  confirmação do usuário.
- Step 6 captura o run na **branch-alvo** — antes era `--branch develop` fixo,
  que num repo de topologia diferente monitora o pipeline errado (ou nenhum).

### Alterado

- **Pre-flight derivado do repo** em vez de hardcoded. `yarn test
  --watchAll=false` e `npx eslint src/` eram do stack de origem e viram no-op
  silencioso em npm/pnpm, monorepo ou outro escopo de lint. Agora detecta o
  gerenciador pelo lockfile e roda os scripts que existem no `package.json`.
  Dois gotchas documentados: script de raiz que não existe sai 0 e parece
  aprovação; e `tsc --noEmit` é **no-op** em tsconfig solution-style
  (`"files": []` + project references) — ali é `tsc -b --noEmit`.
- **Gate novo: CI verde no commit exato que está sendo promovido**, conferindo o
  `headSha` (run verde num commit anterior não prova nada sobre este).
- **Promoção por PR com merge commit, não squash.** Branch de ambiente é
  long-lived: o squash cria commit sem ancestralidade com a origem, e a
  promoção seguinte enxerga divergência sobre conteúdo idêntico.
- **Sensores antes de promover**: `git log --no-merges $TARGET..$SOURCE` (o que
  vai), o inverso (conteúdo exclusivo do alvo — vazio é o caso saudável, porque
  merges de promoções anteriores são filtrados) e `git diff --name-only --
  .github/workflows/`, que responde qual pipeline vai rodar quando a própria
  promoção altera os workflows.
- Step 7 pede para reportar **qual ambiente está servindo o código novo**, e
  para conferir que o smoke rodou em vez de ter sido pulado — pipeline verde
  que pulou a verificação não é deploy verificado.

### Motivação

Numa promoção real (`sales_quote`, cadeia `develop → staging → main`), seguir a
skill ao pé da letra teria empurrado `main` e disparado o deploy de produção no
host de produção, enquanto anunciava "staging". A skill foi descartada em favor
do fluxo correto e esta versão nasce daí.

A lição generalizável não é "a topologia certa é develop → staging → main" —
cravar isso reintroduz o mesmo defeito com outros nomes. É que **nome de branch
não carrega significado universal**, e a única fonte de verdade sobre o que um
push dispara é o `on.push.branches` do workflow. Por isso o passo de descoberta
vem antes de tudo, e por isso a skill nunca empurra uma branch que não provou
ser o gatilho do ambiente pedido.

---

## [1.4.0] - 2026-03-16

### Corrigido

- Pre-flight: `npx eslint .` corrigido para `npx eslint src/` (alinhado com CI)
- Pre-flight: `yarn vitest run src/test/` corrigido para `yarn test --watchAll=false` (projeto usa Jest, nao Vitest)

### Alterado

- Step 9 reescrito: agora captura o `run-id` do pipeline triggado pelo push
- Novo step 10: monitora o pipeline com `gh run watch <run-id>` ate completar
- Novo step 11: avalia resultado — se falhar, exibe `gh run view --log-failed`; se suceder, reporta com link
- A skill so considera o deploy concluido quando o pipeline terminar com sucesso

### Motivacao

A versao anterior apenas listava os runs recentes sem monitorar o resultado. O usuario precisava verificar manualmente se o pipeline passou. Agora o fluxo e end-to-end.

---

## [1.3.0] - 2026-03-13

### Alterado

- Plugin renomeado de `deploy-staging` para `deploy` (namespace fix)
- Command file renomeado de `deploy-staging.md` para `staging.md`
- Invocação muda de `/deploy-staging:deploy-staging` para `/deploy:staging`
- Preparado para futuros subcomandos (e.g. `/deploy:production`)

---

## [1.2.0] - 2026-03-13

### Adicionado

- Detecção automática de cenário: branch atual `develop` vs feature branch
- Fluxo simplificado quando já em `develop`: sincroniza main com `origin/develop` (ff-only), pusha commits locais e pula direto para verificação de pipeline
- Steps 6-8 preservados como fluxo completo para feature branches

### Motivação

Quando o usuário já está em `develop`, os passos de merge de feature branch são desnecessários. O fluxo simplificado evita checkouts e merges redundantes.

---

## [1.1.0] - 2026-03-13

### Adicionado

- Passo pre-flight: `eslint --max-warnings 0`, `tsc --noEmit`, `vitest run` antes do push
- Aborta o fluxo se qualquer verificação local falhar, evitando falhas no pipeline remoto

### Motivação

Deploy `23060872731` falhou por warning ESLint (`react-refresh/only-export-components`) que teria sido pego localmente.

---

## [1.0.0] - 2026-03-13

### Adicionado

- Workflow completo: verificar working tree → fetch → sincronizar main com develop → merge feature → push develop → verificar pipeline
- Sincronização automática de `main` com `origin/develop` via fast-forward
- Verificação de pipeline via `gh run list`
- Notas sobre CD staging (GHCR `:staging`, self-hosted runner)
