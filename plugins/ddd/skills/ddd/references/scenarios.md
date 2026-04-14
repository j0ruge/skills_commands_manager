# Scenarios e Given-When-Then — validar Ubiquitous Language

> **Fontes:** Vaughn Vernon, *Domain-Driven Design Distilled* (Addison-Wesley, 2016), cap. 2 ("Strategic Design with Bounded Contexts and the Ubiquitous Language"). Dan North, *Introducing BDD* (2006). Liz Keogh, *Behavior-Driven Development* articles. `[Evans DDD]` — uso de exemplos concretos.
> Créditos de conteúdo original aos autores. Esta reference é síntese em pt-BR organizada para consulta dentro da skill DDD.

Linguagem ubíqua não sobrevive sem **uso concreto**. Glossário com definições abstratas vira letra morta em 2 sprints. Cenários escritos no formato Given/When/Then forçam time + domain expert a validarem que os termos e as regras fazem sentido juntos — antes de virarem código.

---

## 1. Por que cenários importam em DDD

`[Distilled cap.2]`

Domain expert entende **exemplos**; não entende diagramas UML nem interfaces abstratas. Cenário é o formato comum entre:

- **Business:** reconhece a situação ("sim, é assim mesmo que funciona")
- **Dev:** transforma direto em teste automatizado
- **QA:** usa como caso de aceitação
- **Doc:** cenário vira exemplo em onboarding de dev novo

Se o cenário não for **compreensível pelo domain expert sem explicação técnica**, a linguagem ubíqua falhou naquele ponto. Corrija ali, não no código.

---

## 2. Formato Given-When-Then

Padrão BDD (Dan North, 2006), compatível com DDD:

```
Given <contexto inicial — estado do mundo relevante>
When  <um comando/ação/evento ocorre>
Then  <novo estado observável ou evento emitido>
```

### Exemplo agnóstico

```
Cenário: Pedido é confirmado quando tem todos os itens em estoque

Given um pedido em estado DRAFT com 3 itens
  And cada item tem pelo menos 1 unidade em estoque
  And o cliente tem limite de crédito aprovado
When o cliente confirma o pedido
Then o pedido muda pra CONFIRMED
  And um evento OrderConfirmed é publicado
  And as unidades em estoque são reservadas
```

Observações:
- **Nomes são da UL**: `DRAFT`, `CONFIRMED`, `OrderConfirmed`, "limite de crédito aprovado" — todos têm peso no negócio
- **Given** estabelece estado sem contar *como* chegou lá (pode haver `Given "order created via X"` se relevante, mas evite detalhes de UI/implementação)
- **When** é UM verbo: o gatilho
- **Then** lista efeitos observáveis — estado, eventos, side effects relevantes
- Não menciona HTTP, SQL, JSON, classe, método — é linguagem de negócio

---

## 3. Usos em sequência

### 3.1 Antes do Event Storming

Cada stakeholder traz 2-3 cenários do que *acontece no negócio real* hoje. Input pro storming: já começa com vocabulário concreto, não com abstrações.

### 3.2 Durante Design Level Event Storming

Pra cada aggregate candidato, escrever 3-5 cenários cobrindo:
- Caminho feliz (Given condições ok → When comando → Then resultado esperado)
- 1-2 invariantes (Given estado proibido → When comando → Then rejeitado com motivo claro)
- 1-2 edge cases (limite de crédito, concorrência, timeout)

Se não conseguir escrever 3 cenários distintos, o aggregate provavelmente é pequeno demais ou foi misturado com outro.

### 3.3 Como acceptance tests automatizados

Cenários viram testes diretamente (Cucumber, SpecFlow, Behave, pytest-bdd, godog). **Importante:** a tradução cenário → código deve ser raso. Se o step definition faz lógica, o cenário está errado (falta de ubiquidade) OU o código está mal fatorado.

```gherkin
Feature: Order confirmation

  Scenario: Order confirmed when all items are in stock
    Given a DRAFT order with 3 items
    And each item has at least 1 unit in stock
    And the customer has approved credit limit
    When the customer confirms the order
    Then the order becomes CONFIRMED
    And an OrderConfirmed event is published
    And stock units are reserved
```

### 3.4 Como documentação viva

Cenários no repo são o **primeiro lugar** onde um dev novo deveria olhar. Mais valor que README. Evoluem com o modelo (refatoração atualiza cenários).

---

## 4. Cenários bons vs. ruins

### ✅ Bom

```
Given a user with 2 failed login attempts in the last hour
When the user attempts to log in with invalid password
Then the account is locked
  And a SecurityAlert is emitted
```

- Vocabulário de negócio
- Estado mensurável
- Efeitos observáveis

### ❌ Ruim (implementation-coupled)

```
Given the POST request to /api/login
When the validate() method returns false
Then it should call lockAccount() and insert into audit_log table
```

- HTTP, nomes de métodos, tabelas de banco — infraestrutura vaza
- Não serve pra conversar com domain expert
- Quebra quando a implementação muda mesmo se o comportamento é o mesmo

### ❌ Ruim (vago)

```
Given some data
When the user does something
Then it should work
```

- Não testa nada, não descreve nada, não valida linguagem

---

## 5. Cenários como detector de conceitos implícitos

`[Distilled cap.2]` em combinação com `refactoring-and-insights.md`

Às vezes, ao escrever cenário, o domain expert diz: "não, não é assim — depende se está em período de carência". Opa — *carência* virou termo. Se o modelo não tem `GracePeriod` como conceito explícito, descobrimos um conceito implícito.

Cenários viram ferramenta de **escuta ativa** do vocabulário do negócio. Recomendação: toda sessão de escrita de cenário tem dev + expert + PM na sala; quem facilita anota termos novos que surgem.

---

## 6. Anti-padrões

- **Cenário testando implementação** — fala de URL, método, tabela. Não é cenário, é teste de integração disfarçado.
- **Cenário exaustivo** — todas as combinações possíveis em Given. 3-5 cenários por aggregate > 30 cenários combinatórios.
- **Cenário só no caminho feliz** — sem invariantes e edge, cenário não protege regra de negócio.
- **Cenário escrito pelo dev sem expert** — vira BDD-theater. Valor vem da colaboração.
- **Cenário + mock de domínio** — teste que mocka a Entity/Aggregate testa o mock, não o domínio. Use in-memory repository + aggregate real.
- **Cenário que precisa de 12 Given's** — aggregate complexo demais ou cenário é múltiplos casos misturados.

---

## 7. Quando NÃO usar

- Domínio trivial (CRUD simples com validações padrão — testes unitários diretos bastam)
- Protótipo/spike descartável
- Feature interna que não tem stakeholder de negócio
- UI pura (fluxos de usabilidade são melhor cobertos por testes E2E no navegador, não por BDD)

---

## 8. Cenários vs. testes unitários — cada um no seu lugar

| Cenários (BDD) | Testes unitários |
|----------------|------------------|
| Linguagem de negócio | Linguagem de código |
| Escritos com expert | Escritos pelo dev |
| Cobertura de regras de negócio | Cobertura de comportamento interno |
| Poucos, significativos (5-20 por aggregate) | Muitos, granulares (dezenas por classe) |
| Rodam em CI, lentos | Rodam a cada save, rápidos |
| Validam UL + regras | Validam edge cases, branches |

Complementam-se. Cenários sem testes unitários = cobertura fraca; testes unitários sem cenários = regras de negócio sem validação com expert.

---

## 9. Integração com a skill

- **Modo 2 (Strategic Design)** — pós-event storming, cada aggregate candidato tem 3-5 cenários rascunhados pra validar UL antes de codar
- **Modo 3 (Spec)** — anexo "Cenários por aggregate" é parte do template de conversão
- **Modo 1 (Analysis)** — código sem cenários acionáveis é achado MÉDIO (UL provavelmente divergindo)
- **Modo 4 (Teaching)** — "como uso BDD com DDD?" traz aqui

Ver também: `event-storming.md` (cenários alimentam storming), `strategic-design.md` (UL), `refactoring-and-insights.md` (cenários detectam conceitos implícitos).

---

## 10. Template rápido pra começar

Pra cada aggregate root:

```
# Cenários — <NomeAggregate>

## Caminho feliz
### Cenário: <ação principal acontece em condições normais>
Given ...
When ...
Then ...

## Invariantes
### Cenário: <comando rejeitado quando invariante X é violada>
Given <estado que viola invariante>
When <comando>
Then <rejeição + motivo específico>
  And <estado não muda>

### Cenário: <outra invariante>
...

## Edge cases
### Cenário: <caso de borda que expert considera relevante>
...
```

3-5 cenários bem escritos > 20 cenários combinatórios. Menos é mais.
