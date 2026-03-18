# Troubleshooting — Backend (Node.js/Express/Prisma)

Cenários de troubleshooting específicos do backend. Para cenários de infra compartilhados, ver `troubleshooting-shared.md`.

---

## Diagnóstico por Exit Code

### Exit 1 — Falha Genérica (Test/Lint)

**Causas comuns:** ESLint warnings com `--max-warnings 0`, Prettier formatting mismatch, Jest test failures, TypeScript compilation errors.

```bash
gh run view <run-id> --log-failed
yarn lint && yarn lint:check && yarn test
```

### Exit 2 — Misuse of Command

**Causa:** Flag inválida ou script não encontrado no package.json.

### Exit 127 — Command Not Found

**Causa:** Binário não instalado (ex: `prettier` sem devDependency).

```bash
grep "prettier" package.json
yarn add -D prettier
```

### Exit 134 — SIGABRT (OOM)

**Sintoma:** `FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory`

```yaml
run: node --max-old-space-size=4096 node_modules/.bin/jest --forceExit
```

### Exit 137 — SIGKILL (OOM Killer)

**Causa:** O sistema operacional matou o processo por uso excessivo de memória.

**Correção:** Aumentar memória do runner ou otimizar testes (`--runInBand`).

---

## Por Mensagem de Erro

### `manifest unknown`

**Causa:** Imagem Docker não existe no registry (ex: `bitnami/postgresql:17` descontinuada).

```yaml
# ANTES (não funciona)
image: bitnami/postgresql:17
env:
  POSTGRESQL_USERNAME: test_user

# DEPOIS
image: postgres:17
env:
  POSTGRES_USER: test_user
```

### Zod Validation Error

**3 cenários distintos:**

1. **No CI (step de teste) — `invalid_type`:** Variável falta no bloco `env:` do step de teste.
2. **No deploy (container) — `invalid_type`:** Variável falta no step "Generate .env" do workflow CD.
3. **No deploy (container) — `invalid_string`:** Variável presente mas com formato inválido (ex: URL sem `https://`).

**Prevenção:** Ao adicionar nova variável no Zod (`src/env.ts`), atualizar AMBOS: o bloco `env:` dos testes E o `printf` do Generate .env nos workflows CD.

### `EADDRINUSE`

```text
Error: listen EADDRINUSE: address already in use :::3003
```

**Causa:** `server.ts` chama `app.listen()` durante os testes. Ver `test-fixes-backend.md` §4.

### `Cannot find module` (case-sensitivity)

```text
Cannot find module '@repositories/vessel.repository'
```

**Causa:** Path no import não corresponde ao case real do arquivo no Linux. Ver `test-fixes-backend.md` §1.

### `TS2688` / `TS2724` — Erros de tipo Prisma

**Causa:** Incompatibilidade entre tipos gerados pelo Prisma e versão do TypeScript.

**Correção:** Adicionar `--skipLibCheck` ao comando `tsc`.

### `npx biome check .` falha em arquivos não-source

**Sintoma:** Biome reporta erros em arquivos de config (`biome.jsonc`, `tsconfig.json`, `Dockerfile`, etc.) ou em arquivos fora de `src/`.

**Causa:** Biome verifica todos os arquivos por padrão, diferente de ESLint que geralmente é configurado para escopo específico.

**Correção:** Configurar `files.includes` em `biome.jsonc` para limitar o escopo:

```jsonc
{
  "files": {
    "includes": ["src/**", "prisma/**"]
  }
}
```

Ou corrigir os erros reportados nos arquivos de config (empty blocks, `node:` protocol, naming conventions).

### Biome 2.x config error (`unknown key "ignore"`)

**Sintoma:** `biome check` falha com erro de configuração ao migrar para Biome 2.x.

**Causa:** Biome 2.x removeu a chave `files.ignore` em favor de `files.includes` (lógica invertida).

**Correção:** Substituir `files.ignore` por `files.includes` no `biome.jsonc`.

### `ERR_CONNECTION_REFUSED` via browser (nginx-proxy OK)

**Sintoma:** Browser retorna `ERR_CONNECTION_REFUSED`. Certificado SSL renova normalmente. Container da API está rodando.

**Causa:** `VIRTUAL_PORT` não definido no `docker-compose.yml`. nginx-proxy usa default porta 80, mas a API escuta em outra porta (ex: 3003).

**Diagnóstico:**

```bash
docker exec nginx-proxy cat /etc/nginx/conf.d/default.conf | grep -A 10 "api.dsr"
docker exec service_report_api sh -c "wget -qO- http://localhost:3003/health || curl -s http://localhost:3003"
```

**Correção:** Adicionar `VIRTUAL_PORT: '${API_PORT}'` no `environment` do `docker-compose.yml`.

---

## Fluxo de Diagnóstico — Backend

```text
Workflow falhou
├── Qual job?
│   ├── lint → ESLint warnings / Prettier / Biome check
│   ├── test → Ver exit code e mensagem
│   │   ├── Exit 134/137 → OOM → aumentar heap
│   │   ├── Exit 1 → Ler log do Jest
│   │   │   ├── Cannot find module → case-sensitivity
│   │   │   ├── ZodError invalid_type → env var faltante
│   │   │   ├── ZodError invalid_string → URL sem https://
│   │   │   ├── EADDRINUSE → guard server.ts
│   │   │   └── Assertion error → dados/seed
│   │   └── Exit 127 → dependência faltante
│   ├── build-and-push → Dockerfile ou GHCR auth
│   └── deploy → Runner offline, compose error ou env var
│       ├── ZodError invalid_type → env var faltante no Generate .env
│       ├── ZodError invalid_string → URL sem https://
│       ├── ERR_CONNECTION_REFUSED → VIRTUAL_PORT não definido
│       └── runner offline → systemctl status actions.runner.*
└── Reproduzir localmente antes de alterar o workflow
```

---

## Comandos de Diagnóstico

```bash
# Logs completos do run falhado
gh run view <run-id> --log-failed

# Logs de um job específico
gh run view <run-id> --log --job <job-id>

# Re-executar apenas jobs falhados
gh run rerun <run-id> --failed

# Status do runner no servidor
sudo systemctl status actions.runner.*
journalctl -u actions.runner.*.service --since "1 hour ago"
```
