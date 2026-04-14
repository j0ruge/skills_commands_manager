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

## Checklist antes de adotar CQRS/ES

- [ ] O time entende eventual consistency e sabe comunicar isso à UX?
- [ ] O negócio aceita delay (segundos-minutos) em queries derivadas?
- [ ] Há auditoria/histórico como requisito real (não "nice to have")?
- [ ] Queries estão hoje dificultando write model? (evidência, não especulação)
- [ ] Time tem capacidade operacional pra manter event store + projeções?
- [ ] Schema de eventos é tratado como API pública (contrato estável, versionado)?

Se 3+ sim, avalie. Se menos, mantenha CRUD + Domain Events pontuais.
