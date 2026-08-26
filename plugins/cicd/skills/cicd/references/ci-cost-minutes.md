# Custo de minutos do GitHub Actions — medir antes de cortar

Referência para quando a **cota de Actions** é a restrição, não a corretude do pipeline. O resto da
skill trata de pipeline quebrado; aqui o pipeline funciona e o problema é o que ele cobra.

Tema unificador: **o custo não é proporcional ao tempo de execução** — ele é proporcional ao número
de jobs em runner hospedado, e boa parte do trabalho pode migrar para capacidade que a organização
já paga e mantém ociosa.

---

## 1. O modelo de custo (as três regras que decidem tudo)

| Regra | Consequência prática |
| ----- | -------------------- |
| Repositório **privado** consome a cota; **público** é gratuito | Um repo que virou privado passa a cobrar sem nenhuma mudança no workflow |
| O GitHub arredonda **cada JOB para cima, ao minuto** | Um job de 51s custa **1 minuto cheio**; dois jobs de 20s custam 2 minutos |
| Runner **self-hosted não consome cota** | Jobs movidos para lá custam **zero**, qualquer que seja a duração |

**Corolário não óbvio:** a **contagem de jobs** é uma alavanca de custo independente da duração.
Dividir um job em dois (por clareza, por paralelismo) adiciona um minuto faturado mesmo que o
trabalho total seja idêntico. O instinto de "paralelizar para ficar mais rápido" **aumenta a conta**
— compra wall-clock com minutos.

Multiplicadores por SO: Linux **1x**, Windows **2x**, macOS **10x**. Se há job em macOS, ele domina
a conta sozinho e é o primeiro lugar a olhar.

---

## 2. Como medir — e a armadilha que invalida a medição

**A armadilha:** o endpoint de timing pode reportar zero faturável para uma execução que
claramente rodou.

```console
$ gh api /repos/<owner>/<repo>/actions/runs/<id>/timing
{"billable":{"UBUNTU":{"total_ms":0,"jobs":2,"job_runs":[...]}},"run_duration_ms":322000}
```

`total_ms: 0` com `run_duration_ms: 322000` (5m22s) e `jobs: 2`. Quem confia nesse número conclui
"não estamos gastando nada" e para de investigar — exatamente a conclusão errada.

**Medição confiável — por job, com o grupo do runner:**

```bash
ID=$(gh run list --limit 1 --workflow="CD Staging" --json databaseId -q '.[0].databaseId')
gh api "/repos/<owner>/<repo>/actions/runs/$ID/jobs" \
  -q '.jobs[] | [.name, .runner_group_name, (((.completed_at|fromdate)-(.started_at|fromdate))|tostring)+"s"] | @tsv'
```

```text
CI                GitHub Actions   90s     ← hospedado  → COBRADO (2 min)
Build & Push      GitHub Actions   83s     ← hospedado  → COBRADO (2 min)
Deploy Staging    Default          47s     ← self-hosted → grátis
```

**`runner_group_name` é a chave de isolamento**: `GitHub Actions` = runner hospedado (cobrado);
`Default` (ou grupo próprio) = self-hosted (grátis). Some as durações dos hospedados **arredondando
cada uma para cima** — é isso que aparece na fatura.

**Billing de organização:** `GET /orgs/<org>/settings/billing/actions` responde **410 Gone**
(endpoint movido) e a rota atual exige escopo `admin:org`. Sem ser admin da org, a medição por job
acima é o caminho — e é suficiente para priorizar.

**Runners disponíveis:** `gh api /repos/<o>/<r>/actions/runners` lista **só os de repositório**.
Um runner de **organização** não aparece ali, e concluir "não existe runner" a partir dessa lista
vazia é erro comum — confirme pelo `runner_name` de um deploy que concluiu:

```bash
gh api "/repos/<o>/<r>/actions/runs/$ID/jobs" -q '.jobs[] | select(.runner_group_name=="Default") | .runner_name'
```

---

## 3. Alavancas, por retorno sobre risco

### (a) Mover jobs cobrados para o self-hosted ocioso — maior economia

Em muitos setups o self-hosted só executa o job `deploy` (dezenas de segundos por dia) enquanto
`build-and-push` e o gate de CI queimam minutos no hospedado. Não há nada nesses jobs que exija
runner hospedado.

```yaml
build-and-push:
  runs-on: [self-hosted, staging]    # era: ubuntu-latest
```

Verifique antes:

- **Service containers exigem Docker no runner** (`services: postgres:` etc.). Host que roda deploy
  com Docker atende, mas é o ponto de falha mais provável da migração.
- O **build da imagem passa a usar CPU/disco do host de deploy**. Em compensação o cache de camadas
  fica quente, e o `docker push` sai da rede do runner hospedado.
- **Um runner executa um job por vez.** Jobs que rodavam em paralelo no hospedado passam a
  serializar. Se já havia `needs:` encadeando, o wall-clock muda pouco.
- Replique qualquer step de **limpeza de workspace** que o job de deploy já tenha (o `.git`
  corrompido entre execuções é recorrente — ver `troubleshooting-shared.md`).

Rollout: **staging primeiro**, observar um deploy real, só então produção.

### (b) `paths-ignore` — inclusive em `pull_request`

A lição 57 cobre `on.push.paths-ignore` para não redeployar em commit de documentação. O mesmo vale
para o **CI de PR**, que costuma ser esquecido:

```yaml
on:
  pull_request:
    branches: [develop, main]
    paths-ignore: ['**/*.md', 'docs/**', 'specs/**', '.claude/**']
  push:
    branches: [develop]
    paths-ignore: ['**/*.md', 'docs/**', 'specs/**', '.claude/**']
```

Em repositório com documentação viva (ADRs, notas, specs, artefatos de QA) a metade dos commits
pode ser só `.md`. **Nuance da lição 57:** `paths-ignore` só pula quando **todos** os arquivos do
push casam — um commit que toque código junto com docs continua rodando tudo.

Não aplique em workflow disparado por **tag** (`on.push.tags`): filtro de path com tag tem semântica
confusa e o deploy de release não deve ser pulável.

### (c) O mesmo commit testado três vezes

Blueprint comum: `ci.yml` no PR, job `ci` no `cd-staging.yml` (push em `develop`) e outro job `ci`
no `cd-production.yml` (tag). O mesmo SHA passa pelo mesmo lint/test **três vezes**.

Ordem de preferência:

1. **Mover os jobs de CI do CD para self-hosted** (alavanca *a*) — mantém os três gates e zera o
   custo dos dois últimos. Preferível, porque o gate de CD é o que protege contra push direto no
   branch protegido (lição 44).
2. Se o self-hosted não puder rodá-los, **remover o job `ci` do `cd-staging.yml`** (o `develop` só
   recebe PR mergeado) e **manter** o do `cd-production.yml` como último portão antes da tag.

### (d) Fundir jobs pequenos

Por causa do arredondamento, dois jobs de menos de um minuto custam 2 minutos. Fundir `lint` e
`test` num job só economiza ~1 minuto por execução. Custo: perde o paralelismo e o sinal
vermelho/verde separado — e, se o time usa **required checks** por nome de job, fundir **quebra a
branch protection** até os nomes serem reconfigurados.

### (e) Gate local de pre-push

Falha de lint/formatação descoberta no CI custa o run inteiro. Rodar `lint`, `format --check` e
typecheck antes do push elimina essas execuções. É a alavanca de maior retorno por esforço quando o
histórico mostra várias execuções seguidas falhando no mesmo passo barato.

---

## 4. O que NÃO economiza (e parece que sim)

- **Composite action para deduplicar o gate de CI (lição 43).** Ela resolve *drift* entre `ci.yml` e
  o re-gate do CD — os passos deixam de divergir. Mas **o job continua existindo e rodando**: a
  economia é zero. Deduplicar *código* de workflow e deduplicar *execução* são coisas diferentes; só
  a segunda aparece na fatura.
- **`cache: 'yarn'` / `cache: 'npm'` configurado.** Configurar não garante cache quente: entradas do
  Actions Cache **expiram após 7 dias sem acesso**. Em repositório de baixo tráfego, todo run começa
  frio mesmo com o `cache:` correto. Confirme antes de contar com ele:

  ```bash
  gh api /repos/<o>/<r>/actions/cache/usage \
    -q '"\(.active_caches_count) entradas, \(.active_caches_size_in_bytes/1048576|floor) MB"'
  ```

  `0 entradas` significa que todo `install` está baixando tudo, sempre.
- **`cancel-in-progress`.** Vale ter (evita runs supersedidos), mas só corta desperdício de pushes
  em rajada — não muda o custo do caminho feliz.
- **Reduzir a duração de um job que já roda em menos de um minuto.** O arredondamento come a
  otimização inteira: de 51s para 20s continua custando 1 minuto.

---

## 5. Checklist rápido

- [ ] O repositório é privado? (se público, não há o que economizar)
- [ ] Medi por job com `runner_group_name`, sem confiar em `billable.total_ms`?
- [ ] Há runner self-hosted ocioso que poderia rodar `build`/`ci`?
- [ ] `paths-ignore` está nos gatilhos de **PR e push**, não só num deles?
- [ ] O mesmo SHA roda CI mais de uma vez? Quantas?
- [ ] Há job em macOS/Windows (multiplicador 10x/2x)?
- [ ] O cache tem entradas ativas, ou está expirando entre execuções?
- [ ] Falhas repetidas de lint/format no histórico sugerem gate local ausente?
