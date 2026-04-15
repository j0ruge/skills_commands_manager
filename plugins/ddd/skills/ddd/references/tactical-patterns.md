# Tactical Patterns — building blocks do modelo

Fontes: `[Evans Reference]`, `[IDDD cap.5-12]`, `[Distilled cap.5-6]`.

Template uniforme por pattern: Definição → Quando usar → Sinais de má aplicação → Código agnóstico curto.

---

## Entity

**Definição canônica:** "Quando um objeto precisa ser distinguido por sua identidade, em vez de seus atributos, faça que isso seja essencial para sua definição do modelo." `[Evans Reference]`

**Quando usar:**
- Objeto tem continuidade de identidade ao longo do tempo
- Dois objetos com os mesmos atributos ainda devem ser distintos
- Ciclo de vida rastreável: criação → evolução → potencial remoção

**Sinais de má aplicação:**
- Entity com apenas getters/setters (anemic)
- Entity sem identidade estável (ID mudando)
- "Identidade" derivada de atributos mutáveis

**Agnóstico:**
```
class Order {
  readonly OrderId id;          // identidade estável
  OrderStatus status;           // atributo mutável
  Money totalAmount;            // VO

  void confirm() {              // comportamento — não é setter
    assert status == DRAFT;
    this.status = CONFIRMED;
    emit OrderConfirmed(id);
  }
}
```

---

## Value Object

**Definição:** Objeto definido apenas por atributos. Imutável. Igualdade por valor. Toda operação é side-effect-free. `[Evans Reference]`

**Quando usar:**
- Descreve, quantifica ou mede algo (Money, Address, Email, PhoneNumber, DateRange, SKU)
- Substitui uso de primitivos ("primitive obsession")
- Regras de validação/formatação pertencem a ele

**Sinais de má aplicação:**
- VO com setter — vira entity disfarçada
- Igualdade por referência — esqueceu de sobrescrever `equals`
- VO grande com mil atributos — quebre em VOs menores

**Agnóstico:**
```
class Money {
  readonly Currency currency;
  readonly BigDecimal amount;

  Money plus(Money other) {                 // side-effect-free
    assert this.currency == other.currency;
    return new Money(currency, amount + other.amount);
  }

  bool equals(Money other) {
    return currency == other.currency && amount == other.amount;
  }
}
```

**Regra de ouro Vernon** `[IDDD cap.6]`: prefira VO a Entity sempre que possível. Entities são mais caras (tracking, persistência, concorrência).

---

## Aggregate

**Definição:** Cluster de Entities e VOs tratado como uma unidade de consistência. Raiz é a única entry point externa. `[Evans Reference]`

**Regras de design detalhadas:** ver `aggregate-design-rules.md`.

**Essência:**
1. Agregados pequenos
2. Referência a outros agregados por identidade (ID), nunca por ponteiro/ref direta
3. Consistência imediata dentro do agregado; eventual fora
4. Uma transação modifica um agregado por vez

**Agnóstico:**
```
class BacklogItem {              // Aggregate Root
  readonly BacklogItemId id;
  SprintId sprintId;             // referência por ID ao Sprint (outro agregado)
  List<Task> tasks;              // Tasks só existem dentro desse agregado

  void commitTo(SprintId targetSprint) {
    assert status == SCHEDULED;
    this.sprintId = targetSprint;
    this.status = COMMITTED;
    emit BacklogItemCommitted(id, targetSprint);
  }
}

class Task {                     // Entity interna, não agregado raiz
  readonly TaskId id;
  Hours remaining;
}
```

---

## Domain Service

**Definição:** operação de domínio que não pertence naturalmente a Entity ou VO. Stateless. `[Evans Reference]`

**Quando usar:**
- Lógica que envolve 2+ agregados (ex.: transferência entre duas contas)
- Cálculo complexo que distorceria a Entity se fosse método dela
- Tradução/ACL entre contextos

**Sinais de má aplicação:**
- Domain Service é um "manager"/"handler" que deveria ser comportamento de Entity — vazamento de lógica → modelo anêmico
- Domain Service com estado

**Diferente de Application Service:** o de domínio tem LÓGICA DE NEGÓCIO. O de aplicação orquestra (transação, carrega, salva, publica eventos) sem regra própria.

---

## Application Service

**Responsabilidades:** `[IDDD cap.14]`
- Receber comando/input
- Carregar agregado via Repository
- Invocar comportamento do agregado
- Persistir + publicar eventos
- Controlar transação

**NÃO faz:** lógica de negócio, validação que devia estar em VO/Entity, queries complexas.

**Agnóstico:**
```
class CommitBacklogItemService {
  void execute(CommitBacklogItemCommand cmd) {
    transaction {
      var item = repo.findById(cmd.itemId);      // carrega
      item.commitTo(cmd.sprintId);               // delega ao domínio
      repo.save(item);                            // persiste
      events.publishAll(item.pullEvents());      // eventos
    }
  }
}
```

---

## Repository

**Definição:** interface collection-like para recuperar e persistir agregados; abstrai tecnologia de persistência. `[Evans Reference]`

**Expor:**
- `findById(id)` — por identidade
- `add(aggregate)`, `remove(aggregate)` — ciclo de vida
- Queries em linguagem de domínio (`allActiveSprintsFor(tenantId)`)

**NÃO expor:**
- Queries ad-hoc genéricas (`findByAnyField(criteria)`)
- SQL / JPQL / lambdas de persistência vazando
- Retornar projeções — use CQRS pra isso (ver `cqrs-event-sourcing.md`)

**Um Repository por Aggregate Root.** Entities internas não têm repository.

---

## Factory

**Definição:** encapsula construção complexa de agregados/VOs garantindo invariantes de criação. `[Evans Reference]`

**Use quando:**
- Construção tem várias etapas
- Requer dados externos (ex.: `TenantId` injetado)
- Cliente não deveria conhecer detalhes internos

**Pode ser:**
- Método de fábrica em Aggregate Root (`tenant.createUser(...)`)
- Classe dedicada (`OrderFactory`)
- Construtor estático (em linguagens que permitem)

Não é Repository. Factory cria novo; Repository reconstrói existente.

---

## Domain Event

**Definição:** registro imutável de algo significativo que aconteceu no domínio. Nome em passado. `[Evans Reference]` `[IDDD cap.8]`

**Emitir quando:**
- Comando bem-sucedido altera estado significativo
- Fato time-based ocorre (FiscalYearEnded)
- Outros agregados/contextos precisam reagir

**Nomenclatura:** `<Aggregate><PastVerb>` — `OrderConfirmed`, `UserPasswordChanged`, `BacklogItemCommitted`.

**Propriedades:** occurredOn (timestamp), IDs dos agregados envolvidos, dados essenciais (NÃO o agregado inteiro).

**Padrões de publicação** `[IDDD cap.8]`:
- Dentro do agregado: acumular eventos em lista
- Application Service publica após commit (ou usa Outbox pattern pra garantir atomicidade)

**Idempotência do consumer:** at-least-once delivery é o default em messaging. Consumer deve ser idempotente (guardar eventIds processados, ou usar operações commutativas).

**Agnóstico:**
```
record OrderConfirmed(
  OrderId orderId,
  CustomerId customerId,
  Money total,
  Instant occurredOn
);
```

---

## Module

**Definição:** agrupamento coeso de elementos do modelo. Nome faz parte da ubiquitous language. `[Evans Reference]`

**Regras:**
- Módulo nomeado por conceito de negócio, não técnico (`Billing` não `Services`, `Inventory` não `Entities`)
- Refatore quando o modelo evolui — módulos não são eternos
- Em modular monolith, módulo = bounded context

---

## Intention-Revealing Interface + Side-Effect-Free Function + Assertion

**Design flexível** — o tripé para modelos que aguentam evolução.

- **Intention-Revealing:** `order.confirm()` > `order.setStatus(CONFIRMED)` — o nome diz a intenção.
- **Side-Effect-Free:** VO métodos retornam novas instâncias. Entity separa queries (retornam) de commands (modificam, void).
- **Assertion:** invariantes declaradas. Se linguagem não suporta, teste unitário.

```
class BacklogItem {
  bool isReadyForSprint() { ... }        // query — sem side effect

  void commitTo(SprintId target) {        // command — side effect
    assert isReadyForSprint();            // invariant
    ...
  }
}
```

---

## Factory — em profundidade

`[IDDD cap.11]` `[Evans Reference]`

Quando construção é complexa (invariantes múltiplas, dados externos necessários, tenancy), construtor público vira armadilha. Factory resolve.

### Factory Method em Aggregate Root

Aggregate cria outro aggregate (ou Entity interna) via método de classe, protegendo invariantes de criação.

```
class Tenant extends Entity {
  User registerUser(username, password, email) {
    assert isActive();
    assert !userAlreadyRegistered(username);
    return new User(this.tenantId, UserId.generate(), username, hashOf(password), email);
  }
}

// Uso:
user = tenant.registerUser("joruge", "s3cr3t", "j@jrc.com");
```

Vantagens:
- `TenantId` automaticamente correto (sem o client esquecer)
- Validação na origem (tenant ativo?)
- Construtor de `User` fica package-private ou internal — ninguém cria User fora desse path

### Abstract Factory em hierarquias

Quando o conceito sendo criado tem múltiplas variantes com lógica de seleção:

```
abstract class NotificationFactory {
  abstract Notification create(event)
}

class EmailNotificationFactory extends NotificationFactory { ... }
class SmsNotificationFactory extends NotificationFactory { ... }
class PushNotificationFactory extends NotificationFactory { ... }

// Resolver no Application Service, não no domínio:
factory = factoryRegistry.forChannel(user.preferredChannel)
notification = factory.create(event)
```

### Domain Service como Factory

Pra integração: tradução de modelos externos em objetos locais é Factory disfarçado.

```
class CustomerTranslator {  // Domain Service + Factory
  Customer fromLegacySAP(SAPCustomerDTO raw) {
    return new Customer(
      CustomerId.from(raw.kunnr),
      CustomerName.parse(raw.name1 + raw.name2),
      new EmailAddress(raw.email.toLowerCase()),
      // mapeia só o que importa; SAP tem 200 campos, Customer tem 15
    );
  }
}
```

Isso é ACL concretizada. Ver `context-mapping.md`.

### Factory vs. Constructor vs. Repository

| Situação | Use |
|----------|-----|
| Criar aggregate novo com regras simples | Constructor |
| Criar aggregate com regras complexas / múltiplas dependências | Factory |
| Criar aggregate filho dentro de aggregate pai | Factory Method no pai |
| Reconstituir aggregate existente do storage | Repository |
| Construir VO complexo (ex.: Money com validação de currency) | Constructor + factory method (`Money.of(amount, currency)`) |

### Multitenancy — caso especial

Em SaaS multi-tenant, **todo** aggregate root carrega `TenantId`. Construtor público é perigoso — dev pode esquecer de setar, ou setar errado. Factory Method no `Tenant` garante.

### Armadilhas

- **Factory gigante** com 30 métodos — virou God Class. Quebre por tipo.
- **Factory fazendo lógica de negócio** — só devia criar. Regra complexa vai pra Domain Service.
- **Construtor público coexistindo com Factory** — confunde. Torne o construtor inacessível.

---

## Repository — queries em Ubiquitous Language

`[IDDD cap.12]` `[Evans Reference]`

Repository básico já foi coberto acima. Aqui, o detalhe que mais vaza linguagem: **os nomes dos métodos de query**.

### Nomes bons vs. ruins

| Ruim (técnico) | Bom (ubiquitous language) |
|----------------|---------------------------|
| `findByStatus("ACTIVE")` | `activeBatteries()` ou `findActiveBatteries()` |
| `findAll(predicate)` | `overdueInvoicesFor(customer)` |
| `getByCriteria(map)` | `ordersReadyForPicking()` |
| `query("SELECT ... WHERE ...")` | `allSubscriptionsExpiringIn(period)` |
| `findByAttribute("tenantId", id)` | `sprintsOf(tenantId)` |

A regra: **o nome do método deve ser lido pelo domain expert e fazer sentido sem contexto técnico**. Se precisar de explicação, está errado.

### Paginação sem quebrar UL

```
// Ruim: expõe paginação como concern técnico no nome
repo.findByStatus(status, page, size, sort)

// Bom: paginação é parâmetro opcional
repo.activeBatteries(page: Page.of(1, 50))
```

Page / Slice como VO; default sensato (primeira página, tamanho limitado).

### Quando a query é realmente complexa

Sinal de CQRS: relatórios, dashboards, multi-join complexo. **Não** polua o Repository — crie read model próprio com query side dedicada. Ver `cqrs-event-sourcing.md`.

### Armadilhas

- **Repository de Entity interna** — só existe repo de Aggregate Root. `OrderLineRepository` é anti-padrão.
- **40+ métodos findBy*** — query explosion. Considere Specification pattern ou CQRS.
- **Expor tipos ORM** (`IQueryable`, `QuerySet`, `FindOptions`) — vaza persistência. Retorne `Collection<Aggregate>` ou cursor próprio.
- **Retornar null vs. Optional vs. throw** — escolha um e seja consistente no projeto. `Optional`/`Maybe`/`Result` > null.

---

## Module — organização que não vira BBoM

`[IDDD cap.9]` `[Evans Reference]`

Module = agrupamento **conceitual** coeso. Não é só pasta; é parte do modelo.

### Naming

- **Pelo conceito de negócio**, nunca por camada técnica:
  - ✅ `sales`, `inventory`, `billing`, `compliance`
  - ❌ `services`, `models`, `controllers`, `utils`, `helpers`
- Nome faz parte da ubiquitous language
- Se o nome mudou no negócio, renomeie o module (refactoring semântico)

### Cohesão intra-module

Dentro de um module, tudo deveria ser sobre a mesma coisa. Teste: se você não consegue descrever o module em uma frase sem "e" ou "ou", ele tem dois conceitos — quebre.

### Acoplamento entre modules — acíclico

Modules podem depender um de outro (`billing` depende de `sales` pra saber de pedidos), mas nunca em ciclo (`sales` não pode também depender de `billing`).

Ciclo = sinal de **fronteira errada** entre modules, OU conceito deveria ser extraído pra um terceiro module independente.

### DDD Module vs. deployment module

- **DDD module** — conceito do modelo (`billing`, `sales`)
- **Deployment module** — unidade de build/deploy (Maven module, npm package, Go module, .NET project)

Em modular monolith, idealmente **1:1**: 1 DDD module = 1 deployment module. Facilita reforço de fronteiras via build system (não compila se `billing` importa interno de `sales`).

### Antipadrão: pasta por camada técnica

```
// Ruim
src/
  controllers/
    OrderController.ts
    PaymentController.ts
    CustomerController.ts
  services/
    OrderService.ts
    PaymentService.ts
  repositories/
    OrderRepo.ts
    PaymentRepo.ts

// Bom
src/
  sales/
    application/OrderService.ts
    domain/Order.ts
    infrastructure/OrderRepo.ts
    api/OrderController.ts
  billing/
    application/PaymentService.ts
    domain/Invoice.ts
    infrastructure/InvoiceRepo.ts
    api/PaymentController.ts
```

Primeiro agrupe por **contexto de negócio**, depois por camada técnica dentro dele.

### Testes de arquitetura

Reforce fronteiras programaticamente:

- **Java**: ArchUnit — `noClasses().that().resideInPackage("..sales..").should().dependOnClassesThat().resideInPackage("..billing..internal..")`
- **.NET**: NetArchTest
- **TS**: `dependency-cruiser` ou ESLint rules custom
- **Go**: convenções de import + custom linter
- **Python**: `import-linter`

Se o teste quebra, build quebra. Fronteira vira contrato verificável.

---

## Design Flexível em profundidade

`[Evans DDD/Reference]` — promovido do glossário pra aplicação concreta. Técnicas que tornam o modelo *supple* (aguenta evolução sem degradar).

### Standalone Class

Classe sem dependências conceituais externas. Redução máxima de carga cognitiva.

Quando buscar:
- VOs de domínio (Money, Email, DateRange)
- Algoritmos puros (cálculos matemáticos, transformações)
- Utilitários de domínio (não "utils" genérico)

Sinal: você lê a classe uma vez e entende 100% sem olhar outras. Sem herança, sem injeção, sem side effect.

```
class DateRange {  // Standalone
  readonly start: Date
  readonly end: Date

  constructor(start, end) {
    assert start <= end
    this.start = start; this.end = end
  }

  contains(date): Boolean = date >= start && date <= end
  overlapsWith(other: DateRange): Boolean = start <= other.end && end >= other.start
  daysCount(): Int = differenceInDays(end, start)
}
```

### Closure of Operations

Operações cujo argumento e retorno são do **mesmo tipo**. Permitem composição.

```
class Money {
  Money plus(Money other) = ...      // Money + Money → Money
  Money minus(Money other) = ...
  Money times(decimal multiplier) = ... // Money × decimal → Money (ainda closure em dimensão)
}

// Composição natural:
total = basePrice.plus(tax).minus(discount).times(quantity)
```

Sem closure, cada operação força conversão, verbosidade aumenta, código fica imperativo.

### Declarative Design

Comportamento expresso por configuração/regra, não código procedural.

Exemplos:
- **Specification pattern** — `new IsOverdue().and(new IsHighValue()).isSatisfiedBy(invoice)`
- **Rules engine** (quando cabe — não exagere)
- **DSL interna** — linguagem de domínio em código (Gherkin para testes, SQL pra queries)
- **Annotations/decorators** pra validação (`@Valid`, `@NotNull` com regras de domínio)

Declarative design **sem** rigor vira magia. Use quando a regra é:
- Composição natural de condições (specifications)
- Comportamento variável configurável sem deploy (rules engine limitado)
- Schema expressivo do domínio (DSL)

### Intention-Revealing Interface

Coberto acima. Princípio: nome expressa intenção de domínio, não mecânica.

### Side-Effect-Free Function

Coberto acima. Princípio: funções que retornam sem mutar.

### Assertions

Coberto acima. Princípio: invariantes explícitas, não implícitas.

### Conceptual Contour

Decomposição alinhada com divisões **naturais** do domínio, não com convenção arbitrária.

Sinal de contour bem achado: mudança no negócio afeta *um* lugar no código. Sinal de contour errado: mudança pequena toca muitos lugares.

Como achar: refatoração iterativa, aprendizado com domain expert, paciência. Não se projeta contour no dia 1.

---

## Specification Pattern

`[Evans DDD cap.9]` `[IDDD cap.5, 7]` — predicado de domínio encapsulado em objeto, composável.

### Definição

Uma Specification encapsula um **teste de satisfação** sobre um objeto: `spec.isSatisfiedBy(candidate) → bool`. O nome expressa regra de negócio; a composição (`and`, `or`, `not`) permite construir critérios complexos sem `if` aninhado.

Evans classifica 3 usos:
1. **Validation** — o objeto satisfaz critério neste momento?
2. **Selection** — selecionar coleção que satisfaz (repository query)
3. **Building-to-order** — criar objeto que satisfaz especificação

### Quando usar

- Regra de negócio reaparece em múltiplos lugares (validation, query, UI) — evita duplicação
- Critério tem variações combinatórias ("ativo E com saldo > X E sem débito pendente")
- Domain expert descreve o critério com nome próprio ("elegível pra desconto fidelidade")

### Sinais de má aplicação

- Specification com 1 uso e 1 linha de código → overengineering; método na Entity basta
- Specification chamando outro Domain Service → acoplamento escondido; provavelmente é Domain Service disfarçado
- Specification mutável ou com side effect → viola a natureza do predicado

### Agnóstico

```
interface Specification<T> {
  bool isSatisfiedBy(T candidate)
  Specification<T> and(Specification<T> other)
  Specification<T> or(Specification<T> other)
  Specification<T> not()
}

class OverdueInvoice implements Specification<Invoice> {
  bool isSatisfiedBy(Invoice inv) = inv.dueDate < clock.now() && !inv.isPaid()
}

class HighValueInvoice implements Specification<Invoice> {
  readonly Money threshold
  bool isSatisfiedBy(Invoice inv) = inv.total >= threshold
}

// Composição natural:
collectable = new OverdueInvoice()
              .and(new HighValueInvoice(Money.of(10_000, BRL)))

if (collectable.isSatisfiedBy(invoice)) {
  collectionService.enqueue(invoice)
}
```

### Specification em queries de Repository

Permite queries expressivas sem "explosão de findBy*":

```
invoices = invoiceRepo.satisfying(collectable)
// em vez de invoiceRepo.findOverdueAndHighValue(threshold)
```

Implementação pode traduzir Specification → SQL / JPQL / ORM query builder internamente (technique: double dispatch ou adapter).

### Specification + Factory (building-to-order)

Quando a criação precisa satisfazer critério:

```
class SubscriptionFactory {
  Subscription create(Customer c, Plan p, PromotionSpec active) {
    Subscription sub = new Subscription(c, p, clock.now())
    if (active.isSatisfiedBy(c)) sub.applyPromotion(active.bonus())
    return sub
  }
}
```

### Armadilhas

- **Specification-mania**: nem todo predicado precisa de classe; métodos em VO/Entity continuam válidos. Use Specification quando há reuso real ou composição.
- **Performance em Selection**: `spec.isSatisfiedBy` em loop sobre 1M de registros é desastre — mapeie pra query. Double dispatch ou Criteria API.
- **Mock-hell em testes**: Specifications puras são fáceis de testar; fique fora de dependências externas.

---

## Identity Generation Strategies

`[IDDD cap.5]` — como gerar o ID de uma Entity/Aggregate. Escolha afeta concorrência, integração, e compliance.

### 4 estratégias principais

| Estratégia | Quem gera | Quando |
|------------|-----------|--------|
| **User-provided** | Cliente da API ou domain expert | IDs naturais bem conhecidos (CPF, CNPJ, ISBN). Raro em sistemas modernos. |
| **Application (UUID/ULID)** | Camada de aplicação, **antes** do persist | Default moderno. Aggregate pode ser construído off-line; IDs únicos globalmente; merge entre sistemas trivial. |
| **Persistence (auto-increment / sequence)** | Banco, no INSERT | Legado com integer PK esperado por relatórios/FKs existentes. Bloqueia construção antes do save. |
| **Value-generated (hash de atributos)** | Função determinística de atributos | Idempotência na criação (ex.: `hash(date+amount+customerId)` evita duplicata). Risco: attrs mutáveis quebram identidade. |

### Guia de decisão

**Escolha UUID/ULID por default** se:
- Sistema novo, sem FK legada
- Integração cross-system (microservices, message bus)
- Cliente precisa gerar ID antes de chamar API (idempotency key)
- Event Sourcing (evento registra ID antes do "save")

**Escolha sequence/auto-increment** só se:
- FK integer obrigatória no schema herdado
- Ordenação por ID tem significado (raro — use timestamp explícito)
- Restrição de 4-8 bytes crítica (IoT, embarcado)

**Nunca misture** no mesmo Aggregate. IDs previsíveis em produção + UUID em teste = bug em integração.

### ULID > UUID v4 quando ordenação importa

ULID (Universally Unique Lexicographically Sortable) é 128-bit como UUID mas prefixado por timestamp. Vantagens:
- Ordenação natural por criação
- Index B-tree eficiente (inserts sequenciais)
- Mesma garantia de unicidade

UUID v7 (draft RFC) resolve o mesmo problema; verifique suporte na stack antes de adotar.

### Agnóstico — factory com UUID

```
class Order {
  readonly OrderId id          // UUID/ULID wrapper VO

  static Order place(CustomerId customer, List<Item> items) {
    assert items.nonEmpty()
    return new Order(OrderId.generate(), customer, items, status: DRAFT)
  }
}

class OrderId {
  readonly String value         // "01J5R2X..."
  static OrderId generate() = new OrderId(Ulid.random().toString())
  static OrderId from(String raw) = new OrderId(validateUlid(raw))
}
```

### Armadilhas

- **Vazar tipo primitivo** — `long id` ou `string id` no domínio. Envelope em VO (`OrderId`) pra ter tipo próprio, validação, e impedir troca acidental (`orderRepo.findById(customerId)` não compila).
- **ID mutável** — nunca. Se precisa "trocar de identidade", é outra Entity (ex.: `Invoice` substituindo `Draft`).
- **UUID em tabela com bilhões de rows sem índice adequado** — UUID v4 fragmenta B-tree; use ULID ou UUID v7.
- **Gerar ID no banco em Event Sourcing** — impossível; evento precisa do ID antes do persist.

### Multitenancy

Em SaaS multi-tenant, **todo** aggregate root carrega também `TenantId`. O ID principal (UUID) pode repetir entre tenants em princípio, mas a combinação `(tenantId, aggregateId)` é que identifica globalmente. Factory Method em `Tenant` (ver §Factory em profundidade) garante.

---

## Hierarquia de uso (agnóstica)

Quando modelar algo novo, pergunte nessa ordem:
1. Pode ser Value Object? (imutável, sem identidade)
2. Se precisa identidade, Entity?
3. Qual Aggregate root controla esse Entity?
4. Há operação que não cabe em Aggregate? → Domain Service
5. Algo mudou e outro agregado/contexto precisa saber? → Domain Event
6. Orquestração + transação + persistência? → Application Service
7. Construção complexa? → Factory
8. Persistência? → Repository (um por Aggregate Root)
