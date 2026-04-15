# Application Services — orquestração, Command Handlers, Unit of Work

> **Fontes:** Vaughn Vernon, *Implementing Domain-Driven Design* (Addison-Wesley, 2013), cap. 4 (Architecture), cap. 14 (Application), Apêndice A (Aggregates + Event Sourcing). Martin Fowler, *Patterns of Enterprise Application Architecture* (Unit of Work). `[Evans Reference]` — Layered Architecture.
> Créditos de conteúdo original aos autores. Esta reference é síntese em pt-BR organizada para consulta dentro da skill DDD.

Application Service é a camada mais subestimada de DDD. Quando mal feita, toda lógica acaba vazando pra ela (anemic domain model) ou pro controller (smart UI). Feita bem, ela é **fina, óbvia, e completamente desinteressante** — o que é exatamente o objetivo.

---

## 1. Responsabilidades (e só elas)

`[IDDD cap.14]`

Application Service faz **somente** estas 5 coisas:

1. **Receber** um comando (DTO/record/POJO) ou query
2. **Carregar** agregado(s) via Repository
3. **Invocar** comportamento no agregado (domínio decide)
4. **Persistir** via Repository
5. **Publicar** Domain Events (via outbox ou publisher)

Tudo isso dentro de **uma transação** controlada explicitamente.

### O que Application Service NÃO faz

- ❌ Lógica de negócio (isso é Entity/Aggregate/VO/Domain Service)
- ❌ Validação de regra de domínio (é do aggregate; service só valida *shape* do comando)
- ❌ Queries complexas com lógica (é CQRS — read model próprio)
- ❌ HTTP / serialização / UI (é adapter inbound)
- ❌ SQL ou ORM vazando (é Repository)

**Teste:** leia o Application Service em voz alta. Se soa como "carrega, delega, salva, publica", está certo. Se soa como "se-então-senão-calcula", lógica vazou.

---

## 2. Anatomia de um Application Service

Pseudocódigo agnóstico:

```
class ConfirmOrderAppService {
  dependency OrderRepo repo
  dependency EventPublisher events
  dependency Clock clock

  Result execute(ConfirmOrderCommand cmd) {
    transaction {
      Order order = repo.findById(cmd.orderId)
                        .orElseThrow(OrderNotFound)

      // domínio decide, service só convoca
      order.confirm(cmd.actorId, clock.now())

      repo.save(order)
      events.publishAll(order.pullEvents())

      return Result.ok(order.id)
    }
  }
}
```

Elementos:
- `Command` é DTO imutável — carrega **o mínimo** que o caso de uso precisa
- Dependências injetadas via construtor (Repository, EventPublisher, Clock, talvez Policy/DomainService)
- Transação explícita (não confie em "default transactional") — o escopo da transação é a operação
- Resultado é tipo intencional (`Result`/`Either`), não void + exceção pra fluxo de negócio
- Eventos publicados **depois** do save e **dentro** da transação (ver Outbox em `cqrs-event-sourcing.md`)

---

## 3. Command Handler pattern

`[IDDD cap.14, Apêndice A]`

Padrão correlato: em vez de uma classe `Service` com N métodos, **uma classe por comando**.

### Vantagens

- SRP real: cada handler é ~15-40 linhas
- Mais testável (mock menos dependências)
- Facilita decorators (ver §4)
- Combina naturalmente com mediator (CQRS) se o time quiser

### Exemplo

```
interface CommandHandler<C, R> { Result<R> handle(C command) }

class ConfirmOrderHandler implements CommandHandler<ConfirmOrderCommand, OrderId> {
  // dependências + handle() idêntico ao exemplo anterior
}

class CancelOrderHandler implements CommandHandler<CancelOrderCommand, Void> { ... }

class PlaceOrderHandler implements CommandHandler<PlaceOrderCommand, OrderId> { ... }
```

### Quando usar

- Múltiplos use cases no mesmo contexto (> 5)
- Time quer preparar pra CQRS
- Decorators transversais úteis (auth, audit, retry, metrics)

### Quando não valer a pena

- Contexto pequeno (2-3 use cases) — classe única com métodos é ok
- Time prefere composição via funções puras (estilo funcional)

---

## 4. Decorators transversais

`[IDDD cap.14]` — concerns que NÃO pertencem ao domínio nem ao handler específico:

| Decorator | O que faz | Quando |
|-----------|-----------|--------|
| **Logging** | registra entrada/saída, duração, eventId | Sempre em produção |
| **Audit** | salva `actor + command + timestamp` em audit trail | Compliance, domínios regulados |
| **Authorization** | checa permissão antes de invocar handler | APIs multi-tenant, B2B |
| **Validation** | valida shape/constraints do command (não regra de domínio) | Sempre, na fronteira |
| **Retry** | reexecuta em erro transiente (concurrency clash, network glitch) | Handlers idempotentes |
| **Transactional** | abre/fecha transação (se não confiar no handler) | Opcional |
| **Metrics** | emite counters/histograms | Observabilidade |

### Composição

```
Pipeline:
  request
    → ValidationDecorator
      → AuthorizationDecorator
        → AuditDecorator
          → LoggingDecorator
            → RetryDecorator
              → Handler (domínio acontece aqui)
```

Stack prática: MediatR (C#), Axon (Java), inversify interceptors (TS), middleware functions em Node/Go.

### Regra

Decorators não conhecem domínio. Handler não conhece decorators. Se você precisa ler estado do command pra decidir autorização, esse concern é **Domain** (policy), não decorator.

---

## 5. Unit of Work

`[Fowler, PoEAA]` + `[IDDD cap.14]`

Unit of Work (UoW) é o objeto que rastreia mudanças em agregados durante uma operação e commita tudo de uma vez. ORMs maduros (EF Core, Hibernate, Django ORM) implementam UoW implícito.

### Lifecycle

1. `begin()` — abre transação + sessão de persistência
2. Handler carrega/modifica agregados (repository usa essa sessão)
3. `commit()` — persiste todas as mudanças + flush de outbox numa única transação do banco
4. `rollback()` em erro — abandona tudo

### Benefícios

- Um único commit por use case (performance + consistência)
- Agregado carregado 2× retorna o mesmo objeto (identity map)
- Cascata de saves controlada

### Armadilhas

- **Long-lived UoW** — passar a UoW entre use cases quebra isolamento. UoW = 1 por operação.
- **Nested transactions** — nem todo banco suporta. Design pra 1 nível.
- **Vazamento de UoW** — repository não deve receber UoW como parâmetro; deve receber do DI container.

Quando o framework não fornece UoW (pouco comum hoje), implemente `TransactionScope` mínimo ou use outbox + commit atômico.

---

## 6. Compensating Transactions e Saga

`[IDDD cap.4, 8]` `[microservices.io]` `[prática pós-2020]`

Quando um use case atravessa **múltiplos agregados ou contextos** com consistência eventual, ACID clássico não serve. Duas alternativas para coordenar: **coreografia** ou **orquestração**. A escolha define observabilidade, testabilidade e acoplamento.

### Coreografia (events encadeados)

Cada aggregate reage ao evento anterior e emite o próximo. Sem coordenador central.

```
OrderPlaced → [Inventory reage] ItemsReserved → [Payment reage] PaymentCaptured → [Shipping reage] ShipmentScheduled
```

**Quando usar:**
- Fluxo linear e estável (raramente muda ordem)
- Poucos passos (3-4)
- Times independentes (cada BC reage sem conhecer o todo)

**Vantagens:** baixo acoplamento, evolução local, nenhum SPOF.

**Desvantagens:**
- Fluxo implícito — documentação obrigatória (diagrama ou event-flow map)
- Debug distribuído — trace distribuído é pré-requisito
- Mudar ordem ou inserir passo novo exige coordenação entre múltiplos times
- Difícil responder "em que passo estamos?"

### Orquestração (Process Manager / Saga)

Um componente central (Process Manager, Saga, Workflow) comanda a sequência. É Entity persistente com estado próprio.

```
OrderSaga (estado: STARTED → ITEMS_RESERVED → PAID → SHIPPED → DONE):
  on OrderPlaced → send(ReserveItems to Inventory)
    on ItemsReserved → send(CapturePayment to Payment)
      on PaymentCaptured → send(ScheduleShipment to Shipping)
        on ShipmentScheduled → mark DONE, emit OrderFulfilled
  on any failure at step N → trigger compensation path
```

**Quando usar:**
- Fluxo com variações/condicionais ("se é cliente VIP, pula aprovação manual")
- 5+ passos ou convergência de múltiplos eventos
- Auditoria regulatória exige "timeline explícita" do processo
- Time precisa responder "em qual passo está a ordem X?" em produção

**Vantagens:** fluxo explícito, fácil mudar, estado observável, timeout trivial.

**Desvantagens:**
- Componente central (mas *não* SPOF se persistido e replicável)
- Acoplamento: Saga conhece N serviços; serviços conhecem só seus próprios eventos

### Process Manager vs. Saga (nomenclatura)

Na prática moderna os termos se confundem. Distinção útil:

- **Saga (strict)** — sequência de transações locais + compensações. Origem: paper de Garcia-Molina 1987.
- **Process Manager** — Entity com estado que **reage** a eventos e emite commands. Padrão do `[IDDD cap.8]`.

Process Manager é a **implementação** mais comum de Saga hoje. Use "Saga" se quer ênfase em compensação; "Process Manager" se quer ênfase em fluxo.

### Compensating Transactions

Em consistência eventual não existe rollback. Em caso de falha no passo N, **compense logicamente** os passos 1..N-1: `ItemsReleased`, `PaymentRefunded`, `ShipmentCancelled` — eventos que revertem o efeito anterior.

**Não é undo** — é *novo* evento de negócio, com seu próprio significado auditável. Na contabilidade não se apaga lançamento: emite-se estorno.

### Padrões de compensação

| Padrão | Quando |
|--------|--------|
| **Backward recovery** | Falhou no passo N → compensa 1..N-1 e reporta falha ao cliente. Default. |
| **Forward recovery** | Falhou no passo N → retry; só compensa se retry esgotou. Uso: idempotent ops com transiente alto (rede). |
| **Pivot transaction** | Ponto de não-retorno: depois dele, só forward recovery. Ex.: depois de `PaymentCaptured`, não compensa — retry ou escala pra humano. |

### Retries, idempotência e dead-letter

- **Retry com backoff exponencial** — padrão em step transiente. Teto (5-10 tentativas) + jitter pra não sobrecarregar.
- **Idempotency key** — cada command carrega ID único; handler rejeita duplicata silenciosamente.
- **Dead-letter queue** — após retries esgotados, mensagem vai pra DLQ + alerta operacional. Nunca "fire and forget".
- **Timeouts explícitos no Saga** — passo sem resposta em T minutos → compensação ou escalada. Não confie só no broker.

### Event Replay e recuperação

Saga persiste estado. Em crash, recarrega estado do storage e retoma. Com Event Sourcing, o próprio stream de eventos do Saga reconstrói o estado.

Regra: **commands do Saga são idempotentes** ou carregam idempotency key. Replay não deve duplicar efeitos.

### Agnóstico — Saga mínimo

```
class OrderSaga {
  readonly OrderSagaId id
  OrderSagaState state = STARTED
  OrderId orderId
  Map<Step, StepResult> history = {}

  void on(OrderPlaced ev) {
    assert state == STARTED
    orderId = ev.orderId
    send(new ReserveItems(ev.orderId, ev.items), correlationId: id)
    state = AWAITING_INVENTORY
  }

  void on(ItemsReserved ev) {
    assert state == AWAITING_INVENTORY
    history.put(INVENTORY, SUCCESS)
    send(new CapturePayment(orderId, ev.total), correlationId: id)
    state = AWAITING_PAYMENT
  }

  void on(PaymentFailed ev) {
    assert state == AWAITING_PAYMENT
    history.put(PAYMENT, FAILED)
    send(new ReleaseItems(orderId), correlationId: id)  // compensação
    state = COMPENSATING
  }

  void on(ItemsReleased ev) {
    assert state == COMPENSATING
    state = ABORTED
    emit(new OrderAborted(orderId, reason: "payment failed"))
  }

  // ... timeouts, demais passos
}
```

### Armadilhas

- **Saga "distribuído se acha que ACID"** — expectativas erradas de rollback. Comunique explicitamente: consistência é eventual, compensação é novo evento.
- **Saga síncrono (aguarda response in-process)** — vira chamada RPC encadeada. Use messaging assíncrono.
- **Compensação impossível** — alguns efeitos não reverter (e-mail enviado). Desenhe o fluxo pra que esses passos venham **depois** do pivot.
- **Saga God Class** — 40 estados, 80 handlers. Quebre por subworkflow ou volte pra coreografia.
- **Sem timeout** — passo "travado" fica pra sempre. Todo estado de Saga tem TTL.

---

## 7. Application Service vs. Domain Service vs. Handler — limites claros

Confusão mais comum. Regra de decisão:

| Tem que orquestrar transação, carregar/salvar agregado, publicar evento? | → **Application Service** |
| Tem lógica de negócio que envolve 2+ agregados sem dono natural em nenhum deles? | → **Domain Service** |
| É comportamento de 1 agregado que envolve invariantes daquele agregado? | → **Método do Aggregate** |
| É validação de shape do input (campo não-nulo, formato)? | → **Validação no Command** (VO ou decorator) |
| É autorização/auditoria/logging? | → **Decorator** |
| É query de leitura complexa com múltiplas projeções? | → **Read Model (CQRS query side)** |

Se está confuso, escreva o teste unitário: **o que precisa mockar?** Se muitos mocks + muita lógica, está no lugar errado.

---

## 8. Antipadrões frequentes

- **Fat Application Service** — 400 linhas com if/else. Lógica vazou do domínio. Mova comportamento pra Entity/Aggregate.
- **Application Service chamando outro Application Service** — cria acoplamento transversal. Use Domain Event ou Process Manager.
- **Exception-driven flow** — lançar exceção pra controlar fluxo de negócio. Use `Result<T, E>` ou sum types.
- **Repository injetando serviços de aplicação** — inversão errada. Repository é infra baixa, Application Service é camada alta.
- **Transação aninhada acidental** — decorator abre transação que outro decorator também abre. Saga um nível só.
- **"Service" genérico com 30 métodos** — quebre em Command Handlers.
- **Lógica de domínio em controller HTTP** — controller é adapter inbound, deve ter 3-8 linhas (parse → command → dispatch → response).

---

## 9. Checklist de auditoria

Pra um Application Service existente:

- [ ] Cabe em < 40 linhas?
- [ ] Faz só os 5 passos? (receber, carregar, delegar, salvar, publicar)
- [ ] Controla transação explícita?
- [ ] Não tem `if`/`else` de regra de negócio?
- [ ] Dependências injetadas, não newed-up?
- [ ] Retorna tipo intencional (Result/Either), não void + exception?
- [ ] Eventos publicados dentro da transação (outbox)?
- [ ] Tem teste unitário que só mocka Repository e Publisher?
- [ ] Nome do service/handler está na ubiquitous language?

Se 2+ "não", refatore.

---

## 10. Quando Application Service é pouco — e você precisa de mais

- **Multi-contexto com eventual consistency** → adicione Process Manager / Saga (§6)
- **Regulação forte com auditoria** → adicione decorators de Audit + Event Sourcing no domínio
- **High throughput com writes concorrentes** → adicione CQRS + retry com backoff (ver `cqrs-event-sourcing.md`)
- **Integração com legado indisponível** → ACL + fallback queue (ver `legacy-migration.md`)

Application Service fino é condição necessária, não suficiente, pra essas escalas.
