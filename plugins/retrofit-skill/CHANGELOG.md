# Changelog

## [0.2.1] — 2026-06-06

### Adicionado

- **Passo "ANTES DE EDITAR — atualize o repo local"** no fluxo do comando: antes
  de tocar em arquivos, fazer `git fetch` e trazer a branch alvo para o estado do
  remoto (fast-forward ou rebase). Inclui o cuidado de, num clone recém-migrado
  Windows→WSL, limpar o ruído de CRLF/filemode (`git diff --ignore-cr-at-eol`
  vazio → `core.fileMode=false` + `git checkout -- .`) antes do rebase.

### Motivação

- Nesta sessão (publicação da skill `wsl-windows-onboarding`) o clone local estava
  **atrás do `origin/main`** — outra origem havia empurrado 4 commits. O `git push`
  foi **rejeitado** e foi preciso `git fetch` + `git rebase origin/main` com o
  commit já feito sobre uma base defasada (ainda por cima com a árvore "suja" só
  por CRLF, o que travava o rebase até um `git checkout -- .`). Sincronizar o repo
  ANTES de editar elimina esse retrabalho e faz o push final passar de primeira.

## [0.2.0] — 2026-06-05

### Adicionado

- **Modo enxuto (lean)** para skills locais. Passo 0 do fluxo agora escolhe entre **completo**
  (skill publicada no marketplace: bump de versão + `marketplace.json` + README + push) e
  **enxuto** (skill local de outro repo, ex.: `<outro-repo>/.claude/skills/<nome>/`: edita os
  arquivos + registra a lição num `CHANGELOG.md` na pasta da skill e commita no repo onde ela
  vive, **sem** bump, `marketplace.json`, README do marketplace ou push aqui).
- Critério explícito para não confundir os dois modos (está versionada no marketplace? → completo;
  é local/correção de cobertura? → enxuto).

### Motivação

- Nesta sessão o retrofit foi aplicado à skill `abnt-academico`, que é **local** (vive em
  `aula_veiga/.claude/skills/abnt-academico/`, fora do marketplace). O fluxo original assumia
  `<REPO>/plugins/$ARGUMENTS/`, bump em `marketplace.json` e push para o `origin/main` do repo de
  skills — passos inválidos para uma skill local. Faltava distinguir os dois cenários, o que gerava
  confusão entre "retrofit enxuto" e "retrofit completo".

## 0.1.0 — 2026-04-18

- Initial release: packaged the personal `/retrofit-skill` command as a marketplace plugin.
