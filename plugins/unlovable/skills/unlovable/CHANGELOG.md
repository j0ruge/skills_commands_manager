# Changelog — unlovable

## [1.1.0] — 2026-09-09

Primeiro uso real depois de publicada: limpeza do `sales_quote` (Vite + React
com `lovable-tagger`, caso 3a). Três coisas que a skill não tinha.

### Changed

- **`og:image`: a recomendação estava invertida.** A v1.0.0 dizia *"se houver
  `og:image` do Lovable, apontar p/ asset próprio"* — que soa como uma edição de
  uma linha e não é. `og:image` quer URL **absoluta**, e num projeto com staging
  e produção em domínios diferentes isso é variável de build, não string no HTML;
  além disso o logo que existe no repo costuma ser faixa de cabeçalho (457x154 no
  caso medido), não o 1200x630 do card. A saída certa é **remover** `og:image` /
  `twitter:image` e usar `twitter:card: summary`, registrando a imagem própria
  como pendência — o branding some hoje, sem asset e sem chumbar domínio.

### Added

- **Ler o card como mapa.** `og:title` normalmente já está correto (o Lovable o
  preenche com o nome do app), então o preview sai meio certo e meio Lovable, e
  isso distorce o tamanho aparente do problema. Casar cada linha do print com a
  tag que a produziu vem antes de editar.
- **Verificação no artefato**: `grep -c lovable dist/index.html` no §6. Metadado
  de `index.html` é o que o crawler lê **do build servido**; provar que a string
  saiu da fonte não prova que saiu do que vai para produção.
- **Nem toda sobra em lockfile é mirror de registry.** O Pitfall existente cobria
  só o falso positivo (`sandbox-npm-cache.lovable.dev` em URLs `resolved`). Em
  monorepo há um segundo caso: `npm install` da raiz não toca lockfiles órfãos
  dentro dos workspaces, que seguem declarando o pacote como dependência real. O
  `grep` do §6 acusa depois de o trabalho estar certo e o build limpo — e a saída
  é reconhecer o resíduo como **inerte**, não "consertar" um arquivo fora do
  escopo.

## [1.0.0] — 2026-09-09

Primeira publicação no marketplace. A skill nasceu em `~/.hermes/skills/devops/`
a partir de uma migração real de um projeto gerado no lovable.dev; esta entrada
registra o que mudou ao entrar no kit.

### Added

- Bifurcação do §3 (build) em **3a Vite + React puro (`lovable-tagger`)** e
  **3b TanStack Start (`@lovable.dev/vite-tanstack-config`)**. A versão original
  só cobria o segundo caso, mas o primeiro é o escafoldamento mais comum do
  Lovable — e a diferença é de ordem de grandeza: `lovable-tagger` é um plugin
  dev-only listado no próprio `vite.config.ts` do projeto, enquanto o wrapper
  TanStack *é* a config e exige reescrevê-la à mão. Sem essa distinção a skill
  mandava reescrever um `vite.config.ts` que não precisava mudar.
- Parágrafo de abertura explicando **por que a ordem importa** (estrutural antes
  de cosmético): uma falha de `build` depois de dez edições de string não diz
  qual delas a causou.
- Nota de **rotação de credencial** no §4 — reescrever o histórico não invalida
  uma chave já empurrada para um remoto.
- Razão explícita para preservar a assinatura da função de email (§2): campo que
  some vira `undefined` na UI, sem erro.

### Changed

- `description` reescrita de 56 para 451 caracteres, com a linha `Triggers — `
  exigida pelo `CLAUDE.md`. A anterior (*"Remove all Lovable traces from a
  Lovable-generated codebase."*) só disparava para quem já escrevesse "lovable"
  literalmente — e a description é a superfície inteira de triggering.
- Frontmatter normalizado para a forma do kit (`name` + `metadata.version` +
  `description` **entre aspas**). Os campos `metadata.trigger`, `when_to_use` e
  `tags` saíram: o primeiro par vive na `description`, e as keywords vivem no
  `plugin.json`, onde o Claude já as lê separadamente.
- **Despersonalização** para publicação: caminhos e endereços de uma instalação
  específica (`~/.hermes/scripts/send-email.mjs`, `~/.hermes/.env`, um e-mail de
  bot corporativo, uma skill privada citada como referência) deram lugar a
  `SMTP_USER`/`SMTP_PASS` e ao SMTP genérico, com o Gmail como *um* exemplo em
  vez do padrão implícito. Dado de instalação em prompt publicado é a classe de
  ruído que a auditoria de 2026-09-03 removeu das outras skills do kit.
