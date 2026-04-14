# Práticas DDD contemporâneas — nuances pós-Evans/Vernon

Coletado via pesquisa web abril/2026. Serve pra diferenciar "DDD do livro" de "DDD como se pratica hoje". Evans (2003) e Vernon (2013/2016) continuam fundação; o que mudou é aplicação em arquiteturas modernas e erros amplamente documentados pela comunidade.

Fontes primárias: `[DDD Crew]`, ContextMapper, kamilgrzybek.com, event-driven.io (Oskar Dudycz), Nick Tune, vfunction.com, leapcell.io, microservices.io.

---

## 1. Modular Monolith como default

**Mudança:** entre 2013-2017, muita literatura DDD ancorou em microserviços. Entre 2020-2026, a comunidade retratou: **modular monolith** é o default recomendado para greenfield.

**Razões documentadas:**
- Microserviços adicionam complexidade operacional que só compensa com maturidade ops real
- Fronteiras de bounded context ainda aprendendo — é caro mover entre serviços, barato entre módulos
- Distributed Monolith (antipadrão) é resultado mais comum de microserviços-first que microserviços funcionais

**Referência canônica:** kgrzybek/modular-monolith-with-ddd (GitHub, 12k+ stars). Stack .NET mas princípios são agnósticos.

**Para a skill:** ao recomendar arquitetura greenfield (inclusive ERP), default = modular monolith. Microserviços apenas com evidência concreta de necessidade.

---

## 2. Distributed Monolith — antipadrão mais comum em 2025

Consenso crescente em 2024-2026: "muitos microserviços são distributed monoliths disfarçados" (vfunction, merginit).

**Sintomas checklist:**
- Deploy sincronizado entre serviços
- Schema de banco compartilhado (foreign keys cruzando serviços)
- Chamadas síncronas em cadeia (A→B→C em série, latência somada)
- Pequeno PR toca múltiplos serviços
- Falha em um serviço derruba outros

**Causa raiz:** fronteiras de serviço escolhidas por **camadas técnicas** (UI-service, business-service, data-service) em vez de por **bounded context** (sales, inventory, billing).

**Remédio:** revisitar strategic design antes de criar mais serviços. Pode significar consolidar.

---

## 3. DDD Crew — processo de bootstrap comunitário

`github.com/ddd-crew`: conjunto de práticas open-source que formalizam **como começar DDD** num projeto novo ou legacy.

**Artefatos mais úteis:**
- **Starter Modelling Process** — sequência passo-a-passo de técnicas (eventstorming, message flow, bounded context canvas, context map)
- **Bounded Context Canvas** — template de 1 página pra descrever cada contexto
- **Context Mapping cheat sheet** — referência rápida de patterns com notação
- **Core Domain Charts** — priorização core/supporting/generic
- **Aggregate Design Canvas** — template de 1 página pra validar aggregate

Adote esses templates em Modo 2 (Strategic) da skill — a comunidade já convergiu neles.

---

## 4. ContextMapper — DSL e ferramenta

`contextmapper.org`: DSL textual (CML) pra modelar context maps versionáveis em Git.

**Vantagens:**
- Diagramas gerados automaticamente
- Refatorações mecânicas (splits, merges de contexto)
- Reverse engineering de código Spring Boot / Docker Compose → CML
- Análise de métricas (acoplamento, complexidade)

**Quando usar:** contextos suficientes (5+) ou mapas sendo editados com frequência. Casos simples: mermaid no markdown basta.

---

## 5. Event Storming maduro

Três sabores (Big Picture, Process Modelling, Design Level) consolidaram. O site `eventstorming.com` continua fonte canônica. Brandolini mantém o livro *Introducing EventStorming* em evolução permanente (leanpub).

**Práticas pós-2020:**
- Formato remoto viável (Miro/Mural templates). Padrão: múltiplas sessões curtas > uma sessão longa.
- Ferramentas especializadas emergiram: Qlerify, Avocado, templates dedicados em Miro.
- Brandolini ensina via `ddd.academy` (Event Storming Masterclass, Remote Modelling Workshop).

Ver `event-storming.md` pra detalhe.

---

## 6. CQRS/ES sem mística

Consenso comunitário 2024-2026 (Dudycz, Dimitrov, contextmapper):

- **CQRS não é obrigatório** — é ferramenta para casos específicos. Não adote "porque DDD".
- **Event Sourcing é ainda mais específico** — audit/compliance/temporal queries.
- **Erros comuns** documentados:
  - Eventos como CRUD disfarçado (`EntityUpdated`)
  - Schema evolution ignorada
  - Projeções acopladas ao event store
  - Sem outbox → eventos perdidos ou duplicados

Ver `cqrs-event-sourcing.md`.

---

## 7. Outbox pattern como padrão

Virou prática comum pra garantir **persistência + publicação atômica** de Domain Events.

Stack comum: aggregate.save() + outbox.insert() na mesma transação; worker separado lê outbox e publica em broker; marca como enviado.

**Implementações:**
- Manual (tabela `outbox`, worker simples)
- Debezium + CDC (lê WAL/binlog e publica em Kafka)
- Bibliotecas específicas (MassTransit, Wolverine, Axon)

---

## 8. DDD em PT-BR

Comunidade relevante:

- **Elemar Júnior** — palestras e cursos em .NET/DDD (eximiatech)
- **Eduardo Pires** — canal desenvolvedor.io, conteúdo em DDD + Clean Architecture em .NET
- **Renato Groffe** — artigos sobre DDD + microserviços
- **Leonardo Galvão** — livros e curso de arquitetura (ticolabs)
- Livros traduzidos: Evans Referência (usada como fonte desta skill), DDD Rápido
- *Implementing DDD* e *Distilled* não têm tradução oficial ampla em pt-BR em 2026 — usa-se o original

Use termos EN/PT no output (bounded context / contexto delimitado) pra acomodar leitores com referências distintas.

---

## 9. Ferramentas de análise estática e arquitetural

- **ArchUnit** (Java) / **NetArchTest** (.NET) / **deptrac** (PHP) — testes arquiteturais que verificam regras de dependência entre camadas/módulos
- **Structurizr** — DSL pra C4 Model (diagramas de arquitetura), não-DDD-específico mas complementar
- **ContextMapper** — ver item 4
- **Code clustering / dependency analysis** (gource, code maat) — descobrir fronteiras ocultas via commit patterns

Pra skill em Modo 1 (Analysis): sugerir ArchUnit-like tests como artefato de saída quando time tem modular monolith — fronteiras de módulo viram testes automáticos.

---

## 10. Tendências emergentes (observar, não prescrever)

- **Domain-Driven Transformation** (livro O'Reilly 2024, Plöd et al.) — foco em transformação de negócio, não só código
- **Wardley Mapping + DDD** — combinar evolução estratégica com decomposição de domínio
- **Team Topologies + DDD** — Conway's law sério: estrutura de times = estrutura de bounded contexts
- **AI-assisted modeling** — usar LLMs pra extrair candidatos a bounded contexts de documentos de requisitos. Prática emergente, resultados mistos — útil como primeira-passada, nunca como decisão final
- **Event modeling** (Adam Dymitruk) — alternativa/complemento a event storming, mais focado em design

---

## 11. Citações "do livro" que a comunidade hoje NUANCIA

- "Aggregate sempre pequeno" (`[IDDD cap.10]`) — ainda válido, mas a comunidade aceita agregados médios quando invariantes do negócio justificam. "Pequeno" é relativo; o que não muda: **uma invariante de negócio, um aggregate**.
- "Repository collection-like" — ainda válido pra write-side; para queries complexas, CQRS + projeções dedicadas é o caminho.
- "Domain Event síncrono in-process" (`[IDDD cap.8]`) — hoje default é **assíncrono via outbox**.
- "Microserviço por bounded context" (Vernon 2013 sugeriu) — hoje **não** é default; modular monolith primeiro.

---

## 12. Principais fontes pra atualização contínua

- **Blogs**: nick-tune.com, kamilgrzybek.com, vaughnvernon.com, verraes.net (Mathias Verraes), event-driven.io (Oskar Dudycz)
- **Comunidades**: DDD Europe (conference + talks em YouTube), Domain-Driven Design Weekly (newsletter), Virtual Domain-Driven Design
- **Talks canônicos recentes**: Nick Tune "Architectural Modernisation"; Kenny Baas-Schwegler "Collaborative Modelling"; Michael Plöd "Strategic Design"; Brandolini palestra EventStorming
- **Livros 2024-2026**: *Domain-Driven Transformation* (Plöd et al., O'Reilly), *Learning Domain-Driven Design* (Khononov, 2021 — excelente ponto de entrada moderno)

Atualize esta reference quando pegar material novo que mude consenso — especialmente em CQRS/ES e modular monolith.
