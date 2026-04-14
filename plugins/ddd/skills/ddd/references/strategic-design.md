# Strategic Design — Bounded Context, Subdomains, Distillation

Fontes: `[Evans Reference]`, `[Evans Rápido]`, `[IDDD cap.2-3]`, `[Distilled cap.2-4]`.

> DDD tático (aggregates, VOs) sobre strategic design frágil é desperdício. Se a ubiquitous language não existe ou os contextos não estão claros, comece aqui.

---

## Bounded Context — o ponto de partida

**Definição:** limite explícito onde um modelo específico é aplicado, com uma ubiquitous language coerente internamente. `[Evans Reference]`

**Sinais de limite correto** `[Distilled cap.2]`:
- Um time responsável (ideal 1 time : 1 contexto)
- Repositório de código separado ou módulo com fronteira física
- Ubiquitous language coesa — o mesmo termo tem um só significado
- Business drivers alinhados (setores departamentais, processos distintos)
- Schema de banco próprio (ou schema lógico claro no modular monolith)

**Sinais de limite ERRADO**:
- Mesmo termo com significados diferentes sem contexto marcado (ex.: "Product" em Vendas = SKU comercial; em Fulfillment = item físico embarcável — contextos diferentes, mesma palavra)
- Imports cruzados direto entre módulos que deveriam ser independentes
- Um PR toca 5+ "contextos" ao mesmo tempo
- Experts de negócio diferentes discordam sobre o significado canônico

**Heurística Vernon** `[IDDD cap.2]`: se a linguagem varia, os contextos são diferentes. Não é erro — é natural. Abrace com contextos explícitos.

---

## Ubiquitous Language — a cola

**Construção:**
1. Reuniões face a face com domain experts + devs
2. Extrair conceitos concretos a partir de cenários, não de diagramas abstratos
3. Refinar iterativamente; contradição revela conceito implícito faltando
4. Usar os termos em **código, testes, conversa, documentação**

**Sintomas de language quebrada:**
- Classes/tabelas/métodos com nomes técnicos ("ElementContainer", "ProcessManager") em vez de domínio
- Devs e business falam idiomas distintos em reunião
- Documentação desatualizada (o código deveria ser a fonte de verdade)

**Escopo da linguagem:** é válida **dentro** de um bounded context. Não tente forçar linguagem global em todo o ERP — é o erro clássico do "modelo canônico da empresa".

---

## Subdomains — onde investir

| Tipo | Característica | Investimento | Quem trabalha |
|------|----------------|--------------|---------------|
| **Core** | Diferenciador competitivo | Máximo | Melhor talento, modelagem profunda |
| **Supporting** | Necessário, não diferenciador, sem solução pronta boa | Moderado | Time médio, código limpo sem overengineering |
| **Generic** | Problema padrão (auth, contabilidade básica) | Mínimo | Comprar / biblioteca / COTS |

**Critérios de classificação** `[Distilled cap.3]`:
1. Valor estratégico — o negócio ganha mercado por causa disso?
2. Requer knowledge acquisition profunda no domínio?
3. Há solução madura no mercado?
4. Mudanças nessa área impactam outros subdomínios?

**Armadilha clássica:** tratar subdomínio genérico como core. Resultado: gastar anos reinventando contabilidade. Compre.

**Armadilha oposta:** tratar core como supporting. Resultado: o diferenciador fica fraco, concorrente ultrapassa.

---

## Distillation — extrair o core

Padrões derivados de `[Evans Reference]`:

- **Domain Vision Statement** (1 página) — o que o sistema faz de único no mercado. Escreva antes de modelar.
- **Highlighted Core** — marque visualmente, no código e na doc, o que é core. Onboarding de dev novo tem que encontrar o core em menos de 10 minutos.
- **Segregated Core** — refatoração física: separe módulos/pastas/repo core dos de suporte. Não misture.
- **Abstract Core** — quando o core tem múltiplos subdomínios que interagem, isole as interfaces em módulo próprio.

**Teste de sanidade:** se o time não souber dizer em uma frase o que é o core, o projeto ainda não está pronto para DDD tático.

---

## Relação Subdomain (problema) ↔ Bounded Context (solução)

Ideal: **1 subdomain = 1 bounded context**. `[IDDD cap.2]`

Realidade: legacy systems frequentemente violam essa regra. Use Context Map pra documentar a realidade atual e o alvo.

---

## Como identificar bounded contexts na prática

**Técnicas combinadas** `[DDD Crew Starter Process]`:

1. **Event Storming Big Picture** (2-4h) — descobrir eventos do negócio, clusters temporais revelam contextos.
2. **Domain Message Flow Modelling** — traçar quem envia/recebe mensagens (comandos, eventos). Cada fluxo fechado tende a ser um contexto.
3. **Conversational analysis** — ouvir calls de suporte, vendas, ops. Mudança de vocabulário = mudança de contexto.
4. **Heatmap de mudança** — regiões do código que mudam juntas no git log ao longo de 12 meses. Cohesion temporal é sinal.

---

## Armadilhas de strategic design

- **"Modelo canônico da empresa"** — tentar fazer uma só classe `Customer` que vale em vendas, financeiro, suporte. Cai em anemic ou em Deus Object. Não faça.
- **Microserviço por tabela** — se os serviços têm schema compartilhado, não são contextos separados. É distributed monolith. Ver `architecture-styles.md`.
- **Strategic design de uma vez só** — você não descobre todos os contextos no dia 1. Começa com 2-3 óbvios e refatora conforme aprende.
- **Confundir bounded context com microserviço** — contexto é conceito de modelagem. Pode ser módulo num monolito modular. Decisão de deploy é independente. `[prática pós-2020]`

---

## Domain Vision Statement — template

`[Evans Reference]`

Documento de **1 página** que descreve o Core Domain e sua proposição de valor. Lido por todo stakeholder (business, tech, design). Alinhamento em 10 minutos de leitura.

### Estrutura

```markdown
# <Nome do Domain>

## O problema (1 parágrafo)
Descreva o problema de negócio real que o sistema resolve. Em linguagem de negócio, sem referência a tecnologia. Quem sofre? O que dói hoje?

## Quem usa (bullets)
- <Papel 1> — o que faz com o sistema
- <Papel 2> — ...

## O que diferencia (o core)
Em 2-4 bullets, o que este sistema faz **melhor ou diferente** do mercado. É essa parte que justifica investimento em modelagem profunda.
- <Diferenciador 1>
- <Diferenciador 2>

## O que NÃO é escopo
Explicitamente fora: o que outros sistemas fazem que este não fará. Evita expansão acidental do core.

## Métricas de sucesso
2-3 métricas de negócio (não técnicas) que indicam que o sistema cumpre a proposição. Evite vaidade; prefira impacto.
```

### Exemplo curto (fictício)

```markdown
# Battery Lifecycle Management — JRC

## O problema
Técnicos marítimos precisam saber, a qualquer momento, quais baterias de segurança
(EPIRB, AIS, SART) em suas embarcações estão dentro da validade regulatória. Hoje isso
é feito em planilhas, com erros que custam multas de GMDSS e risco à tripulação.

## Quem usa
- Técnico de campo — consulta status, registra saída de bateria pra navio
- Gerente de estoque — acompanha vencimentos, planeja reposição
- Auditor — rastreia histórico pra compliance SUSEP/ANTAQ

## O que diferencia
- Cálculo automático de shelf time e service time por modelo de bateria
- Eventos publicados para integração com manutenção e compras (reposição automática)
- Rastreabilidade completa de 20 anos (regulatório)

## O que NÃO é escopo
- Gestão de embarcações ou tripulação (é Frota)
- Contabilidade/depreciação (é Financeiro, consome eventos)
- Manutenção preventiva de equipamentos (é Manutenção)

## Métricas de sucesso
- 0% de baterias vencidas em operação (compliance)
- Redução de 50% no tempo de auditoria regulatória
- Reposição automática iniciada ≤ 30 dias antes do vencimento
```

### Antipadrões

- **Versão técnica** — "usa PostgreSQL + RabbitMQ + CQRS" → errado, não fala com business
- **Marketing** — "o melhor sistema de batteries do mundo" → vazio, não ajuda decisão
- **Longo** — 10 páginas ninguém lê; a regra é 1 página
- **Nunca revisado** — Domain Vision evolui com aprendizado; revisite a cada trimestre

---

## Abstract Core — quando os subdomínios se tocam

`[Evans Reference]`

Em domínios complexos, o Core se compõe de múltiplos subdomínios que **interagem** entre si. Se cada um tiver modelo próprio sem interface comum, integração explode em acoplamento.

Abstract Core: extrair interfaces e classes abstratas que descrevem as interações **no nível conceitual**, ficando em módulo próprio.

```
abstract-core/              (módulo)
  PolicyHolder              (interface abstrata)
  Claim                     (interface abstrata)
  Premium                   (interface abstrata)
  events/PolicyIssued       (evento canônico)
  events/ClaimFiled

subdomain-auto/             (consome abstract-core)
  AutoPolicy implements PolicyHolder
  ...

subdomain-life/             (consome abstract-core)
  LifePolicy implements PolicyHolder
  ...
```

Subdomínios comunicam-se **via interfaces do Abstract Core**, não por dependências diretas entre si. Escalável, testável, evoluível.

**Quando vale:** sistemas grandes, múltiplos subdomínios Core interagindo.
**Quando não vale:** sistema simples, 1-2 subdomínios — Abstract Core vira overengineering.

---

## Continuous Integration — pattern estratégico entre times

`[Evans Reference]`

Além do conceito técnico (CI/CD), Evans trata Continuous Integration como **pattern estratégico**: times que dividem um Bounded Context ou Shared Kernel precisam integrar mudanças continuamente, não em big-bangs trimestrais.

- Mesmo contexto, múltiplos devs → merge diário no main, testes de UL passando
- Shared Kernel entre contextos → integração contínua do kernel; cada mudança passa por ambos os times
- Ausência → drift de modelo, merge horroroso, integração que vira projeto

Ver `refactoring-and-insights.md` §8 (CI do modelo) pra práticas concretas.

---

## Output típico de uma sessão de strategic design

- 1 Domain Vision Statement (curto)
- 1 tabela de Subdomains (Core/Supporting/Generic)
- 1 Context Map inicial (draft, será refinado)
- 1 lista de candidatos a bounded context com owner sugerido
- 1 recomendação de estilo arquitetural (ver `architecture-styles.md`)
- 1 backlog de refinamento (workshops próximos, eventos que ficaram ambíguos)
