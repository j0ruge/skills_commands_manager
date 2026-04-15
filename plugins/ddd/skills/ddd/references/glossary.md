# Glossário DDD — terminologia canônica (PT-BR / EN)

Lookup rápido. Definições derivadas de `[Evans Reference]` e `[Evans Rápido]`. Quando o livro traz frase-marca literal, ela aparece entre aspas.

Convenção: cada entrada traz **termo EN** / *termo PT-BR* — definição curta — fonte.

---

## Fundamentais

- **Domain** / *Domínio* — "O aspecto da realidade sobre o qual o software é construído; o problema específico que o software resolve." `[Evans Rápido]`
- **Model** / *Modelo* — Abstração rigorosamente organizada e seletiva do conhecimento do domínio. Não é o diagrama; é a ideia que o diagrama transmite. `[Evans Rápido]`
- **Ubiquitous Language** / *Linguagem Onipresente / Linguagem Ubíqua* — Linguagem comum baseada no modelo, usada consistentemente em fala, escrita, diagramas e código dentro de um Bounded Context. Mudanças na linguagem = mudanças no modelo. *Nota pt-BR:* "Linguagem Ubíqua" é variante mais comum na comunidade brasileira; "Linguagem Onipresente" aparece na tradução oficial do Evans Rápido. Ambas aceitas. `[Evans Reference]` `[Evans Rápido]`
- **Bounded Context** / *Contexto Delimitado* — Limite explícito dentro do qual um modelo específico é aplicado. Dentro dele a linguagem e o modelo são coerentes. `[Evans Reference]` `[IDDD cap.2]`
- **Context Map** / *Mapa de Contexto* — Diagrama + narrativa que mostra os Bounded Contexts existentes e as relações entre eles. Base para estratégia realista. `[Evans Reference]`
- **Subdomain** / *Subdomínio* — Área menor do problema dentro do domínio maior. Tipos: Core / Supporting / Generic. `[Evans Reference]`
- **Core Domain** / *Domínio Principal* — Subdomínio com valor estratégico; diferencia o negócio. Recebe o melhor talento e investimento. "Defina um Domínio Principal e forneça meios para diferenciá-lo facilmente." `[Evans Reference]`
- **Supporting Subdomain** / *Subdomínio de Suporte* — Necessário pra operação, mas não diferenciador. Candidato a time menos sênior. `[Evans Reference]`
- **Generic Subdomain** / *Subdomínio Genérico* — Problema padrão resolvido em qualquer indústria (autenticação, contabilidade básica). Candidato a COTS / biblioteca. `[Evans Reference]`

---

## Strategic Design — Distillation

- **Domain Vision Statement** / *Declaração da Visão de Domínio* — Descrição curta (~1 página) do Core Domain e sua proposição de valor. `[Evans Reference]`
- **Highlighted Core** / *Núcleo Destacado* — Sinalização visível (doc de 3-7 páginas ou marcação em módulos) do que é Core vs. suporte. `[Evans Reference]`
- **Segregated Core** / *Núcleo Segregado* — Refatoração que separa fisicamente conceitos Core dos de suporte. `[Evans Reference]`
- **Abstract Core** / *Núcleo Abstrato* — Interfaces e classes abstratas expressando interações centrais entre subdomínios. `[Evans Reference]`

---

## Integração entre contextos (Context Map patterns)

- **Partnership** / *Parceria* — Dois contextos com sucesso/fracasso conjunto; coordenação explícita. `[Evans Reference]`
- **Shared Kernel** / *Núcleo Compartilhado* — Subconjunto pequeno do modelo é compartilhado e mantido em conjunto. Mudanças requerem consulta. `[Evans Reference]`
- **Customer-Supplier** / *Cliente-Fornecedor* — Upstream prioriza necessidades do downstream; testes de aceitação conjuntos. `[Evans Reference]`
- **Conformist** / *Conformista* — Downstream adota modelo upstream integralmente, sem tradução. `[Evans Reference]`
- **Anti-Corruption Layer (ACL)** / *Camada Anticorrupção* — Camada de tradução defensiva isolando o modelo local de um modelo upstream indesejável. `[Evans Reference]`
- **Open Host Service (OHS)** / *Serviço de Host Aberto* — Upstream publica protocolo padronizado para múltiplos clientes. `[Evans Reference]`
- **Published Language** / *Linguagem Publicada* — Linguagem/schema bem documentado para intercâmbio entre contextos. Frequente combinado com OHS. `[Evans Reference]`
- **Separate Ways** / *Caminhos Separados* — Contextos não se integram; duplicação local é aceitável. `[Evans Reference]`
- **Big Ball of Mud** / *Grande Bola de Lama* — Anti-padrão. Reconhecer e cercar com ACL para não contaminar adjacentes. `[Evans Reference]`

---

## Tactical (Building Blocks)

- **Entity** / *Entidade* — "Quando um objeto precisa ser distinguido por sua identidade, em vez de seus atributos, faça que isso seja essencial para sua definição do modelo." Mutável, identidade estável. `[Evans Reference]`
- **Value Object** / *Objeto de Valor* — Definido só por atributos. Imutável. Substituído, não modificado. Igualdade por valor. `[Evans Reference]`
- **Aggregate** / *Agregado* — Cluster de Entities/VOs tratado como unidade de consistência. Raiz controla acesso externo. "Permita que objetos externos mantenham referências apenas à raiz." `[Evans Reference]`
- **Aggregate Root** / *Raiz do Agregado* — Entity principal do agregado; única referenciável de fora. `[Evans Reference]`
- **Service (Domain)** / *Serviço de Domínio* — Operação de domínio que não pertence naturalmente a Entity ou VO. Stateless. `[Evans Reference]`
- **Application Service** / *Serviço de Aplicação* — Camada fina que orquestra use cases; controla transação; não contém lógica de negócio. `[IDDD cap.14]`
- **Repository** / *Repositório* — "Consultar o acesso a Agregados expressos na Linguagem Onipresente." Interface collection-like; abstrai persistência. `[Evans Reference]`
- **Factory** / *Fábrica* — Encapsula construção complexa de agregados com invariantes. `[Evans Reference]`
- **Domain Event** / *Evento de Domínio* — Registro imutável de algo significativo ocorrido no domínio. Nome em passado. `[Evans Reference]` `[IDDD cap.8]`
- **Module** / *Módulo* — Agrupamento coeso de elementos do modelo; nome faz parte da Ubiquitous Language. `[Evans Reference]`

---

## Design Flexível

- **Intention-Revealing Interface** / *Interface Reveladora de Intenção* — Nomes expressam o "porquê" (domínio), não o "como" (implementação). `[Evans Reference]`
- **Side-Effect-Free Function** / *Função Livre de Efeitos Colaterais* — Retorna resultado sem modificar estado. Essencial em VOs. `[Evans Reference]`
- **Assertion** / *Asserção* — Pós-condições e invariantes explicitadas (no código, testes ou doc). `[Evans Reference]`
- **Standalone Class** / *Classe Autônoma* — Classe sem dependências conceituais externas; reduz carga cognitiva. `[Evans Reference]`
- **Closure of Operations** / *Fechamento de Operações* — Argumentos e retorno do mesmo tipo; permite composição. `[Evans Reference]`
- **Declarative Design** / *Design Declarativo* — Comportamento expresso por configuração/anotação em vez de procedural. `[Evans Reference]`
- **Conceptual Contour** / *Contorno Conceitual* — Decomposição alinhada com divisões naturais do domínio. `[Evans Reference]`
- **Specification** / *Especificação* — Predicado de domínio que testa se um objeto satisfaz critério (`isSatisfiedBy`). Composável via `and`/`or`/`not`. Três usos (Evans): validation, selection (query), building-to-order. Detalhado em `tactical-patterns.md`. `[Evans DDD cap.9]` `[IDDD cap.5,7]`

---

## Arquitetura

- **Layered Architecture** / *Arquitetura em Camadas* — Apresentação, Aplicação, Domínio, Infraestrutura. Dependências de cima pra baixo; domínio não depende de infra. `[Evans Reference]`
- **Hexagonal / Ports & Adapters** — Domínio no centro; ports definem contratos; adapters traduzem protocolos externos. `[IDDD cap.4]`
- **CQRS** — Command Query Responsibility Segregation. Separar modelo de escrita e leitura. `[IDDD cap.4, Appendix A]`
- **Event Sourcing** — Estado derivado de sequência imutável de Domain Events. `[IDDD Appendix A]`
- **Large-Scale Structure** / *Estrutura em Larga Escala* — Padrão coeso que abrange todo o sistema (System Metaphor, Responsibility Layers, Knowledge Level, Pluggable Component Architecture). `[Evans Reference]`

---

## Conceitos pós-livros (prática contemporânea)

- **Modular Monolith** — Um deploy, múltiplos módulos com fronteiras fortes alinhadas a bounded contexts. Default recomendado para greenfield em 2025. `[prática pós-2020]` (kgrzybek, stxnext)
- **Distributed Monolith** — Antipadrão. Serviços distribuídos com acoplamento de monolito (shared DB, deploy conjunto, chamadas síncronas chatty). `[prática pós-2020]`
- **Strangler Fig Pattern** — Migração incremental: novo sistema cresce "estrangulando" o legado. `[Martin Fowler]`
- **Bubble Context** — Pequeno bounded context novo, cercado por ACL, crescendo dentro do legacy. `[Nick Tune]`
- **Saga** — Sequência de transações locais coordenada por eventos ou orquestrador, para consistência eventual entre agregados/contextos. `[microservices.io]`
- **Outbox Pattern** — Persistir evento junto com mudança do agregado na mesma transação; publicar depois. Evita perda de eventos. `[prática pós-2020]`
- **Notification** — Envelope padronizado para Domain Event publicado cross-context: typeName, version, occurredOn, eventBody, metadata. Permite consumer uniforme e schema evolution. `[IDDD cap.13]`
- **NotificationReader** — Leitor type-safe de Notification que navega por dot notation (`reader.stringValue("eventBody.orderId")`), sem exigir classe POJO espelhada do publisher. Evita acoplamento de tipos. `[IDDD cap.13]`
- **Unit of Work (UoW)** — Padrão de Fowler: objeto que rastreia mudanças em agregados durante uma operação e commita todas numa única transação. ORMs maduros implementam implicitamente. `[Fowler PoEAA]` `[IDDD cap.14]`
- **Snapshot** — Estado serializado de um aggregate em versão N, armazenado pra evitar replay de todos os eventos em Event Sourcing. Cache, nunca fonte de verdade. `[IDDD Apêndice A]`
- **Modeling Spike** — Investigação timeboxed (4-8h) pra reduzir incerteza sobre parte do domínio antes de implementar. Saída = aprendizado documentado, não código. `[Distilled cap.7]`
- **Modeling Debt** — Decisão consciente de não modelar profundamente agora, aceitando que o modelo fica raso até compensar. Tem que virar backlog explícito com nome, juros, vencimento. `[Distilled cap.7]`
- **SWOT (em DDD)** — Strengths/Weaknesses/Opportunities/Threats aplicado ao modelo de domínio e estratégia de Core Domain. Ferramenta de priorização. `[Distilled cap.7]`
- **Scenario (Given-When-Then)** — Exemplo concreto de comportamento do domínio em formato BDD. Valida ubiquitous language com domain expert antes de virar código. `[Distilled cap.2]`
- **Deeper Insight** — Refatoração do modelo motivada por descoberta de conceito implícito ou mudança de entendimento do domínio — diferente de refatoração técnica (estrutura só). `[Evans DDD]`
- **Breakthrough** — Acúmulo de insights pequenos que convergem numa mudança grande e simplificadora do modelo. Não se força; se facilita. `[Evans DDD]`
- **Bounded Context Canvas** — One-pager estruturado (DDD Crew) que define purpose, strategic classification, domain roles, ubiquitous language, business decisions, inbound/outbound, constraints de um BC. Preenche-se pós-Big Picture, antes do Design Level. Ver `bounded-context-canvas.md`. `[DDD Crew]`
- **Domain Message Flow Modelling** — Técnica DDD Crew que desenha sequência de mensagens (Commands, Events) entre BCs candidatos em swimlanes temporais. Alimenta Context Map e Canvas. Ver `event-storming.md`. `[DDD Crew]` `[Distilled cap.4]`
- **DDD Crew Starter Process** — Sequência canônica de 6 fases: Big Picture → Message Flow → BC Canvas → Context Map → Design Level → ADRs+implementação. Ver `ddd-crew-process.md`. `[DDD Crew]`
- **Process Manager** — Entity persistente com estado que reage a Domain Events e emite Commands pra coordenar workflow multi-aggregate/multi-BC. Implementação comum de Saga. `[IDDD cap.8]`
- **Saga Orchestration / Choreography** — Orquestração: componente central (Process Manager) comanda sequência. Coreografia: cada BC reage a evento anterior, sem coordenador. Escolha por explicitação de fluxo vs. acoplamento. `[microservices.io]` `[IDDD cap.4,8]`
- **Compensating Transaction** — Novo evento de negócio que reverte logicamente efeito anterior em consistência eventual. Não é undo; é estorno com significado auditável. `[Saga literature]`
- **Identity Generation Strategy** — Como gerar IDs de Aggregate: user-provided, application (UUID/ULID), persistence (auto-increment), value-generated (hash). Default moderno: ULID/UUID gerado na aplicação. Ver `tactical-patterns.md`. `[IDDD cap.5]`
- **ULID** — Universally Unique Lexicographically Sortable Identifier. 128-bit, prefixo de timestamp permite ordenação natural e index B-tree eficiente. Alternativa moderna ao UUID v4 quando ordenação importa. `[prática pós-2020]`
- **Task-Board Shuffle** — Anti-padrão: sprints entregam features (stickies movendo na board) sem avanço de modelo. Velocity alta + glossário estagnado = modeling debt invisível. Ver `acceleration-tools.md`. `[Distilled cap.7]`
- **Knowledge Acquisition Cycle** — Iteração curta (1-4h) de scenario → modelagem → refinement com expert → código mínimo → feedback. Mantém UL e modelo alinhados continuamente. Ver `acceleration-tools.md`. `[Distilled cap.7]`
- **Temporal Coupling** — Acoplamento de disponibilidade: RPC síncrono cross-BC faz incidente num contexto derrubar outros. Mitigação: async messaging, REST pull, cache local. `[prática pós-2020]`
- **Wire Format** — Formato de serialização do payload na fronteira de integração: JSON, JSON Schema/OpenAPI, Protobuf, Avro, XML. Escolha afeta evolução, tamanho e tooling. Ver `context-mapping.md`. `[Distilled cap.4]`
