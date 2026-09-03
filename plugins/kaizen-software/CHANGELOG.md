# Changelog — `kaizen-software`

Formato: [Semantic Versioning](https://semver.org/)

## [1.3.0] — 2026-09-03

Pergunta do usuário, logo depois da 1.2.0: "além do poka-yoke, algum outro conceito do Kaizen está
sendo ignorado no fluxo? Cada passo é útil em qualquer área, inclusive resolução de problemas de TI."

### Medição, não opinião

`grep` de cada conceito do cânone em `SKILL.md` × references separou três estados: **passo no
fluxo** (Gemba, PDCA, SDCA, jidoka, 5 Porquês, 5S, poka-yoke, retrospectiva), **só verbete**
(mura/muri, kaikaku, blitz, genchi genbutsu) e **ausente** (yokoten, andon, Ishikawa, o 8º
desperdício, hansei, kata, A3, kanban, VSM). Nas seis respostas da sonda A/B da 1.2.0, o modelo
não usou yokoten, Ishikawa nem o 8º desperdício uma vez sequer; mura/muri e kaikaku só apareceram
quando o subagente leu a referência inteira. Mesmo defeito do poka-yoke: verbete não vira ação.

### Sete conceitos ganham um lugar no fluxo (+16 linhas, description intacta)

- **Yokoten** — Fase 3, bugs, passo 4 novo: a causa raiz achada aqui existe onde mais (servidores,
  repositórios, clientes, skills)? Campo `Yokoten` no template do Kaizen Log. Padronizar é vertical;
  yokoten é lateral — sem ele o mesmo incidente é resolvido N vezes, uma por equipe.
- **Andon** — princípio 5 e Fase 2: parar **visivelmente**; "pare, avise, conserte". Conserto
  silencioso não vira contagem nem padrão — e é a raiz do "tudo falha em silêncio".
- **Ishikawa** — Fase 3, bugs, passo 2 e nota no template dos 5 Porquês: quando um "por quê" tem
  duas respostas verdadeiras, siga cada ramo (processo, ferramenta, ambiente, medição,
  conhecimento) com contramedida própria. Incidente de TI raramente tem uma causa só.
- **Mura/Muri** — Fase 1, caça de desperdícios: o plano empilha tudo no fim? sobrecarrega alguém?
- **Kaikaku** — Fase 1, sinal de alerta: quando nem refatiando dá, nomear, exigir ADR com a
  alternativa kaizen medida, e fatiar o próprio kaikaku (strangler, feature flag).
- **8º desperdício** — seção nova em `desperdicios.md` (sem renumerar os 7): talento e conhecimento
  não usados — quem já resolveu não é consultado, runbook inexistente, bus factor.
- **Gemba sem ticket** — Fase 3, intro: olhar logs, alertas, métricas e as oportunidades do log
  periodicamente; o problema achado antes do usuário custa uma fração.

`kaizen-conceitos.md` ganha os verbetes de andon, Ishikawa e yokoten, para o ensino acompanhar o
corpo — e o corpo aponta para o verbete em vez de duplicá-lo. Ficam de fora, de propósito: hansei
(a retrospectiva cobre), kanban/WIP ("um incremento por vez" já é WIP 1), A3 (Plano PDCA + 5
Porquês já é um A3), kata, VSM, takt, hoshin — superprocessamento para uma skill de código.

## [1.2.0] — 2026-09-03

Duas fontes, uma mudança. **Relato do usuário:** "a skill tem acionado pouco o poka-yoke, na
verdade quase nunca." **Auditoria de prompt** (`/claude-api prompt-audit`, modelo-alvo Claude Fable
5.1) sobre os 4 arquivos da skill e os espelhos da description.

### Poka-yoke entra no fluxo operacional

Gemba antes de opinar: `grep -rni poka` na skill → duas ocorrências, e as duas no caminho de
**ensino** (`SKILL.md` L79, lista de vocabulário; `kaizen-conceitos.md` L36, o verbete). Zero nos
princípios, nas três fases e nos templates. O corpo pedia como contramedida "teste que teria pegado"
e "padronize em convenção/doc/CLAUDE.md" — teste e regra escrita; nunca "torne o erro impossível".

5 Porquês, encurtados: o modelo não propunha poka-yoke porque o fluxo não pedia; não pedia porque,
na 1.0.0, jidoka, 5 porquês, 5S e SDCA viraram **passos** e poka-yoke ficou **verbete**; ninguém
notou porque a ausência falha em silêncio — plano e log saem "corretos" sem ele. Causa raiz: não
havia, no fluxo, um ponto onde a pergunta "dá para tornar esse erro impossível ou óbvio?" fosse
feita, nem sensor que mostrasse a ausência.

Contramedida em seis hunks curtos, sem caps:

- **Princípio 6 (SDCA)** ganha a escada de padronização: poka-yoke (tipo, validador na borda,
  lint, hook, gate de CI, script que recusa) > template ou script > convenção escrita — e o porquê:
  regra escrita depende de alguém lembrar. Aponta para o verbete em vez de duplicá-lo.
- **Fase 1, caça de desperdícios:** "passo que só funciona se alguém lembrar de fazer X — e que um
  poka-yoke dispensaria?"
- **Fase 2, Check explícito:** sonda nova só merece confiança depois de vermelha num caso sabotado
  e verde num caso bom.
- **Fase 3, bugs:** padronizar **começando** pelo poka-yoke, nomeando o mecanismo; regra escrita só
  quando nenhum couber, e o registro diz por quê.
- **`templates.md`, 5 Porquês:** o campo Contramedida pede o poka-yoke — ou o motivo de não haver.
- **`desperdicios.md`, #7 Defeitos:** "qual poka-yoke teria impedido este defeito?"

Verificado por sonda A/B antes de aplicar (3 cenários, 1.1.0 × nova, subagentes com contexto
limpo): 14/14 asserções passam nas duas versões — sem regressão — e a diferença aparece onde a
1.1.0 fechava com regra escrita. Planejar uma feature: 0 → 4 menções, o Act vira uma tabela de
poka-yokes. Apagar uma branch: 1 → 4, o Act vira escada (auto-delete na plataforma > `fetch.prune`
> script sabotado > regra por último). Custo: +5 % de tokens.

### Auditoria de prompt — o que mudou e o que ficou

A skill é a mais limpa do marketplace em todos os sinais do guia (zero caps, zero `STEP n`, zero
datas/tickets/modelos). Três achados de confiança média aplicados: a **description** passou de 9
para 8 gatilhos (pares `kaizen log/retrospectiva` e `desperdício/dívida técnica`), ganhou
`poka-yoke` como capacidade e gatilho, e perdeu "respeitando as convenções do repo" (é
comportamento, coberto pela seção própria; não é gatilho) — 483 chars, agora entre aspas como o
`CLAUDE.md` pede; `ANTES` em caps virou `antes` (a razão já estava na frase seguinte); a pergunta
do desperdício #1 trocou "cotação" por "usuário" — vazamento do projeto `sales_quote`, onde a skill
nasceu. De brinde, "Caçe" → "Cace".

Ficou de propósito (keep list do guia): o script exato das ações irreversíveis, a redundância
funcional do "Padronizado em" em três arquivos (os textos concordam), os exemplos ilustrativos, e o
negrito de abertura dos itens — estrutura, não ênfase.

## [1.1.0] — 2026-08-07

Uso real da skill numa sessão de revisão + limpeza de repositório expôs quatro lacunas.
Três delas são a mesma ideia aparecendo em lugares diferentes, e ela agora tem nome.

### `Rótulo ≠ artefato` entra no vocabulário

Duas vezes na mesma sessão, em domínios sem relação, uma ferramenta disse que estava tudo
bem enquanto a coisa que deveria existir não existia:

- um `postgres-backup` respondia `healthy` **antes de qualquer ciclo** — o endpoint de
  status nasce com `Exit_status: 0`, que é valor inicial, não resultado de dump. Um deploy
  com senha errada passaria pelo gate de saúde e só falharia às 06:00 do dia seguinte;
- `PR MERGED` no GitHub descreve o que a PR **consumiu**, não o que a branch contém agora.
  Duas branches "seguras para apagar" tinham commits que nenhum `refs/pull` protegia.

A skill já mandava "ir ao Gemba", mas Gemba genérico não distingue *olhar o sistema* de
*olhar a coisa certa do sistema*. O verbete novo em `kaizen-conceitos.md` nomeia a
distinção e diz o que perguntar: qual artefato deveria existir, e ele está lá? A Fase 2
(Check explícito) passa a apontar para ele — "testes verdes" e "deploy succeeded" são
rótulos sobre o processo.

### O campo `Padronizado em` do kaizen log precisa de sensor

Numa entrada escrita nessa mesma sessão, o campo dizia `este log + .claude/napkin.md` e o
napkin não tinha uma linha a respeito. O log afirmava uma convenção inexistente, e ninguém
teria notado.

É o defeito acima aplicado ao próprio registro da melhoria: aquele campo é a **única** linha
do log que afirma algo sobre o mundo fora do log, e escrever o caminho dá a sensação de ter
padronizado. O template e o princípio 6 (SDCA) passam a mandar abrir o arquivo citado e
confirmar — ou escrever `pendente`, que é informação honesta e acionável.

### Poka-yoke: a sonda caseira que alarma à toa

Uma sonda escrita na hora (`git merge-tree` contra a branch principal) acusou 4 de 6 casos.
Ela media um **proxy** — a idade da branch — quando a pergunta era se havia trabalho a
perder. Sonda que erra em 4 de 6 ensina o operador a ignorá-la, e aí ele também não vê o
alarme verdadeiro. O verbete de poka-yoke ganha esse modo de falha e a contramedida:
sabotar de propósito para ver a sonda vermelha, e rodá-la num caso bom para vê-la verde.
Sonda conferida num estado só não é sonda.

### Fase 3 ganha "Ações irreversíveis"

A skill prega incrementos "pequenos e reversíveis"; apagar branch, rodar migration
destrutiva, revogar acesso ou publicar perdem o segundo adjetivo — e é justamente aí que
faltava orientação. Quatro regras curtas, sendo a central: **fatie de modo que o passo
reversível venha primeiro**. Na sessão, apagar as cópias locais antes das remotas fez uma
divergência inesperada aparecer quando ainda custava uma verificação; num laço único sobre
tudo, teria custado um commit órfão.

### Descrição

Enxugada, não só somada (390 → 474 chars). Entra o diferencial novo (verificar pelo
artefato) e o gatilho que a sessão provou faltar: a skill foi invocada para **confirmar uma
remoção destrutiva**, uso que nenhuma palavra da descrição anterior cobria.

## [1.0.0] — 2026-08-03

Empacotamento inicial da skill local `kaizen-software` no marketplace. A skill guia as três
fases da vida de um software — planejamento, implementação e manutenção — pelo ciclo PDCA, e
também ensina Kaizen (história, vocabulário, roteiro de treinamento).

### Por que empacotar agora

A skill vivia apenas em `<projeto>/.claude/skills/kaizen-software/`, um diretório que o
`.gitignore` do projeto ignora. Ou seja: existia numa única máquina, sem versão, sem
histórico e sem distribuição — um `git clean -xfd` a apagaria sem deixar rastro. Publicar é
o que lhe dá as três coisas, e é o próprio princípio de padronização (SDCA) que a skill
prega: melhoria que não vira padrão evapora.

### Added

- `SKILL.md` — 10 princípios (incrementos pequenos, PDCA, gemba, muda, jidoka, SDCA, 5
  porquês, kaizen log, anti-perfeccionismo, todos melhoram) e as três fases operacionais.
- `references/desperdicios.md` — os 7 desperdícios traduzidos para software, com perguntas
  de detecção, mais mura/muri.
- `references/kaizen-conceitos.md` — história, vocabulário e roteiro de ensino, para
  onboarding do time ou apresentação à diretoria.
- `references/templates.md` — Plano PDCA, Kaizen Log, 5 Porquês e Retrospectiva.

### Changed — description reescrita para caber no orçamento de trigger

A description original tinha ~1000 caracteres, abria com "Use esta skill SEMPRE" e repetia
os gatilhos duas vezes (em prosa e em lista). Isso viola o padrão do marketplace (≤ 350
caracteres, teto 500) e o efeito não é cosmético: quando o conjunto de skills estoura o
`skillListingBudgetFraction`, as descriptions são **descartadas silenciosamente** e a skill
perde justamente o texto que a faz disparar. A nova tem ~385 caracteres, um idioma só e uma
linha `Gatilhos —` com 8 termos. Mesmo texto espelhado em `SKILL.md`, `plugin.json` e
`marketplace.json`.

### Changed — o template do Kaizen Log passou a refletir o uso real

O uso da skill no projeto `sales_quote` (feature SQ-62) produziu entradas de log com duas
subseções que o template não previa, e ambas se provaram as mais consultadas depois:

- **Desperdícios evitados (cortes conscientes)** — o que ficou fora do escopo e por quê.
  Sem isso, o corte deliberado é lido como esquecimento seis meses depois, e alguém reabre
  um escopo que já havia sido rejeitado com razão. Também fecha o laço com
  `references/desperdicios.md`, até então consultado só na entrada do ciclo.
- **O que aprendemos** — a pegadinha técnica que custou tempo (no caso real: o `tsconfig`
  que exclui `__tests__` do typecheck, e o glob de rota que não casa `/`). Sem registro, a
  próxima pessoa paga o mesmo custo de descoberta.

Ambas entram como **opcionais** — a skill rejeita preencher formulário sem conteúdo real.
