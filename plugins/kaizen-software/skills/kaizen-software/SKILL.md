---
name: kaizen-software
metadata:
  version: 1.3.0
description: "Metodologia Kaizen (melhoria contínua) para planejar, implementar e manter software — e para ensinar Kaizen ao time. Conduz as três fases pelo ciclo PDCA, verifica pelo artefato e não pelo rótulo da ferramenta, prefere poka-yoke a regra escrita, e mapeia os artefatos Kaizen nos que o projeto já tem (ADR, notas, TODO, CHANGELOG). Gatilhos — Kaizen, PDCA, kaizen log/retrospectiva, 5 porquês, poka-yoke, desperdício/dívida técnica, planejar feature, confirmar antes de apagar/limpar."
---

# Kaizen para Software

Kaizen (改善, "mudança para melhor") é a filosofia de melhoria contínua nascida no Sistema Toyota de Produção. Aplicada a software, ela se resume a uma ideia central: **muitas melhorias pequenas, frequentes e verificadas valem mais do que uma grande mudança arriscada**. Nada é grande demais para ser fatiado; nada é pequeno demais para ser melhorado.

Esta skill guia as três fases da vida de um software — planejamento, implementação e manutenção — usando o ciclo PDCA como espinha dorsal.

## Princípios que governam toda decisão

1. **Pequenos incrementos.** Toda mudança deve ser pequena o bastante para ser entendida, revisada e revertida com facilidade. Se um plano tem um passo "grande", fatie-o.
2. **PDCA em tudo.** Plan (planejar) → Do (fazer) → Check (verificar) → Act (padronizar ou corrigir). Nenhuma mudança está completa sem o Check e o Act.
3. **Vá ao Gemba.** Gemba é "o lugar real onde as coisas acontecem". Em software: leia o código de verdade, rode o sistema, olhe os logs e os dados reais antes de opinar. Nunca planeje ou diagnostique por suposição.
4. **Elimine desperdício (Muda).** Antes de adicionar, pergunte o que pode ser removido. Os 7 desperdícios do software estão em `references/desperdicios.md` — consulte ao planejar e ao revisar.
5. **Pare a linha (Jidoka).** Se um teste quebra ou um defeito aparece durante a implementação, conserte antes de continuar. Defeito não anda para frente. E pare **visivelmente** (andon): diga o que quebrou e onde antes de consertar — defeito consertado em silêncio não vira contagem nem padrão, e é assim que o mesmo problema reaparece no vizinho.
6. **Padronize o que funciona (SDCA).** Melhoria sem padronização evapora. Quando algo dá certo, registre no padrão do projeto para que a melhoria vire o novo piso, não um pico isolado — e no degrau mais alto que couber: **poka-yoke** (tipo, validador na borda, lint, hook, gate de CI, script que recusa a entrada errada) > template ou script > convenção escrita (CLAUDE.md, docs). Regra escrita depende de alguém lembrar; o poka-yoke torna o erro impossível ou óbvio, e por isso vem primeiro — a regra escrita fica para quando nenhum degrau acima cabe, dizendo por quê (ver *Poka-yoke* em `references/kaizen-conceitos.md`). **Depois de escrever onde padronizou, abra o arquivo e confirme que a mudança está lá** — "Padronizado em: X" é uma afirmação sobre o mundo fora do log, e escrever o caminho dá a sensação de ter feito. Se ainda não foi feito, escreva "pendente".
7. **Causa raiz, não sintoma.** Use os 5 Porquês: pergunte "por quê" repetidamente até chegar na causa de processo, não na culpa individual. Bug corrigido sem causa raiz identificada é bug que volta.
8. **Registre a melhoria.** Todo ciclo concluído gera uma entrada no `KAIZEN_LOG.md` do projeto. O log é a memória institucional do time — sem ele, o mesmo problema é redescoberto a cada seis meses.
9. **Rejeite o perfeccionismo.** Feito e verificado hoje vale mais que perfeito nunca. Itere.
10. **Todos melhoram.** Sugestões de melhoria vêm de qualquer pessoa (ou agente). Ao notar uma oportunidade fora do escopo da tarefa, registre-a no kaizen log como "oportunidade" em vez de ignorá-la ou de sair do escopo.

## Fase 1 — PLANEJAMENTO (Plan)

Ao planejar uma funcionalidade, mudança ou projeto:

1. **Gemba primeiro.** Explore o código existente, entenda o fluxo atual e os pontos de contato da mudança. Liste os arquivos afetados.
2. **Defina o problema em uma frase** e a **métrica de sucesso** (como saberemos que melhorou? ex.: "cotação gerada em < 5 cliques", "zero erros de arredondamento nos testes").
3. **Cace desperdícios no plano.** Confronte o plano com os 7 desperdícios (`references/desperdicios.md`): há funcionalidade que ninguém pediu? Etapa que gera espera? Complexidade além do requisito? Passo que só funciona se alguém lembrar de fazer X — e que um poka-yoke (validação, gate, hook) dispensaria de lembrar? E os irmãos do muda: o plano empilha tudo no fim (mura)? Sobrecarrega uma pessoa ou um módulo (muri)?
4. **Fatie em incrementos pequenos.** Cada incremento deve: entregar valor verificável por si só, ser testável, e ser reversível. Ordene do mais valioso/menos arriscado para o mais incerto.
5. **Escreva o plano no formato PDCA** usando o template em `references/templates.md` (seção "Plano PDCA"). Cada incremento carrega seu próprio critério de verificação (Check).

Sinal de alerta: um plano em que a primeira entrega verificável só aparece na semana 3 não é um plano Kaizen. Refatie. Se nem refatiando dá — a meta exige trocar a base (framework, banco, arquitetura) —, nomeie o que é: **kaikaku**. Ele não dispensa o método: pede um ADR com a alternativa kaizen medida e rejeitada, e o próprio kaikaku fatiado (strangler, feature flag) para que cada passo continue verificável e reversível.

## Fase 2 — IMPLEMENTAÇÃO (Do + Check)

Ao implementar:

1. **Um incremento por vez.** Implemente, teste e verifique o incremento atual antes de tocar no próximo. Não misture refatoração com funcionalidade nova no mesmo passo — separe em passos distintos.
2. **Teste junto com o código.** Todo incremento novo chega com seu teste. Se o projeto não tem testes, o primeiro incremento de qualquer plano é criar a base mínima de testes para a área afetada.
3. **Jidoka.** Rode os testes após cada incremento. Teste quebrou → pare, avise (o que, onde), conserte, só então avance.
4. **Regra do escoteiro.** Deixe o código que você tocou um pouco melhor do que encontrou (nome mais claro, código morto removido) — mas melhorias grandes fora do escopo viram entrada de "oportunidade" no kaizen log, não desvio da tarefa.
5. **Commits pequenos que explicam o porquê.** Um incremento = um commit (ou poucos). A mensagem diz por que a mudança existe, não só o que mudou.
6. **Check explícito.** Ao final de cada incremento, confronte o resultado com o critério de verificação do plano e diga isso ao usuário: o que era esperado, o que foi observado, passou ou não. Verifique pelo **artefato**, não pelo rótulo que fala dele — "testes verdes", "deploy succeeded" e "healthy" descrevem o processo, e o processo pode ir bem enquanto a coisa que deveria existir não existe (ver *Rótulo ≠ artefato* em `references/kaizen-conceitos.md`). Sonda nova (script, check, healthcheck) só merece confiança depois de ficar vermelha num caso sabotado de propósito e verde num caso bom (ver *Poka-yoke*, ali mesmo).

## Fase 3 — MANUTENÇÃO (Check + Act contínuos)

A manutenção é onde o Kaizen mora de verdade — o sistema em produção é o Gemba permanente. Vá lá sem ticket também: periodicamente, olhe logs, alertas, métricas e as oportunidades do kaizen log — o problema achado antes do usuário custa uma fração.

**Para bugs e defeitos:**

1. Reproduza o defeito antes de corrigir (Gemba — nunca corrija "no escuro").
2. Aplique os **5 Porquês** até a causa raiz de processo. Registre a cadeia no kaizen log. Se um "por quê" tem mais de uma resposta verdadeira, o problema é multicausal: siga cada ramo (processo, ferramenta, ambiente, medição, conhecimento — o diagrama de Ishikawa em forma de lista) e dê contramedida a cada um. Incidente de TI raramente tem uma causa só.
3. Corrija a causa, adicione um teste que teria pegado o defeito, e **padronize** começando pelo poka-yoke: qual mecanismo torna essa classe de erro impossível ou óbvia (tipo, validador na borda, lint, hook, gate de CI)? Nomeie-o na contramedida. Só quando nenhum couber a contramedida vira regra escrita — e o registro diz por quê.
4. **Yokoten — desdobre na horizontal.** A causa raiz encontrada aqui existe onde mais? Outros servidores, outros repositórios, outros clientes, outras skills. Liste-os e aplique (ou registre como oportunidade com dono) antes de fechar o ciclo: correção que fica num lugar só é a que volta pelo vizinho.

**Para saúde contínua do código — 5S do código** (aplique periodicamente ou quando o usuário pedir "limpeza", "organização" ou "reduzir dívida técnica"):

- **Seiri (separar):** remova código morto, dependências não usadas, features abandonadas.
- **Seiton (ordenar):** cada coisa no seu lugar — estrutura de pastas e nomes previsíveis.
- **Seiso (limpar):** lint, formatação, warnings zerados.
- **Seiketsu (padronizar):** as três acima viram convenção escrita e automatizada (linter, CI, template).
- **Shitsuke (disciplina):** automatize a verificação para que o padrão se sustente sem heroísmo.

**Para ações irreversíveis** (apagar branch/arquivo/volume, migration destrutiva, revogar acesso, publicar): a regra "incrementos pequenos e reversíveis" perde o segundo adjetivo justamente onde ele mais valia, então a ordem passa a fazer o trabalho que a reversibilidade fazia.

1. **Gemba por artefato, nunca por rótulo.** O que autoriza apagar não é o rótulo da ferramenta ("PR MERGED", "backup healthy", "já está em produção") — é ter olhado e visto que nada se perde. Prove por conteúdo (hash, diff, existência do arquivo), não por nome nem por assunto de commit: dois artefatos com o mesmo título podem ser coisas diferentes, e o inverso também acontece.
2. **Fatie de modo que o passo reversível venha primeiro.** Apagar a cópia local antes da remota, arquivar antes de excluir, marcar antes de remover. A divergência que você não previu aparece no primeiro passo, quando ainda custa uma verificação em vez de uma perda.
3. **Jidoka vale mais aqui do que em qualquer outro lugar.** Qualquer surpresa no passo reversível interrompe a sequência inteira até ser explicada — mesmo que pareça ruído, e principalmente se a explicação for "deve ser normal".
4. **Anote os identificadores antes de destruir** (SHAs, caminhos, IDs) na saída da sessão. É a rede de segurança mais barata que existe, e só serve se for escrita antes.

**Retrospectivas:** ao fechar um ciclo de trabalho (sprint, entrega, sessão longa), conduza uma retrospectiva curta com o template em `references/templates.md` e converta os aprendizados em entradas do kaizen log com dono e próximo passo.

## Ensinar Kaizen

Quando o usuário quiser **entender** Kaizen (ou preparar treinamento, onboarding ou apresentação para o time/diretoria), leia `references/kaizen-conceitos.md` — história, vocabulário (PDCA, SDCA, gemba, muda/mura/muri, jidoka, 5S, poka-yoke, 5 porquês), os 10 princípios e um roteiro de ensino. Regras ao ensinar:

- Comece pelo problema que o time sente, não pela teoria.
- Traduza cada conceito para um exemplo concreto de software — de preferência do próprio projeto do usuário.
- Termine sempre com um primeiro passo pequeno e praticável (ex.: criar o kaizen log, rodar 5 porquês no último bug).

## Respeite as convenções do projeto

As convenções do projeto (CLAUDE.md, regras em `.claude/rules/`, guias internos) **têm precedência** sobre os padrões genéricos desta skill. Kaizen padroniza — nunca atropela o padrão existente. Em particular:

- **Se o projeto proíbe refatorar sem solicitação explícita** (regra comum), a "regra do escoteiro" muda de forma: em vez de melhorar o código no ato, registre a oportunidade no kaizen log / TODO do projeto e proponha ao usuário. Achado não autoriza mudança.
- **Mapeie os artefatos Kaizen para os artefatos que o projeto já tem** em vez de criar estruturas paralelas: decisões arquiteturais → ADRs (`docs/adr/`); notas de desenvolvimento → o diretório de notas do projeto; oportunidades/dívidas → `TODO.md` ou backlog existente; pegadinhas recorrentes → runbook/napkin do projeto; histórico → `CHANGELOG.md`. O `KAIZEN_LOG.md` complementa esses artefatos como registro de melhoria (antes/depois/padronização) — referencie-os em vez de duplicá-los.
- **Padronizar (Act) significa atualizar o padrão oficial do projeto** (CLAUDE.md, rules, convenções automatizadas), com o consentimento do usuário — não criar um documento novo que ninguém lê.

## Artefatos que esta skill produz

| Situação | Artefato | Template |
|---|---|---|
| Planejamento de feature/mudança | Plano PDCA em Markdown | `references/templates.md` § Plano PDCA |
| Qualquer ciclo concluído | Entrada no `KAIZEN_LOG.md` na raiz do projeto | `references/templates.md` § Kaizen Log |
| Análise de bug recorrente | Registro de 5 Porquês | `references/templates.md` § 5 Porquês |
| Fechamento de ciclo | Retrospectiva | `references/templates.md` § Retrospectiva |
| Ensino/treinamento de Kaizen | Explicação ou material didático | `references/kaizen-conceitos.md` |

Se o projeto ainda não tem `KAIZEN_LOG.md`, crie na primeira oportunidade usando o template. Leia `references/templates.md` antes de gerar qualquer um desses artefatos, e `references/desperdicios.md` sempre que for planejar ou revisar código.

## Tom e postura

Kaizen é sem culpa (no-blame): critique processos, nunca pessoas. Ao apontar problemas no código do usuário, aponte também o caminho pequeno e concreto de melhoria. Prefira "o próximo passo pequeno é X" a "o ideal seria reescrever tudo".
