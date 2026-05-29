---
name: ticket
description: "Gestão de tickets Jira para projetos JRC Brasil — criar issues, branches, sub-issues e fechar com resumo automático. Comandos: /ticket start, /ticket split, /ticket close, /ticket status"
user_invocable: true
argument_description: "Subcomando: start | split | close | status"
metadata:
  version: 1.0.1
---

# Skill: Ticket — Gestão de Tickets Jira

Gerencia o ciclo de vida de tickets Jira integrado com Git, seguindo o fluxo padronizado da JRC Brasil.

**CLI:** `/usr/bin/acli` (Jira CLI v1.3.14) + MCP `mcp__atlassian__*` quando disponível
**Projeto Jira:** detectado dinamicamente — ver "Detecção de Projeto" abaixo
**Branch naming:** `${BRANCH_PREFIX}-XXX_descricao_curta` (ex.: `RS-605_...`, `SQ-22_...`)

## Referências

Antes de executar qualquer comando, leia os arquivos de referência:

- `~/.claude/skills/ticket/references/workflow.md` — Workflow de status, regras de transição, gotchas
- `~/.claude/skills/ticket/references/templates.md` — Templates de descrição e fechamento

## Detecção de Projeto

A skill **não tem projeto Jira hardcoded** — cada repo declara o seu via arquivo
`.jira-project` na raiz (`$(git rev-parse --show-toplevel)/.jira-project`).
Antes de qualquer comando, ler e carregar 3 variáveis em escopo:

```ini
# ~/repos/sales_quote/.jira-project (exemplo)
PROJECT=SQ
BOARD=51
BRANCH_PREFIX=SQ
BASE_BRANCH=main   # opcional — base de branches/PR; default detectado (ver tabela)
```

| Variável | Uso |
|---|---|
| `$PROJECT` | `--project "$PROJECT"` no `acli workitem create`; regex `${PROJECT}-\d+` na detecção da branch; `--jql "parent = ${PROJECT}-XXX"` no `split`/`close` |
| `$BOARD` | `--id $BOARD` em `acli jira board list-sprints` |
| `$BRANCH_PREFIX` | Prefixo do nome da branch (`${BRANCH_PREFIX}-XXX_descricao`). Geralmente igual a `$PROJECT`, mas pode divergir se o time usar convenção própria. |
| `$BASE_BRANCH` | Base para criar branches e abrir PRs (`git checkout`/`gh pr --base`). **Opcional.** Se ausente, **detectar o branch default do repo** — `git symbolic-ref --short refs/remotes/origin/HEAD` (ex.: `origin/main` → `main`) ou `git remote show origin \| sed -n 's/.*HEAD branch: //p'`. ⚠️ **Não assumir `develop`** — `sales_quote`/SQ usa `main`. |

### Bootstrap se `.jira-project` não existir

1. Avisar o dev que o repo não tem `.jira-project` configurado.
2. Perguntar:
   - **Project key** (ex.: `SQ`, `RS`, `BAT`) — sugerir baseado no nome do repo + olhada na auto-memory por entries `project_jira_*`.
   - **Board ID** — descobrir via `mcp__atlassian__searchJiraIssuesUsingJql(jql: "project = $PROJECT", maxResults: 1)` ou `acli jira board list`. Em caso de múltiplos boards, perguntar qual.
   - **Branch prefix** — default igual ao project key; só perguntar se o dev quiser custom.
3. Criar `.jira-project` com os 3 valores + comentário cabeçalho explicando origem. Sugerir adicionar ao `.gitignore` apenas se contiver dados sensíveis (normalmente não — keys e board IDs não são secretos).
4. Continuar o comando solicitado com os valores recém-coletados.

**Por que arquivo no repo (e não env var / auto-memory)?** Versionado junto com o código, explícito, sobrevive a trocas de máquina e a limpezas de memória do Claude. Quem clona o repo já tem a configuração correta.

## Roteamento de Comandos

Analise o argumento passado pelo usuário e execute o comando correspondente:

- `start` → Seção "Comando: start"
- `split` → Seção "Comando: split"
- `close` → Seção "Comando: close"
- `status` → Seção "Comando: status"
- Sem argumento ou argumento não reconhecido → Mostrar lista de comandos disponíveis

---

## Comando: start

**Propósito:** Iniciar desenvolvimento a partir de uma issue existente ou criar nova issue no Jira, branch Git, e transicionar para "Em andamento".

### Detecção de sub-fluxo

Antes de tudo, analisar o argumento passado após `start`:

- Se o argumento contém uma **key Jira** (regex: `${PROJECT}-\d+`) ou uma **URL do Jira** (regex: `https?://jrcbrasil\.atlassian\.net/browse/(${PROJECT}-\d+)`):
  - Extrair a key via regex
  - Seguir o **Sub-fluxo A: Issue existente**
- Caso contrário (sem argumento extra, ou argumento que não é key/URL):
  - Seguir o **Sub-fluxo B: Nova issue**

---

### Sub-fluxo A: Issue existente

1. **Buscar dados da issue:**

   ```bash
   # Dados básicos (summary, status, assignee)
   acli jira workitem view ${PROJECT}-XXX

   # Sprint e story points (custom fields, não aparecem no view padrão)
   acli jira workitem view ${PROJECT}-XXX --fields "customfield_10016,customfield_10020" --json
   ```

   - `customfield_10016` = story points (número ou null)
   - `customfield_10020` = array de sprints (pegar a com `"state": "active"`)
   - Se o comando falhar (issue não encontrada), informar o dev e abortar

2. **Mostrar resumo ao dev:**

   ```text
   📋 ${PROJECT}-XXX — {summary}
   📊 Status: {status}
   👤 Responsável: {assignee ou "Nenhum"}
   🏃 Sprint: {sprint ou "Nenhuma"}
   🎯 Score: {story points ou "Nenhum"}
   ```

3. **Verificar responsável:**
   - Se assignee está vazio/nulo:
     - Perguntar ao dev: "Essa issue não tem responsável. Quer se atribuir como responsável?"
     - Se sim: `acli jira workitem edit --key "${PROJECT}-XXX" --assignee "{username}"`
     - Se não: continuar sem responsável
   - Se já tem assignee: mostrar e continuar

4. **Verificar sprint:**
   - Se a issue **não está em nenhuma sprint** (campo sprint vazio/nulo):
     - Perguntar ao dev: "Essa issue não está em nenhuma sprint. Quer adicionar à sprint atual ou informar outra?"
     - Se sim:
       1. Listar sprints ativas: `acli jira board list-sprints --id $BOARD --state active --json`
       2. Extrair o ID da sprint ativa (ou pedir ao dev para escolher se houver mais de uma)
       3. Atribuir via MCP: `mcp__atlassian__editJiraIssue(issueIdOrKey: "${PROJECT}-XXX", fields: { "customfield_10020": SPRINT_ID })`
     - Se não: continuar sem sprint (registrar que o dev optou por pular)
   - Se já tem sprint: mostrar qual é e continuar

5. **Verificar score (story points):**
   - Se story points está vazio/nulo/zero:
     - Perguntar ao dev: "Essa issue não tem score. Quer atribuir story points? (ex: 1, 2, 3, 5, 8, 13)"
     - Se sim: atribuir via MCP: `mcp__atlassian__editJiraIssue(issueIdOrKey: "${PROJECT}-XXX", fields: { "customfield_10016": N })`
     - Se não: continuar sem score
   - Se já tem story points: mostrar e continuar

6. **Verificar status e transicionar:**
   - Se não está "Em andamento": `acli jira workitem transition --key "${PROJECT}-XXX" --status "Em andamento"`
   - Se já está "Em andamento": pular

7. **Criar branch Git:**

   - Gerar nome: `${BRANCH_PREFIX}-XXX_descricao_curta` (snake_case, sem acentos, max ~50 chars, baseado no summary da issue)
   - Verificar que está em `${BASE_BRANCH}` e atualizado:

     ```bash
     git checkout ${BASE_BRANCH}
     git pull origin ${BASE_BRANCH}
     git checkout -b ${BRANCH_PREFIX}-XXX_descricao_curta
     ```

8. **Output:** Mostrar resumo final:

   ```text
   ✅ Issue: ${PROJECT}-XXX — {summary}
   🌿 Branch: ${BRANCH_PREFIX}-XXX_descricao_curta
   📋 Status: Em andamento
   👤 Responsável: {assignee}
   🔗 Sprint: {sprint ou "Nenhuma"}
   🎯 Score: {story points ou "Nenhum"}
   ```

---

### Sub-fluxo B: Nova issue

1. **Perguntar ao dev:**
   - Nome/summary da issue
   - Descrição (pode ser breve — será formatada no template)
   - Tipo: Tarefa, História, Bug (default: Tarefa)
   - Story points (opcional)
   - Sprint: mostrar sprints ativas para escolha, ou usar sprint corrente. **Se o dev não informar sprint, perguntar explicitamente:** "Quer adicionar à sprint atual?" — não pular silenciosamente.

2. **Criar issue no Jira:**

   ```bash
   acli jira workitem create --project "$PROJECT" --type "{tipo}" --summary "{nome}" --description "{descrição formatada}"
   ```

   - Capturar a key retornada (ex.: `RS-605` ou `SQ-32`)
   - Se story points informados: `mcp__atlassian__editJiraIssue(issueIdOrKey: "${PROJECT}-XXX", fields: { "customfield_10016": N })`
   - Se sprint informada:
     1. Listar sprints ativas: `acli jira board list-sprints --id $BOARD --state active --json`
     2. Atribuir via MCP: `mcp__atlassian__editJiraIssue(issueIdOrKey: "${PROJECT}-XXX", fields: { "customfield_10020": SPRINT_ID })`

3. **Criar branch Git:**

   - Gerar nome: `${BRANCH_PREFIX}-XXX_descricao_curta` (snake_case, sem acentos, max ~50 chars)
   - Verificar que está em `${BASE_BRANCH}` e atualizado:

     ```bash
     git checkout ${BASE_BRANCH}
     git pull origin ${BASE_BRANCH}
     git checkout -b ${BRANCH_PREFIX}-XXX_descricao_curta
     ```

4. **Transicionar issue:**

   ```bash
   acli jira workitem transition --key "${PROJECT}-XXX" --status "Em andamento"
   ```

5. **Output:** Mostrar resumo:

   ```text
   ✅ Issue criada: ${PROJECT}-XXX — {nome}
   🌿 Branch: ${BRANCH_PREFIX}-XXX_descricao_curta
   📋 Status: Em andamento
   🔗 Sprint: {sprint}
   ```

### Regras

- SEMPRE perguntar antes de criar — nunca criar issue sem confirmação do dev
- SEMPRE verificar sprint — tanto para issues existentes quanto novas. Nunca pular sprint silenciosamente.
- Branch DEVE partir de `${BASE_BRANCH}` (detectado/declarado na "Detecção de Projeto" — **não** assumir `develop`)
- Se `git status` mostrar mudanças não commitadas, avisar o dev antes de trocar de branch
- Usar template de descrição de `references/templates.md` (apenas sub-fluxo B)

---

## Comando: split

**Propósito:** Quebrar issue atual em sub-issues no Jira (Passo 04.1).

### Fluxo

1. **Detectar issue atual:**

   - Extrair `${PROJECT}-XXX` do nome da branch corrente via regex: `^(${BRANCH_PREFIX}-\d+)`
   - Se não estiver em branch de issue, pedir a key ao dev

2. **Perguntar ao dev:**

   - Nome/summary da sub-issue
   - Descrição breve (opcional)

3. **Criar sub-issue no Jira:**

   ```bash
   acli jira workitem create --project "$PROJECT" --type "Subtarefa" --summary "{nome}" --description "{descrição}"
   ```

   - Capturar key retornada (ex.: `RS-606` ou `SQ-33`)

4. **Vincular à issue pai:**

   ```bash
   acli jira workitem edit --key "${PROJECT}-YYY" --parent "${PROJECT}-XXX"
   ```

5. **Transicionar sub-issue para Em andamento (se dev confirmar):**

   ```bash
   acli jira workitem transition --key "${PROJECT}-YYY" --status "Em andamento"
   ```

6. **NÃO criar branch nova.** Output:

   ```text
   ✅ Sub-issue criada: ${PROJECT}-YYY — {nome}
   🔗 Vinculada a: ${PROJECT}-XXX
   📌 Branch: continuar na branch atual (${BRANCH_PREFIX}-XXX_descricao)

   Para commitar trabalho desta sub-issue, use:
     git commit -m "${PROJECT}-YYY: {descrição do commit}"
   ```

### Regras

- NUNCA criar branch para sub-issue
- Sub-issues usam tipo "Subtarefa" (PT-BR)
- Perguntar se quer criar mais sub-issues (loop até o dev dizer que terminou)

---

## Comando: close

**Propósito:** Fechar issue com resumo auto-gerado e transições de status (Passo 05).

### Fluxo

1. **Detectar issue:**

   - Extrair `${PROJECT}-XXX` da branch corrente (regex `^(${BRANCH_PREFIX}-\d+)`)
   - Se não encontrar, pedir ao dev

2. **Verificar sub-issues:**

   ```bash
   acli jira workitem search --jql "parent = ${PROJECT}-XXX"
   ```

   - Se houver sub-issues não "Finished", alertar o dev e perguntar se quer continuar

3. **Auto-gerar resumo:**

   - Coletar dados:

     ```bash
     git log ${BASE_BRANCH}..HEAD --oneline
     git diff ${BASE_BRANCH}...HEAD --stat
     acli jira workitem view ${PROJECT}-XXX
     ```

   - Montar resumo usando template de `references/templates.md`:
     - **Visão Geral:** Extrair da descrição da issue no Jira
     - **Solução:** Sintetizar a partir dos commit messages
     - **Teste:** Inferir dos arquivos de teste modificados; se não houver, pedir ao dev

4. **Apresentar rascunho ao dev** — Mostrar o resumo gerado e pedir confirmação ou edições

5. **Comentar na issue — preferir MCP atlassian com markdown:**

   O MCP `mcp__atlassian__addCommentToJiraIssue` aceita markdown direto e converte
   para ADF server-side. Isso elimina o ritual de montar ADF JSON manual + arquivo
   temp + `acli --body-file` (que continua disponível como fallback). Validado em
   prática 2026-05-20 — markdown multi-parágrafo, listas, tabelas, blocos de
   código e bold/itálico renderizam idêntico ao ADF.

   ```text
   mcp__atlassian__addCommentToJiraIssue(
     cloudId: "<cloud-id-da-jrcbrasil>",        # `getAccessibleAtlassianResources` se não souber
     issueIdOrKey: "${PROJECT}-XXX",
     body: "<resumo em markdown — ver template em references/templates.md §Markdown>",
     contentFormat: "markdown"
   )
   ```

   **Fallback (sem MCP atlassian disponível):** montar ADF JSON manual e postar
   via `acli --body-file` — ver `references/templates.md §ADF (legado)` para a
   estrutura e a referência rápida. Markdown e Wiki Markup **não** funcionam
   no `acli` (renderizam como texto puro).

6. **Transicionar até o status "done" — descobrir as transições, não cravar nomes:**

   A sequência é **específica do projeto** (ver `references/workflow.md`). Listar
   as transições disponíveis e caminhar até o status final:

   ```text
   mcp__atlassian__getTransitionsForJiraIssue(cloudId, issueIdOrKey: "${PROJECT}-XXX")
   # escolher a transição cujo to.name é o status "done" do projeto e aplicar por id:
   mcp__atlassian__transitionJiraIssue(cloudId, issueIdOrKey: "${PROJECT}-XXX", transition: { id: "<id>" })
   ```

   - **RS:** `Em andamento → Aprovação → Finished` (duas transições, por nome).
   - **SQ:** `Em andamento → Concluído` direto (**não há `Aprovação`**) —
     `acli --status "Concluído"` funciona (casa pelo nome do **status de
     destino**); alternativamente, MCP transição **id `31`** ("Itens concluídos").
   - Fallback `acli` (pelo nome do **status de destino**): `acli jira workitem transition --key "${PROJECT}-XXX" --status "<status-destino>"`.

7. **Commitar mudanças pendentes:**

   - Verificar `git status` — se houver mudanças não commitadas (staged ou unstaged):
     - Mostrar as mudanças ao dev e perguntar se deve commitar
     - Incluir arquivos untracked relevantes (perguntar ao dev)
     - Gerar mensagem de commit no padrão Conventional Commits (`fix:`, `feat:`, etc.)
     - Incluir a key da issue no body do commit (ex.: `${PROJECT}-XXX`)
   - Após commitar, rodar `yarn lint` para verificar se o código passa no CI
     - Se houver erros de lint, corrigir e commitar o fix antes de prosseguir
   - Se não houver mudanças, pular para o próximo passo

8. **Criar Pull Request:**

   - Push da branch:

     ```bash
     git push -u origin ${BRANCH_PREFIX}-XXX_descricao_curta
     ```

   - Criar PR com `gh`. O body do PR usa **Markdown** (GitHub renderiza Markdown, igual ao MCP atlassian — se você usou markdown no step 5, pode reaproveitar o mesmo body aqui):

     ```bash
     gh pr create --base ${BASE_BRANCH} --title "${PROJECT}-XXX: {summary}" --body-file "/tmp/${PROJECT}-XXX-pr-body.md"
     ```

   - Se PR já existir para a branch, mostrar a URL existente (`gh pr view --web`)
   - O body do PR deve conter o mesmo conteúdo do resumo. Se você usou o caminho
     MCP no step 5, **é o mesmo markdown** — sem duplicação de trabalho.

9. **Voltar para `${BASE_BRANCH}`:**

   ```bash
   git checkout ${BASE_BRANCH}
   git pull origin ${BASE_BRANCH}
   ```

   > Se o dev pediu para **permanecer no branch atual** (fluxo direto no
   > `${BASE_BRANCH}`, sem feature branch e sem PR — como no commit direto em
   > `main`), pular os steps 8-9.

10. **Output:**

   ```text
   ✅ Issue ${PROJECT}-XXX fechada
   📋 Status: Finished
   💬 Resumo postado como comentário
   🔀 PR criada: {URL}
   🌿 Voltou para ${BASE_BRANCH}
   ```

### Regras

- SEMPRE mostrar o resumo para o dev antes de postar
- Verificar sub-issues antes de fechar — alertar se houver pendentes
- Adaptar transições ao status atual (não tentar transicionar para um status em que já está)
- Consultar `references/workflow.md` para a sequência correta de transições
- **Formatação:** preferir MCP atlassian com `contentFormat: "markdown"` para
  comentar no Jira — escreve uma vez o markdown e reaproveita no PR body. O
  caminho `acli --body-file` com ADF JSON manual continua suportado como
  fallback (consultar `references/templates.md §ADF (legado)`), mas é o
  segundo plano agora.
- Antes de criar PR, verificar mudanças não commitadas com `git status`
- Rodar `yarn lint` após commit e antes do push — corrigir erros antes de criar PR

---

## Comando: status

**Propósito:** Mostrar status atual da issue vinculada à branch.

### Fluxo

1. **Detectar issue:** Extrair `${PROJECT}-XXX` da branch corrente

2. **Buscar dados:**

   ```bash
   acli jira workitem view ${PROJECT}-XXX
   acli jira workitem search --jql "parent = ${PROJECT}-XXX"
   ```

3. **Output:**

   ```text
   📋 ${PROJECT}-XXX — {summary}
   📊 Status: {status atual}
   👤 Responsável: {assignee}
   🏃 Sprint: {sprint}

   Sub-issues:
   - ${PROJECT}-601 — {summary} [Em andamento]
   - ${PROJECT}-602 — {summary} [Finished]
   ```

   Se não houver sub-issues, omitir a seção.

---

## Detecção de Issue a partir da Branch

Lógica comum usada por todos os comandos (com `$BRANCH_PREFIX` carregado da
"Detecção de Projeto"):

```javascript
const branch = execSync('git branch --show-current').toString().trim();
// Exemplo: BRANCH_PREFIX="SQ" → regex /^(SQ-\d+)/
const match = branch.match(new RegExp(`^(${BRANCH_PREFIX}-\\d+)`));
const issueKey = match ? match[1] : null;
```

Se `issueKey` for `null`, perguntar ao dev: "Não consegui detectar a issue da
branch atual. Qual é a key? (ex.: `${PROJECT}-605`)"

---

## Tratamento de Erros

- **`acli` falha:** Mostrar o erro completo ao dev e sugerir verificar credenciais/conexão
- **Branch não está em `${BASE_BRANCH}`:** Avisar antes de criar branch
- **Transição falha (`"No allowed transitions found"`):** não insistir no nome cravado —
  listar as transições reais com `mcp__atlassian__getTransitionsForJiraIssue` e
  transicionar pelo `id` da transição cujo `to.name` é o status desejado (ver
  `references/workflow.md`). Lembrar que `acli --status` casa pelo **nome do
  status de destino** (ex.: `--status "Concluído"`).
- **Mudanças não commitadas:** Avisar antes de trocar de branch
