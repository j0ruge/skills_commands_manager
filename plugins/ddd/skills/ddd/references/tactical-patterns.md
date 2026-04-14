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
