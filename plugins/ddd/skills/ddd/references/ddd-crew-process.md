# DDD Crew Starter Process — sequência canônica da descoberta à implementação

> **Fontes:** `[Distilled cap.4-5]`, DDD Crew — github.com/ddd-crew (Nick Tune, Marco Heimeshoff, Krisztina Hirth, Alberto Brandolini, e outros). `[prática pós-2020]`.
> Créditos ao DDD Crew. Esta reference é síntese em pt-BR do workflow completo.

Todo mundo sabe das técnicas isoladas (event storming, context map, canvas). O valor de um "starter process" é **ordem**: o que fazer primeiro, o que fazer depois, como usar a saída de uma etapa como entrada da próxima. Sem ordem, o time roda as técnicas em paralelo e gasta o dobro.

---

## O processo em 6 fases

```
1. Big Picture Event Storming
        ↓ (candidatos a BC + eventos pivotais)
2. Domain Message Flow Modelling
        ↓ (fluxo de mensagens cross-BC)
3. Bounded Context Canvas (1 por candidato)
        ↓ (BCs com propósito + UL + integração definidos)
4. Context Map
        ↓ (patterns de integração entre BCs)
5. Design Level Event Storming (1 por BC, em paralelo)
        ↓ (aggregates + commands + policies por BC)
6. ADRs + implementação incremental
        ↓ (código que roda)
```

Duração típica pra um ERP novo de médio porte: **3-6 semanas** da fase 1 à fase 6 começando.

---

## Fase 1 — Big Picture Event Storming

**Objetivo:** mapa do negócio inteiro. **Saída:** eventos pivotais, candidatos a Bounded Context, hotspots.

**Duração:** 2-4h (pode repetir em 2 sessões).

**Participantes:** 5-15 — domain experts + devs + product + ops. **Sem** espectadores.

Ver detalhes em `event-storming.md` → "Big Picture Event Storming — passo a passo".

**Antes de passar pra fase 2:**
- [ ] Timeline de eventos consolidada (1-2 meses de operação "normal" representados)
- [ ] Pivotal events marcados (eventos que mudam o estado do mundo)
- [ ] Candidatos a BC desenhados como swimlanes
- [ ] Hotspots listados num backlog (não resolva tudo agora)

---

## Fase 2 — Domain Message Flow Modelling

**Objetivo:** tornar explícito **quem envia o quê pra quem** entre os candidatos a BC. É o "diagrama de sequência de negócio" — ainda sem tecnologia.

**Saída:** diagrama (Mermaid sequence, ou sticky notes em swimlanes) mostrando:
- Actor/BC origem
- Mensagem (Command enviado ou Event publicado)
- Actor/BC destino
- Momento temporal

Ver detalhes em `event-storming.md` → "Domain Message Flow Modelling".

**Duração:** 90-120 min.

**Antes de passar pra fase 3:**
- [ ] Todo pivotal event da fase 1 aparece no flow
- [ ] Todo cruzamento entre candidatos a BC está explicitado
- [ ] Identificou 2-3 cenários críticos (happy path + 1-2 exceções)

---

## Fase 3 — Bounded Context Canvas

**Objetivo:** para **cada** candidato a BC, preencher 1 canvas (purpose, UL, inbound/outbound, constraints).

**Saída:** N canvases (1 por BC) em markdown no repo de arquitetura.

**Duração:** 60-90 min por canvas. Se tem 5 BCs, são ~5-7h total (distribuídas em múltiplas sessões).

Ver detalhes em `bounded-context-canvas.md`.

**Antes de passar pra fase 4:**
- [ ] Todo candidato a BC tem canvas com purpose definido
- [ ] Ubiquitous language amostrada em cada canvas (5-15 termos)
- [ ] Inbound/Outbound de cada canvas **bate** com o flow da fase 2 (se não bate, volta pra fase 2)

**Sinal de problema:** canvas impossível de preencher → BC não é real → volte pra fase 1.

---

## Fase 4 — Context Map

**Objetivo:** consolidar as relações entre BCs num diagrama único, com **pattern explícito** em cada linha (ACL, OHS+PL, Customer-Supplier, Conformist, Shared Kernel, Partnership, Separate Ways).

**Saída:** 1 Context Map em Mermaid, ContextMapper DSL, ou ASCII — versionado no repo.

**Duração:** 90 min.

Ver detalhes em `context-mapping.md`.

**Antes de passar pra fase 5:**
- [ ] Cada aresta do map tem um pattern explícito (nenhuma aresta "default")
- [ ] BCs upstream/downstream estão claros
- [ ] Decisões de integração (síncrona vs assíncrona, REST pull vs messaging push) discutidas

---

## Fase 5 — Design Level Event Storming (em paralelo por BC)

**Objetivo:** transformar **cada** BC em design concreto: Aggregates, Commands, Events, Policies, Read Models.

**Saída:** por BC — lista de Aggregates com seus Commands e Events, Policies que conectam, Read Models necessários. Direto pra código.

**Duração:** 4-8h por BC (múltiplas sessões).

**Paralelismo:** se há 5 BCs e 3 times, 3 BCs podem correr em paralelo. Cuidado: **compartilhem 1 glossário** pra UL não divergir.

Ver detalhes em `event-storming.md` → "Design Level Event Storming — passo a passo".

**Antes de passar pra fase 6:**
- [ ] Cada Command mapeia a 1 Application Service + 1 método de Aggregate
- [ ] Cada Event tem consumer identificado (mesmo BC ou outro)
- [ ] Policies têm owner claro
- [ ] Hotspots resolvidos ou marcados como modeling spikes (ver `acceleration-tools.md`)

---

## Fase 6 — ADRs + implementação incremental

**Objetivo:** capturar decisões arquiteturais **antes** do código, escolher 1 BC por vez, entregar incrementalmente.

**Saída:**
- ADRs (Architecture Decision Records) — markdown curto (< 1 página) por decisão: contexto, decisão, consequências, alternativas descartadas
- 1º BC implementado end-to-end (ou bubble context no legado — ver `legacy-migration.md`)

**Incremental:**
- Escolha o BC de **maior valor + menor risco** pra começar (cruze SWOT do `acceleration-tools.md`)
- Entregue 1 Aggregate + 1 Command + 1 Event + 1 Read Model rodando em produção
- Só depois avance pro próximo Command/Aggregate ou BC

**Regra de ouro:** implementação ≠ mais workshops. Se a fase 6 está parada porque "precisa de mais event storming", algo está errado — provavelmente falta de confiança no código (testes) ou deploy arriscado.

---

## Quando pular fases

- **Projeto pequeno (1 BC, time único):** pule fase 2 (Message Flow) e fase 3 (Canvas). Vá de Big Picture → Context Map simples (auto-referência) → Design Level.
- **Migração de legado:** insira "arqueologia do legado" antes da fase 1. Big Picture sem conhecer o legado gera fantasia.
- **Greenfield de feature dentro de produto existente:** só faça fases 3, 5, 6 (canvas do novo contexto + design level + ADRs).

---

## Cadência realista

Empresa média, ERP novo, time de 8-12 pessoas, **~4 semanas** pra chegar em código:

- Semana 1: fases 1-2 (workshops intensivos)
- Semana 2: fase 3 (canvases em paralelo)
- Semana 3: fase 4 + início da fase 5 pro BC prioritário
- Semana 4: começa implementação (fase 6) enquanto fase 5 continua pros demais BCs

**Não espere** ter tudo pronto pra começar código. O primeiro BC roda enquanto outros ainda estão em design.

---

## Anti-padrões do processo

- **Pular direto pra Design Level sem Big Picture** — você vai desenhar aggregates pra um domínio que o time não entende em conjunto
- **Canvas antes do Big Picture** — canvas sem storming é ficção estruturada
- **Context Map antes dos canvases** — patterns de integração definidos sem propósito de cada BC claro degeneram rápido
- **Big Picture eterno** — se chegou no mês 2 ainda no storming, algo está errado; parta pra canvas imperfeito
- **Implementação sem ADR** — 6 meses depois ninguém lembra por que a decisão X foi tomada

---

## Integração com outras práticas

- **Acceleration tools (SWOT + estimation):** use na fase 1 pra priorizar; e na fase 6 pra decidir qual BC primeiro (ver `acceleration-tools.md`)
- **Scenarios (BDD):** escreva cenários concretos **entre** fases 1 e 2 — validam UL
- **Modeling spikes:** hotspots da fase 1 ou 5 viram spikes antes de entrar em implementação
- **Legacy migration:** em projeto de modernização, fase 0 é "arqueologia do legado" + bubble context plan

Ver também: `event-storming.md`, `bounded-context-canvas.md`, `context-mapping.md`, `acceleration-tools.md`, `legacy-migration.md`, `scenarios.md`.
