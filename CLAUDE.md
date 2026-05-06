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

## Skill description guidelines

The `description` field in SKILL.md frontmatter and `marketplace.json` is the
primary trigger mechanism. When the combined skill listing exceeds Claude
Code's `skillListingBudgetFraction` (default 1% of context), descriptions are
**dropped silently** and the skills lose their trigger. Keep descriptions tight
so this never happens.

### DO
- Keep `description` ≤ 350 characters (hard cap: 500). Fits one line in
  `/skills` output.
- Open with one sentence describing the function — not "Use this skill when…".
- Follow with 1–2 distinctive capabilities that disambiguate from neighbors.
- End with a single trigger list of ≤ 8 keywords, prefixed `Triggers — `.
- Pick **one language** per description (English preferred for cross-team
  reach). Body of the skill can stay bilingual.
- Mirror the exact same description in `SKILL.md` frontmatter and the matching
  entry in `.claude-plugin/marketplace.json` — single source of truth.
- Run `/doctor` after adding or editing skills. If it reports any descriptions
  dropped, trim before merging.

### DON'T
- Don't enumerate every quirk, capability, file, or use-case in the description
  — that belongs in the SKILL.md body or in a `references/` file.
- Don't write the trigger list twice (once in prose "Use when X, Y, Z" and
  again as a bullet list). Pick one form, prefer the explicit `Triggers — `
  line.
- Don't write "Use this skill SEMPRE / ALWAYS / PROACTIVELY" — it's noise that
  triggers nothing extra and eats budget.
- Don't mix languages inside a single description (PT + EN). It doubles the
  text without doubling the recall.
- Don't paste the raw `keywords:` list into `description:` — Claude already
  sees `keywords` separately.
- Don't ship hash-suffixed copies (`my-skill-2f5564a0.md`) in
  `~/.claude/commands/`. If they appear, they're orphans from old installs and
  should be deleted.

### Why
Each dropped description silently disables a skill's trigger — Claude only
sees the name, never the "when to use it" text. Symptoms: skills that used to
work stop firing on their canonical phrases, and `/doctor` shows
`N descriptions dropped`. The fix is always trimming descriptions, not raising
the budget (raising costs ~5k tokens per session and consumes rate limits
faster).

## Identity & canonical repository

**Chewiesoft is the fictional software company / brand. j0ruge is the GitHub
user that owns and publishes everything under that brand.** The two names
coexist by design — Chewiesoft is product branding, j0ruge is the GitHub
account that ships it.

| Layer | Value | Where it appears |
|---|---|---|
| Brand / company (fictional) | **Chewiesoft** | `author.name` in `plugin.json`, `owner.name` in `marketplace.json`, README/install.py headings |
| Marketplace slug | **chewiesoft-marketplace** | `name` in `.claude-plugin/marketplace.json`, key in `.claude/settings.json` |
| GitHub owner / user | **j0ruge** | All clone/install URLs, `git remote` |
| Canonical repo URL | **`https://github.com/j0ruge/skills_commands_manager`** | All install snippets, README, this CLAUDE.md |

Chewiesoft is **not** a GitHub organization. The repo lives under the personal
user `j0ruge`.

### DO
- Use `j0ruge/skills_commands_manager` in every install/clone snippet
  (`README.md`, this `CLAUDE.md`, `install.py`, `.claude/settings.json`,
  `/plugin marketplace add` examples).
- Keep `"author": { "name": "Chewiesoft" }` in plugin manifests and
  `"chewiesoft-marketplace"` as the marketplace slug — those are branding,
  not repo references.
- When introducing a new plugin, use the same pairing: `author.name =
  "Chewiesoft"` and any source/clone URL pointing at
  `j0ruge/skills_commands_manager`.

### DON'T
- Don't write URLs like `Chewiesoft/skills_commands_manager` or
  `chewiesoft/...` as if Chewiesoft were a GitHub org — it isn't. The user
  `j0ruge` owns the repo.
- Don't introduce URLs pointing at any other GitHub owner or repo name for
  this marketplace (internal mirrors, forks, archived predecessors). Any
  reference that resolves to a different repo is stale and must be replaced
  with the canonical URL above.
- Don't rename the brand to "j0ruge Marketplace" or vice-versa — the two
  names coexist on purpose.
- Don't confuse external doc links (zitadel, wpfui, microsoft/fluentui,
  FlaUI, ddd-crew, kgrzybek) with marketplace repo links — those external
  links are valid and should not be rewritten.

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
