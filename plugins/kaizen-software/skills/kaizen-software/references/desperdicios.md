# Os desperdícios (Muda) no desenvolvimento de software

No Kaizen/Lean, desperdício é tudo que consome esforço sem gerar valor para quem usa o software. Os 7 desperdícios clássicos da Toyota, traduzidos para software:

| # | Desperdício | No software | Perguntas para detectar |
|---|---|---|---|
| 1 | **Superprodução** | Funcionalidades que ninguém pediu; generalização prematura; documentação que ninguém lê | "Quem pediu isso? Qual usuário/cliente real precisa disso hoje?" |
| 2 | **Espera** | Build lento, CI demorado, aguardar aprovação/feedback, ambiente que demora a subir | "Onde o trabalho fica parado esperando algo ou alguém?" |
| 3 | **Transporte** | Passagem de bastão entre pessoas/sistemas: retrabalho de comunicação, dados re-digitados, integrações frágeis entre módulos | "Quantas mãos/sistemas essa informação atravessa até virar valor?" |
| 4 | **Superprocessamento** | Over-engineering: abstração além do necessário, otimização sem medição, camadas que só repassam chamadas | "A solução é mais complexa que o problema?" |
| 5 | **Estoque** | Código escrito e não integrado (branches longas), backlog gigante, features pela metade, dívida técnica acumulada | "O que está 'pronto mas parado'? O que foi começado e nunca terminou?" |
| 6 | **Movimentação** | Troca de contexto constante, reuniões que não decidem nada, procurar informação espalhada | "Quanto tempo se perde alternando tarefas ou caçando informação?" |
| 7 | **Defeitos** | Bugs em produção, retrabalho, correção sem teste (que reabre o bug), suporte apagando incêndio | "Quanto do esforço do time é refazer o que já foi feito? Qual poka-yoke teria impedido este defeito?" |

## Mura e Muri — os irmãos do Muda

- **Mura (desnivelamento):** fluxo irregular de trabalho — semanas ociosas seguidas de crunch; sprints com 2 entregas e sprints com 20. Kaizen busca fluxo constante de incrementos pequenos.
- **Muri (sobrecarga):** exigir além da capacidade — de pessoas (horas extras crônicas) ou de sistemas (módulo que faz coisas demais, função de 300 linhas). Sobrecarga gera defeito; defeito gera retrabalho; retrabalho gera mais sobrecarga.

## Como usar esta referência

- **No planejamento:** percorra a tabela e confronte cada item do plano. Corte ou adie o que cair em superprodução ou superprocessamento.
- **Na revisão de código:** procure especialmente #4 (complexidade desnecessária), #5 (código morto/incompleto) e #7 (ausência de teste).
- **No diagnóstico de processo:** quando o usuário reclamar de lentidão do time ("as entregas demoram", "sempre tem retrabalho"), use a tabela como roteiro de investigação e registre os desperdícios encontrados no kaizen log, cada um com uma contramedida pequena.
