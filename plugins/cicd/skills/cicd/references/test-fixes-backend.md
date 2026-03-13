# Padrões de Correção de Testes para CI

Problemas comuns ao rodar testes no CI Linux e como corrigi-los.

---

## 1. Case-Sensitivity em Imports

**Problema:** macOS (HFS+) é case-insensitive por padrão. Um import `@repositories/vessel.repository` funciona local mas falha no Linux se o arquivo se chama `Vessel.repository.ts`.

**Diagnóstico:**

```bash
# Listar arquivos com case diferente do esperado
find src/ -name "*.ts" | sort -f | uniq -di
```

**Correção:** Renomear o arquivo para corresponder ao import, ou corrigir o import.

```typescript
// ERRADO (no CI Linux)
import { VesselRepository } from '@repositories/vessel.repository';
// Arquivo real: src/repositories/Vessel.repository.ts

// CORRETO
import { VesselRepository } from '@repositories/Vessel.repository';
```

---

## 2. Case-Sensitivity em `jest.mock()`

**Problema:** `jest.mock('@repositories/vessel.repository')` não intercepta se o módulo real é `Vessel.repository`. O mock simplesmente não é aplicado, e o teste usa a implementação real.

**Correção:** O path no `jest.mock()` deve corresponder exatamente ao case do arquivo.

```typescript
// ERRADO
jest.mock('@repositories/vessel.repository');

// CORRETO (se o arquivo é Vessel.repository.ts)
jest.mock('@repositories/Vessel.repository');
```

---

## 3. `prismaTransaction` Opcional

**Problema:** Alguns services recebem `prismaTransaction` como parâmetro opcional, mas os testes não o passam, causando erro no acesso ao banco.

**Correção:** Garantir que o parâmetro tem fallback para o client principal:

```typescript
async execute(data: CreateDTO, prismaTransaction?: PrismaClient) {
  const client = prismaTransaction || prisma
  // usar client ao invés de prismaTransaction diretamente
}
```

---

## 4. Guard do `server.ts` para `NODE_ENV=test`

**Problema:** Se `server.ts` chama `app.listen()` incondicionalmente, testes que importam o app tentam ouvir na porta, causando `EADDRINUSE` ou interferência entre suites.

**Correção:**

```typescript
// server.ts
if (process.env.NODE_ENV !== 'test') {
  app.listen(port, host, () => {
    console.log(`Server running on ${host}:${port}`);
  });
}

export { app };
```

---

## 5. Seed Data em `beforeAll`

**Problema:** Testes de integração assumem dados pré-existentes no banco (ex: um usuário, um report). No CI, o banco é limpo a cada run.

**Correção:**

```typescript
beforeAll(async () => {
  // Inserir dados necessários para os testes
  await prisma.user.create({
    data: {
      id: 'test-user-id',
      name: 'Test User',
      email: 'test@example.com',
    },
  });
});

afterAll(async () => {
  // Limpar apenas dados de teste criados no beforeAll
  await prisma.user.delete({
    where: { id: 'test-user-id' },
  });
  await prisma.$disconnect();
});
```

---

## 6. Skip Condicional de E2E Tests

**Problema:** Testes E2E que fazem requests HTTP reais (com `supertest` contra um servidor real) falham no CI porque o servidor não está rodando.

**Correção:**

```typescript
const isCI = process.env.CI === 'true' || process.env.NODE_ENV === 'test';

describe('E2E: Service Report Routes', () => {
  if (isCI) {
    it.skip('Skipping E2E tests in CI', () => {});
    return;
  }

  // ... testes E2E reais
});
```

Ou usar `describe.skipIf`:

```typescript
const skipE2E = !process.env.E2E_BASE_URL;

describe.skipIf(skipE2E)('E2E Tests', () => {
  // ...
});
```

---

## 7. Jest OOM Fix

**Problema:** Com muitas test suites, Jest pode exceder o heap limit padrão do Node.js (~1.7GB), terminando com `FATAL ERROR: Reached heap limit Allocation failed` (exit code 134 / SIGABRT).

**Correção no CI workflow:**

```yaml
- name: Run tests
  run: node --max-old-space-size=4096 node_modules/.bin/jest --forceExit
```

**Correção local (package.json):**

```json
{
  "scripts": {
    "test": "node --max-old-space-size=4096 node_modules/.bin/jest --watch",
    "test:ci": "node --max-old-space-size=4096 node_modules/.bin/jest --forceExit"
  }
}
```

---

## 8. Assertions com Dados Dinâmicos

**Problema:** Testes que comparam UUIDs, timestamps ou dados gerados falham porque os valores mudam a cada execução.

**Correção:** Usar matchers parciais:

```typescript
expect(response.body).toEqual(
  expect.objectContaining({
    name: 'Expected Name',
    id: expect.any(String),
    createdAt: expect.any(String),
  })
);
```

---

## Resumo de Padrões

| Problema                    | Fix Rápido                            |
| --------------------------- | ------------------------------------- |
| Import case mismatch        | Corrigir case do arquivo ou import    |
| jest.mock case mismatch     | Alinhar path com nome real do arquivo |
| prismaTransaction undefined | Adicionar fallback `\|\| prisma`      |
| server.ts inicia no test    | Guard `NODE_ENV !== 'test'`           |
| Dados faltantes             | Seed em `beforeAll`                   |
| E2E sem servidor            | `describe.skip` condicional           |
| Jest OOM                    | `--max-old-space-size=4096`           |
| UUIDs/timestamps            | `expect.any(String)`                  |
