# Context Mapping — 9 padrões de integração entre contextos

Fontes: `[Evans Reference]`, `[Distilled cap.4]`, `[IDDD cap.3]`, `[DDD Crew context-mapping]`.

O Context Map é **diagrama + narrativa**. Mostra contextos existentes e a relação entre eles. Cada relação tem um pattern — **não há integração "sem pattern"**; se você não escolher, cai em Big Ball of Mud por padrão.

## Tabela resumo

| Pattern | Direção | Acoplamento | Custo | Quando usar |
|---------|---------|-------------|-------|-------------|
| Partnership | ↔ | Alto | Alto | Times que afundam/flutuam juntos |
| Shared Kernel | ↔ | Alto | Médio-Alto | Pedaço pequeno compartilhado, coordenação disciplinada |
| Customer-Supplier | ↑ dono | Médio | Médio | Relação upstream/downstream saudável |
| Conformist | ↑ dono | Baixo esforço, Alto risco | Baixo | Upstream poderoso e estável; downstream sem força |
| ACL | ↑ upstream, ↓ isolado | Isola downstream | Alto | Upstream é ruim/legacy/instável, modelo local precisa ser protegido |
| Open Host Service (OHS) | Upstream publica | Baixo por client | Médio | Múltiplos clientes consumindo mesmo serviço |
| Published Language | Upstream publica | Baixo por client | Médio | Complementa OHS; contrato versionado |
| Separate Ways | — | Zero | Zero | Integração não compensa |
| Big Ball of Mud | Misturado | Tudo | Mascarada, se espalha | Reconhecer e cercar com ACL |

---

## Partnership
Dois contextos cooperam ativamente. Falha de integração é falha mútua. Requer planejamento conjunto, CI integrada, releases sincronizadas.

**Use quando:** dois times dependem radicalmente um do outro (ex.: Vendas e Faturamento num ERP onde tudo que vende precisa faturar imediato).

**Evite quando:** times não conseguem coordenar (fusos, prioridades diferentes). Vira Conformist disfarçado.

---

## Shared Kernel
Um subconjunto pequeno do modelo é compartilhado. Código em lib comum. Mudanças só com acordo.

**Use quando:** duplicação causaria drift semântico real (ex.: tipo `Money` com arredondamento fiscal específico da empresa).

**Anti-sinal:** kernel cresce e vira modelo canônico. Sem disciplina forte, degenera rápido.

---

## Customer-Supplier
Relação upstream→downstream com voz do cliente. Downstream participa do planejamento upstream. Testes de aceitação automatizados protegem downstream.

**Use quando:** há relação clara de dependência unidirecional e o supplier tem incentivo pra atender.

**Dica pós-2020:** use contract testing (Pact, etc.) pra materializar a proteção.

---

## Conformist
Downstream abraça modelo upstream sem tradução.

**Use quando:** upstream é muito maior/estável (ex.: API pública da Receita Federal, Stripe). Traduzir custa mais que aceitar.

**NÃO use quando:** upstream é legacy interno ruim. Aí você quer ACL.

---

## Anti-Corruption Layer (ACL)
Camada de tradução defensiva. Downstream expõe para si mesmo um modelo limpo; ACL traduz de/para o modelo upstream.

**Padrão de implementação** `[IDDD cap.3, 13]`:
- Domain Service no downstream que consome interface upstream
- Traduz DTOs upstream → Value Objects locais
- Isola: se upstream muda, só a ACL muda

**Use quando:**
- Migrando de legacy: o novo código NUNCA deve importar tipos do velho
- Integrando com sistema terceiro mal modelado
- Protegendo core domain de contextos genéricos

**Custo:** manter a tradução. Compensado porque protege o modelo limpo.

---

## Open Host Service (OHS)
Upstream publica API padronizada pública. Suporta múltiplos clientes sem adaptação per-client.

**Use quando:** seu contexto é consumido por 2+ outros contextos/sistemas.

**Combine com:** Published Language.

---

## Published Language
Linguagem de troca bem documentada (schema JSON/XML/Protobuf/AsyncAPI). Versionada. Independente dos modelos internos.

**Use quando:** há OHS; integração atravessa fronteiras organizacionais; contrato precisa sobreviver a refatorações internas.

**Prática pós-2020:** schema-first + versionamento semântico + testes de contrato.

---

## Separate Ways
Decisão consciente de NÃO integrar. Duplicação local aceita como menor mal.

**Use quando:** esforço de integração >> benefício. Ex.: módulo interno de gestão de ativos não precisa falar com módulo de marketing.

**Não confunda com negligência.** Separate Ways é explícito no Context Map.

---

## Big Ball of Mud (BBoM)
Anti-padrão. Reconheça, cerque com ACL, não se espalhe.

**Como reconhecer:**
- Não dá pra explicar os módulos em uma frase
- Tudo importa de tudo
- Testes só rodam com DB real + todos os serviços up
- Time sênior evita mexer

**Estratégia** `[Distilled cap.4]`: tratar BBoM como um contexto único. Toda interação com ele passa por ACL. Greenfield novo cresce ao lado, isolado. Ver `legacy-migration.md`.

---

## Como desenhar um Context Map

**Mínimo viável:**

```
[Contexto A] ──<pattern>── [Contexto B]
                              │
                          <pattern>
                              │
                         [Contexto C]
```

**Notação DDD Crew** (recomendada, `[DDD Crew]`):
- `U` = Upstream, `D` = Downstream
- Rótulos nas setas: `OHS`, `PL`, `ACL`, `CF` (Conformist), `SK` (Shared Kernel), `P` (Partnership), `CS` (Customer-Supplier), `SW` (Separate Ways)

Mermaid é OK pra Context Maps leves. ContextMapper DSL (contextmapper.org) pra modelos grandes versionáveis.

---

## Notification pattern — operacional pra integração cross-context

`[IDDD cap.13]`

Quando Bounded Contexts publicam Domain Events pra outros consumirem, o *formato da mensagem* importa tanto quanto os patterns de relação. Sem padrão de publicação, cada consumer reinventa deserialização.

### Notification como wrapper do Event

Em vez de publicar o Domain Event cru, envolva-o em **Notification** — um envelope padronizado:

```
Notification {
  notificationId: UUID          // identidade da mensagem (pra idempotência do consumer)
  typeName: String              // "OrderPlaced", "BatteryExpired"
  version: Int                  // schema version do event
  occurredOn: Instant           // timestamp do fato (não da publicação)
  eventBody: Payload            // o Domain Event serializado
  // metadata opcional: sourceContext, correlationId, causationId, trace
}
```

Benefícios:
- Consumer processa uniformemente: lê `typeName` + `version` → dispacha
- Idempotência trivial via `notificationId`
- Tracing distribuído fica fácil
- Schema evolution isolada (adicionar campo ao envelope não quebra)

### NotificationReader — leitura type-safe sem classes compartilhadas

Consumer **não deve** depender das classes concretas do publisher (acoplamento proibido). Em vez disso, leia payload via navegação:

```
reader = NotificationReader(notificationJson)
if reader.typeName() == "OrderPlaced" && reader.version() == 2:
  orderId = reader.stringValue("eventBody.orderId")
  customerId = reader.stringValue("eventBody.customerId")
  total = reader.decimalValue("eventBody.total.amount")
```

Biblioteca (NotificationReader, JsonPath, GJSON) navega por dot notation sem exigir classe POJO/POCO espelhada. Consumer constrói seu próprio VO local com o que precisa.

Vantagem: publisher evolui livremente (adiciona campos, refactora internals) sem quebrar consumers.

### Custom Media Type / Published Language

Defina media type próprio pro seu domínio, não confie em `application/json` genérico:

```
Content-Type: application/vnd.jrc.battery.notification.v2+json
```

Benefícios:
- Content negotiation HTTP: consumers pedem versão que suportam (`Accept: ...v1+json` vs `...v2+json`)
- Documentação explícita do contrato (spec do media type é a Published Language)
- Facilita parallel evolution: publisher serve v1 e v2 simultaneamente

### Estratégia v1-forward-compatible

Regra de ouro: **v1 consumers nunca devem quebrar**.

- **Additive changes** (novos campos, novos events): incremento de minor version; v1 clients ignoram os campos novos — ok
- **Breaking changes** (remover campo, mudar semântica, renomear): v2 coexistindo com v1 por janela de transição (meses); eventual deprecation anunciada
- **Deletion**: só depois que monitoring mostra zero clientes em v1

Implementação típica: publisher emite eventos em dois media types simultaneamente durante transição; filtro/router de broker faz o split.

### Versionamento de eventos no event store

Relacionado, mas distinto: dentro do próprio contexto, events persistidos precisam sobreviver a refactors.

- Adicione campo novo com default sensato
- Nunca remova campo; marque deprecated
- Mudança semântica → novo `typeName` + **upcaster** (função `v1 → v2` aplicada ao carregar evento antigo)

### REST pull (Atom/feed-style) vs. Messaging push

**REST pull (feed)** — publisher expõe endpoint `/notifications?since=X`. Consumer rastreia posição (cursor) e pede batches.

Vantagens:
- Consumer controla ritmo (backpressure natural)
- Sem broker — reduz infra
- Idempotência natural via cursor persistido do consumer
- Replay trivial: consumer volta o cursor, reprocessa
- Funciona em ambientes com acesso só de saída (firewall)

Desvantagens:
- Latência mínima = intervalo de polling (segundos a minutos)
- Consumer precisa manter estado (cursor)
- Scaling horizontal de consumer precisa coordenação de cursor

**Implementação:**
- Atom 1.0 feed com paginação por link (`<link rel="next">`)
- Endpoint custom REST: `GET /notifications?afterId=N&limit=100`
- Consumer persiste `lastSeenId` localmente, pede sempre `afterId=lastSeenId`
- Publisher mantém events ordenados e imutáveis (event store, não tabela mutável)

**Messaging push** — publisher envia pra broker (RabbitMQ, Kafka, NATS, SQS), consumer subscribe.

Vantagens: latência baixa (ms), backpressure via ack, multi-consumer trivial, padrões (at-least-once, exactly-once com Kafka transactions).

Desvantagens: broker é nova infra + SPOF potencial, curva de aprendizado, operação (replay, DLQ, lag monitoring).

Escolha:
- Contextos internos, integração simples, SLA tolerante a minutos → **pull** basta e é mais simples
- Alta frequência, muitos consumers, auditoria regulatória, baixa latência → **push via broker**
- Equipe sem experiência em broker → comece com pull, migre quando houver necessidade real
- Nunca ambos ao mesmo tempo sem necessidade (complexidade dobra sem benefício)

### Wire formats — trade-offs rápidos

`[Distilled cap.4]`

Não basta escolher "JSON" — o formato do payload afeta evolução, tamanho, e tooling.

| Formato | Schema | Evolução | Tamanho | Quando |
|---------|--------|----------|---------|--------|
| **JSON** | Implícito (documentado externo) | Flexível — consumers toleram campos extras | Médio-grande | Default pra APIs REST, público. Legível humanamente. |
| **JSON Schema + OpenAPI** | Explícito versionado | Additive-safe com contract tests | Médio-grande | REST com múltiplos clientes e contrato formal |
| **Protobuf** | Explícito (.proto) | Backward/forward compat por regras fixas | Pequeno | gRPC, alto throughput interno, múltiplas linguagens |
| **Avro** | Explícito (schema registry) | Schema evolution com resolução automática | Pequeno | Kafka + Confluent ecosystem, event streaming |
| **XML** | DTD/XSD explícito | Flexível, tooling pesado | Grande | Legado SOAP, integrações B2B regulamentadas (NFe, EDI) |

**Regras:**
- **Interno cross-BC assíncrono:** Avro ou Protobuf (performance + schema registry)
- **Público REST:** JSON + OpenAPI versionado (SemVer)
- **Brazilian compliance (NFe, SPED):** XML é inescapável
- **Nunca:** payload sem schema algum (mesmo que implícito em doc)

### RPC e temporal coupling

`[Distilled cap.4]`

RPC síncrono (REST bloqueante, gRPC) cria **temporal coupling**: se o destino está fora, o originador também falha. Em integração cross-BC, isso contamina disponibilidade.

Sinais de temporal coupling doloroso:
- Incidente num BC derruba outros BCs
- Latência p99 cresce com a cadeia de chamadas síncronas
- Circuit breakers e retries viram feature obrigatória em todo cliente

**Alternativas:**
- **Async messaging** (push) — desacopla disponibilidade
- **REST pull feed** — consumer tolera publisher fora
- **Async command + event de resposta** — command vai, event de "done/failed" volta
- **Cache local** — última resposta conhecida quando upstream fora

**Quando RPC síncrono ainda vale:**
- Query cross-BC que não cabe em read model local (raro; normalmente indica fronteira errada)
- Integração externa paga por request onde o cliente precisa da resposta imediata (gateway de pagamento)
- Ambiente legacy sem messaging disponível

**Regra pós-2020:** async-first para comunicação cross-BC. Síncrono exige justificativa.

### Outbox obrigatório em ambos os casos

Independente de pull ou push: evento não é publicado até commitar na mesma transação do aggregate save. Ver `cqrs-event-sourcing.md` → Outbox pattern.

---

## Anti-padrões de context mapping

- **Context Map não existe** — ninguém sabe como contextos integram. Default = BBoM.
- **Contexto sem nome canônico** — ubiquitous language não incluir o nome dos próprios contextos é sintoma.
- **Pattern implícito** — "a gente só integra via REST". REST é protocolo, não pattern. É ACL? OHS+PL? Conformist?
- **Shared Database** — dois contextos compartilham schema/tabelas sem pattern explícito. Isso é Shared Kernel mal feito ou BBoM disfarçado. Em modular monolith, cada módulo tem schema lógico próprio.
