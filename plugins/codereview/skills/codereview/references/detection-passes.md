# Detection Passes

This file contains all detection patterns applied per-file during code review analysis. Sonnet agents load this file alongside the file diff/content to produce structured findings.

When analyzing a file, apply **all applicable passes** below. Return findings as a structured list.

## Finding Format

Each finding must include:
- **file**: path relative to repo root
- **line**: line number(s) from the diff
- **severity**: CRITICAL / HIGH / MEDIUM / LOW
- **category**: the pass that caught it (e.g., "Readability", "Security", "Bug")
- **description**: what the issue is, referencing the actual code
- **suggestion**: concrete fix direction

---

## Zen Principles Analysis (Passes 5.1–5.5)

Apply these 5 principles as analysis lenses to all CODE files (reduced rigor for UI_LIB — only CRITICAL/HIGH).

### 5.1 "Beautiful is better than ugly" & "Readability counts"

**Universal:**

- Non-semantic variable/function names (single letters, abbreviations, misleading names)
- Inconsistent formatting within the changed code
- Magic numbers or strings without named constants
- Excessively long functions (>50 lines of logic)
- Missing or misleading documentation on exported/public functions
  - `react|vue|angular|node`: JSDoc (`/** ... */`)
  - `dotnet`: XML documentation comments (`/// <summary>`)

### 5.2 "Explicit is better than implicit"

**Universal:**

- Missing parameter validation at public API boundaries
- Implicit type conversions that could lose data

**When `frameworkPatterns` is `react|vue|angular|node` (web frontend):**

- Missing TypeScript types or using `any`
- Implicit return types on exported functions
- React component props without explicit interface/type
- `useEffect` with missing or incorrect dependency arrays
- Implicit boolean coercion that could mask bugs (e.g., `value && <Component />` where value could be `0`)

**When `frameworkPatterns=dotnet`:**

- `var` used where type is genuinely ambiguous (non-obvious inference)
- `dynamic` keyword without strong justification
- Implicit conversions that could lose data (e.g., `long` to `int`)

### 5.3 "Simple is better than complex"

**Universal:**

- Over-engineered abstractions for simple problems
- Unnecessary indirection (wrapper functions that just forward calls)
- Single Responsibility Principle violations (class/component doing too much)
- Premature optimization without evidence of need (flag as LOW with note: "Consider profiling to confirm benefit before applying")

**When `frameworkPatterns` is `react|vue|angular|node`:**

- Custom hooks that could be replaced with simpler patterns

**When `frameworkPatterns=dotnet`:**

- Business logic in XAML code-behind instead of ViewModel (MVVM violation)
- Over-abstracted service interfaces with single implementation and no test seam justification

### 5.4 "Flat is better than nested"

**Universal:**

- Arrow code (>3 levels of nesting)
- Missing guard clauses (early returns)

**When `frameworkPatterns` is `react|vue|angular|node`:**

- Deeply nested ternary operators in JSX
- Callback pyramids (nested `.then()` chains or nested callbacks)
- Complex conditional rendering that could be extracted

**When `frameworkPatterns=dotnet`:**

- Deeply nested `if/else` chains that could use pattern matching or guard clauses
- Complex LINQ chains (>3 chained operations) that would be clearer as separate steps

### 5.5 "Errors should never pass silently"

**Universal:**

- Empty `catch` blocks or catch that only logs without re-throwing or returning error
- API/service calls without error feedback path
- Silent fallbacks that hide bugs

**When `frameworkPatterns` is `react|vue|angular|node`:**

- Unhandled Promise rejections
- Missing error boundaries for component trees

**When `frameworkPatterns=dotnet`:**

- `async void` methods outside of UI event handlers (unobservable exceptions) — flag as CRITICAL
- `catch (Exception) { }` without logging or re-throw — flag as HIGH
- Missing `try/finally` or `using` for `IDisposable` resources — flag as HIGH

---

## Additional Detection Passes (6.1–6.8)

### 6.1 Bug Detection

**Universal:**

- Potential null access without checks
- Off-by-one errors in loops or array operations
- `async` functions that never `await` anything (likely missing await or unnecessary async)

**When `frameworkPatterns` is `react|vue|angular|node`:**

- `useEffect` dependency array mismatches (missing deps or unnecessary deps)
- Race conditions from stale closures or unmounted component updates
- Direct state mutation (modifying state objects/arrays without creating new references)
- Incorrect equality checks (`==` instead of `===`)

**When `frameworkPatterns=dotnet`:**

- `async void` (except UI event handlers) — unhandled exceptions crash the app
- `IDisposable` not disposed (missing `using` statement)
- Race conditions with `Task.Run` and shared mutable state
- `DateTime.Now` instead of `DateTime.UtcNow` in cross-timezone logic
- Deadlocks from `.Result` or `.Wait()` on async code in UI thread

### 6.2 Security

**Universal:**

- Exposed secrets, API keys, tokens in code or config
- Hardcoded API URLs, service endpoints, or connection strings (should use environment variables or config)
- `eval()`, `new Function()`, or dynamic code execution
- Missing input validation/sanitization at system boundaries

**When `frameworkPatterns` is `react|vue|angular|node`:**

- XSS vectors: `dangerouslySetInnerHTML`, unescaped user input in DOM
- Sensitive data in localStorage without encryption

**When `frameworkPatterns=dotnet`:**

- SQL string concatenation (use parameterized queries or Entity Framework)
- `MessageBox.Show()` or `OpenFileDialog` in service/domain classes (UI leak into business layer)
- `System.Windows.Forms` using in non-UI classes
- Hardcoded file paths without `Path.Combine()`

### 6.3 Performance

**Universal:**

- Large classes/components that should be split for maintainability or lazy loading
- Expensive computations without caching or memoization

**When `frameworkPatterns` is `react|vue|angular|node`:**

- Inline object/array/function creation in JSX props (new reference every render)
- Missing `key` props or using array index as `key` in dynamic lists
- **`React.memo` missing** — flag as **MEDIUM** only when the component is rendered inside a list or loop, or when prop identity changes are known to cause unnecessary child re-renders. Otherwise flag as **LOW** or omit.
- **`useCallback` missing** — flag as **MEDIUM** only when the callback is passed as a prop to a memoized child or used in a `useEffect` dependency array and its identity changes provably cause repeated effect execution. Otherwise flag as **LOW** or omit.
- **`useMemo` missing** — flag as **MEDIUM** only when the computation is demonstrably expensive (>100ms measured, or explicitly identified by profiling). For cheap computations flag as **LOW** or omit.
- **All other memoization suggestions** — assign **LOW** and include a note: _"Recommend running a profiler before applying this optimization to confirm a measurable benefit."_

**When `frameworkPatterns=dotnet`:**

- `new HttpClient()` per-call instead of `IHttpClientFactory` or injected instance
- String concatenation in loops (use `StringBuilder`)
- `Thread.Sleep()` in async code or tests
- LINQ `.ToList()` or `.ToArray()` when `IEnumerable` suffices (unnecessary materialization)

### 6.4 Type Safety

**Universal:**

- Missing discriminated union / exhaustive switch checks (switch without default)
- Excessive type casting that bypasses type checking

**When `frameworkPatterns` is `react|vue|angular|node`:**

- Usage of `any` type (explicit or implicit)
- Type assertions (`as Type`) that bypass type checking
- Missing return types on exported functions
- Optional chaining chains longer than 3 levels (`a?.b?.c?.d?.e`)

**When `frameworkPatterns=dotnet`:**

- `public static` mutable fields used as service locator pattern
- Missing null checks on deserialized objects (JSON/XML)
- Casting with `(Type)obj` instead of pattern matching (`is Type t`)
- `object` or `dynamic` used where a generic `<T>` or interface fits

### 6.5 Documentation Sync & Docstring Coverage

Stale documentation is worse than no documentation — it actively misleads. This pass verifies that project documentation stays synchronized with code changes and that new/modified code has proper inline documentation.

**6.5.1 Docstring / Code Comment Coverage**

For every **new or modified** function, method, class, or exported constant in the diff, check whether it has documentation appropriate to its language:

- **TypeScript/JavaScript**: JSDoc comment (`/** ... */`) on exported functions, classes, interfaces, and type aliases. At minimum: a one-line description. Parameters and return types documented when not obvious from the signature. If the project's CLAUDE.md or rules specify a documentation language (e.g., "docstrings in Brazilian Portuguese"), flag docstrings written in the wrong language as **MEDIUM**.
- **C# / .NET**: XML documentation comments (`/// <summary>`) on public members.
- **Python**: Docstrings on public functions, classes, and modules.
- **Go**: Package-level comments and exported function comments per `godoc` convention.
- **Shell** (`.sh`, `.bash`): Header comment block describing script purpose and usage; inline comments on non-obvious logic. No formal docstring standard — flag only when a script has zero header comment.
- **Other languages**: Language-appropriate documentation conventions.

**Severity rules for missing docstrings:**
- Exported/public function or class without any doc comment → **HIGH** (public API contract undocumented)
- Internal/private function without doc comment → **LOW** (nice to have)
- Test callback (`describe`, `it`, `test`) without doc comment → **MEDIUM** if the project's CLAUDE.md or conventions explicitly require it, **LOW** otherwise
- Modified function where the doc comment no longer matches the behavior (e.g., doc says "returns X" but code now returns Y) → **HIGH** (actively misleading)

**6.5.2 Project Documentation Sync**

When the diff introduces new API endpoints, data models, configuration, features, or architectural patterns, verify that the corresponding project documentation was also updated in the same branch.

| What changed in code | Documentation to verify | Severity if missing |
|---------------------|------------------------|-------------------|
| New/modified API endpoints (routes, controllers) | OpenAPI/Swagger spec | **HIGH** |
| New/modified API endpoints | `README.md` API section (if one exists) | **MEDIUM** |
| New data model / DB migration / schema change | OpenAPI spec (if model surfaces in API), README data model section | **MEDIUM** |
| New route patterns, middleware, or architectural conventions | Framework rules file | **MEDIUM** |
| New frontend public routes | Framework rules file listing public routes | **MEDIUM** |
| New features visible to end users | `README.md` features/roadmap section | **LOW** |
| Changes to stack, dependencies, or project structure | `CLAUDE.md` or equivalent project instructions | **LOW** |
| New patterns, conventions, or corrections to stale info | `MEMORY.md` or equivalent persistent memory index | **LOW** |

**Skip this sub-pass** if the project has no documentation files at all (no README, no OpenAPI, no rules files). Don't penalize projects that haven't started documenting.

### 6.6 Race Conditions & TOCTOU (Time-of-Check to Time-of-Use)

Race conditions occur when code checks a state and then acts on it in separate operations, allowing another process/request to change the state in between.

Read `references/toctou-patterns.md` for the full pattern catalog with code examples. Apply these heuristics:

**Universal (all languages/frameworks):**

- **Check-then-act on database records**: Read query gating a write query without atomic operation.
  - CRITICAL when it involves tokens, payments, invites, or one-time-use resources
  - HIGH when it involves user records, resource limits, or state transitions

- **Read-modify-write on numeric fields**: Reading a value, computing in app code, then writing back. Concurrent requests cause lost updates. → **HIGH**

- **Business rules enforced only in application code**: Count/uniqueness/limit checks via app query + conditional logic instead of DB constraints. → **HIGH**

- **Read outside transaction, write inside**: Read before transaction block, body relies on that read without re-validating. → **HIGH**

- **File system check-then-act**: `exists()` / `stat()` followed by `read()` / `write()` in separate calls. → **MEDIUM**

- **Cache check-then-compute without coalescing**: Simple cache miss → compute → store without mutex. → **MEDIUM**

- **Shared mutable state without synchronization** (Java, C#, Go, Python): Reading shared variable and acting on it outside synchronized/lock block. → **MEDIUM**

When a check-then-act pattern is ambiguous (single-user CLI tool, idempotent reads, or code handles the race gracefully) — downgrade to LOW or skip.

### 6.7 Accessibility

Applies to any frontend framework that renders HTML.

**When `frameworkPatterns` is `react|vue|angular|node`:**

- **Icon-only buttons without accessible name**: `<button>` with only icon child, no `aria-label`. → **HIGH**
- **Form buttons without explicit type**: `<button>` in `<form>` without `type="button"`. → **MEDIUM**
- **Interactive elements without keyboard support**: Clickable `<div>` without `role`, `tabIndex`, `onKeyDown`. → **MEDIUM**
- **Images without alt text**: `<img>` without `alt` attribute. → **LOW**

### 6.8 Data Integrity & Schema Safety

- **Cascade delete on user/tenant-facing entities**: `ON DELETE CASCADE` on user/account/tenant FK. → **CRITICAL**
- **Missing database indexes on frequently-queried columns**: Junction tables or FKs without indexes. → **MEDIUM**
- **URL/link fields accepting dangerous protocols**: `javascript:`, `data:`, `vbscript:` accepted. → **CRITICAL**
- **Inconsistent validation schemas**: Same field validated differently across endpoints. → **HIGH**
- **Test fakes/mocks missing fields from real schema**: Fakes don't mirror all schema fields. → **MEDIUM**

---

## Severity Reference

| Severity | Criteria |
|----------|----------|
| **CRITICAL** | Security vulnerabilities, data loss risk, crashes in production, exposed secrets |
| **HIGH** | Bugs likely to manifest, missing error handling on user-facing flows, `any` on public API |
| **MEDIUM** | Code smell, minor Zen violations, missing tests for new logic, performance concerns |
| **LOW** | Style preferences, minor readability improvements, suggestions for future improvement |
