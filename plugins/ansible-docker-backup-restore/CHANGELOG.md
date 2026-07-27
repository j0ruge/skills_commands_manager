# Changelog — ansible-docker-backup-restore

Formato: [Semantic Versioning](https://semver.org/)

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
