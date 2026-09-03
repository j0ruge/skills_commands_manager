# Kaizen — conceitos, história e vocabulário

Use esta referência quando o usuário pedir para **entender ou ensinar** Kaizen: "o que é Kaizen?", onboarding de um dev novo, material de treinamento para o time, apresentação para a diretoria. Ao ensinar, sempre traduza cada conceito para um exemplo concreto de software — de preferência do próprio projeto do usuário.

## O que é, em uma frase

Kaizen (改善: *kai* = mudança, *zen* = para melhor) é a prática de melhorar continuamente por meio de mudanças pequenas, frequentes, baratas e verificadas, feitas por todos — não só por especialistas ou chefes.

## De onde veio

- **Pós-guerra no Japão (anos 1950):** com poucos recursos, a indústria japonesa não podia investir em grandes reformas; a saída foi melhorar o que existia, um pouco por dia. As ideias de qualidade de **W. Edwards Deming** (ciclo PDCA) encontraram terreno fértil.
- **Sistema Toyota de Produção (TPS):** Taiichi Ohno estruturou a eliminação de desperdícios (muda) e o "pare a linha" (jidoka) — qualquer operário podia parar a produção ao ver um defeito.
- **Masaaki Imai (1986):** o livro *Kaizen: The Key to Japan's Competitive Success* levou o conceito ao Ocidente e fundou o Kaizen Institute.
- **Software:** o Kaizen chegou via **Lean Software Development** (Mary e Tom Poppendieck, 2003) e está no DNA das práticas ágeis: retrospectivas, entrega incremental, refatoração contínua, CI/CD.

## Kaizen vs. outras formas de mudança

| Conceito | O que é | No software |
|---|---|---|
| **Kaizen** | Melhoria contínua, pequena, diária, de baixo risco | Refatoração incremental, teste a mais por ciclo, automatizar um passo manual |
| **Kaikaku** | Mudança radical, pontual, de alto impacto | Reescrever um módulo, trocar de framework — raro e planejado, não o padrão |
| **Kaizen blitz/evento** | Esforço concentrado (dias) de um time num problema específico | Mutirão de dívida técnica, sprint de correção de flaky tests |

A armadilha comum: times que só fazem kaikaku ("vamos reescrever tudo") e nunca kaizen. O Kaizen inverte: o padrão é o passo pequeno; a mudança radical é exceção justificada.

## Vocabulário essencial

- **PDCA** — Plan, Do, Check, Act: planejar a melhoria, executar em pequena escala, verificar contra a métrica, e então padronizar (ou ajustar e repetir). É o motor do Kaizen.
- **SDCA** — Standardize, Do, Check, Act: o irmão do PDCA para **estabilizar** — primeiro padronize o processo atual, depois melhore. Sem padrão, não dá para saber se algo melhorou.
- **Gemba** — "o lugar real". Decidir olhando o código, os logs e o usuário de verdade, não o organograma nem a memória.
- **Rótulo ≠ artefato** — a forma mais afiada do Gemba, e a que produz falso-verde. Toda ferramenta emite rótulos *sobre* a coisa: `healthy`, `PR MERGED`, `build passing`, `deploy succeeded`, ou o campo "Padronizado em" de um kaizen log. O rótulo pode ser verdadeiro sobre o **processo** e falso sobre o **artefato** — um container de backup responde `healthy` porque o processo está vivo, mesmo sem nunca ter gerado um dump; "PR MERGED" descreve o que a PR consumiu, não o que a branch contém agora. Pergunte sempre qual artefato deveria existir e vá olhar: o dump está no disco? o commit está alcançável por algum ref? a linha entrou no arquivo citado? Quando o rótulo e o artefato divergem, é o rótulo que mente — e ele mente com confiança, porque foi desenhado para tranquilizar.
- **Muda** — desperdício (7 tipos — ver `desperdicios.md`). **Mura** — desnivelamento do fluxo. **Muri** — sobrecarga de pessoas ou sistemas.
- **Jidoka** — "automação com toque humano": o processo para sozinho ao detectar defeito. No software: CI que bloqueia merge com teste quebrado; e a disciplina de parar e consertar em vez de acumular.
- **Andon** — o sinal visível de que a linha parou. Jidoka para; andon avisa. No software: o teste vermelho que todo mundo vê, o alerta que chega antes do ticket, o "parei porque X quebrou" dito ao usuário em vez do conserto silencioso — o defeito só vira padrão se alguém souber que ele existiu.
- **5S** — Seiri, Seiton, Seiso, Seiketsu, Shitsuke: separar, ordenar, limpar, padronizar, sustentar. Aplicado ao código: remover o morto, organizar, zerar warnings, transformar em convenção, automatizar a cobrança.
- **5 Porquês** — técnica de causa raiz: perguntar "por quê?" em cadeia até chegar a uma causa de **processo**. A resposta nunca é uma pessoa.
- **Ishikawa (espinha de peixe)** — o diagrama de causa e efeito para quando os 5 Porquês bifurcam: um efeito, várias categorias de causa (processo, ferramenta, ambiente, medição, conhecimento). Incidente de TI costuma ter mais de uma causa contribuindo; siga cada ramo e dê contramedida a cada um.
- **Poka-yoke** — "à prova de erro": desenhar o processo para o erro ser impossível ou óbvio. No software: tipos que não compilam com valor inválido, validação Zod na borda, lint que barra o padrão proibido. **Cuidado com a sonda caseira**: um poka-yoke que alarma quando não devia é pior que nenhum, porque ensina o operador a ignorá-lo — e aí ele também não vê o alarme verdadeiro. A causa quase sempre é a sonda medir um **proxy** em vez da propriedade de interesse (medir a idade de uma branch quando a pergunta era se há trabalho a perder). Antes de confiar numa sonda nova, sabote o sistema de propósito e confira que ela fica vermelha — e rode-a num caso sabidamente bom para ver que fica verde. Sonda conferida num estado só não é sonda.
- **Genchi genbutsu** — "vá e veja por si mesmo": a versão verbo do Gemba.
- **Yokoten** — desdobramento horizontal: a melhoria (ou a causa raiz) encontrada num lugar é levada a todos os lugares onde a mesma classe de problema existe — outros servidores, repositórios, clientes, skills. Padronizar é vertical (vira o novo piso aqui); yokoten é lateral (o vizinho não precisa redescobrir). Sem ele, o mesmo incidente é resolvido N vezes, uma por equipe.
- **No-blame** — princípio cultural: defeito é informação sobre o processo, não acusação. Sem isso, os problemas se escondem e o Kaizen morre.

## Os 10 princípios (versão clássica, adaptada a software)

1. Abandone ideias fixas; questione o "sempre foi assim".
2. Pense em como fazer, não em por que não dá.
3. Não aceite desculpas; comece questionando a prática atual.
4. Não busque a perfeição: 60% agora vale mais que 100% nunca.
5. Corrija o erro imediatamente, no local (jidoka).
6. Não gaste dinheiro no Kaizen — use criatividade antes de capital (automatize com o que já tem).
7. A sabedoria emerge diante da dificuldade: problema é oportunidade.
8. Pergunte "por quê?" cinco vezes; busque a causa raiz.
9. Melhor a sabedoria de dez pessoas que o conhecimento de uma: melhoria é de todos.
10. O Kaizen não tem fim.

## Como ensinar (roteiro sugerido)

1. Comece pelo problema que o time sente (retrabalho? bug que volta? entrega lenta?) — não pela teoria.
2. Apresente a ideia central: pequeno + frequente + verificado > grande + raro + arriscado.
3. Mostre o PDCA com um exemplo real do projeto (um bug recente é ótimo material para 5 Porquês).
4. Apresente os 7 desperdícios e peça para o time apontar onde eles aparecem no dia a dia.
5. Feche com o compromisso mínimo: kaizen log vivo + retrospectiva com um experimento por ciclo.

Ao gerar material de treinamento (documento, apresentação), estruture nessa ordem e use exemplos do código/processo real do time sempre que disponível.
