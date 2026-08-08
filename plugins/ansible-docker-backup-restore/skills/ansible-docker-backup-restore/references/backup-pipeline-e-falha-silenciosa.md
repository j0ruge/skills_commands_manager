# O pipeline de backup e as quatro formas de ele morrer calado

**Gate obrigatório.** Um restore não termina quando os serviços sobem; termina
quando o backup daquele servidor foi provado vivo. Este arquivo também é o ponto
de partida sempre que um backup for suspeito.

O caso que originou esta skill: o backup de um servidor ficou **dias sem
completar**. Nenhum alerta, nenhuma falha visível, nenhum e-mail. O que
denunciou foi acaso — alguém foi conferir se um caminho novo entraria no backup
e reparou que a última pasta no destino era de dias atrás. A causa raiz foi o
**restore anterior**, que renomeou um container e não atualizou o inventário.

---

## §1. Primeiro: prove que o backup de hoje existe e está completo

Antes de investigar qualquer coisa, meça. `scripts/check-backup-freshness.sh`
faz isto de forma somente-leitura; à mão é assim:

```bash
# A pasta de hoje existe? E as anteriores formam uma sequência SEM buracos?
ssh root@<backup_host> 'ls -1 <backup_root>/<servidor>/'

# Um dump por banco esperado, nenhum com tamanho ridículo?
ssh root@<backup_host> 'ls -la <backup_root>/<servidor>/<hoje>/databases/'

# Contagem de volumes compatível com `docker volume ls` no servidor?
ssh root@<backup_host> 'ls -1 <backup_root>/<servidor>/<hoje>/volumes/ | wc -l'
ssh <user>@<servidor>  'sudo docker volume ls -q | wc -l'
```

**O buraco na sequência de datas é o sinal mais barato que existe**, e é o único
que teria pego o caso acima no primeiro dia. Se você automatizar uma única coisa
depois de ler este arquivo, automatize isto.

Três leituras da listagem, em ordem de gravidade:

| O que você vê | O que significa |
|---|---|
| Falta a pasta de hoje | A play não chegou ao fim — §2.1 ou §2.3 |
| A pasta existe, mas falta o dump de um banco | Falha silenciosa por item — §2.2 |
| Tudo existe, mas um dump tem poucos bytes | O comando rodou e falhou dentro do container; o arquivo é a mensagem de erro |

### §1.1 Tamanho é proxy fraco — prove integridade e prove que há DADOS

A última linha da tabela acima ("poucos bytes") pega o caso grosseiro, e é onde
`check-backup-freshness.sh` para. Mas o inverso passa: **um dump só com o schema é
grande, bem formado e inútil para restaurar.** `CREATE TABLE` de cem tabelas dá dezenas
de KB sem uma única linha de dado. Três perguntas, em ordem de custo:

```bash
# 1. É um gzip válido? (pega truncamento por disco cheio / conexão cortada)
ssh root@<backup_host> 'gzip -t <dump>.sql.gz && echo "gzip OK"'

# 2. Tem DADOS, não só DDL? Cada COPY é um bloco de linhas.
ssh root@<backup_host> 'gzip -dc <dump>.sql.gz | grep -c "^COPY public"'

# 3. Um registro que você SABE que existe está lá dentro?
ssh root@<backup_host> 'gzip -dc <dump>.sql.gz | grep -c "<valor conhecido>"'
```

A pergunta 3 é a única que fecha o círculo, e é barata: escolha algo estável e único do
domínio (a razão social da empresa, o código da filial padrão, um e-mail de sistema). Se
ela não aparece, você tem um arquivo que passa nas perguntas 1 e 2 e ainda assim não é o
backup daquele banco — dump apontado para o cluster errado, para um banco homônimo vazio,
ou de antes da carga inicial.

Para dumps em formato custom (`pg_dump -Fc`), troque as perguntas 1 e 2 por
`pg_restore -l <dump> | wc -l`, que lista o índice do arquivo sem restaurar nada e falha
se o arquivo estiver corrompido.

> Isto pertence ao §1 e não ao §2 de propósito: as quatro formas de morrer calado do §2
> são falhas **do pipeline**. Aqui o pipeline funcionou, a play saiu `failed=0`, o arquivo
> está no lugar e no horário certo — e não serve. Nenhum sinal do §2 acusa isso.

### §1.2 O healthcheck de um container de backup normalmente mede a coisa errada

Quando o backup é um container dedicado (`prodrigestivill/postgres-backup-local` e
parentes) em vez de uma play Ansible, o instinto é confiar no `healthy` do Docker. Não
confie: o healthcheck dessas imagens observa **a porta HTTP de status que a própria imagem
expõe**, não o arquivo que o job deveria produzir. O container fica genuinamente `healthy`
— o servidorzinho dentro dele está no ar — enquanto o `pg_dump` falha todas as noites.

Caso real: **três meses `healthy`, zero dumps.** A causa foi configuração —
a imagem faz fan-out de lista CSV **só** em `POSTGRES_DB`, contra **um** host/usuário/senha;
uma lista em `POSTGRES_HOST`/`POSTGRES_USER`/`POSTGRES_PASSWORD` é usada literalmente, então
o `pg_dump` tentava autenticar com o usuário `erp,zitadel` e morria. O banco que ficou
desprotegido era o do IdP que autenticava todos os outros serviços do host.

```bash
# Não pergunte ao healthcheck. Force um ciclo e olhe o artefato.
docker exec <backup-ctr> /backup.sh
docker exec <backup-ctr> ls -lh /backups/last/
docker exec <backup-ctr> sh -c 'gzip -t /backups/last/*.sql.gz && echo "íntegro"'
```

Duas armadilhas de configuração que valem conferir de saída:

| Sintoma | Causa |
|---|---|
| `pg_dump` autenticando com usuário do tipo `a,b` | lista CSV no campo errado — um service por cluster/credencial |
| `pg_dump: server version mismatch` | tag da imagem mais antiga que o servidor (cluster 17 exige `:17-alpine`, não `16-alpine`) |

O segundo falha alto — mas falha de madrugada e sem plateia, o que na prática dá no mesmo
que falhar calado.

---

## §2. Os quatro padrões de falha silenciosa

### 2.1 `ignore_errors` + `no_log` na mesma task = silêncio absoluto

```yaml
# NÃO faça isto
- name: Dump dos bancos
  community.docker.docker_container_exec:
    container: "{{ item.name }}"
    command: sh -c "<dump> | gzip > /tmp/<arquivo>"
  loop: "{{ db_containers }}"
  ignore_errors: true      # esconde a falha
  no_log: true             # esconde a mensagem
  register: dumps

- name: Copiar os dumps para fora do container
  ansible.builtin.shell: docker cp …
  loop: "{{ dumps.results }}"
  when: item.rc == 0       # e agora a cópia é PULADA, também em silêncio
```

O `no_log` está ali por um bom motivo (a senha do banco vai no comando). O
`ignore_errors` está ali por outro bom motivo (um container parado não deve
derrubar o backup dos outros). **Juntos, transformam erro de configuração em
nada**: nome de container errado ⇒ sem dump, sem cópia, sem aviso, `changed=0` e
a play segue verde.

O antídoto não é remover as duas — é **contar e asserir depois**:

```yaml
- name: Falhar se algum banco esperado ficou sem dump
  ansible.builtin.assert:
    that: dumps.results | rejectattr('rc', 'equalto', 0) | list | length == 0
    fail_msg: >
      Sem dump para:
      {{ dumps.results | rejectattr('rc','equalto',0) | map(attribute='item.name') | join(', ') }}
```

Note que a asserção usa só o **nome** do item, não a saída — então ela pode ser
explícita sem violar o `no_log`.

**Melhor ainda: um preflight que confere as DUAS direções, antes de dumpar.** A
asserção acima pega o banco declarado que sumiu. Falta o reverso, que é o mais
insidioso: um banco **em execução mas não declarado** no inventário. Ele não é
dumpado por ninguém, e **nada dá erro** — não há item na lista para falhar. Fica
anos sem backup sem um sintoma sequer. Compare `docker ps` com a lista declarada,
nos dois sentidos:

```yaml
- name: Listar containers em execução
  ansible.builtin.command: docker ps --format '{{"{{.Names}}"}}'
  register: running
  changed_when: false

# Declarado mas ausente → FALHA (o erro acontece antes de dumpar, apontando aqui)
- name: Falhar se um container de banco declarado não existe
  vars:
    declarados: "{{ (pg_containers|default([]) + mysql_containers|default([])) | map(attribute='name') | list }}"
  ansible.builtin.assert:
    that: declarados | difference(running.stdout_lines) | length == 0
    fail_msg: "Declarados e ausentes: {{ declarados | difference(running.stdout_lines) | join(', ') }}"

# Em execução com cara de banco mas NÃO declarado → AVISA (heurística, não falha)
- name: Apontar bancos em execução que ninguém dumpa
  vars:
    declarados: "{{ (pg_containers|default([]) + mysql_containers|default([])) | map(attribute='name') | list }}"
    suspeitos: "{{ running.stdout_lines | select('search','(?i)(postgres|mysql|mariadb|_db$|-db$)') | difference(declarados) | list }}"
  ansible.builtin.debug:
    msg: "{{ 'EM EXECUÇÃO e não declarados (não são dumpados): ' ~ (suspeitos|join(', ')) if suspeitos else 'nenhum banco fora do inventário' }}"
```

O aviso só avisa (a heurística por nome pode acusar um não-banco; falhar por
heurística treina todo mundo a ignorar o alerta). Num caso real esse preflight
achou dois bancos de produção — um Postgres e um MariaDB — **em execução e nunca
dumpados por ninguém**, porque simplesmente nunca tinham sido adicionados ao
inventário.

### 2.2 A mesma causa numa task SEM `ignore_errors` = parada total

Na mesma role, uma task de limpeza (`rm` do dump temporário dentro de cada
container) **não** tinha `ignore_errors`. O mesmo nome de container errado que
antes produzia silêncio aqui produzia `Could not find container` e **abortava a
play na quinta task** — antes dos outros dumps, antes dos volumes, antes da
sincronização para o host de backup.

Por isso nada chegava ao destino. E o sintoma que aparecia para quem olhava de
longe era "o backup está demorando", não "o backup falhou".

> As duas metades vinham da **mesma** causa raiz e nenhuma delas gritava. Uma
> escondia, a outra parava. Ao ler uma role de backup, mapeie quais tasks
> abortam e quais engolem — a mistura é que produz o comportamento
> incompreensível.

### 2.3 `set -euo pipefail` + `tar` num diretório vivo

Scripts de backup de volume rodam com `set -euo pipefail`, o que é correto. Mas
o GNU `tar` devolve **1** para `file changed as we read it` — situação **normal**
ao tarar o datadir de um banco em execução. Com `set -e`, isso mata o script.

Pior: volumes costumam ser tarados em ordem alfabética. Um volume de banco cedo
no alfabeto aborta tudo o que vinha depois — outros volumes, e a sincronização
final. E como depende de o banco escrever exatamente durante aquela janela, **a
falha parece intermitente**: em alguns dias passa.

```bash
# Trate rc=1 como aviso CONTADO, e mantenha rc>=2 como falha dura.
tar_volume() {
  local out="$1"; shift
  local rc=0
  tar -cf "$out" "$@" || rc=$?
  if (( rc >= 2 )); then
    echo "  ✗ ERRO FATAL ao gerar ${out} (tar rc=${rc})" >&2
    return "$rc"
  fi
  if (( rc == 1 )); then
    echo "  ⚠ ${out}: arquivos mudaram durante a leitura (volume vivo)." >&2
    WARNED=$((WARNED + 1))
  fi
  return 0
}
```

Isso é seguro **para volume de banco** porque a fonte autoritativa daquele dado
é o dump SQL feito antes, não o tar do datadir. Para volume de aplicação, um
aviso merece investigação.

Detalhe que faz o contador funcionar: alimente o laço com **process
substitution**, não com pipe. Num pipe o laço roda em subshell e a variável
morre antes do resumo final.

```bash
while read -r vol; do … done < <(docker volume ls --format '{{.Name}}')
```

### 2.4 Um caminho ausente derruba o backup inteiro

Uma task que copia um caminho fixo — um arquivo de compose na raiz, por exemplo
— quebra a play toda quando aquele arquivo não existe. E ele deixa de existir
justamente **depois de um restore**, quando os serviços passaram a ser subidos
de outro jeito.

Toda referência a caminho fixo precisa de `stat` + `when`, e de uma mensagem que
**registre a lacuna** em vez de fingir que o arquivo existe.

### 2.5 O caminho de push nunca foi estabelecido — e ninguém verificou por host

A etapa 5 (rsync para o host de backup) pressupõe que o cliente **alcança** o
host de backup por SSH. Essa confiança é fácil de assumir e traiçoeira de
verificar: num caso real, um servidor **nunca teve backup** em parte porque
`root@<cliente>` não tinha a chave de host do destino no `known_hosts` nem chave
autorizada lá. O rsync falhava com `Host key verification failed` e depois
`Permission denied (publickey)` — o terceiro de três bloqueadores empilhados
naquele host.

O erro de raciocínio que o escondeu: **"o sentido cliente→backup funciona" tinha
sido verificado em OUTRO servidor.** A topologia de SSH é por par de hosts;
generalizar de um cliente para outro é como o caso passou meses sem backup.
Verifique o push **de cada cliente**, não de um representante:

```bash
ansible <cliente> -m command -a \
  'rsync -e "ssh -o BatchMode=yes" --dry-run /etc/hostname root@<backup_host>:<dest>/'
```

**E quando for conceder esse acesso, conceda o mínimo.** O rsync vai do cliente
para o host de backup, então autorizar ali a chave root **ampla** do cliente dá,
a quem comprometer esse cliente, root no host de backup — e com ele os backups de
**todos** os servidores, não só os dele. O host de backup vira alvo de
movimentação lateral. É a mesma postura da regra "nunca gravar credencial no
repo", aplicada ao sentido do tráfego.

Chave dedicada, confinada por `rrsync`, e **provada** sem poder de shell:

```
# authorized_keys no host de backup (uma linha):
command="/usr/bin/rrsync -wo <dest_daquele_cliente>",restrict,from="<ip_do_cliente>" ssh-ed25519 AAAA… backup-<cliente>
```

- `rrsync -wo <dir>` → a chave só executa o rrsync, e só escreve (`-w`), e só
  dentro de `<dir>`. Um cliente comprometido não lê nem toca o backup de outro.
- `restrict` → sem PTY, sem port-forward, sem agent. **Sozinho não basta**: ele
  desliga encaminhamentos, não execução de comando — sem o `command=`, a chave
  ainda roda `ssh … 'rm -rf …'`.
- `from="<ip>"` → a chave só vale daquele host.

Prove as duas coisas depois de autorizar — que o push funciona **e** que a chave
não abre shell:

```bash
rsync -e "ssh -i <chave> -o BatchMode=yes" --dry-run /etc/hostname root@<backup_host>:/<subdir>/   # deve passar
ssh -i <chave> -o BatchMode=yes root@<backup_host> id                                              # deve FALHAR
```

Uma restrição que ninguém testou dá a sensação de segurança sem a segurança —
pior que restrição nenhuma, porque ninguém volta a olhar. E cuidado com o destino:
com `rrsync`, o caminho é **relativo** a `<dir>` — mandar `:/opt/backups/x/`
absoluto vira `<dir>/opt/backups/x/`.

---

## §3. Anatomia do pipeline, e onde cada etapa falha

| Etapa | O que faz | Como falha calado |
|---|---|---|
| 1. Dumps de banco | `exec` no container, dump para `/tmp` interno, `docker cp` para fora, `rm` dentro | §2.1 (dump) e §2.2 (limpeza) |
| 2. Volumes | script que itera `docker volume ls` e tara cada um | §2.3, e §3.3 (bind mount não aparece no `volume ls`) |
| 3. Diretórios de código | tar dos caminhos de uma lista de inventário | §2.4, e §3.1 abaixo |
| 4. Configs do sistema | pacotes, `docker ps`, versão, rede, crontabs | raramente falha; é a fonte do inventário do próximo restore |
| 5. Sincronização para o host de backup | `rsync` do diretório temporário | não roda se 1-4 abortaram |
| 6. Retenção | apaga pastas mais velhas que N dias no destino | §4 |

### 3.1 A variável "documentada" que o código não lê

**Leia a task que consome a variável, não a variável.** Duas ocorrências reais na
mesma role:

- Uma lista de diretórios a backupear era testada apenas por veracidade
  (`| length > 0`) e a task tarava um caminho **fixo**, ignorando o conteúdo.
  Alguém acrescentou o caminho certo à lista, e nada mudou. Foi assim que
  definições de três serviços ficaram fora do backup.
- Uma lista de volumes em inventário não é lida por task nenhuma — o script
  itera `docker volume ls` e pega tudo que existir no host. A lista é
  documentação, não configuração.

O segundo caso é benigno (a cobertura é maior que a lista) e o primeiro é grave,
mas o erro de leitura é o mesmo: presumir que uma variável declarada está sendo
consumida.

### 3.3 `docker volume ls` não enxerga bind mount

O item anterior conforta com "o script itera `docker volume ls` e pega tudo que
existir no host". Isso vale para **volume nomeado**. Um container montado via
**bind mount** (`-v /opt/algum/dir:/data`, ou `type: bind` no compose) guarda os
dados num caminho do host que **não** aparece em `docker volume ls` — logo, o
script de volumes passa por cima dele sem tarar nada, e sem reclamar.

O engano é cruel porque a metade visível funciona: num caso real, os dumps de
banco dos dois wikis estavam presentes no backup, o que dava toda a aparência de
cobertura — mas os **26 GB de imagens/uploads** desses wikis moravam num bind
mount (`/opt/containers/<app>/…`) e ficaram de fora. Banco sem as mídias devolve
um wiki de texto com todas as figuras quebradas.

É a mesma classe da postura "não existe em backup só dentro das origens que você
enumerou": o dado estava num lugar que a ferramenta não olha. Para achar os bind
mounts antes que o restore os procure:

```bash
docker ps -q | xargs -r docker inspect \
  --format '{{"{{.Name}}"}} {{"{{range .Mounts}}{{if eq .Type \"bind\"}}{{.Source}}->{{.Destination}} {{end}}{{end}}"}}'
```

Cada `Source` de bind mount com dado insubstituível é um caminho que o backup de
volumes **não** cobre — trate-o como diretório a incluir explicitamente (com a
mesma checagem de existência do §2.4), não como algo que "o `volume ls` pega".

### 3.2 Renomear container é mudança de duas pontas

Se um restore renomeia um container, o inventário do backup **tem que mudar no
mesmo commit**. Não é higiene — é a causa raiz do incidente que abre este
arquivo. Ponha na definição de pronto do restore.

O mesmo vale para qualquer variável que referencie o container por nome em outro
lugar (senha lida por `selectattr`, por exemplo): um nome que não casa devolve
lista vazia, e um `| first` sobre lista vazia quebra a play em um lugar que não
tem nada a ver com o problema.

---

## §4. A aritmética da retenção

```
dias_de_retencao × tamanho_diario  ≤  espaço_livre_no_destino
```

Se não fecha, a retenção configurada é ficção — e ninguém descobre até o disco
encher, momento em que o backup para de proteger **tudo**, não só o que cresceu.

Meça de verdade, dos dois lados:

```bash
ssh root@<backup_host> 'df -h <backup_root>; du -sh <backup_root>/<servidor>/*'
```

Um restore bem-sucedido costuma **aumentar** o tamanho diário — é o objetivo,
afinal: dado que antes não era coberto passou a ser. Recalcule a conta depois de
cada restore, não antes.

Saídas, em ordem de preferência: excluir conteúdo derivado (§5), comprimir os
tars, dar cadência diferente aos volumes grandes, reduzir a retenção, aumentar o
disco. As três primeiras não perdem informação; as duas últimas são decisão do
dono, não sua.

---

## §5. Exclusões: a decisão de apagar dado para sempre

Uma linha de exclusão escrita uma vez remove aqueles caminhos de **todo** backup,
**todo dia**, sem nunca avisar. Se o dado morrer no servidor, ele não existe mais
em lugar nenhum — e a descoberta acontece anos depois, num restore.

Caso real: um script antigo trazia

```bash
tar --exclude={a,b,c,d} -cvf <saida>.tar <pasta>
```

A expansão de chaves gerou quatro exclusões literais, e elas **funcionaram
exatamente como escritas**. Só que uma delas casava com um diretório que não era
lixo: era o feed de auto-update de uma aplicação instalada em clientes. Ficou
fora de todos os backups por anos, e morreu na troca de discos — com os clientes
sem conseguir se atualizar até alguém reconstruir o caminho à mão.

> Detalhe que engana quem investiga: diretórios **vizinhos** com sufixo
> (`<nome>.bak-<data>`) sobreviveram, porque o padrão literal não casava com
> eles. Isso faz parecer que "as exclusões não funcionavam". Elas funcionavam;
> quem não casava era o vizinho.

### Regras

1. **Justifique por escrito, no próprio script**, ao lado da linha: por que este
   caminho é descartável, e como se regenera.
2. **Só exclua conteúdo derivado** — cache de página, thumbnails regeneráveis,
   logs de aplicação, perfis de navegador headless. Se você não sabe dizer o
   comando que o reconstrói, não é derivado.
3. **Ancore o padrão.** `--exclude='./caminho/exato'` em vez de um nome solto que
   casa em qualquer profundidade.
4. **Nunca exclua por tamanho.** "É grande" não é sinônimo de "é descartável" —
   costuma ser o oposto.
5. Ao herdar um script com exclusões, **liste o que elas removem hoje** antes de
   confiar nelas:

```bash
tar -cvf /dev/null --exclude=<padrao> <pasta> 2>/dev/null | wc -l   # com
tar -cvf /dev/null <pasta> 2>/dev/null | wc -l                      # sem
```

A diferença é exatamente o que você está decidindo perder.
