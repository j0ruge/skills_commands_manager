# Changelog — ticket

## [1.5.0] — 2026-09-11

Quatro lições de um `close` real (RS-877, projeto RS). Três são sensores que
mentem de formas diferentes; a quarta é um passo que faltava no fluxo.

### `acli jira workitem comment` é um GRUPO, não um comando

`acli jira workitem comment --key ... --body-file ...` devolve
`✗ Error: unknown flag: --key`, que soa como flag errada e manda a investigação
para o lugar errado. O comando é **`comment create`**. A skill dizia "postar via
`acli --body-file`" sem nomear o subcomando; agora nomeia, com exemplo.

### 🔴 `acli comment list --json` achata o ADF para texto puro

O sensor óbvio para "o comentário ficou formatado?" é reler pelo `acli`. Ele
devolve o `body` como **string crua** mesmo quando o ADF foi armazenado
perfeitamente — e a conclusão natural ("o ADF não foi interpretado") é falsa.
Quase virou um defeito reportado que não existia: o REST mostrou o `body` como
objeto, com os 17 nós certos.

A skill já avisava que o **exit code** do `acli` não é sensor. Esta é a mesma
família por outra porta: a **leitura de volta** também não é. O veredito é o
`GET /rest/api/3/issue/<KEY>/comment`, e o comando pronto está no step 5 do
`close`.

### A tabela de transições descrevia convenção como se fosse restrição

A linha do RS dizia "duas transições (`Aprovação`, depois `Finished`)". Medido: a
partir de `Em andamento` existe `id=31 Itens concluídos → Finished`, que **pula a
Aprovação**. O caminho de duas etapas é o **processo do time**, não um limite do
board — e vale segui-lo mesmo assim, porque é o rastro que o time espera; o
atalho economiza uma chamada e apaga a etapa do histórico.

Junto, um detalhe que a Regra 1 implicava sem dizer: **o conjunto de transições
muda conforme o status atual**. De `Aprovação` aparece `id=6 DONE → Finished`,
que não existe a partir de `Em andamento`. Reaproveitar ids de uma leitura
anterior quebra.

### O `close` não perguntava `fixVersion`

O `start` pergunta sempre; o `close` fechava um ticket que foi a produção sem
rótulo de release — foi o que aconteceu na RS-877. Novo step 7 (os seguintes
renumerados): lê o campo, compara com as tags do repo, e trata o caso difícil
com cuidado — quando a versão **não existe** no Jira, para e pergunta, porque
criar `fixVersion` é ato de nível de projeto, não detalhe de fechamento.

## [1.5.0] — 2026-09-11

Quatro lições de um `close` real (RS-877, projeto RS). Três são sensores que
mentem de formas diferentes; a quarta é um passo que faltava no fluxo.

### `acli jira workitem comment` é um GRUPO, não um comando

`acli jira workitem comment --key ... --body-file ...` devolve
`✗ Error: unknown flag: --key`, que soa como flag errada e manda a investigação
para o lugar errado. O comando é **`comment create`**. A skill dizia "postar via
`acli --body-file`" sem nomear o subcomando; agora nomeia, com exemplo.

### 🔴 `acli comment list --json` achata o ADF para texto puro

O sensor óbvio para "o comentário ficou formatado?" é reler pelo `acli`. Ele
devolve o `body` como **string crua** mesmo quando o ADF foi armazenado
perfeitamente — e a conclusão natural ("o ADF não foi interpretado") é falsa.
Quase virou um defeito reportado que não existia: o REST mostrou o `body` como
objeto, com os 17 nós certos.

A skill já avisava que o **exit code** do `acli` não é sensor. Esta é a mesma
família por outra porta: a **leitura de volta** também não é. O veredito é o
`GET /rest/api/3/issue/<KEY>/comment`.

### A tabela de transições descrevia convenção como se fosse restrição

A linha do RS dizia "duas transições (`Aprovação`, depois `Finished`)". Medido: a
partir de `Em andamento` existe `id=31 Itens concluídos → Finished`, que **pula a
Aprovação**. O caminho de duas etapas é o **processo do time**, não um limite do
board — e vale segui-lo mesmo assim, porque é o rastro que o time espera; o
atalho economiza uma chamada e apaga a etapa do histórico.

Junto, um detalhe que a Regra 1 implicava sem dizer: **o conjunto de transições
muda conforme o status atual**. De `Aprovação` aparece `id=6 DONE → Finished`,
que não existe a partir de `Em andamento`. Reaproveitar ids de uma leitura
anterior quebra.

### O `close` não perguntava `fixVersion`

O `start` pergunta sempre; o `close` fechava um ticket que foi a produção sem
rótulo de release — foi o que aconteceu na RS-877. Novo step 7 (os seguintes
renumerados): lê o campo, compara com as tags do repo, e trata o caso difícil
com cuidado — quando a versão **não existe** no Jira, para e pergunta, porque
criar `fixVersion` é ato de nível de projeto, não detalhe de fechamento.

## [1.4.1] — 2026-09-10

Uma sessão real (abertura do **SQ-122** no projeto SQ) cobrou a conferência que a
1.4.0 tinha acabado de alinhar. Todas as lições abaixo foram **medidas**.

### Fixed

- **A JQL de conferência tem lag de indexação — e a 1.4.0 a tinha promovido a
  sensor** (`SKILL.md` sub-fluxos A/B, `references/workflow.md §Conferir que
  gravou`). Segundos após um `POST /issue` que nasceu com `customfield_10020: 405`,
  `key = SQ-122 AND sprint in openSprints()` devolveu `{"issues":[]}` enquanto
  `GET /issue/SQ-122?fields=customfield_10020` já mostrava `(405, "Formulário",
  active)`; a mesma JQL achou a issue segundos depois. Quem seguisse a regra
  *"se não bater, reportar a falha"* anunciaria ao dev um cartão no backlog que
  **estava** na sprint — o alarme falso que a seção existe para evitar, e pelo
  qual o `sprint list-workitems` já tinha sido descartado (por paginação). O
  veredito pós-criação passa a ser a **leitura do campo**; a JQL fica para
  conferência tardia, com o desempate `key = X` sozinha, que separa "não está na
  sprint" de "ainda não indexou". Três sensores desta skill já falharam de três
  jeitos diferentes — paginação, lag e silêncio —, e o texto agora diz isso.
- **`acli workitem search` que não casa nada imprime NADA** — sem linha, sem
  "0 results", sem erro, e ainda sai 0. Saída vazia é indistinguível de comando
  quebrado, então não vale como veredito. Registrado ao lado do `✗ Failure` que
  sai 0.

### Changed

- **Um `GET` do REST substitui o par de ferramentas na releitura.** A 1.2.0 tinha
  tornado a conferência *por campo* ("o sensor difere por campo") e o resultado
  prático era rodar `acli view` para dois campos e `curl` para o `fixVersion`. Um
  `GET /issue/<KEY>?fields=status,assignee,fixVersions,customfield_10016,customfield_10020`
  lê os cinco de uma vez e responde na hora — a assimetria continua verdadeira
  (o `acli` **não** lê `fixVersions`), só deixa de custar duas chamadas.

### Added

- **Os dois ids que o `POST /rest/api/3/issue` exige** (`references/workflow.md`).
  O corpo pede `project` e `issuetype` por **id**, e o `.jira-project` guarda a
  *key* — a receita de criação em uma chamada estava incompleta sem isso.
  `GET /project/<KEY>` e `GET /issue/createmeta/<KEY>/issuetypes` resolvem, com os
  valores medidos em SQ como exemplo (e o lembrete de confirmar: tipo de issue é
  configuração de projeto).
- **O envelope de `board list-sprints --json` é `{"sprints":[…]}`** — não lista
  nua, não `values`. Um parser escrito por analogia com outras APIs do Jira quebra
  com `'str' object has no attribute 'get'`, mensagem que não sugere o formato
  certo.
- **O construtor de ADF vai num arquivo, não num heredoc canalizado**
  (`references/templates.md`). Um typo (`])` onde cabia `]}`) faz o Python apontar
  para "linha N de stdin" e obriga a repassar o script inteiro; em arquivo, o
  conserto é uma linha. E heredoc **quotado** entrega UTF-8 intacto — tirar acento
  "por segurança" só custa a rodada de devolvê-los.

## [1.4.0] — 2026-09-03

Duas frentes: três lições **medidas** numa sessão real de 2026-09-02 (abriu 4 cartões
RS-850…RS-853, criou vínculos de bloqueio e comentou num quinto — o detalhe está em
`skills/ticket/CHANGELOG.md`) e o prompt audit da skill contra o modelo atual
(`/claude-api prompt-audit`, alvo Claude Fable 5.1), a última da rodada de 16 skills do
marketplace. Relatório e diff do audit ficaram fora do repo; aqui vai o quê e o porquê.

### Added

- **Vínculos entre issues (`references/workflow.md §Vínculos entre issues`).** Não havia nada
  sobre `issueLink`, e o campo só existe via REST. O detalhe que morde: em
  `POST /rest/api/3/issueLink` **quem executa o verbo `outward` é o `inwardIssue`** — ler o
  payload da esquerda para a direita monta o oposto do que se queria, e o Jira aceita os
  dois sentidos sem erro. Entram os tipos de link do site, o exemplo na direção certa, a
  releitura de conferência **pela issue-alvo** (mesma disciplina de sprint/story points) e
  a remoção de link errado, um id por chamada (a lista inteira numa URL devolve `HTTP 000`,
  que parece falha de rede).
- **Checagem de estrutura do ADF junto com a de marks (`references/templates.md §Antes de
  postar`).** A varredura da 1.3.0 só olhava `marks`; um helper de lista que repassa strings
  direto para `content` gera `{"type":"paragraph","content":["texto"]}`, sem mark nenhuma, e
  a varredura passava **limpa** — o Jira devolvia o mesmo 400 mudo. Agora todo item de
  `content` tem de ser nó com `type`, o relatório traz o caminho (`root.paragraph.content[1]`)
  e a receita é normalizar string→nó na entrada do helper.
- **Registrar cartão sem começar o trabalho (`SKILL.md §Registrar cartão SEM começar`).** O
  sub-fluxo B assumia que criar issue é o primeiro passo de programar (branch + "Em
  andamento"). Defeito de QA/code review registrado para o time priorizar não é isso: a
  branch nasce vazia e o status mente. A seção diz quando pular branch e transição
  (sprint, pontos, `fixVersion` e releitura continuam), e as Regras distinguem "abrir para
  já começar" de "registrar para priorizar".

### Changed — prompt audit

- **PII fora do corpo.** O e-mail pessoal e o nome de uma pessoa serviam de "prova" da
  regra `--assignee "@me"` em `SKILL.md` e `workflow.md`; a regra e o sintoma
  (`✗ Failure … trace id`) ficam, a identidade sai.
- **Changelog fora do workflow.** O blockquote "Correção de 2026-08-07: esta skill
  afirmava…" era um diff contra uma versão do prompt que o modelo nunca viu; fica só a
  instrução viva ("entre com a saída do comando").
- **Tabela de sensores alinhada.** `workflow.md §Sprint e Story Points` ainda listava
  `sprint list-workitems` como forma de conferir — o comando que a 1.2.0 tirou do papel de
  sensor por paginar. A célula aponta para o JQL `sprint in openSprints()`.
- **Arqueologia vira regra.** Treze trechos "medido no SQ-74 (2026-08-07) e de novo no
  SQ-107…" perderam ticket, projeto e história; ficou a regra com o mecanismo da falha e,
  onde havia, um único carimbo de verificação. As falhas são das ferramentas (`acli` sai 0,
  paginação, 400 mudo, `fixVersion` cego), não do modelo — por isso nenhuma regra saiu.
- **Tom normal nas Regras**: `SEMPRE`/`NUNCA`/`DEVE` em cinco linhas viram frase plana com a
  razão ao lado (o modelo atual sobre-aplica ênfase em caps).
- **`yarn lint` deixa de ser regra** numa skill multi-projeto ("rodar o lint do projeto, o
  mesmo que o CI roda"); `/usr/bin/acli` vira `acli`; fraseado migratório ("elimina o
  ritual", "segundo plano agora", "caminho antigo") reescrito como estado presente; nota do
  template de descrição corrigida (no sub-fluxo B a descrição vai em ADF, não texto puro);
  typo que invertia uma instrução ("não cheque" → "não chute").
- **Description 498 → 456 chars, 10 → 8 gatilhos** (saem `/ticket`, que é invocação por
  slash, e `open`, genérico demais). Estava a 2 chars do cap de 500 que derruba o gatilho em
  silêncio, e crescia a cada retrofit.

Registrados sem mudança: `~/.hermes/.env` ×4 como fonte das credenciais REST (convenção da
equipe; falha alto se faltar), "(Passo 04.1)"/"(Passo 05)", o trecho JS de detecção da
branch, e a leitura das duas references em todo comando.

## [1.3.0] — 2026-08-26

A skill já mandava montar ADF por script e já avisava que malformado é recusado
"sem dizer qual nó". O que faltava era o passo seguinte: **como descobrir qual
nó**. Sem isso, o aviso só antecipa a frustração — não a resolve.

Motivador concreto (RS-822): um helper de comentário recebeu `"strong"` como
**string** onde esperava lista. O loop iterou caractere a caractere e gerou
`{"type":"s"}`, `{"type":"t"}`, `{"type":"r"}`… O JSON ficou sintaticamente
válido, `json.tool` passou, e o Jira devolveu **400 sem nomear nada**. Montar por
script não impediu o erro — o script também erra.

### Added

- **`references/templates.md` ganha §"Antes de postar: valide o ADF"**: a lista
  dos 6 `marks` aceitos (`strong`, `em`, `code`, `link`, `strike`, `underline`)
  e uma varredura de ~10 linhas que percorre o documento e falha nomeando as
  marks inválidas. Troca um 400 cego por um diagnóstico exato.
- **Receita de conserto sem remontar**: quando a varredura acusa marks quebradas
  em caracteres soltos, juntar os caracteres de cada nó e substituir pela palavra
  resultante recupera o payload já montado.
- **Ponteiro para o suspeito seguinte**: se a varredura de marks vier limpa e o
  400 persistir, o problema costuma ser um `type` de nó fora da tabela (`bold` em
  vez de `strong`, `italic` em vez de `em`).

### Changed

- **`SKILL.md` deixa de tratar "monte por script" como suficiente.** O texto
  agora diz explicitamente que o script também erra e aponta para a varredura
  como passo obrigatório antes do POST.

## [1.2.0] — 2026-08-24

Rodada motivada por uma constatação desconfortável: das quatro armadilhas
medidas em 2026-08-07 (SQ-74) e registradas como pendência, **duas voltaram a
cobrar pedágio no SQ-107**, 17 dias depois, do mesmo jeito. Uma lição que não
entra na skill é uma lição que se paga de novo.

### Added

- **fixVersion ganha seção própria em `references/workflow.md`.** O campo não
  existia em lugar nenhum da skill, embora seja parte do que se decide ao abrir
  um cartão. É o campo com os piores sensores locais: `acli` não escreve **nem
  lê** (devolve `[]` sobre valor gravado), o MCP não confirma, e `updated` não
  bumpa. Tudo por REST, com tabela de operação → endpoint.
- **A flag `released` do Jira não é sensor de release.** No SQ-107 a `0.7.1`
  aparecia `unreleased` estando em produção desde 20/ago. Antes de repassar esse
  metadado ao dev, confira o artefato (`git branch -r --contains <sha>` e a
  versão no `package.json` de `origin/main`) e corrija o Jira.
- **`open`/`abrir` como alias de `start`** no roteamento. O comando não existia e
  é o que o dev digita — duas vezes na mesma sessão.
- **Criação por `POST /rest/api/3/issue` numa chamada** quando há fixVersion:
  `fixVersions` + sprint + pontos + `description` em ADF juntos. O
  `create --from-json` do `acli` não escreve `fixVersions`, então o caminho dele
  sempre exigiria um segundo passo que só existe via REST.

### Fixed

- **`--assignee` com e-mail falha; o certo é `@me`.** O `SKILL.md` mandava
  `--assignee "{username}"` e o `workflow.md` exemplificava com e-mail. O
  `userEmail` da sessão não é necessariamente a conta Jira, e o erro
  (`✗ Failure: … unexpected error, trace id: …`) não nomeia campo nem causa.
  Medido em 2026-08-07 e de novo em 2026-08-24. Para outra pessoa: accountId via
  REST.
- **`sprint list-workitems` sai do papel de sensor — entra JQL.** O step 6 vendia
  aquele comando como "confirmação independente"; ele pagina em ~30 itens e o
  cartão recém-criado cai fora da primeira página. Seguir a skill produzia
  exatamente o alarme falso que o passo existe para evitar. Medido no SQ-74 e no
  SQ-107 — nas duas vezes o cartão **estava** na sprint.
- **`acli` imprime `✗ Failure` e sai 0** — agora dito no topo dos gotchas.
  Cadeia `&&` e `$?` são decorativas; o sensor é a releitura do campo.
- **A criação de branch passa a medir a base em vez de confiar no `pull`.**
  `git pull … | tail` dentro de um `&&` devolve o exit do `tail`, então um pull
  que falhou deixa a cadeia seguir e a branch nasce de base não verificada, sem
  aviso. Poka-yoke: `git rev-list --left-right --count HEAD...origin/$BASE_BRANCH`
  deve dar `0	0`.
- **Releitura pós-criação passa a ser por campo**, porque o sensor é literalmente
  diferente para cada um: `acli view --json` serve para sprint/score e mente
  sobre fixVersion, que só o REST GET lê.

### Note

Todas as correções desta versão têm a mesma assinatura: **o passo de verificação
da própria skill é que falhava**, e falhava para o lado que parece seguro (exit
0, cadeia que continua, listagem que "não achou", campo que volta `[]`). Sensor
cego é pior que sensor ausente — ele produz confiança.

## [1.1.1] — 2026-08-07

### Fixed

- **A skill afirmava a branch base errada para o `sales_quote`/SQ.** O `SKILL.md`
  dizia, em dois pontos (exemplo do `.jira-project` e nota da tabela de
  variáveis), que o projeto usa `main`. Usa **`develop`** —
  `origin/HEAD → origin/develop` desde a feature 017, e o fluxo é
  `develop → staging → main`. **Consequência real:** branch nova nasceria da base
  errada e a PR iria para o alvo errado, e o sintoma só aparece no merge, quando
  já custa caro. Detectado na sessão de fechamento da SQ-73, quando a base teve
  de ser corrigida à mão.
- **A nota agora manda detectar, não trocar um chute por outro.** O texto antigo
  avisava "não assuma `develop`" e em seguida cravava `main` — o mesmo erro de
  forma. Passa a ser "não assuma **nem** `main` **nem** `develop`", com o comando
  de detecção como caminho único.

### Added

- **`references/workflow.md § Branch base`** — a seção não existia, e é por isso
  que a afirmação errada sobreviveu: não havia onde ela pudesse ser contradita.
  Traz o comando de detecção (`git symbolic-ref --short refs/remotes/origin/HEAD`),
  o fallback para quando o `origin/HEAD` não está resolvido localmente
  (`git remote set-head origin -a`), tabela de estado conhecido por repo, e a
  instrução de registrar a **saída do comando**, não o que parece razoável.
- **Recomendação de declarar `BASE_BRANCH` no `.jira-project`** em vez de
  redetectar a cada uso. É a única das três camadas que não depende de alguém
  ler a documentação.

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
