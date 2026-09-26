---
name: todo-to-github-issues
description: "Mirror an sdd-style TODO.md (`<!-- sdd:open -->` / `<!-- sdd:decided -->`) as GitHub issues, idempotently, re-syncing as the file changes; also audits and fixes an off-standard TODO.md and routes an `ACHADOS-*.md` report to the tracker. Triggers — TODO.md para issues, sincronizar issues do TODO, auditar TODO.md, relatório de achados, ACHADOS, gh issue create em lote."
user_invocable: true
argument_description: "plan (padrão) | apply | apply --close-orphans | audit | fix | fix --write"
metadata:
  version: 2.0.1
---

# TODO.md → GitHub issues

O `TODO.md` continua sendo **a fonte da verdade**; cada issue é um espelho dele. O script é
idempotente: pode rodar quantas vezes quiser, e só cria ou edita o que mudou.

O formato é o do **kit sdd**, não desta skill: `templates/todo.md` (uma variante por
`OUTPUT_LANG`, ex. `todo.pt-BR.md`). Duas seções `##`, cada uma com seu marcador na linha de baixo:
`<!-- sdd:open -->` (os achados, espelhados como issues) e `<!-- sdd:decided -->` (registros do que
foi refutado ou decidido; **não** viram issue). O texto do heading segue o idioma do repo; o
marcador e o `RESOLVED by <hash>` são o contrato, em inglês. Só a seção aberta é lida, até o
próximo `##`, e as `###` dentro dela viram as labels de seção.

## Requisitos (conferidos a cada execução — o script recusa, nunca degrada)

| Requisito | Vale para | Se faltar |
|---|---|---|
| Python ≥ 3.8, `git`, `bash` | tudo | instalar; o script lista **todas** as faltas de uma vez e sai com rc 3 |
| `gh` instalado e autenticado | espelho e relatório | https://cli.github.com e `gh auth login` |
| **o kit sdd** | espelho, `--audit`, `--fix` | `git clone https://github.com/j0ruge/sdd_agents ~/repos/sdd_agents`, ou `export SDD_HOME=<clone>` |
| kit com `--count` no sensor | idem | kit anterior ao esqueleto: `git -C "$SDD_HOME" pull` |
| `TODO.md` com `<!-- sdd:open -->` | espelho | `--audit` mostra o que falta e `--fix` acrescenta (seção abaixo) |

O kit é achado por `SDD_HOME` e, sem ele, pelo `sdd` no `PATH` ou por `~/repos/sdd_agents`. Um
`SDD_HOME` errado é **erro**, nunca motivo para usar outro kit: medir o arquivo contra o sensor
errado seria pior que não medir. Esta skill **não carrega cópia** do formato nem do sensor.

## Comando

```bash
S={SKILL_DIR}/scripts/todo_issues.py      # {SKILL_DIR} = o diretório que contém este SKILL.md
python3 $S                              # 1. PLANO: só lê, não toca no GitHub
python3 $S --apply --limit 1            # 2. canário: uma issue; abra e confira a renderização
python3 $S --apply                      # 3. o resto (~2,5 s por issue, com ritmo contra rate limit)
python3 $S --apply --close-orphans      # só depois de ler as linhas ORPHAN do plano
```

Opções: `--file` (padrão `TODO.md`), `--repo OWNER/NAME` (padrão: o repo do arquivo, via `gh`;
obrigatório num clone cujo `origin` é um caminho local) e `--dump DIR` (grava os corpos
renderizados em disco, sem rede). Mexeu no script? Rode `python3 scripts/test_todo_issues.py
<TODO.md de um repo real, já no esqueleto>`, que não usa a rede.

## Como ler o plano

| Linha | Significa | O que fazer |
|---|---|---|
| `CREATE` | item sem issue | `--apply` cria a issue, com as labels `todo` e `todo: <seção>` |
| `UPDATE` | texto, título ou seção mudou | `--apply` edita o corpo e troca a label da seção |
| `SKIP` | o corpo traz `RESOLVED by <hash>` e não existe issue | nada: não se abre card para achado já fechado |
| `ORPHAN` | a issue está aberta, mas o item saiu do arquivo | confira que o item foi **consertado** (não renomeado) e rode `--close-orphans` |
| `RENAME?` | par `ORPHAN` + `CREATE` com ≥ 85% do mesmo texto: o título mudou | confirme com o humano; se for o mesmo achado, rode o comando impresso **antes** do `--apply`, e a issue antiga vira `UPDATE` |
| `CLOSED` | a issue foi fechada à mão, mas o item continua no arquivo | decisão humana: reabrir a issue ou apagar o item |
| `DUP` | duas issues com a mesma chave | feche à mão todas menos a de menor número |

Depois do `--apply`, uma nova rodada do plano **tem de** mostrar `create=0 update=0`.

Antes de qualquer plano, o script passa o arquivo pelo sensor do kit
(`check-todo.sh --check <arquivo> --allow-empty`) e confere a contagem dele (`--count`) contra a
própria. Sem marcador: rc 4, e o recado manda rodar `--audit`. Arquivo fora de forma: rc 4, com as
violações. Contagens diferentes: rc 5 (*parser drift*) — pare, não espelhe nenhum dos dois números.

## Auditar e acertar o formato (`--audit`, `--fix`)

```bash
python3 $S --audit                        # o que está fora do padrão; não toca em nada
python3 $S --fix                          # idem + o diff das correções mecânicas; não toca em nada
python3 $S --fix --write                  # grava o diff e roda o sensor de novo
python3 $S --fix --open-heading "Pendências"   # quando o --audit não sabe qual `##` guarda os achados
python3 $S --fix --lang pt-BR             # repo sem OUTPUT_LANG em .sdd/config.sh
```

`AUTO` é o que o script corrige sozinho, porque é determinístico e não perde nada:

- a semente antiga do `sdd install`, **intocada** (mesmo blob), trocada pela variante do idioma;
  com um byte a mais ela é trabalho de alguém — só o preâmbulo dela é trocado;
- o marcador `<!-- sdd:open -->` sob o **único** `##` candidato (`Aberto`, `Open`, `Achados…`,
  `Findings`); `## Open` da semente antiga vira o heading da variante;
- a seção decidida acrescentada no fim; um `## Resolved` vazio removido;
- `RESOLVIDO por <hash>` → `RESOLVED by <hash>`, só dentro da seção aberta;
- item de uma linha sem negrito: o texto antes do primeiro ` — ` vira o `**título**` (só se
  couber num título de issue, ≤ 150 caracteres);
- linha física acima de 100 colunas quebrada com recuo de 2 espaços, sem mudar uma palavra — o
  que costuma **revelar** um item acima do teto de 8 linhas que passava por estar numa linha só;
- `- [x]` apagado **só** quando todo commit que ele declara (`RESOLVED by`/`RESOLVIDO por|em`)
  já está na branch padrão, provado por `git merge-base --is-ancestor`.

`MANUAL` é o resto, agrupado por regra, com a linha (no arquivo **depois** do `AUTO`) e a ação.
Resolva-os **com o humano, um grupo por vez**, e nunca em silêncio:

| MANUAL | O que fazer |
|---|---|
| nenhum/mais de um `##` candidato | perguntar qual guarda os achados e rodar `--open-heading` |
| item acima do teto | a análise vai para `docs/` (ou o handoff da missão) e o item aponta para lá; fica ~6 linhas |
| `##` sem marcador | narrativa → `docs/`; categoria → `###` dentro da seção aberta; assunto encerrado → uma linha na seção decidida |
| `[x]` sem hash, ou com hash não mergeado | consertado: citar o commit e rodar de novo; refutado/decidido: uma linha na seção decidida; não mergeado: `- [ ] … RESOLVED by <hash>` até mergear |
| sem âncora, sem data, sem autor | completar com o humano — o script não inventa `arquivo:linha` nem quem achou |
| âncora que não aponta arquivo do repo, ou cujo arquivo não contém nenhum símbolo `entre crases` do item perto da linha (ADR 0011 do kit) | reancorar no código atual — `tests/check-todo.sh --anchors TODO.md` do kit lista só essas |

`--fix --write` recusa (rc 6) arquivo versionado com mudança não commitada, para a correção chegar
como um diff próprio; arquivo não versionado é escrito com aviso. Branch e commit ficam com você.
Mexeu no script? `python3 scripts/test_todo_format.py` (sem rede; precisa do kit e do git).

A cópia que o sensor mede é escrita **ao lado** do arquivo checado (oculta, apagada em seguida), não
em `/tmp`: desde o ADR 0011 a âncora é resolvida contra o repositório do arquivo, e uma cópia fora
dele fazia toda âncora falhar — o `--audit` do sales_quote acusava 188 violações onde o kit vê 97.

## Relatório de achados (`ACHADOS-*.md`)

Um arquivo com seções `### N. <título>` entra no **modo relatório** sozinho (`--format` força) —
menos um `TODO*.md`, que é sempre o backlog: sem o marcador ele vai para a recusa do sensor, e um
com marcador continua backlog mesmo com uma categoria `### 1. …`.
Relatório é fotografia datada, não backlog: quase tudo nele já fechou, e o que segue aberto foi
roteado a algum lugar que já tem issue. Por isso a unidade é a **seção**, nunca as linhas
`- [ ]` de dentro dela, e o status sai da **tabela de roteamento** (primeira tabela cuja coluna 1
é `#`, com uma coluna `Desfecho`/`Status` e, se houver, `Evidência`).

| Linha do plano | Significa | O que fazer |
|---|---|---|
| `CREATE closed` | o desfecho começa com `RESOLVIDO`/`RESOLVED`/`FIXED` | `--apply` cria a issue **e a fecha** como concluída, com desfecho e commits no topo |
| `LINK?` | achado aberto e sem destino | descubra a issue que já o acompanha (em geral, o espelho do `TODO.md`) e passe `--link N=<issue>`; só use `--open-unlinked` se não houver nenhuma |
| `COMMENT` | `--link` dado | `--apply` comenta **uma vez** na issue, com o texto em `<details>` |
| `CLOSE` | resolvido no relatório, issue aberta | `--apply` fecha (é o que sobra de uma queda entre criar e fechar) |

Seção sem número (uma "observação") entra por `--link "<começo do título>=<issue>"`; o prefixo
tem de casar com exatamente um cabeçalho. `--close-orphans` não existe neste modo: nada sai de um
relatório.

```bash
python3 $S --file ACHADOS-x.md                                     # plano
python3 $S --file ACHADOS-x.md --apply --limit 1                   # canário, SEM --link
python3 $S --file ACHADOS-x.md --apply --link 6=153 --link "Uma obs=155"
```

## Identidade: por que o script faz assim

- **A chave é só o título** (`<!-- todo-key -->` no corpo). Âncora `arquivo:linha` fica de fora
  porque o número da linha muda a toda hora, e cada mudança viraria uma issue nova. O preço disso:
  **renomear o título cria uma issue nova e deixa a antiga órfã**. O plano marca o par como
  `RENAME?` e imprime o comando que copia a chave nova para a issue antiga.
- **As issues existentes vêm de `gh issue list`, nunca de `--search`.** O índice de busca do
  GitHub atrasa minutos, e uma segunda rodada logo depois de uma queda criaria duplicatas.
- **O `todo-hash` cobre título, seção e texto, e deixa os links de fora.** Assim um commit novo em
  `HEAD` não reescreve 98 issues só porque o sha do permalink mudou.
- **Cada issue sabe de que arquivo veio** (`<!-- todo-src -->`, ou o link do rodapé nas antigas).
  Sem isso, rodar com `--file` num segundo arquivo lia **todo** o espelho do primeiro como órfão,
  e um `--close-orphans` o fecharia inteiro.
- **O corpo sai literal**: o texto do item, desquebrado em parágrafos, porque numa issue cada
  quebra simples vira `<br>`. A âncora e todo link relativo viram links para o sha em `HEAD`, e
  todo `@nome` fora de bloco de código ganha um espaço de largura zero depois da arroba: sem isso,
  `` `@codex review` `` citado num achado fez o conector do Codex responder na issue (crase não
  protege: bot lê o texto cru). Com o arquivo sujo ou com `HEAD` fora do remoto, o script avisa e gera
  links sem número de linha.

## Erros comuns

- **Tratar `RESOLVED by` solto como fechado.** Um item pode falar da convenção sem ter sido
  fechado (`` o ciclo de vida do `RESOLVED by` ``). Só conta `RESOLVED by <hash>`. O antigo
  `RESOLVIDO por` não é lido pelo espelho: `--fix` o converte.
- **Espelhar antes de acertar o formato.** Num arquivo sem marcador o espelho recusa (rc 4). A
  ordem é `--audit` → `--fix` → `--fix --write` → os `MANUAL` com o humano → commit → plano.
- **Ler o `MANUAL` como tarefa do script.** Tudo ali exige julgamento: o que é decidido, para onde
  vai uma análise, qual heading guarda os achados. Pergunte; não escolha pelo humano.
- **Fechar órfã sem ler.** `--close-orphans` nunca é o primeiro comando. Primeiro o plano, depois
  confira cada `ORPHAN`.
- **Passar `--link` no canário.** O `--limit` limita criações, não comentários: com `--link`, o
  canário já comenta em todas as issues vinculadas.
- **Traduzir ou resumir o item na issue.** O espelho que se afasta da fonte deixa de ser espelho.
  Corrija o texto no `TODO.md` e sincronize.
- **Vírgula no `###` da seção.** O GitHub recusa vírgula em nome de label (422 `Label.name is
  invalid`, sem dizer qual caractere) e a primeira issue nunca sai. O script troca `, ` por ` · `
  na label (o texto da seção no arquivo não muda). O teto de 50 é de **caracteres**, não bytes:
  acento não encurta nada.
- **Rodar com o arquivo vazio ou fora do lugar.** O script recusa um arquivo sem nenhum item
  (rc 2), porque nesse caso toda issue viraria órfã.
