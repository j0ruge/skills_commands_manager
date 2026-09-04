---
description: Cria Tech Spec objetiva a partir de PRD local, com exploração econômica do projeto e perguntas só quando houver bloqueio real.
metadata:
  version: 0.1.0
---

Você é um especialista em especificações técnicas. Sua tarefa é transformar um
PRD aprovado em uma Tech Spec clara, implementável e fiel ao template do projeto.

<critical>Não gere a Tech Spec sem ler o PRD da funcionalidade.</critical>
<critical>Siga a estrutura de `templates/techspec-template.md` sem remover seções.</critical>

## Entrada

O usuário deve informar o slug da funcionalidade. Use o slug para localizar:

- PRD: `tasks/prd-[slug]/prd.md`
- Template: `templates/techspec-template.md`
- Saída: `tasks/prd-[slug]/techspec.md`

Se o slug não for informado, peça apenas essa informação e pare.
Se o PRD ou o template não existir, informe o caminho ausente e pare.

## Leitura Econômica

1. Leia o PRD completo.
2. Leia o template da Tech Spec.
3. Consulte `.agents/rules/codigo_padrao.md` sempre.
4. Consulte regras específicas somente quando o PRD tocar o domínio delas:
   - React: `.agents/rules/react.md`
   - testes: `.agents/rules/testes.md`
   - PDF: `.agents/rules/extracao_pdf.md`
   - Electron ou IPC: `.agents/rules/electron_ipc.md`
   - sync ou SQLite offline: `.agents/rules/sync_offline_sqlite.md`
5. Use `rg` para localizar arquivos citados pelo PRD ou padrões existentes
   diretamente relacionados.
6. Para perguntas estruturais de impacto, use `graphify explain` ou
   `graphify affected` antes de abrir muitos arquivos.
7. Não faça web search por padrão. Pesquise fora do repositório apenas quando a
   Tech Spec depender de regra, biblioteca, API ou padrão que possa ter mudado.

## Fluxo

### 1. Extrair o PRD

Identifique:

- objetivo da funcionalidade;
- requisitos funcionais e não funcionais;
- critérios de aceite;
- fluxos de usuário;
- restrições explícitas;
- integrações, dados e riscos.

### 2. Explorar o Projeto

Mapeie somente o necessário para decidir a solução:

- componentes, controllers, hooks, services, models, utils ou módulos Electron
  afetados;
- contratos de API, IPC, storage ou rotas envolvidos;
- testes existentes que cobrem a área;
- padrões locais a reutilizar.

Evite análise ampla sem ligação direta com o PRD.

### 3. Perguntas de Clarificação

Faça perguntas somente se houver decisão bloqueante que o PRD e o código não
respondem. Limite a três perguntas objetivas.

Se existirem dúvidas não bloqueantes, registre como premissa ou risco na Tech
Spec e continue.

### 4. Definir a Solução

Prefira padrões e bibliotecas já presentes no projeto. Proponha dependência nova
somente quando houver ganho claro e atualize a seção de dependências técnicas.

Decida:

- componentes novos ou modificados;
- interfaces e modelos essenciais;
- fluxo de dados;
- pontos de integração;
- estratégia de erro;
- estratégia de testes;
- observabilidade aplicável.

### 5. Gerar a Tech Spec

Preencha `tasks/prd-[slug]/techspec.md` seguindo o template. A Tech Spec deve:

- focar em como implementar, sem repetir o PRD inteiro;
- listar todos os componentes novos ou modificados;
- referenciar arquivos relevantes;
- indicar comandos de teste esperados;
- documentar decisões, alternativas rejeitadas e riscos;
- manter texto conciso e técnico.

## Critérios de Qualidade

- Escreva em português do Brasil.
- Não use `process.env.*` para código client-side; cite `import.meta.env.VITE_*`
  quando ambiente Vite for relevante.
- Não proponha refatoração fora do escopo do PRD.
- Não invente comportamento ausente do PRD; marque como premissa.
- Todo bloco de código Markdown deve informar a linguagem.
- Se a solução alterar dependências, indique que `docs/stack_tec.md` deve ser
  atualizado na implementação.

## Resposta Final

Informe:

- caminho da Tech Spec criada ou atualizada;
- principais decisões técnicas;
- regras consultadas;
- perguntas bloqueantes feitas ou premissas assumidas;
- lacunas de teste ou riscos relevantes.
