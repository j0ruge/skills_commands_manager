# Workflow de Status — Jira (multi-projeto)

> Placeholders `${PROJECT}` (ex.: `SQ`, `RS`) e `$BOARD` (ex.: `51`, `10`) vêm
> do arquivo `.jira-project` da raiz do repo — ver `SKILL.md §Detecção de Projeto`.

## Sequência de Transições

> ⚠️ **As transições são específicas de cada projeto/board — não existe sequência
> universal.** O board RS tem a etapa intermediária `Aprovação`; o board SQ **não**
> tem (vai direto de `Em andamento` para `Concluído`). Cravar a sequência de um
> projeto quebra no outro com `"No allowed transitions found for given status"`.
> **Antes de transicionar, descubra as transições reais da issue** (abaixo) e
> caminhe até o status de destino — não assuma nomes entre projetos.

### Exemplos conhecidos (confirmar antes de usar — boards mudam)

| Projeto | Board | Caminho até "done" | Status final | Como chegar ao done |
|---|---|---|---|---|
| RS | 10 | `Tarefas pendentes → Em andamento → Aprovação → Finished` | `Finished` | duas transições (`Aprovação`, depois `Finished`) |
| SQ | 51 | `Tarefas pendentes → Em andamento → Concluído` (**sem `Aprovação`**) | `Concluído` | `acli --status "Concluído"` direto (ou MCP transição **id `31`**) |

### Descobrir transições (fazer isto, não chutar)

Preferir o MCP — retorna `id` + `name` + `to.name` (status destino) e permite
transicionar **por id**, o que é robusto quando o nome da transição diverge do
nome do status:

```text
mcp__atlassian__getTransitionsForJiraIssue(cloudId, issueIdOrKey: "${PROJECT}-XXX")
# → [{ id, name, to: { name } }] — escolher a transição cujo to.name é o status desejado:
mcp__atlassian__transitionJiraIssue(cloudId, issueIdOrKey: "${PROJECT}-XXX", transition: { id: "31" })
```

Fallback com `acli` — **transiciona pelo NOME DO STATUS DE DESTINO** (o próprio
help do `acli` descreve `--status` como "Status to transition the work item"),
não pelo nome da transição:

```bash
# Passa o STATUS de destino (ex.: "Concluído"), não o nome da transição:
acli jira workitem transition --key "${PROJECT}-XXX" --status "Concluído"
```

### Regras

1. **Descubra antes de transicionar.** `getTransitionsForJiraIssue` (ou ler o erro
   do `acli`) revela a sequência real. Transição inexistente/fora de ordem retorna
   `"No allowed transitions found for given status"`.
2. **Status/transições em PT-BR**, conforme configurado no projeto.
3. **`acli --status` casa pelo NOME DO STATUS DE DESTINO, não da transição.**
   Verificado 2026-05-29 (SQ-42/SQ-43, ambos partindo de "Em andamento"):
   `acli --status "Concluído"` **funciona**; `acli --status "Itens concluídos"`
   (o *nome da transição* que leva a "Concluído", id `31`) **falha** com
   `No allowed transitions found for given status`. Bate com o help do `acli`
   (`--status` = "Status to transition the work item"). O MCP
   `transitionJiraIssue(transition: { id })` continua útil quando você prefere o
   `id`; para o `acli`, passe o **status alvo**.
   ⚠️ O mesmo erro `No allowed transitions found` também aparece quando a
   transição não é permitida a partir do status **atual** — por isso a Regra 1
   (descobrir/caminhar passo a passo) continua valendo.

## Branch base (`$BASE_BRANCH`)

> ⚠️ **Detecte. Não cheque, e não confie na memória de outro projeto.** Cravar
> uma base errada faz a branch nascer do lugar errado e a PR ir para o alvo
> errado — e o sintoma só aparece no merge, quando já custa.

```bash
git symbolic-ref --short refs/remotes/origin/HEAD   # → origin/develop
# se falhar (HEAD remoto não resolvido localmente):
git remote show origin | sed -n 's/.*HEAD branch: //p'
```

Se `refs/remotes/origin/HEAD` não existir na cópia local, criar com
`git remote set-head origin -a` antes de continuar.

### Estado conhecido (confirmar antes de usar — repos mudam)

| Repo | Projeto | `$BASE_BRANCH` | Fluxo |
|---|---|---|---|
| `sales_quote` | SQ | **`develop`** | `develop → staging → main`; PRs vão para `develop` desde a feature 017 |

> **Correção de 2026-08-07:** esta skill afirmava que "`sales_quote`/SQ usa
> `main`". **Errado** — o default do repo é `develop`
> (`origin/HEAD → origin/develop`), e é para lá que as PRs vão. A afirmação
> vivia só no `SKILL.md`, sem nada aqui que a contradissesse; daí esta seção. Se
> um repo novo entrar na tabela, entre com a **saída do comando**, não com o que
> parece razoável.

### Declarar em vez de redetectar

Quando o repo já é conhecido, escreva `BASE_BRANCH` no `.jira-project` — é
versionado, explícito, e vale para quem clonar:

```ini
BASE_BRANCH=develop
```

## Tipos de Issue (em PT-BR)

- História, Tarefa, Bug, Epic, Subtarefa, Entrevista, Análise, DevOps, Divida Técnica, Idea
- Usar nomes em português: `--type "Tarefa"`, **não** `--type "Task"`

## Gotchas do `acli`

- **`acli` imprime `✗ Failure` e sai com exit 0.** Verificado três vezes
  (2026-08-07 ×2, 2026-08-24). Consequência: cadeia `&&`, `set -e` e checagem de
  `$?` são **decorativas** — quem automatiza em cima do exit code reporta sucesso
  sobre falha silenciosa. O único sensor confiável é reler o campo.
- `--type` deve usar o nome em PT-BR conforme configurado no projeto
- Transições fora da ordem retornam: `"No allowed transitions found"`
- O comando `view` não aceita `--key`, passar o ID direto: `acli jira workitem view ${PROJECT}-XXX`
- **`view` padrão omite sprint e story points.** Usar `--fields "customfield_10016,customfield_10020" --json` para obter esses campos. `customfield_10016` = story points, `customfield_10020` = array de sprints (pegar a com `"state": "active"`). Para descobrir IDs num site novo: `--fields "*all" --json`
- **`create` escreve custom fields, `edit` não.** `create --from-json` aceita
  `additionalAttributes` (sprint/story points na criação, sem MCP);
  `edit --from-json` rejeita a mesma chave com
  `json: unknown field "additionalAttributes"`. Issue existente → MCP
  `editJiraIssue`. Ver §Sprint e Story Points.
- `--generate-json` (em `create` e `edit`) imprime o template aceito por
  `--from-json` — é a forma de checar quais chaves a sua versão suporta, em vez
  de deduzir
- **Não existe `workitem update`.** Usar `workitem edit` para editar campos (summary, assignee, labels, etc.)
- **Para atribuir responsável, use `@me` — não o e-mail.**
  `acli jira workitem edit --key "${PROJECT}-XXX" --assignee "@me"` funciona; com
  e-mail o comando responde `✗ Failure: … can't be edited: unexpected error,
  trace id: …`, que não nomeia campo nem causa. A razão é identidade: o
  `userEmail` da sessão não é necessariamente a conta Jira (no SQ, sessão
  `it@jrcbrasil.com`, conta `jorge.ferrari@…`). Para **outra pessoa**, accountId
  via REST (`GET /rest/api/3/myself` ou `lookupJiraAccountId`) + `PUT
  /rest/api/3/issue/<KEY>` com `{"fields":{"assignee":{"accountId":"…"}}}` → 204.
  ⚠️ `lookupJiraAccountId` devolve **lista vazia** para e-mail errado, não erro.
- `acli jira workitem create` retorna a key criada no output (ex.: `RS-605`, `SQ-32`)
- Comentários: usar `comment create` (subcomando), não `comment` direto — `--body-file` para multiline
- `--body-file` aceita ADF JSON nativamente — para comentários formatados via
  `acli`, usar ADF (`{ "version": 1, "type": "doc", ... }`). Markdown e Wiki
  Markup renderizam como texto puro **no `acli`**. **Alternativa preferida:**
  `mcp__atlassian__addCommentToJiraIssue(..., contentFormat: "markdown")` aceita
  markdown direto (Jira converte server-side) — escreve uma vez o markdown e
  reaproveita no body do PR. Ver `SKILL.md §close step 5`.

## Sub-issues

- Tipo: `--type "Subtarefa"`
- Vincular à issue pai: `acli jira workitem edit --key "${PROJECT}-YYY" --parent "${PROJECT}-XXX"`
- Sub-issues **não** ganham branches próprias — commits vão na branch da issue pai
- Issue pai só fecha quando **todas** as sub-issues estiverem "Finished"
- Listar sub-issues: `acli jira workitem search --jql "parent = ${PROJECT}-XXX"`

## Sprint e Story Points

Estes dois campos são a origem do sintoma mais comum da skill: **o cartão vai
parar no backlog e sem pontuação**. A causa raiz é que a escrita depende de qual
caminho está disponível, e o caminho mais óbvio (criar a issue e editar depois)
é justamente o que falha calado. A ordem de preferência abaixo é por
confiabilidade, não por elegância.

| Situação | Caminho | Precisa de MCP? |
|---|---|---|
| Issue **nova** | `acli jira workitem create --from-json` com `additionalAttributes` | ❌ não |
| Issue **existente** | `mcp__atlassian__editJiraIssue` | ✅ sim |
| Conferir o que gravou | `acli ... view --fields` / `acli jira sprint list-workitems` | ❌ não |

### Descobrir os IDs dos campos (não confie nos números)

`customfield_10016` (story points) e `customfield_10020` (sprint) são do site
**jrcbrasil** — não são constantes do Jira. Num site/projeto novo, descubra:

```bash
acli jira workitem view <KEY-que-já-tem-os-campos> --fields "*all" --json
```

`*all` traz ~100 campos; sem ele o `--json` devolve só 5 e **nenhum** custom
field (é por isso que o `view` "não mostra" sprint/score). Identifique pelo
formato: sprint é o array cujos objetos têm `boardId`/`state`; story points é o
número solto. O `acli` não tem comando para listar definições de campo
(`acli jira field` só cria/atualiza/apaga).

### Descobrir a sprint ativa

```bash
acli jira board list-sprints --id $BOARD --state active --json
```

Retorna as sprints ativas do board do projeto detectado (ex.: board `10` para
RS, `51` para SQ). Extrair o `id`.

> ⚠️ **A sprint ativa é a de `"state": "active"` — ponto.** Não a descarte
> porque o `endDate` já passou: times deixam a sprint correr além da data
> planejada sem fechá-la. Em ago/2026 o board 51 tinha a sprint `405`
> (`endDate` de fev/2026) ainda `active`, e tratá-la como "vencida" é
> exatamente o que faz o cartão cair no backlog.

#### Quando não aparece sprint ativa

1. **`$BOARD` errado ou de outro projeto** — a causa mais frequente. Conferir:
   `acli jira board search --name "<projeto>"` e `acli jira board list-projects --id $BOARD`.
2. **Descobrir pela issue, sem depender do board** — JQL resolve:
   `acli jira workitem search --jql "project = $PROJECT AND sprint in openSprints()" --fields "customfield_10020" --json`
   → o array de sprint das issues já traz `id` + `boardId` da sprint corrente.
3. **Board scrum sem sprint aberta** (todas `closed`/`future`): não invente uma —
   avise o dev e pergunte se deve criar (`acli jira sprint create`) ou deixar no
   backlog conscientemente. Board **kanban** não tem sprint: nesse caso o campo
   simplesmente não se aplica.

### Issue nova — `create --from-json` (não precisa de MCP)

O template oficial (`acli jira workitem create --generate-json`) inclui
`additionalAttributes`, que aceita `customfield_*` **na criação**. Validado em
2026-08-04 no projeto SQ: a issue nasceu com sprint `405` e 3 story points sem
nenhuma chamada MCP.

```json
{
  "projectKey": "SQ",
  "type": "Tarefa",
  "summary": "Título da issue",
  "description": { "version": 1, "type": "doc", "content": [
    { "type": "paragraph", "content": [ { "type": "text", "text": "Descrição em ADF." } ] }
  ] },
  "additionalAttributes": {
    "customfield_10016": 3,
    "customfield_10020": 405
  }
}
```

```bash
acli jira workitem create --from-json /tmp/nova-issue.json
# ✓ Work item SQ-66 created: https://jrcbrasil.atlassian.net/browse/SQ-66
```

- Sprint é o **id como número puro** (`405`). `{"id": 405}` não é o formato aqui.
- `description` é **ADF**, não markdown — o `--from-json` não converte.
- Omitir a chave quando o dev não informou o valor (não mandar `null`).

### Issue existente — MCP `editJiraIssue`

```text
mcp__atlassian__editJiraIssue(issueIdOrKey: "${PROJECT}-XXX", fields: { "customfield_10020": 405 })
mcp__atlassian__editJiraIssue(issueIdOrKey: "${PROJECT}-XXX", fields: { "customfield_10016": 8 })
```

> ⚠️ **`acli edit --from-json` NÃO aceita `additionalAttributes`** — falha com
> `json: unknown field "additionalAttributes"` (v1.3.22). A assimetria é real:
> `create` aceita custom fields, `edit` não. Também não existe comando de sprint
> que mova work items (`acli jira sprint` só faz create/update/view/delete/
> list-workitems). Portanto, para issue já criada **não há caminho sem MCP** —
> se ele não estiver disponível, diga isso ao dev (ele pode arrastar no board)
> em vez de seguir como se tivesse dado certo.

> **MCP não-autenticado ou sem as tools de escrita?** Numa sessão nova o servidor
> atlassian pode expor só `authenticate`/`complete_authentication`. Antes de
> tratar como problema de login, **confira o endpoint**: o transporte HTTP+SSE
> (`https://mcp.atlassian.com/v1/sse`) foi descontinuado em **30/jun/2026** e
> precisa virar Streamable HTTP —
> `claude mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp`
> (em JSON: `{"type": "http", "url": "https://mcp.atlassian.com/v1/mcp"}`).
> Se a autorização não completar, use `https://mcp.atlassian.com/v1/mcp/authv2`:
> sondando os dois (2026-08-04), só o `authv2` devolve
> `WWW-Authenticate: Bearer resource_metadata="…"` — o discovery OAuth
> (RFC 9728) que permite ao cliente achar o servidor de autorização sozinho.
> Depois de corrigir, chame `mcp__atlassian__authenticate` e repasse a URL ao dev.
> Enquanto isso, transição (`--status "<status-destino>"`) e comentário (ADF via
> `--body-file`) seguem funcionando pelo `acli`.

## fixVersion (rótulo de release)

**Este é o campo com os piores sensores das ferramentas locais** — `acli` não
escreve **nem lê**, e o MCP não confirma. Medido no SQ-83 (2026-08-10) e
reconfirmado no SQ-107 (2026-08-24). Tudo aqui é REST.

| Operação | Caminho | `acli`/MCP servem? |
|---|---|---|
| Listar versões do projeto | `GET /rest/api/3/project/<KEY>/versions` | `acli jira project view --json` lê, mas o REST é a fonte |
| Criar versão | `POST /rest/api/3/version` com `{"name","projectId"}` | ❌ não existe |
| Marcar lançada | `PUT /rest/api/3/version/<ID>` com `{"released":true,"releaseDate":"AAAA-MM-DD"}` | ❌ |
| Pôr no cartão | `POST /rest/api/3/issue` (criação) ou `PUT /rest/api/3/issue/<KEY>` | ❌ `acli edit` não tem a flag (e **sai 0**) |
| **Ler** | `GET /rest/api/3/issue/<KEY>?fields=fixVersions` | ❌ `acli view --json` devolve `[]` **mesmo com o campo gravado** |

```bash
set -a; . ~/.hermes/.env; set +a     # JIRA_EMAIL / JIRA_API_TOKEN
J=https://jrcbrasil.atlassian.net/rest/api/3
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$J/project/SQ/versions"          # listar
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -X POST -H 'Content-Type: application/json' \
  -d '{"name":"0.8.0","projectId":10050}' "$J/version"                     # criar (devolve o id)
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$J/issue/SQ-107?fields=fixVersions"                                     # ÚNICO sensor de leitura
```

⚠️ **`updated` não é sensor**: o Jira não bumpa `fields.updated` numa mudança de
`fixVersions`. Concluir "não gravou" pelo timestamp é errado.

### A flag `released` do Jira não diz se a versão foi lançada

No SQ-107 o Jira listava `0.7.1` como `unreleased` — e a versão estava em
produção desde 20/ago (`origin/main` continha o bump, e o `package.json` de lá
dizia `0.7.1`). O campo é metadado que alguém precisa marcar à mão, então ele
atrasa em relação ao mundo.

**Antes de afirmar ao dev que uma versão não foi lançada, confira o artefato:**

```bash
git branch -r --contains <sha-do-bump>          # origin/main aparece?
git show origin/main:package.json | grep version
```

Se o repo diz que foi, corrija o Jira (`PUT /version/<ID>` com `released` e
`releaseDate`) em vez de repassar o metadado defasado.

### Conferir que gravou (o passo que evita o backlog silencioso)

```bash
# O que a issue tem agora
acli jira workitem view ${PROJECT}-XXX --fields "customfield_10016,customfield_10020" --json

# Confirmação independente — JQL, determinístico e sem paginação:
acli jira workitem search --jql "key = ${PROJECT}-XXX AND sprint in openSprints()" --fields "key,status"
```

⚠️ **`sprint list-workitems` é falso-negativo por paginação.** Ele lista ~30
itens; cartão recém-criado cai fora da primeira página e "some". Medido no SQ-74
(2026-08-07) e repetido no SQ-107 (2026-08-24) — nas duas vezes o cartão
**estava** na sprint. Usar esse comando como sensor produz exatamente o alarme
falso que a conferência existe para evitar.

Se o valor não bater com o pedido, reportar a falha explicitamente. Um "issue
criada ✅" sem essa releitura é como o cartão some no backlog sem ninguém notar.
