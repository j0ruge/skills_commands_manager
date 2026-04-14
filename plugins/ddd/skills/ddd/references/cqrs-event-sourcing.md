# CQRS e Event Sourcing — quando e quando NÃO

Fontes: `[IDDD cap.4, Appendix A]`, `[Distilled cap.6]`, `[Evans Reference]`, microservices.io, event-driven.io (Oskar Dudycz), Microsoft Architecture Center.

> Ambos os padrões são ferramentas específicas. São maduros em 2026, mas carregam custo. Escolha deliberada — não porque "DDD mandou" (não mandou).

---

## CQRS — Command Query Responsibility Segregation

**Definição:** modelo de escrita (commands, muda estado, usa aggregates DDD) é separado do modelo de leitura (queries, projeções otimizadas, pode ser denormalizado). Os dois conversam via Domain Events (ou polling).

**Não é:** separar pastas `Query/` e `Command/` no código. Isso é organização. CQRS real tem **modelo distinto** — potencialmente storage distinto.

---

### Quando ADOTAR CQRS

- Queries exigem projeções denormalizadas que distorcem o modelo de escrita (dashboards, relatórios, mobile views específicas) `[IDDD p.2612]`
- Contenção de concorrência: writes bloqueiam reads frequentemente
- Leitura e escrita escalam diferente (10k reads/s, 100 writes/s)
- Múltiplas views do mesmo dado, cada consumidor com formato próprio

### Quando NÃO adotar CQRS

- CRUD simples, poucas queries `[Microsoft Architecture]`
- Time pequeno, timeline curta (CQRS adiciona carga mental)
- Eventual consistency nas queries é inaceitável no caso de uso
- MVP / prototipagem

### Erros comuns

- **CQRS sem justificativa** — adiciona complexidade sem ganho. Oskar Dudycz (event-driven.io) enfatiza: "CQRS não é sobre infra separada, é sobre reconhecer que perguntas e mudanças são conceitualmente diferentes."
- **Fingir CQRS** — mesmo modelo usado para ambos, só renomeando classes. Perde todo benefício, mantém complexidade.
- **Stale reads inaceitáveis** — esquecer que query model tem lag. Desenhe UX pra isso (timestamp da projeção, refresh explícito).
- **Sincronizar via polling em vez de eventos** — acopla e perde consistência. Use Domain Events.

---

## Event Sourcing

**Definição:** estado do aggregate é derivado de uma sequência imutável de Domain Events persistidos em event store. Reconstituição via replay. `[IDDD Appendix A]`

**Não é:** apenas guardar eventos em log pra auditoria (isso é event logging). ES é **estado = f(eventos)**.

---

### Quando ADOTAR Event Sourcing

- Requisito legal/compliance de auditoria completa (ex.: saúde, financeiro, regulatórios) `[IDDD p.2646]`
- Domínio rico em "por quê" — analytics e reconstrução histórica são features
- Sistemas colaborativos complexos (versionamento, merge, temporal queries)
- Testes de regressão de processos longos via event replay

### Quando NÃO adotar Event Sourcing

- CRUD com alguns eventos esporádicos — logging basta
- Estado é derivado fácil e não há valor no histórico
- Time sem experiência em event-driven (curva íngreme: schema evolution de eventos, snapshots, projeções)
- MVP / curto prazo

### Erros comuns

- **Eventos como CRUD** — `ProductUpdated` com o estado completo. Perde semântica. Eventos devem ser fatos de negócio específicos: `PriceChanged`, `DescriptionRevised`.
- **Schema evolution não planejada** — event antigo com campo que não existe mais. Planeje versioning (upcasters, schema registry).
- **Projeções acopladas ao event store** — read models dependem direto do storage. Use adapter/port.
- **Replay lento sem snapshots** — reconstruir aggregate com 100k eventos demora. Snapshot a cada N eventos.
- **Sem outbox pattern** — evento publicado fora da transação pode ser perdido ou duplicado. Persiste evento + commit atômico + publisher separado.

---

## CQRS + Event Sourcing — combinação comum

Casam bem: write side persiste events; read side materializa projeções consumindo os mesmos events. Cada query view é uma projeção.

**Benefícios:** write side simples (só appendable), read side liberto pra otimizar por view, auditoria built-in.

**Custo:** operacional (event store, schema registry, monitoramento de lag de projeção, replay tools).

---

## Alternativas mais leves antes de adotar

- **CRUD + Domain Events pontuais** — modelo DDD tático, transações normais, eventos pra integrar com outros contextos. Resolve 80% dos casos.
- **CQRS sem Event Sourcing** — write side relacional normal, read side materializado via triggers/views/eventos. Simples, poderoso.
- **Event log para auditoria** — grava eventos como log, mas o estado canônico ainda é o agregado persistido normal. Audit sem a complexidade do ES.

---

## Outbox Pattern — pré-requisito prático

Sempre que você tem "persistir aggregate + publicar evento", use Outbox:

```
transaction {
  aggregate.save();                           // tabela normal
  outbox.insert(event);                       // mesma transação, tabela de saída
}
// publisher separado lê outbox e publica; marca como enviado; idempotente
```

Sem isso, você tem a clássica dupla falha: ou perde evento (publicou antes, rollback), ou publica duplicado (publicou depois, falhou em marcar).

`[prática pós-2020]`

---

## Saga / Process Manager

Quando um processo atravessa múltiplos agregados ou contextos, com consistência eventual:

- **Coreografia** (events encadeando-se): cada aggregate reage ao evento anterior e emite o próximo. Baixo acoplamento, alto implicit flow.
- **Orquestração** (process manager central): um componente coordena, chamando cada etapa. Flow explícito, mas ponto central que precisa recuperar de falhas.

**Compensating transactions** — se etapa 3 falha depois de 1 e 2, emita eventos que desfazem (logicamente) os efeitos de 1 e 2. Não dá rollback em eventual consistency.

---

## Concorrência em Event Sourcing — conflict resolution e retry

`[IDDD Apêndice A]`

Event Sourcing sem estratégia de concorrência é frágil em cargas paralelas. Dois writers mirando o mesmo aggregate vão conflitar eventualmente.

### Optimistic concurrency check

Event store guarda, por aggregate, a **versão** atual (sequence number do último evento aplicado). Ao tentar append:

```
appendEvents(aggregateId, expectedVersion, newEvents):
  currentVersion = store.getVersion(aggregateId)
  if currentVersion != expectedVersion:
    throw ConcurrencyException(currentVersion, expectedVersion)
  store.append(aggregateId, newEvents, currentVersion + len(newEvents))
```

Quem começou o comando com versão V espera commitar em V+1, V+2, ... Se outro writer commitou no meio, o segundo falha.

### Conflict resolution (`ConflictsWith()` pattern)

Falhar direto em toda concorrência é caro. Muitos conflitos são **inocentes** — eventos concorrentes que não interferem entre si.

Vernon propõe checagem semântica: "os eventos que aconteceram desde que carreguei o aggregate **conflitam** com o que eu quero fazer?"

```
handle(cmd):
  aggregate = store.load(cmd.aggregateId)         // carrega e aplica todos os eventos
  versionAtLoad = aggregate.version
  newEvents = aggregate.handle(cmd)               // domínio produz novos eventos

  try:
    store.append(cmd.aggregateId, versionAtLoad, newEvents)
  catch ConcurrencyException:
    eventsSinceLoad = store.eventsAfter(cmd.aggregateId, versionAtLoad)
    if anyConflictsWith(newEvents, eventsSinceLoad):
      throw ConflictException  // caller decide se falha ou refaz
    else:
      retry(cmd)  // eventos concorrentes foram compatíveis; tenta de novo
```

Cada par de eventos tem regra: `BatteryWithdrawn conflitaCom BatteryWithdrawn` (mesma battery só pode sair uma vez); `PriceChanged` + `DescriptionUpdated` é compatível (atributos diferentes).

**Custo:** manter tabela de compatibilidade entre eventos. Vale em domínios com concorrência alta e regras claras; em domínios mais complexos, falhar e deixar o caller decidir é mais seguro.

### Retry com exponential backoff

Em conflitos genuínos, retry simples com backoff resolve muitos casos:

```
attempts = 0
while attempts < maxAttempts:
  try:
    return handle(cmd)
  catch ConcurrencyException:
    attempts += 1
    sleep(baseDelay * 2^attempts + jitter)
throw MaxRetriesExceeded
```

Regras:
- `baseDelay` ~50-100ms; `maxAttempts` 3-5; jitter aleatório ±30% pra evitar thundering herd
- Só faça retry se o handler for idempotente semanticamente (rerodar não duplica evento indevido)
- Log todos os retries em observabilidade — retries altos = contenção estrutural, não concorrência saudável

---

## Snapshots — quando e como

`[IDDD Apêndice A]`

Aggregate com 100k eventos leva segundos pra reconstituir por replay. Solução: snapshot periódico do estado derivado.

### Estratégia comum

- **A cada N eventos** (ex.: N=100). Snapshot armazenado em tabela paralela: `(aggregateId, version, serializedState)`.
- Ao carregar: pega snapshot mais recente + eventos após a versão dele. Replay só da diferença.

### Trade-offs

- **Prós:** load rápido mesmo em aggregates de vida longa; memória controlada.
- **Contras:** snapshot pode ficar inválido após refactoring do modelo (serialização ligada a classes); versionamento de snapshot obrigatório; tabela de snapshots tem own size.

### Armadilhas

- **Snapshot como fonte de verdade** — nunca. Eventos sempre são a verdade; snapshot é cache.
- **Snapshot síncrono no write path** — piora latência. Faça em worker assíncrono após commit.
- **Ignorar versão de snapshot ao refactor** — se mudou o formato serializado, invalidate snapshots antigos; domain ainda é reconstrutível via replay (mais lento até novo snapshot).

---

## Master/Clone replication

`[IDDD Apêndice A]`

Pra leitura de event store em alta escala:

- **Master** aceita writes (único ponto de append com versionamento)
- **Clones** (read replicas) recebem eventos propagados e servem queries
- Write-through (sync): master só responde OK após N clones replicarem — consistência maior, latência maior
- Write-behind (async): master responde OK imediato; replicação eventual — latência menor, janela de staleness

**Escolha:** compliance/financeiro → write-through (zero perda). Analytics/dashboards → write-behind (staleness aceitável).

Event store moderno (EventStoreDB, Kurrent, Axon Server, Marten+Postgres) oferece ambos como config.

---

## Checklist antes de adotar CQRS/ES

- [ ] O time entende eventual consistency e sabe comunicar isso à UX?
- [ ] O negócio aceita delay (segundos-minutos) em queries derivadas?
- [ ] Há auditoria/histórico como requisito real (não "nice to have")?
- [ ] Queries estão hoje dificultando write model? (evidência, não especulação)
- [ ] Time tem capacidade operacional pra manter event store + projeções?
- [ ] Schema de eventos é tratado como API pública (contrato estável, versionado)?

Se 3+ sim, avalie. Se menos, mantenha CRUD + Domain Events pontuais.
