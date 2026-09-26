# Changelog — skill `todo-to-github-issues`

Registro por sessão da skill; o changelog **versionado** é `plugins/todo-to-github-issues/CHANGELOG.md`.
Cada entrada registra **o que mudou e por quê** — a lição que a motivou, não só o diff.

## 2026-09-26 — a largura que a skill guardava sozinha

Publicado como **v2.0.2**.

- O humano pediu para mergear um PR do kit com o `TODO.md` "em harmonia com a skill". O sensor do
  kit dizia limpo; o `--audit` dizia 42 linhas longas e 6 itens acima do teto. O mesmo `--audit`
  sobre a `main` do kit dava o mesmo — não era o PR. Era a skill: `WRAP = 100` no `todo_format.py`,
  contra `WIDTH_CAP=120` no `check-todo.sh`. Os 100 são mais velhos que a regra do kit; quando o
  kit ganhou a regra, a cópia virou segunda opinião, e o teste da skill (`len(p) <= f.WRAP`)
  concordava consigo mesmo. A skill jurava não carregar cópia do formato e carregava um número.
- A largura passa a ser lida do sensor a cada execução; kit sem ela é recusado, nunca adivinhado.
  Medido: o `--audit` do `TODO.md` do kit foi de `auto=1 manual=6` para `auto=0 manual=0`.
- A sabotagem achou um probe cego: "o nome num comentário não é declaração" passava com a regex
  sem âncora, porque a fixture tinha texto depois do número e nenhuma das duas formas casava.
  Fixture sem esse texto, e o probe morde.
- De carona, um vermelho antigo do `test_todo_issues.py` (`body edit -> 1 update`): a sonda
  editava pela última linha do item, e atribuição se repete. Vermelho pelo motivo errado — o
  espelho estava certo; agora a sonda edita o bloco, que é único.
- Lição de uso, não de código: depois de um PR que desloca linhas de um arquivo ancorado, o plano
  traz `UPDATE` em massa (14 no #170 do kit), e todos eram número de âncora. Normalizar os dígitos
  do `--dump` contra o corpo vivo provou isso antes do `--apply`.

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
