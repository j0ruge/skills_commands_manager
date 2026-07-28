---
name: ansible-docker-backup-restore
metadata:
  version: 1.0.0
description: Back up and restore a Linux server's Docker services with Ansible — volume tars, pg_dump/mysqldump, snapshot-guarded overwrite, and proof the nightly backup still runs. Catches silently dead backups: stale host_vars, ignore_errors+no_log. Triggers — ansible, playbook, backup, restore, disaster recovery, volume snapshot, mysqldump, retention.
---

# Backup e restore de serviços Docker via Ansible

Procedimento validado em produção: um servidor levado de 7 a 30 containers após
troca de discos, com zero perda de dados — e, na sequência, o conserto do backup
daquele mesmo servidor, que estava morto havia dias sem ninguém perceber.

**As duas metades são um ciclo só, e é por isso que moram na mesma skill.** Foi
um restore que quebrou o backup (um container renomeado, um `host_vars` que não
acompanhou), e foi uma lacuna antiga do backup que decidiu o que o restore
conseguiu recuperar. Tratá-las separado é como o incidente nasce.

> Este documento é a espinha: regras que valem sempre, ordem de execução e os
> dois gates obrigatórios. O detalhe vive em `references/` — cada seção abaixo
> diz **em que momento** abrir cada arquivo. Não tente executar de cabeça; as
> validações existem porque a ausência de cada uma causou um incidente real.

---

## REGRAS INVIOLÁVEIS

Violar qualquer uma causa perda de dado ou derruba produção.

| # | Regra | Por quê |
|---|---|---|
| 1 | Nunca `docker compose … --remove-orphans` | Apaga containers de outro projeto que colidam no nome. Num caso real teria deletado uma API de produção. |
| 2 | Nunca recriar a rede do proxy reverso | Ela carrega todos os containers em execução; recriar desconecta tudo. Guarde o ID completo no início e confira no fim. |
| 3 | Nunca sobrescrever volume com dados sem snapshot antes | Ver `references/restore-volumes-e-guarda.md`. A guarda existe para isso. |
| 4 | Nunca gravar credencial em arquivo do repositório | Leia segredos de inventário já existente ou do servidor em tempo de execução. Um subagente já fez isso sem autorização. |
| 5 | Nunca trocar versão ou origem de imagem por conta própria | Se a imagem sumiu do registry, **pare e pergunte**. Trocar publicador é decisão do dono. |
| 6 | `tar -xf`, nunca `-xzf`, e **nunca** `--strip-components` em tar de volume | Tars de volume costumam ser POSIX puros com entradas `./`. Confirme com `file` — há scripts que geram gzip com extensão `.tar`. |
| 7 | Reporte o que observou, não o que esperava | Cole a saída real. E `PLAY RECAP` com `failed=1` **não é sucesso**, mesmo que um `; echo $?` encadeado devolva 0 — o `$?` passa a ser o do último comando da cadeia. |
| 8 | Nenhum container declara `VIRTUAL_HOST` antes de você ler `vhost.d/<dominio>` inteiro | Um arquivo órfão ali derruba **todos** os domínios HTTPS do host de uma vez. Gate obrigatório — ver abaixo. |
| 9 | Nunca `ignore_errors: true` junto com `no_log: true` na mesma task | Um esconde o erro, o outro esconde a mensagem. É assim que um backup morre em silêncio. |
| 10 | Toda exclusão de backup é uma decisão de apagar dado **para sempre** | Justifique por escrito no próprio script antes de acrescentar uma. Uma lista escrita uma vez remove aqueles caminhos de todo backup, todo dia, sem avisar. |
| 11 | Nome genérico em ambiente compartilhado é colisão esperando acontecer | Vale para nome de projeto compose (prefixo de volume) e para service key (vira alias DNS). `db`, `app`, `web`, `node`, `postgres` já colidiram de verdade. |

### Uma postura, não uma regra

**"Não existe em backup" só é verdade dentro do conjunto de origens que você
enumerou por escrito.** Antes de declarar um dado perdido, liste as origens
varridas e pergunte quais existem fora dela — scripts de backup próprios,
sincronizações para nuvem, cópias manuais de alguém. Um site inteiro foi dado
como perdido depois de varrer quatro origens; estava numa quinta, criada por um
script que ninguém tinha aberto.

---

## Roteamento — quando abrir cada reference

Leia a linha que descreve o que você está prestes a fazer.

| Você vai… | Abra antes |
|---|---|
| começar qualquer coisa | `references/levantamento-e-escopo.md` |
| escrever ou rodar o primeiro playbook | `references/ambiente-e-armadilhas-ansible.md` |
| escrever em qualquer volume, ou subir um compose | `references/restore-volumes-e-guarda.md` |
| importar um dump SQL | `references/restore-bancos.md` |
| **declarar `VIRTUAL_HOST` ou mexer em TLS** | `references/proxy-reverso-e-tls.md` — **gate** |
| **encerrar um restore, ou desconfiar de um backup** | `references/backup-pipeline-e-falha-silenciosa.md` — **gate** |
| reportar resultado, ou despachar subagente | `references/provas-que-nao-mentem.md` |

Em `assets/` há um contrato de variáveis, a guarda anti-sobrescrita comentada e
um script de backup de volumes — pontos de partida, não código para colar sem
ler. Em `scripts/check-backup-freshness.sh` há uma checagem somente-leitura de
"o backup de hoje existe e está completo".

---

## Ordem de execução

1. **Proxy reverso e companion de TLS** — sem eles nenhum domínio funciona. Se
   já estiverem no ar, **não toque**.
2. **Painel de administração** (Portainer ou equivalente) — note que stacks
   podem reaparecer sozinhas.
3. **Bancos de dados** antes das aplicações que dependem deles.
4. **O serviço mais simples primeiro**, para validar a role ponta a ponta:
   compose já no disco, sem volume nomeado, sem build. Só depois os que exigem
   build ou compose reconstruído.
5. Demais serviços por criticidade de negócio.

Rode **um serviço por vez** e verifique antes de seguir. Verificação que aceita
"provavelmente subiu" não é verificação — `references/provas-que-nao-mentem.md`.

---

## Gate 1 — antes de qualquer `VIRTUAL_HOST`

Um proxy reverso orientado a container inclui automaticamente o arquivo de
configuração por domínio (`vhost.d/<dominio>` ou equivalente) no bloco daquele
vhost. Enquanto nenhum container declara o domínio, o arquivo **não é incluído**
— então `nginx -t` passa e o problema fica invisível.

O risco: diretórios de config do proxy costumam ter **montagens assimétricas**.
Um deles é volume e sobrevive à troca de discos; outro não é, e morre. Se o que
sobreviveu referencia algo que o que morreu definia, você tem uma referência
órfã armada. Ao subir o container, o proxy recusa a config inteira; o reload
para de ser aplicado **para todos os serviços**, e no próximo restart ele entra
em crash loop e derruba todos os domínios juntos.

Antes de declarar o domínio: leia `references/proxy-reverso-e-tls.md`, leia o
arquivo de vhost **inteiro** e prove que toda diretiva ali tem definição viva.
Depois que o container subir, `nginx -t` (ou equivalente) é **asserção dura**,
não aviso.

## Gate 2 — restore não termina sem backup provado

**Um backup que ninguém verifica não é um backup.** O caso que originou esta
skill: o backup de um servidor ficou dias sem completar, e o que denunciou foi
acaso — nenhum alerta, nenhuma falha visível. A causa raiz foi o próprio
restore, que renomeou um container sem atualizar o inventário no mesmo commit.

Por isso, o restore **não está pronto** quando os serviços sobem. Está pronto
quando:

1. o playbook de backup rodou **ponta a ponta** e o `PLAY RECAP` mostra
   `failed=0`;
2. o backup do dia existe no destino, com dump de **cada** banco esperado e
   contagem de volumes compatível — `scripts/check-backup-freshness.sh`;
3. a aritmética da retenção fecha: `dias × tamanho_diário` cabe no espaço livre
   do destino. Se não cabe, a retenção configurada é ficção e alguém vai
   descobrir isso quando o disco encher.

Abra `references/backup-pipeline-e-falha-silenciosa.md` e siga.

---

## Encerramento

1. **Smoke test global** — um playbook que confere todos os containers e todos
   os domínios esperados, e que **reporta explicitamente** os que estão
   sabidamente imperfeitos em vez de escondê-los atrás de um sucesso genérico.
2. **Corrija a causa raiz do backup.** Se alguma definição se perdeu, é porque
   estava fora do escopo do backup. Acrescente o caminho — e **confira se a
   variável é de fato consumida pelo código**, não apenas declarada.
3. **Versione o que foi reconstruído**, com data, causa e aviso de não reverter
   (especialmente troca de namespace de imagem).
4. **Documente o que ficou quebrado** no cabeçalho do próprio playbook, não só
   num relatório. Serviço que sobe mas não serve precisa dizer por quê.
5. **Migre segredos para `ansible-vault`** antes de qualquer `git remote add`.
   Senha em texto claro no histórico não sai apagando a linha — exige reescrever
   com `git filter-repo`. E há uma armadilha: uma senha **fraca igual a um
   identificador público** (nome de schema ou de container) **não** pode ser
   removida por substituição literal — apagar o valor apagaria o identificador em
   toda parte. Discriminador: o valor aparece na árvore do HEAD? Se sim, é
   identificador, e o único conserto é **rotacionar** a senha, não reescrever.
   Guarde um bundle da história antiga antes de reescrever; ele contém os
   segredos, então apague-o depois de confirmar o remote.

---

## Checklist rápida

```
RESTORE
[ ] inventário do que roda hoje lido; contagem, volumes e ID de rede anotados
[ ] TODAS as imagens validadas com `docker manifest inspect` antes de começar
[ ] origens de backup ENUMERADAS por escrito antes de declarar algo perdido
[ ] nome de projeto compose explícito, derivado do PREFIXO DO VOLUME
[ ] guarda anti-sobrescrita testada em volume descartável
[ ] conteúdo do dump conferido antes de assumir nome de banco
[ ] vhost.d lido inteiro ANTES do primeiro VIRTUAL_HOST; `nginx -t` depois
[ ] verificação por corpo da resposta, não só por código HTTP
[ ] contagem de containers e ID de rede idênticos ao esperado no fim

BACKUP — o restore não terminou sem isto
[ ] inventário revisto no MESMO commit que renomeou qualquer container
[ ] nenhuma task com `ignore_errors` e `no_log` juntos
[ ] preflight confere `docker ps` vs inventário nos DOIS sentidos (declarado-ausente falha; em-execução-não-declarado avisa)
[ ] bind mounts com dado insubstituível incluídos à mão — `docker volume ls` não os enxerga
[ ] push cliente→host de backup verificado DESTE host (não generalizado de outro)
[ ] acesso de push com menor privilégio: chave dedicada + `rrsync -wo`, provada sem abrir shell
[ ] playbook de backup rodado ponta a ponta, PLAY RECAP com failed=0
[ ] backup do dia no destino: um dump por banco esperado, volumes conferidos
[ ] toda exclusão justificada por escrito no script
[ ] aritmética da retenção conferida contra o espaço livre real
```
