# Bounded Context Canvas — template e guia

> **Fontes:** DDD Crew — github.com/ddd-crew/bounded-context-canvas (Nick Tune, Gienah Trystan, Marco Heimeshoff). `[Distilled cap.4]` (Brandolini influence). `[prática pós-2020]`.
> Créditos ao DDD Crew. Esta reference é síntese em pt-BR organizada para consulta dentro da skill DDD.

BC Canvas é um **one-pager estruturado** que força o time a decidir, de forma explícita, o propósito e a identidade de um Bounded Context candidato. Nasce pós-Big Picture Event Storming, antes do Design Level. Evita o sintoma "descobrimos 7 contextos mas ninguém sabe o que cada um faz".

---

## 1. Quando preencher um canvas

- Depois do Big Picture Event Storming, para cada candidato a BC identificado
- Antes de decidir fronteira entre dois contextos que parecem se sobrepor
- Em retrospectiva trimestral: reavaliar se o canvas ainda descreve o contexto real

Não se preenche canvas de contexto genérico (autenticação compartilhada, por exemplo); só faz sentido onde há decisão de design não-trivial.

---

## 2. Seções canônicas (v5 DDD Crew)

### 2.1 Name
Nome na Ubiquitous Language. Se o time ainda debate o nome, marque hotspot — canvas não resolve.

### 2.2 Purpose
1-2 frases: **que capacidade de negócio este contexto entrega**. Não é "o que faz", é "por que existe". Teste: remova o contexto — qual capacidade some?

### 2.3 Strategic Classification
- **Domain Type:** Core / Supporting / Generic (ver `strategic-design.md`)
- **Business Model:** Revenue Generator / Engagement / Compliance / Cost Saver
- **Evolution Stage (Wardley-inspired):** Genesis / Custom / Product / Commodity

Isso define **quanto investir** no contexto. Core-Revenue-Genesis recebe top talento; Generic-Cost-Commodity provavelmente é COTS.

### 2.4 Domain Roles (arquétipos)
Classificação funcional. O DDD Crew propõe ~10 arquétipos; os mais úteis:

- **Specification:** define regras declarativas (motor de políticas, tabelas de taxa)
- **Execution:** executa transações de negócio (pedidos, faturamento)
- **Audit:** captura histórico imutável
- **Approver:** aprova/rejeita propostas (workflow)
- **Gateway:** traduz entre mundos (ACL, adapter)
- **Analysis:** agregação e relatórios (BI, read models)

Um contexto pode ter 1-2 arquétipos. 3+ = provavelmente tem fronteira errada.

### 2.5 Ubiquitous Language (amostra)
5-15 termos-chave com definição curta. Basta o suficiente pra que outro time leia e entenda do que este contexto fala.

### 2.6 Business Decisions
Decisões-chave tomadas **dentro** do contexto (commands bem-sucedidos que mudam estado relevante). Linha direta com stickies azuis do Event Storming.

Exemplos:
- "Aprovar crédito para cliente"
- "Programar despacho de pedido"
- "Calcular imposto retido"

### 2.7 Inbound Communication
O que entra no contexto:
- **Mensagens** (commands recebidos, queries)
- **Origem** (actor humano? outro BC? sistema externo?)
- **Frequência** (high-freq / low-freq)
- **Collaboration pattern:** Partnership / Customer-Supplier / Conformist (ver `context-mapping.md`)

### 2.8 Outbound Communication
O que sai:
- **Domain Events publicados** (ver `domain-events-catalog.md`)
- **Commands enviados a outros contextos** (rare — prefira events)
- **Queries feitas a outros** (quando inevitável)
- **Published Language** (se tem Open Host Service — ver `context-mapping.md`)

### 2.9 Assumptions / Constraints
Pressupostos explícitos:
- "Assume que Billing está sempre disponível"
- "SLA de 200ms p99 pra queries de Catalog"
- "Compliance LGPD: dados pessoais só aqui"

Constraints violadas em produção são a fonte #1 de incidente. Torne visíveis.

---

## 3. Template pronto pra uso

```markdown
# Bounded Context Canvas — <Nome>

## Purpose
<1-2 frases>

## Strategic Classification
- **Domain:** Core / Supporting / Generic
- **Business Model:** Revenue / Engagement / Compliance / Cost Saver
- **Evolution:** Genesis / Custom / Product / Commodity

## Domain Roles
- <arquétipo 1>: <como se manifesta aqui>
- <arquétipo 2>: <idem>

## Ubiquitous Language
| Termo | Definição |
|-------|-----------|
| <Termo> | <1 linha> |

## Business Decisions (Commands)
- <decisão 1>
- <decisão 2>

## Inbound Communication
| Mensagem | Origem | Frequência | Collaboration |
|----------|--------|------------|---------------|
| <Cmd/Query> | <BC/Actor> | high/low | ACL/CS/CF/... |

## Outbound Communication
| Mensagem | Destino | Tipo |
|----------|---------|------|
| <Event> | <broadcast/BC> | Domain Event / Command / Query |

## Assumptions & Constraints
- <pressuposto 1>
- <SLA X>
- <compliance Y>

## Open Questions (hotspots)
- <pergunta 1>
```

---

## 4. Como rodar a sessão (60-90 min por canvas)

**Participantes:** 3-6 pessoas — product, tech lead, domain expert, 1-2 devs.

**Passos:**
1. **Nome + Purpose** (15 min). Se travar aqui, pare e volte ao Event Storming.
2. **Strategic classification + Domain Roles** (10 min). Discussão forte; worth the time.
3. **Ubiquitous Language** (15 min). Termos que aparecem nos commands/events do storming.
4. **Business Decisions** (10 min). Direto dos stickies azuis.
5. **Inbound/Outbound** (20 min). Aqui nascem decisões de integração (ACL? OHS?).
6. **Assumptions/Constraints + Open Questions** (10 min). Capture hotspots pra backlog.

**Entregável:** markdown no repo de arquitetura (não em Notion). Versionado. Revisado trimestralmente.

---

## 5. Armadilhas

- **Canvas perfeito antes do código** — overengineering. Faça v0.1, implemente 1 sprint, revise.
- **Canvas sem Open Questions** — provavelmente não pensaram o suficiente. Toda decisão real tem dúvida residual.
- **Muitos arquétipos (3+ em Domain Roles)** — fronteira errada. Quebre o contexto.
- **Inbound/Outbound idêntico a outro contexto** — Partnership disfarçado ou duplicação real. Escolha explicitamente.

---

## 6. Integração com outras técnicas

- **Pré:** Big Picture Event Storming identifica candidatos; canvas preenche cada um
- **Paralelo:** Domain Message Flow Modelling (ver `event-storming.md`) detalha Inbound/Outbound
- **Pós:** Context Map agrega canvases num diagrama de relações (ver `context-mapping.md`)
- **Pós:** Design Level Event Storming por contexto usa canvas como anchor

Ver também: `ddd-crew-process.md` (sequência canônica), `event-storming.md`, `context-mapping.md`, `strategic-design.md`.
