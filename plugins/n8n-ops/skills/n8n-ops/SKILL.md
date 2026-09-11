---
name: n8n-ops
metadata:
  version: 1.0.0
description: "Operar n8n como infraestrutura, não desenhar fluxos: diagnosticar automação que não avisou (gravou? notificou? entregou?), importar workflow sem criar duplicata invisível, ensaiar antes de ativar, e escrever alarme que não mente. A coluna `active` NÃO prova que um workflow roda — o sensor é a tabela de execuções. Triggers — n8n, workflow não disparou, webhook não chegou, automação silenciosa, import:workflow, execution_entity, watchdog de automação."
---

# n8n como infraestrutura

Esta skill é sobre **operar e diagnosticar** um n8n que já existe e roda coisa séria — não sobre
desenhar fluxos na tela. Ela existe porque quase todo item aqui custou uma tentativa falha: a
mensagem de erro do n8n raramente aponta para a causa, e vários dos seus modos de falha são
**silêncio**, que se parece com funcionamento.

Antes de operar uma instância concreta, leia o contrato de configuração:
[`references/instancia.md`](references/instancia.md) — quais variáveis a skill espera, o que medir
sobre a instância (modo regular × `queue`, projeto pessoal × de equipe, gravação de execuções) e por
que os valores concretos ficam na regra do repositório privado, nunca aqui. O corpo abaixo vale para
qualquer n8n.

## A regra que evita o erro mais caro

> 🔴 **`workflow_entity.active` NÃO prova que um workflow está executando.**

O n8n mantém o agendamento **em memória**. A coluna é o estado que vale no próximo restart, não o
que está acontecendo agora. Medido: depois de um reimport a coluna ficou `f` e o workflow **seguiu
executando de 10 em 10 minutos, sem falhar uma vez, por onze horas**.

Ler a coluna erra nos dois sentidos — alarme falso quando está `f` e rodando; e, muito pior, a
leitura inversa ("está `t`, logo está rodando") esconde um agendamento que morreu.

**O sensor confiável é a tabela de execuções, sempre:**

```sql
select max("startedAt") from execution_entity where "workflowId" = '<id>';
```

O mesmo vale para a API: um `POST /workflows/<id>/activate` pode não surtir efeito nenhum — nem
mexer no `updatedAt` — quando memória e banco estão dessincronizados. **Se a API não move o
`updatedAt`, não insista: vá à UI**, que é o que reconcilia os dois.

## A pré-condição que quase todo mundo esquece

Muitas instâncias rodam com `EXECUTIONS_DATA_SAVE_ON_SUCCESS=none`. Com isso, **sucesso não deixa
rastro**: não há o que diagnosticar e não há o que vigiar. Antes de investigar qualquer silêncio,
confirme que o workflow tem override por workflow:

```sql
select name, settings from workflow_entity where id in ('<id>', '<id>');
-- procure "saveDataSuccessExecution": "all"
```

Sem isso, toda execução saudável é invisível, e um vigia que compare "houve gatilho mas não houve
sucesso" produzirá **ausência falsa em cima de ausência falsa**. Execução **manual** costuma ser
gravada mesmo assim (`EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS`, default `true`) — é por isso que
ensaio manual aparece na lista e cron não aparece.

## Diagnosticar silêncio: "gravou? notificou? entregou?"

Quando uma automação não avisou alguém, siga **nesta ordem**. Cada passo elimina uma hipótese;
pular um faz acusar a etapa errada — e a etapa errada costuma ser a mais visível, não a culpada.

1. **O dado foi gravado?** Confirme no banco do produto que o evento existe *e* que ele satisfaz a
   pré-condição do fluxo. Um fluxo que só dispara com item não-vazio **não deveria** ter rodado se o
   registro veio vazio: nesse caso o "erro" no console é esperado, e o diagnóstico acaba aqui.
2. **O gatilho executou?** Consulte `execution_entity` do workflow de entrada. Nenhuma execução *e*
   o dado gravado significa uma de duas coisas: o evento nasceu num canal que não chama o webhook
   (App, backend, job), ou a gravação de execuções está desligada.
3. **O fluxo seguinte executou?** Mesma consulta no workflow dependente, correlacionando por
   identidade de negócio e janela de tempo — o payload de um raramente carrega a chave do outro.
4. **A entrega aconteceu?** Leia o último nó executado da execução (ver `flatted`, abaixo). Parou
   antes do nó de e-mail/Slack ⇒ não entregou, e a causa está no nó anterior.
5. **O cliente chama o endpoint certo?** Se tudo acima está verde, o POST saiu para um lugar que
   ninguém escuta. Compare o endpoint **servido ao usuário** com os paths dos workflows ativos.

Detalhe de cada passo, com as consultas prontas:
[`references/diagnostico.md`](references/diagnostico.md).

### 🔴 `/webhook/` × `/webhook-test/` não são sinônimos

O `-test` só responde **enquanto alguém está com a aba "Test workflow" aberta** na UI. Em produção
o POST cai no vazio. Como quase todo disparo de webhook é *fire-and-forget* (a falha vira um
`console.warn` que ninguém lê), um endpoint `-test` publicado em produção pode passar **meses**
sem ninguém notar. Se o cliente é um bundle compilado, a URL é build-time: trate como configuração
de build, não de runtime.

### `execution_data.data` vem achatado

O campo é JSON no formato **`flatted`**: toda string dentro de um objeto é um **índice** para outra
entrada do array, não o valor. `JSON.parse` funciona e devolve lixo aparentemente válido. Desachate
antes de ler `resultData.lastNodeExecuted` ou `resultData.error.message` — receita em
[`references/diagnostico.md`](references/diagnostico.md).

## Importar e exportar workflows

O CLI do n8n tem armadilhas que mentem na mensagem. As quatro que mais custam:

| Sintoma | Causa real |
|---|---|
| `null value in column "id" ... violates not-null constraint` | o JSON não tem `id`. Fixe um id estável no arquivo — é também o que faz o reimport **atualizar** em vez de criar um segundo workflow invisível |
| `The credential with ID "undefined" is already owned by...` | `--projectId` apontando para projeto **pessoal**. Use `--userId` do dono |
| `The credential with ID "<id do workflow>" is already owned by...` | flag de destino num **reimport**. O destino só vale na criação; o id citado é do workflow, não de credencial |
| import falha inteiro com `--activeState=fromJson` | essa flag exige modo `queue`/`multi-main`. Em modo regular, o workflow nasce **inativo** e ativar é ato humano |

🔴 **O CLI sai com código 0 mesmo quando o import falha.** Não declare sucesso pela ausência de
erro. E não caia na armadilha seguinte: um veredito *negativo* ("não achei `error|failed` no texto")
deixa passar tudo que quebra **antes** de o n8n rodar — `Connection refused`, `No such container`,
`Permission denied`. Propague o **código de saída do comando remoto** como sinal primário, e use o
texto só como segundo. A marca **positiva** de sucesso é estritamente melhor que qualquer lista de
falhas: anote a saída literal no primeiro import de verdade e passe a casar com ela.

⚠️ **Reimportar desliga o workflow** — e não é pelo `active` do arquivo (um arquivo com
`"active": true` é desligado do mesmo jeito). É o modo regular. Reative depois de todo import, ou o
próximo disparo devolve **404**. Melhor que anotar isso num runbook: faça o importador **ler o
`active` antes e depois** e gritar quando ele próprio causou o desligamento. Runbook não é sensor —
quem lê o `✅` não vai conferir o banco.

Mais casos e os comandos: [`references/operacao.md`](references/operacao.md).

## Ensaiar antes de confiar

**Sonda que nunca ficou vermelha não é sonda.** Antes de ativar qualquer vigia ou alarme, prove que
ele dispara com um fixture que *deveria* disparar, e que fica calado com um que não deveria.

🔴 **`n8n execute` do CLI não serve para isso.** Três paredes, e a terceira não tem contorno: a porta
do task broker já está ocupada pelo servidor; o CLI não parte de um nó de schedule; e — o
definitivo — **o processo do CLI não carrega módulos que o servidor carrega** (Data Table é o caso
clássico), então o ensaio morre num nó que funciona perfeitamente em produção.

A saída é fazer o ensaio rodar **dentro do processo do servidor**: gere um gêmeo inativo do
workflow, troque o gatilho de schedule por um **webhook de caminho fixo**, troque as fontes de dado
por fixtures, importe, ative e dispare por `curl`. Depois apague o gêmeo.

Duas armadilhas que produzem **sucesso aparente** no ensaio:

- **`$json` num nó de gravação é a saída do nó anterior**, não o dado que você quer. Se o nó de
  registro vem depois do de envio, `{{ $json.chave }}` é `undefined` e a linha nasce com tudo nulo —
  o dedup nunca casa e o alarme reenvia para sempre. Alcance o nó de origem explicitamente:
  `{{ $('NomeDoNó').item.json.chave }}`.
- **Fixture com data fixa envelhece.** Um instante de dois anos atrás cai fora da janela de 24 h e o
  ensaio devolve zero alerta — parecendo que as regras quebraram. Use marcadores relativos
  (`__AGORA_MENOS_15MIN__`) resolvidos na hora de gerar o ensaio.

## Escrever um alarme que não mente

Se você está construindo vigilância **sobre** o n8n, três princípios decidem se ela vai servir:

**1. A regra não mora dentro da ferramenta vigiada.** Um nó Code com a lógica do alarme não é
versionado, ninguém revisa, e morre calado. Ponha as regras num módulo do repositório, com teste por
regra, e **injete** no nó por script — com um modo `--check` no CI que quebra o build se o nó
divergir do módulo. Sensor que só existe dentro da coisa vigiada não é sensor.

**2. A chave de dedup precisa de discriminante, e ele difere por família de regra.** Dedup grosseiro
é pior que nenhum: o segundo problema real da janela colide com o primeiro e **some para sempre** —
e na segunda falha já ninguém está olhando.

| Família | Discriminante | Por quê |
|---|---|---|
| Evento (ausência, presa, erro) | id da execução | dois eventos são dois problemas |
| Estado de conteúdo (endpoint divergente) | marca do conteúdo da divergência | duas divergências diferentes no mesmo dia não podem herdar a chave uma da outra |
| Estado binário (gravação desligada) | nenhum | "uma vez por dia por workflow" é a semântica certa; repetir é ruído |

**3. Uma regra pode invalidar outra — e isso precisa ser código, não comentário.** Se a gravação de
sucesso está desligada, os sucessos não existem no banco e **toda** execução saudável vira uma
ausência falsa. A regra que detecta a cegueira tem de suprimir a que depende do dado cego.

Mais: [`references/vigia.md`](references/vigia.md).

## Superfície de acesso: dê permissão ao script, nunca ao `ssh`

Liberar `ssh <host-do-n8n>` a um agente libera **qualquer comando** no host que roda a automação da
empresa inteira, mais os backups. O caminho seguro é um script estreito que só lê — e três lições
duras sobre como fazê-lo direito, todas medidas como bypass real:

- 🔴 **SQL nunca cruza `ssh host "<string>"`.** O `ssh` concatena os argumentos e entrega ao shell
  remoto, que reinterpreta: um `$(...)` dentro da consulta vira **comando no host**, antes de o
  `psql` existir. Mande o SQL por **stdin** (`psql -f -`) e deixe o comando remoto fixo. Regra geral
  que vale além do n8n: dado do usuário não vira sintaxe de shell do outro lado.
- ⚠️ **`docker exec` sem `-i` não liga o stdin ao container** — o `psql -f -` leria vazio e
  devolveria rc 0 com zero linhas, que é o pior dos silêncios.
- ⚠️ **Uma guarda de "só leitura" por texto é frágil.** `with x as(delete ... returning id) select *`,
  `copy(select 1)to program'id'` e `select ... into` são escrita, e passam por bordas de palavra
  ingênuas. Exija **uma única sentença**, case sobre a string inteira (não por linha), recuse
  metacomando do `psql` (`\!`, `\copy`) e funções que alcançam o sistema de arquivos. E saiba que
  isso continua sendo guarda de texto, não parser: a defesa real é um papel Postgres com `SELECT` e
  nada mais.

🔴 **Crie credencial pela UI, nunca por `import:credentials`.** No CLI a senha viaja em claro e fica
num arquivo temporário no host; a UI cifra com a chave da instância e testa a conexão na hora. O que
o repositório precisa guardar é só o **id**.

## MCP do n8n × scripts do repositório

Um MCP de n8n embrulha a API pública em ferramentas convenientes. Antes de usá-lo, saiba o que ele
é: **um servidor de terceiro segurando uma chave que alcança todos os workflows da instância** — não
só os do seu projeto. A chave deve vir do ambiente (`N8N_API_KEY=${N8N_API_KEY}`), nunca literal num
arquivo de configuração que não é gitignored e viaja entre máquinas. Um `401` quase sempre é a
variável ausente no shell que lançou o agente, não a instalação.

Como escolher: **para inspecionar, prefira o script somente-leitura** do repositório — ele recusa
escrita por construção. O MCP ganha no que o script não cobre: listar nós disponíveis, validar
workflow, explorar documentação de nós.

⚠️ Uma consulta SQL crua também tem limite: `psql -At -F'|'` quebra em coluna JSON multilinha (a
coluna `nodes` tem quebras de linha e `|` dentro), e uma linha do banco vira várias na saída. Para
ler um workflow inteiro, use a API: `GET /api/v1/workflows/<id>`.

## Ruído conhecido que se ignora

Avisos de permissão do arquivo de settings, deprecação de `binaryData` e `WARNING` de versão de
collation do Postgres aparecem em **toda** chamada. Filtre-os na saída dos seus scripts e não os
persiga — mas **não filtre a stderr inteira**, que é onde mora o erro de verdade.
