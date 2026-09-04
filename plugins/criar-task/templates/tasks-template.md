# Tasks — [Nome da Funcionalidade]

- **Slug:** `[slug-kebab-case]`
- **PRD:** `tasks/prd-[slug]/prd.md`
- **Tech Spec:** `tasks/prd-[slug]/techspec.md`

## Visão Geral

Uma linha sobre o que o conjunto de tarefas entrega quando completo.

## Tarefas Principais

| # | Título | Entregável | Depende de | Testes | Paralelizável | Status |
|---|---|---|---|---|---|---|
| 1.0 | | | — | unidade | não | [ ] |
| 2.0 | | | 1.0 | integração | não | [ ] |

Regras da tabela:

- `#` usa o formato `X.0`; as subtarefas `X.Y` ficam no arquivo individual.
- `Entregável` descreve valor verificável, não atividade ("tela lista pedidos",
  não "mexer no frontend").
- `Depende de` traz `—` quando não há dependência.
- `Status` é `[ ]` pendente e `[x]` concluída, marcado só após validação.

## Ordem de Execução

Dependências antes de dependentes. Aponte os grupos que podem correr em paralelo.

## Arquivos Gerados

- `tasks/prd-[slug]/1_task.md`
- `tasks/prd-[slug]/2_task.md`

## Premissas e Lacunas

O que ficou assumido a partir do PRD/Tech Spec e o que ainda falta responder.
