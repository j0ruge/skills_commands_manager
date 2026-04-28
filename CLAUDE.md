# CLAUDE.md

## Project Overview

**chewiesoft-marketplace** — a dual-platform plugin marketplace owned by **j0ruge**. Distributes skills and commands for **Claude Code** and **Cursor**, developed exclusively by the owner.

For Claude Code, this repository follows the [Claude Code Plugin Marketplace](https://code.claude.com/docs/en/plugins-reference) specification.
For Cursor, skills are installed via the interactive `install.py` script at the repo root.

## Marketplace Structure

```
skills_commands_manager/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace catalog (lists all plugins)
├── plugins/                      # Plugin directories (one per plugin)
│   └── .gitkeep
├── .claude/
│   ├── commands/                 # Speckit commands (SDD dev tools, NOT marketplace content)
│   └── settings.json             # Team distribution config
├── .specify/                     # SDD framework (dev tooling, NOT marketplace content)
├── install.py                    # Interactive installer (Claude Code + Cursor)
└── CLAUDE.md
```

### Key files

- **`.claude-plugin/marketplace.json`** — The marketplace catalog. Lists all available plugins with their source paths. This is the entry point Claude Code reads when registering the marketplace.
- **`plugins/`** — Each subdirectory is a self-contained plugin with its own `.claude-plugin/plugin.json` manifest.
- **`.claude/settings.json`** — Registers this repo as a known marketplace for team auto-discovery.
- **`install.py`** — Interactive installer. Handles both Claude Code (shows installation commands) and Cursor (copies and adapts skills to `~/.cursor/skills/` or `.cursor/skills/`).

### Platform Compatibility

Each `plugin.json` includes a `platforms` field declaring which platforms support the plugin:
- `["claude-code", "cursor"]` — available on both platforms
- `["claude-code"]` — Claude Code only (e.g., `statusline`)

## Adding a New Plugin

1. Create a directory under `plugins/`:
   ```
   plugins/my-plugin/
   ├── .claude-plugin/
   │   └── plugin.json        # Plugin manifest (name, description, author, etc.)
   ├── commands/               # Command definitions (.md files)
   ├── skills/                 # Skill definitions (SKILL.md files)
   ├── agents/                 # Agent definitions (.md files) [optional]
   └── hooks/                  # Hook configurations [optional]
   ```

2. Create `plugins/my-plugin/.claude-plugin/plugin.json`:
   ```json
   {
     "name": "my-plugin",
     "description": "What this plugin does",
     "author": {
       "name": "Chewiesoft"
     },
     "version": "1.0.0",
     "keywords": ["relevant", "tags"],
     "platforms": ["claude-code", "cursor"],
     "commands": "./commands",
     "skills": "./skills",
     "agents": "./agents",
     "hooks": "./hooks"
   }
   ```
   Set `"platforms": ["claude-code"]` if the plugin uses Claude Code-specific APIs (e.g., status line, MCP tools) and cannot work in Cursor.

3. Register the plugin in `.claude-plugin/marketplace.json`:
   ```json
   {
     "plugins": [
       {
         "name": "my-plugin",
         "source": "./plugins/my-plugin",
         "version": "1.0.0",
         "description": "Brief plugin description shown in Discover tab",
         "category": "development",
         "keywords": ["relevant", "tags"],
         "platforms": ["claude-code", "cursor"]
       }
     ]
   }
   ```

4. If the plugin supports Cursor, add a mapping entry to `CURSOR_SKILL_MAP` in `install.py` so the installer knows how to copy and adapt the content.
   - For skills: add an entry with `"source_type": "skill"` pointing to the skill directory.
   - For commands: add an entry with `"source_type": "command"` and a `"cursor_description"` for Cursor's trigger-based discovery.

## Plugin Source Options

When registering plugins in `marketplace.json`, the `source` field supports:
- **Relative path**: `"./plugins/my-plugin"` — local directory in this repo
- **GitHub**: `{ "source": "github", "repo": "j0ruge/plugin-repo" }` — from a GitHub repository
- **npm**: `{ "source": "npm", "package": "@j0ruge/my-plugin" }` — from npm registry

## Installation (End Users)

### Cursor

```bash
git clone git@github.com:j0ruge/skills_commands_manager.git
cd skills_commands_manager
python install.py
```

The installer prompts for platform (Claude Code / Cursor / Both) and install location, then copies and adapts the skills automatically.

**Cursor caveat:** Cursor (as of 2026) does not auto-load skills from a global directory — only project-local `.cursor/skills/` is read by the agent. Run `install.py` inside each project and pick the **Project** option. The optional **Staging cache** writes to `~/.cursor/skills/` as a master copy you mirror manually.

### Claude Code

Users can install this marketplace in Claude Code:
```
/plugin marketplace add <path-or-url-to-this-repo>
```

Or clone the repo and add locally:
```
/plugin marketplace add ./path/to/skills_commands_manager
```

## Speckit (Development Tooling)

The `.claude/commands/speckit.*` commands and `.specify/` directory are **development tools** (Specification-Driven Development framework) used to build this project. They are NOT part of the marketplace content and are not distributed as plugins.

Available speckit commands: `specify`, `clarify`, `plan`, `analyze`, `tasks`, `implement`, `checklist`, `constitution`, `taskstoissues`.

## Session Rules

- At the end of every coding session, update `README.md` to reflect the current state of the marketplace — especially the **Available Plugins** table (sync with `.claude-plugin/marketplace.json`).

## Git

- **Main branch**: `main`
