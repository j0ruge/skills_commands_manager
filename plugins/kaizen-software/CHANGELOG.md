# Changelog — `kaizen-software`

Formato: [Semantic Versioning](https://semver.org/)

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
