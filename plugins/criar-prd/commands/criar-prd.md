---
description: Cria PRDs enxutos a partir de uma descrição de funcionalidade, com perguntas de clarificação, template padronizado e pesquisa web apenas quando necessária. Triggers — criar PRD, PRD, product requirements, requisitos de produto, especificação de produto, planejamento de feature.
metadata:
  version: 0.1.0
---

Você cria PRDs claros e acionáveis para produto e desenvolvimento.

<critical>Antes de gerar o PRD, faça uma única rodada com até 5 perguntas de clarificação.</critical>
<critical>Use exatamente a estrutura do template de PRD resolvido em "Entrada e Saída".</critical>

## Entrada e Saída

- **Slug:** kebab-case de segmento único, casando com `^[a-z0-9]+(-[a-z0-9]+)*$`.
  Recuse antes de montar qualquer caminho um slug que contenha `/`, `\`, `..`,
  espaço ou caractere fora desse conjunto, e peça outro.
- **Template:** use `templates/prd-template.md` do projeto quando existir; caso
  contrário use o template empacotado em
  `${CLAUDE_PLUGIN_ROOT}/templates/prd-template.md`.
- **Saída:** `tasks/prd-[slug]/prd.md`.

## Fluxo

1. Faça até 5 perguntas de clarificação cobrindo:
   - problema e objetivo mensurável;
   - usuários e fluxo principal;
   - funcionalidades principais;
   - restrições e fora de escopo;
   - UX/acessibilidade quando relevante.

2. Após as respostas, leia somente o template de PRD resolvido acima, salvo se o usuário indicar documentos específicos.

3. Pesquise na web somente se houver dependência de regra externa, legislação, mercado, API pública ou informação atual. Caso use pesquisa, cite brevemente o motivo.

4. Gere o PRD focado no O QUÊ e POR QUÊ, não no COMO:
   - requisitos funcionais numerados;
   - linguagem objetiva;
   - máximo de 2.000 palavras;
   - sem decisões de implementação detalhadas.

5. Crie o diretório e salve em `tasks/prd-[slug]/prd.md`.

6. Responda com:
   - caminho final;
   - decisões assumidas;
   - questões em aberto.

## Princípios

- PRD define resultado, escopo e restrições; implementação detalhada pertence à Tech Spec.
- Minimize ambiguidades com declarações mensuráveis.
- Não explore o repositório inteiro para criar PRD; análise técnica profunda pertence ao comando de Tech Spec.
- Não use pesquisa web por padrão.

## Checklist de Qualidade

- [ ] Perguntas de clarificação feitas e respondidas
- [ ] Slug validado como kebab-case de segmento único
- [ ] Template de PRD seguido (do projeto ou o empacotado)
- [ ] Requisitos funcionais numerados incluídos
- [ ] PRD com até 2.000 palavras
- [ ] Arquivo salvo em `tasks/prd-[slug]/prd.md`
- [ ] Caminho final informado
