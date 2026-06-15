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

## Additional Detection Passes (6.1–6.10)

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

**6.5.3 Contract Drift in Tests**

Tests that assert literal-by-literal contracts about exported constants (enums, tuples, schema shapes) silently rot when the exported value gains or loses members and the test is not updated in the same PR. The test keeps passing on every other branch until the drift produces a real conflict — at which point the failure looks "pre-existing / from another feature" and gets dismissed instead of root-caused.

Apply this sub-pass whenever the diff modifies an exported constant of the form `export const X = [...] as const` (or a Zod / Yup / TS literal-union schema). For each such symbol `X` modified:

1. Grep the codebase (not just the diff) for usages: `expect(X).toEqual(`, `expect(X).toStrictEqual(`, `expect(X).toMatchObject(`, `assertEquals(X,`, `assert.deepEqual(X,`, and equivalent in the project's test framework.
2. For each hit, compare the asserted literal's length and content against the current export.
3. If the asserted literal is **shorter** than the current export (test asserts old contract; export grew) **or** has different members (test asserts old contract; export was reshaped) → flag.

**Severity:**
- **HIGH** when the exported symbol is part of a public API contract (Zod schema in `shared-api-types`, exported enum used cross-package, OpenAPI-mirrored constant). A stale assertion here means the suite is no longer guarding the contract — CI will go red on the next refactor that touches it, the failure will look unrelated, and someone will dismiss it as drift.
- **MEDIUM** when the constant is internal (single-module, not exported beyond the package) and the test is exercising it as fixture validation rather than contract guard.
- **LOW** when the asserted literal is *longer* than the current export (test still passes — superset; flag only as cleanup suggestion).

**Output format**: include the constant symbol, the test file path, and a one-line diff showing `asserted [N items] vs current export [M items]`. Example: `FORMA_PAGAMENTO: test asserts [4 items: BOLETO_30_DIAS, BOLETO_60_DIAS, ANTECIPADO, A_VISTA] but export has [7 items]`.

**Why this pass exists**: the v1.13.0 case that motivated this sub-pass — a contracts test in `@sales-quote/shared-api-types` asserted `FORMA_PAGAMENTO.toEqual([...4 items])` while the exported tuple had 7. The PR that restored the 3 legacy values (with an explicit docstring documenting the rollback) did not touch the test. The test stayed red on every branch for weeks. Each new contributor's `npm test` lit up the same red row; each one reproduced "fails on baseline too" via `git stash` and dismissed it. Static review at the originating PR's review time would have caught it deterministically — the diff modified the const, the test asserted the old shape, and a grep across the codebase makes the mismatch trivially visible. This is the same family as 6.5.2 (project docs drift when code changes) generalized to test artifacts that assert literal contracts.

**Skip this sub-pass** when:
- The constant being modified is not exported (purely internal symbol with no test consumers).
- The test file is also in the diff with a matching update (the developer already kept them in sync — confirm by re-reading the test diff, not just file path).

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

### 6.9 Dead Code & Unused Symbols

Dead code is the inverse of a bug: it doesn't break anything, it just *accumulates* — unread, untested, and silently misleading the next reader into thinking it matters. Left alone it bloats build output, hides real bugs (a "fixed" path replaced but the old one left wired), and rots into broken references no one notices because nothing runs it. This pass surfaces it and **recommends cleanup** — it never deletes anything (the skill is strictly read-only).

**Executor — read this first**: unlike passes 6.1–6.8 and 6.10, this pass is **NOT run by the per-file sonnet agents**. Each per-file agent sees only one file plus its diff, so it physically cannot tell whether an exported symbol is referenced *elsewhere* in the repo. Dead-code detection is inherently a **whole-repo reference-graph** question. It is therefore executed by the dedicated **Dead Code Sweep agent (Phase B2 in `SKILL.md`)**, which has the changed-file list, the diff, and grep/tooling access to the entire repository. The per-file agents must NOT attempt 6.9.

**Scope is hybrid** — two buckets, reported separately:

- **Bucket A — introduced or orphaned by THIS PR (primary, always reported).** Dead code the diff *created* or *exposed*. This is the part that belongs to the PR under review and is the most actionable:
  - **Newly-added-but-unused**: a symbol (function/class/const/export/file) added in this diff that nothing references yet.
  - **Diff-orphaned**: the diff removed the last caller/import of an existing symbol, or deleted the last importer of a file, leaving it dead. The PR *caused* this — it's a loose end the author should resolve before merge.
- **Bucket B — pre-existing (secondary, capped summary).** Dead code that already existed and this PR didn't touch, surfaced opportunistically by repo tooling. Label it **"pre-existing (not introduced by this PR)"** and **cap it** (e.g. top ~10 by impact + a total count) so it never drowns the PR-relevant findings. This is the "keep the project healthy" signal — useful, but it must not turn every small PR into a repo-wide audit dump.

**Detection categories** (apply to both buckets where relevant):

- Unused **exports** (exported symbol referenced **nowhere at all** — including within its own file). If the symbol *is* used inside its defining file but has no external importers, that's **over-export**, not dead code — see the over-export guardrail below.
- **Orphaned files** (a module that exports things but is imported by nothing).
- Unused **imports**, **local variables**, and **private members/fields/methods**.
- **Unreachable code** (statements after `return` / `throw` / `break` / `continue`, or inside an always-false branch).
- **Unused dependencies** (a `package.json` / `requirements` entry no longer imported anywhere; or a dep the diff stopped using).

**Deepsearch method** (the grep fallback — always available, no tooling required):

1. For each symbol defined or exported in the changed files, grep the **whole repo** (excluding the defining file) for references — not just `import` lines but name usages, **and references in non-code files**: HTML/JSX templates, JSON/YAML config, SQL, route manifests, DI registration files, `.env`. A symbol used only from a template is **not** dead.
2. Zero references **AND** not part of the public API surface **AND** not framework/dynamically wired → candidate (apply the guardrails below before flagging).
3. **Diff-orphan check**: when the diff deletes a call/import, grep the remaining repo for any other reference to that target; if none remain → it became dead in this PR (Bucket A).

**Opportunistic tooling** (read-only — same pattern as ggshield/gitleaks in pass 6.10): if any of these are on `PATH` / runnable in the repo, use them and **merge + dedup** (`{file, symbol, kind}`) with the grep results; tool-surfaced whole-repo findings feed **Bucket B**:

- TS/JS: `npx knip`, `npx ts-prune`, `npx depcheck` (deps), ESLint `no-unused-vars`.
- Python: `vulture`, `ruff` (`F401` unused import, `F811` redefinition, `F841` unused local).
- .NET/C#: Roslyn analyzers `IDE0051` (unused private member) / `CS0169` surfaced via `dotnet build` warnings.
- Go: `deadcode`, `staticcheck` (`U1000`).
- Rust: `cargo build` `dead_code` warnings, `cargo +nightly udeps` (deps).

If none are available, say so in the agent's notes and rely on the grep deepsearch — do **not** treat "no tooling" as "no dead code".

**False-positive guardrails — the heart of this pass. Be conservative; recommending deletion of live code is worse than missing some dead code.** Do NOT flag (or flag only at **LOW** with an explicit *"verify — may be referenced via X"* note) when:

- **Public API surface**: the symbol is a declared package entry point (`main`/`module`/`exports` in `package.json`, a library crate's `pub` items, a barrel `index.ts` / `__init__.py` re-export, a published SDK function). Absence of *internal* references doesn't mean it's unused — external consumers are invisible to the repo grep.
- **Framework / dynamic wiring** (invisible to a static grep): route handlers, DI-registered services, decorators (`@Injectable`, `@Component`, `@EventHandler`, `[Route]`), reflection, dynamic `import()` / `require()` with computed paths, string-keyed registries/factories, ORM entities, (de)serialization targets, CLI command auto-discovery, test auto-discovery.
- **Referenced from non-code files** (templates, config, SQL, manifests) — see deepsearch step 1.
- **Re-exports / barrels**: a symbol re-exported through an index that is itself consumed is *used*.
- **Test-only utilities**: a helper used only by tests is **not** dead — tests are real consumers.
- **Conditional compilation / platform-specific**: `#if`, `Platform.OS === ...`, feature-flag-gated code, `__DEV__` blocks.
- **Just-added scaffolding**: a symbol added in *this* diff but not yet wired may be intentional groundwork for a follow-up. Flag at **LOW** with *"added but unused — intentional scaffolding or forgotten wiring?"* rather than asserting it's dead.
- **Over-exported (used only within its own file)**: a symbol that *is* referenced inside its defining file but has no external importers is **not dead** — `knip`/`ts-prune` report it as an "unused export" because they only count *cross-file* references. The fix is to **drop the `export` keyword** (make it module-private), **not delete the symbol**. Flag at **LOW** as cleanup with *"used only in-file — remove `export`, keep the symbol."* (Verify by grepping the symbol within its own file before recommending anything.) Real case that motivated this: a `DefField` helper used 11× in its own module, reported as an unused export — deleting it would have broken the page.
- **Regenerable / generated scaffolding** under `generatedDirs` (default `src/components/ui/**`, `**/generated/**`): design-system primitives (e.g. shadcn/ui components re-addable via `npx shadcn add`) and codegen output. Tooling like `knip` surfaces unused ones **in bulk** — a 30-file dump that buries the PR-relevant findings. Keep these in **Bucket B**, **Low confidence**, lean on the cap, and label them *"regenerable scaffolding (not introduced by this PR)"* — do **not** present them as actionable app dead code unless the diff itself orphaned one.

Every finding carries a **Confidence** (High / Medium / Low) reflecting how many guardrails it cleared. A plain unreachable-statement-after-`return` is High confidence; an unreferenced exported function in a library package is Low.

**Severity** — dead code is **hygiene, never a blocker**:

- **MEDIUM** when the diff itself orphaned something (Bucket A diff-orphan — the PR left a loose end the author should close) **or** a whole file is orphaned.
- **LOW** for everything else (newly-added-but-unused scaffolding, pre-existing tooling-surfaced dead code, unused imports/locals, cleanup suggestions).
- **Never CRITICAL or HIGH. This pass never forces the grade to F and never blocks a PR.** It is a cleanliness recommendation, not a gate. (Contrast pass 6.10, which always blocks.)

**Output format**: include the symbol/file, the kind (unused export / orphaned file / unreachable / unused import / unused dependency / diff-orphaned), the location, the bucket (PR / pre-existing), the confidence, and a one-line recommended cleanup. Populate the **🧹 Dead Code & Cleanup** section in the report (see `references/report-template.md`); findings flow into Recommended Actions → *Consider Fixing (MEDIUM/LOW)* and contribute to the **Code Quality (Zen)** grade rationale.

### 6.10 Hardcoded Secrets Detection

This pass approximates what a dedicated secret scanner (GitGuardian, gitleaks, trufflehog) would flag. It exists **because CI secret scanners will block the PR on push** — catching these locally saves the user from having to rotate credentials and rewrite git history after the fact.

**Detection is deterministic, not LLM-simulated** (since v1.8.0). The script `scripts/scan_secrets.py` (invoked via `scripts/scan_secrets.sh`) applies the regex catalog below using Python's `re` engine, plus optionally `ggshield`/`gitleaks` if installed. Phase A's haiku agent runs the script over the unified diff and the output is the **authoritative** input to the Secrets Detection table. Sonnet agents in Phase B still apply this pass for context-aware nuance (e.g. spotting a custom DSL where the keyword is non-standard) but their findings are supplemental — see Phase C merge logic in `SKILL.md`. Why deterministic: LLMs aren't regex engines, and substring shapes like `initialPassword: '...'` (where `password` appears as a suffix) are easy to miss.

**Critical rule: this pass applies to ALL file categories except `EXCLUDED` and `DOCS`** — that includes `CODE`, `TESTS`, `CONFIG`, `UI_LIB`, and `STYLES`. A hardcoded password in `auth.test.ts` is exactly as leaked as one in `server.ts`; GitGuardian does not distinguish, and neither should this pass. This is intentional: test fixtures are one of the most common sources of real-world leaks, because developers underestimate the risk.

**Always-on**: even when a focus area is specified (e.g. `performance`), pass 6.10 still runs. Never skip it. Secrets in a diff are the one finding the user cannot afford to miss.

**Single source of truth**: the table below is the conceptual catalog. The script `scripts/scan_secrets.py` carries the executable form. **Adding/changing a pattern requires updating both** — a code-review/audit checklist for this skill should verify the two stay in sync. There is no automated guard yet (future work).

**Patterns to flag** (each `match → CRITICAL` unless noted otherwise):

| Kind | Pattern (regex-ish, conceptual) | Notes |
|---|---|---|
| Generic password literal | `(password\|passwd\|pwd\|senha\|secret\|api[_-]?key\|apikey\|access[_-]?token)\s*[:=]\s*["'][^"']{4,}["']` | Most common leak shape. See exceptions below. |
| JWT / eyJ prefix | `eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+` | Real JWTs, often left in tests. |
| Bearer token | `Bearer\s+[A-Za-z0-9_\-\.]{20,}` | Inline in fetch/axios calls or test fixtures. |
| PEM private key block | `-----BEGIN (RSA \|OPENSSH \|EC \|DSA \|PGP )?PRIVATE KEY-----` | |
| AWS Access Key ID | `AKIA[0-9A-Z]{16}` | |
| AWS Secret literal | `aws_secret_access_key\s*=\s*["'][^"']{20,}["']` | |
| Google API key | `AIza[0-9A-Za-z_\-]{35}` | |
| Slack token | `xox[baprs]-[A-Za-z0-9\-]{10,}` | |
| GitHub PAT / app token | `gh[pousr]_[A-Za-z0-9]{30,}` | `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_` |
| Credentialed connection string | `(postgres\|postgresql\|mysql\|mongodb\|mongodb\+srv\|redis\|amqp)://[^:@/\s]+:[^@/\s]+@` | The `:password@` segment is the tell. |
| Stripe secret key | `sk_(live\|test)_[A-Za-z0-9]{20,}` | Test keys are lower risk but still flag — rotation policy differs per org. |
| `.env`-shaped assignment | Line matching `^(SECRET_KEY\|DATABASE_URL\|API_KEY\|JWT_SECRET\|PRIVATE_KEY\|CLIENT_SECRET\|AUTH_TOKEN)\s*=\s*\S.+` in a non-`.env.example` / non-`.env.sample` file | Treat `.env.example` / `.env.sample` / `.env.template` as allowed placeholders *only if* the value looks like a placeholder (see exceptions). |

**Why regex AND scanners (when available)**: the skill cannot guarantee `ggshield` or `gitleaks` is installed on the user's machine, so the script ships its own Python regex pass that always runs. When `ggshield` or `gitleaks` IS on `PATH`, the script invokes them too and merges results (dedup by `{file, line, kind}`). The skill is still read-only — `Bash` invocations from the haiku agent are pure scans (`gh`/`grep`/`ggshield secret scan`) with no mutation. Always recommend the user also install `ggshield pre-commit` as a durable defense for future commits.

**Exceptions (do not flag):**

- Value is a runtime lookup: `process.env.FOO`, `import.meta.env.FOO`, `config.get("foo")`, `Deno.env.get(...)`, `os.environ[...]`, `ConfigurationManager.AppSettings[...]`.
- Value is a well-known placeholder: `""`, `null`, `undefined`, `"CHANGE_ME"`, `"changeme"`, `"xxx"`, `"your-key-here"`, `"<...>"`, `"***"`, `"REPLACE_ME"`, `"redacted"`.
- `.env.example` / `.env.sample` / `.env.template` where the RHS is a placeholder or empty.
- The match is inside a comment explicitly describing the shape of a secret (e.g. `// Format: sk_live_...`) with no literal value.

**Test-file nuance**:

- Inline literal passwords in test body (`password: "test123"`, `expect(user.password).toBe("s3cret")`) → **HIGH**, not CRITICAL. They're less dangerous than prod keys but still rejected by GitGuardian, so still blocking.
- Same secret pulled from `process.env.TEST_PASSWORD` or imported from a `fixtures/` module or `testFactory` helper → do not flag.
- `.spec.ts` / `.test.ts` fixtures that use **obviously fake** values like `"password123"`, `"test"` → still flag at **HIGH**. GitGuardian's `Generic Password` detector fires on these; the review must warn the user.

**Multi-occurrence signal**: if the same pattern (same regex family) fires **3+ times within one file** or **5+ times across the PR**, report a single aggregate finding with count and line ranges, and escalate severity to CRITICAL regardless of category. This is the "systemic leak" signal — one slip is a mistake, ten is a pattern.

**Remediation block** (include under every pass-6.10 finding, verbatim or lightly adapted):

> **Remediation** (per [GitGuardian best practices](https://blog.gitguardian.com/secrets-api-management/)):
>
> 1. **Understand the blast radius**: search the repo for other usages of this secret; identify which external service it authenticates to.
> 2. **Replace with an environment variable or secret manager**. For tests, read from `process.env.TEST_<NAME>` or a fixture that resolves via env. Never commit the real value, even to a test file — CI scanners don't distinguish.
> 3. **Rotate the secret** at the provider. Assume the value in the diff is already compromised the moment it lands on a branch that anyone else can fetch. Revoke first, rotate second.
> 4. **Consider rewriting git history** (`git filter-repo` or BFG Repo-Cleaner) *only* if the secret hasn't been pushed yet or the repo is private and coordinated with the team — history rewrites break other contributors' clones.
> 5. **Install `ggshield` pre-commit hook** (`pip install ggshield && ggshield install -m local`) to catch the next leak on your machine before it leaves.

**Output format for pass 6.10 findings**: in addition to the standard finding format, populate the "Secrets Detection" table in the report (see `references/report-template.md`). Any ≥1 finding in this pass forces overall grade to **F** and prepends a BLOCKED banner to the report.

---

## Severity Reference

| Severity | Criteria |
|----------|----------|
| **CRITICAL** | Security vulnerabilities, data loss risk, crashes in production, exposed secrets |
| **HIGH** | Bugs likely to manifest, missing error handling on user-facing flows, `any` on public API |
| **MEDIUM** | Code smell, minor Zen violations, missing tests for new logic, performance concerns |
| **LOW** | Style preferences, minor readability improvements, suggestions for future improvement |
