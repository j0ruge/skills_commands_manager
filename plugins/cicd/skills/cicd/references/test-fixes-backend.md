# Test Fix Patterns for CI

Common issues when running tests on CI Linux and how to fix them.

---

## 1. Case-Sensitivity in Imports

**Problem:** macOS (HFS+) is case-insensitive by default. An import `@repositories/vessel.repository` works locally but fails on Linux if the file is named `Vessel.repository.ts`.

**Diagnosis:**

```bash
# List files with different case than expected
find src/ -name "*.ts" | sort -f | uniq -di
```

**Fix:** Rename the file to match the import, or correct the import.

```typescript
// WRONG (on CI Linux)
import { VesselRepository } from '@repositories/vessel.repository';
// Actual file: src/repositories/Vessel.repository.ts

// CORRECT
import { VesselRepository } from '@repositories/Vessel.repository';
```

---

## 2. Case-Sensitivity in `jest.mock()`

**Problem:** `jest.mock('@repositories/vessel.repository')` does not intercept if the actual module is `Vessel.repository`. The mock simply is not applied, and the test uses the real implementation.

**Fix:** The path in `jest.mock()` must exactly match the file case.

```typescript
// WRONG
jest.mock('@repositories/vessel.repository');

// CORRECT (if the file is Vessel.repository.ts)
jest.mock('@repositories/Vessel.repository');
```

---

## 3. Optional `prismaTransaction`

**Problem:** Some services receive `prismaTransaction` as an optional parameter, but tests do not pass it, causing a database access error.

**Fix:** Ensure the parameter has a fallback to the main client:

```typescript
async execute(data: CreateDTO, prismaTransaction?: PrismaClient) {
  const client = prismaTransaction || prisma
  // use client instead of prismaTransaction directly
}
```

---

## 4. `server.ts` Guard for `NODE_ENV=test`

**Problem:** If `server.ts` calls `app.listen()` unconditionally, tests that import the app attempt to listen on the port, causing `EADDRINUSE` or interference between suites.

**Fix:**

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

## 5. Seed Data in `beforeAll`

**Problem:** Integration tests assume pre-existing data in the database (e.g., a user, a report). On CI, the database is clean on each run.

**Fix:**

```typescript
beforeAll(async () => {
  // Insert data needed for the tests
  await prisma.user.create({
    data: {
      id: 'test-user-id',
      name: 'Test User',
      email: 'test@example.com',
    },
  });
});

afterAll(async () => {
  // Clean up only test data created in beforeAll
  await prisma.user.delete({
    where: { id: 'test-user-id' },
  });
  await prisma.$disconnect();
});
```

---

## 6. Conditional E2E Test Skip

**Problem:** E2E tests that make real HTTP requests (with `supertest` against a real server) fail on CI because the server is not running.

**Fix:**

```typescript
const isCI = process.env.CI === 'true' || process.env.NODE_ENV === 'test';

describe('E2E: Service Report Routes', () => {
  if (isCI) {
    it.skip('Skipping E2E tests in CI', () => {});
    return;
  }

  // ... real E2E tests
});
```

Or use `describe.skipIf`:

```typescript
const skipE2E = !process.env.E2E_BASE_URL;

describe.skipIf(skipE2E)('E2E Tests', () => {
  // ...
});
```

---

## 7. Jest OOM Fix

**Problem:** With many test suites, Jest can exceed the default Node.js heap limit (~1.7GB), terminating with `FATAL ERROR: Reached heap limit Allocation failed` (exit code 134 / SIGABRT).

**Fix in CI workflow:**

```yaml
- name: Run tests
  run: node --max-old-space-size=4096 node_modules/.bin/jest --forceExit
```

**Local fix (package.json):**

```json
{
  "scripts": {
    "test": "node --max-old-space-size=4096 node_modules/.bin/jest --watch",
    "test:ci": "node --max-old-space-size=4096 node_modules/.bin/jest --forceExit"
  }
}
```

---

## 8. Assertions with Dynamic Data

**Problem:** Tests that compare UUIDs, timestamps, or generated data fail because the values change on each execution.

**Fix:** Use partial matchers:

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

## Pattern Summary

| Problem                     | Quick Fix                             |
| --------------------------- | ------------------------------------- |
| Import case mismatch        | Fix the file or import case           |
| jest.mock case mismatch     | Align path with actual file name      |
| prismaTransaction undefined | Add fallback `\|\| prisma`            |
| server.ts starts in test    | Guard `NODE_ENV !== 'test'`           |
| Missing data                | Seed in `beforeAll`                   |
| E2E without server          | Conditional `describe.skip`           |
| Jest OOM                    | `--max-old-space-size=4096`           |
| UUIDs/timestamps            | `expect.any(String)`                  |
