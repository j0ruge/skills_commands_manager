# Troubleshooting — Frontend (React/Vite/nginx)

Cenários de troubleshooting específicos do frontend. Para cenários de infra compartilhados, ver `troubleshooting-shared.md`.

---

## Cenários Detalhados

### 1. Página em Branco (SPA não carrega)

**Sintoma**: Browser mostra página branca sem erros de rede.

**Diagnóstico:**

```bash
# Verificar se dist/ tem conteúdo
docker exec service_report_web ls -la /usr/share/nginx/html/

# Verificar se index.html referencia os assets corretos
docker exec service_report_web cat /usr/share/nginx/html/index.html

# Verificar se VITE_* estão embeddadas
docker exec service_report_web sh -c "grep -r 'VITE_' /usr/share/nginx/html/assets/*.js | head -5"
```

**Causas comuns:**

1. VITE_* não foram passadas como `build-args` no `docker/build-push-action`. O `vite build` completou sem erro, mas `import.meta.env.VITE_API_URL` é `undefined`.
2. `vite.config.ts` ausente no git (ex: adicionado ao `.gitignore`). Sem o arquivo, o `vite build` executa sem o plugin React, gerando um bundle que não renderiza nada.

**Solução:** Verificar que todos os 11 ARGs estão no Dockerfile, que o workflow passa cada um via `build-args:`, e que `vite.config.ts` está versionado.

---

### 2. API Calls Falhando (CORS, URL errada)

**Sintoma:** App carrega mas chamadas para a API falham.

**Diagnóstico:**

```bash
docker exec service_report_web sh -c "grep -o 'https://[^\"]*jrcbrasil[^\"]*' /usr/share/nginx/html/assets/*.js | sort -u"
```

**Causa:** VITE_API_URL aponta para o ambiente errado (staging vs produção) ou não inclui protocolo `https://`.

**Solução:** Verificar e corrigir o secret `VITE_API_URL` no environment correto do GitHub.

---

### 3. 404 em Rotas do React Router

**Sintoma:** Rota `/reports` retorna 404 ao acessar diretamente (não via navegação SPA).

**Causa:** nginx não tem `try_files $uri $uri/ /index.html` configurado.

**Solução:** Verificar `infra/dsr_web/nginx.conf`:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

---

### 4. `Cannot access 'X' before initialization` (Runtime)

**Sintoma:** App carrega o HTML mas o JavaScript falha com `Cannot access 'X' before initialization` ou `ReferenceError`.

**Diagnóstico:**

```bash
grep -n 'treeshake\|manualChunks\|moduleSideEffects' vite.config.ts
```

**Causa:** `treeshake.moduleSideEffects: false` no `vite.config.ts` combinado com `manualChunks` que agrupam módulos com dependências circulares.

**Solução:** Remover `treeshake` e `manualChunks` customizados do `vite.config.ts`. O treeshaking padrão do Rollup/Vite já é suficiente.

---

### 5. Container `unhealthy` — Healthcheck Falha em Alpine

**Sintoma:** `docker ps` mostra container como `unhealthy` mas nginx está rodando.

**Diagnóstico:**

```bash
docker inspect service_report_web --format '{{json .State.Health}}' | jq .
# Testar com IPv4 explícito
docker exec service_report_web wget -qO- http://127.0.0.1:80/index.html | head -5
# Comparar com localhost (pode falhar)
docker exec service_report_web wget -qO- http://localhost:80/index.html | head -5
```

**Causa:** Em imagens Alpine, `localhost` pode resolver para `::1` (IPv6). Se o nginx escuta apenas em IPv4, o healthcheck falha.

**Solução:** Usar `127.0.0.1` em vez de `localhost` no healthcheck:

```yaml
healthcheck:
  test: ["CMD", "wget", "-qO-", "http://127.0.0.1:80/index.html"]
```

---

### 6. Vitest Coletando Testes E2E Playwright

**Sintoma:** CI falha com erros de import do Playwright ou testes inesperados sendo executados.

**Diagnóstico:**

```bash
npx vitest run --reporter=verbose 2>&1 | grep "e2e/"
```

**Causa:** Sem configuração explícita, o Vitest coleta todos os `*.test.ts` / `*.spec.ts`, incluindo os de `e2e/`.

**Solução:** Criar ou atualizar `vitest.config.ts` com exclude:

```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    exclude: ['e2e/**', 'node_modules/**'],
  },
})
```

---

### 7. Container nginx 403 — dist/ Vazio

**Sintoma:** nginx retorna 403 Forbidden.

**Causa:** O diretório `dist/` não foi copiado ou está vazio na imagem.

**Diagnóstico:**

```bash
docker exec service_report_web ls -la /usr/share/nginx/html/
```

**Solução:** Verificar que `npm run build` gera `dist/` no Dockerfile e que o `COPY --from=build` está correto.

---

## Fluxo de Diagnóstico — Frontend

```text
Pipeline falhou?
├── Qual job?
│   ├── CI (lint/typecheck/test)
│   │   ├── ESLint falhou? → --max-warnings 0 com warnings existentes
│   │   ├── tsc --noEmit falhou? → Erros de tipo
│   │   └── Vitest falhou?
│   │       ├── Teste específico → verificar localmente
│   │       └── Coletando testes E2E? → vitest.config.ts com exclude
│   │
│   ├── Build-and-push
│   │   ├── Docker build falhou?
│   │   │   ├── yarn install falhou → verificar yarn.lock
│   │   │   ├── npm run build falhou → verificar tsc e vite build
│   │   │   └── ARG faltando → verificar build-args no workflow
│   │   └── Docker push falhou? → GHCR auth (permissions: packages: write)
│   │
│   └── Deploy
│       ├── Container unhealthy? → localhost IPv6 em Alpine → usar 127.0.0.1
│       ├── Container subiu mas app não funciona?
│       │   ├── Página em branco → VITE_* faltando ou vite.config.ts ausente
│       │   ├── Cannot access 'X' before initialization → treeshake / circular
│       │   ├── 404 em rotas → nginx try_files
│       │   ├── 403 Forbidden → dist/ vazio
│       │   └── API calls falhando → VITE_API_URL incorreto
│       └── SSL? → ERR_SSL → DNS não aponta (ver troubleshooting-shared.md)
└── Reproduzir localmente antes de alterar o workflow
```

---

## Comandos de Diagnóstico

```bash
# Status do container
docker ps --filter name=service_report_web

# Logs do container
docker logs service_report_web --tail 50

# Verificar imagem usada
docker inspect service_report_web --format '{{.Config.Image}}'

# Verificar healthcheck
docker inspect service_report_web --format '{{json .State.Health}}' | jq .

# Testar nginx (usar 127.0.0.1, não localhost)
docker exec service_report_web wget -qO- http://127.0.0.1:80/index.html | head -5

# Verificar VITE_* embeddadas no JS
docker exec service_report_web sh -c "grep -r 'jrcbrasil' /usr/share/nginx/html/assets/*.js | head -5"
```
