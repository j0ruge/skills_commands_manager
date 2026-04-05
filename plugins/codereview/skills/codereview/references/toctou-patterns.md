# TOCTOU Race Condition Patterns — Code Review Reference

Detection checklist for Time-of-Check to Time-of-Use vulnerabilities. Read this reference when analyzing services, repositories, or controllers that perform check-then-act operations.

---

## Quick Reference — Red Flags

| Red Flag | Risk | Fix |
|----------|------|-----|
| `findUnique` then `create` (outside tx) | Duplicate creation | `upsert` or unique constraint + catch |
| `findUnique` then `update` based on field value | Double-spend/use | `updateMany` with WHERE conditions |
| Read outside `$transaction`, write inside | Stale data in tx | Move read inside tx or re-validate |
| `$transaction` without `isolationLevel` | False safety | Use atomic claim WHERE inside tx |
| `balance - amount` computed in JS | Lost update | `{ decrement: amount }` atomic op |
| `existsSync` then `readFile` | File race | Try-catch on operation directly |
| `cache.get` then compute on miss | Thundering herd | Promise coalescing / mutex |
| GET check + POST act (client-side) | Stale availability | Server-side atomic claim |

---

## Category 1: Database Check-Then-Act

### 1.1 — findUnique followed by conditional create

```typescript
// VULNERABLE
const existing = await prisma.user.findUnique({ where: { email } });
if (!existing) {
  await prisma.user.create({ data: { email } }); // race: another request created it
}
```

**Fix:** Use `upsert`, or rely on unique constraint + handle `P2002` error.

### 1.2 — findUnique followed by conditional update (state transition)

```typescript
// VULNERABLE
const invite = await repo.findByToken(token);
if (!invite.used_at) {
  await repo.markAsUsed(invite.id); // two requests pass the check
}
```

**Fix:** Atomic claim pattern:

```typescript
const result = await prisma.inviteTokens.updateMany({
  where: { id: invite.id, used_at: null, revoked_at: null },
  data: { used_at: new Date() },
});
if (result.count === 0) throw new Error('Already claimed');
```

### 1.3 — Count check followed by insert (business limit bypass)

```typescript
// VULNERABLE
const count = await prisma.team.count({ where: { ownerId } });
if (count >= MAX_TEAMS) throw new Error('Limit reached');
await prisma.team.create({ data: { ownerId } }); // concurrent request bypasses limit
```

**Fix:** Serializable transaction, or database CHECK constraint.

### 1.4 — Read-modify-write on numeric fields (lost update)

```typescript
// VULNERABLE
const account = await prisma.account.findUnique({ where: { id } });
await prisma.account.update({
  where: { id },
  data: { balance: account.balance - amount }, // lost update if concurrent
});
```

**Fix:** Atomic increment/decrement (`{ decrement: amount }` in Prisma).

---

## Category 2: Transaction Isolation Pitfalls

### 2.1 — Interactive transaction with default isolation

Prisma/PostgreSQL default is Read Committed — does NOT prevent phantom reads within the transaction. Two transactions can both read `used_at = null` and proceed.

**Fix:** Use `updateMany` with WHERE conditions inside the transaction (atomic claim), or specify `isolationLevel: 'Serializable'` when needed.

### 2.2 — Check outside transaction, mutate inside

```typescript
// VULNERABLE
const invite = await repo.findByToken(token); // stale by time tx runs
await prisma.$transaction(async (tx) => {
  await tx.inviteTokens.update({ ... }); // invite state may have changed
});
```

**Fix:** Move the read inside the transaction, or re-validate with atomic claim inside tx.

---

## Category 3: File System TOCTOU

### 3.1 — existsSync followed by read/write

```typescript
// VULNERABLE
if (fs.existsSync(filePath)) {
  const data = fs.readFileSync(filePath); // file deleted between check and read
}
```

**Fix:** Try the operation directly, catch `ENOENT`.

### 3.2 — Check directory then write file

**Fix:** Use `fs.mkdirSync(dir, { recursive: true })` (idempotent).

---

## Category 4: Cache TOCTOU

### 4.1 — Cache miss thundering herd

```typescript
// VULNERABLE
let value = cache.get(key);
if (!value) {
  value = await expensiveComputation(); // 10 concurrent requests all compute
  cache.set(key, value);
}
```

**Fix:** Promise coalescing or mutex per cache key.

### 4.2 — Stale cache used for auth decisions

Cached permissions used to gate security-sensitive operations.

**Fix:** Always query source of truth for security-critical checks.

---

## Category 5: API-Level & Token TOCTOU

### 5.1 — Token validation separate from consumption

Token verified (lookup) then consumed (update) in separate steps.

**Fix:** Atomic claim: `UPDATE tokens SET used_at = NOW() WHERE id = ? AND used_at IS NULL`.

### 5.2 — Multi-step wizard without server-side protection

**Fix:** Re-validate all preconditions on final step atomically.

---

## Detection Heuristics for Code Review

When reviewing code, look for these patterns in the diff:

1. **Two separate Prisma/ORM calls** where the first is a read and the second is a write that depends on the read's result
2. **`if (!entity.field)` followed by `entity.update()`** — classic check-then-act
3. **Business rules enforced in JS** (count checks, balance checks) instead of database constraints
4. **`$transaction` blocks** where the first operation is `findUnique` — consider if `updateMany` with WHERE would be safer
5. **Service methods** that call repository read, then repository write, without transaction wrapping

### Severity Assignment

| Pattern | Severity |
|---------|----------|
| Token/invite/payment claim without atomic update | **CRITICAL** |
| Duplicate creation risk (user, record) | **HIGH** |
| Lost update on numeric field | **HIGH** |
| Business limit bypass (count check) | **HIGH** |
| File system TOCTOU in server code | **MEDIUM** |
| Cache thundering herd | **MEDIUM** |
| Stale cache for display (non-security) | **LOW** |
