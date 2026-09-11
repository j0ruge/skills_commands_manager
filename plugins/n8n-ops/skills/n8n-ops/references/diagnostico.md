# Diagnosticar uma automação que não avisou

Índice: [`../SKILL.md`](../SKILL.md). Este arquivo detalha a escada "gravou? notificou? entregou?".

## Por que a ordem importa

Cada passo elimina exatamente uma hipótese. Pular um faz acusar a etapa errada — e a etapa errada
costuma ser a mais visível (o e-mail que não chegou), não a culpada (o gatilho que nunca rodou).
A ordem também é a mais barata primeiro: o passo 1 é uma consulta ao banco do produto, o passo 4
exige desachatar um JSON.

## 1. O dado foi gravado, e satisfaz a pré-condição?

```sql
select <chave>, created_at from <tabela> where <correlação> = '<valor>';
select count(*) from <tabela_de_itens> where <fk> = '<id>';
```

Se o fluxo tem pré-condição (só notifica quando há item, só alerta acima de um limiar), confira-a
aqui. **Pré-condição não satisfeita ⇒ o fluxo não deveria ter rodado**, e o erro que apareceu no
console do cliente é esperado, não defeito. Diagnóstico encerrado.

## 2. O gatilho executou?

```sql
select id, status, "startedAt" from execution_entity
where "workflowId" = '<id-do-gatilho>' order by "startedAt" desc limit 5;
```

| Resultado | Leitura |
|---|---|
| Há execução `success` | siga para o passo 3 |
| Nenhuma execução, e o dado está gravado | ou o evento nasceu num canal que não chama o webhook (app desktop, backend, job), ou a gravação de execuções está desligada |
| Execução `error`/`crashed` | pule para o passo 4, a mensagem está gravada |

⚠️ **Não troque esta consulta por um olhar em `workflow_entity.active`.** A coluna não prova que o
workflow está ou não executando — ver a regra no corpo da skill. O sensor é esta tabela, aqui e em
qualquer outro passo.

## 3. O fluxo dependente executou?

Mesma consulta com o outro `workflowId`. A correlação entre os dois raramente é direta: o payload
do primeiro costuma não carregar a chave de negócio do segundo. Correlacione por **identidade de
negócio + janela de tempo**, e confirme pela ordem dos `startedAt`.

## 4. A entrega aconteceu? — desachatando `flatted`

```sql
select data from execution_data where "executionId" = <id>;
```

O campo é um array JSON no formato **`flatted`**: toda string dentro de um objeto é um **índice**
para outra entrada do array. `JSON.parse` devolve algo que parece válido e não é.

```js
/**
 * Desachata o formato `flatted` que o n8n usa em `execution_data.data`.
 *
 * @param {string} bruto JSON achatado vindo do banco.
 * @returns {object} Objeto com as referências por índice já resolvidas.
 */
function desachatar(bruto) {
  const arr = JSON.parse(bruto);
  const resolvido = new Map();
  const resolver = (v) => {
    if (typeof v === 'string' && /^\d+$/.test(v)) return resolver(arr[Number(v)]);
    if (Array.isArray(v)) return v.map(resolver);
    if (v && typeof v === 'object') {
      if (resolvido.has(v)) return resolvido.get(v);
      const saida = {};
      resolvido.set(v, saida);
      for (const [k, val] of Object.entries(v)) saida[k] = resolver(val);
      return saida;
    }
    return v;
  };
  return resolver(arr[0]);
}
```

Depois de desachatar, os dois campos que respondem quase tudo:

- `resultData.lastNodeExecuted` — parou antes do nó de entrega ⇒ não entregou.
- `resultData.error.message` — a causa real, quando o status é `error`.

Erro costuma ficar gravado mesmo com sucesso desligado (`EXECUTIONS_DATA_SAVE_ON_ERROR=all`), com
retenção limitada (`MAX_AGE`, tipicamente 72 h). Diagnostique dentro da janela ou o rastro some.

## 5. O cliente chama o endpoint que alguém escuta?

Se tudo acima está verde, o POST saiu para um lugar sem ouvinte. Compare o endpoint **como servido
ao usuário** (não o do código-fonte, nem o de dentro do container) com os paths dos workflows
ativos:

```bash
# o que o navegador realmente recebe
JS=$(curl -s https://<host>/ | grep -oE '/assets/index-[^"]+\.js' | head -1)
curl -s "https://<host>$JS" | grep -oE 'https://[^"]*/webhook[^"]*'
```

Duas causas típicas de divergência:

- **`/webhook-test/` publicado** — só responde com a aba de teste aberta na UI (ver corpo da skill).
- **Configuração de build errada** — se o cliente é um bundle, a URL foi embutida em tempo de
  compilação. Em CI com Environments, **secret de Environment prevalece sobre secret de
  repositório**: corrigir o do repositório não muda nada, e a divergência sobrevive a rebuilds.

## Remediações por sintoma

| Sintoma | Onde olhar |
|---|---|
| Gatilho rodou, dependente não, pré-condição satisfeita | passo 5 primeiro; se verde, confira se o workflow está ativo e se o path bate |
| Execução presa em `running`/`waiting` | abra a execução pelo id e veja o `lastNodeExecuted`; nó de e-mail preso costuma ser credencial expirada |
| `status = error` | `resultData.error.message` do passo 4 |
| Nenhum sucesso aparece, nunca | gravação de sucesso desligada — o vigia está cego para esse workflow |
