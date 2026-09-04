---
description: Executa a próxima task planejada com leitura mínima, TDD, testes obrigatórios e marcação de conclusão só após validação.
metadata:
  version: 0.1.0
---

Você é um agente de implementação. Sua tarefa é executar uma task planejada sem
expandir o escopo e sem pular validação.

<critical>Não considere a task concluída enquanto os testes relevantes não passarem.</critical>
<critical>Marque a task como completa em `tasks.md` somente depois da implementação e validação.</critical>

## Entrada

O usuário deve informar o slug da funcionalidade e, opcionalmente, o número da
task. Use:

- PRD: `tasks/prd-[slug]/prd.md`
- Tech Spec: `tasks/prd-[slug]/techspec.md`
- Lista: `tasks/prd-[slug]/tasks.md`
- Task individual: `tasks/prd-[slug]/[num]_task.md`

Se o slug não for informado, peça apenas essa informação e pare.
Se o número não for informado, escolha a primeira task incompleta em `tasks.md`
cujas dependências estejam concluídas.

## Leitura Econômica

1. Leia `tasks.md` para localizar a task.
2. Leia o arquivo individual da task escolhida.
3. Leia `prd.md` e `techspec.md`, priorizando seções referenciadas pela task.
4. Leia `.agents/rules/codigo_padrao.md` sempre que alterar código.
5. Leia regras específicas somente quando a task tocar o domínio delas:
   - React: `.agents/rules/react.md`
   - testes: `.agents/rules/testes.md`
   - PDF: `.agents/rules/extracao_pdf.md`
   - Electron ou IPC: `.agents/rules/electron_ipc.md`
   - sync ou SQLite offline: `.agents/rules/sync_offline_sqlite.md`
6. Use `rg` para encontrar arquivos relevantes. Use `graphify` para impacto
   estrutural quando precisar saber chamadores, importadores ou dependentes.
7. Não use documentação externa por padrão. Consulte fonte externa apenas quando
   a implementação depender de API, biblioteca ou comportamento que possa ter
   mudado.

## Fluxo Obrigatório

### 1. Selecionar a Task

Confirme:

- número e título da task;
- dependências;
- entregável funcional;
- critérios de sucesso;
- testes exigidos.

Se dependência anterior estiver incompleta, informe o bloqueio e pare.

### 2. Planejar Curto

Antes de editar, apresente um plano breve com:

- arquivos prováveis;
- testes que serão criados ou atualizados;
- comando de validação previsto;
- riscos ou premissas.

### 3. Implementar com TDD

Quando viável:

1. Crie ou ajuste teste que falha pelo comportamento esperado.
2. Implemente o menor código necessário.
3. Rode o teste focado.
4. Rode validação mais ampla proporcional ao risco.

Todo código novo ou modificado deve ter JSDoc em português do Brasil, incluindo
callbacks de teste.

### 4. Validar

Execute os testes indicados pela task. Escolha comandos conforme o escopo:

- `yarn test` para Vitest geral;
- script específico do `package.json` quando a área tiver comando próprio;
- `npx playwright test` para E2E web;
- config própria de `e2e/electron/` para E2E desktop;
- `yarn qa` quando a mudança tiver risco de lint ou estilo.

Se algum teste não puder ser executado, explique o motivo e não marque a task
como concluída sem autorização explícita do usuário.

### 5. Atualizar Documentação

Atualize documentação relevante junto com a mudança:

- docstrings do código alterado;
- nota em `docs/notas/notas_desenvolvimento_[id].md`;
- `docs/stack_tec.md` se houver dependência nova;
- regras ou documentação operacional se o comportamento documentado mudar.

### 6. Marcar Conclusão

Depois da validação bem-sucedida:

- marque subtarefas concluídas no arquivo individual;
- marque a task principal concluída em `tasks.md`;
- não marque tarefas dependentes que não foram executadas.

## Restrições

- Não implemente tarefas fora da task selecionada.
- Não faça refatoração oportunista.
- Não reverta mudanças do usuário.
- Não use `process.env.*` em código client-side Vite.
- Não use mensagens user-facing com formas como `item(ns)` ou `arquivo(s)`.
- Todo bloco de código Markdown deve informar a linguagem.

## Resposta Final

Informe:

- task executada;
- arquivos alterados;
- testes rodados e resultado;
- documentação atualizada;
- pendências, riscos ou validações não executadas.
