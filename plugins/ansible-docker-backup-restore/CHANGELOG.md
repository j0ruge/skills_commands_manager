# Changelog — ansible-docker-backup-restore

Formato: [Semantic Versioning](https://semver.org/)

## [1.3.0] — 2026-08-08

Sexta sessão, e o achado veio de fora: durante um deploy de produção **de outro
produto** no mesmo host, o container de backup do ERP e do IdP estava `unhealthy`
desde 06/05/2026 e **nunca havia gerado um único dump** — três meses.

### Adicionado

- **`backup-pipeline-e-falha-silenciosa.md` §1.1 — tamanho é proxy fraco.**
  **O quê**: três perguntas em ordem de custo — `gzip -t` (integridade), contar
  `^COPY public` (há dados?) e procurar **um registro conhecido** (é este banco?).
  **Por quê**: a skill parava na heurística de tamanho (`-size -1k`, "um dump que é só
  a mensagem de erro tem poucos bytes"), que pega o caso grosseiro e deixa passar o
  inverso — **um dump só com o schema é grande, bem formado e inútil para restaurar**.
  `CREATE TABLE` de cem tabelas dá dezenas de KB sem uma linha de dado. A terceira
  pergunta é a única que distingue "dump válido" de "dump **deste** banco": aponte o
  `pg_dump` para o cluster errado, ou para um homônimo vazio, e as duas primeiras
  passam. Fica no §1 e não no §2 de propósito — as quatro formas de morrer calado do
  §2 são falhas *do pipeline*; aqui a play saiu `failed=0`, o arquivo está no lugar e
  no horário certo, e não serve.
- **`backup-pipeline-e-falha-silenciosa.md` §1.2 — o healthcheck de um container de
  backup mede a coisa errada.** **O quê**: quando o backup é container dedicado
  (`prodrigestivill/postgres-backup-local` e parentes) em vez de play Ansible, forçar
  um ciclo e olhar o artefato; mais as duas armadilhas de configuração (lista CSV só
  faz fan-out em `POSTGRES_DB`; tag da imagem ≥ versão do servidor). **Por quê**: o
  healthcheck dessas imagens observa a **porta HTTP de status que elas expõem**, não o
  arquivo. O container fica genuinamente `healthy` — o servidorzinho dentro dele está
  no ar — enquanto o `pg_dump` falha todas as noites. No caso real a lista CSV estava
  em `POSTGRES_HOST`/`POSTGRES_USER`, onde o valor é literal, então o `pg_dump`
  autenticava com o usuário `erp,zitadel`. O banco desprotegido era o do IdP que
  autenticava todos os outros serviços do host.
- **`provas-que-nao-mentem.md` §4b — a ausência de sinal também não prova nada.**
  **O quê**: vazio é produzido por dois mundos indistinguíveis (nada aconteceu / o
  instrumento nunca esteve vivo), e a cura é provocar um positivo que você mesmo
  causou. **Por quê**: o arquivo cobria só o gêmeo oposto — sinal positivo enganoso
  (§1 "um 301 não prova nada", §4 "um 200 também pode mentir"). Falta que aplica às
  próprias verificações desta skill: `find … -size -1k` sem resultado prova que não há
  dump pequeno **ou** que o caminho está errado e não há dump nenhum. Pergunta única
  que resolve: *"isto teria me mostrado um positivo?"*

### Alterado

- **`scripts/check-backup-freshness.sh`** ganha `gzip -t` por dump e detecção de
  dumps **schema-only** (zero blocos `COPY`), ambos somente-leitura, mais uma nota
  sobre `pg_restore -l` para dumps em formato custom. A terceira prova (registro
  conhecido) fica como `note` deliberadamente: não é automatizável sem conhecer o
  domínio, e automatizá-la com um valor genérico daria falsa confiança.
- **Gate 2 ganha um passo** (o antigo 3 vira 4): "cada dump abre e contém dados",
  com o corolário do registro conhecido, e uma nota de que `healthy` de container de
  backup não é evidência. Quatro linhas novas na checklist rápida.
- `description`: acrescenta a prova por conteúdo e a desconfiança do healthcheck.

## [1.2.0] — 2026-07-29

### Adicionado

Quinta sessão. Um serviço que todos davam por restaurado havia quatro dias
estava, na verdade, quebrado em dois lugares — e **as duas falhas passaram por
um playbook verde**. As lições abaixo saem de descobrir por que a verificação
não pegou nenhuma das duas.

- **`restore-bancos.md` §5 — o datadir traz o PLUGIN de autenticação, não só a
  senha.** O §4 já cobria a senha de um volume MySQL pré-populado. Faltava o
  atributo que viaja junto: usuários vindos de um datadir restaurado num MySQL 8
  chegam com `caching_sha2_password`, e clientes antigos (`DBD::mysql`, `mysqli`
  velho, JDBC antigo) não fecham esse handshake sem TLS — a conexão é recusada
  **com a senha inteiramente correta**. Duas armadilhas específicas: a flag
  `--default-authentication-plugin` do compose *não* corrige (só vale para
  usuários criados depois dela, e os do datadir já chegam prontos), e o sintoma
  aparece em um cliente e não em outro — a interface web seguia no ar porque o
  driver do PHP fala `caching_sha2`, enquanto o endpoint dos agentes, em Perl,
  não conectava. Corrigir só o plugin, preservando a mesma senha, e confirmar
  antes **de onde** a aplicação lê usuário e senha: num caso real o usuário
  efetivo vinha de outro arquivo, carregado depois na ordem alfabética do
  diretório de configs. Corrigir a credencial do usuário errado não produz erro
  nenhum — só continua sem funcionar.

- **`provas-que-nao-mentem.md` §4 — promova a prova de conteúdo a contrato da
  role.** Esta seção já existia e já citava o domínio real que servia a página
  padrão do servidor web. Ele passou mais quatro dias servindo exatamente isso,
  num restore que terminou verde o tempo todo. A nota estava escrita, foi lida, e
  não impediu nada — quem roda o restore confia no que a role afirma, não no que
  um documento sugere conferir. Daí `verify_body_contains` (default vazio =
  comportamento anterior, sem efeito nos playbooks existentes), agora também no
  contrato em `assets/restore-defaults.yml`. Corolário na mesma seção: **verifique
  todos os planos de entrada** — interface humana e endpoint de máquina quebram
  de forma independente, e o que fica de pé mascara o que caiu.

- **`provas-que-nao-mentem.md` §7 — o erro do log pode ser o secundário.** Rastro
  apontando para rotina de encerramento (`rollback`, `finally`, destrutor) quase
  sempre é o handler de erro estourando sobre recursos que a falha real impediu
  de existir. Caso real: `Can't call method "rollback" on an undefined value`
  descrevia a segunda vítima; a causa era conexão recusada. Agravante: o erro
  primário costuma estar **desligado por padrão** (log de diagnóstico em nível
  zero, impressão de erro do driver desabilitada). Ligar a verbosidade antes de
  teorizar — e revertê-la no mesmo script, porque ela vaza dado sensível.

- **`ambiente-e-armadilhas-ansible.md` §6 — `lineinfile` com `regexp` que não
  casa.** Não é erro: o módulo acrescenta a linha no fim do arquivo e reporta
  `changed`. Num arquivo com blocos, ela cai fora de todo contexto, fica inerte,
  e a task fica verde. Provar que a diretiva existe (`grep -c` + `assert`) antes
  de reescrevê-la.

### Corrigido

- `SKILL.md` declarava `metadata.version: 1.0.0` enquanto o `plugin.json` estava
  em `1.1.0`. As duas passam a ser espelhadas.

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
