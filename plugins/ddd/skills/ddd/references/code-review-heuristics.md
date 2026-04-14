# Heurísticas de revisão DDD — checklist agnóstico

Checklist pra auditar um codebase sob a lente DDD. Cada item é um *sinal observável* — independe de linguagem/framework. Use em Modo 1 (Analysis) da skill.

Para cada achado, classifique severidade:
- **CRÍTICO**: viola invariante de domínio, causa bug em produção
- **ALTO**: degrada manutenibilidade significativamente, converge pra BBoM
- **MÉDIO**: friction, retrabalho previsível
- **BAIXO**: cosmético, padrão preferível, sem dano imediato

---

## 1. Ubiquitous Language

- [ ] Classes/métodos/tabelas usam termos do negócio? Ou técnicos genéricos (`Manager`, `Handler`, `Processor`, `Util`, `Helper`)?
- [ ] O mesmo conceito tem um só nome dentro do módulo/contexto?
- [ ] Termos se alinham com como o domain expert fala? (teste: leia o código em voz alta pro expert; ele entende?)
- [ ] Documentação reflete o código ou está desatualizada?
- [ ] Termos em inglês/português misturados sem critério?

**Red flags:** `doStuff()`, `process()`, `handle()` como nomes públicos. `CustomerManager` gerenciando coisa nenhuma. Classes terminando em `-Entity`, `-Model`, `-DTO` expostas ao negócio.

---

## 2. Entities vs Value Objects

**Entities:**
- [ ] Identidade estável, nunca muda?
- [ ] Têm comportamento (não só getters/setters)?
- [ ] Invariantes verificadas em construtor e em métodos de mutação?
- [ ] Ciclo de vida claro (criação → modificação → remoção)?

**Value Objects:**
- [ ] **Imutáveis**? (campos `final`/`readonly`/`const`; sem setters)
- [ ] Igualdade por valor (`equals` sobrescrito)?
- [ ] Operações retornam novo VO em vez de mutar?
- [ ] Não têm identidade própria?

**Primitive obsession:**
- [ ] Há `String email`, `String cpf`, `BigDecimal amount` soltos? Deveriam ser VOs.
- [ ] Validação de formato repetida em múltiplos lugares? Deveria estar no VO.

**Red flags:** `setStatus()`, `setName()`, `setAmount()` públicos em entities; VOs com `setX`; `equals()` por referência em VO; `DateTime` ou `String` representando conceitos de domínio (usar VO).

---

## 3. Aggregates

- [ ] Cada aggregate tem UM aggregate root claro?
- [ ] Acesso externo passa pelo root (Law of Demeter)?
- [ ] Outros aggregates referenciados por ID, nunca por objeto direto?
- [ ] Tamanho razoável? (carregar não traz 100+ objetos, profundidade ≤ 3)
- [ ] Invariantes declaradas no código (assertions / guards)?
- [ ] Transações tocam um aggregate por vez?
- [ ] Métodos do root retornam entidades internas ou devolvem só dados/VOs?

**Red flags:**
- Aggregate com 20+ campos ou 5+ collections
- `Order.customer.address.city` (navegação profunda entre aggregates)
- `OrderService` fazendo save em Order + Customer + Invoice na mesma transação
- ORM lazy loading cruzando aggregates — acopla sem limite

Ver `aggregate-design-rules.md` pra deep-dive.

---

## 4. Services

**Domain Services:**
- [ ] Stateless?
- [ ] Contém lógica de **domínio** (não orquestração)?
- [ ] Nome expressa ação de domínio (`TransferFunds`, não `FundsManager`)?
- [ ] Necessário mesmo? (poderia ser método de aggregate?)

**Application Services:**
- [ ] Fino? (carrega, delega, salva, publica)
- [ ] Zero lógica de negócio?
- [ ] Controla transação explicitamente?
- [ ] Recebe comandos/DTOs, não expõe entities?

**Red flags:**
- `OrderService.calculateTotal()` — deveria estar em Order
- Application Service com 200+ linhas, if/else de regra
- Domain Service consultando repository dentro de operação — passe dados já prontos

---

## 5. Repository

- [ ] Interface collection-like (`findById`, `add`, `remove`)?
- [ ] Queries nomeadas em linguagem de domínio?
- [ ] Sem queries genéricas (`findByCriteria(anyObject)`)
- [ ] Um repository por aggregate root?
- [ ] SQL/ORM vazando? (ex.: repository retorna `EntityManager`, `QuerySet`, objetos parciais)
- [ ] Persiste agregado completo, não partes?

**Red flags:**
- 50+ métodos `findBy...` no mesmo repo — virou QueryObject
- Repository de Entity interna (não-root)
- Repository expondo `Iterator<EntityInternal>` cru
- `repo.save(fragment)` que salva só parte do aggregate

---

## 6. Domain Events

- [ ] Nomes em **passado** (`OrderConfirmed`, não `ConfirmOrder`)?
- [ ] Imutáveis?
- [ ] Contêm dados essenciais (IDs, timestamp, dados mínimos) — não o aggregate inteiro?
- [ ] Emitidos como resultado de comandos, não em getters?
- [ ] Publicação coordenada com persistência (outbox ou similar)?
- [ ] Consumers idempotentes?

**Red flags:**
- `EntityUpdated` genérico — perde semântica
- Evento com estado completo do aggregate — não é evento, é snapshot
- Emissão de evento dentro de construtor do aggregate
- Publicação antes do commit — pode perder/duplicar

---

## 7. Bounded Contexts e estrutura de módulos

- [ ] Código organizado por bounded context (top-level packages nomeados por conceito de negócio)?
- [ ] Módulos têm API pública explícita vs. interna privada?
- [ ] Imports entre módulos limitados à API pública?
- [ ] Cada módulo tem seu próprio schema lógico de DB?
- [ ] Mesmo conceito com nome diferente em contextos diferentes é **intencional**?
- [ ] Há "modelo canônico" tentando servir a todos contextos? (anti-sinal)

**Red flags:**
- Pasta `shared/models/` ou `common/entities/` sendo importada por tudo
- Foreign keys cruzando módulos livremente
- Time tocando 5+ módulos numa feature — fronteiras erradas
- Mesma classe `User`, `Customer`, `Product` usada em vendas, estoque, faturamento — provável anemic canonical model

---

## 8. Context Map / Integrações

- [ ] Documenta-se *como* módulos/contextos integram (pattern nomeado)?
- [ ] ACL existe onde integração cruza fronteira crítica (legacy, terceiro)?
- [ ] Published Language versionada quando contexto expõe API?
- [ ] Síncrono vs. assíncrono por decisão consciente, não acidente?

**Red flags:** integração por "REST pq a gente sempre usa REST", sem análise; contextos acoplados em banco compartilhado sem pattern declarado.

---

## 9. Arquitetura / camadas

- [ ] Domínio **não depende** de infraestrutura (DB, HTTP, framework)?
- [ ] Inversão de dependência via interfaces (port & adapter)?
- [ ] Controllers HTTP / CLI entries finos (delegam a Application Service)?
- [ ] Camada de domínio testável sem DB/HTTP?

**Red flags:**
- Entity com annotation `@Entity` (ORM) — força modelo pelo DB, não pelo domínio
- Controller com 100+ linhas de lógica
- Import de `javax.persistence` / `sqlalchemy` / `prisma` dentro da pasta `domain/`
- Teste de domínio que precisa subir container DB

---

## 10. Smells gerais

- [ ] **Anemic model**: entidades são DTOs, lógica na camada de serviço?
- [ ] **God service**: classe com 30+ métodos coordenando tudo?
- [ ] **Generic wrappers**: `Response<T>`, `Result<T>` vazando pra domínio?
- [ ] **Utility-bloating**: `StringUtils`, `DateUtils` com lógica de negócio?
- [ ] **Magic numbers/strings**: `if (status == "ACTIVE")` vs. enum/VO?
- [ ] **Transações longas**: abrangem múltiplos aggregates, múltiplas chamadas externas?

---

## Como produzir o relatório de Analysis

Para cada achado:

```markdown
### [SEVERIDADE] <título curto>

**Evidência:**
- `src/orders/OrderService.java:42` — snippet curto
- `src/orders/Order.java:15` — snippet curto

**Referência:** <regra do livro / pattern>

**Impacto:** <o que pode dar errado>

**Correção sugerida:** <passo incremental>

**Esforço:** baixo/médio/alto
```

**Reforço positivo** ao fim: "o que o time já acerta" — tão importante quanto apontar problemas. Motiva a continuar.

---

## Apêndice — Snippets bom/ruim (agnósticos)

Use esses como referência pra ilustrar achados no relatório de analysis. Adapte à linguagem do projeto alvo.

### Anemic model vs Rich domain

```
// Ruim — anemic (entity é DTO, lógica espalhada fora)
class Order {
  id; customerId; status; items; total;
  getStatus() { return this.status; }
  setStatus(s) { this.status = s; }
}

class OrderService {
  confirm(orderId) {
    const o = repo.findById(orderId);
    if (o.status !== 'DRAFT') throw new Error('invalid');
    o.setStatus('CONFIRMED');          // <- lógica vazada
    o.total = calculateTotal(o.items); // <- cálculo fora
    repo.save(o);
  }
}

// Bom — rich domain (entity encapsula comportamento + invariantes)
class Order {
  readonly id; readonly customerId;
  private status; private items; private total;

  confirm() {
    assert(this.status === DRAFT, 'only DRAFT can be confirmed');
    assert(this.items.length > 0, 'no items');
    this.status = CONFIRMED;
    this.total = Money.sum(this.items.map(i => i.subtotal));
    this.recordEvent(new OrderConfirmed(this.id, this.total, now()));
  }
}

class ConfirmOrderAppService {
  execute(cmd) {
    transaction {
      const o = repo.findById(cmd.orderId);
      o.confirm();                    // <- delega ao domínio
      repo.save(o);
      events.publishAll(o.pullEvents());
    }
  }
}
```

### Value Object vs primitive obsession

```
// Ruim
function sendEmail(to: string) { /* ... */ }
sendEmail("not-an-email");          // aceita qualquer string

// Bom
class Email {
  readonly value: string;
  constructor(raw: string) {
    if (!raw.match(EMAIL_REGEX)) throw new InvalidEmail(raw);
    this.value = raw.toLowerCase();
  }
  equals(other: Email) { return this.value === other.value; }
}

function sendEmail(to: Email) { /* ... */ }
sendEmail(new Email(input));        // validação no boundary
```

### Aggregate — referência por ID vs navegação

```
// Ruim — navegação direta entre aggregates
class Order {
  customer: Customer;              // carrega Customer inteiro
}
order.customer.address.update(...); // modifica outro aggregate na mesma transação

// Bom — referência por ID
class Order {
  customerId: CustomerId;           // só identidade
}

// Se precisa do Customer, App Service carrega ANTES e passa dados já prontos
appService.execute(cmd) {
  const c = customerRepo.findById(cmd.customerId);
  const o = orderRepo.findById(cmd.orderId);
  o.applyCustomerDiscount(c.tier);  // passa dado, não aggregate
}
```

### Repository — collection-like vs DAO vazado

```
// Ruim — expõe mecânica de persistência
interface OrderRepo {
  executeQuery(sql: string): any[];
  findByCriteria(criteria: object): Order[];  // query genérica
  findById(id): Partial<Order>;               // objeto parcial
}

// Bom — collection-like, linguagem de domínio
interface OrderRepo {
  findById(id: OrderId): Order | null;
  add(order: Order): void;
  remove(order: Order): void;
  activeOrdersForCustomer(id: CustomerId): Order[];  // nome de domínio
  ordersPendingShipmentAt(date: Date): Order[];
}
```

### Domain Event — específico vs genérico

```
// Ruim — genérico, consumer força switch no payload
record OrderUpdated(orderId, changedFields: Map<String, Any>)

// Bom — específico, semântica preservada
record OrderConfirmed(orderId, total, occurredOn)
record OrderShipped(orderId, trackingNumber, shippedAt)
record OrderCancelled(orderId, reason, cancelledBy, occurredOn)
```

### Application Service — fino vs gordo

```
// Ruim — lógica de negócio no service
class CancelOrderService {
  execute(cmd) {
    const o = repo.findById(cmd.orderId);
    if (o.status === 'SHIPPED') {        // <- regra de domínio
      throw new Error('cannot cancel');
    }
    if (daysSince(o.createdAt) > 30) {   // <- regra de domínio
      chargeFee(o.customerId, 10);       // <- side effect externo
    }
    o.status = 'CANCELLED';
    repo.save(o);
  }
}

// Bom — service orquestra, domínio decide
class CancelOrderService {
  execute(cmd) {
    transaction {
      const o = repo.findById(cmd.orderId);
      const fee = o.cancel(cmd.reason, clock.now());  // <- retorna evento+fee se aplicável
      repo.save(o);
      events.publishAll(o.pullEvents());
      // fee é outro evento que Billing consumirá — não chamar Billing aqui
    }
  }
}
```

### Bounded Context — vazamento vs ACL

```
// Ruim — contexto Orders importa tipos de Identity
import { User, Permission } from '../identity/domain';

class Order {
  placedBy: User;                 // vazamento total
  check() {
    if (!this.placedBy.hasPermission(Permission.PLACE_ORDER)) {...}
  }
}

// Bom — ACL traduz pra VO do próprio contexto
import { OrderCustomer } from './domain'; // VO local

class Order {
  placedBy: OrderCustomer;        // só o que Order precisa saber
}

// Adapter na fronteira
class IdentityToOrderAcl {
  toOrderCustomer(user): OrderCustomer {
    return new OrderCustomer(user.id, user.displayName);
    // permission, email, phone — não sai
  }
}
```

---

## Heurísticas sobre granularidade

- Análise leve (review de PR): foque em camadas 1-6
- Auditoria completa (review de codebase): inclua 7-10
- Due-diligence arquitetural (vender/comprar): todas + matriz de dívida técnica quantificada
