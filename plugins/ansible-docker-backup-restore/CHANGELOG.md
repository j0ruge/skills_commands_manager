# Changelog — ansible-docker-backup-restore

Formato: [Semantic Versioning](https://semver.org/)

## [1.1.0] — 2026-07-28

### Adicionado

Quarta sessão sobre o mesmo servidor e um segundo servidor irmão que **nunca
tinha tido backup**. Os bloqueadores dele estavam empilhados — três, cada um
escondendo o próximo — e três das lições abaixo saíram de desempilhá-los. Nada
que a 1.0.0 já cobria foi reescrito; estas são as bordas novas.

- **`backup-pipeline-e-falha-silenciosa.md` §2.5 — o caminho de push nunca foi
  estabelecido.** A etapa de rsync pressupõe que o cliente alcança o host de
  backup por SSH. Num host isso simplesmente não valia (`Host key verification
  failed` → `Permission denied`), e o engano que escondeu foi generalizar de
  *outro* cliente onde o push funcionava. A topologia de SSH é por par de hosts:
  verifique o push de **cada** cliente. E conceda o acesso com menor privilégio —
  chave dedicada confinada por `rrsync -wo`, **provada** sem poder de shell —
  porque autorizar a chave root ampla do cliente faz do host de backup um alvo de
  movimentação lateral para os backups de todos os servidores.
- **`backup-pipeline-e-falha-silenciosa.md` §2.1 (estendido) — preflight nos dois
  sentidos.** Além de "declarado e ausente falha", agora "em execução e **não
  declarado** avisa": um banco que nunca entrou no inventário não é dumpado por
  ninguém e nada dá erro. O preflight achou dois bancos de produção em execução e
  nunca dumpados.
- **`backup-pipeline-e-falha-silenciosa.md` §3.3 — bind mount escapa do
  `docker volume ls`.** O script de volumes itera `docker volume ls` e por isso
  **não** enxerga bind mount. Os dumps de banco presentes davam aparência de
  cobertura, mas dezenas de GB de mídia num bind mount ficavam de fora.
- **`ambiente-e-armadilhas-ansible.md` §6 — `delegate_to` num arquivo
  compartilhado corre.** Vários hosts delegando edição do mesmo `authorized_keys`
  se sobrescrevem; `throttle: 1` serializa.
- **`SKILL.md` Encerramento #5 (estendido) — reescrita de histórico.** Uma senha
  fraca igual a um identificador público (schema/container) não sai por
  substituição literal; só rotação resolve. Discriminador: o valor aparece na
  árvore do HEAD?

## [1.0.0] — 2026-07-27

### Adicionado

Primeira versão. Consolida o aprendizado de três sessões de recuperação de um
servidor Linux Dockerizado — a restauração em si e, na sequência, o conserto do
backup daquele mesmo servidor, que estava morto havia dias sem ninguém perceber.

**A skill cobre as duas metades de propósito.** Foi um restore que quebrou o
backup (um container renomeado, um inventário que não acompanhou), e foi uma
lacuna antiga do backup que decidiu o que o restore conseguiu recuperar.
Separá-las é como o incidente nasce.

- **`SKILL.md`** — espinha com 11 regras invioláveis, tabela de roteamento
  para as references, ordem de execução e **dois gates obrigatórios**: nenhum
  `VIRTUAL_HOST` antes de auditar o vhost do domínio, e nenhum restore dado por
  encerrado antes de o backup rodar ponta a ponta com `failed=0`.
- **`references/backup-pipeline-e-falha-silenciosa.md`** — as quatro formas de
  um backup morrer calado: `ignore_errors` + `no_log` na mesma task (esconde o
  erro *e* a mensagem); a mesma causa numa task sem `ignore_errors` (aborta a
  play e parece lentidão); `set -euo pipefail` com `tar` devolvendo rc=1 num
  datadir vivo (mata o script, e a ordem alfabética dos volumes faz parecer
  intermitente); caminho fixo ausente derrubando a play inteira. Mais a
  aritmética da retenção e o capítulo sobre exclusões.
- **`references/proxy-reverso-e-tls.md`** — montagens assimétricas de config do
  proxy criam referência órfã armada: o diretório que é volume sobrevive, o que
  não é morre, e `nginx -t` passa até alguém declarar o domínio. Nesse instante
  o proxy recusa a config inteira e o próximo restart derruba **todos** os
  domínios HTTPS do host. Mais: o PEM do certificado pode sobreviver sem o
  estado do cliente ACME, e a criação dos symlinks planos só acontece se a
  emissão der certo.
- **`references/restore-volumes-e-guarda.md`** — a armadilha do nome de projeto
  compose (silenciosa: cria volume vazio e o serviço sobe sem erro), a mesma
  armadilha na camada de rede (service key genérica vira alias DNS colidente), a
  guarda anti-sobrescrita em 8 passos, bind mount de arquivo único, e por que
  ler o entrypoint da imagem antes de montar volume pré-populado.
- **`references/levantamento-e-escopo.md`**, **`restore-bancos.md`**,
  **`ambiente-e-armadilhas-ansible.md`**, **`provas-que-nao-mentem.md`** — a
  metade de restore, incluindo a postura que ficou na espinha: *"não existe em
  backup" só é verdade dentro das origens que você enumerou por escrito*.
- **`assets/`** — contrato de variáveis, a guarda anti-sobrescrita comentada
  passo a passo, e um script de tar de volumes com o tratamento de rc=1.
- **`scripts/check-backup-freshness.sh`** — checagem somente-leitura de "o
  backup de hoje existe e está completo": buracos na sequência de datas, um dump
  por banco, dumps pequenos demais, cobertura de volumes e a conta da retenção
  contra o espaço livre real. Na primeira execução contra um host real ele achou
  um buraco de três dias que tinha passado despercebido.

### Notas

Todo o conteúdo é agnóstico: nenhum nome de servidor, domínio, container,
volume ou endereço de rede de qualquer ambiente específico. Os casos reais estão
descritos pelo mecanismo, com placeholders — o que faz a lição transferir, e
mantém fora deste repositório o que pertence ao repositório de infraestrutura de
onde ela veio.
