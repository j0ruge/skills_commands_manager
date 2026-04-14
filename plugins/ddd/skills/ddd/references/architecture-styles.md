# Estilos arquiteturais — escolher o alvo

Fontes: `[IDDD cap.4]`, `[Distilled cap.4]`, microservices.io, kamilgrzybek.com (modular monolith), vfunction.com (antipatterns).

Não há "arquitetura DDD oficial". DDD é sobre *modelagem* — ele se acomoda em diferentes estilos. A escolha depende de: tamanho do time, maturidade, requisitos de escala, tolerância a complexidade operacional.

---

## Default contemporâneo — Modular Monolith

`[prática pós-2020]` — consenso crescente em 2024-2026: para greenfield (inclusive ERPs), **comece com modular monolith**. Microserviços são decisão, não default.

**Definição:** um deploy único, múltiplos módulos internos com fronteiras fortes. Cada módulo = bounded context. Comunicação entre módulos por **interfaces públicas** (ports), nunca direta a classes internas.

**Regras de ouro** (kgrzybek, stxnext):
- 1 módulo = 1 top-level package/namespace
- Cada módulo tem **uma API pública** (facade, Application Services expostos)
- Modelo interno, repositories, entities — tudo **privado** ao módulo
- Módulos comunicam por:
  - Chamada síncrona via API pública (quando consistência imediata é justificada)
  - Domain Events (default, eventual consistency)
- Schema de DB lógico separado por módulo (mesmo servidor, schemas ou prefixos distintos)
- Testes validam que módulo A não importa classes internas de B

**Quando usar:**
- Greenfield de complexidade média-alta (ERP, SaaS B2B, marketplace)
- Time até ~30 pessoas
- Requisitos de escala linear, não multi-região
- Quer ter o caminho aberto para microserviços no futuro sem reescrever

**Vantagens vs. microserviços iniciais:**
- Deploy simples, transações atômicas onde necessário
- Refatoração entre módulos é barata (ainda é código no mesmo repo)
- Complexidade operacional baixa
- Evolução: se um módulo precisar virar serviço depois, a fronteira já está desenhada

**Recursos canônicos:**
- `github.com/kgrzybek/modular-monolith-with-ddd` (Kamil Grzybek)
- "Modular Monolith Primer" — kamilgrzybek.com/blog/posts/modular-monolith-primer

---

## Hexagonal / Ports & Adapters

**Definição:** domínio no centro, isolado de tudo externo. Ports definem contratos (interfaces). Adapters traduzem protocolos (HTTP, DB, messaging). `[IDDD cap.4]`

**Estrutura típica:**

```
┌─────────────────────────────────────────────┐
│   Inbound Adapters                          │
│   (REST controllers, CLI, schedulers,       │
│    message listeners)                       │
│        ↓                                    │
│   Application Layer (use cases, transação)  │
│        ↓                                    │
│   Domain Layer (aggregates, VOs, events)    │
│        ↑                                    │
│   Outbound Ports (repository interface,     │
│                    event publisher)         │
│        ↑                                    │
│   Outbound Adapters                         │
│   (ORM, message broker, HTTP client)        │
└─────────────────────────────────────────────┘
```

**Vantagens:**
- Domínio testável sem infra
- Trocar adapter (ex.: DB relacional → documento) sem tocar domínio
- Separação clara inbound (dirige o domínio) vs outbound (domínio dirige)

**Observação:** hexagonal é **compatível** com modular monolith. Cada módulo pode ser hexagonal internamente. Também é compatível com microserviços.

**Termos correlatos:** Clean Architecture, Onion Architecture — variantes com a mesma essência (dependência apontando pra dentro, domínio puro).

---

## Layered Architecture

**Definição clássica** `[Evans Reference]`:
1. **Presentation/UI**
2. **Application** (orquestração, transações)
3. **Domain** (modelo — aggregates, VOs, services, events)
4. **Infrastructure** (persistência, mensageria, integrações)

Dependências fluem de cima pra baixo. Domain **não depende** de Infrastructure (use inversion of control via interfaces).

**Use quando:**
- Projeto simples-médio
- Time se sente confortável (estrutura familiar)
- CRUD-heavy

**Limitação:** sem force de isolamento, camadas vazam. Hexagonal é uma evolução mais rigorosa.

---

## Microservices

Cada bounded context num processo/serviço independente, deploy separado, storage separado.

**Quando usar:**
- Organização já tem maturidade operacional (observability, CI/CD maduro, culturas de on-call, etc.)
- Times grandes (50+), precisam autonomia real de deploy
- Requisitos de escala/fault isolation distintos por contexto
- Negócio tolera complexidade operacional inerente

**Quando NÃO usar:**
- Greenfield com time pequeno — modular monolith primeiro
- Sem maturidade em observabilidade — debug distribuído é caro
- Transações cross-context são frequentes — vira distributed monolith
- Custo de coordenação > ganho de autonomia

### Distributed Monolith — antipadrão a evitar

`[vfunction.com, merginit.com, 2025]`

Sintomas:
- Serviços têm **deploy sincronizado** — mudar um exige mudar outros
- **Schema de banco compartilhado** entre serviços
- **Chamadas síncronas chatty** (serviço A chama B que chama C em série)
- Se B cai, A também cai
- PR pequeno toca 3+ serviços

Causas:
- Fronteiras de serviço por camada técnica (UI service / business service / data service) em vez de por bounded context
- "Microserviços" decididos antes do strategic design

**Remédio:**
1. Parar de criar serviços novos
2. Revisitar bounded contexts (strategic design)
3. Consolidar serviços que deveriam ser um só contexto
4. Introduzir Domain Events + eventual consistency onde fizer sentido

---

## Event-Driven Architecture (EDA)

Domain Events são cidadãos de primeira classe. Serviços/módulos publicam events; outros consomem. Assíncrono por default.

**Combina com:**
- Modular Monolith (eventos in-process ou via broker leve)
- Microserviços (eventos via broker — Kafka, RabbitMQ, NATS)

**Benefícios:**
- Baixo acoplamento temporal e espacial
- Auditoria natural (combinando com event sourcing ou event log)
- Escala de consumers independente

**Desafios:**
- Eventual consistency e UX (comunicar ao usuário)
- Schema evolution
- Observabilidade distribuída (correlation IDs, tracing)

---

## Matriz decisória

| Fator | Modular Monolith | Hexagonal + camadas | Microservices |
|-------|------------------|---------------------|---------------|
| Greenfield, time pequeno | ✅ default | ✅ como estrutura interna | ❌ evitar |
| ERP empresarial | ✅ | ✅ | Só se houver maturidade ops |
| Time >50, autonomia crítica | Ainda viável com múltiplos módulos fortes | — | ✅ |
| Requisitos de escala heterogênea | Ok até certo ponto | — | ✅ |
| Complexidade operacional aceita baixa | ✅ | ✅ | ❌ |

---

## Recomendação default pra ERP greenfield

1. **Modular Monolith + Hexagonal interno** como ponto de partida
2. Bounded contexts mapeiam 1:1 para módulos
3. Comunicação entre módulos:
   - Síncrona via Application Service público (quando consistência imediata justifica)
   - Assíncrona via Domain Event (default)
4. CQRS **só** em módulos onde queries forem pesadas o suficiente pra justificar
5. Event Sourcing **só** em módulos com requisito de auditoria regulatório
6. Microserviços **só depois** que um módulo tiver requisitos de escala/time que compensem extrair

Isso mantém o custo cognitivo e operacional proporcional à maturidade atual e preserva opções futuras.
