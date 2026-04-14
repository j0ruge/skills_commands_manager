# Legacy → DDD — estratégia de migração incremental

Fontes: `[IDDD cap.3]`, `[Distilled cap.3]`, Nick Tune (medium.com/nick-tune-tech-strategy-blog), Martin Fowler (Strangler Fig), DDD Crew.

**Princípio rígido:** jamais "reescrever tudo". Migração é incremental, mensurável, com rollback possível em cada passo. Time tem que entregar valor durante a migração.

---

## Padrões canônicos

### Strangler Fig Pattern (Fowler)

Sistema novo cresce "estrangulando" o legacy, roteando progressivamente tráfego/uso do velho pro novo. Quando o novo cobre tudo, aposenta o velho.

**Como aplicar:**
1. Identifique uma fatia (feature, endpoint, bounded context candidato)
2. Implemente essa fatia em módulo novo (com DDD)
3. Redirecione tráfego/chamadas dessa fatia pro módulo novo (via proxy, feature flag, roteador)
4. Monitore paridade (comportamento, performance, correção)
5. Remova a implementação antiga dessa fatia
6. Escolha próxima fatia, repita

**Ferramenta:** proxy/gateway (API gateway, BFF) pra rotear por rota ou feature flag.

### Bubble Context (Nick Tune)

Pequeno bounded context novo, bem modelado em DDD, **vive dentro do legacy** cercado por ACL.

Toda integração com o legacy passa pela ACL — o bubble nunca importa tipos do legacy. O bubble cresce; outros bubbles aparecem; eventualmente o legacy vira ilha.

**Quando usar:**
- Precisa entregar feature nova no meio do legacy
- Não dá pra fatia vertical completa (strangler) ainda
- Quer provar DDD em escopo contido antes de escalar

**Anti-sinal:** bubble parou de crescer. Ou o time perdeu foco, ou o domínio não é adequado, ou a ACL foi negligenciada.

### Anti-Corruption Layer (ACL) — isolamento

Use sempre que há interação entre código DDD novo e legacy. ACL:
- Define o modelo interno limpo do lado novo
- Traduz DTOs/models do legacy → VOs/aggregates locais
- Protege o core de corrupção semântica

**Implementação minimalista:**
- Um Domain Service no bounded context novo, nomeado pelo conceito traduzido (ex.: `CustomerAccountTranslator`)
- Depende de interface (port) que o adapter implementa chamando o legacy
- Retorna VOs/entities do modelo novo — nunca tipos do legacy

---

## Abordagem geral pra ERP legacy

Fases típicas (Nick Tune, adaptado):

### Fase 0 — Arqueologia (1-3 semanas)
- Eventstorming retroativo: mapear como o legacy opera hoje (eventos que acontecem de fato)
- Context Map atual: o que existe como "contexto" implícito, mesmo que BBoM
- Core Domain hoje: onde está o valor real (pode não ser onde o código acha que está)
- Identificar **hotspots**: onde mudança é mais cara, bugs mais frequentes, time mais ansioso

### Fase 1 — Primeira fatia (1 quarter)
- Escolher 1 bounded context pequeno e relevante pra começar (ideal: core domain, ou pelo menos supporting com alto ROI)
- Implementar como bubble context ou strangler de fatia pequena
- Cercar com ACL total — zero imports do legacy no novo
- Estabelecer padrões (layout de módulo, testes, ubiquitous language) que vão ser usados pelos próximos

### Fase 2 — Crescimento (ongoing)
- Cada novo feature grande = candidato a novo bounded context ou expansão do existente
- Todo código novo tem que ter bounded context explícito e pattern de integração claro com o resto
- Backlog de "decommission legacy": partes do legacy que podem ser removidas à medida que o novo cobre

### Fase 3 — Consolidação
- Legacy encolheu a ponto de ser um bounded context entre outros (agora nomeado, delimitado, com ACL)
- Ou foi completamente aposentado

---

## Ordem de ataque — quais contextos migrar primeiro

Matriz 2x2: **valor estratégico** × **dor atual**.

| | Baixa dor | Alta dor |
|---|-----------|----------|
| **Alto valor** | Segundo | **Primeiro** |
| **Baixo valor** | Último | Terceiro (ou terceirize/COTS) |

**Primeiro**: core domain que está doendo. Migração cria valor competitivo e alivia problema agudo.
**Segundo**: core domain estável. Não urgente, mas importante modernizar.
**Terceiro**: dor alta em subdomain de suporte — considere COTS em vez de migrar.
**Último**: subdomain genérico estável — deixa quieto ou substitui por biblioteca.

---

## Anti-padrões de migração

- **"Big bang" reescrita** — alta probabilidade de morrer. Não faça.
- **"Copiar e evoluir"** — clonar tabelas/models do legacy no novo, esperando refatorar depois. Resultado: mesmo modelo anêmico com nova tecnologia.
- **ACL parcial** — algumas partes usam tipos do legacy "só dessa vez". A ACL vira queijo suíço, modelo novo polui, desiste.
- **Sem métricas de paridade** — migra sem testes comparativos. Descobrem bug em produção, confiança desaba.
- **Ignorar dados** — DDD model novo perfeito, mas a migração de dados é gambiarra. Model e dados precisam do mesmo cuidado.
- **Strategic design só uma vez** — define contextos na fase 0 e nunca revisita. Contextos evoluem com aprendizado.

---

## Métricas pra acompanhar migração

- % de tráfego/requests servido pelo modelo novo
- % de features novas em módulo novo vs. legacy
- Tempo pra entregar nova feature (deve cair)
- MTTR de bugs na área migrada (deve cair)
- Tamanho de ACL (cresce no começo, estabiliza, idealmente diminui com o legacy encolhendo)
- Dívida técnica medida no legacy (deve diminuir ou ser aposentada, não crescer)

---

## Data migration — o elefante na sala

Bounded contexts novos frequentemente têm modelo de dados diferente. Opções:

- **Shared DB (fase de transição)**: novo lê/escreve em tabelas do legacy via ACL. Aceitável **por tempo limitado**. Nunca fim.
- **Sync dual-write**: operação escreve em ambos. Arriscado (inconsistência). Use com feature flag pra validar, não como arquitetura duradoura.
- **Migration por evento**: novo consome Domain Events do legacy (capturados via CDC — change data capture) e constrói seu próprio modelo.
- **Backfill + cutover**: migração em lote de dados históricos + cutover de escrita numa janela de manutenção.

`[prática pós-2020]`: CDC (Debezium + Kafka) é a ferramenta comum pra expor o legacy como fonte de eventos sem mexer no código dele.

---

## Recursos canônicos

- Nick Tune, "Legacy Architecture Modernisation With Strategic Domain-Driven Design" (medium)
- Martin Fowler, "Strangler Fig Application" (martinfowler.com)
- Sam Newman, *Monolith to Microservices* (livro; aplica a modular monolith também)
- Vaughn Vernon, "Strategic Design Essentials" workshops (vlingo)
- DDD Crew: `github.com/ddd-crew/core-domain-charts` pra priorizar
- Livro recente: *Domain-Driven Transformation* (O'Reilly, Plöd et al.)
