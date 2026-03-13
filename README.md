# Chewiesoft Marketplace

Plugin marketplace for Claude Code — skills and commands for development workflows.

## Available Plugins

| Plugin | Version | Description |
|--------|---------|-------------|
| **cicd** | 2.0.0 | Unified CI/CD troubleshooting and pipeline configuration for GitHub Actions, Docker, GHCR, and self-hosted runners |
| **deploy-staging** | 1.2.0 | Automated deployment to staging via CD pipeline — syncs main with develop, merges feature branches, pushes to trigger staging pipeline, and verifies the run |

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
