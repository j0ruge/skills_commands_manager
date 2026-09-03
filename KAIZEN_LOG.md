# Kaizen Log — skills_commands_manager

Registro de melhorias: o que mudou, por quê, e onde o aprendizado foi padronizado
para não se perder. Complementa os `CHANGELOG.md` de cada plugin — eles contam o
**o quê** por versão; aqui fica o **porquê de processo**.

---

## 2026-09-03 — Prompt audit das 16 skills + poka-yoke na kaizen-software + custo do codereview

- **Tipo:** melhoria (16 skills re-lidas para o modelo atual) · correção de causa raiz (cruft
  acumulado por retrofit) · oportunidade (custo do `codereview` — mudança publicada, medição
  pós-mudança pendente)
- **Antes:** skills escritas para Opus 4.x carregavam ênfase em caps, narrativas de incidente com
  data/ticket/PR, nomes/hosts/e-mail do projeto de origem e modelos fixos em prosa; 10 plugins sem
  `metadata.version` no `SKILL.md`; a `kaizen-software` ensinava poka-yoke no verbete mas fechava
  o fluxo com regra escrita; uma invocação de `/codereview` custava **$11–16** (46–65% de cada
  sessão REVIEW do pipeline `sdd_agents`, medido em 16 sessões).
- **Depois:** 14 commits em `origin/main` (tabela abaixo), `validate-versions.py` verde em todos,
  `metadata.version` em todos os SKILL.md tocados; `kaizen-software` 1.3.0 com poka-yoke,
  yokoten, andon e Ishikawa no fluxo (sonda A/B: 14/14 sem regressão; menções a poka-yoke
  0→4 e 1→4 nos cenários em que a antiga fechava com regra escrita); `codereview` 1.19.0 com
  contrato dos agentes em arquivo, prompt de lançamento curto, `model` como poka-yoke, Bucket B
  opt-in e linha *Cost footprint* — medido em duas invocações headless sobre o mesmo diff:
  **$6,62 e $5,92 por revisão** (agentes $0,58–1,61 cada, 3–20 turnos, 8 de 8 leram as references)
  contra $11–16 e ≈45 turnos por agente no baseline; ver item (h).
- **Causa raiz (5 porquês abaixo):** sem eval nem sensor, a única evidência de que uma linha da
  skill "funciona" é o incidente que a gerou — ninguém tem base para removê-la, então só se
  acrescenta.
- **Padronizado em:** `CLAUDE.md` § *Prompt hygiene* (confirmado no arquivo após a edição):
  re-rodar `/claude-api prompt-audit` a cada retrofit e a cada release de modelo; brief
  reutilizável em `~/.claude/handoff/prompt-audit-2026-09-03/prompt-audit/BRIEF-auditoria.md`;
  o quê/porquê vai para o CHANGELOG do plugin, relatórios e diffs ficam fora do repo.
- **Yokoten:** a mesma causa existe fora do marketplace — `sdd_agents/agents/sdd-reviewer.md`
  ("Reproduce before you conclude" + "adversarial" = cauda de ≈ $5,4 e ~50 turnos por sessão
  REVIEW, e é o que empurra os agentes a construir sandboxes) e o `CLAUDE.md` + `.claude/rules`
  do `digital_service_report_api` (≈ 110 KB ≈ 28k tokens injetados em **cada** subagente).
  Registrados como oportunidades (f); não feitos nesta rodada.

### Antes → Depois (um commit por plugin, todos em `origin/main`)

| Commit | Plugin | Versão | O quê |
|---|---|---|---|
| `ac59240` | kaizen-software | 1.2.0 | poka-yoke entra no fluxo (escada de padronização, Fase 1/2/3, template dos 5 Porquês, desperdício #7, description com 8 gatilhos) |
| `7569ff9` | kaizen-software | 1.3.0 | yokoten, andon, Ishikawa, mura/muri, kaikaku, 8º desperdício, gemba sem ticket |
| `186948c` | codereview | 1.18.0 | Fase A inline (sem agente haiku), 28 de 32 linhas em caps voltam ao tom normal, registry de reviewers medido, "opus" fixo sai |
| `efbd550` | dotnet-wpf | 1.7.0 | hooks JSON inválido corrigido, VMs Singleton nas references, resíduos VDA/VDR fora |
| `cf9ab8e` | cicd | 2.26.0 | nomes JRC → placeholders, runner version → latest, lições alinhadas ao paths-ignore |
| `dfe3de7` | zitadel-idp | 0.12.0 | e-mail/IP/hosts fora, "47 quirks" → catálogo, quirks 38–45 viram gatilhos |
| `1647f39` | whisper-preprocess | 1.1.0 | copiar os 2 scripts (merge silencioso), lição 9 no presente, afftdn escopado |
| `fa90577` | pdf-generation | 1.6.1 | linha de downloads npm (falsa) fora, skill inexistente fora, NON-NEGOTIABLE/MUST |
| `4b58bf3` | ddd | 0.4.2 | e-mail do autor e marca → Acme/example.com, "fora de escopo" sem diff de versão |
| `8068660` | ansible-docker-backup-restore | 1.3.2 | nomes de uma instalação → placeholders; arqueologia fora |
| `df3f2c7` | dev-script | 0.5.3 | contagens de incidente fora, tetos numéricos viram qualitativos, 8 gatilhos |
| `174373f` | cors | 1.0.1 | hosts internos e data saem do caso medido; acentos na description |
| `2dc4881` | wsl-windows-onboarding | 0.4.2 | descoberta de caminho sem assumir o layout do autor; "current WSL" robusto |
| `6322d3b` | codereview | 1.19.0 | custo: contrato dos agentes em `references/`, prompt de ~12 linhas, `model: "sonnet"` como poka-yoke, Bucket B opt-in, Cost footprint |

Fora do rollout: `ticket` (árvore com edição em andamento do usuário — auditar depois do commit
dele; sinais já medidos: 8 linhas com datas, 5 com IDs de issue, e-mail pessoal no `SKILL.md`).

### 5 Porquês — por que as skills acumularam cruft
- **Sintoma:** 16 de 16 skills com achados de confiança alta/média no prompt audit — ênfase em
  caps que não previne mais nada, incidentes com data e ticket no corpo, nomes do projeto de
  origem virados regra, modelos fixos em prosa.
1. Por quê? O `retrofit-skill` soma **uma lição por sessão** ao texto que já existe.
2. Por quê somar em vez de reescrever? A lição chega com o nome, o host e o número do incidente
   que a gerou, e vira regra com eles dentro — reescrever custaria re-ler a skill inteira.
3. Por quê ninguém re-lê? Cada retrofit edita só o trecho da lição; não há passo que leia a skill
   **inteira contra o modelo novo**, e a release de modelo não dispara nada no repo.
4. Por quê nada dispara? Não existe eval nem sensor: nada mede se a ênfase ainda previne a falha
   para a qual foi escrita (a sonda do piloto foi a primeira medição desse tipo).
5. **Causa raiz (processo):** sem eval, a única evidência de que uma linha "funciona" é o
   incidente que a gerou; ninguém tem base para removê-la, então só se acrescenta.
- **Contramedida:** o audit periódico é regra escrita (`CLAUDE.md` § *Prompt hygiene*) — poka-yoke
  não coube: o único gate do repo (`validate-versions.py`) vê só a description. O sensor que
  nasceu nesta rodada é a linha *Cost footprint* do `codereview` — custo e turnos por agente
  passam a aparecer no próprio relatório, sem abrir log.
- **Teste que teria pegado:** nenhum existe; o mais perto é o grep de sinais do brief
  (caps, datas, tickets, e-mails, modelos fixos) — roda em segundos sobre `plugins/`.

### Desperdícios evitados (cortes conscientes)
- **Sem `docs/prompt-audit` no repo** — 16 relatórios + 20 diffs ficam em
  `~/.claude/handoff/prompt-audit-2026-09-03/`; o CHANGELOG de cada plugin carrega o quê e o
  porquê. Evitou superprocessamento e um diretório que envelheceria como as skills.
- **Sonda A/B só onde o diff muda comportamento** (kaizen-software). Nas outras, o diff é
  remoção; validação estática (`git apply --check` + validate) bastou.
- **Trade-offs do codereview fora até existir eval:** Haiku nos agentes, `effort: low`, agrupar
  5 arquivos por agente, sweep inteiro opt-in — cada um muda o que se analisa e não há como
  julgar achados perdidos hoje.

### O que aprendemos
- **O sensor pré-registrado do piloto não discriminou** (14/14 asserções passam nas duas versões
  da kaizen-software): o enunciado do cenário já apontava a falha da regra escrita, então a
  skill antiga também acertava. A métrica que separou as versões apareceu depois (menções a
  poka-yoke no Act). Cenário-sensor de comportamento novo tem de ser um em que o enunciado
  **não** empurre para a resposta.
- **A description cap é a única superfície com gate**; todo o resto do prompt audit é revisão
  humana — daí a regra escrita, e não um validador.
- **Agentes derrubados pelo 429 já tinham gravado os artefatos** em disco — conferir o disco
  antes de relançar; 4 relançamentos evitados.
- **No codereview o custo não era o tamanho das references** (1 de 66 agentes as leu) nem o
  prompt: era **turnos por agente** (~45 contra ~6 no desenho) — cache-read cresce com o
  quadrado dos turnos. Caminho relativo nas instruções + orquestrador que parafraseia o bloco
  `Agent(...)` = agente explorando livre.
- **O desenho "mesma missão, 2 rodadas" nunca ia medir nada:** `sdd retry` retenta a fase corrente
  (PR), a missão do baseline já estava mesclada em `main` (diff vazio → nenhum agente) e o seu revisor
  deixou de invocar o skill a partir da r3. A sessão forçada (`sdd run --phase REVIEW`, que ignora o
  teto de rodadas por desenho) fez checkout da branch da missão na árvore do usuário e commitou duas
  notas de intervenção — desfeitas por ele em um minuto. O que mediu foi `claude -p
  "/codereview:codereview"` num worktree destacado e, quando essa branch também foi mesclada, num
  clone descartável com `main` fixado no merge-base antigo: zero contato com o checkout de quem
  trabalha no repo em paralelo.
- **Job longo em Bash de fundo com timeout morre no prazo, com o grupo de processos inteiro**
  ($4,70 de sessão perdida): `setsid nohup … &` + Monitor. E um Monitor cujo comando contém o literal
  que ele procura com `pgrep -f` casa consigo mesmo e nunca sai.
- **Bucket B do sweep sem foco no prompt de lançamento é regra sem sensor**: o agente não tinha
  como saber o foco; o prompt agora leva `Focus area` e `Sweep`.

### Oportunidades registradas (dono: j0ruge — único mantenedor)
- (a) `scripts/validate-versions.py` não lê `metadata.version` do `SKILL.md` e o check 6 procura
  só `skills/<plugin>/SKILL.md` — plugins multi-skill (`codereview`, `dotnet-wpf`) ficam sem
  verificação de description e de versão por skill.
- (b) `README.md` com células-changelog na tabela de plugins (`kaizen-software`, `codereview` —
  a de codereview cresceu de novo nesta rodada); mover para os CHANGELOGs e deixar uma frase.
- (c) `coderabbit-review.md`, `copilot-review.md`, `gemini-review.md` soltos na raiz —
  ignorados por `.gitignore:4`, sobras de runs da `coderabbit_pr` anteriores à Fase 6 (1.17.0);
  apagar depois de confirmar que nenhum PR aberto os usa.
- (d) `create-readme` duplicado em `.claude/skills/` e `.agents/skills/`.
- (e) `ansible-docker-backup-restore`: a prova "há dados" conta blocos `COPY` — Postgres-only;
  `mysqldump` grava `INSERT INTO` (já anotado no CHANGELOG 1.3.2, sem diff).
- (f) Fora do repo: `sdd_agents/agents/sdd-reviewer.md` "Reproduce before you conclude" —
  reproduzir só CRITICAL/HIGH; `CLAUDE.md` + `.claude/rules` do DSR com ≈ 110 KB — cada
  subagente paga ≈ 28k tokens de prefixo.
- (g) `ticket`: auditar com o brief assim que o usuário commitar a edição em andamento.
- (h) Medição da 1.19.0 — **feita** (2026-09-03, ≈ $18 dos ≈ $40 aprovados; $4,70 deles numa sessão do
  runner morta pelo timeout do próprio agente): duas invocações headless sobre o mesmo diff de 18
  arquivos — $6,62 e $5,92 por revisão; agentes $0,58–1,61 (3–20 turnos) contra $2,0 (≈45 turnos);
  sweep $0,62–0,69 (6–8 turnos) contra $3,1–3,5 (63–66); references lidas por 8 de 8 agentes; nenhum
  CRITICAL/HIGH; os dois relatórios convergem no mesmo achado principal. **L1–L5 ficam.** Tabela no
  CHANGELOG do `codereview` (1.19.0); streams e relatórios em
  `~/.claude/handoff/prompt-audit-2026-09-03/prompt-audit/work/codereview-custo/medicao-1.19.0/`.

---

## 2026-08-26 — Descriptions acima do cap: da dívida ao gate

**Problema:** 7 dos 16 plugins tinham `description` acima do cap de 500 chars do
`CLAUDE.md` — o pior com **871**. A `description` é a única superfície de
triggering: é por ela que o Claude decide invocar a skill. Texto longo dilui o
sinal e pode ser **cortado em silêncio** na lista `/skills`, piorando exatamente
o que deveria melhorar.

**Métrica de sucesso:** `scripts/validate-versions.py` com zero erros e zero
warnings.

### Gemba

Não foi suposição. `git log` no `plugin.json` de cada plugin mostrou o padrão:
**`codereview` tem 21 commits** no arquivo, `zitadel-idp` 12, `wsl-windows-onboarding` 6.
Cada retrofit acrescentava sua lição ao texto existente.

### 5 Porquês

1. Por que 7 descriptions passaram do cap? Cada retrofit **somou** a lição nova.
2. Por que somar em vez de reescrever? É mais barato acrescentar uma cláusula do
   que reequilibrar o texto inteiro.
3. Por que nada barrou? O cap era **warning**, não erro — não reprovava o gate.
4. Por que warning? Quando o cap foi criado, as descriptions **já** estavam acima;
   torná-lo erro reprovaria o repositório inteiro de imediato.
5. **Causa raiz (processo, não pessoa):** o padrão nasceu depois da deriva e foi
   aplicado como aviso. Aviso que nunca reprova vira ruído de fundo — todo mundo
   aprende a rolar a tela. **O padrão só se sustenta quando a dívida é zerada
   primeiro e o gate é fechado logo em seguida.**

### Antes → Depois

| Plugin                          | Antes | Depois |
| ------------------------------- | ----- | ------ |
| `wsl-windows-onboarding`        | 871   | 468    |
| `codereview`                    | 686   | 489    |
| `zitadel-idp`                   | 670   | 476    |
| `ansible-docker-backup-restore` | 593   | 473    |
| `dev-script`                    | 578   | 434    |
| `whisper-preprocess`            | 578   | 406    |
| `cicd` (divergente + acima)     | 756   | 473    |

Todos os **16** plugins agora cabem no cap. O corte foi **encurtar, não resumir
mecanicamente**: saiu enumeração de detalhe (mensagens de erro literais, nomes de
ferramentas alternativas, exemplos), que continua no corpo da skill; ficaram o que
a skill faz e os diferenciais que a distinguem das vizinhas.

### Muda eliminado

Aplicar a mesma mudança em 6 plugins × 4 arquivos à mão é **retrabalho**. Virou
`aplica_desc.py`: recebe plugin + arquivo de descrição, aplica nos três arquivos,
faz bump de patch, atualiza o README e **recusa** texto acima do cap. Foi esse
poka-yoke que barrou a primeira tentativa do `wsl-windows-onboarding`, com 511
chars — o erro morreu antes de virar commit.

### Act — padronização

**Padronizado em `scripts/validate-versions.py`:** o cap deixou de ser warning e
virou **erro**. Verificado por injeção — 400 chars a mais num plugin e o gate
reprovou; teste revertido em seguida.

Agora que a dívida está zerada, o custo de manter o padrão é encurtar no ato de
cada retrofit, que é barato. Deixar acumular custou este mutirão.

**Oportunidade registrada (fora do escopo desta rodada):** o `retrofit-skill`
poderia lembrar de rodar o validador antes do commit — nesta sessão o erro do
`cicd` só apareceu porque um retrofit anterior alterou 2 dos 3 arquivos.
