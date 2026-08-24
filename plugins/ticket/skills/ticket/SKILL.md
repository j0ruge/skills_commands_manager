---
name: ticket
description: "Jira ticket lifecycle for JRC Brasil projects, integrated with Git — create issues/sub-issues and branches, close with an auto-generated summary. Per-repo config via `.jira-project`; discovers project-specific transitions instead of assuming. Creates issues already in the active sprint, with story points and fixVersion, then reads each field back with the sensor that can actually see it. Triggers — ticket, /ticket, open, Jira, criar issue, fechar ticket, sprint, story points, fixVersion, acli."
user_invocable: true
argument_description: "Subcomando: start (open) | split | close | status"
metadata:
  version: 1.2.0
---

# Skill: Ticket — Gestão de Tickets Jira

Gerencia o ciclo de vida de tickets Jira integrado com Git, seguindo o fluxo padronizado da JRC Brasil.

**CLI:** `/usr/bin/acli` (Jira CLI — validado na v1.3.22; `--from-json` em
`workitem create` exige ≥ 1.3.2x, confirme com `acli --version`) + MCP
`mcp__atlassian__*` quando disponível
**Projeto Jira:** detectado dinamicamente — ver "Detecção de Projeto" abaixo
**Branch naming:** `${BRANCH_PREFIX}-XXX_descricao_curta` (ex.: `RS-605_...`, `SQ-22_...`)

## Referências

Antes de executar qualquer comando, leia os arquivos de referência (caminhos
relativos a esta skill — funcionam tanto instalada pelo marketplace quanto local):

- `references/workflow.md` — Workflow de status, transições, sprint/story points, gotchas do `acli`
- `references/templates.md` — Templates de descrição e fechamento

## Detecção de Projeto

A skill **não tem projeto Jira hardcoded** — cada repo declara o seu via arquivo
`.jira-project` na raiz (`$(git rev-parse --show-toplevel)/.jira-project`).
Antes de qualquer comando, ler e carregar 3 variáveis em escopo:

```ini
# ~/repos/sales_quote/.jira-project (exemplo real)
PROJECT=SQ
BOARD=51
BRANCH_PREFIX=SQ
BASE_BRANCH=develop   # opcional — base de branches/PR; se ausente, detectar (ver tabela)
```

| Variável | Uso |
|---|---|
| `$PROJECT` | `--project "$PROJECT"` no `acli workitem create`; regex `${PROJECT}-\d+` na detecção da branch; `--jql "parent = ${PROJECT}-XXX"` no `split`/`close` |
| `$BOARD` | `--id $BOARD` em `acli jira board list-sprints` |
| `$BRANCH_PREFIX` | Prefixo do nome da branch (`${BRANCH_PREFIX}-XXX_descricao`). Geralmente igual a `$PROJECT`, mas pode divergir se o time usar convenção própria. |
| `$BASE_BRANCH` | Base para criar branches e abrir PRs (`git checkout`/`gh pr --base`). **Opcional.** Se ausente, **detectar** — nunca chutar: `git symbolic-ref --short refs/remotes/origin/HEAD` (ex.: `origin/develop` → `develop`) ou `git remote show origin \| sed -n 's/.*HEAD branch: //p'`. ⚠️ Não assumir **nem** `main` **nem** `develop` — ver `references/workflow.md §Branch base`. |

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

- `start` (ou `open`, `abrir`) → Seção "Comando: start"
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
   - ⚠️ Esses IDs são **do site jrcbrasil**, não uma constante do Jira. Se vierem
     vazios num projeto novo, **descubra**: `acli jira workitem view <KEY> --fields "*all" --json`
     lista os ~100 campos (o `--json` sem `--fields` traz só 5 e **nenhum**
     custom field). A sprint é o array com `boardId`/`state`; story points é o
     número solto. Ver `references/workflow.md §Descobrir os IDs`.

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
     - Se sim: `acli jira workitem edit --key "${PROJECT}-XXX" --assignee "@me"`
       ⚠️ **Use `@me`, não o e-mail.** O e-mail da sessão (`userEmail`) não é
       necessariamente a identidade da conta Jira — e quando não é, o `acli`
       responde `✗ Failure: ... can't be edited: unexpected error, trace id: …`,
       que não nomeia o campo nem a causa. Medido duas vezes (2026-08-07 e
       2026-08-24, projeto SQ), com `it@jrcbrasil.com` recusado e a conta real
       sendo outra.
       Para atribuir a **outra pessoa**, o caminho é o accountId via REST:
       ```bash
       set -a; . ~/.hermes/.env; set +a
       AID=$(curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
         "https://jrcbrasil.atlassian.net/rest/api/3/myself" | python3 -c 'import json,sys;print(json.load(sys.stdin)["accountId"])')
       curl -s -o /dev/null -w '%{http_code}\n' -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
         -X PUT -H "Content-Type: application/json" \
         -d "{\"fields\":{\"assignee\":{\"accountId\":\"$AID\"}}}" \
         "https://jrcbrasil.atlassian.net/rest/api/3/issue/${PROJECT}-XXX"   # espera 204
       ```
     - Se não: continuar sem responsável
   - Se já tem assignee: mostrar e continuar

4. **Verificar sprint:**
   - Se a issue **não está em nenhuma sprint** (campo sprint vazio/nulo):
     - Perguntar ao dev: "Essa issue não está em nenhuma sprint. Quer adicionar à sprint atual ou informar outra?"
     - Se sim:
       1. Descobrir a sprint ativa: `acli jira board list-sprints --id $BOARD --state active --json`
          — a ativa é a de `"state": "active"`. **Não descarte uma sprint pelo
          `endDate` no passado**: times deixam a sprint correr além da data
          planejada e ela continua `active` (o board 51 tinha, em ago/2026, a
          sprint 405 ativa com `endDate` de fev/2026). Se a lista vier vazia, ver
          `references/workflow.md §Quando não aparece sprint ativa`.
       2. Extrair o `id` (pedir ao dev para escolher se houver mais de uma)
       3. Atribuir via MCP: `mcp__atlassian__editJiraIssue(issueIdOrKey: "${PROJECT}-XXX", fields: { "customfield_10020": SPRINT_ID })`
          — o valor é o **número puro** (`405`), não `{ "id": 405 }`.
          ⚠️ Para issue **já existente** este é o único caminho automatizado: o
          `acli` **não escreve custom fields no `edit`** (ver §Tratamento de
          Erros). Se o MCP não estiver disponível, diga isso ao dev em vez de
          seguir como se tivesse funcionado.
     - Se não: continuar sem sprint (registrar que o dev optou por pular)
   - Se já tem sprint: mostrar qual é e continuar

5. **Verificar score (story points):**
   - Se story points está vazio/nulo/zero:
     - Perguntar ao dev: "Essa issue não tem score. Quer atribuir story points? (ex: 1, 2, 3, 5, 8, 13)"
     - **Não devolva a pergunta em branco.** Você acabou de ler o summary e a
       descrição da issue — proponha um número com uma justificativa de uma
       linha (escopo, arquivos/serviços afetados, se há migração ou teste
       novo) e deixe o dev confirmar ou corrigir. Ancorar a conversa numa
       estimativa é o que destrava a pontuação; pedir um número do nada é o
       que faz o campo ficar vazio.
     - Se sim: atribuir via MCP: `mcp__atlassian__editJiraIssue(issueIdOrKey: "${PROJECT}-XXX", fields: { "customfield_10016": N })`
       (mesma ressalva do passo 4 — `acli edit` não grava este campo)
     - Se não: continuar sem score
   - Se já tem story points: mostrar e continuar

6. **Confirmar que gravou (releitura obrigatória):**

   Uma escrita de custom field pode retornar "ok" e não aplicar — e o sintoma é
   silencioso: o cartão fica no backlog, fora da sprint, e ninguém percebe até a
   daily. Depois de mexer em sprint/score, **releia e compare**:

   ```bash
   acli jira workitem view ${PROJECT}-XXX --fields "customfield_10016,customfield_10020" --json
   ```

   Verificação independente de que o cartão está mesmo na sprint — **por JQL,
   que é determinístico**:

   ```bash
   acli jira workitem search --jql "key = ${PROJECT}-XXX AND sprint in openSprints()" --fields "key,status"
   ```

   ⚠️ **Não use `sprint list-workitems` como sensor.** Ele pagina (~30 itens) e o
   cartão recém-criado costuma cair fora da primeira página — seguir a skill ao pé
   da letra produz exatamente o alarme falso que este passo existe para evitar
   (*"a sprint não foi aplicada"* sobre um cartão que **está** na sprint). Medido
   no SQ-74 (2026-08-07) e de novo no SQ-107 (2026-08-24).

   ⚠️ **O exit code do `acli` não é sensor de nada.** Ele imprime `✗ Failure: …`
   e **sai 0** — cadeia `&&` e checagem de `$?` são decorativas aqui. O que diz a
   verdade é a releitura do campo.

   Se o valor não bateu com o que foi pedido, **avise o dev explicitamente**
   ("a sprint não foi aplicada — o cartão continua no backlog") em vez de
   reportar sucesso no resumo final.

7. **Verificar status e transicionar:**
   - Se não está "Em andamento": `acli jira workitem transition --key "${PROJECT}-XXX" --status "Em andamento"`
   - Se já está "Em andamento": pular

8. **Criar branch Git:**

   - Gerar nome: `${BRANCH_PREFIX}-XXX_descricao_curta` (snake_case, sem acentos, max ~50 chars, baseado no summary da issue)
   - Verificar que está em `${BASE_BRANCH}` e atualizado:

     ```bash
     git checkout ${BASE_BRANCH}
     git pull origin ${BASE_BRANCH}
     git checkout -b ${BRANCH_PREFIX}-XXX_descricao_curta
     # poka-yoke: a branch nasceu MESMO da base atual?
     git fetch origin -q
     git rev-list --left-right --count HEAD...origin/${BASE_BRANCH}   # espera `0	0`
     ```

   ⚠️ **Não canalize o `pull` para `tail` dentro de uma cadeia `&&`**: o exit
   status de um pipeline é o do **último** comando, então um pull que falhou
   (mudança não commitada + rebase configurado é o caso comum) deixa a cadeia
   seguir e a branch nasce de base não verificada, sem nada avisar. Por isso a
   verificação acima mede a base em vez de confiar no pull.

9. **Output:** Mostrar resumo final:

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
   - **Story points** — perguntar sempre, não tratar como detalhe opcional que
     some no meio do fluxo: "Quantos pontos? (1, 2, 3, 5, 8, 13)". Se o dev não
     souber, ofereça uma estimativa sua com a justificativa (escopo/arquivos
     afetados) para ele confirmar ou corrigir — é mais fácil ajustar um número
     proposto do que produzir um do zero. Só siga sem score se ele disser que
     não quer pontuar.
   - Sprint: mostrar sprints ativas para escolha, ou usar sprint corrente. **Se o dev não informar sprint, perguntar explicitamente:** "Quer adicionar à sprint atual?" — não pular silenciosamente.
   - **fixVersion** (rótulo de release, ex.: `0.8.0`): perguntar sempre que o
     projeto versione releases. Liste o que existe e proponha o próximo número,
     em vez de pedir do nada — ver §fixVersion em `references/workflow.md`, que
     traz o detalhe que morde: **`acli` e MCP são cegos nesse campo**, e a flag
     `released` no Jira **não é sensor de release** (no SQ, a `0.7.1` seguia
     marcada `unreleased` estando em produção desde 20/ago). Quem sabe se
     lançou é o repo: `origin/main` + a versão no `package.json`.

2. **Descobrir a sprint ativa (antes de criar):**

   ```bash
   acli jira board list-sprints --id $BOARD --state active --json
   ```

   Pegar o `id` da sprint com `"state": "active"` — **ignorando o `endDate`**,
   que frequentemente já passou sem a sprint ter sido fechada. Se houver mais de
   uma, perguntar ao dev; se vier vazio, ver `references/workflow.md
   §Quando não aparece sprint ativa`.

3. **Criar issue no Jira — já com sprint e story points:**

   O caminho confiável é `--from-json` com `additionalAttributes`, que aceita
   custom fields **na criação**. Isso é o que impede o cartão de nascer no
   backlog: criar primeiro e tentar editar depois depende do MCP autenticado, e
   quando ele não está o cartão fica órfão.

   ```bash
   cat > /tmp/${PROJECT}-new.json <<'JSON'
   {
     "projectKey": "SQ",
     "type": "Tarefa",
     "summary": "{nome}",
     "description": { "version": 1, "type": "doc", "content": [
       { "type": "paragraph", "content": [ { "type": "text", "text": "{descrição}" } ] }
     ] },
     "additionalAttributes": {
       "customfield_10016": 3,
       "customfield_10020": 405
     }
   }
   JSON
   acli jira workitem create --from-json /tmp/${PROJECT}-new.json
   ```

   - `customfield_10016` = story points (número); `customfield_10020` = **id da
     sprint como número puro** (`405`, não `{"id": 405}`)
   - Omitir uma chave de `additionalAttributes` quando o dev não informou o valor
   - `description` aqui é **ADF**, não markdown (o `--from-json` não converte)
   - Capturar a key retornada (ex.: `RS-605` ou `SQ-32`)
   - Se a versão do `acli` não tiver `--from-json`, cair para o caminho antigo
     (`create` simples + `mcp__atlassian__editJiraIssue`) e avisar o dev que
     sprint/score dependem do MCP autenticado

   **Quando houver fixVersion, prefira o REST — ele faz tudo numa chamada.** O
   `--from-json` do `acli` não escreve `fixVersions`, então o caminho dele exige
   um segundo passo que só existe via REST de qualquer forma. `POST
   /rest/api/3/issue` aceita `fixVersions`, `customfield_10016` (pontos) e
   `customfield_10020` (sprint, **número puro**) juntos, com `description` em
   ADF — uma chamada, um ponto de falha (medido no SQ-107, 2026-08-24):

   ```bash
   set -a; . ~/.hermes/.env; set +a
   curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -X POST -H "Content-Type: application/json" \
     --data-binary @/tmp/nova-issue.json \
     "https://jrcbrasil.atlassian.net/rest/api/3/issue"
   # fields: { project:{id}, issuetype:{name}, summary, description(ADF),
   #           fixVersions:[{id}], customfield_10016: N, customfield_10020: SPRINT_ID }
   ```

   Monte o ADF com um script (heredoc Python) em vez de escrever JSON à mão: um
   `description` malformado é recusado **sem dizer qual nó** está errado.

4. **Confirmar que a issue nasceu completa** — cada campo pelo sensor que o
   enxerga (é literalmente diferente por campo):

   ```bash
   # sprint + score: o acli lê bem
   acli jira workitem view ${PROJECT}-XXX --fields "customfield_10016,customfield_10020" --json
   # fixVersion: SÓ o REST GET lê — o acli devolve [] mesmo com o campo gravado
   curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
     "https://jrcbrasil.atlassian.net/rest/api/3/issue/${PROJECT}-XXX?fields=fixVersions,customfield_10016,customfield_10020,status,assignee"
   ```

   Se algum campo não veio como pedido, dizer isso ao dev — o cartão está no
   backlog ou sem rótulo de release. Não reportar sucesso sem essa releitura.

5. **Criar branch Git:**

   - Gerar nome: `${BRANCH_PREFIX}-XXX_descricao_curta` (snake_case, sem acentos, max ~50 chars)
   - Verificar que está em `${BASE_BRANCH}` e atualizado:

     ```bash
     git checkout ${BASE_BRANCH}
     git pull origin ${BASE_BRANCH}
     git checkout -b ${BRANCH_PREFIX}-XXX_descricao_curta
     ```

6. **Transicionar issue:**

   ```bash
   acli jira workitem transition --key "${PROJECT}-XXX" --status "Em andamento"
   ```

7. **Output:** Mostrar resumo:

   ```text
   ✅ Issue criada: ${PROJECT}-XXX — {nome}
   🌿 Branch: ${BRANCH_PREFIX}-XXX_descricao_curta
   📋 Status: Em andamento
   🔗 Sprint: {sprint}
   🎯 Score: {story points ou "Nenhum"}
   ```

### Regras

- SEMPRE perguntar antes de criar — nunca criar issue sem confirmação do dev
- SEMPRE verificar sprint — tanto para issues existentes quanto novas. Nunca pular sprint silenciosamente.
- **Issue nova nasce dentro da sprint** (`create --from-json` com
  `additionalAttributes`), não criada-e-depois-editada. O caminho
  criar→editar depende do MCP autenticado; quando ele falha, o cartão fica no
  backlog e a falha passa despercebida.
- **Releia depois de escrever** sprint/score e confirme antes de dizer que deu
  certo (sub-fluxo A step 6 / sub-fluxo B step 4)
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
- **`json: unknown field "additionalAttributes"` no `edit`:** não é erro de
  sintaxe — o `acli` aceita `additionalAttributes` **só no `create`**. Para
  issue existente, custom fields (sprint/story points) só via MCP
  `editJiraIssue`. Verificado na v1.3.22.
- **MCP atlassian ausente ou só com `authenticate`/`complete_authentication`:**
  antes de concluir que é falta de login, **confira o endpoint** — o transporte
  HTTP+SSE (`https://mcp.atlassian.com/v1/sse`) foi descontinuado em
  30/jun/2026. A config precisa ser Streamable HTTP:

  ```bash
  claude mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp
  ```

  Equivalente em `~/.claude.json` (por projeto) ou `.mcp.json`:
  `{"type": "http", "url": "https://mcp.atlassian.com/v1/mcp"}` — o `"type":
  "sse"` antigo é o sintoma. Se a autenticação não completar nesse endpoint,
  tente `https://mcp.atlassian.com/v1/mcp/authv2`: só ele responde com
  `WWW-Authenticate: ... resource_metadata=...`, o discovery OAuth (RFC 9728)
  que o cliente usa para achar o servidor de autorização sozinho.
- **Branch não está em `${BASE_BRANCH}`:** Avisar antes de criar branch
- **Transição falha (`"No allowed transitions found"`):** não insistir no nome cravado —
  listar as transições reais com `mcp__atlassian__getTransitionsForJiraIssue` e
  transicionar pelo `id` da transição cujo `to.name` é o status desejado (ver
  `references/workflow.md`). Lembrar que `acli --status` casa pelo **nome do
  status de destino** (ex.: `--status "Concluído"`).
- **Mudanças não commitadas:** Avisar antes de trocar de branch
