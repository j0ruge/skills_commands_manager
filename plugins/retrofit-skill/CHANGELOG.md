# Changelog

## [0.3.0] — 2026-08-26

O fluxo já mandava rodar `validate-versions.py` — e mesmo assim um retrofit
passou deixando dois resíduos: a `description` do `cicd` entrou em 2 dos 3
arquivos e o README ficou uma versão atrás. O erro só apareceu na sessão
seguinte, quando outra pessoa rodou o validador.

Ou seja: o problema não era a ausência da instrução. Era o que ela não dizia —
**quando** rodar, **o que fazer com os warnings**, e que ter editado não é prova
de que o arquivo mudou.

### Added

- **Passo de verificação antes do commit**, com o validador movido para posição
  de gate e não de formalidade final, mais um snippet que confere os quatro
  lugares (`SKILL.md`, `plugin.json`, `marketplace.json`, README) e reporta se a
  description bate nos três e se a versão chegou ao README.
- **WARNINGS passam a ser bloqueantes para a skill que está sendo tocada.** Eles
  não reprovam o gate, e é por isso que passam despercebidos: aviso que nunca
  reprova vira ruído. Encurtar uma description no ato é barato; deixar acumular
  virou um mutirão de 7 plugins (até 871 chars).
- **Aviso sobre `git checkout -- .claude-plugin/marketplace.json`**: o arquivo é
  único e compartilhado, então usá-lo para desfazer uma sondagem leva junto as
  edições reais da sessão. A recuperação é ressincronizar a partir do
  `plugin.json`, que é canônico por plugin.

### Changed

- **A atualização do README deixou de ser condicional.** O texto dizia "*se* a
  mudança afeta como a skill é descrita/versionada" — mas um bump **sempre**
  muda a versão na tabela. Foi por esse "se" que o `2.20.0` sobreviveu.

## [0.2.3] — 2026-07-25

### Corrigido

- **Commits deste fluxo não levam mais o trailer `Co-Authored-By: Claude`.** Os dois
  modos (completo e enxuto) mandavam explicitamente assinar com coautoria do Claude.
  O usuário quer que o histórico do repositório dele mostre só o nome dele.
- A regra ficou numa seção própria (*Autoria dos commits*) e é **afirmativa**, não
  uma omissão: o prompt padrão do Claude Code instrui a terminar mensagens de commit
  com esse trailer, então apenas apagar a menção deixaria o default vencer. Dizer
  "sem `Co-Authored-By`" é o que efetivamente muda o comportamento.

Editado: `commands/retrofit-skill.md` (modo completo, modo enxuto e nova seção).
Sem mudança na superfície de triggering — descrição inalterada.

## [0.2.2] — 2026-06-06

### Adicionado

- **Seção "Mantenha a descrição ENXUTA (triggering)"** — orienta o retrofit a não deixar a `description` (superfície de triggering) inchar: não anexar a lição de cada versão, alvo ~350–500 chars, enxugar em vez de só somar (uma frase do que faz + 1–2 diferenciais + `Triggers —` compacto ≤8 itens), espelhada nos três lugares (SKILL.md, plugin.json, marketplace.json); detalhe vai para references/README.
- **Seção "Editando `marketplace.json` com segurança"** — ao editar programaticamente, escopar ao bloco do plugin alvo (`"name": "$ARGUMENTS"`); um match ingênuo em `"description":` ou `sed` global sobrescreve as descrições de TODOS os plugins.

### Motivação

- Nesta sessão, a descrição da skill `wsl-windows-onboarding` inchou para ~1.100 chars ao longo de v0.1.0→v0.2.0 (cada retrofit anexando) e precisou ser enxugada para ~720 — exatamente o anti-padrão que esta diretriz previne. E uma edição programática do `marketplace.json` por prefixo `"description":` chegou a sobrescrever as 14 outras descrições (revertida do git) — daí a regra de escopar ao bloco do alvo. Meta-retrofit: o `retrofit-skill` aplicado a si mesmo.

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
