# Changelog — cors

Formato: [Semantic Versioning](https://semver.org/)

## 2026-09-22 — Preflight aprovado e requisição bloqueada — [1.1.0]

**O quê:** nova seção `casos-limite.md` §1a — o preflight que responde `204` com todos os headers
e ainda assim tem a requisição real recusada, porque `Access-Control-Allow-Methods` não lista o
método. Junto: a mensagem literal do Chrome (`Method <M> is not allowed by
Access-Control-Allow-Methods in preflight response`) entra nas duas tabelas sintoma→causa, o passo
(3) da triagem deixa de sondar com `POST` fixo, o guia de leitura ganha a linha do `204`-mas-
bloqueado, e `configuracao.md` §3 explica por que o exemplo de Express **não** passa `methods`.

**Por quê:** numa sessão real, um review de PR pegou uma allowlist que omitia `PUT` num backend
cuja rota de edição usava exatamente esse método. Três coisas que a skill não cobria ficaram
visíveis de uma vez:

1. **O sintoma é parcial, e por isso é caro.** `GET` e `POST` quase sempre estão na lista — são os
   primeiros que alguém escreve. A tela carrega, o cadastro salva, só a edição quebra, e a
   investigação começa na tela que falhou em vez do console. O preflight que *falha*, coberto no
   §1, derruba tudo de uma vez e por isso é mais fácil.

2. **A triagem da própria skill era cega para ele.** O passo (3) mandava
   `Access-Control-Request-Method: POST` fixo. O preflight é julgado por método: perguntar por
   `POST` quando quem falha é `PUT` devolve `204` completo, e a sonda passava a atestar saúde
   exatamente onde havia doença. Sonda que só pergunta pelo caminho feliz não é sonda.

3. **A lista de métodos é uma duplicata da tabela de rotas.** Escrita uma vez à mão, enquanto as
   rotas crescem toda semana; e nenhum teste de backend emite preflight (`supertest` não passa
   pela rede, mock de frontend intercepta antes dela), então a divergência só aparece num browser.
   O conserto durável não é acrescentar o método que faltou — é derivar a lista do router, ou
   guardar a igualdade com um teste que percorre as rotas registradas. O §1a traz esse teste com
   as duas armadilhas dele: a asserção anti-vacuidade (varredura vazia passa igual a varredura
   completa) e a exigência de vê-lo vermelho antes de confiar no verde.

## 2026-09-03 — Prompt audit — [1.0.1]

Prompt audit (`/claude-api prompt-audit`, modelo-alvo Claude Fable 5.1); relatório completo fora do repo. Corpo limpo fora de um hunk.

- `references/diagnostico.md`, "Caso medido (28/08/2026)": três hostnames internos de staging
  (`api.dsr/erp/estimates.jrcbrasil.net`), a mensagem literal do app de origem e "parser de PDF"
  num plugin distribuído. O exemplo é load-bearing (as strings literais do Chrome, o `401` que
  ainda é "vivo", as duas lições), então vira `exemplo.com` — vocabulário que a skill já usa — sem
  a data.
- Description: os acentos que faltavam (`portão`, `idênticos`, `lê`, `dá`) — o auditor mediu que
  foi descuido, não decisão (a mesma string carrega `—`, o valor é aspeado, outras descriptions em
  PT têm acento). Espelhada nos 3 lugares.
- `SKILL.md` ganha `metadata.version`.

## 2026-08-28 — Skill nova — [1.0.0]

**O quê:** skill dedicada a diagnosticar e configurar CORS. `SKILL.md` com a triagem de um minuto e
a tabela sintoma → causa, mais quatro references: `diagnostico.md`, `configuracao.md`,
`seguranca.md` e `casos-limite.md`.

**Por quê:** numa sessão real, apontar um e2e de um front local para uma API de staging queimou duas
tentativas por uma razão que nenhuma skill cobria. O curl devolvia `200` para os três serviços e a
página dizia **"Serviço indisponível"** — o `checkHealth()` do app chamava `fetch`, caía no `catch` e
traduzia a exceção para "fora do ar". A causa estava só no console: a API respondia
`Access-Control-Allow-Origin: https://dsr.jrcbrasil.net` e a página rodava em `http://localhost`.
Não havia serviço fora do ar, nem falha de rede, nem o defeito de parsing que a mensagem seguinte
acusava.

Disso saiu a espinha da skill — **o sintoma mente**, em três níveis:

1. **O `catch` do app mente.** Praticamente todo cliente HTTP embrulha CORS num "falha de rede"; o
   nome do subsistema na mensagem é suposição do app, não diagnóstico.
2. **O curl mente por omissão.** Ele prova alcance, não permissão: `200` no curl com o browser
   bloqueado é a *assinatura* de uma falha de CORS, não uma contradição. É o reflexo de debug que
   produz evidência verdadeira e irrelevante.
3. **Três portões falham idênticos no JS** — CORS, CSP `connect-src` e mixed content. Na mesma
   sessão o build de front tinha CSP gerada por variável de ambiente, então trocar a URL da API sem
   trocar a CSP produziria uma página apontando para um lugar que ela mesma proíbe. Decidir o portão
   antes de mexer no servidor economiza a maior parte do tempo.

O resto veio de pesquisa, priorizando o que falha em produção e não em dev: `add_header` do nginx
que não vale para `4xx`/`5xx` (o `500` legítimo vira "erro de CORS"), `if` que não herda header,
preflight que não pode redirecionar e que não pode ser autenticado, `Vary: Origin` ausente virando
cache poisoning em CDN, `Expose-Headers` (paginação e `Content-Disposition` "só quebram em
produção"), e o Local Network Access do Chrome 142, que barra público → localhost por permissão do
usuário e **não** é CORS, embora se pareça.

A parte de segurança é deliberadamente enfática porque afrouxar CORS é a correção mais rápida e
algumas formas de afrouxar são a vulnerabilidade: refletir a origem sem allowlist é **pior** que
`*` (funciona com credenciais), `null` na allowlist é explorável por `<iframe sandbox>`, e
`endsWith`/`includes`/regex sem âncora têm bypass conhecido. Fecha com o que CORS **não** faz — não
é auth, não é anti-CSRF, e não torna uma API privada.

Fontes principais: MDN (`Access-Control-Expose-Headers`, `CORSExternalRedirectNotAllowed`),
Chrome for Developers (Local Network Access, Private Network Access), PortSwigger/PayloadsAllTheThings
(misconfigurations), getpagespeed (nginx), expressjs/cors.
