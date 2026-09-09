# Changelog — unlovable

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
