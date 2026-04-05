<div align="center">

# Chewiesoft Marketplace

*Skills and commands for Claude Code — CI/CD, code review, deployments, releases, and more.*

[![Plugins](https://img.shields.io/badge/plugins-6-blue?style=flat-square)](#available-plugins)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code-blueviolet?style=flat-square)](https://code.claude.com)
[![License](https://img.shields.io/badge/license-Proprietary-red?style=flat-square)](#)

</div>

[Installation](#installation) · [Plugins](#available-plugins) · [Auto-updates](#auto-updates) · [Team Distribution](#team-distribution) · [References](#references)

---

A curated plugin marketplace for [Claude Code](https://code.claude.com) by **Chewiesoft**. Each plugin packages production-ready skills and commands that integrate directly into your Claude Code workflow — no configuration needed beyond install.

## Installation

```bash
# Add the marketplace (pick one)
/plugin marketplace add j0ruge/skills_commands_manager          # via GitHub
/plugin marketplace add git@github.com:j0ruge/skills_commands_manager.git  # via SSH
```

Then install any plugin:

```bash
/plugin install codereview    # or: cicd, deploy, release, statusline, dotnet-wpf
```

> [!TIP]
> Keep plugins up to date with a single command:
> ```bash
> /plugin marketplace update
> ```

## Available Plugins

| Plugin | Version | Category | Description |
|--------|---------|----------|-------------|
| [**cicd**](#cicd) | 2.3.0 | Development | CI/CD troubleshooting for GitHub Actions, Docker, GHCR, and self-hosted runners |
| [**codereview**](#codereview) | 1.4.0 | Quality | Pre-PR code review with severity grading (A-F), TOCTOU detection, accessibility, and CodeRabbit PR resolver |
| [**deploy**](#deploy) | 1.4.0 | Development | Automated staging deployment with pre-flight checks and pipeline monitoring |
| [**release**](#release) | 1.3.0 | Development | GitHub Release creation with categorized notes, multi-stack and monorepo support |
| [**statusline**](#statusline) | 1.3.0 | Customization | Interactive status line setup — cross-platform (Bash + PowerShell), 9 sections |
| [**dotnet-wpf**](#dotnet-wpf) | 1.1.0 | Development | WPF toolkit — project audit, Fluent Design guide (90+ controls), MVVM migration, E2E testing |

---

## Plugin Details

<details>
<summary><strong>cicd</strong> — CI/CD Troubleshooting & Configuration</summary>

Unified troubleshooting and pipeline configuration for GitHub Actions, Docker, GHCR, and self-hosted runners. Auto-detects backend (Prisma/Biome) or frontend (Vite) projects and routes to specific references.

| Skill | Description |
|-------|-------------|
| `/cicd` | Troubleshoots and configures CI/CD pipelines — 30+ scenarios, 25 lessons learned |

**Highlights:** project-type detection, tagged troubleshooting (`[S]` shared / `[B]` backend / `[F]` frontend), Jest OOM fixes, Biome 2.x migration, stale Docker image cache handling.

</details>

<details>
<summary><strong>codereview</strong> — Automated Code Review</summary>

Stack-agnostic pre-PR code review built on **The Zen of Python** as a universal analysis framework. Five principles — *readability*, *explicitness*, *simplicity*, *flatness*, and *error handling* — applied as analysis lenses to any codebase.

| Skill | Description |
|-------|-------------|
| `/codereview` | Full pre-PR review — diffs against base branch, severity-rated findings (CRITICAL → LOW), final grade (A-F) |
| `/codereview:coderabbit_pr` | Resolves CodeRabbit bot comments on a GitHub PR — extracts, triages, fixes, runs regression tests, resolves GitHub conversations |

**Analysis layers:** Bug Detection · Security · Performance · Type Safety · Test Coverage · Documentation Sync · Race Conditions (TOCTOU) · Accessibility · Data Integrity

**Framework presets:** `react` (default) · `vue` · `angular` · `node` · `dotnet` · `generic`

</details>

<details>
<summary><strong>deploy</strong> — Automated Deployments</summary>

Automated deployment commands for staging and production pipelines via CD.

| Command | Description |
|---------|-------------|
| `/deploy:staging` | Syncs main ↔ develop, merges current branch, pushes to trigger CD Staging pipeline |

**Highlights:** auto-detects branch flow (develop vs feature), pre-flight checks (ESLint, TypeScript, Jest), pipeline monitoring via `gh run watch`.

</details>

<details>
<summary><strong>release</strong> — GitHub Release Automation</summary>

Auto-generates categorized release notes from git history and creates a GitHub Release via `gh` CLI.

| Command | Description |
|---------|-------------|
| `/release:release [VERSION] [--path DIR]` | Generates release notes and creates a GitHub Release |

**Multi-stack:** C#/.NET · Node.js · Go · Rust · Python
**Monorepo:** `--path` filter scopes commits to subdirectories
**Contributors:** resolved via GitHub API with org membership cross-reference

</details>

<details>
<summary><strong>statusline</strong> — Status Line Customization</summary>

Interactive wizard to configure Claude Code's status line — model info, context bar, git branch, cost tracking, and more.

| Command | Description |
|---------|-------------|
| `/statusline:setup` | Interactive setup wizard — sections, colors, emojis, separator |

**9 composable sections:** Model name · Context bar · Git branch · Project folder · Session cost · Duration · Lines changed · Token counts · Vim mode

**Cross-platform:** Bash + PowerShell, no jq dependency, Windows/Git Bash compatible.

</details>

<details>
<summary><strong>dotnet-wpf</strong> — .NET WPF Development Toolkit</summary>

Complete development toolkit for C#/.NET WPF desktop applications — from project setup to E2E testing.

| Skill | Description |
|-------|-------------|
| `/dotnet-wpf:dotnet-desktop-setup` | Configures and audits .NET desktop projects for Claude Code |
| `/dotnet-wpf:dotnet-wpf-design` | Fluent Design guide — layout patterns, typography, 90+ WPF-UI controls catalog |
| `/dotnet-wpf:dotnet-wpf-mvvm` | WinForms → WPF MVVM migration with CommunityToolkit.Mvvm and WPF-UI |
| `/dotnet-wpf:dotnet-wpf-e2e-testing` | FlaUI + xUnit E2E testing — Page Objects, AutomationId patterns, CI/CD setup |

</details>

## Auto-updates

For private repo auto-updates at startup, set a GitHub token with `repo` scope:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

> [!IMPORTANT]
> Generate a token at [github.com/settings/tokens](https://github.com/settings/tokens) with the `repo` scope.

## Team Distribution

Projects that clone this repo get automatic marketplace discovery via `.claude/settings.json`. When team members trust the folder, Claude Code prompts them to install the marketplace — no manual setup needed.

## References

- [Plugin Marketplaces — Claude Code Docs](https://code.claude.com/docs/en/plugin-marketplaces)
- [Plugins Reference — Claude Code Docs](https://code.claude.com/docs/en/plugins-reference)

---

<div align="center">
Proprietary — <strong>j0ruge</strong>. All rights reserved.
</div>
