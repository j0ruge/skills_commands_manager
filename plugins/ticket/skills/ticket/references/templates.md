# Templates — Skill Ticket

> **Formatação de comentários no Jira:** existem 2 caminhos.
>
> 1. **Preferido — `mcp__atlassian__addCommentToJiraIssue` com
>    `contentFormat: "markdown"`**: aceita markdown direto (headings, listas,
>    tabelas, blocos de código, bold/itálico) e converte para ADF server-side.
>    Validado 2026-05-20 — renderiza idêntico ao ADF manual. Usar o
>    `Template: Resumo de Fechamento (Markdown)` abaixo.
> 2. **Fallback — `acli --body-file` com ADF JSON**: o `acli` não converte
>    markdown nem Wiki Markup (ambos viram texto puro). Quando o MCP atlassian
>    não estiver disponível, usar a `Referência Rápida: ADF (legado)` + a
>    estrutura JSON do `Template: Resumo de Fechamento (ADF JSON — legado)`.
>
> Sempre que possível, escrever o resumo uma única vez em markdown e
> reaproveitá-lo no body do PR (GitHub também é markdown).

## Template: Resumo de Fechamento (Markdown — preferido)

Usado no `/ticket close` step 5 quando o MCP atlassian está disponível. Auto-gerado
a partir de commits e diff. Postar via `mcp__atlassian__addCommentToJiraIssue(...,
contentFormat: "markdown")` e reaproveitar como body do PR no GitHub.

```markdown
## Visão Geral

{Descrição resumida — extraída da descrição original no Jira}

## Solução

{Síntese das mudanças — gerada a partir dos commit messages}

- {mudança 1}
- {mudança 2}

**Arquivos modificados:** {N} arquivos

## Teste

- {teste 1}
- {teste 2}
```

## Referência Rápida: ADF (legado)

O ADF é um JSON com estrutura `{ "version": 1, "type": "doc", "content": [...] }`.

| Elemento | ADF type | Atributos |
|----------|----------|-----------|
| Heading | `heading` | `attrs.level` (1-6) |
| Parágrafo | `paragraph` | — |
| Bold | mark `strong` | — |
| Itálico | mark `em` | — |
| Inline code | mark `code` | — |
| Code block | `codeBlock` | `attrs.language` |
| Bullet list | `bulletList` > `listItem` > `paragraph` | — |
| Ordered list | `orderedList` > `listItem` > `paragraph` | — |
| Link | mark `link` | `attrs.href` |
| Horizontal rule | `rule` | — |

### Antes de postar: valide o ADF

O Jira recusa ADF malformado com **400 sem dizer qual nó** está errado — a
resposta não nomeia o campo, o índice nem o tipo. Isso transforma um erro de uma
linha em tentativa e erro. Uma varredura de segundos transforma o mesmo 400 num
diagnóstico exato, então vale rodá-la sempre antes do POST, não só depois de
falhar.

Os únicos `marks` aceitos — qualquer outro derruba a requisição:

`strong` · `em` · `code` · `link` · `strike` · `underline`

```python
VALIDAS = {'strong', 'em', 'code', 'link', 'strike', 'underline'}
ruim = []
def check(n):
    if isinstance(n, dict):
        for m in n.get('marks', []) or []:
            if m.get('type') not in VALIDAS:
                ruim.append(m.get('type'))
        for c in n.get('content', []) or []:
            check(c)
    elif isinstance(n, list):
        for c in n:
            check(c)
check(doc)
assert not ruim, f'marks invalidas: {sorted(set(ruim))}'
```

**O erro clássico que isso pega** (medido em 2026-08-26, RS-822): um helper que
aceita `marks` e recebe **string** em vez de lista. `t("texto", "strong")` faz o
loop iterar caractere a caractere e produz `{"type":"s"}`, `{"type":"t"}`,
`{"type":"r"}`… O JSON fica sintaticamente válido, o `python -m json.tool` passa,
e o Jira devolve 400 mudo. Passe sempre lista: `t("texto", ["strong"])`.

Se a varredura acusar marks quebradas em caracteres soltos, dá para consertar o
payload já montado em vez de remontá-lo: junte os caracteres soltos de cada nó
(`''.join(...)`) e, se a palavra resultante estiver em `VALIDAS`, substitua as
marks daquele nó por ela.

⚠️ O mesmo vale para **tipos de nó**, não só marks: `bold` em vez de `strong`,
`italic` em vez de `em`, ou um `type` inexistente produzem o mesmo 400 mudo.
Quando a varredura de marks vier limpa e o 400 persistir, o suspeito seguinte é
um `type` de nó fora da tabela acima.

## Template: Descrição de Issue

Usado ao criar issues com `/ticket start`. Enviar como **plain text** — o campo `--description` do `acli` não suporta ADF.

```text
Objetivo:
{descrição do que deve ser feito}

Critérios de Aceite:
- {critério 1}
- {critério 2}

Contexto:
{informações adicionais, links, referências}
```

## Template: Resumo de Fechamento (ADF JSON — legado)

**Fallback** quando o MCP atlassian não está disponível na sessão. Auto-gerado
a partir de commits e diff. Salvar como `/tmp/${PROJECT}-XXX-comment.json` e
postar via `acli jira workitem comment create --key "${PROJECT}-XXX" --body-file ...`.

O agente deve **montar o JSON ADF programaticamente** seguindo esta estrutura:

```json
{
  "version": 1,
  "type": "doc",
  "content": [
    {
      "type": "heading",
      "attrs": { "level": 2 },
      "content": [{ "type": "text", "text": "Visão Geral" }]
    },
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "{Descrição resumida — extraída da descrição original no Jira}" }
      ]
    },
    {
      "type": "heading",
      "attrs": { "level": 2 },
      "content": [{ "type": "text", "text": "Solução" }]
    },
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "{Síntese das mudanças — gerada a partir dos commit messages}" }
      ]
    },
    {
      "type": "bulletList",
      "content": [
        {
          "type": "listItem",
          "content": [
            { "type": "paragraph", "content": [{ "type": "text", "text": "{mudança 1}" }] }
          ]
        },
        {
          "type": "listItem",
          "content": [
            { "type": "paragraph", "content": [{ "type": "text", "text": "{mudança 2}" }] }
          ]
        }
      ]
    },
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "Arquivos modificados:", "marks": [{ "type": "strong" }] },
        { "type": "text", "text": " {N} arquivos" }
      ]
    },
    {
      "type": "heading",
      "attrs": { "level": 2 },
      "content": [{ "type": "text", "text": "Teste" }]
    },
    {
      "type": "bulletList",
      "content": [
        {
          "type": "listItem",
          "content": [
            { "type": "paragraph", "content": [{ "type": "text", "text": "{teste 1}" }] }
          ]
        }
      ]
    }
  ]
}
```

### Regras para montar o ADF

1. Substituir os placeholders `{...}` pelo conteúdo real
2. Adicionar/remover `listItem` conforme necessário
3. O arquivo deve ser JSON válido — usar extensão `.json`
4. **Apresentar ao dev uma versão legível** (texto formatado) para revisão antes de postar o JSON

## Template: Commit com Referência a Sub-issue

Ao trabalhar em sub-issues (criadas via `/ticket split`), os commits devem referenciar a key da sub-issue:

```text
${PROJECT}-YYY: descrição do que foi feito para a sub-issue
```

Exemplo (projeto RS):

```text
RS-601: implementar validação de campos obrigatórios
RS-602: ajustar layout do formulário de upload
```

Exemplo (projeto SQ):

```text
SQ-22: aplicar design Navigational Horizon na tela de login
SQ-32: investigar handler do botão Salvar rascunho que não dispara
```
