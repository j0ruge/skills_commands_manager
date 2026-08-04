# Changelog — ticket

## [1.1.0] — 2026-08-04

### Added

- **Issue nova nasce dentro da sprint, com score — sem depender do MCP.**
  `acli jira workitem create --from-json` aceita `additionalAttributes` com
  `customfield_*`, então sprint e story points podem ser gravados **na criação**.
  Validado em 2026-08-04 no projeto SQ (issue descartável criada com sprint
  `405` + 3 pontos, conferida e deletada). O `start` sub-fluxo B passa a usar
  esse caminho. **Por quê:** o fluxo antigo criava a issue "pelada" e tentava
  editar depois via MCP; quando o MCP não estava autenticado a edição falhava e
  **o cartão ficava no backlog sem sprint nem pontos** — o sintoma relatado.
- **Releitura obrigatória depois de escrever sprint/score** (novo step no
  sub-fluxo A e no B), com verificação independente por
  `acli jira sprint list-workitems --board $BOARD --sprint <ID>`. Uma escrita de
  custom field pode "dar ok" e não aplicar; sem reler, a skill reportava sucesso
  enquanto o cartão continuava no backlog.
- **Como descobrir os IDs dos custom fields**, em vez de confiar nos números:
  `acli jira workitem view <KEY> --fields "*all" --json` traz ~100 campos (o
  `--json` sem `--fields` traz só 5 e **nenhum** custom field — motivo pelo qual
  o `view` parecia "não ter" sprint/score). `10016`/`10020` são do site
  jrcbrasil, não constantes do Jira.
- **Fallbacks para "não acho a sprint ativa"** (`workflow.md §Quando não aparece
  sprint ativa`): `$BOARD` errado é a causa mais comum (`board search` /
  `board list-projects`); descoberta independente do board via JQL
  `sprint in openSprints()`; e o caso legítimo de board sem sprint aberta ou
  kanban — avisar o dev em vez de inventar uma sprint.
- **Story points viraram pergunta de primeira classe** no sub-fluxo B: se o dev
  não souber pontuar, a skill propõe uma estimativa justificada para ele
  confirmar. Antes era um "(opcional)" que se perdia no meio do fluxo.

### Changed

- **Endpoint do MCP atlassian: HTTP+SSE → Streamable HTTP.**
  `https://mcp.atlassian.com/v1/sse` foi descontinuado em **30/jun/2026**; a
  config correta é `claude mcp add --transport http atlassian
  https://mcp.atlassian.com/v1/mcp` (`{"type": "http", ...}` no JSON).
  Documentado em `SKILL.md §Tratamento de Erros` e no `workflow.md` como a
  **primeira** coisa a checar quando o servidor expõe só
  `authenticate`/`complete_authentication` — antes esse sintoma era tratado
  apenas como falta de login.
  Registrada também a diferença medida entre os endpoints (2026-08-04): só
  `https://mcp.atlassian.com/v1/mcp/authv2` responde com
  `WWW-Authenticate: Bearer resource_metadata="…"`, o discovery OAuth (RFC 9728)
  — é a variante a usar quando a autorização não completa no `/v1/mcp`.
- `acli` de referência: v1.3.14 → **v1.3.22** (versão em que `--from-json` /
  `--generate-json` foram validados).
- Caminhos das referências passaram de absolutos
  (`~/.claude/skills/ticket/references/…`) para **relativos** (`references/…`) —
  o absoluto só resolvia na máquina que tem o symlink local, quebrando para quem
  instala pelo marketplace.
- `description` reduzida de ~1.400 para 465 chars (teto do repo é 500). A
  descrição é a superfície de triggering; descrições longas são cortadas
  silenciosamente da lista `/skills` e a skill perde o gatilho. O histórico
  detalhado vive aqui no CHANGELOG, não na descrição.

### Fixed

- **Formato do valor de sprint estava errado na doc**: o exemplo mandava
  `{"customfield_10020": {"id": 471}}`; o valor correto é o **id como número
  puro** (`405`). Um objeto ali é rejeitado/ignorado — mais uma rota para o
  cartão terminar no backlog.
- **Corrigida a afirmação "o `acli` não escreve custom fields"**, que era verdade
  só para o `edit`. A assimetria real, medida na v1.3.22: `create --from-json`
  **aceita** `additionalAttributes`; `edit --from-json` rejeita com
  `json: unknown field "additionalAttributes"`. Também não existe comando de
  sprint que mova work items (`acli jira sprint` só faz
  create/update/view/delete/list-workitems) — para issue **existente** não há
  caminho sem MCP, e a skill agora diz isso ao dev em vez de fingir sucesso.

### Origin

Retrofit pedido após sessões em que a skill "jogava os cartões no backlog e não
conseguia definir os pontos", somado ao aviso de depreciação emitido pelo próprio
servidor MCP da Atlassian. As afirmações novas foram verificadas nesta sessão
contra o Jira de produção (boards 51/SQ e 10/RS) e contra os endpoints MCP.

## [1.0.1] — 2026-05-29

### Fixed

- **Correção do "Corolário" da v1.0.0 — `acli --status` casa pelo NOME DO
  STATUS DE DESTINO, não da transição.** A v1.0.0 documentou o **inverso**
  (que `acli --status "Concluído"` falharia e que o flag casava por nome de
  transição). Em uso real (fechamento de **SQ-42** e **SQ-43**, ambos partindo
  de `Em andamento`) o comportamento observado foi o oposto:
  `acli --status "Concluído"` **funciona**, enquanto
  `acli --status "Itens concluídos"` (o *nome da transição*, id `31`) **falha**
  com `No allowed transitions found for given status`. Isso bate com o próprio
  help do `acli` (`--status` = "Status to transition the work item"). Provável
  causa do engano na v1.0.0: a falha original do SQ-41 era em `"Aprovação"`/
  `"Finished"` — status que **não existem** no board SQ —, não por casamento de
  nome; o `--status "Concluído"` nunca tinha sido testado isolado a partir de
  `Em andamento`.
- **Por quê importa:** a guidance anterior mandava evitar um comando que
  funciona e depender desnecessariamente do MCP. Corrigido em `SKILL.md`,
  `references/workflow.md`, `plugin.json`, `marketplace.json` e `README.md`.
  O MCP `transitionJiraIssue(transition:{id})` segue documentado como
  alternativa robusta. A **Regra 1** (descobrir transições / caminhar passo a
  passo) permanece — o mesmo erro também ocorre a partir de um status-fonte
  inválido.

### Added

- Nota em `workflow.md §Sprint e Story Points via MCP`: numa sessão nova o
  servidor atlassian MCP pode expor só `authenticate`/`complete_authentication`
  (as tools de escrita não aparecem no ToolSearch). Chamar
  `mcp__atlassian__authenticate`, repassar a URL ao dev e prosseguir após
  autorizar; **story points/sprint ficam bloqueados até autenticar** (o `acli`
  não escreve custom fields), mas transição e comentário (ADF) seguem via `acli`.

### Origin

Sessão de fechamento de **SQ-42 + SQ-43** (sales_quote): com o MCP atlassian
não-autenticado, a transição foi feita por `acli` — a tentativa pelo *nome da
transição* (`"Itens concluídos"`, conforme a doc v1.0.0) falhou, e o *nome do
status* (`"Concluído"`) funcionou, desmentindo o corolário da v1.0.0.

## v1.0.0 — 2026-05-29

### Added

- **Empacotamento inicial** da skill `ticket` (antes apenas local em
  `~/.claude/skills/ticket/`) no marketplace, com `plugin.json`, este CHANGELOG,
  entrada em `marketplace.json` e linha no `README`. Capacidades existentes:
  comandos `/ticket start | split | close | status`, detecção de projeto
  por-repo via `.jira-project` (`PROJECT`/`BOARD`/`BRANCH_PREFIX`), criação de
  issues/sub-issues, branches, e fechamento com resumo auto-gerado. Prefere
  `acli` + MCP atlassian (markdown em comentários; custom fields como story
  points/sprint que o `acli` não escreve).
- **Lição 1 — transições são por-projeto, não universais.** A documentação
  cravava a sequência do RS (`Em andamento → Aprovação → Finished`) como se
  valesse para todos os boards. O board **SQ não tem `Aprovação`**: vai
  `Em andamento → Concluído` direto, via transição **id `31`** ("Itens
  concluídos"). Agora o `close` e o `workflow.md` mandam **descobrir** as
  transições com `getTransitionsForJiraIssue` e transicionar por **id**.
- **Corolário — `acli --status` casa pelo NOME DA TRANSIÇÃO, não do status.**
  No SQ a transição p/ "Concluído" chama-se "Itens concluídos" — então
  `acli --status "Concluído"` falha, mas `transitionJiraIssue(transition:{id:"31"})`
  funciona. Documentado como o caminho confiável quando o nome diverge.
- **Lição 2 — base de branch é por-projeto.** Novo campo opcional `BASE_BRANCH`
  no `.jira-project`, com **fallback que detecta o branch default do repo**
  (`git symbolic-ref --short refs/remotes/origin/HEAD`). Substituídas todas as
  referências cravadas a `develop` em `start`/`close` por `${BASE_BRANCH}`.
  ⚠️ Não assumir `develop` — `sales_quote`/SQ usa `main`.

### Why / Origin

Sessão de fechamento do ticket **SQ-41** (sales_quote): o `/ticket close`
tentou `acli --status "Aprovação"` e `"Finished"` e falhou 2× com
`"No allowed transitions found for given status"`, porque o board SQ não tem
essa etapa. A correção (descobrir transições por id + base de branch por-projeto)
foi aplicada à skill local; este empacotamento traz a skill para o marketplace
para ganhar versionamento e o fluxo do `retrofit-skill`.
