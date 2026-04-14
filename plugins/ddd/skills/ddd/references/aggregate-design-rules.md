# Aggregate Design — as 4 regras de Vernon

Fonte primária: `[IDDD cap.10]` ("Effective Aggregate Design"). Complementos: `[Distilled cap.5]`.

Aggregate é o conceito tático que mais dá errado. Agregados grandes demais matam performance e concorrência; agregados pequenos demais forçam operações cross-aggregate em transação. Vernon formalizou 4 regras que resolvem isso.

---

## Regra 1 — Modele invariantes verdadeiras em consistency boundaries

**O que é invariante:** condição que deve ser verdadeira ao final de toda operação (início e fim da transação). Não durante — durante pode ficar temporariamente inconsistente.

**Como aplicar:**
1. Pergunte: que regra de negócio exige que A e B sejam coerentes *no mesmo instante*?
2. Se a resposta for "imediatamente, sempre" → estão no mesmo aggregate.
3. Se a resposta for "eventualmente, em segundos/minutos" → aggregates diferentes, coordenados por Domain Event.

**Exemplo `[IDDD cap.10]`:**

```
BacklogItem { status, sprintId }  // invariante: status=COMMITTED ⟹ sprintId != null
```
A invariante exige que a transição seja atômica. Logo, `commitTo(sprint)` muda os dois campos juntos dentro do mesmo aggregate.

**Armadilha:** confundir "requisito do DB" ("preciso de ACID nessas duas tabelas") com "invariante de negócio". Requisito de DB vem do design; invariante vem do negócio. Pressão por "consistência imediata em tudo" é sinal de dev/DBA dirigindo o modelo, não o domain expert.

---

## Regra 2 — Desenhe pequenos agregados

**Por quê:**
- Menor contenção otimística (optimistic concurrency check falha menos)
- Carga de memória menor, GC mais rápido
- Transações mais curtas e confiáveis
- Testes mais simples (menos setup)

**Heurística operacional:**
- Comece com **uma única Entity como Aggregate Root** + VOs intrínsecos
- Só adicione Entities filhas se houver invariante real exigindo
- Se filhos crescem sem limite (ex.: `Product` com milhares de `BacklogItem`), é sinal claro de quebrar

**Sinais de aggregate gigante:**
- Carregar o agregado traz 100+ objetos
- Operações simples tocam 50%+ do estado
- Profundidade > 3 níveis de composição
- Versão otimística conflita frequentemente entre usuários

**Como quebrar:** identifique se um "filho" tem vida própria (ciclo de vida independente, regras próprias) — ele é outro agregado. Relacione via ID.

---

## Regra 3 — Referencie outros agregados por identidade, nunca por referência direta

**Errado:**
```
class Order {
  Customer customer;              // referência direta ❌
}
```

**Certo:**
```
class Order {
  CustomerId customerId;          // só o ID ✓
}
```

**Por quê `[IDDD cap.10]`:**
- Cada agregado é carregado/persistido independente
- Permite diferentes storage por agregado (relacional, documento, KV)
- Transações ficam naturalmente restritas a um agregado
- Evita "travessia" acidental que carrega grafo inteiro
- Habilita distribuição (agregados podem viver em nós diferentes)

**Se precisa dos dados do outro agregado:** carregue explicitamente via Repository no Application Service, **antes** de chamar o método do agregado. O domínio recebe VOs/IDs, não outros agregados.

---

## Regra 4 — Use eventual consistency fora do boundary

**Mantra Vernon:** "one transaction per aggregate".

**Como:**
1. O agregado A conclui sua operação e emite Domain Event
2. Application Service commit a transação do A + outbox do evento
3. Subscriber recebe o evento (mesmo processo ou via messaging) e em **transação separada** atualiza agregado B

**Janela de eventual consistency:** o negócio define o aceitável. Pode ser "imediato" (mesmo processo, síncrono depois do commit) ou "minutos" (messaging entre serviços). Quase nunca é "zero".

**Quando você acha que precisa de consistência imediata entre aggregates:** revise regra 1. Provavelmente estão no aggregate errado OU você está sobrestimando a necessidade.

**Exceção legítima:** initialização atômica (criar A e B ao mesmo tempo como parte da mesma operação conceitual) — ainda assim, considere um "Creation Service" que emite ambos, ou repensar se é um agregado só.

---

## Invariantes — onde morar

**Dentro do aggregate (cumpridas pelo Root):**
- Consistência entre filhos e VOs do próprio aggregate
- Transições de estado do próprio aggregate

**Fora do aggregate (cumpridas por outra mecânica):**
- Invariantes "globais" (ex.: "só um cliente com esse CPF no sistema inteiro") → unique constraint no DB + verificação no Application Service antes de criar. Não é invariante de aggregate.
- Invariantes cross-aggregate (ex.: "estoque ≥ reservas") → resolva com Domain Event + Process Manager / Saga, eventual consistency.

---

## Processo de right-sizing (Vernon)

1. **Start small:** cada aggregate candidate começa com 1 Entity + VOs intrínsecos
2. **Liste reações:** "quando A muda, o que deveria mudar como consequência?"
3. **Pergunte o timeframe ao domain expert:** imediato ou pode aceitar segundos?
4. **Imediato** → compor no mesmo aggregate; **eventual** → separar + Domain Event
5. **Itere:** revise sempre que surgir requisito novo

---

## Anti-padrões específicos de aggregate

- **God Aggregate** — root com 50+ campos, dezenas de filhos. Quebrar.
- **Aggregate sem invariante real** — "parece que X e Y ficam junto" sem regra de negócio. É só conveniência — separe.
- **Cross-aggregate Loop** — evento em A trigger evento em B que trigger evento em A. Design smell; revise quem é realmente dono do estado.
- **Repository dentro de Aggregate** — injetar repository pra "lazy load" filhos. Quebra isolamento, acopla com persistência. Não faça. Carregue antes e passe os dados.
- **Aggregate como tabela** — 1:1 com tabela relacional. Erra em dois sentidos: (a) força VOs a virarem tabelas (b) não respeita invariantes. O modelo dirige o schema, não o contrário.

---

## Checklist rápido pra revisar aggregate existente

- [ ] Tem um único Aggregate Root (Entity) claro?
- [ ] Referências externas vão pro Root apenas?
- [ ] Outros aggregates são referenciados por ID (não por objeto)?
- [ ] Tamanho razoável? (carregamento rápido, poucos objetos)
- [ ] Invariantes do aggregate declaradas em código/teste?
- [ ] Transações tocam apenas este aggregate?
- [ ] Operações inter-aggregate usam Domain Events + eventual consistency?
- [ ] VOs são imutáveis?
