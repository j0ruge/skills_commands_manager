# Tech Spec — [Nome da Funcionalidade]

- **Slug:** `[slug-kebab-case]`
- **PRD de origem:** `tasks/prd-[slug]/prd.md`
- **Data:** [AAAA-MM-DD]

## 1. Resumo da Solução

Como a funcionalidade será construída, em um parágrafo. Foque no COMO — o O QUÊ
já está no PRD e não deve ser repetido aqui.

## 2. Contexto Técnico Atual

O que já existe e será tocado: módulos, camadas, padrões locais a reutilizar.
Cite arquivos por caminho.

## 3. Componentes Novos ou Modificados

| Componente | Caminho | Novo/Modificado | Responsabilidade |
|---|---|---|---|
| | | | |

## 4. Interfaces e Modelos de Dados

Tipos, esquemas, contratos de API/IPC/eventos, mudanças de persistência.
Inclua apenas o essencial para implementar — não a implementação inteira.

## 5. Fluxo de Dados

Do gatilho ao efeito observável, passando pelos componentes da seção 3.

## 6. Pontos de Integração

Serviços, filas, storage, rotas, processos externos. Diga o que muda em cada um.

## 7. Estratégia de Erro

Falhas previstas, como são detectadas, o que o usuário vê, o que é registrado.

## 8. Estratégia de Testes

- **Unidade:** o que cobrir e onde.
- **Integração:** quais fronteiras exercitar.
- **E2E:** os fluxos que justificam o custo.
- **Comando de validação esperado:** o comando de teste do projeto.

## 9. Observabilidade

Logs, métricas ou eventos que provam que a funcionalidade está funcionando em
produção. Omita a seção se não se aplicar.

## 10. Dependências Técnicas

Bibliotecas novas ou versões alteradas, com a justificativa. Prefira o que o
projeto já usa; proponha dependência nova só com ganho claro.

## 11. Decisões e Alternativas Rejeitadas

| Decisão | Alternativa considerada | Por que foi rejeitada |
|---|---|---|
| | | |

## 12. Riscos e Premissas

Dúvidas não bloqueantes registradas aqui em vez de virarem perguntas.
