# Chewiesoft Marketplace

Plugin marketplace for Claude Code — skills and commands for development workflows.

## Available Plugins

| Plugin | Version | Description |
|--------|---------|-------------|
| **cicd** | 2.3.0 | Unified CI/CD troubleshooting and pipeline configuration for GitHub Actions, Docker, GHCR, and self-hosted runners |
| **deploy** | 1.3.0 | Automated deployment commands — staging and production pipelines via CD |
| **codereview** | 1.2.0 | Stack-agnostic code review powered by the Zen of Python — 5 analysis principles, bug/security/performance/type-safety detection, test coverage mapping, and A-F grading. Presets: TypeScript/React (default), C#/.NET (`dotnet`), Vue, Angular, Node, Python, Go. |
| **statusline** | 1.1.0 | Interactive setup for Claude Code status line — cross-platform (Bash + PowerShell) |
| **release** | 1.0.0 | Automated GitHub Release creation with categorized release notes from git history |

### codereview

Automated pre-PR code review built on **The Zen of Python** (PEP 20) as a universal, language-agnostic analysis framework. Five timeless principles — *readability*, *explicitness*, *simplicity*, *flatness*, and *error handling* — are applied as analysis lenses to any codebase, regardless of language or framework.

**Analysis layers:**
- **Zen Principles** — readability, explicit > implicit, simple > complex, flat > nested, errors never silent
- **Bug Detection** — null access, race conditions, async pitfalls, equality checks
- **Security** — exposed secrets, injection vectors, UI leaks, input validation
- **Performance** — unnecessary allocations, missing memoization, per-call instantiation
- **Type Safety** — unsafe casting, missing exhaustive checks, service locator anti-patterns
- **Test Coverage** — maps production files to tests, flags stale or missing coverage

**Framework presets** (`frameworkPatterns`):
- `react` (default) / `vue` / `angular` / `node` — web-frontend checks (hooks, JSX, XSS, memoization)
- `dotnet` — C#/.NET checks (async void, IDisposable, MessageBox in services, MVVM violations)
- `generic` — universal checks only

| Skill | Description |
|-------|-------------|
| `/codereview` | Full pre-PR review — diffs against base branch, severity-rated findings (CRITICAL to LOW), and a final grade (A-F) |
| `/codereview:coderabbit_pr` | Resolves CodeRabbit bot comments on a GitHub PR — extracts, triages, fixes, and runs regression tests |

### deploy

| Command | Description |
|---------|-------------|
| `/deploy:staging` | Syncs main with develop, merges current branch into develop, and pushes to trigger the CD Staging pipeline |
| `/deploy:production` | *(planned)* |

### release

| Command | Description |
|---------|-------------|
| `/release:release` | Automatically generates release notes from the latest release and creates a new GitHub Release via gh CLI |

### statusline

| Command | Description |
|---------|-------------|
| `/statusline:setup` | Interactive wizard to configure status line sections, colors, emojis, and separator |

## Installation

### Add the marketplace

```bash
# Via GitHub (requires repo access)
/plugin marketplace add ChewieSoft/skills_commands_manager

# Via SSH
/plugin marketplace add git@github.com:ChewieSoft/skills_commands_manager.git

# Via local clone
git clone git@github.com:ChewieSoft/skills_commands_manager.git
/plugin marketplace add ./skills_commands_manager
```

### Install a plugin

Once the marketplace is added, browse and install plugins:

```bash
/plugin install cicd
```

### Update plugins

```bash
/plugin marketplace update
```

## Auto-updates (private repo)

For background auto-updates at startup, set a GitHub token with `repo` scope in your shell config (`~/.zshrc` or `~/.bashrc`):

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

Generate a token at: https://github.com/settings/tokens

## Team Distribution

Projects that clone this repo get automatic marketplace discovery via `.claude/settings.json`. When team members trust the folder, Claude Code will prompt them to install the marketplace.

## References

- [Plugin Marketplaces — Claude Code Docs](https://code.claude.com/docs/en/plugin-marketplaces)
- [Plugins Reference — Claude Code Docs](https://code.claude.com/docs/en/plugins-reference)

## License

Proprietary — Chewiesoft. All rights reserved.
