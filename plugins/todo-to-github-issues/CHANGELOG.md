# Changelog — todo-to-github-issues

Changelog **versionado** do plugin. O registro por sessão da skill fica em
`skills/todo-to-github-issues/CHANGELOG.md`.

## [2.0.2] — 2026-09-26

### Fixed

- **`--audit` / `--fix` quebravam linha numa largura que o kit não tem.** O `todo_format.py`
  guardava um `WRAP = 100` próprio, de antes de o kit ter regra de largura. A regra 5 do sensor do
  kit chegou em 2026-09-25 com `WIDTH_CAP=120`, e desde então a skill dava uma segunda opinião:
  no `TODO.md` do próprio kit, que o sensor chama de limpo (82 achados, âncoras no alvo), o
  `--audit` acusava 42 linhas longas e **6 itens acima do teto de 8 linhas** que só existiam na
  quebra em 100. A largura agora é **lida do sensor** (`kit.width_cap`, `^WIDTH_CAP=N` na coluna
  0); com ela o mesmo `--audit` dá `auto=0 manual=0`. Kit sem `WIDTH_CAP` (anterior à regra):
  `--audit`/`--fix` recusam com rc 3 e o `git pull` que resolve, como o resto do preflight. O
  espelho não usa a largura e não muda.
- **`test_todo_issues.py` reprovava `body edit -> 1 update` no `TODO.md` real do kit** sem defeito
  no espelho: a sonda editava o item 3 pela **última linha**, uma atribuição (`— descoberto por …`)
  que se repete em 7 itens, e o `replace(…, 1)` editava o primeiro deles (#102). Agora edita o
  bloco inteiro do item, que é único.

### Added

- Testes da largura em `test_todo_format.py`: a largura usada é a do kit; uma linha entre 100 e o
  `WIDTH_CAP` **não** é quebrada (a regressão); `width_cap` ignora o nome citado num comentário; um
  kit sem `WIDTH_CAP` é recusado com rc 3. Cada regra foi sabotada numa cópia e o teste ficou
  vermelho (o probe do comentário só passou a morder depois de a fixture perder o texto depois do
  número).
- `SKILL.md`: o requisito do kit com `WIDTH_CAP`, e a nota de que o número da âncora é texto — um
  PR que desloca linhas gera `UPDATE` em massa, que se prova com `--dump` antes do `--apply`.

## [2.0.1] — 2026-09-26

A skill entra no marketplace. Até aqui ela vivia só em `~/.claude/skills/`, fora de qualquer
repositório; a 2.0.0 é o estado em que ela rodava local, e esta versão traz a primeira correção
publicada.

### Fixed

- **`--audit` / `--fix` contavam toda âncora como inválida.** O ADR 0011 do kit sdd (2026-09-25)
  passou a resolver a âncora `arquivo:linha` contra o repositório **do arquivo checado**, e a skill
  media uma cópia gravada em `/tmp` — fora de qualquer repositório. Resultado medido no `TODO.md`
  do `sales_quote`: 188 violações acusadas onde o sensor do kit vê 97. A cópia agora é gravada ao
  lado do arquivo (oculta, apagada no `finally`), como o `with_decided` do próprio kit faz.
- **5 casos de `test_todo_format.py` vermelhos** pelo mesmo motivo: as fixtures ancoravam em
  arquivos que não existiam (`bin/x:1`, `a:1`). Ganharam um repositório temporário com os arquivos
  citados, e cada item cita um símbolo presente no arquivo ancorado. Sensor provado por sabotagem:
  devolver a cópia a `/tmp` traz de volta exatamente as 5 falhas.

### Changed

- `SKILL.md`: linha nova na tabela de MANUAL para âncora que não aponta arquivo do repo (com o
  `check-todo.sh --anchors` do kit), e o porquê da cópia ao lado do arquivo.
- `description` encurtada de 839 para 369 caracteres (cap do marketplace: 500).
- O comando do `SKILL.md` apontava `~/.claude/skills/todo-to-github-issues/scripts/`, caminho que só
  existe na instalação local por symlink — instalado pelo marketplace (cache de plugins) ou no Cursor,
  o primeiro comando quebraria. Passa a `{SKILL_DIR}/scripts/`, a convenção da skill `codereview`.
- Entrada no `CURSOR_SKILL_MAP` do `install.py` (a pasta `scripts/` é copiada inteira).

## [2.0.0] — antes de 2026-09-26

Estado local, não publicado: espelho idempotente `TODO.md` → issues (`plan` / `apply` /
`--close-orphans`), `--audit` / `--fix` contra o sensor do kit sdd, e o relatório `ACHADOS-*.md`.
