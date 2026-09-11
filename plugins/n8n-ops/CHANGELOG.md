# Changelog — n8n-ops

Formato: [Semantic Versioning](https://semver.org/)

## [1.0.1] — 2026-09-11

Description reescrita para disparar melhor. **Mudança de julgamento, não de medição** — e vale
registrar por quê, porque a tentação de tratar como medida é grande.

O otimizador de description da `skill-creator` rodou 5 iterações sobre 20 consultas e devolveu
`recall=0%` para **todas** as candidatas, incluindo versões muito explícitas em inglês, com scores
byte-idênticos (`18/36`, `12/24`) entre descrições radicalmente diferentes. Isso não é resultado: é
instrumento. O harness detecta disparo observando uma invocação do `Skill` tool em
`claude -p --output-format stream-json`, e **em modo print o modelo não invoca skills** — provado por
controle: uma pergunta de CORS de manual, com a skill `cors` instalada, invocou `Bash` duas vezes e
nunca `Skill`. Recall é estruturalmente zero para qualquer texto naquele ambiente.

Então nada foi aplicado a partir dos números. O que foi aproveitado são os **princípios** que as
candidatas exibiam e a description original não:

- **Diretiva, não descritiva** — "Use quando JÁ existe um n8n rodando e algo nele está errado" em vez
  de "Operar n8n como infraestrutura".
- **Sintomas, não temas** — "diz sucesso sem mudar nada", "desliga o workflow calado", "alarme que
  deduplica sem esconder a segunda falha", em vez de "importar workflow" e "escrever alarme".
- **Exclusão explícita dos vizinhos** — "Não use para Zapier, Make ou Airflow". As três apareceram
  como quase-acertos no conjunto de consultas negativas.
- **Cap duro de 500 chars** do `CLAUDE.md` deste repo, que vence o teto de 700 do fluxo de retrofit:
  a versão diretiva nasceu com 760, foi cortada para 497 enxugando em vez de somar. Ficou de fora a
  declaração de idioma ("vale em PT e EN") — cabe no corpo da skill, não na superfície de disparo.

## [1.0.0] — 2026-09-11

Primeira versão. Nasceu de uma missão real em que uma automação gravou o registro e **a logística
nunca soube** — e a investigação levou três meses de atraso porque quase todo modo de falha do n8n é
**silêncio**, que se parece com funcionamento.

A skill é sobre **operar e diagnosticar** um n8n que já roda coisa séria, não sobre desenhar fluxos
na tela. Cada item custou pelo menos uma tentativa falha; a mensagem de erro do n8n quase nunca
aponta para a causa, e em três casos ela aponta para a coisa errada com convicção.

### O que entra

- **A regra que evita o erro mais caro:** `workflow_entity.active` **não** prova que um workflow está
  executando — o agendamento vive em memória. Medido: coluna `f` e o workflow rodando de 10 em 10
  minutos, sem falhar, por onze horas. O sensor é sempre `execution_entity`.
- **Escada de diagnóstico "gravou? notificou? entregou?"**, em cinco passos que eliminam uma hipótese
  cada, mais o desachatamento do `flatted` de `execution_data.data` (onde toda string dentro de um
  objeto é um índice, e `JSON.parse` devolve lixo aparentemente válido).
- **As quatro mensagens que mentem** no `import:workflow`: `id` ausente, `--projectId` em projeto
  pessoal, flag de destino em reimport (a mensagem fala de "credential" com o id do **workflow**) e
  `--activeState=fromJson` fora de modo `queue`.
- **O verde mentiroso do CLI:** sai com código 0 mesmo falhando, e um veredito *negativo* ("não achei
  `error|failed`") deixa passar tudo que quebra antes de o n8n rodar.
- **Ensaiar antes de confiar:** por que `n8n execute` não serve (o processo do CLI não carrega
  módulos que o servidor carrega — sem contorno), a receita do gêmeo com webhook fixo, e as duas
  armadilhas que gravam linha vazia em silêncio (`$json` é a saída do nó anterior; fixture com data
  fixa envelhece).
- **Desenhar alarme que não mente:** regras fora da ferramenta vigiada com `--check` no CI; chave de
  dedup com discriminante por família (evento × estado de conteúdo × estado binário), porque dedup
  grosseiro faz a segunda falha real sumir para sempre; e invalidação entre regras como código, não
  como comentário.
- **Superfície de acesso só-leitura:** SQL por stdin (nunca `ssh host "<string>"`, onde `$(...)` vira
  comando no host), `docker exec -i`, os bypasses que uma guarda de texto ingênua aceita, e por que
  credencial se cria pela UI.
- **MCP × scripts:** o MCP é um terceiro segurando uma chave que alcança **todos** os workflows da
  instância; a chave vem do ambiente, nunca literal no arquivo de configuração.

### O que deliberadamente NÃO entra

Nenhum hostname, id de workflow, id de projeto, conta de serviço ou chave. **Este repositório é
público**, e esses são dados de infraestrutura de terceiro. `references/instancia.md` descreve o
*contrato* — quais variáveis a skill espera e o que medir sobre a instância — e diz que os valores
ficam na regra do repositório privado que a opera.
