# Construir vigilância sobre o n8n

Índice: [`../SKILL.md`](../SKILL.md). Este arquivo é sobre **desenhar um alarme que não mente** —
seja ele um workflow n8n que vigia outros workflows, seja um job externo.

## Onde o vigia deve morar

**O n8n não vigia a si mesmo.** Se a instância cair, um vigia hospedado nela cai junto e o silêncio
é total — e silêncio é exatamente o que ele existe para quebrar. Um vigia interno serve para
detectar workflow parado, execução em erro e endpoint divergente; a saúde da própria instância
precisa de um segundo vigia **de fora** (um cron no CI, um monitor externo) que afirme pelo menos o
`/healthz` e o endpoint servido ao usuário.

O mesmo raciocínio vale para o runner que roda o vigia: um vigia hospedado no runner que ele vigia
fica `queued` junto com o deploy preso — cego justamente no dia em que importa.

## 🔴 A regra não mora dentro da ferramenta vigiada

Um nó Code com a lógica do alarme é um beco: não é versionado, ninguém revisa num PR, não tem teste,
e quando alguém o edita pela UI a mudança some no próximo deploy — ou pior, sobrevive e diverge sem
que ninguém saiba.

O arranjo que funciona:

1. As regras vivem num **módulo do repositório**, funções puras, com **teste por regra**.
2. Um script **injeta** o módulo no nó Code na hora de gerar o workflow.
3. Um modo `--check` roda no **CI** e quebra o build se o nó divergir do módulo.

Com isso, "nunca edite o nó pela UI" deixa de ser um pedido e passa a ser algo que o CI reprova.

## 🔴 A chave de dedup precisa de discriminante

Dedup existe porque um alarme que reenvia a cada ciclo vira ruído e é ignorado. Mas **dedup
grosseiro é pior que nenhum**: o segundo problema real da janela colide com o primeiro e some para
sempre — e na segunda falha já ninguém está olhando.

O erro concreto: chave `{regra, workflow, entidade, dia}` num domínio onde **a mesma entidade
produz vários eventos no mesmo dia**. Duas falhas reais, uma chave, um alerta.

O discriminante difere por família:

| Família | Regras típicas | Discriminante | Por quê |
|---|---|---|---|
| **Evento** | ausência, execução presa, erro | **id da execução** | dois eventos são dois problemas |
| **Estado de conteúdo** | endpoint divergente, configuração fora do esperado | **marca do conteúdo** (hash das divergências) | duas divergências diferentes no mesmo dia não podem herdar a chave uma da outra |
| **Estado binário** | gravação desligada, workflow inativo | **nenhum** | "uma vez por dia por workflow" é a semântica certa; repetir é ruído |

## 🔴 Uma regra pode invalidar outra — e isso é código

Se a gravação de sucesso está desligada, os sucessos não existem no banco. Uma regra do tipo "houve
gatilho mas não houve sucesso correspondente" passa a disparar em **toda** execução saudável:
ausência falsa em cima de ausência falsa, até o alarme virar ruído e ser desligado.

A regra que detecta a cegueira (`gravação desligada`) tem de **suprimir** as que dependem do dado
cego, para aquele workflow. Um comentário prometendo a invalidação não invalida nada — isso precisa
estar no código, com teste.

## Ensaie até ficar vermelho

**Sonda que nunca ficou vermelha não é sonda.** Dois fixtures, no mínimo:

- um que **deve** disparar → exatamente **1** alerta, com a identidade certa no corpo;
- um saudável → **0** alertas.

E um terceiro ensaio que quase ninguém faz: **dispare duas vezes com o mesmo fixture**. A segunda
tem de parar no nó de regras, sem e-mail e sem linha nova. É a única prova de que o dedup funciona —
e é onde as duas armadilhas abaixo aparecem.

### As duas armadilhas que gravam linha vazia em silêncio

Ambas produzem **sucesso aparente**: o workflow fica verde, o e-mail chega, e o registro nasce
inútil.

1. **`$json` no nó de gravação é a saída do nó anterior.** Se o nó de registro vem depois do de
   envio, `{{ $json.chave }}` é `undefined` e a linha nasce com todos os campos nulos — o dedup nunca
   casa e o alarme reenvia para sempre. Alcance o nó de origem: `{{ $('Regras').item.json.chave }}`.
2. **Fixture com data fixa envelhece.** Um `startedAt` de dois anos atrás cai fora da janela e o
   ensaio devolve zero alerta, parecendo que as regras quebraram. Use marcadores relativos
   (`__AGORA_MENOS_15MIN__`) resolvidos na geração do ensaio.

## A tabela de dedup cresce

Se o vigia lê todas as linhas a cada ciclo e nada poda as antigas, a leitura fica mais cara a cada
dia. Como a chave costuma carregar o dia, tudo com mais de uma janela é lixo.

Escreva a **regra** de expiração junto com as outras (versionada, testada) mesmo que a **poda** ainda
dependa de um ato manual na UI — inventar às cegas a forma de um nó de exclusão quebra o workflow em
produção. Deixar a regra pronta é o que permite automatizar depois sem redescobrir o critério.

## O que um vigia de automação deve cobrir

Uma matriz que se mostrou suficiente, como ponto de partida:

| Regra | Dispara quando |
|---|---|
| `AUSENCIA` | o gatilho executou com sucesso e a pré-condição valia, passou o atraso, e não há sucesso do fluxo dependente na janela |
| `PRESA` | execução em `running`/`waiting`/`new` há mais tempo que o limiar |
| `ERRO` | execução em `error`/`crashed` na janela |
| `ENDPOINT_DIVERGENTE` | o cliente servido aponta para endpoint que nenhum workflow ativo escuta, ou usa `/webhook-test/`, ou o workflow vigiado está inativo |
| `GRAVACAO_DESLIGADA` | workflow vigiado sem `saveDataSuccessExecution: "all"` — o vigia está cego para ele |

Cada alerta deve carregar a **âncora de remediação**: o que fazer, não só o que quebrou. Alarme sem
próximo passo é interrompido e não resolvido.
