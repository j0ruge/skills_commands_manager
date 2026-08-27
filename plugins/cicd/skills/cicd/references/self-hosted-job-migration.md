# Migrar um job cobrado para o runner self-hosted — o que quebra

## Quando usar esta reference

Você decidiu puxar a alavanca de custo da `ci-cost-minutes.md` §3a — mover `ci` / `build-and-push`
de `ubuntu-latest` para `[self-hosted, <label>]`. Ou o job já foi movido e agora falha em algum
lugar onde nunca falhava.

Esta reference cobre a **outra metade** daquele conselho: o runner hospedado é uma imagem curada,
cheia de coisa pré-instalada e com uma topologia de rede específica. Um runner self-hosted não é
nada disso. O YAML não muda, e mesmo assim o job quebra.

> **Distinção importante:** `self-hosted-runner-docker.md` trata de **construir e registrar** o
> runner (imagem `myoung34`, token, crashloop). Esta trata de **rodar jobs de aplicação** nele.

---

## O pré-voo, na ordem de risco medida

A versão anterior desta lista rankeava "service containers exigem Docker no runner" como o ponto de
falha mais provável. **Medido numa migração real: passou de primeira** — `Initialize containers`
subiu o Postgres e o healthcheck ficou `healthy` sem nenhum ajuste. O que quebrou foi outra coisa,
três vezes seguidas.

| # | Verificar | Sintoma se faltar |
| - | --------- | ----------------- |
| 1 | **Toolchain que o runner hospedado dá de graça** (`yarn`, `pnpm`, `jq`, `ss`, `ip`) | §1 — `setup-node` morre antes do `install` |
| 2 | **Como o job alcança um `services:` container** | §2 — `P1001` / connection refused, com o container `healthy` |
| 3 | **Versão do runner**, se você pensar em `container:` | §3 — `checkout` nem executa |
| 4 | Step de **limpeza de workspace** replicado | `fatal: missing blob object` no `checkout` |
| 5 | Docker disponível para `services:` | raro; costuma estar OK no host que já faz deploy |
| 6 | Um runner roda **um job por vez** | jobs antes paralelos serializam |

E uma verdade operacional que vale por si: **"movido para self-hosted" não é "funciona em
self-hosted".** Um workflow que teve o `runs-on` trocado e ainda não executou carrega configuração
não testada. Se você mover `ci.yml` e o job `ci` do `cd-staging.yml` juntos, corrija os dois em
paralelo — senão o merge descobre cada armadilha de novo, uma por vez.

---

## §1. O runner não tem `yarn` — e o `cache:` do `setup-node` morre antes do `install`

```
##[error]Unable to locate executable file: yarn. Please verify either the file path exists or
the file can be found within a directory specified by the PATH environment variable.
```

**Por que engana:** o step que falha é o `actions/setup-node`, que "não tem nada a ver com yarn".
Tem: `cache: 'yarn'` faz a action **invocar o binário** para descobrir o diretório de cache e
montar a chave. Sem yarn no `PATH`, ela morre — antes de qualquer `yarn install`, e antes de
qualquer chance de instalar o yarn num step seu.

Em `ubuntu-latest` isso nunca aparece porque a imagem traz yarn 1.x pré-instalado.

**Fix** — tirar o cache do `setup-node` e provisionar a ferramenta num step próprio:

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '22.15.0'
    # sem `cache:` — ver §1

- name: Provisiona o yarn
  run: |
    corepack enable || true
    yarn --version || npm install -g yarn@1.22.22
    yarn --version
```

Perder o cache do Actions custa pouco aqui: no self-hosted o `~/.cache/yarn` sobrevive entre
execuções, que é justamente o que o cache do Actions estava simulando. (E veja
`ci-cost-minutes.md` §3d — `cache:` configurado não garante cache quente de qualquer forma.)

**Generalize:** a mesma classe morde `pnpm`, `jq`, `ss`, `ip`, `zip`. Antes de migrar, rode um step
descartável com `command -v` para cada ferramenta que o workflow assume.

---

## §2. O job não alcança o `services:` container

```
Error: P1001: Can't reach database server at `localhost:5432`
```

(`P1001` é do Prisma; com `psql`/`pg_isready` o sintoma é `Connection refused`.)

**Por que engana muito:** o log mostra o container subindo corretamente —

```
docker create ... --network github_network_<id> --network-alias postgres -p 5432:5432 ...
postgres service is healthy.
```

— e `Initialize containers` fica verde. Mas **o healthcheck roda DENTRO do container**
(`pg_isready` no próprio Postgres). Ele prova que o banco subiu; não prova **nada** sobre o job
conseguir alcançá-lo.

### Duas hipóteses plausíveis que custam rodadas — e são falsas

**"`localhost` resolve para `::1` e o Docker publicou só IPv4."** Verificável em um `grep`: o log do
runner imprime o mapeamento. Se disser

```
5432/tcp -> 0.0.0.0:5432
5432/tcp -> [::]:5432
```

as duas famílias estão publicadas e trocar `localhost` por `127.0.0.1` não muda nada.

**"É só declarar `container:` no job."** Direcionalmente certo (põe o job na rede dos services, onde
o alias `postgres` resolve) mas depende do runner — ver §3.

### A causa real: o runner pode estar dentro de um container

Se o runner roda conteinerizado (comum — é o próprio blueprint da `self-hosted-runner-docker.md`),
então `docker create -p 5432:5432` publica a porta no **host**, enquanto `127.0.0.1` dentro do job é
o loopback **do runner**. Os dois nunca se encontram. O caminho é o **gateway do bridge**.

### Descubra em vez de supor

Este é o ponto da seção. Você geralmente **não tem SSH para o host do runner** — então o job é o
único instrumento de medição disponível. Faça-o reportar o ambiente e escolher o host sozinho:

```yaml
- name: Descobre como alcancar o Postgres
  shell: bash
  run: |
    # `ip` costuma NÃO existir no container do runner; o gateway sai de
    # /proc/net/route (hex little-endian). `strtonum` é extensão do gawk e o
    # Debian traz mawk, então a conversão vai no printf do bash.
    gw=""
    if [ -r /proc/net/route ]; then
      hex=$(awk '$1 != "Iface" && $2 == "00000000" { print $3; exit }' /proc/net/route)
      [ -n "$hex" ] && gw=$(printf '%d.%d.%d.%d' "0x${hex:6:2}" "0x${hex:4:2}" "0x${hex:2:2}" "0x${hex:0:2}")
    fi
    for i in $(seq 1 30); do
      for h in "$gw" 127.0.0.1 host.docker.internal postgres; do
        [ -z "$h" ] && continue
        if (echo > /dev/tcp/"$h"/5432) 2>/dev/null; then
          echo "postgres alcancavel em $h:5432"
          echo "DATABASE_URL=postgres://u:p@$h:5432/test_db" >> "$GITHUB_ENV"
          exit 0
        fi
      done
      sleep 2
    done
    echo "::error::Postgres inalcancavel em todos os candidatos"
    echo "hostname=$(hostname)"
    if [ -f /.dockerenv ]; then echo "job roda DENTRO de container"; else echo "job roda no HOST"; fi
    cat /proc/net/route 2>/dev/null || echo "(ilegivel)"
    exit 1
```

Os demais steps deixam de declarar `DATABASE_URL` — ele vem do `$GITHUB_ENV`. A ordem dos
candidatos cobre as três topologias (runner no host, runner em container, job em container), então
o mesmo workflow serve para as três sem você saber de antemão qual é.

**O bloco de diagnóstico é a parte que paga.** Numa medição real, `hostname=eb386592c048` +
`/.dockerenv` presente respondeu em uma execução o que três hipóteses não tinham respondido.

⚠️ **Cuidado com `2>/dev/null` em sonda de diagnóstico.** Uma primeira versão desse step fazia
`ss -ltn 2>/dev/null | grep 5432` e imprimiu **nada** — o que se lê como "nenhuma porta escutando",
mas era `ss: command not found` engolido pelo redirect. Sonda que pode não existir merece
`command -v` antes, ou a mensagem de erro visível.

---

## §3. `container:` não é a saída se o runner estiver desatualizado

```
OCI runtime exec failed: exec failed: unable to start container process:
exec: "/__e/node24/bin/node": stat /__e/node24/bin/node: no such file or directory
```

**O que está acontecendo:** quando o job declara `container:`, o GitHub monta os `externals` do
runner dentro dele em `/__e` e executa as actions JavaScript com **o Node do runner**. Como o
GitHub força as actions para Node 24, um runner antigo — que só traz `node16`/`node20` — não tem o
binário pedido. O `actions/checkout` **nem chega a rodar**.

**Assinatura de isolamento:** o mesmo workflow funciona **sem** `container:` no mesmo runner. Se
tirar o `container:` conserta, é versão de runner, não rede.

**Fixes, na ordem:**

1. **Atualizar o runner** (correção de verdade; é manutenção de host).
2. **Não usar `container:`** — resolva a rede pelo §2, que não depende da versão do runner.
3. `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true` força as actions para Node 20. Desbloqueia, mas é
   band-aid num caminho que o GitHub está removendo — só como ponte até (1).

Aviso relacionado: a linha `Node.js 20 is deprecated … being forced to run on Node.js 24` aparece
como **warning** em execuções que passam. Num runner desatualizado ela é o aviso prévio de (3).

---

## §4. Workspace sujo entre execuções

O runner reaproveita o diretório de trabalho, e um `.git` corrompido de execução anterior derruba o
`checkout` com `fatal: missing blob object`. O job de `deploy` de um blueprint self-hosted
normalmente já carrega o guard; ao **migrar** outros jobs, replique-o como primeiro step de cada um:

```yaml
- name: Clean self-hosted workspace
  shell: bash
  run: |
    if [ -d "${{ github.workspace }}/.git" ]; then
      rm -rf "${{ github.workspace }}/.git"
    fi
```

---

## §5. Como confirmar que a migração pegou

```bash
gh api "/repos/<o>/<r>/actions/runs/<id>/jobs" \
  -q '.jobs[] | [.name, .runner_name, .runner_group_name, .conclusion] | @tsv'
```

- `runner_name` preenchido com o seu runner = rodou onde devia, custo zero.
- `runner_name` **vazio** + **zero steps** + duração de ~3s = **não é falha de código**; é bloqueio
  de cota/cobrança. Ver `ci-cost-minutes.md` §5.

---

## §6. A lição que generaliza

Foram **quatro rodadas de CI gastas em hipóteses lidas do YAML** (IPv6, `container:`, ordem dos
candidatos) contra **uma** que respondeu: a que fez o job descrever o próprio ambiente.

Quando o runner é uma caixa-preta — sem SSH, sem `docker exec`, sem saber se é host ou container —
**o job é o instrumento de medição**. Um step que imprime `hostname`, `/.dockerenv`, rotas e o
resultado de cada candidato custa segundos e substitui uma rodada inteira de adivinhação.

Faça isso **na primeira falha**, não depois do terceiro palpite.
