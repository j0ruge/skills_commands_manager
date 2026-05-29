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
| SQ | 51 | `Tarefas pendentes → Em andamento → Concluído` (**sem `Aprovação`**) | `Concluído` | transição **id `31`** ("Itens concluídos") |

### Descobrir transições (fazer isto, não chutar)

Preferir o MCP — retorna `id` + `name` + `to.name` (status destino) e permite
transicionar **por id**, o que é robusto quando o nome da transição diverge do
nome do status:

```text
mcp__atlassian__getTransitionsForJiraIssue(cloudId, issueIdOrKey: "${PROJECT}-XXX")
# → [{ id, name, to: { name } }] — escolher a transição cujo to.name é o status desejado:
mcp__atlassian__transitionJiraIssue(cloudId, issueIdOrKey: "${PROJECT}-XXX", transition: { id: "31" })
```

Fallback com `acli` — **transiciona pelo NOME DA TRANSIÇÃO** (não pelo nome do
status, nem pela key da issue):

```bash
acli jira workitem transition --key "${PROJECT}-XXX" --status "Em andamento"
```

### Regras

1. **Descubra antes de transicionar.** `getTransitionsForJiraIssue` (ou ler o erro
   do `acli`) revela a sequência real. Transição inexistente/fora de ordem retorna
   `"No allowed transitions found for given status"`.
2. **Status/transições em PT-BR**, conforme configurado no projeto.
3. **`acli --status` casa pelo NOME DA TRANSIÇÃO, não do status.** No SQ a transição
   que leva a "Concluído" chama-se **"Itens concluídos"** — então `acli --status
   "Concluído"` falha, mas `transitionJiraIssue(transition: { id: "31" })` funciona.
   Quando o nome da transição diverge do status (ou você não o conhece), o **MCP por
   id é o caminho confiável**.

## Tipos de Issue (em PT-BR)

- História, Tarefa, Bug, Epic, Subtarefa, Entrevista, Análise, DevOps, Divida Técnica, Idea
- Usar nomes em português: `--type "Tarefa"`, **não** `--type "Task"`

## Gotchas do `acli`

- `--type` deve usar o nome em PT-BR conforme configurado no projeto
- Transições fora da ordem retornam: `"No allowed transitions found"`
- O comando `view` não aceita `--key`, passar o ID direto: `acli jira workitem view ${PROJECT}-XXX`
- **`view` padrão omite sprint e story points.** Usar `--fields "customfield_10016,customfield_10020" --json` para obter esses campos. `customfield_10016` = story points, `customfield_10020` = array de sprints (pegar a com `"state": "active"`)
- **`edit` não suporta custom fields.** Story points (`customfield_10016`) e sprint (`customfield_10020`) não podem ser setados via `acli` — usar MCP `mcp__atlassian__editJiraIssue` como alternativa (ver seção "Sprint e Story Points via MCP" abaixo)
- **Não existe `workitem update`.** Usar `workitem edit` para editar campos (summary, assignee, labels, etc.)
- Para atribuir responsável: `acli jira workitem edit --key "${PROJECT}-XXX" --assignee "email@example.com"`
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

## Sprint e Story Points via MCP

O `acli` não suporta escrita em custom fields. Para atribuir **sprint** e **story points**, usar a tool MCP `mcp__atlassian__editJiraIssue`.

### Listar sprints ativas

```bash
acli jira board list-sprints --id $BOARD --state active --json
```

Retorna um JSON com as sprints ativas do board do projeto detectado (ex.: board
`10` para RS, board `51` para SQ). Extrair o `id` da sprint desejada.

### Atribuir sprint

Usar `mcp__atlassian__editJiraIssue` com o campo `customfield_10020`:

```text
mcp__atlassian__editJiraIssue(
  issueIdOrKey: "${PROJECT}-XXX",
  fields: { "customfield_10020": SPRINT_ID }
)
```

### Atribuir story points

Usar `mcp__atlassian__editJiraIssue` com o campo `customfield_10016`:

```text
mcp__atlassian__editJiraIssue(
  issueIdOrKey: "${PROJECT}-XXX",
  fields: { "customfield_10016": N }
)
```

### Exemplo completo (sprint + story points)

```text
# 1. Listar sprints ativas para obter o ID
acli jira board list-sprints --id $BOARD --state active --json

# 2. Atribuir sprint (ex.: ID 471)
mcp__atlassian__editJiraIssue(issueIdOrKey: "${PROJECT}-XXX", fields: { "customfield_10020": { "id": 471 } })

# 3. Atribuir story points (ex.: 8 pontos)
mcp__atlassian__editJiraIssue(issueIdOrKey: "${PROJECT}-XXX", fields: { "customfield_10016": 8 })
```
