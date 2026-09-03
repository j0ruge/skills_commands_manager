# Configuration

> **Defaults target TypeScript/React projects. Override any value to adapt the skill to a different stack (Vue, Angular, Python, Go, Node-only, etc.).**

## Default Values

| Variable | Default | Description |
|---|---|---|
| `baseDir` | `src/` | Root directory that contains application source files. |
| `fileExtensions` | `["ts", "tsx"]` | Extensions considered source code. Extend with `["js","jsx","vue","svelte","py","go"]` etc. |
| `testFilePatterns` | `["**/*.{test,spec}.{ts,tsx}", "**/test/**"]` | Globs that identify test files (resolved relative to `baseDir`). |
| `generatedDirs` | `["src/components/ui/**", "prisma/**", "**/generated/**"]` | Globs for auto-generated or UI-lib directories — classified as `UI_LIB` (reduced-rigor). |
| `uiLibReducedRigor` | `true` | When `true`, `UI_LIB` files receive only CRITICO/ALTO checks. Set to `false` to apply full analysis. |
| `frameworkPatterns` | `react` | Framework hint controlling which framework-specific rules are active. Options: `react` \| `vue` \| `angular` \| `node` \| `dotnet` \| `generic`. |
| `configFilePatterns` | `["*.config.*", "tsconfig*", ".env*", "package.json"]` | Globs matched as CONFIG files. |
| `styleFilePatterns` | `["**/*.css", "**/*.scss", "**/*.less"]` | Globs matched as STYLES files. |
| `sweep` | `pr` | Scope of the dead-code sweep (pass 6.9). `pr` = Bucket A only (symbols this PR introduced or orphaned); `full` = also run Bucket B (repo-wide tooling over code the PR did not touch, capped). Focus `dead-code` implies `full`. |

> **Note:** The array values in the table above are in JSON format for clarity only. When overriding, use comma-separated values without brackets (see Override Syntax below).

## Override Syntax

When `$ARGUMENTS` contains key-value overrides, apply them before classification.

**Format**: `key=value` pairs separated by spaces. Array values use commas.

**Examples**:

```text
# Python project
/codereview baseDir=app/ fileExtensions=py testFilePatterns=**/test_*.py frameworkPatterns=generic

# Vue project
/codereview baseDir=src/ fileExtensions=ts,vue frameworkPatterns=vue

# Node-only project (no UI framework)
/codereview fileExtensions=ts,js frameworkPatterns=node

# Disable reduced rigor for generated files
/codereview uiLibReducedRigor=false

# C#/.NET WPF project
/codereview fileExtensions=cs,xaml testFilePatterns=**/*Tests.cs,**/*.Tests/**/*.cs frameworkPatterns=dotnet generatedDirs=**/obj/**,**/bin/**,**/*.Designer.cs configFilePatterns=*.csproj,*.sln,*.props,appsettings*.json

# C#/.NET Web API (ASP.NET Core)
/codereview fileExtensions=cs testFilePatterns=**/*Tests.cs frameworkPatterns=dotnet

# C#/.NET minimal — just set framework, use sensible auto-detection
/codereview fileExtensions=cs frameworkPatterns=dotnet
```

Overrides are applied on top of defaults — only the specified values change; unmentioned values keep their defaults.
