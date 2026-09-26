# Changelog — todo-to-github-issues

Changelog **versionado** do plugin. O registro por sessão da skill fica em
`skills/todo-to-github-issues/CHANGELOG.md`.

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
