# Importação de dumps SQL

Mesma filosofia da guarda de volumes: **só importa se o banco não tiver dado**, e
isso é decidido por **linhas numa tabela específica** — não por "o banco existe"
nem por "o schema existe".

Motivo real: um ORM criava o schema e as chaves estrangeiras sozinho ao subir.
Uma guarda por presença de schema diria "já tem dado" e o restore nunca
aconteceria.

## 1. Confira o CONTEÚDO do dump antes de assumir nomes

```bash
zcat <dump>.sql.gz | grep -iE "^(CREATE DATABASE|USE )" | head
zcat <dump>.sql.gz | grep -c "^CREATE TABLE"
```

- A documentação dizia que o dump continha duas bases com nomes conhecidos.
  Continha **uma**, com outro nome. Validar contra o nome errado teria reportado
  falha num restore correto.
- Um banco cujo nome citava um produto continha, na verdade, as tabelas de
  **outro** produto — herança de uma stack criada por copia-e-cola.

Repare também na **forma** do dump, porque ela decide o comando de importação:

| Forma | Como se reconhece | Importa com |
|---|---|---|
| `--all-databases` / `--databases` | tem `CREATE DATABASE` e `USE` | `mysql -u… -p…` sem nomear banco |
| schema único | cabeçalho diz `Database: <x>`, **sem** `CREATE DATABASE` | `mysql -u… -p… <banco>` — nomeando |

Entregar um dump de schema único a um comando que não nomeia o banco falha de
formas confusas, ou importa para o banco errado.

## 2. Postgres: importar "por cima" falha em silêncio

`pg_dumpall` pressupõe destino vazio e adiciona as FKs no fim. Se a aplicação já
criou schema e FKs, o `COPY` colide e **várias tabelas ficam vazias com
`rc=0`** — sucesso aparente, dado ausente.

Derrube e recrie o banco (`DROP DATABASE … WITH FORCE`) — **depois** de gravar e
conferir o dump de segurança do estado atual.

## 3. MySQL: a imagem sobe em duas fases

A imagem oficial inicia um servidor temporário de inicialização, encerra, e sobe
o definitivo. Há uma janela de poucos segundos em que nada aceita conexão, e
**`mysqladmin ping` responde para os dois servidores**. Uma checagem que caia
nessa janela aborta por falso positivo.

Use `until`/`retries`/`delay`, tolerando erro de conexão como transitório e
decidindo só em resultado definitivo (`rc == 0`, ou mensagem de tabela
inexistente):

```yaml
until: >-
  (check.rc == 0) or ("doesn't exist" in (check.stderr | default('')))
retries: 10
delay: 3
```

## 4. Senha em volume MySQL pré-populado

`MYSQL_ROOT_PASSWORD` só vale na **primeira** inicialização do datadir. Um volume
restaurado já traz a senha original gravada — o valor no compose precisa apenas
**coincidir** com ela.

Se não coincidir, **não reinicialize o volume** para "consertar": reporte a
divergência. Reinicializar apaga o banco.

## 5. O datadir também traz o PLUGIN de autenticação dos usuários

O item acima trata da senha. Existe um segundo atributo que viaja junto e que
quase ninguém confere: **o plugin de autenticação de cada usuário**.

Num datadir restaurado num MySQL 8, os usuários costumam vir com
`caching_sha2_password`. Clientes antigos — `DBD::mysql` do Perl, `mysqli`
velho, drivers JDBC antigos — não fecham esse handshake sem TLS, e a conexão é
recusada **com a senha inteiramente correta**:

```
Authentication plugin 'caching_sha2_password' reported error:
Authentication requires secure connection.
```

Duas armadilhas específicas:

**A flag do compose não corrige.** `--default-authentication-plugin=mysql_native_password`
só decide o plugin de usuários criados **depois** dela. Quem veio dentro do
datadir já chegou pronto, com o plugin gravado. A flag estar presente no compose
faz parecer que o assunto está resolvido — e não está.

**O sintoma aparece em um cliente e não no outro.** Caso real: a interface web
de um serviço funcionava normalmente (o driver do PHP fala `caching_sha2`)
enquanto o endpoint que recebe os agentes, em Perl, não conectava. Um serviço
com dois planos de entrada pode ter só um quebrado — e o plano que ficou de pé
esconde o outro. Como a UI abria, o banco parecia saudável e a investigação foi
para o lugar errado.

Confira o plugin, não só a senha:

```sql
select user, host, plugin from mysql.user;
```

Para corrigir, troque **apenas o plugin**, preservando a mesma senha — não
invente uma nova, e não reinicialize nada:

```
ALTER USER '<usuario>'@'%' IDENTIFIED WITH mysql_native_password BY <a MESMA senha>
```

Passe o valor por *stdin* do cliente `mysql`, não em `argv`, para não expô-lo no
`ps` do host. E antes de alterar qualquer coisa: **confirme de onde a aplicação
lê o usuário e a senha**. Num caso real o usuário efetivo não era o declarado no
arquivo principal de configuração — outro arquivo, carregado depois na ordem
alfabética do diretório de configs, sobrescrevia a variável. Corrigir a
credencial do usuário errado não produz erro nenhum: só continua sem funcionar.

## 6. Sempre reconfira depois de importar

Conte as linhas da tabela de checagem **de novo**, depois do import, e aborte se
continuar zero. Um import que devolve `rc=0` e deixa a tabela vazia é
exatamente o modo de falha do item 2 — e é indistinguível de sucesso sem essa
segunda contagem.

Guarde o dump de segurança do estado anterior antes de qualquer import
destrutivo, e cite o caminho dele na mensagem de erro: quem estiver lendo o
aborto às três da manhã precisa saber para onde correr.
