# Refatoração para Insight Profundo e Integridade do Modelo

> **Fontes:** Eric Evans, *Domain-Driven Design: Tackling Complexity in the Heart of Software* (Addison-Wesley, 2003) — partes III-IV. Eric Evans, *Domain-Driven Design Reference* (capítulos sobre Refactoring Toward Deeper Insight, Maintaining Model Integrity). Eric Evans, *Domain-Driven Design Rápido* (síntese pt-BR).
> Créditos de conteúdo original a Eric Evans. Esta reference é síntese em pt-BR organizada para consulta dentro da skill DDD.

Um modelo que não evolui degrada. Entender **quando** refatorar por insight (não por estética de código) e **como** manter integridade do modelo ao longo de anos é o que separa DDD aplicado de DDD teórico.

---

## 1. Dois tipos de refatoração

### Refatoração técnica (Fowler)

Melhorar estrutura do código **sem mudar comportamento observável**. Regras mecânicas: extract method, rename, move class. Ferramenta ajuda (IDE), cobertura de teste protege.

Importante mas **insuficiente** pra DDD. Modelo anêmico com refatoração técnica perfeita continua anêmico.

### Refatoração pra Insight Profundo (Evans)

Mudar o **modelo** — conceitos, relações, vocabulário — quando o entendimento do domínio amadureceu. Não é mecânica: depende de descobrir algo novo sobre o negócio.

Sinal: o time descobriu que um conceito existia há meses mas estava escondido em `if` aninhado, em método com nome técnico, em coleção genérica. Tornar esse conceito **objeto de primeira classe** é refatorar pra insight profundo.

---

## 2. Deeper Insight — como acontece

`[Evans DDD, parte III]`

Três gatilhos comuns:

### Gatilho 1 — Conceito implícito insistente

A mesma regra aparece espalhada em vários lugares. Ex.: "desconto só vale de seg-sex, das 9h às 18h, exceto feriados" aparece em `OrderService`, `PricingEngine`, `PromotionValidator`. Insight: isso é um conceito — `BusinessHours` ou `ValidityWindow` — merece ser VO com `includes(moment)`.

### Gatilho 2 — Vocabulário do domain expert não mapeia no código

Domain expert diz "apólice em carência" e os devs traduzem pra `Policy.status == 'PENDING' && Policy.startDate > now - 30d`. Se o expert usa um termo com peso, o código deveria ter o mesmo termo como conceito.

### Gatilho 3 — Uma mudança simples toca muitos lugares

Se adicionar uma regra nova implica editar 12 classes, o modelo não comporta a mudança — falta abstração. Refatorar pra encontrar onde o conceito deveria morar.

---

## 3. Breakthrough — quando vários insights se acumulam

`[Evans DDD, parte III]`

Vários insights pequenos, acumulados ao longo de semanas, às vezes **convergem** em uma mudança maior que reorganiza o modelo inteiro. Evans chama isso de *breakthrough*.

Características:
- Time tinha a sensação de que "algo está estranho" há um tempo
- Um novo requisito ou conversa com expert destrava a visão
- A refatoração resultante é grande mas simplifica drasticamente — elimina código condicional, junta conceitos dispersos, renomeia com clareza nova

### Como facilitar (não forçar)

- Manter **conversas frequentes** com domain experts, mesmo sem feature ativa
- **Ler a literatura do domínio** — livros sobre logística, seguros, contabilidade, manufatura têm conceitos acumulados por décadas
- **Rejeitar atalhos** que mascaram confusão semântica ("vou colocar um flag `isSpecial` pra diferenciar"). Flags booleanas acumulados são sinal de conceito faltando.
- **Timebox modelagem** (ver `acceleration-tools.md`) — breakthrough não vem de paralisia de análise, vem de ciclos curtos de código + reflexão.

### Quando NÃO forçar

Refatoração pra insight exige **confiança no time e no código**. Se testes são ruins, se deploy é arriscado, se time está estressado, **não é hora de breakthrough**. Faça refatoração técnica antes pra criar espaço.

---

## 4. Model Integrity — pilares

`[Evans DDD, parte IV]`

Modelo íntegro = **coeso internamente** + **consistente em toda extensão onde se aplica**. Sem integridade, o modelo degrada mesmo com refatoração bem-feita.

Os 4 pilares:

### 4.1 Ubiquitous Language preservada

O mesmo termo tem o mesmo significado em **todo** o Bounded Context:
- Código (classes, métodos, variáveis)
- Testes (nomes e asserções)
- Conversa (reuniões, chat)
- Documentação

Quando a linguagem divaga, o modelo está perdendo integridade. Ex.: PM começa a usar "lead" em vez de "prospect"; dev mantém o código com `Prospect` — em 6 meses ninguém sabe mais qual é qual.

**Prática:** glossário da UL vivo, revisado a cada sprint. `references/glossary.md` do projeto, não no Notion.

### 4.2 Bounded Context claro

Cada contexto tem dono, linguagem própria, e fronteira respeitada. A integridade morre quando:
- Módulos começam a importar classes de outro contexto sem ACL
- Schema de banco tem foreign keys atravessando fronteiras
- "Classe compartilhada" cresce sem ninguém querer ser dono

**Prática:** testes de arquitetura (ArchUnit/NetArchTest) que quebram build se módulo A importa interno de B.

### 4.3 Context Map atualizado

Integrações entre contextos têm pattern explícito (ACL, OHS+PL, Conformist, etc. — ver `context-mapping.md`). Pattern "default" (sem nome) é BBoM emergente.

**Prática:** context map em markdown ou mermaid no repo, revisado trimestralmente.

### 4.4 Refatoração pra insight como hábito

Se nunca refatoramos o modelo, ele está defasado. Não precisa ser quarterly big-bang; pode ser melhoria em cada sprint.

---

## 5. Sinais de drift (modelo perdendo integridade)

Check mensal. 3+ sinais = pare e refatore antes de nova feature.

- **Vocabulary drift** — domain expert usa termo novo, código ainda tem termo antigo
- **Bug loops** — bugs similares reaparecem porque regra espalhada
- **PR gigante** — feature simples vira 30 arquivos modificados
- **Onboarding lento** — dev novo leva semanas pra entender o modelo; docs desatualizadas
- **Flags booleanas acumuladas** — `isX`, `hasY`, `isActive`, `isVerified` em Entity: provável conceito faltando
- **Comentários longos explicando "exceções"** — `// este status funciona diferente se ...` é sinal de conceito escondido
- **Services gigantes** — `FooService` com 800 linhas: orquestração roubou comportamento do domínio
- **Repository com 40+ métodos findBy** — modelo de leitura deveria ser CQRS ou o modelo está anêmico
- **Times evitam uma parte do código** — "ninguém mexe nisso, sempre quebra" é drift grave

---

## 6. Roteiro de refatoração pra DDD (diferente de clean code)

Quando decidir refatorar o modelo:

1. **Nomeie o insight em uma frase.** "Policy tem um conceito implícito de ValidityWindow que precisa existir como VO."
2. **Escreva o teste novo primeiro**, na nova linguagem — ele vai falhar. Se não conseguir escrever, o insight ainda é vago.
3. **Crie o conceito novo** como VO/Entity/Aggregate/Service, **pequeno**, isolado, com invariantes.
4. **Migre uso por uso** pro conceito novo. Nunca "big bang rewrite".
5. **Remova o conceito velho** quando não houver mais call sites. Mantenha testes velhos até a migração terminar.
6. **Atualize UL** — glossário, ADR, docs.
7. **Conte pro time.** Breakthrough individual não vira integridade do modelo; é a **linguagem comum** que garante.

Diferença crítica pra clean code: aqui o **nome** e o **conceito** importam mais que a forma. Clean code aceita `OrderProcessorHelper.calculateTax()`; DDD exige `TaxRule.applyTo(order)` porque `TaxRule` é um conceito do negócio.

---

## 7. Supple Design — o modelo aguenta evolução

`[Evans DDD, parte III]`

Um modelo é *supple* ("flexível") quando extensões e mudanças são fáceis. Características:

- **Intention-Revealing Interfaces** — nomes expressam *o que*, não *como*
- **Side-Effect-Free Functions** — operações que não mudam estado (VOs, queries)
- **Assertions** — pré/pós-condições explícitas (código, testes, tipos)
- **Conceptual Contours** — decomposição alinhada com divisões naturais do domínio
- **Standalone Class** — unidades sem dependências conceituais externas
- **Closure of Operations** — operações cujo argumento e retorno são do mesmo tipo (compõem)
- **Declarative Design** — comportamento expresso por configuração/regra, não procedural

Ver `tactical-patterns.md` — apêndice "Design Flexível em profundidade".

Modelo supple é **resultado** de refatoração pra insight aplicada consistentemente. Não se projeta supple no dia 1; se evolui pra supple.

---

## 8. Continuous Integration do modelo (não só do código)

`[Evans DDD, parte IV]`

Quando múltiplos devs trabalham no mesmo Bounded Context, a integridade do **modelo** pode divergir mesmo com CI do código passando. Sinais:

- Dev A extraiu `OrderStatus` como enum com 5 valores; Dev B extraiu como hierarquia de classes polimórficas. Ambos funcionam isolados.
- Dois PRs mergeados na mesma semana: um que quebrou Order em `DraftOrder` + `ConfirmedOrder`; outro que adicionou campo `isConfirmed` em `Order`. Agora temos duas maneiras de representar o mesmo estado.

### Prática de Continuous Integration do modelo

- **Daily standup 5 min sobre mudanças no modelo** — quem mexeu em Aggregate/VO/evento novo?
- **Glossário atualizado por PR** — mudou conceito? Atualiza glossário no mesmo PR.
- **Design reviews rápidos** (15-30 min) pra mudanças estruturais antes do code review
- **Refactoring coordenado** — dois devs não refatoram Aggregate ao mesmo tempo; pair up ou sequencial

Isso é diferente de CI/CD técnico — é CI da **linguagem e do modelo**.

---

## 9. Checklist de saúde do modelo (revisão trimestral)

- [ ] UL documentada e atualizada nos últimos 30 dias?
- [ ] Context Map revisado nos últimos 90 dias?
- [ ] Zero contextos importando internos de outros?
- [ ] Testes de arquitetura em CI protegem fronteiras?
- [ ] Nenhum Aggregate > 20 campos ou 5 coleções?
- [ ] Nenhum Service > 300 linhas?
- [ ] Flags booleanas acumuladas justificadas?
- [ ] ADRs cobrem decisões estruturais recentes?
- [ ] Time vê o modelo como ativo a cuidar, não como código legado?

3+ "não" → sessão de SWOT + refatoração pra insight (ver `acceleration-tools.md`).

---

## 10. Integração com outros modos da skill

- **Modo 1 (Analysis)** — achados que indicam conceitos implícitos ou drift geram entradas neste roteiro
- **Modo 2 (Strategic)** — pós-event storming, breakthrough frequentemente identifica novo Bounded Context ou renomeia contexto existente
- **Modo 3 (Spec)** — fase 0 de arqueologia inclui "sinais de drift" desta reference como input
- **Modo 4 (Teaching)** — pergunta "quando devo refatorar meu domínio?" traz aqui

Ver também: `strategic-design.md` (Core Domain evolui), `tactical-patterns.md` (Supple Design), `acceleration-tools.md` (timeboxed modeling).
