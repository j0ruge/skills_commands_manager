# Configuração por stack

## §0. Antes de escrever qualquer header: escolha UM dono

CORS pode ser emitido pela aplicação, pelo reverse proxy, pelo API Gateway ou pelo CDN. Quando dois
emitem, o browser recebe

```
Access-Control-Allow-Origin: https://app.exemplo.com, https://app.exemplo.com
```

e **recusa** — `header contains multiple values`. Note que o valor pode até estar certo nos dois; a
duplicação sozinha invalida. É a causa clássica de "funcionava e parou depois que subimos o nginx na
frente".

Regra: **um dono, e desligue o outro explicitamente.** Onde colocar:

- **Na aplicação** quando a decisão depende de rota, tenant ou usuário. Mais fácil de testar.
- **No proxy/gateway** quando há vários serviços atrás dele e a política é uniforme — evita repetir
  a mesma allowlist em N linguagens.

Ao migrar de um para o outro, remova o antigo **na mesma mudança**; a janela em que os dois emitem
quebra o app.

---

## §1. nginx

Três armadilhas específicas, e as três geram sintomas que não parecem de configuração.

**(a) `add_header` só se aplica a respostas de sucesso.** Por padrão vale para `200, 201, 204, 206,
301, 302, 303, 304, 307, 308`. Um `401`, `422` ou `500` sai **sem CORS**, e o browser reporta erro
de CORS para o que é um erro legítimo da API — você conserta o CORS e descobre o `500` que estava
lá. Sempre `always`:

```nginx
add_header Access-Control-Allow-Origin $cors_origin always;
```

**(b) `add_header` não é herdado por um bloco que tem `add_header` próprio.** Um `if
($request_method = OPTIONS)` com headers dentro **descarta** os do `location`. É preciso repetir
todos ali dentro.

**(c) Não existe wildcard de subdomínio no protocolo.** `*.exemplo.com` não é valor válido. A saída
é `map`, que faz allowlist exata e devolve string vazia (= header não emitido) para o resto:

```nginx
map $http_origin $cors_origin {
    default "";
    "https://app.exemplo.com"   $http_origin;
    "https://admin.exemplo.com" $http_origin;
}

server {
    location / {
        if ($request_method = OPTIONS) {
            add_header Access-Control-Allow-Origin      $cors_origin always;
            add_header Access-Control-Allow-Methods     "GET, POST, PUT, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers     "Content-Type, Authorization" always;
            add_header Access-Control-Allow-Credentials "true" always;
            add_header Access-Control-Max-Age           86400 always;
            add_header Vary                             "Origin" always;
            add_header Content-Length                   0 always;
            return 204;
        }

        add_header Access-Control-Allow-Origin      $cors_origin always;
        add_header Access-Control-Allow-Credentials "true" always;
        add_header Vary                             "Origin" always;

        proxy_pass http://backend;
    }
}
```

O `Vary: Origin` é **obrigatório** aqui — a resposta varia por origem e sem ele qualquer cache
compartilhado serve a resposta de uma origem para outra (ver `seguranca.md` §4).

**Alternativa que remove (a) e (b):** o módulo `headers-more`
(`more_set_headers`), que herda corretamente e não precisa de `always`.

⚠️ Se o nginx é um proxy e o backend **também** emite CORS, use `proxy_hide_header
Access-Control-Allow-Origin` antes de emitir o seu — senão cai no §0.

---

## §2. Credenciais: a regra que não tem exceção

Se a requisição leva cookie, TLS client cert ou `credentials: 'include'`, então:

- `Access-Control-Allow-Origin` **não pode ser `*`** — tem de ser uma origem literal;
- `Access-Control-Allow-Credentials: true` é obrigatório;
- `Access-Control-Allow-Headers: *` e `Allow-Methods: *` **não** funcionam como coringa: com
  credenciais o `*` é tratado literalmente. Liste os nomes.

Cabeçalho `Authorization` (Bearer) **não** conta como "credential" no sentido do
`credentials: 'include'` — mas torna a requisição não-simples e **força preflight**. É a causa mais
comum de "o GET funciona e o POST autenticado não".

---

## §3. Node / Express

```js
const cors = require('cors');

const PERMITIDAS = new Set(['https://app.exemplo.com', 'https://admin.exemplo.com']);

app.use(cors({
  origin(origin, cb) {
    // `origin` é undefined em same-origin e em clientes sem browser — deixe passar,
    // mas NUNCA aceite a string 'null' (ver seguranca.md §2).
    if (!origin || PERMITIDAS.has(origin)) return cb(null, true);
    return cb(null, false);            // false = sem header. NÃO passe um Error:
  },                                    // um throw aqui vira 500 sem CORS e o console culpa o CORS.
  credentials: true,
  allowedHeaders: ['Content-Type', 'Authorization'],
  exposedHeaders: ['X-Total-Count'],
  maxAge: 86400,
}));
```

Armadilhas de Express:

- **Ordem importa.** `app.use(cors())` tem de vir **antes** das rotas e antes de qualquer middleware
  de autenticação — senão o `OPTIONS` do preflight é barrado com `401` e a requisição real nunca
  acontece. Preflight **não** carrega credenciais; autenticá-lo é sempre erro.
- **Error handler.** Um handler de erro que responde sem passar pelo middleware de CORS produz
  `500` sem headers. Garanta que o CORS já escreveu os headers antes (ele escreve na entrada), ou
  emita-os também no handler.
- **`app.options('*', cors())`** para o preflight quando o CORS é aplicado por rota em vez de global.
- Roteador montado depois de um `express.static` ou de um redirect pode fazer o `OPTIONS` receber
  `301` — e preflight não redireciona (`casos-limite.md` §1).

---

## §4. Django

`django-cors-headers`:

```python
INSTALLED_APPS += ["corsheaders"]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",   # ANTES de CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    ...
]

CORS_ALLOWED_ORIGINS = ["https://app.exemplo.com"]
CORS_ALLOW_CREDENTIALS = True
# CORS_ALLOW_ALL_ORIGINS = True  -> só em dev, e nunca junto com credentials
```

⚠️ **`CSRF_TRUSTED_ORIGINS` não é CORS** e não substitui o de cima. São dois mecanismos separados:
CORS libera a leitura da resposta; CSRF valida o POST de sessão. Atrás de proxy TLS você
provavelmente precisa dos dois, mais `SECURE_PROXY_SSL_HEADER`.

⚠️ `CorsMiddleware` precisa vir **antes** de qualquer middleware que possa responder cedo
(`CommonMiddleware` com `APPEND_SLASH` gera redirect — e preflight não redireciona).

---

## §5. Spring Boot

O erro mais comum é de **ordem de filtros**: o Spring Security roda antes do MVC, então o
`@CrossOrigin` do controller não chega a ser consultado e o preflight leva `401`.

```java
@Bean
SecurityFilterChain chain(HttpSecurity http) throws Exception {
  http.cors(Customizer.withDefaults())         // liga o CorsFilter DENTRO do Security
      .authorizeHttpRequests(a -> a.anyRequest().authenticated());
  return http.build();
}

@Bean
CorsConfigurationSource corsConfigurationSource() {
  var c = new CorsConfiguration();
  c.setAllowedOrigins(List.of("https://app.exemplo.com"));  // NÃO use setAllowedOriginPatterns("*") com credentials
  c.setAllowedMethods(List.of("GET","POST","PUT","DELETE","OPTIONS"));
  c.setAllowedHeaders(List.of("Content-Type","Authorization"));
  c.setAllowCredentials(true);
  c.setMaxAge(86400L);
  var s = new UrlBasedCorsConfigurationSource();
  s.registerCorsConfiguration("/**", c);
  return s;
}
```

---

## §6. FastAPI / Starlette

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.exemplo.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Total-Count"],
    max_age=86400,
)
```

⚠️ `allow_origins=["*"]` **junto com** `allow_credentials=True` é silenciosamente degradado — o
Starlette não emite a origem e o browser rejeita. Use `allow_origin_regex` se precisa de padrão, e
ancore-o (`^https://[a-z0-9-]+\.exemplo\.com$`).

---

## §7. CDN, API Gateway e cache

- **`Vary: Origin` é obrigatório** quando a resposta varia por origem. Sem ele, um cache
  compartilhado guarda a resposta da primeira origem e serve a todas.
- **Nem todo CDN respeita `Vary: Origin`** para separar entradas de cache (a Cloudflare, por
  exemplo, não separa por esse header). Nesses casos, ou a política é a mesma para todos (`*` em
  conteúdo público sem credencial), ou o CORS não pode ser resolvido na borda cacheada.
- **API Gateway (AWS) com proxy integration:** o `OPTIONS` precisa existir como método, e os headers
  de erro do gateway (`DEFAULT_4XX`/`DEFAULT_5XX` gateway responses) precisam de CORS próprio —
  senão um `403` do authorizer chega sem headers e vira "erro de CORS".
- **Cache de preflight:** `Access-Control-Max-Age` corta latência de forma expressiva num SPA, mas
  os browsers impõem teto próprio (na ordem de horas) e **ignoram** valores maiores. E cuidado ao
  reduzir uma allowlist: preflights já cacheados continuam válidos no cliente até expirar.
