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

## Anti-padrões de context mapping

- **Context Map não existe** — ninguém sabe como contextos integram. Default = BBoM.
- **Contexto sem nome canônico** — ubiquitous language não incluir o nome dos próprios contextos é sintoma.
- **Pattern implícito** — "a gente só integra via REST". REST é protocolo, não pattern. É ACL? OHS+PL? Conformist?
- **Shared Database** — dois contextos compartilham schema/tabelas sem pattern explícito. Isso é Shared Kernel mal feito ou BBoM disfarçado. Em modular monolith, cada módulo tem schema lógico próprio.
