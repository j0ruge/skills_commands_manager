---
name: cors
metadata:
  version: 1.0.0
description: "Diagnostica e configura CORS — o erro que mente sobre a causa. Decide qual portao barrou (CORS x CSP connect-src x mixed content, identicos no JS), le a mensagem literal do Chrome, e da a receita por stack (nginx, Express, Django, Spring, FastAPI, CDN). Preflight, credenciais, Vary: Origin e as misconfigs que viram vulnerabilidade. Triggers — CORS, Access-Control-Allow-Origin, preflight, blocked by CORS policy, cross-origin, OPTIONS 401, no-cors, erro de CORS."
---

# CORS — diagnóstico, configuração e as armadilhas

Skill para quando uma requisição do browser é **bloqueada entre origens** — ou quando você vai
expor uma API que um browser vai consumir.

---

## Comece por aqui: três coisas que quase todo mundo erra

**1. CORS não é uma proteção do servidor. É uma permissão que o browser pede.**
O servidor **já processou** a requisição — recebeu, executou, respondeu. O browser é que se recusa a
entregar a resposta ao JavaScript. Consequências que mudam o diagnóstico:

- Um `POST` bloqueado por CORS **pode ter gravado no banco**. "Deu erro de CORS" não é sinônimo de
  "não aconteceu". Confira o efeito antes de repetir a chamada.
- CORS **não** substitui autenticação nem protege contra CSRF. Requisições "simples" são enviadas
  de qualquer forma; só a *leitura* da resposta é barrada.
- Cliente que não é browser (curl, Postman, servidor→servidor, o `request` do Playwright) **não tem
  CORS**. Nunca terá o erro, e por isso nunca o reproduz.

**2. `curl` não reproduz o problema — e isso já custou sessões inteiras.**
`curl` prova **alcance**, não **permissão**. Um `200` no curl com o browser bloqueado é o estado
normal de uma falha de CORS, não uma contradição. Ver `references/diagnostico.md` §1.

**3. Três portões diferentes falham exatamente igual no JS.**
`fetch` rejeita com `TypeError: Failed to fetch` nos três casos, e o `catch` do app costuma traduzir
isso para "serviço indisponível". Antes de mexer no servidor, decida qual portão é:

| Portão | Quem decide | Onde aparece a verdade |
| ------ | ----------- | ---------------------- |
| **CORS** | headers `Access-Control-*` da resposta | console: `blocked by CORS policy` |
| **CSP `connect-src`** | `<meta http-equiv>` ou header `Content-Security-Policy` da SUA página | console: `Refused to connect to … violates … Content Security Policy` |
| **Mixed content** | página `https:` chamando `http:` | console: `Mixed Content: … was loaded over HTTPS, but requested an insecure resource` |

Uma página servida de origem nova costuma esbarrar nos **dois primeiros ao mesmo tempo** — libera o
CORS, e a CSP continua barrando. Trate como duas correções, não uma.

---

## Triagem em um minuto

```bash
# 1) O servidor responde? (prova alcance — NÃO prova CORS)
curl -sS -o /dev/null -w '%{http_code}\n' "$URL"

# 2) O que ele diz para a SUA origem? (simula a decisão; o browser é quem decide)
curl -sS -D- -o /dev/null -H "Origin: $ORIGEM" "$URL" | grep -i '^access-control\|^vary'

# 3) E o preflight? (obrigatório se há Authorization, ou método/header não-simples)
curl -sS -D- -o /dev/null -X OPTIONS "$URL" \
  -H "Origin: $ORIGEM" \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: authorization,content-type' \
  | grep -i '^HTTP/\|^access-control'
```

Leitura dos três:

- **Sem nenhum `access-control-*` na saída (2)** → o servidor não tem CORS configurado para essa
  origem. É o caso mais comum e o mais simples.
- **`access-control-allow-origin` com OUTRO valor** → há allowlist e a sua origem não está nela.
  Não adianta insistir do lado do cliente: **isso não tem contorno**. Ou a origem entra na lista, ou
  você roda a partir de uma origem que já está.
- **(3) não devolve `2xx`** → o preflight falha, e a requisição real nunca sai. Causas típicas:
  `OPTIONS` caindo em autenticação (`401`), redirect (`301/307/308` — **preflight não pode
  redirecionar**), ou header pedido fora de `Access-Control-Allow-Headers`.
- **`Vary: Origin` ausente com allowlist dinâmica** → funciona hoje e quebra atrás de CDN. Ver
  `references/casos-limite.md` §3.

Se (2) e (3) parecem certos e o browser ainda bloqueia, o portão é outro — releia a tabela dos três
portões e vá para `references/diagnostico.md` §2 ler a mensagem exata.

---

## Sintoma → causa

| Mensagem no console (Chrome) | Causa | Onde corrigir |
| ---------------------------- | ----- | ------------- |
| `No 'Access-Control-Allow-Origin' header is present` | servidor não emite CORS para essa rota/origem | `configuracao.md` |
| `…has a value 'X' that is not equal to the supplied origin` | allowlist não inclui a sua origem | `configuracao.md` §1 |
| `Response to preflight request doesn't pass access control check` | o `OPTIONS` não respondeu 2xx com os headers | `casos-limite.md` §1 |
| `Request header field <h> is not allowed by Access-Control-Allow-Headers` | falta o header na resposta do preflight | `configuracao.md` |
| `…'Access-Control-Allow-Credentials' header in the response is ''` | falta `true`, ou a origem veio como `*` | `configuracao.md` §2 |
| `Redirect is not allowed for a preflight request` | `OPTIONS` recebeu 301/307/308 | `casos-limite.md` §1 |
| `…header contains multiple values 'A, B'` | **dois** lugares emitindo CORS (app + proxy) | `configuracao.md` §0 |
| `Refused to connect to … Content Security Policy` | não é CORS — é CSP | `diagnostico.md` §3 |
| `TypeError: Failed to fetch` **sem mais nada** | rede, DNS, TLS, extensão, ou CORS com log suprimido | `diagnostico.md` §2 |

⚠️ **Erro `4xx`/`5xx` que "virou erro de CORS"** é uma classe própria e enganosa: muitas
configurações só emitem os headers em respostas de sucesso, então um `500` legítimo chega ao browser
sem CORS e o console culpa o CORS. Você conserta o CORS e descobre o `500` que estava lá o tempo
todo. Ver `configuracao.md` §1 (nginx `always`) e §3 (ordem do error handler).

---

## Referências

| Assunto | Arquivo |
| ------- | ------- |
| **Diagnóstico** — por que o curl mente, ler a mensagem exata, sonda para colar na página, `no-cors` e resposta opaca, e2e/Playwright | `references/diagnostico.md` |
| **Configuração por stack** — quem é o dono do header, nginx, Express, Django, Spring, FastAPI, CDN/API Gateway | `references/configuracao.md` |
| **Segurança** — reflexão de origem, `null`, matching por substring/regex, `Vary: Origin`, o que CORS **não** protege | `references/seguranca.md` |
| **Casos-limite** — preflight (redirect, cache, custo), expose-headers, erros sem CORS, Local Network Access do Chrome, WebSocket, canvas/fontes | `references/casos-limite.md` |

---

## Antes de propor a correção

- **Decida o portão primeiro.** Metade do tempo perdido com "CORS" é CSP ou mixed content.
- **Meça no browser, não no curl.** O curl é útil para ler headers; ele nunca reproduz o bloqueio.
- **Um dono só para o header.** App **ou** proxy — os dois juntos produzem `multiple values` e
  quebram o que estava funcionando.
- **Não relaxe para destravar.** `Access-Control-Allow-Origin: *` num endpoint autenticado é
  rejeitado pelo browser quando há credenciais, e refletir a origem sem allowlist é uma
  vulnerabilidade, não um atalho. Ver `seguranca.md`.
- **Se a origem não está na allowlist e você não controla o servidor, não há contorno no cliente.**
  Rode a partir de uma origem permitida, ou use um proxy do seu lado (servidor→servidor não tem
  CORS). Qualquer "solução" que pareça desligar o CORS no browser é desligar a proteção do usuário.
