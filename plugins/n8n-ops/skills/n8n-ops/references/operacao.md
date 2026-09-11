# Operar workflows: import, export, ativação, API

Índice: [`../SKILL.md`](../SKILL.md).

## As mensagens que mentem

Todas medidas. A mensagem do n8n quase nunca aponta para a causa.

### `null value in column "id" ... violates not-null constraint`

O JSON não tem `id` e esta instância não gera um. **Fixe um id estável no arquivo** — não é só para
o import passar: é o que faz o reimport **atualizar** em vez de criar um segundo workflow, invisível
e desatualizado, que continua rodando em paralelo com o primeiro.

### `The credential with ID "undefined" is already owned by the user...`

Não é sobre credencial. Aparece com `--projectId` apontando para um projeto **pessoal**
(`project.type = personal`): o n8n tenta "re-own" as credenciais referenciadas e aborta. Use
`--userId` do dono; o workflow cai no projeto pessoal dele, que é o mesmo lugar.

### `The credential with ID "<id>" is already owned by the user...`

Também não é sobre credencial — repare que o id citado é o do **workflow**. Aparece ao
**reimportar** algo que já existe passando qualquer flag de destino. **A flag de destino só vale na
criação.** Consulte o banco antes e só passe destino quando o id ainda não existir.

### O import falha inteiro com `--activeState=fromJson`

Essa flag só funciona em modo `queue`/`multi-main`. Em modo regular o import **falha por inteiro**.
Em modo regular o workflow nasce inativo e ativar é ato humano na UI — o que é desejável: workflow
novo não deve começar a mandar e-mail antes de alguém ver o ensaio passar.

## 🔴 O verde mentiroso do CLI

**`n8n import:workflow` sai com código 0 mesmo quando falha.** Três gerações de defeito na mesma
família, todas vividas:

1. **Declarar sucesso sem olhar.** O pior dos mundos: import falho anunciado como feito.
2. **Olhar só o texto, com veredito negativo.** "Não achei `error occurred|failed` ⇒ ✅" deixa passar
   tudo que quebra **antes** de o n8n rodar: `ssh: connect ... Connection refused`,
   `Error: No such container: n8n`, `Permission denied`.
3. **O que funciona:** propagar o **código de saída do comando remoto** (`exit $RC` no fim da cadeia
   remota) como sinal primário, e usar o texto como segundo.

⚠️ O sinal ideal é a marca **positiva** de sucesso do CLI. Ela costuma não estar documentada em
lugar nenhum — então anote a saída literal no primeiro import de verdade e troque a checagem por
ela. É estritamente melhor que qualquer lista de falhas, que por construção é incompleta.

## 🔴 Reimportar desliga o workflow — e isso precisa de sensor

Não é pelo `active` do arquivo: um JSON com `"active": true` é desligado do mesmo jeito. É o modo
regular. Reative depois de todo import, ou o disparo devolve **404**.

**Runbook não é sensor.** Quem lê o `✅ Importado` não vai conferir o banco por conta própria. Faça
o importador ler o `active` **antes e depois** e gritar quando ele próprio causou o desligamento,
com o link da UI. Três detalhes que decidem se esse poka-yoke serve:

- **A falha da leitura não pode virar silêncio.** `2>/dev/null || true` deixa a variável vazia e o
  aviso nunca dispara — sensor que cega calado, que é o defeito que ele existe para combater. Quando
  não der para ler, diga que ficou cego.
- **Avise só quando o import CAUSOU a mudança** (estava ligado, ficou desligado). Avisar nos outros
  casos vira ruído, e aviso que vira ruído não é lido.
- **O veredito verde vai por último.** Se o `✅` sai na stdout antes dos avisos da stderr, a última
  linha no terminal é o verde e o alerta fica enterrado acima.

## Proteja os workflows que são espelho de leitura

Workflow mantido na UI por gente e espelhado num arquivo do repositório **não deve ser importado por
cima**: um diff desatualizado vira rollback silencioso da configuração viva. Recuse esses ids no
próprio importador, com mensagem dizendo que a direção correta é exportar.

## API pública `/api/v1`

Habilitada quando responde `401` sem chave (e não `404`). A chave é criada em **Settings → n8n API**
e vale como o usuário que a criou — alcança **todos** os workflows da instância.

```bash
GET    /api/v1/workflows/<id>                # estado, inclusive `active`
POST   /api/v1/workflows/<id>/activate
POST   /api/v1/workflows/<id>/deactivate
DELETE /api/v1/workflows/<id>                # remover um gêmeo de ensaio
GET    /api/v1/executions?workflowId=<id>
```

⚠️ A API é também a forma certa de **ler um workflow inteiro**: `psql -At -F'|'` quebra em coluna
JSON multilinha (`nodes` tem quebras de linha e `|` dentro), e uma linha do banco vira várias na
saída — `JSON.parse` morre com `Unterminated string`.

⚠️ `activate` pode não surtir efeito nenhum, nem mexer no `updatedAt`, quando memória e banco estão
dessincronizados. **Se o `updatedAt` não se move, vá à UI** — é ela que reconcilia.

⚠️ A API de data tables pode existir sem o caminho de linhas: limpar linha de ensaio costuma
continuar sendo ato de UI.

## Ensaiar sem o CLI

`n8n execute` esbarra em três paredes, e a terceira não tem contorno:

| Sintoma | Causa | Saída |
|---|---|---|
| `Task Broker's port 5679 is already in use` | o servidor já ocupa a porta | variável de porta alternativa no `exec` |
| `Missing node to start execution` | o CLI não parte de `scheduleTrigger` | trocar o gatilho |
| `Attempted to use <X> node but the module is disabled` | **o processo do CLI não carrega o módulo; o servidor carrega** | **sem contorno** |

A receita que funciona, porque roda dentro do processo do servidor:

```bash
# 1. gerar gêmeo de ensaio: gatilho vira webhook de caminho fixo, fontes viram fixture
# 2. importar o gêmeo (id próprio, inativo)
# 3. ativar por API e disparar por curl
curl -s -X POST -H "X-N8N-API-KEY: $K" https://<host>/api/v1/workflows/<id-ensaio>/activate
curl -s -X POST -d '{}' -H 'Content-Type: application/json' https://<host>/webhook/<path-fixo>
# 4. conferir: 1 alerta no fixture que deve disparar, 0 no que não deve
# 5. apagar o gêmeo
curl -s -X DELETE -H "X-N8N-API-KEY: $K" https://<host>/api/v1/workflows/<id-ensaio>
```

⚠️ **Reimportar desativa** — reative antes de disparar, ou o `curl` devolve 404.
