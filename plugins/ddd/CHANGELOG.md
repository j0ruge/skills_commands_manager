# Changelog — ddd

Formato: [Semantic Versioning](https://semver.org/)

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
