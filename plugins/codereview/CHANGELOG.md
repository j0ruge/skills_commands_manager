# Changelog — codereview

Formato: [Semantic Versioning](https://semver.org/)

## [1.19.0] — 2026-09-03

Otimização de custo (`/claude-api` → `cost-optimization`, Steps 0–4) da skill `codereview`, **medida**
em 16 sessões REVIEW do pipeline `sdd_agents` (14/08–01/09) que invocaram `/codereview:codereview`
(Opus 5 como orquestrador, Sonnet 5 nos agentes). Relatório completo, simulador e sensores ficaram
fora do repo; aqui vai o que mudou e por quê.

### `codereview` 1.14.0

**O que foi medido.** Uma invocação custava $11–16, 46–65% da sessão REVIEW ($24,40 em média).
Os agentes da Fase B respondiam por $10,33 (42%): $2,5 por agente, 22–65 turnos cada (média ≈ 45)
contra ~6 no desenho. O custo era cache-read acumulado (2,7–7 M tokens por agente), não o tamanho
das references: **1 de 66 agentes leu `detection-passes.md`** (caminho relativo — o agente não achava
e seguia explorando livre); **16 de 16 sessões parafrasearam o prompt de lançamento** (o bloco de
45 linhas virava "adversarial review", "sabotage pass", com sandboxes de repro em `/tmp`); em
**6 de 16 sessões `model:` foi omitido** e os agentes rodaram no modelo principal a 1,6× a tarifa.
O sweep (B2) seguia o mesmo formato: 63–66 turnos de grep um a um. Pelo desenho, a mesma revisão
custaria ≈ $2,7 — o gap é o número de turnos, não o prompt.

- **Contrato dos agentes em arquivo** (`references/per-file-agent.md`, `references/sweep-agent.md`):
  o agente lê as próprias instruções por caminho absoluto (`{SKILL_DIR}/references/…`); o
  orquestrador emite só o prompt de lançamento de ~12 linhas, "nada a mais, nada a menos" — o que
  ele não escreve, não reescreve. As instruções mandam: um lote de leituras no primeiro turno
  (references + diff + arquivo); escopo = o diff e o arquivo (sem sandbox de repro, sem rodar a
  suíte, sem varrer o repo — achado que precisa de reprodução volta marcado `needs reproduction`);
  arquivo > ~600 linhas lido por hunks ±40 mais o bloco de imports; `toctou-patterns.md` só com
  check-then-act; "planeje ~10 tool calls". Trailer `Tool calls | Files read in full` +
  `END_OF_FILE_REVIEW`; no sweep, `TOOL_CALLS:` antes de `END_OF_DEAD_CODE_SWEEP`.
- **`model: "sonnet"` como poka-yoke:** parágrafo no roteamento diz o que acontece sem o campo
  (a mesma análise a 2,5–5× a tarifa) e o footprint devolve o modelo que de fato rodou.
- **Bucket B do sweep opt-in:** a varredura repo-wide de código morto pré-existente (tooling
  `knip`/`ts-prune`/`vulture`…) só roda com foco `dead-code` ou `sweep=full`; a revisão completa fica
  com o Bucket A (o que este PR introduziu ou orfanou). Nos três sweeps medidos, o Bucket B era
  30–40% de $3,1–3,5 e nada dele pertencia ao PR em revisão. Sem o bucket, o relatório traz uma
  linha dizendo como obtê-lo. O prompt de lançamento passa a levar `Focus area` e `Sweep` (antes
  o agente não tinha como saber o foco); chave `sweep` documentada em `configuration.md`.
- **Fase A em três turnos:** passos 1–3 num comando (fallback de branch base em cadeia), passo 4,
  passos 5–8 em paralelo; probe de cobertura de testes num único loop de shell. Defaults inline no
  SKILL.md; `configuration.md` só com override `key=value` ou stack ≠ TS/React.
- **Cost footprint:** última linha de todo relatório —
  `_Cost footprint: N per-file agents (model), sweep …, M files read in full, agent tool calls
  min–max, orchestrator Bash calls K._` — alimentada pelos trailers. `END_OF_FILE_REVIEW` ausente ⇒
  arquivo `partially analyzed`. "Measure, don't guess" entra nas Context Efficiency Rules.
- `detection-passes.md` 6.6: `toctou-patterns.md` por caminho absoluto e só com check-then-act.

**Fora desta versão, por decisão:** Haiku nos agentes e `effort: low` (trade-offs sem eval de
achados para julgar — e `effort` só entra por definição de agente, que o plugin não distribui);
agrupar 5 arquivos por agente e subir o threshold inline (refutado: move a análise para o modelo
principal a tarifa maior); sweep inteiro opt-in (perderia o Bucket A).

**Como verificar (keep/revert):** turnos por agente < 15 e todos os agentes lendo as references
no stream do pipeline; custo dos agentes caindo ≥ 30% **sem** sumir CRITICAL/HIGH entre o relatório
antigo e o novo do mesmo diff. Se um CRITICAL/HIGH sumir, reverter primeiro só a frase "Plan on
roughly ten tool calls" em `per-file-agent.md` e medir de novo.

**Medido depois da publicação (2026-09-03).** Duas invocações headless de `/codereview:codereview`
(`claude -p`, orquestrador Opus 5) sobre o **mesmo diff real** de 18 arquivos (6 de código, `bin/sdd` com
6,6k linhas) no `sdd_agents`, lidas pelo stream com o mesmo sensor do baseline:

| | Baseline (16 sessões, 1.17.x) | Run A | Run B |
|---|---|---|---|
| Custo da revisão (ledger) | $11–16 só o codereview | **$6,62** (Opus $3,07 + Sonnet $3,55) | **$5,92** (Opus $2,64 + Sonnet $3,29) |
| Agente por arquivo | $2,0 (Sonnet), ≈45 turnos, 30–90 tool calls | $0,58 / $0,76 / $1,61 — 3 / 9 / 20 turnos — 13 / 13 / 28 tool calls | $0,73 / $0,83 / $0,87 — 7 / 12 / 11 turnos — 20 / 26 / 15 tool calls |
| Sweep | $3,1–3,5, 63–66 turnos | $0,62, 6 turnos | $0,69, 8 turnos |
| Leu as references | 1 de 66 agentes | 4 de 4 | 4 de 4 |
| Modelo que rodou | Opus em 6 de 16 sessões | Sonnet 4/4 | Sonnet 4/4 |
| Trailer + sentinela | — | 4/4 | 4/4 |
| Relógio | 20–33 min por sessão | 13 min | 11 min |

Achados: nenhum CRITICAL/HIGH nas duas; as duas convergem no mesmo achado principal (fail-open do glob
`0|0.*` no teto de orçamento) e em dois secundários; cada uma achou 1–2 MEDIUM que a outra não achou —
variância normal entre runs. O Bucket B saiu como a linha "não varrido" e o Cost footprint fechou os dois
relatórios. **Veredito: L1–L5 ficam** (custo por agente −50–60%, turnos < 15 em 7 dos 8 agentes,
references lidas por todos). O que a medição **não** cobre: o diff não tinha revisão anterior à 1.19.0,
então "nenhum CRITICAL/HIGH sumiu" fica sem teste; a missão do baseline (`20260901-o-revisor-so-acha`) já
estava mesclada e o seu revisor deixou de invocar o skill a partir da r3 — a comparação é por agente, não
por missão.

### `coderabbit_pr` 3.6.0

Inalterada.

## [1.18.0] — 2026-09-03

Prompt audit (`/claude-api prompt-audit`, modelo-alvo Claude Fable 5.1) nas duas skills do plugin.
Relatórios completos ficaram fora do repo; aqui vai o que mudou e por quê.

### `codereview` 1.13.0

- **Fase A roda inline.** Os sete comandos `git`, a classificação de arquivos e o pré-scan de
  secrets são um plano determinístico — cada passo tem uma resposta certa — executado por um agente
  haiku. O agente era a causa do incidente da 1.12.0 (campo `SECRETS_PRESCAN` que não voltava), e as
  36 linhas de ênfase, template de retorno e fallback tratavam o sintoma. A sonda do auditor mediu
  variação entre runs no mesmo arquivo. Agora os comandos rodam na sessão principal; as saídas são
  pequenas e a Fase C precisava delas de qualquer jeito. A `coderabbit_pr` já tinha feito essa
  migração na 1.17.0. Fase B (sonnet, paralelo) e Fase C (modelo principal) inalteradas.
- **Ênfase:** 28 de 32 linhas em caps voltaram ao tom normal; as 4 que ficam têm a razão ao lado.
  O bloco "Mandatory final sections" (4× "Forbidden", escrito contra Opus 4.x) virou um parágrafo
  que diz o que renderizar e por quê — o modelo-alvo segue uma instrução única.
- **Modelo fixo em prosa:** "opus" era citado 8× como o modelo principal; agora "the main model —
  whichever model the session is running". A description troca `(haiku/sonnet/opus)` por
  "tiered model routing" (489 → 476 chars, idêntica nos 3 lugares).
- `detection-passes.md`: a narrativa do incidente `@sales-quote`/`FORMA_PAGAMENTO` (projeto de
  origem) vira a forma geral do defeito; referências ao "haiku agent" saem.

### `coderabbit_pr` 3.6.0

- **Registry de reviewers corrigido por medição** (`gh api users/` e os 25 PRs mais recentes):
  `copilot-pull-request-reviewer` é a organização, não o bot — o review object vem de
  `copilot-pull-request-reviewer[bot]` e os inline sob um segundo login, `Copilot`, que ninguém
  listava; os dois logins do Codex não existiam (404) — o que existe é `chatgpt-codex-connector[bot]`.
- Frases relativas à versão anterior ("inline **now**", "rows that **still** delegate") e
  arqueologia de PR (`PR #6 de validade_bateria_estoque`, `PR #7`) saem; a regra fica.
- "opus"/"sonnet" fixos viram "main model"/"cheaper model" (o exemplo `model: "sonnet"` fica).
- O baseline de testes (4.0) diz onde de fato roda: no início da 3.2, quando os vereditos indicam
  que algo vai mudar — as duas sondas cegas do auditor travaram exatamente nesse ponto.
- "Address every comment… Never skip" ganha o sensor: `unresolved: 0` da fase 5.3.

## [1.17.2] — 2026-08-26

Higiene de `description`, sem mudança de comportamento: o texto tinha **686 chars**,
acima do cap de 500 do `CLAUDE.md`. A `description` é a superfície de triggering — é só
por ela que o Claude decide invocar a skill —, e descrição longa demais dilui o sinal e
pode ser **cortada em silêncio** na lista `/skills`, piorando justamente o que ela deveria
melhorar.

### Changed

- **Description encurtada de 686 para 489 chars**, espelhada nos três arquivos
  (`SKILL.md`, `plugin.json`, `marketplace.json`). Encurtada **em vez de somada**: o que
  saiu foi a qualificação dos detectores (`GitGuardian-equivalent regex`, `knip/ts-prune/vulture or grep`, o exemplo de contract drift) e o preset `dotnet` — detalhe que continua no corpo da skill, onde é útil de fato.
  Os sinais de disparo (o que a skill faz + os diferenciais que a distinguem das vizinhas)
  foram preservados.

## [1.17.1] - 2026-07-25

### Fixed (coderabbit_pr 3.5.0 → 3.5.1 — quatro defeitos de coerência que uma rodada REAL da v1.17.0 expôs)

Motivação: a v1.17.0 foi testada ao vivo no PR #25 do `ui24-agent`. As quatro mudanças
novas funcionaram (checagem de branch pegou a divergência e trocou sozinha; a varredura
apagou dois checklists do PR #7 parados na árvore desde 28/06; a união dos dois endpoints
achou o Copilot que só aparecia em `/reviews`; o caso (b) registrou "não rodou" em vez de
"aprovou"). Mas a rodada expôs quatro incoerências — três delas **introduzidas pela
própria v1.17.0**:

- **Fase 2 e Fase 6 se contradiziam em rodada de zero achados.** A 2 mandava criar o
  arquivo mínimo "for audit completeness" e a 6 apagava segundos depois — o arquivo nunca
  chegava a ser artefato de auditoria nenhum. Agora o arquivo só é escrito quando
  `--keep-checklists` garante que ele sobrevive; no default a determinação (a)/(b) vai
  para o **relatório final**, que é onde o usuário lê. A determinação em si continua
  obrigatória: é a diferença entre "este PR passou pela revisão" e "ninguém olhou".
- **O "Stop" do Error Handling colidia com o caminho de zero achados da Fase 2.** Ficou
  explícito que parar vale só quando **nenhum bot postou nada** (nem em `/comments`, nem em
  `/reviews`). Um reviewer que postou mas não achou nada — ou que reportou não ter
  conseguido rodar — segue pela Fase 2 e **tem** de ser relatado; parar ali engoliria
  justamente o achado mais importante da rodada.
- **A Fase 4 não tinha ramo "nada mudou".** Ela compara um antes e um depois; sem edição
  não há depois. Agora é pulada quando a Fase 3 não alterou arquivo nenhum, com o motivo
  dito no relatório. Dois custos concretos evitados: minutos de suíte inútil num repo
  grande, e uma falha pré-existente chegando com cara de ter sido causada pela rodada —
  exatamente a confusão que o baseline da 4.0 existe para impedir.
- **O `rm` da Fase 6 não era determinístico** — justo na fase cuja proposta era ser
  determinística. Listava quatro nomes fixos mais um comentário não executável ("plus any
  `{bot-login}-review.md`"). Agora casa pelo **cabeçalho que a própria skill escreve**, o
  que cobre reviewer desconhecido sem lista fixa e **não toca** em doc de projeto que só
  por acaso termina em `-review.md` (`security-review.md`, `architecture-review.md`) — que
  é o que um `rm -f *-review.md` ingênuo apagaria. Mesmo guard já usado na varredura da 1.1.

Editado: `skills/coderabbit_pr/SKILL.md` (Error Handling, Fase 2, Fase 4, Fase 6) e
`skills/coderabbit_pr/references/checklist-template.md` (o arquivo mínimo agora é
condicionado ao `--keep-checklists`). Sem mudança na superfície de triggering.

## [1.17.0] - 2026-07-25

### Changed (coderabbit_pr 3.4.0 → 3.5.0 — as fases mecânicas viram determinísticas e a skill passa a limpar o próprio lixo)

Motivação: numa sessão real (PR #15 do `ui24-agent`, 3 achados do Gemini) as fases
mecânicas mostraram três problemas — dois de confiabilidade e um de sujeira acumulada.

- **Listar comentários e fechar threads eram delegados a subagentes** (haiku/sonnet) com
  prompts em prosa ("return ONLY the unique bot logins", "Run them in parallel. Report how
  many succeeded"). São chamadas de API com UMA resposta certa: o agente no meio só
  adiciona variação, latência e **omissão silenciosa** — uma rodada que pula uma thread é
  indistinguível de uma rodada limpa. Agora rodam inline, com comandos fixos, e a fase 5
  termina numa **asserção `unresolved: 0`** que é o gate da conclusão.
- **A extração agora é uma projeção `--jq` fixa**, separada da *interpretação*. Isso
  resolve melhor o próprio problema que a skill citava (30-50KB de JSON cru poluindo o
  contexto): descarta `diff_hunk`/URLs/reações **antes** de qualquer contexto, em vez de
  absorver tudo num subagente e confiar no resumo. Delegação a sonnet continua, mas com
  gatilho objetivo (>1500 linhas ou 3+ reviewers com body longo). Dois detalhes não
  óbvios ficaram codificados: `\(.line // .original_line)` (o `line` vem **null** quando o
  diff do comentário fica defasado) e `select(.body != "")` (approvals têm body vazio e
  viravam achado fantasma).
- **Nova Fase 6 — limpeza.** No repositório real havia `gemini-review.md` e
  `coderabbit-review.md` do **PR #7 (2026-06-28)** ainda na árvore em **2026-07-25**; o
  `.gitignore` até os declarava efêmeros (`*-review.md`) e mesmo assim nada limpava. Pior:
  para não sobrescrever o registro antigo, a rodada nova nomeou os arquivos
  `gemini-review-pr15.md` — que **escapa do padrão `*-review.md`** e vira arquivo não
  rastreado permanente. As duas regras agora se sustentam em par: **nome sempre fixo**
  `{reviewer}-review.md` e **apagar ao concluir com sucesso** (só no caminho de sucesso,
  preservando a resumibilidade). Flag `--keep-checklists` para quem quer o artefato.
  Varredura de resto de execução anterior na Fase 1.1 como backstop — importante porque o
  cross-reviewer check da 3.1 LÊ esses arquivos e um checklist velho engana a rodada.

### Fixed (dois bugs de correção encontrados na mesma sessão)

- **A skill dizia "All fixes are made on the current branch"** — falso sempre que se
  resolve o PR estando em outro branch. Na sessão o usuário estava em
  `fix/webapp-eco-corretivo` e o PR #15 vivia em `docs/pos-mvp-prd`; seguir a skill ao pé
  da letra teria posto correções de PRD num branch alheio, **sem nunca chegar ao PR e sem
  nada falhar alto**. A Fase 1.1 agora compara `git branch --show-current` com o
  `headRefName` do PR: árvore limpa → checkout e avisa; árvore suja → para e reporta.
- **"Não rodou" era registrado como "aprovou".** O template de zero achados escrevia
  *"reviewer approved without issues"*; o Copilot respondeu **"unable to review — quota
  limit"**, ou seja, a review nunca aconteceu. Agora os dois casos são distintos, o (b)
  registra o texto literal do bot, é marcado como **lacuna de cobertura** e não conta como
  cobertura no resumo final.

Editado: `skills/coderabbit_pr/SKILL.md` (fases 1.1, 1.2, 1.3, 2, 5, nova 6, tabela de
Model Routing e Operating Principles) e `skills/coderabbit_pr/references/checklist-template.md`
(zero achados em dois casos + regra de nomeação). Descrição: acrescentado apenas
"then cleans up its own checklist files" (396 → 436 chars, dentro do alvo).

## [1.16.0] - 2026-06-15

### Changed (pass 6.9 Dead Code — guardrail "over-export" agora distingue dois sub-casos com correções OPOSTAS)

Motivação: numa sessão real de cleanup, o guardrail over-export (introduzido na
v1.15.0) dava UMA correção — "remova o `export`". Mas símbolos usados só dentro do
próprio arquivo se dividem em dois casos com remédios opostos, e aplicar o errado
quebra código vivo:

- **(a) plumbing interno** (não aparece em nenhuma assinatura exportada) → remover
  `export` (como antes). Ex.: `DefField`.
- **(b) superfície de tipo pública** — o símbolo aparece na assinatura de um símbolo
  **exportado** (ex.: `AuthUser` tipando o campo `user` do `UseAuthReturn` exportado;
  `UpdateArgs` dentro do `UseCotacaoMutationsReturn` exportado) → **manter o `export`**.
  Removê-lo quebra o contrato de tipo público e pode disparar o erro TS *"exported X
  has or is using private name Y"* (TS4023/TS4094) sob declaration emit / build
  composto (`tsc -b`). Se a ferramenta ainda reclamar, **marcar intencional** com
  `@public` (o knip honra) ou `@internal` — nunca deletar/narrowing.

O grep within-file/exported-signature agora é **check obrigatório por-símbolo** em
TODO achado "unused export", não uma anedota. (No caso real, um PRD derivado de
review ainda mandou "apagar" `cotacaoQueryKey`/`cotacaoEventosQueryKey` — mesmo padrão
do `DefField` já citado — prova de que a aplicação não era sistemática.)

Editado: `references/detection-passes.md` §6.9 (bullet over-export reescrito em (a)/(b))
e `SKILL.md` Phase B2 (resumo do guardrail espelha os dois sub-casos). Sem mudança na
superfície de triggering — descrição inalterada.

## [1.15.0] - 2026-06-15

### Changed (codereview SKILL.md v1.11.0 → v1.12.0 — calibração do pass 6.9 Dead Code para a saída de `knip`/`ts-prune`)

Motivação: numa sessão real, o agente de Dead Code Sweep (Phase B2) rodou `knip` e
produziu dois falsos-positivos que exigiram correção manual. Esta versão codifica
as duas lições como guardrails, para o agente acertar de forma determinística em vez
de depender de julgamento.

- **Categoria "unused export" precisada** em `references/detection-passes.md`: agora
  distingue *morto de fato* (sem referência em lugar nenhum, inclusive no próprio
  arquivo) de **over-export** (símbolo usado DENTRO do próprio arquivo, mas sem
  importadores externos). `knip`/`ts-prune` reportam over-export como "unused export"
  porque só contam referências *cross-file* — mas o símbolo está vivo.
- **Novo guardrail "Over-exported (used only within its own file)"**: a correção é
  **remover o `export`** (tornar module-private), **não deletar o símbolo**. Flag em
  LOW/cleanup. Motivado por caso real: um helper `DefField` usado 11× no próprio
  módulo, reportado como unused-export — deletá-lo quebraria a página.
- **Novo guardrail "Regenerable / generated scaffolding"** sob `generatedDirs`
  (`src/components/ui/**`, `**/generated/**`): primitivos de design-system (shadcn/ui
  re-adicionáveis via `npx shadcn add`) e saída de codegen. `knip` os surfaceia em
  massa (dump de ~30 arquivos que afoga os achados do PR) → mantê-los em **Bucket B**,
  **Low confidence**, capados, rotulados "regenerable scaffolding"; nunca como
  dead-code acionável do app, salvo se o próprio diff orfanou um.
- **Phase B2 (`SKILL.md`)**: a lista de guardrails do agente de sweep agora cita
  explicitamente over-export e scaffolding regenerável.

## [1.14.0] - 2026-06-13

### Added (codereview SKILL.md v1.10.0 → v1.11.0 — pass 6.9 Dead Code + Phase B2 dedicated sweep agent)

- **Novo pass 6.9 "Dead Code & Unused Symbols" em `references/detection-passes.md`** (no slot livre entre 6.8 e 6.10). Detecta exports não usados, arquivos órfãos, código inalcançável (após `return`/`throw`/`break`), imports/locals/membros privados não usados e dependências mortas. Escopo **híbrido**: Bucket A = código morto introduzido OU orfanado por este diff (primário, sempre reportado); Bucket B = código morto pré-existente surfaceado por tooling do próprio repo (secundário, rotulado "pre-existing", capado em ~10 + contagem total para não afogar o report). Detecção **tooling + grep fallback**: usa `knip`/`ts-prune`/`depcheck` (TS/JS), `vulture`/`ruff` (Python), Roslyn `IDE0051` via `dotnet build` (.NET), `deadcode`/`staticcheck` (Go) quando disponíveis — read-only, mesmo padrão oportunista do ggshield/gitleaks no pass 6.10 — e cai pro deepsearch por grep de referências (incluindo arquivos não-code: HTML/JSON/YAML/SQL) quando não há tooling.
- **Guardrails de falso-positivo são o coração do pass** (recomendar deletar código vivo é pior que deixar passar código morto): public API surface (entry points de pacote, barrels, libs), wiring por framework/reflexão (rotas, DI, decorators, `import()` dinâmico, registries por string, entidades ORM, serialização, test discovery), referências em arquivos não-code, re-exports, utilitários só-de-teste, compilação condicional, scaffolding recém-adicionado. Cada finding carrega **Confidence** (High/Medium/Low).
- **Novo agente paralelo dedicado "Phase B2: Dead Code Sweep" no `SKILL.md`**, lançado no mesmo batch paralelo dos agentes per-file da Phase B. É um agente separado — não um pass per-file — porque dead-code é uma pergunta de **grafo de referências do repo inteiro**: cada agente per-file vê só um arquivo e não consegue saber se um export é usado em outro lugar. Roda em full review, foco `bugs` e foco `dead-code`; é **skipado** em focos estreitos (security/a11y/types/performance/docs/tests) — diferente do 6.10 (secrets), dead-code é higiene, não gate. Para ≤3 CODE files (routing desligado) roda inline no main model. Tem return-template + output-discipline como Phase A/B, mas resultado ausente é **não-bloqueante**.
- **Severidade: MEDIUM** só para itens orfanados pelo diff ou arquivos órfãos inteiros; **LOW** para o resto. **Nunca CRITICAL/HIGH, nunca força grade F, nunca bloqueia o PR.**
- **Phase C ganhou step 9 "Merge dead-code findings"** (produce-report passou a step 10): funde Bucket A/B, respeita Confidence, mantém Bucket B capado, e renderiza a nova seção. Dead-code alimenta Recommended Actions → Consider Fixing e a rationale de Code Quality (Zen) — sem adicionar linha à tabela mandatória Overall Grade (preserva o contrato v1.13.0).
- **`references/report-template.md`**: nova seção **🧹 Dead Code & Cleanup** (após Documentation Sync, antes de Overall Grade) com tabela `Symbol/File | Kind | Location | Origin (PR/pre-existing) | Confidence | Recommended Cleanup`; nova linha **Dead Code (pass 6.9)** na tabela Bug/Security/Performance/Types Summary (só colunas MEDIUM/LOW).
- **Skill description ganhou clause + triggers de dead-code** ("dead code", "unused exports", "cleanup", "code health") espelhados em SKILL.md / `plugin.json` / `marketplace.json`, com a description enxugada (corte do parêntese verboso de contract-drift) pra ficar ≤700 chars e não inchar a superfície de triggering.

### Why (pass 6.9)

Pedido do dono via `/retrofit-skill`: "faça um deepsearch e adicione um agente extra paralelo que procura código morto e recomenda sua limpeza para manter o projeto de código saudável". O gap é real e estrutural, não inventado: os passes existentes 6.1–6.10 são todos **per-file / diff-scoped**. Cada agente sonnet da Phase B recebe **um único arquivo** + seu diff e retorna findings — ele fisicamente não consegue responder "este export é referenciado em algum outro lugar do repo?", que é a pergunta central de código morto. Logo, exports não usados, arquivos órfãos e símbolos que o diff deixou sem nenhum chamador escapam de todos os passes atuais: 6.4 (Type Safety) cobre `any`/casts, 6.1 (Bug) cobre null/async, 6.5.x cobre docs/contract-drift, 6.10 cobre secrets — nenhum olha o grafo de referências do repositório. A escolha de um **agente paralelo dedicado** (não um pass per-file) reflete exatamente essa restrição: dead-code precisa de visão whole-repo via grep/tooling, então merece seu próprio agente rodando em paralelo com os per-file, com escopo híbrido (relevante ao PR primeiro, saúde do projeto como secundário capado) e guardrails fortes pra nunca recomendar deletar código que só *parece* morto (wiring por framework, reflexão, consumidores externos de lib).

## [1.13.0] - 2026-05-22

### Changed (codereview SKILL.md v1.9.0 → v1.10.0 — new detection pass 6.5.3 + mandatory Overall Grade rendering)

**Part 1 — new detection pass 6.5.3 "Contract Drift in Tests":**

- **Novo sub-pass 6.5.3 em `references/detection-passes.md`** logo após 6.5.2 (Project Documentation Sync). Detecta drift entre constantes exportadas (`export const X = [...] as const`, schemas Zod/Yup/literal-union) modificadas no diff e os testes que asserem essa constante com literal-by-literal (`expect(X).toEqual([...])`, `toStrictEqual`, `toMatchObject`, `assertEquals`, `deepEqual`). Severidade: **HIGH** quando o símbolo é parte de contrato público (Zod em `shared-api-types`, enum cross-package, constante espelhada em OpenAPI); **MEDIUM** para constantes internas usadas como fixture-validation; **LOW** quando o teste asserta um superset do export (passa mas precisa cleanup). Pass é skipado quando o teste também está no diff com update casado.
- **Nova linha "Contract Tests" na Documentation Sync table** do `references/report-template.md`, com status `OK / DRIFTED` e exemplo concreto (`FORMA_PAGAMENTO`: test asserts 4 items, export has 7). Status `DRIFTED` exporta a finding para a Findings Table principal.
- **Skill description ganhou triggers** "contract drift", "stale test contract", "exported const drift", "test-vs-source-of-truth drift" para casar pedidos de review que mencionem esse cenário.

**Part 2 — mandatory final-report sections (Overall Grade + Recommended Actions):**

- **Phase C step 9 no `SKILL.md` recebeu bloco novo "Mandatory final sections"** explicitando que `### Overall Grade` e `### Recommended Actions` NUNCA podem ser omitidos, truncados ou substituídos por prosa. Lista os quatro modos de falha conhecidos (token pressure, zero-findings happy path, focus-area run, long-running review com muitas findings) e exige um self-check antes do return: a resposta tem que conter ambos os headers exatamente uma vez cada.
- **`references/report-template.md` ganhou call-out "ALWAYS rendered"** em cima da tabela Overall Grade e da seção Recommended Actions, com instruções específicas para cada modo de falha: rationale terse (`"clean"`, `"3 HIGH"`, `"n/a"`) sob pressão de contexto, grade `—` + rationale "Not analyzed" para focus-area, `_None._` sob cada bucket vazio de Recommended Actions. Render explícito de buckets vazios é importante porque uma "Must Fix" ausente lê como "relatório incompleto", não como "sem critical findings".

### Why (Part 1 — 6.5.3)

Sessão `/speckit-implement` da feature 012 (`SQ-33_codigo_unico_cotacao_sqn_jdb`) no repo `sales_quote`: ao rodar a suite completa do monorepo, vi `packages/shared/api-types/src/__tests__/contracts.test.ts > FORMA_PAGAMENTO contém os 4 valores canônicos` falhando. Reproduzi em baseline via `git stash + rerun` → também falha → declarei "drift pré-existente de outra feature, não introduzido por esta task" no resumo final do speckit-implement.

O usuário pediu `ultrathink` + `superpowers:systematic-debugging` sobre essa decisão. Em ~5 min e 3 greps:
- `grep "export const FORMA_PAGAMENTO" enums.ts` → tupla tem 7 valores + docstring "Conjunto completo restaurado em SQ-22 (rollback do R-022 da spec 011)".
- `grep -n "FORMA_PAGAMENTO" contracts.test.ts:70` → `expect(FORMA_PAGAMENTO).toEqual([...4 items])`.
- `git log --all --oneline -S 'BOLETO_90_DIAS' -- enums.ts` → commit `58f9d4a feat(SQ-22)` adicionou os 3 boletos legados ao tipo e à tupla. Mesma branch tocou `contracts.test.ts` em commit posterior (`5f3179a`) só para renomear VALIDADA→APROVADA. O `toEqual` ficou stale.

Conclusão: a PR do SQ-22 era exatamente o lugar onde um codereview pré-PR deveria ter pegado isso. O diff modificou `FORMA_PAGAMENTO` (4 → 7 valores) com docstring explicando o motivo, e o `contracts.test.ts` em mesma branch continuou afirmando 4. Cross-check trivial: grep do símbolo no codebase → encontra `expect(FORMA_PAGAMENTO).toEqual([` → comparar literal asserted vs export atual → mismatch → flag HIGH. Nenhum dos passes existentes 6.1–6.10 captura isso: 6.5.2 (Documentation Sync) cobre OpenAPI / README / CLAUDE.md / MEMORY.md, mas não testes-como-contrato. 6.4 (Type Safety) cobre `any` e casts, não drift de literal. 6.10 (Secrets) é outro escopo. Gap real.

O 6.5.3 fecha o gap deterministicamente, sem heurística LLM frágil: o pass é um grep simples + comparação de length/content. O pattern é universal (Vitest, Jest, Mocha, xunit, NUnit — qualquer framework com asserções de igualdade profunda contra constantes importadas). Custo: 1 grep extra por export modificado no diff, com short-circuit cedo se nenhum match. Para diffs sem export modificado é no-op total.

O nome do pass — "Contract Drift in **Tests**" — é deliberado: drift de docs já era coberto por 6.5.2; o que faltava é o caso onde o artefato stale é uma asserção de teste em vez de uma linha de doc. A doc fica stale silenciosamente (alguém lê e fica confuso); o teste fica stale silenciosamente também (passa em todas as branches até a próxima refatoração tocar o símbolo, aí o CI lit up e parece "drift de outra feature"). A segunda forma é mais perigosa porque cada novo contribuinte que vê o vermelho repete o ciclo de `git stash` + dismiss. O sub-pass quebra esse loop no review original.

### Why (Part 2 — Overall Grade mandatory render)

Feedback do usuário em paralelo a este retrofit: "quero também que a tabela que apresenta o resultado e o Grade de cada parte analisada volte a SEMPRE aparecer, essa tabela muitas vezes não tem aparecido". Inspeção da Phase C step 9 mostrou que `Overall Grade` aparecia na lista de seções junto com várias outras, mas SEM o modificador `(always present)` que `Secrets Detection table` tinha desde a v1.8.0. Resultado: sob pressão de contexto / zero findings / focus-area run, o opus omite a tabela e fecha o relatório com prosa do tipo "Looks clean, grade A" — perdendo o entry point que o humano usa para triagem.

Mesma família de bug que motivou a v1.12.0 (Phase A agent fazendo todo o trabalho via tool calls mas devolvendo "results above" como final message): a skill confia na disciplina implícita do modelo de "sempre emitir todas as seções", e essa disciplina falha em condições previsíveis. O fix da v1.12.0 foi prompt mais rígido + orchestrator-side fallback. O fix análogo aqui é (a) elevar `Overall Grade` e `Recommended Actions` ao status explícito de "MANDATORY — NEVER omit", (b) listar os modos de falha conhecidos com instruções concretas para cada um, (c) exigir self-check programático antes do return ("a resposta contém `### Overall Grade` e `### Recommended Actions`?"). Mesmo princípio do "verify-before-trust" da v1.10.0 aplicado à camada de output assembly.

A regra do `_None._` em buckets vazios de Recommended Actions é especialmente importante: render do header com bucket vazio comunica "checado, sem entradas"; ausência do header comunica "esqueci de checar isso". Para a UX humana, são respostas qualitativamente diferentes.

### Migration notes

- Sem breaking changes. Comando público `/codereview` inalterado, args inalterados, modelo de routing inalterado.
- Phase A (haiku) e Phase B (sonnet) ganham, na execução, 1 grep extra por export modificado no diff (`grep -rn "expect({SYMBOL})\.toEqual\|toStrictEqual\|toMatchObject" .`). Para diffs sem export modificado, no-op. Para o mediano (1-2 exports modificados), <500ms extra.
- Phase C (opus) cross-reference já trata findings de 6.5.x sem mudança — só precisa reconhecer 6.5.3 como categoria válida na Documentation Sync table.
- A tabela Documentation Sync no relatório ganha uma linha nova quando há finding 6.5.3 (e fica oculta quando não há, igual às demais linhas N/A — comportamento da `render N/A` da tabela já está estabelecido).
- A nova regra do Part 2 (Overall Grade + Recommended Actions sempre presentes) é puramente prescritiva — não muda formato nem args. Em relatórios que já incluíam essas seções, no-op observável. Em relatórios que omitiam (zero findings / focus-area / token-tight), passam a incluir um bloco mínimo com rationale terse — overhead < 20 tokens.

---

## [1.12.0] - 2026-05-20

### Changed (codereview SKILL.md v1.8.1 → v1.9.0 — Phase A output discipline + secrets-gate fallback)

- **Phase A prompt reescrito com return template literal** (mesma forma do `## Output Format` que já existia na Phase B sonnet). O prompt agora abre com um aviso explícito de "the orchestrator only sees the agent's final assistant message — tool-call outputs are NOT propagated to the caller" e termina com um template literal que o agente preenche (`BASE_BRANCH:`, `DIFF_STAT:`, `COMMIT_LOG:`, `FILES:`, `COUNTS:`, `SECRETS_PRESCAN:`, `END_OF_PHASE_A_REPORT`). Substitui o "Return as a structured list + 8 bullets" abstrato anterior, que dependia de o modelo lembrar de paste-back os outputs.
- **Orchestrator-side fallback obrigatório** documentado logo abaixo do prompt da Phase A. Se a resposta do agente for < ~500 chars, faltar a string `SECRETS_PRESCAN:`, faltar `END_OF_PHASE_A_REPORT`, ou for uma frase-status do tipo "done"/"complete"/"results above"/"structured results returned", o orquestrador é obrigado a re-executar os 8 passos no main session via Bash em paralelo e rodar o `scan_secrets.sh` ele mesmo. Ausência de payload de secrets é tratada como "scan não rodou" (warn + re-run), nunca como "scan limpou".

### Why

Sessão de codereview no branch `SQ-22_aplicar_design_navigational_horizon` do repo `sales_quote`: o agente Phase A (haiku, 9 tool uses, 81s) rodou os 8 passos via tool calls com sucesso mas devolveu como final message apenas `"Phase A complete. Structured results returned above."` — sem nenhum dos dados estruturados que o prompt pediu. O orquestrador (Opus) ficou cego: nem o diff stat, nem a classificação, nem o `SECRETS_PRESCAN` JSON chegaram. Tive que rodar `git status`, `git diff --name-only`, `git diff --stat`, `git log` e pipe-ar para `scan_secrets.sh` manualmente em paralelo no main session — anulando completamente o benefício do model routing haiku → opus que a v1.6.0 introduziu.

Comparação direta entre os prompts mostra a causa raiz: a Phase B sonnet (que funcionou — 8 agentes em paralelo, todos devolveram findings estruturadas) termina com `## Output Format` + template literal numbered list + edge case explícito (`"No findings for {FILE_PATH}"`). A Phase A haiku terminava com `"Return as a structured list"` abstrato + bullets de campos. Em modelos menores (haiku) com prompts de 40+ linhas e múltiplos passos, "lista estruturada" não é instrução forte o suficiente — o modelo trata os tool-call outputs como "já entregues" e o final message vira um status executivo. A interface do Agent tool em Claude Code só propaga a última mensagem do agente, não o transcript; um final message status-only equivale a uma resposta vazia.

Pior do que perder o context routing: o gate F de secrets depende do JSON do `scan_secrets.sh` chegar ao Phase C. Se o agente Phase A "esquecer" de paste-back o JSON, o orquestrador não tem como aplicar o gate — a skill pode silenciosamente reportar "Secrets PASS" mesmo com findings reais existindo no diff. É o mesmo modo de falha do v1.9.0 do `coderabbit_pr` (não esconder failures atrás de uma view normalizada) aplicado a outra surface: não confiar que dados existem só porque uma etapa anterior "deveria ter produzido".

O fix tem duas pernas, deliberadamente redundantes:

1. **Prompt mais robusto** — template literal ancorando o formato, warning sobre o que o caller realmente vê, end-marker (`END_OF_PHASE_A_REPORT`) para o orquestrador detectar truncamento. Reduz a probabilidade do agente errar, mas não elimina.
2. **Fallback obrigatório no orquestrador** — validação programática da resposta + re-execução completa no main session quando o agente under-reportar. Garante que mesmo se o prompt falhar, a skill nunca produz um relatório com secrets-gate degradado silenciosamente.

### Migration notes

- Sem breaking changes. Comando público `/codereview` inalterado, args inalterados, output final do relatório inalterado.
- A nova Phase A consome ~30-50 tokens a mais no prompt (template literal). Para o median PR é overhead desprezível; para PRs pequenos (≤3 CODE files) o threshold de v1.6.0 já roteia tudo para o main session sem agente.
- Quando o fallback dispara (agente under-reportou), o orquestrador roda os passos no main session — custo equivalente a antes do model routing existir. Trade-off intencional: prefiro pagar o custo de re-execução do que produzir um relatório com gate de secrets cego.

---

## [1.11.0] - 2026-05-17

### Changed (coderabbit_pr v3.3.1 → v3.4.0 — byte-exact verification for control-character findings)

- **Phase 3.1 gained step 1.1 "Byte-exact verification for control-character claims"** before classifying invisible-character/NUL-byte findings as false positives. When the reviewer mentions `\0`, `0x00`, `^@`, BOM, zero-width chars, non-printable bytes, embedded escape sequences, or anything described as "invisible/control character", the `Read` tool renders those bytes as plain whitespace — `\0create\0` is visually indistinguishable from ` create ` (regular spaces). Confirm against the actual bytes via `awk 'NR==<line>' <file> | od -c | head`, `tr -cd '\000' < <file> | wc -c`, `xxd <file> | grep -i <pattern>`, or `python -c "print(repr(open('<file>').read()))"` as fallback.
- **Skill description updated** to surface the byte-exact verification step in the triggering metadata, so users searching for "NUL", "BOM", "invisible character", or "control character" review feedback get a sharper triggering signal.

### Why

Session resolving PR #62 of `LouvorFlow`: Copilot flagged NUL bytes (`\^@`) embedded in a CommandItem `value` attribute (`` value={`\0create\0${search.trim()}`} ``). My initial analysis used `Read` to inspect line 297 — it rendered the NUL bytes as plain spaces, so the line looked like a harmless leading-space sentinel `` value={` create ${search.trim()}`} ``. Classified the finding as false positive, posted a public "not applicable — Copilot misinterpreted a space as NUL" comment on the thread, and resolved it.

Confirming after the fact with `od -c` showed `\0create\0` — the bytes were real, exactly as Copilot reported. Had to retract the comment publicly, push a follow-up commit replacing the NUL sentinel with `__create__:`, and re-explain the situation. Embarrassing waste of cycles, public retraction noise in the PR, and worse: produced a false-positive verdict on a legitimate, deterministic reviewer finding.

The generalization for `coderabbit_pr`: NUL bytes, BOM markers, zero-width characters, embedded escape sequences, and other non-printable bytes are exactly the kinds of issues that reviewers — especially deterministic parsers like Copilot's — will flag. And those are exactly the cases where `Read` is unreliable: it returns a *normalized text rendering*, not a byte-faithful one, and there is no warning when bytes were collapsed. Same principle as the v1.10.0 "verify before trust" applied to a different surface: don't outsource truth to a normalized view when the finding hinges on the underlying bytes. The cost of `od -c <file> | head` is essentially zero; the cost of a wrong "not applicable" verdict is a public retraction.

### Migration notes

- No breaking changes. Skill continues to resolve PR comments end-to-end.
- New sub-step (1.1) adds at most one `od -c` invocation per item where the reviewer explicitly cites control characters or invisible bytes. For the median PR (no such findings) the change is a no-op.
- If `od`/`xxd`/`tr` are not available (rare on developer workstations, but possible in stripped containers or some Windows shells), fall back to Python: `python -c "print(repr(open('<file>').read()))"` — `repr()` escapes control characters faithfully and works anywhere Python is installed.

---

## [1.10.0] - 2026-05-05

### Changed (coderabbit_pr v3.2.0 → v3.3.0 — verify-before-trust)

- **Phase 3.1 ganhou novo passo "Verify referenced state"** antes de aplicar QUALQUER fix: quando o reviewer cita arquivo, linha, comportamento runtime, ou referencia artefato externo (cached plan, doc, "as documented in X", "see previous session"), confirmar contra estado atual. PR diff e código vivo são autoritários; reviewer pode estar comentando em snapshot obsoleto desde o último push.
- **Operating Principle "Discipline" novo bullet "Verify before trust"**: reviewer claims sobre arquivos, linhas, comportamento ou artefatos externos são hipóteses a validar contra o código vivo, não fatos. Mesmo princípio do anti-silencing do v1.9.0 aplicado em outra direção.
- **Phase 4.2 nota refinada sobre cascade em fixes**: se o primeiro fix revelar pre-existing failures (cenário do v1.9.0 baseline), considere rerun baseline porque MAIS fixes podem revelar MAIS bugs latentes. Cascade fail-fast pode ter múltiplos níveis — não presuma que o segundo bug é o último.

### Why

Sessão de debug do PR #6 do `validade_bateria_estoque`: cached plan da sessão anterior documentava `TypeError: RequestInit signal AbortSignal` (msw v2 + jsdom + undici) como bug ativo bloqueando 44 testes. Verificação primária via `gh run view --log-failed` mostrou que o erro REAL do CI era completamente diferente: `Cannot find package 'jsdom' imported from /node_modules/vitest/...`. Os dois bugs existiam, mas o do cached plan estava mascarado pelo primeiro. Se eu tivesse aceitado o cached plan sem validar, teria proposto fix para o bug errado.

Generaliza para `coderabbit_pr`: reviewers (CodeRabbit, Copilot, Gemini, Codex) podem citar arquivo, linha ou comportamento que mudou desde o snapshot do review. Sem validar contra código vivo, o skill aplica fix em código que já mudou ou propaga diagnóstico incorreto. O princípio é o mesmo do anti-silencing do v1.9.0 (evidência primária antes de qualquer ação) — só que aplicado em outra direção: v1.9.0 dizia "não esconder failures"; v1.10.0 diz "não trustar referências sem validar".

A nota refinada da Phase 4.2 vem do mesmo PR #6: cicd v2.4.0 já documentava cascade fail-fast (bug 1 mascara bug 2). Aprendemos no PR #6 que pode ter MAIS de 2 níveis (bug 1 → bug 2 → bug 3). Após primeiro fix, considere rerun baseline em vez de assumir que o segundo bug é o último.

### Migration notes

- Sem breaking changes. Skill continua resolvendo PR comments end-to-end.
- Novo passo "Verify referenced state" adiciona ~5-30s por item de review (1 leitura extra de arquivo via Read tool). Para PRs com 50+ items, ainda dentro do orçamento (model routing haiku/sonnet do v1.6.0 já estava em vigor).
- Para itens onde o reviewer cita comportamento runtime que não se reproduz contra estado atual, marcar como `[x]` — "Não verificado: reviewer cita comportamento runtime que não consegui reproduzir contra código atual; PR submitter precisa confirmar antes do fix".

---

## [1.9.0] - 2026-05-05

### Changed (coderabbit_pr v3.1.0 → v3.2.0 — baseline-aware regression testing)

- **New Phase 4.0 "Capture Pre-Fix Baseline"** — instructs the skill to run the project's test command BEFORE applying any review fixes, saving pass/fail counts and the list of failing test names as a baseline. Without this, Phase 4.2 can't tell "regression caused by my fix" from "pre-existing latent unmasked by my fix".
- **Phase 4.2 expanded into a 5-way comparison** against the baseline: all-pass, same-failures-as-baseline (don't fix), new-failures (fix), fewer-failures (note but don't claim), mixed (separate). Each branch has explicit instructions about what to do.
- **Anti-silencing rule** added explicitly to 4.2: do NOT use `it.skip`, `if: false` on workflow steps, or `continue-on-error: true` to make CI green. Document and defer.
- **Operating Principle "Discipline"** gained a new bullet: "Don't expand scope to fix latent bugs — pre-existing test failures unmasked by your fixes are NOT yours to fix. Document and open follow-up issue."

### Why

PR #6 on `validade_bateria_estoque` had 8 red CI jobs. The root cause for 6 of them was a single broken `npm run -w <ws> exec --` syntax in 3 workflows — a fail-fast error that aborted in seconds at the Typecheck step, **masking** all subsequent steps. After the fix unblocked CI, **44 frontend tests started failing** with msw/jsdom AbortSignal interop errors, and 2 backend type errors appeared in `auth-sanity.test.ts`. These were ALL pre-existing — the `npm run … exec` failure was hiding them.

Without baseline awareness, Phase 4 of `coderabbit_pr` would treat these 44+2 failures as "caused by the applied fixes" and either (a) try to fix them (scope explosion: msw/jsdom interop is a non-trivial test infrastructure rabbit hole) or (b) silence them (which the skill explicitly should never do). The correct triage is: capture baseline before any fix, distinguish unmasked-latent from caused-by-edit, document the latent, fix only the caused-by-edit, push.

This generalizes beyond CI cascades: any regression-detection workflow needs a baseline to be honest. Without it, the question "did my change break X?" collapses into "is X broken?" — and the answer is often "yes, but not because of you".

### Migration notes

- No breaking changes. Skill still resolves PR comments end-to-end.
- New mandatory step at start of Phase 4 adds ~30s for typical projects (one extra `npm test` run). For PRs with `--skip-tests`, Phase 4 is skipped entirely as before.
- Existing checklists that don't include a "Pre-existing latent failures" subsection are still valid; the skill will add one when applicable.

## [1.8.0] - 2026-04-28

### Changed (codereview v1.8.0 — deterministic secret scanning replaces LLM-simulated regex)

- **New `scripts/scan_secrets.py` + `scripts/scan_secrets.sh` wrapper** — Phase A haiku agent now runs a real Python regex pass against the unified diff. Catalog from pass 6.10 is encoded as `re.compile` patterns with deterministic exception filtering (env-var lookups, placeholder values, `.env.example`/`.env.sample`/`.env.template` paths). When `ggshield` or `gitleaks` are on `PATH`, the script invokes them too and merges results (dedup by `{file, line, kind}`).
- **Phase A agent prompt now explicitly invokes the script** as numbered step 8 — captures the JSON output as `secrets_prescan` field in the structured return. Previously the prompt asked the agent to "apply" the regex catalog mentally; in practice substring shapes like `initialPassword: '<literal>'` (where `password` is a suffix of the keyword) were missed because LLMs aren't regex engines.
- **Phase C merge logic inverted** — `secrets_prescan` from Phase A is the **authoritative** source for the Secrets Detection table and the F-grade gate. Sonnet pass-6.10 findings are now treated as supplemental (context-aware nuance only); they're added to the table only if they reference a concrete literal credential AND match a pass 6.10 category. This eliminates LLM speculation as a gate-trigger while keeping it useful for edge cases regex can't see.
- **`detection-passes.md` corrected** — removed the false claim "this skill is read-only prose produced by LLM agents — it can't shell out to `ggshield`". The skill IS read-only (no `Edit`/`Write`/destructive git ops) but `Bash` invocations of pure scanners are perfectly compatible with that constraint and were always available. Replaced with a section pointing to the script as the single executable source of truth, with a note that the conceptual catalog and the script must be kept in sync (no automated guard yet).
- **Severity nuance preserved in script** — test-file inline literals stay HIGH (not CRITICAL) per pass 6.10 rules; multi-occurrence escalation (3+ in one file or 5+ across PR) still upgrades to CRITICAL. All exception logic (env lookups, placeholders, template files) ported faithfully from the conceptual catalog.

### Why

After PR #2 on `validade_bateria_estoque` (`feat(002-idp-oidc): IdP OIDC via Zitadel`) was blocked by GitGuardian with **3 Generic Password findings** (2 in test integration files at `initialPassword: '<literal>'` shape, 1 false-positive in a docker-compose env-var substitution), the user pointed out that v1.7.0 should have caught these locally before push. Investigation found three distinct gaps:

1. **Phase A pre-scan was a phantom step** — `SKILL.md` had a paragraph saying "the haiku agent runs a fast regex pre-scan" but the actual agent prompt code block never instructed the agent to do this. The pre-scan never ran.
2. **LLM-simulated regex is unreliable** — sonnet agents were asked to mentally apply the regex catalog from `detection-passes.md`. Substring shapes like `initialPassword: '...'` (where `password` is the suffix of `initialPassword`) were missed because the LLM "saw" the field name, not the regex match. False-negative rate was high enough on real-world test fixtures to defeat the purpose.
3. **`detection-passes.md` falsely claimed the skill couldn't shell out** — citing "read-only prose" as the reason. But read-only proibits Edit/Write/destructive git, not pure scanner invocations. The skill could have been running `ggshield secret scan path` or `grep -nE` since v1.0.

The v1.8.0 fix replaces LLM regex simulation with a real Python regex pass, enforced via an explicit numbered step in the haiku prompt. Verification against the actual PR #2 diff (`git diff a8551d2~1..6039813`) catches all 3 GitGuardian findings (and bonus catches a fourth `const SECRET = '<literal>'` that GitGuardian missed).

### Migration notes

- No breaking changes for users who don't customize the skill. Existing invocations like `/codereview` or `/codereview security` work identically; the only difference is the secrets pass actually fires now.
- If you wrote custom skills extending or wrapping this one, the haiku agent's structured return now includes `secrets_prescan: {findings, scanners, errors}`. Old fields (`BASE_BRANCH`, `BRANCH_NAME`, etc.) are unchanged.
- `scripts/scan_secrets.py` requires Python 3.8+ (uses dataclasses + walrus-free syntax for compatibility). No external deps; works in any environment that already has `python3`.

## [1.7.0] - 2026-04-18

### Added (codereview v1.7.0 — hardcoded secrets detection)

- **New pass 6.10 "Hardcoded Secrets Detection"** in `references/detection-passes.md` — explicit regex-based detection for generic passwords, JWT/Bearer, PEM keys, AWS/GCP/GitHub/Slack/Stripe tokens, `.env`-shaped assignments, and credentialed connection strings. Approximates what a dedicated CI scanner (GitGuardian, gitleaks, trufflehog) would reject.
- **Always applied to ALL file categories** — CODE, TESTS, CONFIG, UI_LIB, STYLES. Previously pass 6.2 was vague and `TESTS` files had reduced scrutiny; in practice test-file password literals are one of the most common leak shapes.
- **Always on regardless of focus area** — pass 6.10 runs even when the user asks for `/codereview performance` or `/codereview types`. A leaked credential is the one finding a user cannot afford to miss, so focus flags never silence it.
- **Phase A haiku pre-scan** — haiku agent now runs a fast regex sweep across the full raw diff (`git diff ${MERGE_BASE}...HEAD`) independent of file classification, catching secrets that land in `EXCLUDED`/`DOCS`/`CONFIG` files that per-file analysis would otherwise skip.
- **Anti-false-positive rules** — env-var lookups (`process.env.X`, `import.meta.env.X`, `config.get(...)`, `os.environ[...]`, `ConfigurationManager.AppSettings[...]`), placeholders (`"CHANGE_ME"`, `"xxx"`, `"<your-key-here>"`, empty string, null), and `.env.example`/`.env.sample`/`.env.template` placeholder values are explicitly not flagged.
- **Test-file nuance** — inline test literals (`password: "test123"`) flagged as HIGH (not CRITICAL) since they're less dangerous than prod keys but still rejected by CI scanners; literals pulled from `fixtures/` modules or `process.env.TEST_*` are not flagged.
- **Multi-occurrence aggregation** — 3+ matches in one file or 5+ across a PR collapse to a single aggregate finding with count and line ranges, escalated to CRITICAL. Signals systemic leaks rather than drowning the report.
- **New "Secrets Detection" table** in `references/report-template.md`, rendered before the Findings Table, with masked snippets (`***`), severity column, and Status (PASS/BLOCKED). Always present — shows `PASS` with 0 rows on clean branches to confirm the pass ran.
- **BLOCKED banner + forced grade F** — any pass 6.10 finding forces overall grade to F and prepends a banner linking to [GitGuardian secrets-API-management best practices](https://blog.gitguardian.com/secrets-api-management/). The Grading Scale is updated to reflect this.
- **Full remediation block** — every pass 6.10 finding now includes the four GitGuardian-recommended remediation steps (understand blast radius → env var / secret manager → rotate → rewrite history) plus the recommendation to install `ggshield pre-commit` for durable local defense. Previously the report said only "move to environment variable", which is necessary but insufficient once the secret is already in git history.
- **Masking rule** — findings show the literal masked as `***` rather than echoing the raw credential back into chat history.
- **Trigger phrases expanded** — `"secret detection"`, `"hardcoded credentials"`, `"gitguardian"`, `"ggshield"`, `"leaked password"`, `"api key"`, `"check for secrets"` now trigger the skill.

### Why

PR #5 on `eb-analytics` (`feat(server): cloud sync backend`) was blocked by GitGuardian with **11 Generic Password findings** across two commits (`f0bc35a`, `7257978`): 8 in `auth.test.ts`, 2 in `concurrency.test.ts`, 1 in `server.ts`. The previous pass 6.2 treated "exposed secrets" as a single vague bullet and gave `TESTS` files reduced scrutiny — exactly where most leaks lived. CodeRabbit passed the same PR clean; secret detection is a distinct domain and deserves a dedicated pass with concrete patterns, always-on enforcement, and blocking severity. Aligns with GitGuardian's best practices: use secrets managers, never commit credentials, install `ggshield` as a pre-commit hook, and when a leak happens rotate first and rewrite history second.

## [1.6.0] - 2026-04-12

### Changed (codereview v1.6.0 — model routing)

- **Model routing for token efficiency**: skill now delegates work to cheaper models
  - Haiku agent: git context, file classification, test coverage mapping (pure CLI + pattern matching)
  - Sonnet agents (parallel): per-file analysis using detection passes (pattern matching on code)
  - Opus (main model): cross-file review, severity recalibration, final report production
  - Auto-skip for small PRs (≤3 CODE files) — runs everything in main model
- **Detection passes extracted to reference file**: Steps 5-6 (~350 lines of detection patterns) moved from SKILL.md to `references/detection-passes.md`, keeping SKILL.md as a lean orchestrator (~200 lines)
  - Sonnet agents load only the detection passes + file content in their context
  - Opus receives only structured findings, not raw code — 76-86% less opus tokens
- **Parallel per-file analysis**: each CODE file analyzed independently in its own sonnet agent, enabling parallel execution for faster reviews
- **Cross-file analysis preserved in opus**: race conditions spanning multiple files, schema consistency, and import chain coherence still analyzed by the main model

### Estimated token savings

| PR Size | Before (all Opus) | After (mixed) | Opus Savings |
|---------|-------------------|---------------|--------------|
| Small (3 files) | ~85K | ~20K opus + 50K sonnet/haiku | ~76% |
| Medium (8 files) | ~150K | ~25K opus + 128K sonnet/haiku | ~83% |
| Large (15 files) | ~210K | ~30K opus + 212K sonnet/haiku | ~86% |

## [1.5.0] - 2026-04-12

### Changed (coderabbit_pr v3.0.0 → resolve_pr_reviews)

- **Multi-reviewer support**: now auto-detects and processes CodeRabbit, Copilot, Gemini Code Assist, and Codex reviews on a PR
  - Each reviewer gets its own checklist file (`coderabbit-review.md`, `copilot-review.md`, `gemini-review.md`, `codex-review.md`)
  - Unknown reviewers are handled with a generic parser and `{bot-login}-review.md`
  - New `--reviewer <name>` flag to process only a specific reviewer
- **Model routing for token efficiency**: skill now delegates work to appropriate model tiers
  - Haiku agents: GitHub API calls, data fetching, thread resolution (mechanical tasks)
  - Sonnet agents: comment parsing, code fix execution (pattern matching tasks)
  - Opus (main model): analysis verdicts, spec verification (judgment calls)
  - Auto-skip routing for small PRs (<5 comments) — overhead not worth it
- **Improved analysis quality**: verdicts now check project specs/docs before marking "not applicable"
  - Prevents false fixes on by-design decisions documented in specs
  - "Not applicable" entries now include spec/doc reference
- **Better large-output handling**: sonnet agents absorb 30-50KB+ API responses in their own context and return only structured summaries, keeping the main opus context clean
- **Deduplication improvements**: cross-reviewer dedup, root-cause linking ("Related to item #N")
- **New `references/reviewer-registry.md`**: extensible registry of bot logins, parsing rules, and output file names
- **Severity recalibration**: opus model reassesses reviewer-assigned severities during Phase 3 analysis based on actual code impact (e.g., Copilot defaults everything to MEDIUM but a broken feature flow is HIGH)
- **Cross-reviewer deduplication with audit trail**: items already fixed by another reviewer's round are marked "Already fixed — see {reviewer}-review.md #{N}" instead of re-analyzing
- **Empty reviewer handling**: reviewers with zero findings (e.g., Gemini approval-only) get a minimal `{reviewer}-review.md` for audit completeness

## [1.4.0] - 2026-04-05

### Added

- Detection pass 6.6 Race Conditions & TOCTOU (Time-of-Check to Time-of-Use)
  - Database check-then-act (findUnique + update without atomic claim)
  - Read-modify-write on numeric fields (lost updates)
  - Business rules enforced only in app code (bypass via concurrency)
  - Read outside transaction, write inside (stale data)
  - File system check-then-act (exists then read/write)
  - Cache thundering herd (miss + compute without coalescing)
  - `references/toctou-patterns.md` — full pattern catalog with code examples
- Detection pass 6.7 Accessibility
  - Icon-only buttons without aria-label
  - Form buttons without type="button" (implicit submit)
  - Interactive elements without keyboard support
  - Images without alt text
- Detection pass 6.8 Data Integrity & Schema Safety
  - Cascade delete risks on user/tenant entities
  - Missing database indexes on junction tables
  - URL fields accepting dangerous protocols (javascript:, data:)
  - Inconsistent validation schemas across endpoints
  - Test fakes/mocks missing fields from production schema
- Focus areas `a11y` and `race-conditions` for targeted reviews
- `security` focus now includes 6.6 Race Conditions and 6.8 URL/cascade checks
- `bugs` focus now includes 6.6 Race Conditions

### Changed (coderabbit_pr v2.0.0)

- Fixed parsing of "outside-diff-range" comments from CodeRabbit review body
  - Now correctly extracts findings from `<details><summary>` blocks in review body
  - Previously only inline diff comments were detected (2-5 items); now captures all 20-30+ items
- Added Phase 5: Resolve GitHub Conversations
  - Uses GraphQL API to fetch and resolve all unresolved review threads
  - Resolves threads from all reviewers (CodeRabbit, Gemini, Copilot, etc.)
  - Reports resolution count in checklist
- Improved severity mapping to handle both emoji and text markers
- Added deduplication between inline and review body findings

## [1.3.0] - 2026-03-28

### Added

- Detection pass 6.5 Documentation Sync & Docstring Coverage
  - 6.5.1 Docstring coverage: verifica JSDoc/XML doc/docstrings em funcoes novas/modificadas, detecta idioma se projeto especifica (PT-BR, etc.)
  - 6.5.2 Project documentation sync: verifica se README, OpenAPI, rules, CLAUDE.md e MEMORY.md foram atualizados junto com o codigo
- Focus area `docs` para revisar apenas documentacao
- Suporte a docstrings de Go e Shell scripts
- Grade "Documentation" no relatorio final
- Secao Documentation Sync no report-template.md

### Changed

- Agnostico de linguagem para deteccao de docstrings (TS/JS, C#/.NET, Python, Go, Shell)
- Step 9 agora mapeia focus areas para passes especificos explicitamente

## [1.2.0] - 2026-03-25

### Added

- `dotnet` as `frameworkPatterns` option for C#/.NET projects (WPF, WinForms, ASP.NET, Console)
- .NET-specific checks: `async void`, `IDisposable`, `MessageBox` in service classes, `public static` mutable, `new HttpClient()`, `Thread.Sleep()`, SQL injection, MVVM violations
- .NET file exclusions: `bin/`, `obj/`, `*.Designer.cs`, `*.g.cs`
- .NET test file mapping: `{ProjectName}.Tests/{Base}Tests.cs` patterns
- .NET test root auto-detection via `.csproj` references to xUnit/NUnit/MSTest
- .NET override examples in configuration.md
- .NET report example in report-template.md
- `dotnet test` command detection in coderabbit_pr skill

### Changed

- Zen Principles (§5) and Detection Passes (§6) refactored into universal + framework-conditional blocks
- All React/TypeScript-specific checks now conditional on `frameworkPatterns=react|vue|angular|node`
- Backward compatible: default behavior unchanged when no `frameworkPatterns` override is specified

## [1.1.0] - 2026-03-23

### Adicionado

- Nova sub-skill `coderabbit_pr` — extrai comentarios do CodeRabbit de um PR, cria checklist estruturado, verifica e corrige cada item, e roda testes de regressao
- Mapeamento de severidades CodeRabbit (🔴🟠🟡🔵) para CRITICO/ALTO/MEDIO/BAIXO
- Suporte a `--dry-run` (somente verificacao) e `--skip-tests`
- `references/checklist-template.md` — template do arquivo de checklist gerado
- Deteccao automatica de comando de teste (npm/cargo/pytest/go/make)

## [1.0.0] - 2026-03-13

### Adicionado

- Skill de code review automatizado pré-PR inspirado no Zen of Python (PEP 20)
- Análise de diffs com severidades CRITICO/ALTO/MEDIO/BAIXO
- 5 princípios Zen como lentes de análise (readability, explicit, simple, flat, error handling)
- Passes de detecção: bugs, segurança, performance, type safety
- Avaliação de cobertura de testes (COM_TESTE / TESTE_DESATUALIZADO / SEM_TESTE)
- Nota final por letra (A-F) com critérios por categoria
- Stack-agnostic com defaults TypeScript/React configuráveis
- `references/report-template.md` — template completo do relatório
- `references/configuration.md` — valores default e sintaxe de override

---

## Histórico Pré-Marketplace

A skill existia como v2.0.0 informal no repositório `digital_service_report_frontend` (sem disciplina semver). O histórico abaixo documenta a evolução antes da publicação no marketplace.

- **v2.0.0** (2026-03-10): Reescrita completa — classificação de arquivos por categoria, progressive disclosure via references, override de configuração stack-agnostic, grading scale A-F, cap de 50 findings
- **v1.0.0** (2026-03): Versão inicial com análise básica de diffs e relatório estruturado
