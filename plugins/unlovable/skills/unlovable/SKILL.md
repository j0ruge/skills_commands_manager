---
name: unlovable
metadata:
  version: 1.1.0
description: "Strip every Lovable trace from a codebase scaffolded on lovable.dev — brand strings, og/twitter preview metadata, `.lovable/` residue, the `LOVABLE_API_KEY` email feature (migrated to SMTP) and the `@lovable.dev/*` Vite wrapper that owns the build. Tells cosmetic residue apart from the removals that break the build. Triggers — lovable, lovable.dev, unlovable, lovable-tagger, LOVABLE_API_KEY, remove Lovable branding, WhatsApp preview shows Lovable."
---

# Unlovable — remover todos os traços do Lovable de um projeto

Checklist para qualquer projeto que saiu do lovable.dev. Objetivo: eliminar resíduos, marca/mensagens e a dependência funcional/estrutural do Lovable — deixando o projeto 100% nativo.

A ordem importa. Os traços se dividem em **cosméticos** (strings, README, metadados) e **estruturais** (o wrapper de build e a feature de email). Os cosméticos são reversíveis e baratos; os estruturais quebram o `build` se removidos sem substituto. Faça o inventário inteiro antes de editar a primeira linha, e ataque o estrutural primeiro — é onde o tempo vai.

## 1. Inventário (read-only primeiro — nunca editar sem mapear)

Localizar os 3 tipos de traço com grep e busca de arquivos:

- **Resíduos**: `.lovable/` (plan.md, project.json), `.env.lovable.bak`, `*.lovable.bak`, pastas/mirror de registry Lovable.
- **Marca/mensagens**: grep `-rin "lovable"` em `src/`, `*.md`, configs. Strings comuns:
  - `__root.tsx` (TanStack) head meta: `title: "Lovable App"`, `description: "Lovable Generated Project"`, `author: "Lovable"`, `twitter:site: "@Lovable"`, og:* herdando esses valores.
  - `index.html` (Vite/React puro) — mesmos metadados og/twitter no `<head>` estático.
  - msg de erro de client Supabase: `Connect Supabase in Lovable Cloud.` (em `client.ts`, `client.server.ts`, `auth-middleware.ts`).
  - README: bloco `This project was built with Lovable` + `## Build with Lovable` (link p/ o editor e `projects/<uuid>`).
- **Funcional/estrutural (o crítico — quebra build/feature)**:
  1. **Email**: `api.lovable.dev/v1/email/send` + `LOVABLE_API_KEY` — a feature real de envio de email ("Lovable Emails"). Removê-la sem substituto derruba um fluxo de produto, não só uma string.
  2. **Build**: o wrapper de config do Vite. Duas formas, e a diferença decide o §3:
     - **`@lovable.dev/vite-tanstack-config`** — pacote que *substitui* o `vite.config.ts`, injetando tanstackStart/react/tailwind/tsConfigPaths/cloudflare/alias/dedupe/css. Removê-lo esvazia o build; é preciso reescrever a config à mão.
     - **`lovable-tagger`** — o caso mais comum (Vite + React puro): um plugin **dev-only** listado no próprio `vite.config.ts` do projeto. Aqui a remoção é local e barata, não uma reescrita.
     - Confira também `minimumReleaseAgeExcludes` no `bunfig.toml`, que costuma listar o pacote.

> ⚠️ Cuidado: `.tanstack/` (TanStack Start router-gen) NÃO é Lovable — não remover. Distinguir sempre.

## 2. Migrar o email (SMTP, não a API Lovable)

Troque a chamada a `api.lovable.dev` por SMTP via Nodemailer, com as credenciais vindas do ambiente — nunca literais no código:

```ts
import nodemailer from "nodemailer";
// server-side (createServerFn, route handler, API route)
const user = process.env.SMTP_USER;
const pass = process.env.SMTP_PASS;      // Gmail: app password, não a senha da conta
const transporter = nodemailer.createTransport({
  service: "gmail",                      // ou { host, port, secure } p/ SMTP genérico
  auth: { user, pass },
});
await transporter.sendMail({ from: `<App> <${user}>`, to, subject, text });
```

- `bun add nodemailer` (ou npm/yarn/pnpm equivalente).
- Variáveis no `.env` local, **nunca versionado** — ver §4.
- **Preserve a assinatura da função.** Se a versão Lovable devolvia um `preview` (ou qualquer campo que o caller exiba), continue devolvendo: o chamador não sabe que o provedor mudou, e um campo que some vira `undefined` na UI sem erro nenhum.

## 3. Build nativo

### 3a. Vite + React puro (`lovable-tagger`)

Caso mais comum e o mais barato: o plugin é dev-only. Remova o import e a entrada do array `plugins` do `vite.config.ts` (costuma estar sob um `mode === "development" && componentTagger()`), tire a dependência do `package.json` e reinstale. O build não muda de forma.

### 3b. TanStack Start (`@lovable.dev/vite-tanstack-config`)

Aqui o pacote **é** a config. Remova-o e recrie o `vite.config.ts` com os plugins que o wrapper injetava:

```ts
import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { cloudflare } from "@cloudflare/vite-plugin";

export default defineConfig({
  plugins: [
    tailwindcss(),
    tanstackStart({ server: { entry: "server" } }),  // entry = caminho sem .ts em src/
    viteReact(),
    cloudflare(),                                    // só se o deploy for Cloudflare
  ],
  css: { transformer: "lightningcss" },
  resolve: { alias: { "@": "./src" } },              // se o projeto usa alias @
});
```

- `server.entry` vai **dentro** de `tanstackStart({...})`, NÃO como chave de topo do `defineConfig`. Fora dali o Vite ignora em silêncio e o servidor não sobe com o entry certo.
- Remover também a entrada do pacote em `minimumReleaseAgeExcludes` do `bunfig.toml`.
- **Valide com `bun run build`** (ou `npm run build`) — é o passo de maior risco; faça isolado e primeiro, antes de qualquer mudança cosmética, para que uma falha de build não fique ambígua entre dez edições.

## 4. Segurança: `.env` nunca versionado

Se o `.env` estiver tracked e sem `.gitignore` (comum nesses repos), o risco de credencial versionada é real:

```sh
git rm --cached .env && printf "\n# Secrets\n.env\n.env.*\n!.env.example\n" >> .gitignore
```

> ⚠️ Isso tira o `.env` do index, mas ele permanece no **histórico git** (commits antigos). Limpar histórico exige `git filter-repo` (reescreve commits) — só com autorização explícita do usuário; reporte como pendência. E lembre que qualquer segredo já empurrado para um remoto deve ser **rotacionado**, não só apagado: reescrever o histórico não invalida a chave.

## 5. Favicon e preview do WhatsApp

- **Favicon**: criar `public/` se não existir, copiar o `.ico`/logo da marca do projeto p/ `public/favicon.ico`, e adicionar `{ rel: "icon", href: "/favicon.ico" }` no head `links:` do `__root.tsx` (TanStack) ou `<link rel="icon">` no `index.html` (Vite).
- **Preview WhatsApp/og**: o preview "remete ao Lovable" vem dos **metadados og/twitter** — não necessariamente de uma imagem. Corrigir `title`/`og:title`/`og:description`/`author`/`twitter:site` para a marca real é o que remove o branding no compartilhamento.

### Leia o card como um mapa: cada linha aponta para uma tag

Antes de editar, case o que o print mostra com a tag que o produziu — `og:title`
costuma **já estar certo** (o Lovable preenche com o nome do app), então o card
sai meio certo e meio Lovable, e isso faz o problema parecer maior ou menor do
que é. Um caso real: título `JRC Sales Quote` correto, subtítulo
`Lovable Generated Project` (o `og:description`) e o banner *"Build apps and
websites by chatting with AI"* (o `og:image` apontando para
`https://lovable.dev/opengraph-image-*.png`).

### Para o `og:image`, remover é a saída certa — apontar para asset próprio é a cara

A tentação é trocar a URL do Lovable pela imagem da marca. Isso quase nunca é
uma edição de uma linha, por dois motivos que só aparecem depois de decidir:

- **`og:image` quer URL absoluta.** Crawler de rede social não resolve caminho
  relativo de forma confiável — e o endereço **difere por ambiente**
  (staging × produção). Chumbar um domínio faz o card de um dos dois ambientes
  apontar para o outro; fazer certo é uma variável de build (`VITE_*` com
  `--build-arg` por workflow), não uma string no HTML.
- **O logo que existe no repo raramente serve.** O formato do card é 1200x630;
  logo de cabeçalho costuma ser uma faixa larga e baixa (457x154 no caso real),
  que sai recortada ou com tarja.

Então: **apague `og:image` e `twitter:image` e troque `twitter:card` para
`summary`.** O card passa a mostrar título e descrição da marca, sem imagem — o
branding do Lovable some hoje, sem asset novo e sem dependência de domínio.
Registre a imagem própria como pendência (`TODO.md`) descrevendo as duas
exigências acima; sem arte, qualquer imagem é pior que nenhuma. Deixe um
comentário no HTML dizendo por que não há imagem, ou o próximo autor "conserta"
a ausência devolvendo o problema.

## 6. Verificação final

```sh
grep -rin "lovable" src/ vite.config.ts package.json  # deve vir vazio (código)
grep -rn "api\.lovable\|LOVABLE_" src/                # vazio
bun run build                                          # exit 0
grep -c lovable dist/index.html                        # 0 — o ARTEFATO, não a fonte
```

A última linha não é redundante. Metadado de `index.html` é copiado para o build
pelo Vite, e o que o crawler do WhatsApp/Telegram lê é o **artefato servido** —
provar que a string saiu da fonte não prova que saiu do que vai para produção.
É a mesma pergunta de sempre: você verificou o rótulo ou a coisa?

Refs remanescentes em docs `.md` que apenas *descrevem* a migração (histórico) podem ficar; o que não pode sobrar é marca/mensagem visível no app e dependência de build/feature.

## Pitfalls

- NÃO remover `.tanstack/` (é TanStack, não Lovable).
- `bun.lock`/lockfile npm podem reter a string "lovable" só como **mirror de registry** (ex.: `sandbox-npm-cache.lovable.dev` em URLs `resolved`) — inofensivo, não é código; conferir antes de gastar tempo. Um `grep` no lockfile é a fonte mais comum de falso positivo neste trabalho.
- **Mas nem toda sobra em lockfile é mirror.** Num monorepo, `npm install` da raiz atualiza o lockfile da raiz e **não toca** lockfiles órfãos dentro dos workspaces (vestígios de quando o pacote era um repo só). O do workspace continua declarando o `lovable-tagger` como dependência de verdade, e o `grep` do §6 acusa depois de o trabalho estar correto e o build limpo. Antes de "consertar", abra o arquivo: entrada de dependência num lockfile que ninguém atualiza é resíduo **inerte** — some quando alguém aposentar o arquivo, e forçá-lo agora mexe em algo fora do escopo desta limpeza. O que não pode sobrar é no lockfile **vivo**.
- O wrapper Lovable também injeta dev-only plugins (componentTagger, sandbox detection) — não precisam ser replicados p/ build/deploy local.
- Mexer no repo exige autorização do usuário (regra inviolável); apresente o inventário e as decisões antes de editar.
