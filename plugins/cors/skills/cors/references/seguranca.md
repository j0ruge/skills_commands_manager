# Segurança — quando afrouxar o CORS vira vulnerabilidade

O risco aqui é assimétrico: relaxar CORS é a forma mais rápida de fazer o erro sumir, e algumas
formas de relaxar entregam ao atacante exatamente o que a same-origin policy existia para impedir —
**ler resposta autenticada de outra origem**. As misconfigs abaixo aparecem em programas de bug
bounty com regularidade justamente porque nasceram como "só para destravar o dev".

---

## §1. Refletir a origem sem allowlist é o pior padrão

```js
res.setHeader('Access-Control-Allow-Origin', req.headers.origin);   // 🔴
res.setHeader('Access-Control-Allow-Credentials', 'true');
```

Isso é **pior** que `*`. O `*` ao menos é recusado pelo browser quando há credenciais; a reflexão
funciona com credenciais e concede a **qualquer site** a permissão de ler respostas autenticadas da
vítima. A exploração é uma página do atacante com `fetch(alvo, {credentials:'include'})` e um `POST`
do resultado para o servidor dele.

Correção: comparação **exata** contra um conjunto fechado.

```js
const PERMITIDAS = new Set(['https://app.exemplo.com']);
const origin = req.headers.origin;
if (origin && PERMITIDAS.has(origin)) {
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Vary', 'Origin');
}
```

Se você não precisa de credenciais e o dado é público, `*` **sem** `Allow-Credentials` é uma escolha
legítima e mais segura que reflexão.

---

## §2. `null` nunca entra na allowlist

O browser envia `Origin: null` em contextos sem origem hierárquica: `data:`, `file:`, sandbox de
iframe, alguns redirects. É comum alguém liberar `null` para "funcionar abrindo o HTML local" — e
com isso qualquer página consegue produzir esse valor, via `<iframe sandbox>`, e passar na allowlist.

```html
<iframe sandbox="allow-scripts" srcdoc="<script>fetch('https://alvo/api', {credentials:'include'})…</script>">
```

Trate `null` como não-permitido, sempre. Para desenvolvimento local, libere a origem real do dev
server (`http://localhost:5173`) — e só no ambiente de desenvolvimento.

---

## §3. Matching por substring e regex frouxa

Todos estes passam quando não deveriam:

| Verificação | Bypass |
| ----------- | ------ |
| `origin.endsWith('exemplo.com')` | `https://evil-exemplo.com` |
| `origin.includes('exemplo.com')` | `https://exemplo.com.atacante.net` |
| `origin.startsWith('https://app.exemplo.com')` | `https://app.exemplo.com.atacante.net` |
| `/exemplo\.com/` (sem âncora) | `https://atacante.com/?x=exemplo.com` em alguns parsers |
| `/^https://.*\.exemplo\.com$/` | subdomínio sob controle do atacante (takeover, ou um `_` aceito pelo browser e não previsto na regex) |
| regex com `.` sem escape | `https://appXexemplo.com` |

Regras que eliminam a classe inteira:

- prefira **conjunto exato** (`Set.has`) a qualquer forma de matching;
- se precisar de padrão, **ancore** (`^…$`) e escape os pontos;
- lembre que a origem inclui **esquema e porta** — `http://app.exemplo.com` e
  `https://app.exemplo.com:8443` são origens diferentes de `https://app.exemplo.com`;
- não gere a allowlist a partir do `Host` ou de um header controlável pelo cliente.

Wildcard de subdomínio **não existe** no protocolo: `Access-Control-Allow-Origin: *.exemplo.com` é
inválido. Quem "precisa" dele está fazendo matching no servidor — e é aí que os bypasses moram.

---

## §4. `Vary: Origin` — sem ele, o cache faz o vazamento por você

Se a resposta varia por origem (allowlist dinâmica), **toda** resposta precisa de `Vary: Origin`.
Sem isso, um cache compartilhado (CDN, proxy corporativo, cache do browser em alguns casos) guarda a
resposta com o `Access-Control-Allow-Origin` da **primeira** origem que passou e serve a mesma a
todas. Dois efeitos, ambos ruins:

- **quebra funcional** — `app-b` recebe o header de `app-a` e o browser recusa, de forma
  intermitente e dependente de qual origem "esquentou" o cache. É um dos bugs mais difíceis de
  reproduzir, porque depende do POP do CDN;
- **vazamento** — se o conteúdo cacheado for específico de uma origem/tenant.

E confirme que a sua camada de cache de fato **separa** por esse header; nem todas separam. Se a
sua não separa, a política tem de ser uniforme para tudo que é cacheado.

---

## §5. O que CORS **não** faz

Enunciar isto evita decisões erradas de arquitetura:

- **Não é autenticação nem autorização.** A requisição chega ao servidor e é executada; o browser só
  decide se o JS pode *ler a resposta*. Todo endpoint continua precisando validar sessão e permissão.
- **Não protege contra CSRF.** Requisições "simples" (`GET`, `POST` de formulário com
  `Content-Type` simples) são enviadas **com cookies** sem preflight. CSRF se combate com token,
  `SameSite` no cookie e verificação de `Origin`/`Referer` no servidor.
- **Não torna uma API privada.** Restringir CORS não impede curl, script, servidor ou app móvel.
  Uma API "interna" protegida só por CORS é uma API pública.
- **Não protege o servidor de nada** — protege o *usuário* de ter os próprios dados lidos por um
  site terceiro.

Corolário operacional: quando alguém propõe abrir o CORS "porque é uma API interna", a pergunta
certa é o que mais protege aquele endpoint. Se a resposta for "nada", o problema não é o CORS.

---

## §6. Revisão rápida (o que procurar num code review)

```bash
# reflexão de origem
grep -rniE "Allow-Origin.*(req|request)\.(headers|META).*origin" .
# wildcard com credenciais
grep -rniE "allow_?origins?.*\*" . | grep -riE "credential"
# matching frouxo
grep -rniE "origin.*(endswith|startswith|includes|indexOf|contains)" .
# null permitido
grep -rniE "['\"]null['\"]" . | grep -i origin
```

Quatro perguntas que fecham a revisão:

1. A allowlist é comparação **exata** e vem de configuração, não de header do cliente?
2. Há `Allow-Credentials: true` em algum lugar que aceita origem dinâmica? Se sim, a allowlist é
   confiável mesmo?
3. Toda resposta com origem dinâmica tem `Vary: Origin`?
4. `null` está excluído, inclusive nos caminhos de desenvolvimento que vazaram para produção?
