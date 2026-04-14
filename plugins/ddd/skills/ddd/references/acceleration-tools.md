# Acceleration Tools — SWOT, estimativas, spikes, timeboxing

> **Fonte primária:** Vaughn Vernon, *Domain-Driven Design Distilled* (Addison-Wesley, 2016), cap. 7 "Acceleration and Management Tools". Complementos: `[IDDD]` em tópicos correlatos.
> Todos os créditos de conteúdo original vão aos autores. Esta reference é síntese em pt-BR organizada para consulta dentro da skill DDD.

Technique mais úteis pra **entregar DDD sob pressão de tempo**, sem perder rigor. Muita equipe trava em "paralisia de análise" tentando desenhar modelo perfeito; essas ferramentas forçam decisão mensurável em horas.

---

## 1. SWOT Analysis aplicada ao domínio

`[Distilled cap.7]`

SWOT clássico (Strengths / Weaknesses / Opportunities / Threats), mas aplicado ao **modelo de domínio** + **estratégia de Core Domain**. Responde: onde investir modelagem profunda agora.

### Como rodar (60-90 min)

1. **Matriz 2×2** na parede/board digital. Stickies coloridas por quadrante (ex.: verde Strengths, amarelo Weaknesses, azul Opportunities, vermelho Threats).
2. **Participantes:** mesmos do event storming (domain experts + devs + PM). Sem espectadores.
3. **Timebox 15 min por quadrante**, nessa ordem:
   - **Strengths** — o que o modelo atual (ou conhecimento do time) acerta? Onde a linguagem ubíqua já é clara?
   - **Weaknesses** — onde o modelo é confuso, anêmico, tem BBoM, linguagem fragmentada?
   - **Opportunities** — regulações novas, integrações futuras, core domain que pode virar diferencial
   - **Threats** — concorrência, débito técnico que vai estourar, dependência de legado instável
4. **Cruzamento final (15 min):** combine quadrantes — ex.: "Strength X + Opportunity Y = primeiro contexto a investir"; "Weakness Z + Threat W = primeiro ponto de ACL".

### Saída

- Lista priorizada de **áreas de modelagem profunda** (core domain real vs. achado)
- Lista de **riscos arquiteturais** (vai virar dívida se não atacar)
- Insumo direto pro backlog de refinamento do Event Storming

### Quando usar

- Início de projeto (antes do primeiro Event Storming serve pra alinhar foco)
- Após 2-3 sprints, quando o time quer revisar o rumo
- Preparação de decisão arquitetural grande (monolito → modular, ou migração legacy)

### Armadilhas

- SWOT virar "brainstorm genérico" — foque em modelo/domínio, não em "cultura" ou "processo ágil".
- Não parar no diagnóstico — o cruzamento é o valor real.

---

## 2. Metrics-Based Estimation via Event Storming

`[Distilled cap.7]`

Depois do Big Picture Event Storming, você tem stickies. Conte e estime.

### Fórmula de referência (valores típicos, calibre com histórico do time)

| Artefato (sticky) | Esforço típico por unidade |
|-------------------|----------------------------|
| Domain Event (laranja) | 1-2h implementação + teste |
| Command (azul) | 2-4h (App Service + transação + validação) |
| Aggregate novo (amarelo) | 1-3 dias (dependendo de invariantes) |
| Policy (lilás/roxo) | 4-8h (handler + testes) |
| External System integration (rosa) | 1-3 dias (ACL/OHS + contract tests) |
| Read Model / View (verde) | 2-6h por projeção |
| Hotspot vermelho não resolvido | **Modeling spike** — 2-4h investigação antes de estimar |

### Fator multiplicador

- **×1.0** time experiente em DDD, stack madura, domínio conhecido
- **×1.3-1.5** time aprendendo DDD
- **×1.5-2.0** stack nova (event broker, messaging, CQRS/ES pela primeira vez)
- **×2.0-3.0** legado com ACL complexa, compliance regulatório

### Exemplo

Event Storming do contexto "Faturamento" produziu:
- 12 Domain Events × 1.5h = **18h**
- 8 Commands × 3h = **24h**
- 3 Aggregates × 2 dias = **48h**
- 4 Policies × 6h = **24h**
- 2 External integrations × 2 dias = **32h**
- 5 Read Models × 4h = **20h**
- 2 Hotspots → 6h spikes = **6h**

Total bruto: **172h**. Time aprendendo DDD × 1.4 = **~240h ≈ 6 sprints**.

Não confunda com estimativa final — é **baseline inicial** pra conversa com PM/PO. Refine por sprint.

### Benefícios

- Força o time a **contar** o que conhece, expondo o que ignora (stickies "vagos" demais viram spikes)
- Linguagem comum com PM que não conhece DDD ("cada sticky amarelo custa em média X dias")
- Histórico evolui: sprint a sprint, calibra os valores com throughput real do time

---

## 3. Modeling Spikes vs. Modeling Debt

`[Distilled cap.7]`

**Modeling Spike** = investigação timeboxed (ex.: 4-8h) pra reduzir incerteza sobre uma parte do domínio antes de implementar. Saída é **aprendizado documentado**, não código. É investimento consciente.

**Modeling Debt** = decisão de *não* modelar profundamente agora, aceitando que o modelo vai ficar raso até compensar. É empréstimo consciente — tem que virar backlog explícito.

### Spike — quando fazer

- Hotspot vermelho do event storming que ninguém do time conseguiu resolver
- Conceito de domínio com vocabulário ambíguo (ex.: "Order" significa coisas diferentes em contextos diferentes — precisa explorar antes de codar)
- Invariante suspeita de envolver regulação (não chute — confirme com domain expert + leia a norma)
- Integração com sistema externo onde não se sabe quais eventos recebe ou em que formato

**Formato do spike:** 1 dev + 1 domain expert, 4-8h, saída é **documento de 1 página** com: pergunta investigada, opções consideradas, decisão recomendada, dúvidas remanescentes. Vira ADR se a decisão é arquitetural.

### Debt — quando aceitar

- Feature urgente, janela apertada (promoção sazonal, compliance com deadline)
- Core domain ainda não está claro — implementa raso, marca como debt, refatora pra insight profundo depois
- Integração temporária com legado: ACL simplificada que vai morrer em 6 meses

**Regra:** toda debt tem que ir pra backlog com **nome**, **juros** (o que piora se não pagar), **vencimento** (evento que obriga quitar).

### Armadilha

Debt sem nome vira BBoM. Spike sem escopo vira gold plating. Ambos têm timebox curto e saída escrita.

---

## 4. Timeboxed Modeling

`[Distilled cap.7]`

Não gaste semanas modelando antes de escrever código. DDD funciona em ciclos curtos:

### Ciclo semanal sugerido

- **Seg (90 min):** Event Storming ou design-level storming do próximo contexto/fatia
- **Ter–Qui:** implementação (code é fonte de verdade do modelo)
- **Sex (60 min):** retrospectiva do modelo — a linguagem ubíqua segurou? novos termos apareceram? o agregado cresceu demais?

Cada ciclo gera **1 ADR** (se mudou algo estrutural) + **1 atualização no glossário/UL**.

### Regras de ouro

1. **Modelagem sem código é teatro.** Se sprint inteira não gerou código que roda, a modelagem provavelmente foi abstrata demais.
2. **Toda refatoração do modelo tem que nascer de um insight concreto** (bug, feature que não encaixou, pergunta do domain expert). Refatorar "porque ficaria mais bonito" é overengineering.
3. **Backlog de refinamento é vivo** — stickies vermelhos do event storming, débitos de modelagem, spikes a fazer. Vira topo da retro de sexta.
4. **Se o time está travado modelando há mais de 1 ciclo no mesmo problema**, é sinal de spike ou de dividir em contextos menores.

---

## 5. Checklist de aceleração

Use no início de projeto novo e a cada 3 sprints:

- [ ] Rodamos SWOT do modelo/domínio nos últimos 3 meses?
- [ ] Temos estimativa baseada em artefatos de event storming? Calibramos com throughput real?
- [ ] Hotspots do event storming viraram spikes com timebox?
- [ ] Toda debt de modelagem tem nome + vencimento no backlog?
- [ ] Ciclos de modelagem estão timeboxed (< 1 semana por fatia)?
- [ ] Glossário de UL foi atualizado nesse sprint?
- [ ] ADRs cobrem as últimas decisões arquiteturais do modelo?

Se 3+ respostas "não", rode uma sessão de acceleration tools antes da próxima sprint.

---

## 6. Integração com outros modos da skill

- **Modo 2 (Strategic Design)** — SWOT é pré-workshop ou complemento ao Event Storming Big Picture; estimativas saem do storming consolidado.
- **Modo 3 (Spec de conversão)** — fase 0 da spec usa SWOT + estimativas pra priorizar qual bubble context atacar primeiro.
- **Modo 1 (Analysis)** — achados do relatório podem gerar spikes / debt items pra backlog.

Ver também: `event-storming.md`, `legacy-migration.md` (onde debt de modelagem frequentemente vive), `project-conversion-spec.md` (fase 0 incorpora essas ferramentas).
