# Changelog — skill `ticket`

Registro por sessão da skill; o changelog **versionado** é `plugins/ticket/CHANGELOG.md`
(a entrada 1.4.0 de 2026-09-03 resume o que está aqui). Cada entrada registra **o que
mudou e por quê** — a lição que a motivou, não só o diff.

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
