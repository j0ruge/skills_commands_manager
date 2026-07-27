# Levantamento e escopo — antes de mudar qualquer coisa

Objetivo: saber o que existe antes de tocar em nada. Tudo que você anotar aqui
vira a linha de base de todas as verificações posteriores.

```bash
# Estado atual do servidor
ssh <user>@<servidor> 'sudo docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}" | sort'
ssh <user>@<servidor> 'sudo docker ps -q | wc -l'                        # GUARDE este número
ssh <user>@<servidor> 'sudo docker volume ls --format "{{.Name}}" | sort' # GUARDE esta lista
ssh <user>@<servidor> 'sudo docker network inspect <rede_proxy> --format "{{.Id}}"'  # GUARDE o ID COMPLETO
ssh <user>@<servidor> 'sudo docker images --format "{{.Repository}}:{{.Tag}}"'
ssh <user>@<servidor> 'df -h /'

# O que o backup realmente contém
ssh root@<backup_host> 'ls /opt/backups/<servidor>/'
ssh root@<backup_host> 'ls -la /opt/backups/<servidor>/<data>/{volumes,databases,containers,configs}/'
ssh root@<backup_host> 'cat /opt/backups/<servidor>/<data>/configs/containers.txt'
```

## 1. O inventário do momento do backup é a fonte da verdade

Um arquivo como `containers.txt` lista o que estava **realmente rodando** quando
o backup foi tirado. Use-o para decidir escopo, não a memória de ninguém.

Serviço que **não** está nessa lista já estava parado antes do incidente.
Restaurá-lo pode ser fora de escopo — e pode colidir com quem está no ar.

- Um serviço de wiki foi tratado como "a restaurar", mas não constava na lista,
  tinha banco com zero tabelas e `.env` com valores de exemplo: **nunca havia
  sido configurado**. Fazê-lo funcionar era instalação nova, não restore.
- Dois serviços opcionais estavam parados justamente porque colidiam de porta
  com um serviço de produção. Subi-los teria derrubado o que funcionava.

## 2. Enumere as origens de backup por escrito

**Antes de declarar qualquer dado perdido, escreva a lista de origens que você
varreu** — e depois pergunte quais existem fora dela.

Origens que costumam escapar de uma varredura "completa":

| Origem | Como costuma aparecer |
|---|---|
| Script de backup próprio, anterior à automação | mencionado só na documentação do serviço |
| Sincronização para nuvem (`rclone`, `rsync` para outro host) | dentro do script acima, com destino que ninguém abre |
| Cópia manual de alguém antes de uma migração | num diretório pessoal do servidor |
| Tarball antigo esquecido no host de backup | fora da árvore de datas |

Um site inteiro foi declarado perdido depois de varrer quatro origens
independentes. Estava numa quinta: um script próprio que enviava para
armazenamento em nuvem, fora do circuito da automação. **A conclusão não estava
errada — o conjunto de origens estava incompleto**, e ninguém tinha escrito qual
era esse conjunto.

## 3. Descubra o que o backup NÃO cobre

```bash
# Diretórios de topo dentro do tarball de código
ssh root@<backup_host> 'tar -tzf .../containers/containers_all.tar.gz | awk -F/ "{print \$1\"/\"\$2}" | sort -u'
```

Compare com o inventário. **O que estiver rodando mas não aparecer no tarball
nem nas stacks do painel teve a definição perdida.**

Cuidado com falso positivo de grep: buscar um nome curto de três letras casa com
qualquer palavra que o contenha (`docs/` casa com uma busca por `ocs`); buscar
um número casa com hash de objeto git e com timestamp de migration. Filtre antes
de concluir.

Três serviços moravam fora do diretório backupeado e não eram stacks do painel.
Seus composes não existiam em backup nenhum — só os dados. Foi preciso
reconstruí-los e passar a versioná-los.

## 4. Valide a disponibilidade de TODAS as imagens — antes de começar

**A validação mais barata e mais rentável do procedimento inteiro.** Consulta o
registry sem baixar nada.

```bash
for img in <todas as imagens do inventário e dos composes>; do
  echo -n "$img -> "
  ssh <user>@<servidor> "sudo timeout 30 docker manifest inspect '$img' >/dev/null 2>&1" \
    && echo DISPONIVEL || echo INDISPONIVEL
done
```

Numa única sessão, **dois fornecedores diferentes** tinham tornado imagens
indisponíveis, sem nenhuma relação com o incidente de disco: um moveu tags
fixadas para fora do namespace gratuito (o serviço quebraria no próximo pull de
qualquer forma), outro tornou o repositório privado.

Descobrir isso agora transforma horas de bloqueio numa lista de pendências
conhecida. **Se uma imagem sumiu: pare e pergunte ao dono.** Procure o namespace
novo e apresente a opção — trocar publicador de imagem não é decisão sua
(regra inviolável 5).

## 5. Onde as definições podem estar escondidas

| Local | Como olhar |
|---|---|
| Diretório de código | `tar -tzf containers_all.tar.gz` |
| Stacks do painel de administração | `/var/lib/docker/volumes/<vol_do_painel>/_data/compose/<id>/{docker-compose.yml,stack.env}` |
| Projeto upstream | Se o nome do projeto compose parece uma versão, procure o repositório oficial daquela versão |
| Dentro de imagem construída localmente | **Irrecuperável.** Arquivo que só existia numa imagem nunca publicada some com ela. |

Os arquivos de variáveis de cada stack (`stack.env` ou equivalente) precisam ser
copiados junto, renomeados para `.env`.

> A última linha da tabela é a que mais dói e a que mais se repete. Ao terminar
> qualquer restore, garanta que o dado passou a viver num **volume nomeado** — é
> a única categoria que a rotina de backup enxerga sozinha. Ver
> `backup-pipeline-e-falha-silenciosa.md`.
