# Templates dos artefatos Kaizen

Use estes templates ao gerar os artefatos. Adapte os campos ao contexto — o template serve ao trabalho, não o contrário.

## Plano PDCA

Salve como `docs/planos/PLANO-<slug-curto>.md` (ou onde o projeto guardar planos).

```markdown
# Plano PDCA — <título curto da mudança>

**Data:** <AAAA-MM-DD> · **Responsável:** <quem>

## Problema / objetivo (1 frase)
<O que dói hoje, ou que valor queremos entregar.>

## Métrica de sucesso
<Como saberemos que melhorou — número, comportamento observável ou teste que passa.>

## Gemba — situação atual
<O que foi observado no código/sistema real: arquivos afetados, fluxo atual, dados.>

## Desperdícios evitados
<Itens cortados/adiados do escopo e por quê (superprodução, superprocessamento...).>

## Incrementos (Do)
| # | Incremento | Entrega verificável | Check (como verificar) |
|---|---|---|---|
| 1 | <menor passo de valor> | <o que fica pronto> | <teste/medição> |
| 2 | ... | ... | ... |

## Riscos e reversão
<O que pode dar errado em cada incremento e como reverter.>

## Act (após o Check)
<Preenchido ao final: o que padronizar, o que ajustar, entrada no kaizen log.>
```

## Kaizen Log

Arquivo único `KAIZEN_LOG.md` na raiz do projeto, entradas mais recentes no topo.

```markdown
# Kaizen Log — <nome do projeto>

Registro de melhorias contínuas. Toda entrada tem: o que melhorou, o que aprendemos, o que virou padrão.

## <AAAA-MM-DD> — <título curto>
- **Tipo:** melhoria | correção de causa raiz | oportunidade (a fazer) | padronização
- **Antes:** <situação anterior em 1 linha>
- **Depois:** <situação nova em 1 linha, com métrica se houver>
- **Causa raiz (se defeito):** <resultado dos 5 porquês>
- **Padronizado em:** <convenção/doc/teste/CI atualizado — ou "pendente">

### Desperdícios evitados (cortes conscientes)
- <o que ficou fora do escopo e por quê — qual dos 7 desperdícios evitou>

### O que aprendemos
- <a pegadinha técnica que custou tempo e que a próxima pessoa redescobriria>
```

**Antes de fechar a entrada, abra o arquivo citado em "Padronizado em" e confirme que a
mudança está lá.** Esse campo é a única linha do log que afirma algo sobre o mundo **fora**
do log — todas as outras descrevem o que já aconteceu, e essa promete que algo mudou em
outro lugar. Escrever o caminho é rápido e dá a sensação de ter padronizado; ninguém
verifica depois, e a entrada passa a documentar uma convenção que não existe. Se a mudança
ainda não foi feita, escreva `pendente` — é informação honesta e acionável. É o mesmo
defeito que o Kaizen ensina a caçar em produção (ver *Rótulo ≠ artefato* em
`kaizen-conceitos.md`), aplicado ao próprio registro da melhoria: o campo é o rótulo, o
arquivo alterado é o artefato.

As duas últimas subseções são **opcionais** — inclua quando houver conteúdo real, não para
preencher formulário. Elas existem porque sem elas o log registra só *o que* mudou: o
**porquê do corte** vira "esqueceram de fazer" seis meses depois (e alguém reabre o escopo
já rejeitado), e a **lição** técnica é redescoberta do zero pela próxima pessoa. O corte
consciente é decisão de engenharia e merece o mesmo registro que a entrega.

## 5 Porquês

Registre dentro da entrada do kaizen log ou no corpo da correção do bug.

```markdown
### 5 Porquês — <defeito>
- **Sintoma:** <o que o usuário viu>
1. Por quê? <resposta>
2. Por quê? <resposta>
3. Por quê? <resposta>
4. Por quê? <resposta — pare antes se chegar à causa de processo>
5. Por quê? <causa raiz de processo>
- **Contramedida:** <mudança pequena que ataca a causa raiz>
- **Teste que teria pegado:** <teste adicionado>
```

Regra de ouro: a causa raiz é sempre um processo ou uma ausência de salvaguarda, nunca uma pessoa ("fulano errou" → continue perguntando: por que o erro foi possível e passou?).

## Retrospectiva

```markdown
# Retrospectiva — <ciclo/período>

## O que fluiu bem (manter)
- ...

## O que atrapalhou (desperdícios observados)
- <item + qual dos 7 desperdícios é>

## Experimentos para o próximo ciclo
| Experimento | Dono | Como saberemos que funcionou |
|---|---|---|
| <mudança pequena de processo> | <quem> | <sinal observável> |
```

Converta cada experimento aprovado em entrada do kaizen log quando concluído.
