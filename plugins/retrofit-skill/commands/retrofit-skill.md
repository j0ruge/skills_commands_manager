---
description: Captura lições aprendidas na sessão e aplica à skill informada no repo skills_commands_manager — bump de versão, CHANGELOG, marketplace.json, README, commit e push
metadata:
  version: 0.1.0
---

Invoque a skill `skill-creator` antes de qualquer outra ação nesta task —
ela orienta o processo de melhorar skills existentes. Se ela não estiver
disponível, prossiga mesmo assim e me avise.

Analise as lições aprendidas nesta sessão e aplique as relevantes à skill
`$ARGUMENTS` no meu repo de skills.

PARA LOCALIZAR O REPO:
- Primeiro tente `../skills_commands_manager` (sibling do repo atual).
- Se não existir, procure siblings com nome contendo "skills" ou "commands".
- Se ainda não achar, me pergunte o caminho. Não adivinhe.
- Confirme o caminho encontrado antes de seguir.

A skill alvo fica em `<REPO>/plugins/$ARGUMENTS/`.

1. Liste as lições NÃO-ÓBVIAS da sessão: erros corrigidos, comportamentos
   surpreendentes, edge cases, padrões que funcionaram. Ignore trivialidades.

2. Filtre pelas que se aplicam ao escopo da skill `$ARGUMENTS`. Se nenhuma
   se aplicar, me diga e pare — não force.

3. Antes de editar, mostre: arquivos a mudar + resumo do diff + tipo de
   bump (patch/minor/major) + justificativa. Espere minha confirmação.

4. Após eu confirmar:
   - Edite os arquivos da skill (commands/*.md, etc.)
   - Bump de versão em plugin.json e no metadata do comando
   - Entrada em CHANGELOG.md com data de hoje, explicando O QUÊ e POR QUÊ
     (a lição que motivou)
   - Atualize `<REPO>/.claude-plugin/marketplace.json` (versão + descrição
     se relevante)
   - Atualize `<REPO>/README.md` se a mudança afeta como a skill é
     descrita/usada
   - Commit: `feat|fix($ARGUMENTS): vX.Y.Z — <resumo>` (com Co-Authored-By
     do Claude)
   - Push pra origin/main

Não invente lições pra justificar uma mudança.
