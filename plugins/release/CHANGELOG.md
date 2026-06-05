# Changelog — release

## [1.3.0] — 2026-04-01

### Changed

- Resolução de contribuidores passa a usar a GitHub commits API e, quando o autor não
  resolve por ela, faz fallback por cross-reference de org membership — entrega usernames
  reais do GitHub em vez de depender do nome de autor do git.

## [1.2.0] — 2026-03-25

### Added

- **Multi-stack project detection** — auto-detects project name from `.sln`, `.csproj`, `package.json`, `Cargo.toml`, `go.mod` (priority order)
- **`--path` filter** — filter commits/diffs to a subdirectory for monorepo component releases (e.g., `1.0.0 --path LicenceManager/`)
- **Multi-stack dependency detection** — detects dependency changes from `*.csproj`/`Directory.Build.props` (C#), `package.json` (Node), `go.mod` (Go), `Cargo.toml` (Rust), `pyproject.toml`/`requirements.txt` (Python)
- Quality rule #8: path filter scoping for commits and file changes

### Changed

- Release target branch now uses current branch (`git branch --show-current`) instead of hardcoded `main`
- Dependencies template section is now language-agnostic (removed hardcoded "Node.js, TypeScript")
- Description updated to mention multi-stack support

## [1.1.0] — 2026-03-25

### Fixed

- **Contributors listed wrong usernames** — git author names (`JorUge`, `Jorge Ferrari`) don't match GitHub usernames (`j0ruge`). Now resolves via `gh api` email lookup instead of `git log --format="%aN"`
- Exclude bot accounts (`noreply@anthropic.com`) from contributors list
- Same person with multiple git author names no longer appears as multiple contributors

### Changed

- Contributors section now uses `gh api /search/users?q=EMAIL` to resolve actual GitHub usernames
- Added quality rule #7: contributors must be resolved GitHub usernames, never fabricated

## [1.0.0] — 2026-03-16

### Added

- Initial release of the `release` plugin
- Automated GitHub Release creation via `gh CLI`
- Categorized release notes from git history (conventional commits)
- Dynamic project name detection (package.json or git directory name)
- PT-BR release notes with emoji-categorized sections
- Dependency diff analysis from package.json changes
- PR and contributor aggregation
