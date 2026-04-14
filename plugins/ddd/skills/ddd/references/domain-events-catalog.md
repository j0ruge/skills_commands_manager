# Domain Events — catálogo, naming e padrões de estrutura

Fontes: `[IDDD cap.8]`, `[Evans Reference]`, event-driven.io (Oskar Dudycz), Microsoft Architecture Center.

> Esta reference é consultada sempre que você for **propor novos eventos** (modos 2, 3) ou **auditar eventos existentes** (modo 1). Garante nomenclatura e estrutura consistentes na skill e no código gerado.

---

## Naming — regras obrigatórias

### 1. Passado perfeito, sempre

Eventos são **fatos** — algo já aconteceu. Use verbo no passado.

| Bom | Ruim | Por quê |
|-----|------|---------|
| `OrderConfirmed` | `ConfirmOrder` | `Confirm` é imperativo → é Command, não Event |
| `BatteryExpired` | `BatteryExpiry` | Substantivo perde a noção de transição |
| `InvoiceSettled` | `InvoiceSettlement` | Mesmo problema |
| `UserPasswordChanged` | `ChangeUserPassword` | Imperativo → Command |

### 2. Entity + Verb, nessa ordem

Prefixo é a entity/aggregate afetado, sufixo é o verbo que descreve o fato.

| Bom | Ruim |
|-----|------|
| `OrderConfirmed` | `ConfirmedOrder` |
| `BatteryWithdrawn` | `WithdrewBattery` |
| `ShipmentDispatched` | `DispatchShipment` |

Padrão: `<Aggregate><PastTenseVerb>`.

### 3. Específico, nunca genérico

Eventos específicos têm **semântica**. Genéricos são CRUD disfarçado.

| Bom (específico) | Ruim (genérico) |
|------------------|------------------|
| `PriceChanged` | `ProductUpdated` |
| `AddressCorrected` | `CustomerModified` |
| `ShipmentCancelled`, `ShipmentCompleted` | `ShipmentChanged` |
| `BatteryEnteredServiceTime`, `BatteryExpired` | `BatteryStatusChanged` |

**Teste:** se o consumidor precisa inspecionar payload pra decidir o que fazer, é genérico demais — quebre em eventos específicos.

### 4. Fato de negócio, não técnico

| Bom (domínio) | Ruim (técnico) |
|---------------|----------------|
| `OrderPlaced` | `OrderInserted` |
| `CustomerDeactivated` | `CustomerRowUpdated` |
| `BatteryAdmitted` | `BatteryRecordCreated` |

Se o domain expert não usaria o nome em conversa, o nome está errado.

### 5. Idioma consistente

Escolha **pt-BR ou EN** e mantenha por contexto. Misturar (`PedidoConfirmed`) é pior que escolher errado.

**Default recomendado:** inglês no tipo/classe do evento (interoperabilidade com libs, docs) + nomes de campos e comentários em pt-BR quando o código do projeto é pt-BR.

---

## Estrutura — payload mínimo e útil

### Campos obrigatórios em TODO domain event

```
record <Nome>Event (
  eventId: UUID,              // identidade única do evento (idempotência)
  occurredOn: Instant,        // timestamp de domínio (quando o fato ocorreu)
  aggregateId: <AggregateId>, // quem foi o aggregate afetado
  aggregateType: String,      // "Battery", "Order" etc (útil em event store genérico)
  eventVersion: Int,          // 1, 2, ... para schema evolution
  ...<dados essenciais>
)
```

### Dados essenciais (NÃO o aggregate inteiro)

O evento carrega **o mínimo pra consumers decidirem**. Não embute o aggregate.

**Bom:**
```
record BatteryWithdrawn(
  eventId, occurredOn, eventVersion,
  batteryId: BatteryId,
  keyCode: KeyCode,             // dado frequentemente consultado
  reason: String,
  withdrawnBy: OperatorId
)
```

**Ruim:**
```
record BatteryWithdrawn(
  eventId, occurredOn,
  battery: Battery              // <- aggregate inteiro serializado. Não faça.
)
```

**Razões:**
- Aggregate tem comportamento (métodos) que não serializa
- Muda o aggregate, muda o schema do evento (acopla)
- Payload cresce sem limite
- Perde-se clareza do que mudou

### Incluir dados "derivados frequentes"

Se 80% dos consumers vão consultar um dado junto, **inclua no payload** — senão cada um vira query de volta ao aggregate.

Ex.: `BatteryWithdrawn` inclui `keyCode` porque Audit, Finance e Maintenance consultam isso imediatamente. Não inclua `batteryTimingPolicy` porque ninguém precisa.

---

## Categorias de eventos

### 1. Lifecycle events (criação, remoção)

Padrão: `<Aggregate>Created`, `<Aggregate>Deleted` (raro — preferir `<Aggregate>Archived`, `<Aggregate>Deactivated`).

```
record OrderPlaced(eventId, occurredOn, orderId, customerId, totalAmount, ...)
record CustomerDeactivated(eventId, occurredOn, customerId, reason, deactivatedAt)
```

### 2. State transition events

Um evento **por transição significativa**. Não use `<Aggregate>StatusChanged` genérico.

```
// Bom
record OrderConfirmed(...)
record OrderShipped(...)
record OrderDelivered(...)
record OrderCancelled(...)

// Ruim
record OrderStatusChanged(orderId, from, to)  // consumers forçados a switch no payload
```

### 3. Attribute change events (menos frequente)

Somente quando a mudança do atributo é **fato de negócio**, não alteração casual.

```
record PriceChanged(productId, oldPrice, newPrice, changedAt, reason)
record AddressCorrected(customerId, oldAddress, newAddress, correctedBy)
```

Se a mudança não tem significado de negócio (ex.: `description` editado), não emita evento.

### 4. Integration events (cruzam bounded context)

Subtipo de domain event, mas **contrato público**. Versionado, documentado como Published Language.

```
// Integration event — publicado para consumers externos
record OrderPlacedV1(
  eventId, occurredOn, eventVersion: 1,
  orderId, customerId, items: [LineItem], total: Money
)
```

**Distinção domain event vs integration event:**
- Domain event: dentro do bounded context. Pode ter VOs ricos, não precisa ser estável.
- Integration event: fronteira do contexto. Schema estável, versionado, sem tipos internos.

Na prática comum (`[prática pós-2020]`): emita **um domain event interno** e um **mapper** traduz para integration event ao publicar externamente.

---

## Quando emitir — critérios

Emita domain event quando:

1. **Estado significativo do aggregate mudou** e a mudança tem nome no negócio
2. **Outros contextos/aggregates precisam reagir** (eventualmente)
3. **Auditoria** do fato é requisito (legal, compliance, debug)

NÃO emita quando:

- É leitura (query)
- É campo técnico (updatedAt, version)
- É cache/derived state que pode ser recalculado
- É comando em processo (emitir o evento do sucesso, não da tentativa)

---

## Quando NÃO emitir

Antipadrões comuns:

- **`EntityUpdated` genérico** — perdeu semântica, virou log
- **Evento em getter/query** — viola separação command/query
- **Evento emitido antes do commit** — pode publicar e o commit falhar
- **Evento síncrono com side effects fora do aggregate** — acopla, torna difícil testar
- **Evento "só pra logar"** — use log, não domain event

---

## Publicação — padrão Outbox

Sempre que persistência do aggregate coexiste com publicação do evento, use Outbox `[prática pós-2020]`:

```
transaction {
  aggregateRepo.save(aggregate)
  outboxRepo.insert(event)            // mesma transação
}

// worker separado e idempotente:
while (true) {
  events = outboxRepo.pullUnsent(batch=100)
  for event in events:
    broker.publish(event)
    outboxRepo.markSent(event.id)
}
```

Sem Outbox: ou perde eventos (publicou antes, rollback), ou duplica (publicou depois, falhou em marcar).

---

## Consumo — idempotência obrigatória

Messaging é "at-least-once" por default. Consumer **deve** ser idempotente.

**Estratégias:**

1. **Guardar eventIds processados** — tabela `processed_events(event_id, processed_at)`. Antes de agir, verificar; após agir na mesma transação, inserir.
2. **Operações commutativas** — ex.: `setStatus(X)` aplicado 2x = aplicado 1x. Nem sempre possível.
3. **Versionamento** — estado do aggregate tem version; evento carrega version esperada; ignorar eventos out-of-order.

---

## Schema evolution — versionamento

Eventos vivem no event store potencialmente anos. Schema evolui.

**Regras:**

- **Nunca remover campo**; marque deprecated
- **Adicionar campo**: novo campo com default sensato
- **Mudar semântica de campo**: bump `eventVersion` + novo evento
- **Upcaster**: função que lê evento v1 e retorna v2 — rodada no carregamento

Ex.:
```
record OrderPlacedV1(..., totalAmount: Decimal)
record OrderPlacedV2(..., totalAmount: Money)  // VO

// Upcaster
OrderPlacedV2 upcast(OrderPlacedV1 v1) =
  OrderPlacedV2(..., Money(v1.totalAmount, defaultCurrency))
```

---

## Catálogo template (para documentar eventos por contexto)

Mantenha um `events.md` em cada bounded context:

```markdown
# Events — <bounded-context>

## Lifecycle

### OrderPlaced
- **Quando:** cliente confirma pedido no checkout
- **Payload:** orderId, customerId, totalAmount, items
- **Consumidores conhecidos:** Inventory (reservar stock), Billing (gerar fatura)
- **Versão atual:** 2
- **Notes:** v2 mudou totalAmount de Decimal para Money

### OrderCancelled
- **Quando:** cliente ou sistema cancela pedido
- **Payload:** orderId, reason, cancelledAt, cancelledBy
- **Consumidores:** Inventory (liberar stock), Billing (cancelar fatura), Audit
- **Versão:** 1

## State transitions

### OrderShipped
...
```

Isso é a **Published Language** do contexto — referência canônica pra quem consome.

---

## Checklist pra revisar um evento proposto

- [ ] Nome é `<Aggregate><PastTenseVerb>`?
- [ ] Descreve fato de negócio, não operação técnica?
- [ ] Específico o bastante (não genérico)?
- [ ] Payload tem `eventId`, `occurredOn`, `aggregateId`, `eventVersion`?
- [ ] Payload traz só o essencial (não o aggregate inteiro)?
- [ ] Há versionamento planejado?
- [ ] Publicação é transacional (Outbox)?
- [ ] Consumer é idempotente?
- [ ] Documentado no `events.md` do contexto?

Se faltar qualquer item, volte ao design antes de codificar.
