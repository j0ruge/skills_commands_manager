# Verificação que não mente

Abra antes de reportar qualquer resultado, e antes de despachar subagente. Os
dois assuntos moram juntos porque são a mesma disciplina: **não aceitar como
prova aquilo que você não leu de uma saída real**.

---

## 1. Um 301 não prova nada

Proxies reversos com companion de TLS emitem **301 na borda**, sem jamais
contatar o container. Checar por HTTP:80 com header `Host` forjado só prova que
existe um vhost.

Faça a requisição chegar na aplicação:

```yaml
ansible.builtin.command: >
  curl -s -o /dev/null -w '%{http_code}'
  --resolve {{ verify_domain }}:443:127.0.0.1
  --max-time {{ verify_http_timeout }} -k
  https://{{ verify_domain }}/
register: http_check
changed_when: false
failed_when: false
retries: "{{ verify_http_retries }}"
delay: "{{ verify_http_retry_delay }}"
until: http_check.stdout not in verify_http_bad_codes
```

**Não use `-L`.** O `--resolve` fixa apenas o domínio alvo; um redirecionamento
para outro host seria seguido via DNS real e você acabaria verificando um
servidor externo.

## 2. Classifique em três faixas, não em duas

| Faixa | Significado | Ação |
|---|---|---|
| 2xx/3xx/4xx | Resposta real da aplicação (**401 e 403 são normais** em API autenticada; 404 é normal sem rota em `/`) | ok |
| 5xx que não é de gateway | **Erro de aplicação** — o proxy repassou e a aplicação respondeu mal | marcar `ATENÇÃO`; não derruba o restore |
| 502/503/504/000/vazio | Upstream inalcançável | falha real |

Não derrube um restore por checagem de domínio: DNS ou certificado propagando
não invalidam um restore bom. Mas **um 5xx não pode parecer sucesso no log**.

## 3. Retentativa é obrigatória

O gerador de configuração do proxy recarrega quando um container entra na rede, e
a checagem pode cair exatamente nessa janela. Dois serviços seguidos deram 502
transitório estando perfeitamente saudáveis.

## 4. Um 200 também pode mentir

Caso real: um domínio devolvia 200 — e era a **página padrão do servidor web**.
O container de proxy daquele serviço tinha perdido a configuração de roteamento;
a aplicação por trás estava íntegra. Um smoke test que só olha o código teria
reportado sucesso para sempre.

Quando o valor de retorno for suspeito — e "200 num serviço que você acabou de
restaurar sem configurar nada" é suspeito — confira o **corpo**:

```bash
curl -sk --resolve <dominio>:443:127.0.0.1 https://<dominio>/ | grep -ciE '<marca_da_aplicacao>'
# e a negação do impostor:
curl -sk … | grep -ci 'Welcome to nginx'
```

Para aplicação com rotas, exercite uma rota **real**, lida do banco ou da
configuração — não uma que você imaginou. Se a aplicação depende de reescrita de
URL, uma rota interna que responde 200 prova a reescrita; a raiz sozinha não
prova.

E teste por dentro, que isola o proxy do problema:

```bash
docker exec <container> curl -s -o /dev/null -w '%{http_code}' http://localhost:<porta>/<caminho_real>
```

## 5. Aguarde de verdade antes de asserir

Sem espera, a asserção de containers dispara logo após o `compose up` e **passa
segundos antes de o serviço morrer**. Caso real: uma API conectou no banco em
plena inicialização, saiu com código 139, e o Ansible reportou `failed=0`.

Se os containers não publicam porta no host, `wait_for` não serve — e pior, se
você apontar `wait_for` para uma porta que o **proxy** escuta, ele passa por
motivo errado. Use dependência real de prontidão:

```yaml
healthcheck:
  test: ["CMD-SHELL", "<comando_de_prontidao>"]
  interval: 5s
  timeout: 5s
  retries: 10
# no serviço dependente:
depends_on:
  <servico_base>:
    condition: service_healthy
```

**Um restore que só funciona na segunda tentativa está quebrado.** Teste sempre
a partir do zero: remova os containers e rode uma vez.

## 6. `PLAY RECAP` com `failed=1` não é sucesso

Encadear `ansible-playbook … ; echo $?` devolve o código do **último comando da
cadeia**, não o do playbook. Leia o RECAP.

E lembre que a etapa de verificação de uma role costuma ter `failed_when: false`
de propósito (item 2 acima) — o que significa que **ela nunca derruba a play**.
Toda prova que precisa bloquear tem que ser um `assert` explícito em
`post_tasks`, não uma expectativa sobre o resultado da role.

## 7. Se você delega a subagentes

Regras aprendidas por incidente real:

1. **Confira você mesmo os números críticos.** Um subagente reportou uma
   contagem de containers errada e um ID de rede que não existia; outro reportou
   um build bem-sucedido que nunca ocorreu.
2. **Exija a saída real**, com frase explícita no prompt: *"Reporte apenas
   valores que você leu diretamente da saída de um comando nesta sessão."*
3. **Um implementador por vez** mexendo em containers — dois em paralelo
   invalidam qualquer verificação de contagem.
4. **Diga explicitamente o que NÃO fazer.** Sem instrução, um subagente gravou
   senha de produção num arquivo do repositório.
5. **Mande reportar falha honestamente**: *"Se falhar, reporte o erro real. Não
   afrouxe a verificação para forçar aprovação, e não altere o código da
   aplicação para o build passar."*
6. **Verifique achado por achado, não o relatório inteiro.** Numa revisão real,
   um subagente errou dois pontos secundários e acertou três bloqueadores de
   produção. Aceitar em bloco teria trazido os erros; descartar em bloco teria
   custado o servidor.
