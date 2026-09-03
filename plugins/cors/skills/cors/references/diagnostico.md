# Diagnóstico — por que o sintoma mente, e como medir

## §1. `curl` prova alcance, não permissão — e o `200` dele é o normal numa falha de CORS

CORS é implementado **no browser**. `curl`, Postman, `requests`, `axios` em Node, o fixture
`request` do Playwright: nenhum implementa a same-origin policy, então nenhum vai recusar a
resposta. A consequência prática é contraintuitiva e custa horas:

> Um endpoint que responde `200` no curl e é bloqueado no browser **não é uma contradição**.
> É a assinatura de uma falha de CORS.

Isso inverte o instinto de debug. O reflexo — "vou confirmar pelo curl se a API está de pé" —
produz uma evidência verdadeira e irrelevante, e ela costuma ser lida como "a API está boa, então o
problema é o front". Meça o que o browser mede.

### Caso medido (hosts anonimizados)

Um e2e apontava um front local (`http://localhost:3100`) para uma API de staging. Diagnóstico por
curl, do lado de fora:

```
https://api.exemplo.com/health              -> 200
https://api2.exemplo.com                    -> 200
https://api3.exemplo.com                    -> 401   (vivo, só exige auth)
```

Três serviços de pé. E o app, na tela, dizia **"Serviço indisponível"**, abortando antes de
qualquer requisição real. O `checkHealth()` da aplicação chamava `fetch`, caía no `catch`, e
traduzia a exceção para "fora do ar". Do console:

```
Access to fetch at 'https://api.exemplo.com/health' from origin 'http://localhost:3100'
  has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present…
Access to fetch at 'https://api2.exemplo.com/health' from origin 'http://localhost:3100'
  has been blocked by CORS policy: The 'Access-Control-Allow-Origin' header has a value
  'https://app.exemplo.com' that is not equal to the supplied origin.
```

A API tinha allowlist de **uma** origem. Não havia bug de rede nem serviço fora do ar — e o
subsistema que a mensagem seguinte do app culpava não tinha relação nenhuma. **Duas lições que
generalizam:**

1. O `catch` do app é onde a informação morre. Quase todo cliente HTTP embrulha o erro de CORS num
   "falha de rede" ou "serviço indisponível" — o nome do subsistema na mensagem é uma **suposição do
   app**, não um diagnóstico. Vá ao console.
2. Quando a allowlist é de uma origem só, **não existe correção do lado do cliente**. Ou a sua
   origem entra na lista (mudança no servidor), ou o teste roda a partir da origem permitida. Ver §5.

---

## §2. Ler a mensagem exata — cada uma nomeia uma correção diferente

O Chrome é específico de propósito na primeira linha e vago no resto. A parte que importa vem depois
de `blocked by CORS policy:`.

| Trecho | Significa | Correção |
| ------ | --------- | -------- |
| `No 'Access-Control-Allow-Origin' header is present` | a resposta não trouxe CORS nenhum | emitir o header (rota certa, método certo, **e em respostas de erro** — ver `configuracao.md`) |
| `has a value 'X' that is not equal to the supplied origin` | há allowlist; você não está nela | acrescentar a origem no servidor, ou rodar da origem permitida |
| `The value of the 'Access-Control-Allow-Credentials' header … is ''` | `credentials: 'include'` sem `Allow-Credentials: true` | `true` no servidor **e** origem explícita (nunca `*`) |
| `Response to preflight request doesn't pass access control check` | o `OPTIONS` falhou; a requisição real nem saiu | ver `casos-limite.md` §1 |
| `Request header field <h> is not allowed by Access-Control-Allow-Headers` | o preflight não autorizou um header seu | listar o header (atenção: `authorization` sozinho já força preflight) |
| `Redirect is not allowed for a preflight request` | `OPTIONS` levou 301/307/308 | responder o `OPTIONS` no lugar que recebe, sem redirect |
| `header contains multiple values 'A, B'` | dois emissores (app **e** proxy) | escolher um dono — `configuracao.md` §0 |

⚠️ **`TypeError: Failed to fetch` sem linha de CORS** não é CORS. É DNS, TLS, rede, extensão de
browser, ou `net::ERR_*`. Abra a aba Network e olhe o status da requisição: `(failed)` sem status é
transporte; status presente com corpo vazio é política.

⚠️ **A resposta bloqueada continua invisível no DevTools.** O browser não mostra o corpo de uma
resposta que ele recusou. Não conclua "a API não respondeu" a partir da aba Network — ela respondeu;
você é que não pode ver.

---

## §3. Separar CORS de CSP: a confusão mais cara

`Content-Security-Policy: connect-src` é um portão **da sua própria página** e falha com a mesma
exceção no JS. Distinguir é um `grep`:

```bash
# a página declara CSP em <meta>?
curl -s "$URL_DA_PAGINA" | grep -oP 'connect-src[^;"]*'
# ou em header?
curl -sI "$URL_DA_PAGINA" | grep -i content-security-policy
```

No console, a assinatura é inconfundível — `Refused to connect to '<url>' because it violates the
following Content Security Policy directive: "connect-src …"`. Se ela aparece, **mexer no CORS do
servidor não resolve nada**: quem barrou foi a sua página.

Armadilha frequente: um build gera a CSP a partir de variável de ambiente, e trocar a URL da API
sem trocar a CSP produz uma página que aponta para um lugar que ela mesma proíbe. Ao mudar o destino
da API, mude os dois — e confira no HTML **servido**, não no fonte.

---

## §4. A sonda que responde em uma execução

Quando o app engole o erro, pergunte ao browser diretamente. Cole no console da página (ou rode via
`page.evaluate` no Playwright/Puppeteer):

```js
// Testa cada candidato nos dois modos e diz QUAL portão barrou.
for (const url of ['https://api.exemplo.com/health']) {
  const r = { url };
  try {
    const res = await fetch(url, { method: 'GET' });
    r.cors = `ok status=${res.status} type=${res.type}`;
  } catch (e) { r.cors = `THROW ${e.message}`; }
  try {
    const res = await fetch(url, { mode: 'no-cors' });
    r.nocors = `type=${res.type} status=${res.status}`;
  } catch (e) { r.nocors = `THROW ${e.message}`; }
  console.log(r);
}
```

Como ler:

- `cors: THROW` + `nocors: type=opaque` → **é CORS**. O servidor está lá e respondeu; falta a
  permissão. (`opaque` prova alcance.)
- `cors: THROW` + `nocors: THROW` → **não é CORS**. É rede/DNS/TLS — ou CSP, que barra os dois
  modos. Olhe a mensagem do `no-cors`.
- `cors: ok` → o portão está aberto; o problema é outro (status, corpo, auth).

No Playwright, ligue os três ouvintes antes de navegar — sem eles o erro real fica só no browser:

```js
page.on('console', (m) => console.log(`[console.${m.type()}] ${m.text()}`));
page.on('pageerror', (e) => console.log(`[pageerror] ${e.message}`));
page.on('requestfailed', (r) => console.log(`[requestfailed] ${r.url()} :: ${r.failure()?.errorText}`));
```

---

## §5. `no-cors` não desbloqueia nada — e sabota health checks

`fetch(url, { mode: 'no-cors' })` **não** contorna a política. Ele troca o erro por uma **resposta
opaca**: `type: 'opaque'`, `status: 0`, sem corpo e sem headers legíveis. Serve para disparar um
efeito (pixel, beacon) e para nada mais.

O dano real aparece quando alguém usa `no-cors` como *fallback de health check*: a sonda passa a
responder "up" para qualquer servidor que exista, inclusive um que bloqueia todas as chamadas reais.
O painel fica verde e o app quebra na primeira requisição de verdade. Se o health check precisa
significar "o front consegue falar com esta API", ele tem de usar **o mesmo modo** das chamadas
reais — e um `catch` que distingue "não alcancei" de "não me deixaram ler".

E não há saída por `no-cors` para requisição autenticada: qualquer header como `Authorization` torna
a requisição não-simples, o que exige preflight, o que exige CORS.

---

## §6. Teste automatizado: aponte para uma origem permitida

Um e2e headless obedece à mesma política de um browser normal — ele **é** um browser. Se a API tem
allowlist, servir o front de `http://localhost` contra ela não funciona, e o teste falha com um
sintoma que acusa o app.

Ordem de preferência:

1. **Rodar contra a origem permitida.** Aponte o `baseURL` para o front já publicado naquela origem
   e injete a sessão no `localStorage` (`addInitScript`) para dispensar o login interativo. Bônus:
   testa o que está de fato no ar.
2. **Alinhar as origens no ambiente de teste** — front e API sob o mesmo host, ou a origem de
   desenvolvimento na allowlist do ambiente de teste (**nunca** na de produção).
3. **Proxy no dev server** (`server.proxy` do Vite, `proxy` do CRA, `devServer.proxy` do webpack): o
   browser fala com a própria origem e o proxy fala com a API. Some o CORS porque some o
   cross-origin. Cuidado: isso **mascara** um CORS que vai existir em produção — bom para
   desenvolver, ruim como prova.

Não tente `--disable-web-security` para "resolver": o teste deixa de exercitar a política que o
usuário real terá, e um bloqueio de produção passa a ser invisível no CI.
