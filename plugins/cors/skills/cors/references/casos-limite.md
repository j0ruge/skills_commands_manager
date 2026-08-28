# Casos-limite

## §1. Preflight — quando ele existe, e por que falha

O browser manda um `OPTIONS` **antes** da requisição real quando ela não é "simples". É simples só
se: método `GET`, `HEAD` ou `POST`; nenhum header além dos safelisted; e `Content-Type` entre
`application/x-www-form-urlencoded`, `multipart/form-data`, `text/plain`.

Na prática, **quase toda chamada de API real faz preflight**, porque `Authorization` ou
`Content-Type: application/json` já bastam. Duas consequências:

- "O `GET` funciona e o `POST` autenticado não" quase nunca é sobre o `POST`. É o preflight.
- Se o `OPTIONS` cai em autenticação, ele leva `401` e a requisição real **nunca sai**. Preflight
  não carrega cookie nem `Authorization` **por definição** — autenticá-lo é sempre erro de
  configuração. Deixe o CORS antes do middleware de auth.

**Preflight não pode redirecionar.** `301`, `307`, `308` no `OPTIONS` → `Redirect is not allowed for
a preflight request`. Origens comuns do redirect acidental:

- `APPEND_SLASH` do Django e equivalentes (`/api/coisa` → `/api/coisa/`);
- redirect de `http` → `https` quando a URL configurada no front está em `http`;
- normalização de path no proxy.

A resposta real **pode** redirecionar; o preflight, não. E o destino do redirect precisa ter CORS
próprio — headers não são herdados através do redirect.

O preflight precisa de **2xx** (204 é o usual) e dos headers `Allow-Origin`, `Allow-Methods`,
`Allow-Headers`, mais `Allow-Credentials` se houver credenciais.

---

## §2. Erros perdem os headers — e o console culpa o CORS

Muita configuração só emite CORS no caminho feliz. Aí um `401`, `422` ou `500` legítimo chega ao
browser sem headers, e a mensagem no console fala de CORS. O efeito é caro: a equipe passa horas no
CORS e o defeito era o `500`.

Onde isso nasce:

- **nginx** — `add_header` sem `always` (ver `configuracao.md` §1a);
- **Express** — error handler que responde sem o middleware de CORS ter rodado;
- **API Gateway** — *gateway responses* (`DEFAULT_4XX`/`DEFAULT_5XX`) têm headers próprios;
- **crash antes do middleware** — nada emite nada.

Teste explicitamente um caminho de erro: force um `500` e confira que `Access-Control-Allow-Origin`
continua na resposta. É o teste que mais revela configuração incompleta.

---

## §3. `Access-Control-Expose-Headers` — o header que existe e o JS não vê

Por padrão o JS só lê um punhado de headers de resposta cross-origin (`Cache-Control`,
`Content-Language`, `Content-Type`, `Expires`, `Last-Modified`, `Pragma`). Qualquer outro —
`X-Total-Count`, `X-Request-Id`, `Location`, `Content-Disposition`, headers de rate limit — é
**invisível**, mesmo estando na resposta.

O sintoma engana: no DevTools o header aparece; no código, `res.headers.get('X-Total-Count')` é
`null`. Não é bug do cliente.

```
Access-Control-Expose-Headers: X-Total-Count, Content-Disposition
```

É por isso que paginação por header e download com nome de arquivo "não funcionam só em produção" —
em dev, mesma origem, não passam por CORS.

---

## §4. Chrome: Local Network Access (público → localhost / rede privada)

Desde o **Chrome 142** existe um portão **adicional** ao CORS: uma página pública que faz requisição
para `127.0.0.0/8`, `::1`, faixas privadas (`192.168.0.0/16`, `10.0.0.0/8`, `fc00::/7`) passa a
exigir **permissão do usuário**. Isso substitui o esforço anterior de *Private Network Access*, que
tentava resolver com preflight e os headers `Access-Control-Request-Private-Network` /
`Access-Control-Allow-Private-Network` — abordagem que ficou em espera.

Por que importa aqui: o bloqueio **não é CORS**, mas se parece com um. Se o seu app web público fala
com um agente/impressora/dispositivo em `localhost` ou na LAN, o sintoma é uma falha de rede que
some quando o usuário concede a permissão — e o CORS do dispositivo não tem nada a ver com isso.

Ao depurar `https://algum-site` → `http://localhost:PORTA`, considere ainda:

- **mixed content** — página `https:` chamando `http:` costuma ser barrada antes de qualquer CORS
  (loopback tem tratamento especial em alguns casos, mas não conte com isso);
- a política é do **Chrome**; Firefox e Safari divergem. Teste nos três se o produto depende disso.

---

## §5. Coisas que parecem CORS e não são

| Situação | O que realmente rege |
| -------- | -------------------- |
| **WebSocket** | não tem CORS. O handshake envia `Origin` e **o servidor** tem de validar — se não validar, qualquer site conecta |
| **`<img>`, `<script>`, `<link>`, `<iframe>`** | carregam cross-origin sem CORS; o que muda é o que o JS pode **ler** deles |
| **`<canvas>` com imagem de outra origem** | o canvas fica *tainted* e `toDataURL`/`getImageData` lançam; precisa de `crossorigin="anonymous"` **e** CORS na imagem |
| **Fontes (`@font-face`)** | exigem CORS mesmo carregadas por CSS — fonte de "a fonte não carrega só em produção" |
| **`EventSource` / SSE** | segue CORS, mas não aceita headers customizados — não dá para mandar `Authorization` |
| **Service Worker / `importScripts`** | escopo e política próprios |
| **Redirect no meio de uma chamada CORS** | cada salto precisa passar; e a origem vira `null` em alguns redirects cross-origin |
| **`window.postMessage`** | não é CORS; a validação de `event.origin` é sua |

---

## §6. Checklist de fechamento

Antes de dizer "CORS está configurado":

- [ ] `OPTIONS` responde **2xx**, sem autenticação e sem redirect
- [ ] `Allow-Headers` cobre tudo que o cliente manda (`authorization`, `content-type`, customizados)
- [ ] respostas de **erro** (401/422/500) também trazem os headers
- [ ] `Vary: Origin` presente quando a origem é dinâmica
- [ ] `Expose-Headers` lista o que o front precisa ler
- [ ] com credenciais: origem **literal**, `Allow-Credentials: true`, nada de `*`
- [ ] allowlist por **comparação exata**; `null` fora; sem reflexão sem validação
- [ ] **um** emissor de header (app **ou** proxy), verificado na resposta real
- [ ] validado **no browser**, não só no curl
