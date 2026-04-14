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

## 6. Compensating Transactions e Saga (básico)

`[IDDD cap.8]` + microservices.io `[prática pós-2020]`

Quando um use case atravessa **múltiplos agregados ou contextos** com consistência eventual, ACID clássico não serve. Duas alternativas:

### Coreografia (events encadeados)

Cada aggregate reage a evento anterior e emite o próximo. Sem coordenador central.

```
OrderPlaced → [Inventory reage] ItemsReserved → [Payment reage] PaymentCaptured → [Shipping reage] ShipmentScheduled
```

Vantagens: baixo acoplamento, fluxo emergente.
Desvantagens: fluxo implícito (difícil depurar), difícil mudar ordem.

### Orquestração (Process Manager / Saga)

Um componente central comanda a sequência.

```
OrderSaga:
  on OrderPlaced → command(ReserveItems)
    on ItemsReserved → command(CapturePayment)
      on PaymentCaptured → command(ScheduleShipment)
        on ShipmentScheduled → mark saga complete
  on any step failure → emit compensating commands (ReleaseItems, RefundPayment, CancelShipment)
```

Vantagens: fluxo explícito, fácil visualizar/alterar.
Desvantagens: ponto central, precisa recuperar de falhas.

### Compensating transactions

Em consistência eventual não existe rollback. Em caso de falha, **compense logicamente**: `ItemsReleased`, `PaymentRefunded`, `ShipmentCancelled` — eventos que reverte o efeito anterior.

Não é undo — é *novo* evento de negócio, com seu próprio significado auditável.

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
