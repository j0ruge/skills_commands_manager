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

### Escreva isso como contrato da role, não como conselho

A lição aqui é sobre o formato do conhecimento, não sobre HTTP. Caso real: a
recomendação de conferir o corpo estava documentada e tinha sido lida, e mesmo
assim um domínio passou **quatro dias** servindo a página padrão do servidor
web, num restore cujo playbook terminou verde o tempo todo. A nota não impediu
nada: quem roda o restore confia no que a role afirma, não no que um documento
sugere conferir.

Então promova a prova de conteúdo a **variável do contrato**, com default vazio
para não mexer nos playbooks que já existem:

```yaml
verify_body_contains: ""   # vazio = só o código HTTP (comportamento anterior)
```

```yaml
- name: "[verify] Baixar o corpo e conferir a marca da aplicação"
  ansible.builtin.command: >
    curl -sS -L --resolve {{ verify_domain }}:443:127.0.0.1
    --max-time {{ verify_http_timeout }} --max-redirs 5 -k
    https://{{ verify_domain }}/
  register: body_check
  changed_when: false
  failed_when: false
  when: verify_domain | length > 0 and verify_body_contains | length > 0

- name: "[verify] Abortar se o corpo não contém a marca da aplicação"
  ansible.builtin.fail:
    msg: |
      {{ verify_domain }} respondeu, mas o corpo não contém
      "{{ verify_body_contains }}" — vhost apontando para o container errado, ou
      para um container que subiu sem a config dele.
      Recebido: {{ (body_check.stdout | default('(vazio)', true))[:300] }}
  when:
    - verify_domain | length > 0
    - verify_body_contains | length > 0
    - verify_body_contains not in (body_check.stdout | default('', true))
```

Aqui o `-L` é correto e no item 1 não era: a marca pode estar depois de um
redirecionamento legítimo (uma raiz que manda para `/<app>/`). O `--resolve`
continua fixando o IP, e redirecionamento relativo mantém o mesmo host.

### Verifique todos os planos de entrada, não só o web

Um serviço pode ter mais de uma porta de entrada — interface humana e endpoint
de máquina, por exemplo — atendidas por processos diferentes, com configurações e
até **credenciais** diferentes. Elas quebram de forma independente.

No caso acima, a interface web respondia perfeitamente enquanto o endpoint que
recebe os agentes estava fora havia mais de uma semana. Ninguém percebeu porque
a verificação — e o olho humano — batiam na interface. Liste os planos de entrada
do serviço e exercite **cada um**; o que estiver de pé mascara o que caiu.

## 4b. A ausência de sinal também não prova nada — prove o sensor

As seções 1 e 4 tratam do **sinal positivo enganoso**: o 301 que não prova, o 200 do
impostor. O gêmeo é mais fácil de engolir e menos comentado: **um resultado vazio.**

Vazio é produzido por dois mundos que se parecem exatamente:

- nada de ruim aconteceu;
- o instrumento nunca esteve vivo.

Um `grep` num log que não casa nada, um `find` que não devolve arquivo, uma captura de log
sem uma linha, um `docker logs --since` que resolveu para a janela errada, um pipe que
morreu quando o SSH caiu. Todos entregam a mesma saída silenciosa, e a leitura natural
("está limpo") é a errada em metade dos casos.

**A regra**: antes de concluir qualquer coisa a partir da ausência de saída, provoque um
positivo que você mesmo causou e confirme que ele aparece.

```bash
# Você acha que está capturando erros 4xx/5xx do serviço.
curl -s -o /dev/null "https://<host>/zz-sonda-$$"   # um 404 causado por você
sleep 5
grep -c "zz-sonda-$$" "$ARQUIVO_DE_CAPTURA"
# 0 → o sensor está morto, não o serviço limpo. Conserte o sensor primeiro.
```

O mesmo raciocínio vale para as verificações deste próprio arquivo. `find … -size -1k` que
não devolve nada prova que não há dump pequeno **ou** que o caminho está errado e não há
dump nenhum. `docker ps | grep -c unhealthy` retornando 0 prova saúde **ou** que o nome do
filtro mudou. Nos dois casos, uma sonda deliberada distingue em segundos.

Pergunta única que resolve: **"isto teria me mostrado um positivo?"** Se você não sabe
responder, o resultado negativo não é evidência.

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

## 7. O erro que aparece no log pode ser o secundário

Antes de formular hipótese a partir de uma mensagem de erro, verifique **de que
ponto do código ela vem**. Se o rastro aponta para rotina de encerramento —
`rollback`, `disconnect`, `finally`, destrutor, um `_end` qualquer — é forte
indício de que você está lendo o *handler de erro estourando*, não a falha
original. O handler pressupõe recursos que a falha real impediu de existir e
quebra em cima, soterrando a causa.

Caso real: um endpoint devolvia 500 com `Can't call method "rollback" on an
undefined value`. A leitura natural — "problema de transação" — está errada: a
rotina de encerramento chamava `rollback` num handle de banco que nunca fora
aberto, *porque a conexão havia sido recusada*. A mensagem descrevia a segunda
vítima.

O agravante é que **o erro real costuma estar desligado por padrão**. Aplicações
maduras trazem o log de diagnóstico em nível zero e a impressão de erro do driver
desabilitada, para não vazar credencial em log de produção. Enquanto isso não é
invertido, você está depurando sem a informação que decide o caso — e duas
hipóteses erradas custaram, aqui, mais tempo que o diagnóstico inteiro.

O procedimento que funciona:

1. Ligue o log verboso da aplicação e a impressão de erro do driver **antes** de
   teorizar. Guarde cópia do arquivo original.
2. Reproduza a falha.
3. Leia o erro primário, agora visível.
4. **Reverta a verbosidade** — ela vaza dado sensível e não deve ficar ligada.

Faça isso como um passo só, com a reversão no mesmo script da ativação: é o que
garante que o servidor não fique verboso porque a sessão foi interrompida no
meio.

## 8. Se você delega a subagentes

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
