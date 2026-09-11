# Changelog — skill `ticket`

Registro por sessão da skill; o changelog **versionado** é `plugins/ticket/CHANGELOG.md`
(a entrada 1.4.0 de 2026-09-03 resume o que está aqui). Cada entrada registra **o que
mudou e por quê** — a lição que a motivou, não só o diff.

## 2026-09-11 — `close` da RS-877: três sensores que mentem

Publicado como **v1.5.0** (detalhe em `plugins/ticket/CHANGELOG.md`).

- `acli jira workitem comment` é **grupo**, não comando: `--key` nele devolve
  `unknown flag`, que soa como flag errada. É `comment create`.
- 🔴 `acli comment list --json` **achata o ADF para texto puro**. Quase reportei
  "o ADF não foi interpretado" com o corpo armazenado perfeito (17 nós). Sensor
  correto: `GET /rest/api/3/issue/<KEY>/comment` — `body` vem **objeto**.
- A tabela de transições do RS descrevia **convenção como restrição**: existe
  `id=31 → Finished` direto de `Em andamento`. E o conjunto de transições muda
  com o status atual (`id=6 DONE` só aparece a partir de `Aprovação`).
- O `close` não perguntava `fixVersion` — a RS-877 fechou com o trabalho em
  produção e o campo vazio. Novo step 7.

## 2026-09-10

Retrofit a partir da abertura do **SQ-122** (projeto SQ): História, 13 pontos,
sprint Formulário, `fixVersion` 0.8.0, criada em uma chamada REST com ADF. O
caminho de criação funcionou como documentado — o que falhou foi a **conferência**.

### `SKILL.md` + `references/workflow.md` — o sensor de conferência tinha um ponto cego próprio

A 1.4.0 alinhou a tabela de sprint à checagem por JQL. Medido agora: logo após o
`POST /issue`, `key = SQ-122 AND sprint in openSprints()` devolve `{"issues":[]}`
com o campo **já gravado** (`GET …?fields=customfield_10020` → `(405,
"Formulário", active)`), e passa a encontrar a issue segundos depois. É lag de
indexação, e a instrução vigente (*"se o valor não bater, reportar a falha
explicitamente"*) transformaria isso num aviso de que o cartão ficou no backlog.

Vale reparar no padrão: a 1.2.0 tinha trocado `sprint list-workitems` por JQL
porque o primeiro dava falso-negativo por **paginação**; a JQL dá o mesmo
falso-negativo por **lag**; e o `acli search` que não casa nada não imprime nada,
o que é um terceiro modo de enganar. O que sobra de confiável é a leitura do
campo — e ela ficou mais barata, porque um `GET` só traz os cinco campos que
interessam.

### `references/workflow.md` — o que faltava para a criação em uma chamada

`POST /rest/api/3/issue` pede `project` e `issuetype` por **id**, e o
`.jira-project` guarda a key. Duas chamadas descobrem (`GET /project/<KEY>`,
`GET /issue/createmeta/<KEY>/issuetypes`); os ids do SQ ficam como exemplo, com o
aviso de confirmar. No mesmo caminho, `board list-sprints --json` devolve
`{"sprints":[…]}` — a chave não é `values` nem uma lista nua, e o parser óbvio
quebra com uma mensagem que não ajuda.

### `references/templates.md` — o construtor de ADF em arquivo

O heredoc canalizado (`python3 - <<'EOF'`) morre inteiro num typo e aponta para
"linha N de stdin". Gravado em `/tmp/build-adf.py`, o conserto é uma linha. Nota
irmã: heredoc quotado preserva UTF-8, então não há motivo para tirar acentos
"por segurança" — devolvê-los depois custou uma rodada nesta sessão.

## 2026-09-02

Retrofit a partir de uma sessão real que abriu 4 cartões (RS-850…RS-853), criou
vínculos de bloqueio e comentou num quinto. As três lições abaixo foram
**medidas**, não deduzidas.

### `references/templates.md` — a varredura de ADF passou limpa num ADF inválido

A varredura documentada só olhava as `marks`. Um helper de lista recebeu
`["texto"]` e repassou as strings direto para `content`, gerando
`{"type":"paragraph","content":["texto"]}`. Sem mark nenhuma envolvida, a
varredura passou **limpa** — e o Jira recusou as 4 issues com o mesmo `400` que
não nomeia nó, campo nem índice.

**O que mudou:** o validador passou a checar **estrutura** junto com marks (todo
item de `content` tem de ser objeto com `type`) e a reportar o **caminho**
(`root.paragraph.content[1]`), que é o que transforma o 400 mudo em ponto exato.
Junto, a receita para não recair: normalizar string→nó na entrada do helper, em
vez de confiar em quem chama.

### `references/workflow.md` — a skill não cobria vínculos entre issues, e a direção é invertida

Não havia nenhuma seção sobre `issueLink`. Pior que a ausência: em
`POST /rest/api/3/issueLink`, **quem executa o verbo `outward` é o
`inwardIssue`** — ler o payload da esquerda para a direita monta o oposto do que
se queria. Com `inwardIssue=RS-844` / `outwardIssue=RS-850` o Jira gravou
"RS-844 blocks RS-850", o contrário do pretendido, e **nada avisou**: os dois
sentidos são válidos.

**O que mudou:** seção nova com os tipos de link do site, o exemplo na direção
certa, a releitura de conferência **pelo lado da issue-alvo** (mesma disciplina
que a skill já exigia para sprint e story points) e como remover um link errado —
inclusive o detalhe de que os ids precisam ser iterados um por chamada, porque
passar a lista inteira devolve `HTTP 000`, que parece falha de rede.

### `SKILL.md` — criar issue nem sempre é começar a trabalhar

O Sub-fluxo B assumia que criar um cartão é o primeiro passo de programar: criava
branch e transicionava para "Em andamento". Registrar defeito de QA/code review
para o time priorizar depois não é isso — a branch nasce vazia e o "Em andamento"
mente sobre o estado.

**O que mudou:** seção explicando quando pular branch e transição (o cartão fica
em "Tarefas pendentes", onde quem planeja a sprint o encontra), mantendo sprint,
story points, `fixVersion` e a releitura de confirmação. Mais uma linha nas
Regras para distinguir "abrir para já começar" de "registrar para priorizar", e
perguntar ao dev quando o pedido não deixar claro.
