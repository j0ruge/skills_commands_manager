# Changelog — ticket

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
