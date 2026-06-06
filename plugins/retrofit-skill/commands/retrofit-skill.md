---
description: Apply non-obvious session lessons to a target skill in two modes — full (marketplace skill: bumps version, updates CHANGELOG/marketplace.json/README, commits and pushes) or lean (local skill in another repo: edits files + CHANGELOG and commits there, no bump or marketplace changes). Triggers — retrofit, skill-maintenance, session-lessons, lean-retrofit, local-skill.
metadata:
  version: 0.2.2
---

Invoque a skill `skill-creator` antes de qualquer outra ação nesta task —
ela orienta o processo de melhorar skills existentes. Se ela não estiver
disponível, prossiga mesmo assim e me avise.

Analise as lições aprendidas nesta sessão e aplique as relevantes à skill
`$ARGUMENTS`.

## PASSO 0 — escolher o MODO (enxuto vs completo)

Antes de tudo, localize a skill alvo e decida o modo. Os dois melhoram a
skill; diferem em **quais artefatos são tocados**:

- **COMPLETO** — a skill é publicada NESTE marketplace, em
  `<REPO>/plugins/$ARGUMENTS/`. Faz o ciclo versionado completo (bump de
  versão, `marketplace.json`, README, push).
- **ENXUTO** — a skill é LOCAL de outro repositório (ex.:
  `<outro-repo>/.claude/skills/$ARGUMENTS/`), fora deste marketplace. Edita
  os arquivos da skill e registra a lição num CHANGELOG dentro da própria
  pasta da skill, commitando NO REPO onde ela vive. NÃO mexe em
  `marketplace.json`, no README do marketplace, nem faz bump/push aqui.

Critério para não confundir: a skill está versionada/publicada no
marketplace? → **completo**. É local, normalmente uma correção de
cobertura/documentação? → **enxuto**. Na dúvida, pergunte ao usuário.

PARA LOCALIZAR O REPO DO MARKETPLACE (só no modo completo):
- Primeiro tente `../skills_commands_manager` (sibling do repo atual).
- Se não existir, procure siblings com nome contendo "skills" ou "commands".
- Se ainda não achar, me pergunte o caminho. Não adivinhe.
- Confirme o caminho encontrado antes de seguir.

No modo completo a skill alvo fica em `<REPO>/plugins/$ARGUMENTS/`.

## ANTES DE EDITAR — atualize o repo local

Sincronize o repo alvo com o remoto **antes de tocar em qualquer arquivo**. Numa
sessão real isto evitaria um push rejeitado: o clone local estava atrás do
`origin/main` (outra máquina/CI havia empurrado commits), então o `git push`
falhou e exigiu fetch+rebase no meio do caminho — com o commit já feito sobre
uma base defasada.

No repo onde o commit vai cair (o marketplace no modo completo; o repo da skill
no modo enxuto):

```bash
git fetch origin
git status -sb                      # veja se aparece "behind N"
# Se a árvore estiver "suja" só por artefatos de migração Windows→WSL
# (working tree CRLF vs blobs LF; /mnt/c entrega arquivos 0777), confirme que
# NÃO há mudança real antes de limpar:
git diff --ignore-cr-at-eol --stat  # vazio = só line-ending, seguro
git config core.fileMode false      # silencia o ruído de permissão 0777
git checkout -- .                   # restaura os blobs LF (só se o diff acima for vazio)
git merge --ff-only origin/<branch> || git rebase origin/<branch>
```

Só comece a editar depois de estar em dia (fast-forward limpo ou rebase). Assim
o commit nasce sobre o estado atual do remoto e o push final passa de primeira,
em vez de rebasear com a edição já feita.

## Fluxo

1. Liste as lições NÃO-ÓBVIAS da sessão: erros corrigidos, comportamentos
   surpreendentes, edge cases, padrões que funcionaram. Ignore trivialidades.

2. Filtre pelas que se aplicam ao escopo da skill `$ARGUMENTS`. Se nenhuma
   se aplicar, me diga e pare — não force.

3. Antes de editar, mostre: **o modo escolhido (enxuto/completo)** + arquivos
   a mudar + resumo do diff + tipo de bump (patch/minor/major — só no modo
   completo) + justificativa. Espere minha confirmação.

4. Após eu confirmar:

   **Modo completo (skill no marketplace):**
   - Edite os arquivos da skill (`commands/*.md`, `skills/**`, `references/**`).
   - Bump de versão em `plugin.json` e no `metadata.version` do comando/skill.
   - Entrada em `CHANGELOG.md` da skill com a data de hoje, explicando O QUÊ
     e POR QUÊ (a lição que motivou).
   - Atualize `<REPO>/.claude-plugin/marketplace.json` (versão espelhada +
     descrição/keywords se relevante).
   - Atualize `<REPO>/README.md` (tabela de plugins) se a mudança afeta como
     a skill é descrita/versionada.
   - Rode `python scripts/validate-versions.py` e corrija o que apontar.
   - Commit: `feat|fix($ARGUMENTS): vX.Y.Z — <resumo>` (com Co-Authored-By
     do Claude). Push pra origin/main.

   **Modo enxuto (skill local de outro repo):**
   - Edite os arquivos da skill na pasta local (`SKILL.md`, `references/**`).
   - Adicione/atualize um `CHANGELOG.md` dentro da pasta da skill com a data
     de hoje, explicando O QUÊ e POR QUÊ. Se a skill não tem versionamento,
     não invente `plugin.json`/bump — só registre a lição.
   - Commit NO REPO onde a skill vive: `feat|fix($ARGUMENTS): <resumo>` (com
     Co-Authored-By do Claude). Push só se o usuário pedir.
   - NÃO toque em `marketplace.json`, no README do marketplace, nem em versões
     do marketplace.

## Mantenha a descrição ENXUTA (triggering)

A `description` (frontmatter do SKILL.md + `plugin.json` + `marketplace.json`) é a **superfície de triggering** — é só por ela (e pelo nome) que o Claude decide invocar a skill. Um retrofit não pode deixá-la inchar:

- **Não vá só anexando** a lição de cada versão na descrição — é assim que ela vira um paredão de 1000+ chars. Detalhe vai para `references/**` e para a linha do README; a descrição fica curta.
- **Alvo ~350–500 chars** (teto ~700 só se a skill for genuinamente complexa). Descrições longas demais diluem o sinal e podem ser **silenciosamente cortadas** na lista `/skills`, o que PIORA o triggering.
- Se o retrofit empurrar a descrição além do teto, **enxugue em vez de só somar**: comece com UMA frase do que a skill faz, mantenha 1–2 diferenciais distintivos, e termine com um `Triggers —` compacto (≤8 frases/keywords, não um dump de palavras).
- **Espelhe a MESMA descrição enxuta** nos três lugares (SKILL.md, `plugin.json`, `marketplace.json`).

## Editando `marketplace.json` com segurança

Ele lista TODOS os plugins, cada um com seu próprio `"description"`/`"version"`. Ao editar programaticamente, **escope ao bloco do plugin alvo** — um match ingênuo em `"description":` (ou `sed` global) atinge as descrições de todos os plugins e as sobrescreve. Localize o bloco pelo `"name": "$ARGUMENTS"` e só então troque `version`/`description` dentro dele; depois confirme que as demais entradas ficaram intactas (ex.: contar descrições distintas) e rode `python -m json.tool` antes de commitar.

Não invente lições pra justificar uma mudança.
