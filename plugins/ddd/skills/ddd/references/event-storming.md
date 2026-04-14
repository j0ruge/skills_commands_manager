# Event Storming — descobrir o domínio rápido

Fontes: `[Distilled cap.7]`, `[EventStorming]` (eventstorming.com, Brandolini), `[DDD Crew]`, discussões contemporâneas (ddd.academy, eventstormingjournal.com).

Criado por Alberto Brandolini. Três sabores, cada um com objetivo distinto. O time escolhe o sabor pela pergunta que quer responder.

---

## Os três sabores

| Sabor | Pergunta que responde | Escala | Duração típica |
|-------|-----------------------|--------|----------------|
| **Big Picture** | Como este negócio funciona? Onde estão os bounded contexts? | Empresa/sistema inteiro | 2-4h |
| **Process Modelling** | Como este processo específico acontece? Onde estão gargalos, decisões? | Um processo (pedido, onboarding...) | 2-4h |
| **Design Level** | Como esse processo vira software? | Um bounded context | 4-8h, múltiplas sessões |

Para um ERP novo: **Big Picture primeiro** (descobrir contextos), depois **Design Level por contexto** (cada contexto com seu time e design próprio).

---

## Convenção de cores (stickies)

A convenção padrão (stickies físicos ou digitais no Miro/Mural):

| Cor | Elemento | Escopo |
|-----|----------|--------|
| Laranja | **Domain Event** (`OrderConfirmed`, `PaymentReceived`) — verbo no passado | Todos os sabores |
| Azul claro | **Command** (`ConfirmOrder`, `ProcessPayment`) — imperativo | Process, Design |
| Amarelo | **Actor / User / Role** | Todos |
| Rosa | **External System** | Big Picture, Process |
| Lilás/Roxo | **Policy** (regra reativa: "whenever X, then Y") | Process, Design |
| Verde | **Read Model / View** | Design |
| Vermelho | **Hotspot** (problema, dúvida, risco) | Todos — sticker vermelho em cima |
| Amarelo pálido (grande) | **Aggregate** | Design |
| Linha / marker | **Bounded Context / Swimlane** | Big Picture, Design |

Fonte: `[EventStorming]`, `[Distilled cap.7]`, Brandolini EventStorming Masterclass.

---

## Big Picture Event Storming — passo a passo

**Objetivo:** ter um mapa do negócio inteiro em 2-4h para descobrir bounded contexts e eventos críticos.

**Participantes:** 5-15 pessoas. Mix crítico: domain experts + devs + product + ops/suporte. **Sem espectadores.** Sem PowerPoint.

**Setup físico:** parede 8-10m × 1.5m, papel kraft, stickies muitos.
**Setup remoto:** board infinito (Miro, Mural, Qlerify, FigJam). `[prática pós-2020]`

**Passos:**

1. **Chaos Storming (30-45min)** — cada participante escreve domain events (stickies laranja, passado) que conhece e cola na parede em aproximação temporal. Sem filtro. Objetivo: quantidade. Esperado: 50-200 stickies.

2. **Enforced timeline (30-45min)** — reorganizar em linha temporal da esquerda pra direita. Eventos simultâneos empilham verticalmente. Facilitador faz perguntas para destravar ambiguidade.

3. **Hotspots (15-20min)** — marque com vermelho tudo que é dúvida, risco, controvérsia. Discuta depois, não agora.

4. **Pivotal Events** — identifique eventos que mudam radicalmente o "estado do mundo" (`OrderPlaced`, `PaymentSettled`, `ShipmentDispatched`). Eles tendem a marcar fronteiras de contexto.

5. **Swimlanes / Bounded Context candidates** — agrupe events com marcadores pretos/linhas. Regiões com linguagem própria, actors distintos, cadência temporal diferente → candidato a bounded context.

6. **Systems & Actors (final)** — adicione rosa (sistemas externos) e amarelo (actors) só onde ajuda na clareza.

**Entregáveis:**
- Foto/export do board
- Lista de pivotal events
- Lista de candidatos a bounded context
- Lista de hotspots (backlog de descoberta)

---

## Design Level Event Storming — passo a passo

**Objetivo:** transformar um processo/contexto em design de software executável. Saída dá insumo direto para código.

**Participantes:** 3-8 pessoas do time do contexto.

**Passos:**

1. **Events + Commands** — para cada evento (laranja), quem o causa? Comando (azul) à esquerda. Quem disparou? Actor (amarelo).

2. **Aggregates** — agrupe (Command → Aggregate → Event). Aggregate (amarelo pálido grande) é a "coisa" que recebe command, enforce invariantes, emite event.

3. **Policies** — "whenever Event X, then Command Y" — políticas (roxo) conectando eventos a novos comandos. É aqui que nasce eventual consistency entre agregados.

4. **Read Models** — o que o usuário precisa ver antes de decidir comandar? Verde, posicionado perto dos commands.

5. **External Systems / Integration** — onde o contexto conversa com outros contextos/sistemas. Aqui nasce a discussão de pattern de context map (ACL, OHS, etc.).

6. **Hotspots remanescentes** — o que ainda não sabemos resolver? Backlog de descoberta.

**Saída mapeia 1:1 para código:**
- Command → Application Service method
- Aggregate → Aggregate class
- Event → Domain Event
- Policy → Domain Event handler que emite novo command
- Read Model → projeção CQRS (se CQRS aplicável)

---

## Formato remoto — realidades pós-2020

`[prática pós-2020]`

**O que funciona:**
- Board infinito (Miro/Mural/FigJam) com templates de Brandolini / DDD Crew
- Sessões mais curtas, mais frequentes (90min cada, 2-3 sessões na semana) em vez de workshop único de dia inteiro
- Facilitador separado do participante — carga cognitiva remota é maior
- Pre-workshop: glossário inicial e 1-pager de contexto
- Breakout rooms para paralelismo em grupos de 3-4

**Armadilhas:**
- "Board virou cemitério de stickies" — sem enforcing de timeline, perde poder
- Participantes com câmera off — não funciona, eventually storming é conversa
- Tentar capturar tudo digitalmente em tempo real — descarrega facilitador; use screenshot e transcrição depois
- Microfones com eco ou áudio ruim — reduz qualidade do output drasticamente

---

## Quando NÃO fazer event storming

- Domínio trivial (CRUD claro, regras óbvias) — não compensa o custo
- Time não tem domain expert disponível — storming sem expert é teatro
- Projeto já tem modelo maduro e testado em produção há tempo — faça refinements pontuais, não big-picture reset

---

## Integração com outras técnicas `[DDD Crew Starter Process]`

Sequência típica pra projeto novo (ERP ex.):
1. Big Picture Event Storming
2. Domain Message Flow Modelling (quem envia/recebe o quê)
3. Bounded Context Canvas (detalha cada candidato: propósito, domain roles, ubiquitous language, decisões)
4. Context Map (patterns entre contextos)
5. Design Level Event Storming por contexto (em paralelo)
6. ADRs (Architecture Decision Records) capturando decisões
7. Implementação incremental (bubble context ou módulo novo)

---

## Recursos canônicos

- `eventstorming.com` — site original de Brandolini
- `github.com/ddd-crew/big-picture-event-storming`
- `github.com/ddd-crew/bounded-context-canvas`
- `ddd.academy/event-storming-master-class` — curso oficial Brandolini
- `eventstormingjournal.com` — casos práticos
- Livro: Alberto Brandolini, *Introducing EventStorming* (em progresso permanente, leanpub)
