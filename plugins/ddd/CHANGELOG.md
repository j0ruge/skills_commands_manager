# Changelog — ddd

Formato: [Semantic Versioning](https://semver.org/)

## [0.4.0] - 2026-04-15

### Added — 2 novas references (fechando gaps IMPORTANTES da re-auditoria)

- `references/bounded-context-canvas.md` — template completo + guia de preenchimento do BC Canvas (DDD Crew v5): purpose, strategic classification (domain type + business model + evolution stage), domain roles, ubiquitous language sample, business decisions, inbound/outbound communication, assumptions/constraints. Inclui roteiro de sessão (60-90 min) e armadilhas.
- `references/ddd-crew-process.md` — sequência canônica de 6 fases (Big Picture → Domain Message Flow → BC Canvas → Context Map → Design Level → ADRs+implementação) com cadência realista (~4 semanas pra um ERP greenfield) e critérios de transição entre fases. `[DDD Crew]` `[Distilled cap.4-5]`

### Changed — 6 expansões em references existentes

- `tactical-patterns.md` — nova seção completa "Specification Pattern" (definição Evans com 3 usos: validation / selection / building-to-order; agnóstico com composição and/or/not; uso em Repository queries; Factory + Specification; armadilhas); nova seção "Identity Generation Strategies" (4 estratégias — user-provided/application/persistence/value-generated; guia de decisão UUID vs ULID vs sequence; multitenancy; armadilhas de ID primitivo) `[Evans DDD cap.9]` `[IDDD cap.5, 7]`
- `application-services.md` — §6 completamente reescrita e expandida: Saga Orchestration vs Choreography (quando usar cada, vantagens/desvantagens detalhadas), distinção Process Manager vs Saga, 3 padrões de compensação (backward recovery / forward recovery / pivot transaction), retries com backoff + idempotency key + dead-letter, event replay e recuperação, exemplo agnóstico de Saga com estado persistente, 5 armadilhas frequentes `[IDDD cap.4, 8]` `[microservices.io]`
- `event-storming.md` — nova seção "Domain Message Flow Modelling" (objetivo, notação sequence-diagram, template Mermaid, roteiro de 90-120 min com 6 passos, integração com BC Canvas / Context Map / Design Level, armadilhas) `[DDD Crew]` `[Distilled cap.4]`
- `acceleration-tools.md` — nova seção "DDD + Agile frameworks" (Scrum com DDD + anti-padrão Task-Board Shuffle, Kanban com DDD, No Estimates — quando faz sentido); nova seção "Knowledge Acquisition Cycles" (iteração 1-4h: scenario → modelagem → refinement com expert → código → feedback, por que ciclos e não fase única) `[Distilled cap.7]`
- `context-mapping.md` — expansão da seção "REST pull vs. Messaging push" com implementação detalhada (Atom feed, cursor persistido); nova seção "Wire formats — trade-offs rápidos" (JSON, JSON Schema/OpenAPI, Protobuf, Avro, XML — quando cada um); nova seção "RPC e temporal coupling" (sinais, alternativas async-first, quando RPC síncrono ainda vale) `[Distilled cap.4]`
- `glossary.md` — Specification expandido com os 3 usos Evans; novas entradas: Bounded Context Canvas, Domain Message Flow Modelling, DDD Crew Starter Process, Process Manager, Saga Orchestration/Choreography, Compensating Transaction, Identity Generation Strategy, ULID, Task-Board Shuffle, Knowledge Acquisition Cycle, Temporal Coupling, Wire Format

### Changed — SKILL.md v0.4.0

- Version bump: `metadata.version: 0.4.0`
- Mode 1 (Analysis): atualizado para mencionar Specification Pattern + Identity Generation (tactical-patterns) e Saga/compensating (application-services) e wire formats/temporal coupling (context-mapping)
- Mode 2 (Strategic): adicionadas `ddd-crew-process.md` e `bounded-context-canvas.md` à lista carregável
- Mode 3 (Spec): adicionadas `ddd-crew-process.md` e `bounded-context-canvas.md`
- Mode 4 (Teaching): tabela de roteamento expandida com triggers para Specification, Identity Generation, Wire Formats, Temporal Coupling, Domain Message Flow, BC Canvas, DDD Crew Process, Scrum/Kanban+DDD, No Estimates, Knowledge Acquisition Cycles, Saga orq/coreografia, Process Manager, Compensating Transactions
- Nova subseção "Deliberadamente fora de escopo (v0.4.0)" explicita: Wardley Maps, DDD funcional puro, ORM details, DI debate, hiring

### Créditos adicionais em v0.4.0

- DDD Crew (Nick Tune, Marco Heimeshoff, Krisztina Hirth, Gienah Trystan) — Bounded Context Canvas, Domain Message Flow Modelling, Starter Process
- Woody Zuill / Vasco Duarte — movimento No Estimates (citado em acceleration-tools)
- microservices.io (Chris Richardson) — Saga patterns / Process Manager

### Motivação

Re-auditoria paralela com 4 agentes (1 por markdown bruto em `~/repos/jrc-manual-rag/processed/markdown/`: Evans Referência, Evans Rápido, Vernon IDDD, Vernon Distilled) reportou convergência sobre 12 gaps residuais pós-v0.3.0:

**CRÍTICO convergente (Evans Ref + Rápido + IDDD):**
1. Specification Pattern — só mencionado em glossary, sem implementação

**IMPORTANTE (múltiplos livros):**
2. Bounded Context Canvas — mencionado em v0.3.0 sem template
3. DDD Crew Starter Process — fluxo consolidado 6 fases ausente
4. Domain Message Flow Modelling — lacuna entre Big Picture e Design Level
5. Saga orquestração vs coreografia + compensating patterns detalhados — v0.3.0 tinha parágrafo único
6. Identity Generation Strategies — ausente (IDDD cap.5 dedica capítulo)
7. Conceptual Contour em profundidade — presente mas superficial
8. Model Integrity 4 pilares — já coberto, reforço cross-reference
9. DDD + Agile cadence (Scrum/Kanban + No Estimates + Task-Board Shuffle warning) — Distilled cap.7
10. Knowledge Acquisition Cycles — ciclo iterativo formal

**NICE-TO-HAVE (Distilled cap.4):**
11. Closure of Operations exemplo concreto
12. RPC temporal coupling + Atom Feed + Wire Formats

v0.4.0 fecha os 10 IMPORTANTES/CRÍTICOS + 2 NICE-TO-HAVE. Cobertura esperada ≥ 95%.

### Deliberadamente fora de escopo (v0.4.0)

Consolidado também em SKILL.md:
- **Wardley Maps** — não central aos 4 livros-fonte
- **DDD em linguagens funcionais puras** — não abordado nos livros canônicos
- **ORM internals (N+1, lazy proxies)** — tema de stack, não de DDD
- **Service Locator vs Dependency Injection debate** — arquitetura geral
- **Hiring & Team Composition** — tema RH

Mantidas também as exclusões de v0.3.0: Large-Scale Structure patterns, SaaSOvation narrativo, analogias didáticas exaustivas, fallback com livros embutidos.

## [0.3.0] - 2026-04-14

### Added — 4 novas references (fechando gaps CRÍTICOS da auditoria v0.2.0)

- `references/acceleration-tools.md` — SWOT aplicado a DDD (passo a passo + cruzamento); metrics-based estimation a partir de artefatos de event storming (tabela evento/comando/aggregate → horas, fórmula, fator multiplicador); modeling spikes vs. modeling debt (timebox, backlog, regras); timeboxed modeling (ciclo semanal, 3 regras de ouro); checklist de aceleração `[Distilled cap.7]`
- `references/application-services.md` — 5 responsabilidades (e só elas); anatomia agnóstica; Command Handler pattern; decorators transversais (logging/audit/auth/validation/retry/transactional/metrics) com pipeline; Unit of Work lifecycle; coreografia vs orquestração (saga) e compensating transactions; limites vs Domain Service vs Handler; antipadrões; checklist de auditoria `[IDDD cap.14, Apêndice A]` `[Fowler PoEAA]`
- `references/refactoring-and-insights.md` — 2 tipos de refatoração (técnica vs. insight profundo); gatilhos de deeper insight; breakthrough e como facilitar; 4 pilares de Model Integrity (UL preservada, Bounded Context claro, Context Map atualizado, refatoração como hábito); 9 sinais de drift; roteiro de refactoring pra DDD; supple design; CI do modelo (não só do código); checklist trimestral `[Evans DDD, Reference]`
- `references/scenarios.md` — Given-When-Then como validador de UL; 4 usos em sequência (pré-event-storming, durante design-level, acceptance tests, documentação viva); cenários bons vs ruins; scenarios como detector de conceitos implícitos; BDD vs testes unitários; template rápido por aggregate `[Distilled cap.2]`

### Changed — 7 expansões em references existentes

- `cqrs-event-sourcing.md` — nova seção "Concorrência em Event Sourcing" (optimistic check, `ConflictsWith()` pattern, retry com exponential backoff); nova seção "Snapshots" (quando, frequência, trade-offs, armadilhas); nova seção "Master/Clone replication" (write-through vs write-behind) `[IDDD Apêndice A]`
- `context-mapping.md` — nova seção "Notification pattern" completa: Notification wrapper (envelope padronizado), NotificationReader type-safe via dot notation, Custom Media Type / Published Language, estratégia v1-forward-compatible, REST pull vs messaging push, outbox obrigatório `[IDDD cap.13]`
- `tactical-patterns.md` — nova seção "Factory em profundidade" (Factory Method em AR, Abstract Factory, Domain Service como Factory / ACL, multitenancy, Factory vs Constructor vs Repository); nova seção "Repository — queries em Ubiquitous Language" (bons vs ruins, paginação, armadilhas); nova seção "Module — organização que não vira BBoM" (naming, cohesão, acoplamento acíclico, DDD vs deployment module, antipadrão "pasta por camada técnica", testes de arquitetura); nova seção "Design Flexível em profundidade" (Standalone Class, Closure of Operations, Declarative Design / Specification, Conceptual Contour com exemplos agnósticos) `[IDDD cap.9, 11, 12]` `[Evans Reference]`
- `strategic-design.md` — novo template completo do Domain Vision Statement (estrutura, exemplo Battery Lifecycle JRC, antipadrões); nova seção "Abstract Core" (quando subdomínios interagem); nova seção "Continuous Integration como pattern estratégico cross-team" `[Evans Reference]`
- `architecture-styles.md` — nova seção "DIP — coração da hexagonal" com exemplo agnóstico e reforço via testes de arquitetura; nova seção "Inbound vs Outbound Adapters com exemplos" (REST/CLI/listener/scheduler vs Repository/Publisher/HTTP client/Clock); nova seção "REST como estilo arquitetural" (resources orientados a caso de uso, HATEOAS, content negotiation, errors semânticos, comparativo REST/gRPC/GraphQL) `[IDDD cap.4]`
- `event-storming.md` — nova seção "Por que funciona — tátil, rápido, barato" (acessibilidade pedagógica preservada do Distilled); nota de integração com scenarios `[Distilled cap.7]`
- `glossary.md` — entrada dupla "Linguagem Ubíqua / Linguagem Onipresente" (ambas variantes pt-BR aceitas); novas entradas: Notification, NotificationReader, Unit of Work, Snapshot, Modeling Spike, Modeling Debt, SWOT (em DDD), Scenario (Given-When-Then), Deeper Insight, Breakthrough

### Changed — SKILL.md v0.3.0

- Mode 1 (Analysis): adicionadas `application-services.md` e `refactoring-and-insights.md` à lista de references carregáveis
- Mode 2 (Strategic): adicionadas `acceleration-tools.md`, `scenarios.md`, `refactoring-and-insights.md`
- Mode 3 (Spec): adicionadas `application-services.md`, `acceleration-tools.md`, `scenarios.md`
- Mode 4 (Teaching): tabela de roteamento expandida com triggers pra SWOT/estimation, command handlers/UoW, deeper insight/refactoring, scenarios/BDD, event storming, concorrência/snapshots em ES

### Créditos de autoria

Todas as references derivam-se das seguintes obras, com créditos explícitos aos autores no topo de cada arquivo:

- Eric Evans — *Domain-Driven Design: Tackling Complexity in the Heart of Software* (Addison-Wesley, 2003)
- Eric Evans — *Domain-Driven Design Reference: Definitions and Pattern Summaries*
- Eric Evans — *Domain-Driven Design Rápido* (tradução pt-BR)
- Vaughn Vernon — *Implementing Domain-Driven Design* (Addison-Wesley, 2013)
- Vaughn Vernon — *Domain-Driven Design Distilled* (Addison-Wesley, 2016)
- Martin Fowler — *Patterns of Enterprise Application Architecture* (Unit of Work)
- Dan North / Liz Keogh — Behavior-Driven Development / Given-When-Then
- DDD Crew, Alberto Brandolini (EventStorming), Nick Tune, Kamil Grzybek, Oskar Dudycz, microservices.io — práticas contemporâneas 2020-2026

### Motivação

Auditoria de cobertura (skill v0.2.0 vs. 4 markdowns brutos dos livros-fonte) com 4 agentes paralelos reportou ~72% de cobertura média. Gaps CRÍTICOS identificados: ES concurrency/snapshots, Application Services em profundidade, Notification pattern, Distilled cap.7 (acceleration tools), Refatoração pra insight profundo + Model Integrity. Gaps IMPORTANTES: Factory detalhado, Module detalhado, Repository UL queries, Domain Vision template, Abstract Core, Scenarios. v0.3.0 fecha todos. Expectativa: cobertura ≥ 90%.

### Deliberadamente fora de escopo

- **Knowledge Level, Evolving Order, Pluggable Component Architecture** (Large-Scale Structure patterns) — mantidos só em glossário; raros em prática moderna
- **SaaSOvation case study narrativo do Vernon** — skill é agnóstica por design
- **Tradução sistemática de analogias didáticas do Distilled** — skill é referência, não tutorial; preservamos uma (event storming "tátil, rápido, barato")
- **Fallback com livros completos embutidos** — skill fornece síntese densa com créditos; consulta ao livro original continua sendo a profundidade máxima

## [0.2.0] - 2026-04-14

### Added

- `references/domain-events-catalog.md` — naming conventions (past tense, entity+verb, específico vs genérico), estrutura de payload (campos obrigatórios, dados essenciais), categorias (lifecycle, state transition, attribute change, integration events), outbox pattern, schema evolution, checklist de revisão de evento, template de catálogo por contexto
- `project-conversion-spec.md`: novo **template enxuto de 1 página** como alternativa ao completo, com matriz de quando usar cada variante
- `code-review-heuristics.md`: apêndice com **snippets bom/ruim agnósticos** cobrindo anemic vs rich domain, primitive obsession, referência de aggregate por ID, repository collection-like, domain events específicos, application service fino, ACL vs vazamento de contexto

### Changed

- SKILL.md (v0.2.0): Mode 1 (Analysis) e Mode 3 (Spec) agora referenciam `domain-events-catalog.md`; Mode 4 (Teaching) tabela expandida de roteamento para referência temática; Mode 3 sinaliza escolha entre template enxuto e completo

### Motivação

Validação aplicada no projeto `validade_bateria_estoque` revelou: (a) subagentes precisaram improvisar naming/estrutura de domain events (inconsistência); (b) spec completa é overkill pra casos pequenos; (c) heurísticas de review ficam mais úteis com exemplos concretos lado a lado.

## [0.1.0] - 2026-04-14

### Added

- Primeira versão da skill DDD
- SKILL.md com roteamento por intenção (analysis / strategic / spec / teaching) e padrão de fan-out via subagentes
- Referências temáticas em `references/`:
  - `glossary.md` — glossário canônico Evans (PT-BR / EN)
  - `strategic-design.md` — Bounded Context, Ubiquitous Language, Subdomains, Core Distillation
  - `context-mapping.md` — 9 padrões de integração entre contextos
  - `tactical-patterns.md` — Entity, VO, Aggregate, Service, Repository, Factory, Domain Event, Module
  - `aggregate-design-rules.md` — as 4 regras de Vernon em profundidade + split/invariantes
  - `event-storming.md` — Big Picture / Process / Design Level, formato remoto
  - `cqrs-event-sourcing.md` — quando adotar, quando evitar, erros comuns
  - `architecture-styles.md` — Layered, Hexagonal, Modular Monolith, Microservices, Event-Driven
  - `legacy-migration.md` — Bubble Context, Strangler, ACL, abordagem faseada para ERP
  - `code-review-heuristics.md` — checklists agnósticos pra auditoria de codebase
  - `project-conversion-spec.md` — template de spec de conversão para DDD
  - `modern-practices.md` — nuances pós-2020 (distributed monolith, DDD Crew, PT-BR)

### Fontes

- Eric Evans — *Domain-Driven Design: Reference* (tradução PT-BR)
- Eric Evans — *Domain-Driven Design Rápido* (tradução PT-BR)
- Vaughn Vernon — *Implementing Domain-Driven Design* (2013)
- Vaughn Vernon — *Domain-Driven Design Distilled* (2016)
- DDD Crew, ContextMapper, EventStorming.com, Nick Tune, Brandolini, microservices.io (pesquisa web abr/2026)
