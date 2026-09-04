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

A varredura precisa cobrir **duas** coisas: as `marks` e a **estrutura**. Elas
falham por motivos diferentes e uma passa limpa enquanto a outra está quebrada —
por isso vale rodar as duas de uma vez:

```python
VALIDAS = {'strong', 'em', 'code', 'link', 'strike', 'underline'}
ruim_marks, ruim_estrutura = [], []

def check(n, caminho='root'):
    if isinstance(n, dict):
        for m in n.get('marks', []) or []:
            # mark tem de ser objeto com um `type` da lista
            if not isinstance(m, dict) or m.get('type') not in VALIDAS:
                ruim_marks.append((caminho, m))
        for i, c in enumerate(n.get('content', []) or []):
            # todo item de content e um NO: objeto com `type`. String crua nao e.
            if not isinstance(c, dict) or 'type' not in c:
                ruim_estrutura.append((f'{caminho}.content[{i}]', repr(c)[:60]))
            else:
                check(c, f"{caminho}.{c.get('type')}")
    elif isinstance(n, list):
        for i, c in enumerate(n):
            check(c, f'{caminho}[{i}]')

check(doc)
assert not ruim_marks, f'marks invalidas: {ruim_marks}'
assert not ruim_estrutura, f'content com item que nao e no: {ruim_estrutura}'
```

O caminho (`root.paragraph.content[1]`) é o que transforma o 400 mudo do Jira num
ponto exato do payload — sem ele, sobra bissecção manual.

**O erro clássico que isso pega:** um helper que
aceita `marks` e recebe **string** em vez de lista. `t("texto", "strong")` faz o
loop iterar caractere a caractere e produz `{"type":"s"}`, `{"type":"t"}`,
`{"type":"r"}`… O JSON fica sintaticamente válido, o `python -m json.tool` passa,
e o Jira devolve 400 mudo. Passe sempre lista: `t("texto", ["strong"])`.

Se a varredura acusar marks quebradas em caracteres soltos, dá para consertar o
payload já montado em vez de remontá-lo: junte os caracteres soltos de cada nó
(`''.join(...)`) e, se a palavra resultante estiver em `VALIDAS`, substitua as
marks daquele nó por ela.

**O erro que a varredura de marks NÃO pega:** um helper de lista que recebe
`["texto simples"]` e repassa as strings direto para `content`, produzindo
`{"type":"paragraph","content":["texto simples"]}`. Não há mark nenhuma
envolvida, então a varredura de marks passa **limpa** — e o Jira devolve o mesmo
400 mudo.

A regra que evita a família inteira: **`content` só aceita nós**, nunca strings.
Se o seu helper aceita tanto `"texto"` quanto `{...}` por conveniência, normalize
na entrada em vez de confiar em quem chama:

```python
def _no(x):
    return t(x) if isinstance(x, str) else x   # string vira nó de texto

def p(*filhos):
    return {'type': 'paragraph', 'content': [_no(f) for f in filhos]}
```

⚠️ O mesmo vale para **tipos de nó**, não só marks: `bold` em vez de `strong`,
`italic` em vez de `em`, ou um `type` inexistente produzem o mesmo 400 mudo.
Quando a varredura de marks vier limpa e o 400 persistir, o suspeito seguinte é
um `type` de nó fora da tabela acima.

## Template: Descrição de Issue

Usado ao criar issues no `/ticket start` (sub-fluxo B). A descrição vai em **ADF**
(`--from-json` ou REST): cada bloco abaixo vira um `paragraph` e os critérios um
`bulletList`. Só o fallback sem `--from-json` (`create --description`) recebe
**texto puro** — esse campo não aceita ADF.

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
