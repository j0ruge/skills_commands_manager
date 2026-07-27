# Proxy reverso e TLS — o gate antes de declarar um domínio

**Gate obrigatório.** Nenhum container declara `VIRTUAL_HOST` (ou equivalente)
antes de você ter lido este arquivo e o vhost do domínio inteiro.

O padrão em questão: um proxy reverso orientado a container (docker-gen +
nginx-proxy e parentes) observa os containers, gera a configuração e recarrega
sozinho. Um companion de ACME cuida dos certificados. É conveniente — e a
conveniência é exatamente o que torna as falhas abaixo invisíveis até tarde.

---

## 1. Montagens assimétricas criam referência órfã armada

Esses proxies leem configuração de mais de um diretório, e **nem todos costumam
ser volume**. Um sobrevive à troca de discos, outro morre. Se o que sobreviveu
referencia algo que o que morreu definia, você tem uma bomba armada.

Caso real, e o raio de alcance é o host inteiro:

- `vhost.d/<dominio>` — **é volume**, sobreviveu. Terminava com uma diretiva de
  limite de requisição referenciando uma zona nomeada.
- `conf.d/` — **não é volume**, morreu. Era lá que a zona era definida (a
  diretiva que define zona é de contexto `http`, e por isso não podia morar no
  arquivo de vhost).

`nginx -t` passava. Passava porque, sem nenhum container declarando aquele
domínio, o proxy não incluía o arquivo de vhost na configuração gerada — a
referência órfã não era lida por ninguém.

No instante em que um container declarasse o domínio, o gerador incluiria o
arquivo e o nginx recusaria a configuração **inteira**:
`[emerg] unknown limit_req_zone "…"`. A partir daí:

- **imediato** — o reload é recusado, o serviço novo nunca sobe, e todo reload
  futuro do gerador para de ser aplicado, em silêncio, **para todos os
  serviços**;
- **no próximo restart do proxy** (que normalmente roda com `--restart always`)
  — ele lê a config do disco, falha no `[emerg]` e entra em **crash loop**,
  derrubando **todos** os domínios HTTPS do host de uma vez.

### O procedimento

```bash
# 1. Que diretórios de config são volume, e quais não são?
docker inspect <proxy> --format '{{range .Mounts}}{{.Destination}} <- {{.Source}}{{println}}{{end}}'

# 2. Leia o vhost do domínio INTEIRO — não faça grep pelo que você espera achar
docker exec <proxy> cat /etc/nginx/vhost.d/<dominio>

# 3. Toda diretiva ali tem definição viva?
docker exec <proxy> grep -rn '<diretiva_que_define>' /etc/nginx/
```

Depois que o container subir, `nginx -t` é **asserção dura**, não aviso:

```yaml
- name: Validar a config do proxy depois de o vhost entrar
  ansible.builtin.command: docker exec <proxy> nginx -t
  register: t
  changed_when: false
  failed_when: false

- ansible.builtin.assert:
    that: t.rc == 0
    fail_msg: |
      A config do proxy ficou inválida. Ele está rodando com a config antiga em
      memória e o PRÓXIMO RESTART derruba todos os domínios.
      Aja agora: pare o container novo para o gerador retirar o include.
```

Se você precisar remover uma diretiva órfã, **registre por escrito no próprio
arquivo** por que ela saiu e o que seria necessário para trazê-la de volta.
Diretiva de contexto `http` não volta num arquivo de vhost, nem num diretório
incluído em contexto main — exige mudar o que é volume, ou imagem própria.

---

## 2. O certificado pode sobreviver sem o estado do cliente ACME

Os arquivos PEM e o **estado do cliente ACME** vivem em lugares diferentes, e
podem ter destinos diferentes num desastre.

```bash
docker exec <companion> ls /etc/acme.sh/default/      # há pasta para o domínio?
docker exec <companion> ls -la /etc/nginx/certs/<dominio>/
```

Se os PEM existem mas **não há estado do ACME** para o domínio, o companion não
faz "skip renewal": ele tenta **emitir do zero**. E na implementação típica, a
criação dos symlinks planos (`<dominio>.crt`, `<dominio>.key`) só acontece se a
emissão retornar sucesso. Emissão falha ⇒ symlinks nunca aparecem ⇒ o proxy não
encontra certificado para o vhost ⇒ o domínio cai no certificado padrão
autoassinado. Com a aplicação forçando HTTPS, o resultado é o site inteiro fora.

**Tire o ACME do caminho crítico**: crie os symlinks à mão antes de subir,
exatamente no formato que o companion usa.

```bash
ln -s ./<dominio>/fullchain.pem  <certs>/<dominio>.crt
ln -s ./<dominio>/key.pem        <certs>/<dominio>.key
ln -s ./<dominio>/chain.pem      <certs>/<dominio>.chain.pem
ln -s ./dhparam.pem              <certs>/<dominio>.dhparam.pem
```

A função de criação de link do companion é idempotente quando o symlink já
aponta para o mesmo destino, então isso não conflita com a renovação futura.
Confira antes que o certificado ainda é válido e cobre os nomes que você vai
declarar:

```bash
openssl x509 -in <certs>/<dominio>/cert.pem -noout -subject -dates -ext subjectAltName
```

Se você declarar mais de um nome, **mantenha o nome-base primeiro na lista** — é
dele que o companion deriva o diretório do certificado.

---

## 3. Service key genérica vira alias DNS colidente

Coberto em `restore-volumes-e-guarda.md` §1. Repetido aqui porque o sintoma
aparece do lado da rede: uma aplicação que conecta ora no banco certo, ora em
outro, sem padrão. Confira os aliases da rede antes de culpar a aplicação.

---

## 4. Defaults do proxy que mordem

| Default | Sintoma | Correção |
|---|---|---|
| `client_max_body_size` não é definido pelo proxy | Upload acima de **1 MB** morre em 413 antes de chegar na aplicação, mesmo com o runtime configurado para muito mais | Acrescente a diretiva no `vhost.d/<dominio>` |
| Redirecionamento HTTP→HTTPS na borda | `curl` em `:80` devolve 301 sem nunca contatar o container | Verifique na 443 com SNI — ver `provas-que-nao-mentem.md` |
| Certificado só aparece quando um container declara o domínio | Domínio "sem certificado" que na verdade só está sem vhost | Ver §2 |
