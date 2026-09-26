# Changelog — skill `todo-to-github-issues`

Registro por sessão da skill; o changelog **versionado** é `plugins/todo-to-github-issues/CHANGELOG.md`.
Cada entrada registra **o que mudou e por quê** — a lição que a motivou, não só o diff.

## 2026-09-26 — a regra de âncora do kit, e a cópia que morava fora do repo

Publicado como **v2.0.1**.

- O `test_todo_format.py` tinha 5 casos vermelhos. A hipótese do usuário — "o kit está mudando
  neste momento" — estava certa na causa e errada no tempo: a mudança (ADR 0011, `fb6fb78` +
  `2cf432d`) já estava na `main` do kit, e o `check-todo.sh` do checkout era idêntico ao da
  `origin/main`. Não era trabalho em voo; era a skill defasada.
- O defeito não era só de fixture. `sensor_violations` escrevia o texto em `/tmp`, e a âncora passou
  a ser resolvida contra o repositório do arquivo checado — toda âncora de um `TODO.md` real virava
  "names no file". Sensor que mede uma cópia em outro lugar mede outro arquivo.
- A regra, medida: arquivo **não rastreado** serve (o sensor olha o disco, não o índice); a âncora
  precisa ter forma de caminho (`a:1` não é lida como âncora); e um span entre crases da cabeça do
  item precisa ocorrer no arquivo até 10 linhas da linha ancorada.
