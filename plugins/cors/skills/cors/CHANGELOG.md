# Changelog — cors

Formato: [Semantic Versioning](https://semver.org/)

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
