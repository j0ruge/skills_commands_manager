#!/usr/bin/env python3
"""Chewiesoft Marketplace Installer

Installs plugins as Cursor skills or shows Claude Code setup instructions.
No external dependencies required — uses Python standard library only.

Usage:
    python install.py
"""
from __future__ import annotations

import re
import shutil
import sys
import textwrap
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent

# ─────────────────────────────────────────────────────────────────────────────
# Skill mapping: how each source asset maps to a Cursor skill
#
# source_type "skill"   → copy skill directory (SKILL.md + references/)
# source_type "command" → convert a command .md file to SKILL.md
# ─────────────────────────────────────────────────────────────────────────────

CURSOR_SKILL_MAP: list[dict[str, Any]] = [
    {
        "plugin": "cicd",
        "cursor_name": "cicd",
        "display": "CI/CD — troubleshooting GitHub Actions, Docker & GHCR pipelines",
        "source_type": "skill",
        "source_dir": "plugins/cicd/skills/cicd",
    },
    {
        "plugin": "codereview",
        "cursor_name": "codereview",
        "display": "Code Review — automated pre-PR review with severity grading (A–F)",
        "source_type": "skill",
        "source_dir": "plugins/codereview/skills/codereview",
    },
    {
        "plugin": "codereview",
        "cursor_name": "coderabbit-pr",
        "display": "CodeRabbit PR — resolve CodeRabbit bot review comments on a GitHub PR",
        "source_type": "skill",
        "source_dir": "plugins/codereview/skills/coderabbit_pr",
    },
    {
        "plugin": "deploy",
        "cursor_name": "deploy-staging",
        "display": "Deploy Staging — merge branch to develop and trigger the CD Staging pipeline",
        "source_type": "command",
        "source_file": "plugins/deploy/commands/staging.md",
        "cursor_description": (
            "Deploy the current branch to the staging environment. Syncs main with develop, "
            "merges the current feature branch into develop, and pushes to trigger the CD Staging "
            "pipeline. Use when the user asks to deploy to staging, send to staging, merge to "
            "staging, trigger the staging pipeline, or push the current branch to develop."
        ),
    },
    {
        "plugin": "release",
        "cursor_name": "release",
        "display": "Release — generate categorized release notes and create a GitHub Release",
        "source_type": "command",
        "source_file": "plugins/release/commands/release.md",
        "cursor_description": (
            "Create a GitHub Release with categorized release notes from git history. "
            "Analyzes all commits since the last release tag and creates the release via the gh CLI. "
            "Works with any stack (Node.js, C#/.NET, Go, Rust, Python). "
            "Use when the user asks to create a release, generate release notes, publish a new version, "
            "tag a release, or run a release. Reads the target semantic version from the user's message "
            "(e.g. '2.0.0') or asks if not provided. Supports --path for monorepo component releases."
        ),
    },
    {
        "plugin": "ddd",
        "cursor_name": "ddd",
        "display": "DDD — Domain-Driven Design analysis, strategic design, legacy → DDD conversion",
        "source_type": "skill",
        "source_dir": "plugins/ddd/skills/ddd",
    },
    {
        "plugin": "dotnet-wpf",
        "cursor_name": "dotnet-desktop-setup",
        "display": "Dotnet Desktop Setup — configure & audit C#/.NET WinForms/WPF/Avalonia projects",
        "source_type": "skill",
        "source_dir": "plugins/dotnet-wpf/skills/dotnet-desktop-setup",
    },
    {
        "plugin": "dotnet-wpf",
        "cursor_name": "dotnet-wpf-design",
        "display": "WPF Design — Fluent Design layout, spacing, theming and 90+ controls catalog",
        "source_type": "skill",
        "source_dir": "plugins/dotnet-wpf/skills/dotnet-wpf-design",
    },
    {
        "plugin": "dotnet-wpf",
        "cursor_name": "dotnet-wpf-mvvm",
        "display": "WPF MVVM — WinForms → WPF migration with CommunityToolkit.Mvvm and WPF-UI",
        "source_type": "skill",
        "source_dir": "plugins/dotnet-wpf/skills/dotnet-wpf-mvvm",
    },
    {
        "plugin": "dotnet-wpf",
        "cursor_name": "dotnet-wpf-e2e-testing",
        "display": "WPF E2E Testing — FlaUI + xUnit, Page Objects, AutomationIds, CI/CD setup",
        "source_type": "skill",
        "source_dir": "plugins/dotnet-wpf/skills/dotnet-wpf-e2e-testing",
    },
    {
        "plugin": "retrofit-skill",
        "cursor_name": "retrofit-skill",
        "display": "Retrofit Skill — apply session lessons to a marketplace skill (bump, CHANGELOG, push)",
        "source_type": "command",
        "source_file": "plugins/retrofit-skill/commands/retrofit-skill.md",
        "cursor_description": (
            "Apply non-obvious session lessons to a target skill in the chewiesoft-marketplace repo. "
            "Bumps the skill version, updates CHANGELOG.md, marketplace.json and README, and commits "
            "and pushes the changes. Use when the user asks to retrofit a skill, apply lessons learned, "
            "atualizar uma skill, sync skill version, ou bump skill version after a session insight. "
            "Reads the target skill name from the user's message (e.g. 'codereview') or asks if not "
            "provided."
        ),
    },
]

# Plugins not available for Cursor (Claude Code only)
CLAUDE_CODE_ONLY = {"statusline"}

# ─────────────────────────────────────────────────────────────────────────────
# Content transformation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _split_frontmatter(content: str) -> tuple[str, str]:
    """
    Split a Markdown file into (frontmatter_text, body_text).
    frontmatter_text does NOT include the --- delimiters.
    Returns ('', content) if no frontmatter is detected.
    """
    if content.startswith("---\n"):
        end = content.find("\n---\n", 4)
        if end != -1:
            return content[4:end], content[end + 5:]
    return "", content


def _remove_metadata_block(fm_text: str) -> str:
    """Remove the 'metadata:' key and its indented children from YAML frontmatter text."""
    return re.sub(r"^metadata:\n(?:[ \t]+[^\n]*\n)*", "", fm_text, flags=re.MULTILINE)


def _adapt_body(body: str) -> str:
    """
    Adapt Markdown body for Cursor:
    - Remove the ```text\\n$ARGUMENTS\\n``` fenced placeholder blocks
    - Replace any remaining $ARGUMENTS occurrences with 'the user's message'
    - Collapse triple+ blank lines to double
    """
    # Remove the fenced $ARGUMENTS placeholder block (with optional trailing newline)
    body = re.sub(r"```text\n\$ARGUMENTS\n```\n?", "", body)
    # Replace remaining $ARGUMENTS occurrences in prose
    body = body.replace("$ARGUMENTS", "the user's message")
    # Collapse triple+ blank lines
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _wrap_yaml_description(description: str) -> str:
    """
    Format a long description string as a YAML folded block scalar (>).
    Returns the full YAML value text, e.g.:
        >
          First wrapped line of the description
          continuing here...
    """
    lines = textwrap.wrap(description.strip(), width=76)
    indented = "\n".join("  " + line for line in lines)
    return ">\n" + indented


def _build_markdown(fm_text: str, body: str) -> str:
    """Reassemble a Markdown file from frontmatter text and body."""
    return f"---\n{fm_text.rstrip()}\n---\n\n{body}\n"


# ─────────────────────────────────────────────────────────────────────────────
# Installation functions
# ─────────────────────────────────────────────────────────────────────────────

def _install_from_skill_dir(entry: dict[str, Any], dest_dir: Path) -> None:
    """
    Copy a skill directory to dest_dir, adapting SKILL.md for Cursor:
    - Strip 'metadata:' block from frontmatter
    - Remove $ARGUMENTS placeholder blocks from the body
    - Copy all reference files unchanged
    """
    source_dir = REPO_ROOT / entry["source_dir"]

    # Adapt SKILL.md
    skill_md_src = source_dir / "SKILL.md"
    content = skill_md_src.read_text(encoding="utf-8")
    fm_text, body = _split_frontmatter(content)
    fm_text = _remove_metadata_block(fm_text)
    body = _adapt_body(body)
    (dest_dir / "SKILL.md").write_text(_build_markdown(fm_text, body), encoding="utf-8")

    # Copy all other items (references/, etc.) as-is
    for item in source_dir.iterdir():
        if item.name == "SKILL.md":
            continue
        dest_item = dest_dir / item.name
        if item.is_dir():
            if dest_item.exists():
                shutil.rmtree(dest_item)
            shutil.copytree(item, dest_item)
        else:
            shutil.copy2(item, dest_item)


def _install_from_command(entry: dict[str, Any], dest_dir: Path) -> None:
    """
    Convert a Claude Code command .md file to a Cursor SKILL.md:
    - Replace the command frontmatter with a Cursor-style name + description
    - Adapt the body (remove $ARGUMENTS blocks)
    """
    source_file = REPO_ROOT / entry["source_file"]
    content = source_file.read_text(encoding="utf-8")

    # Discard the original command frontmatter; keep only the body
    _, body = _split_frontmatter(content)
    body = _adapt_body(body)

    # Build a new Cursor frontmatter
    desc_yaml = _wrap_yaml_description(entry["cursor_description"])
    fm_text = f"name: {entry['cursor_name']}\ndescription: {desc_yaml}"

    (dest_dir / "SKILL.md").write_text(_build_markdown(fm_text, body), encoding="utf-8")


def _install_skill(entry: dict[str, Any], dest_base: Path) -> None:
    """Install a single skill to dest_base/<cursor_name>/."""
    dest_dir = dest_base / entry["cursor_name"]
    dest_dir.mkdir(parents=True, exist_ok=True)

    if entry["source_type"] == "skill":
        _install_from_skill_dir(entry, dest_dir)
    else:
        _install_from_command(entry, dest_dir)


# ─────────────────────────────────────────────────────────────────────────────
# Interactive prompts
# ─────────────────────────────────────────────────────────────────────────────

def _choose(prompt_text: str, options: list[str], default_index: int = 0) -> int:
    """Present a numbered menu and return the 0-based index of the chosen option."""
    print(f"\n{prompt_text}")
    for i, opt in enumerate(options, 1):
        marker = "  [default]" if i - 1 == default_index else ""
        print(f"  {i}) {opt}{marker}")
    while True:
        raw = input("\nEnter number: ").strip()
        if not raw:
            return default_index
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"  Please enter a number between 1 and {len(options)}.")


def _multiselect(prompt_text: str, options: list[str]) -> list[int]:
    """
    Present a numbered list and allow multi-selection.
    Returns list of 0-based indices. Empty input selects all.
    """
    print(f"\n{prompt_text}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}) {opt}")
    print()
    raw = input("Enter numbers separated by commas (or press Enter to select all): ").strip()
    if not raw or raw.lower() == "all":
        return list(range(len(options)))
    indices: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(options):
            indices.append(int(part) - 1)
    if not indices:
        print("  No valid input — selecting all.")
        return list(range(len(options)))
    return indices


# ─────────────────────────────────────────────────────────────────────────────
# Claude Code instructions
# ─────────────────────────────────────────────────────────────────────────────

_CLAUDE_CODE_INSTRUCTIONS = """\

  Claude Code Installation
  ────────────────────────────────────────────────────────────────────

  Add the marketplace inside Claude Code (run as slash commands):

    Via GitHub:
      /plugin marketplace add j0ruge/skills_commands_manager

    Via SSH:
      /plugin marketplace add git@github.com:j0ruge/skills_commands_manager.git

    Via local clone:
      /plugin marketplace add ./skills_commands_manager

  Then install individual plugins:
      /plugin install cicd
      /plugin install codereview
      /plugin install ddd
      /plugin install deploy
      /plugin install dotnet-wpf
      /plugin install release
      /plugin install retrofit-skill
      /plugin install statusline    ← Claude Code only

  Update at any time:
      /plugin marketplace update
"""

# ─────────────────────────────────────────────────────────────────────────────
# Cursor installation flow
# ─────────────────────────────────────────────────────────────────────────────

def _cursor_install_flow() -> None:
    # 1. Choose install location
    #
    # NOTE: Cursor (as of 2026) does NOT support a global/personal skills directory.
    # Only project-local `.cursor/skills/` is auto-loaded. The "Staging cache" option
    # below copies the converted skills to `~/.cursor/skills/` as a master copy that
    # the user can manually mirror into each project's `.cursor/skills/` — useful as
    # a cache, but Cursor will not pick those skills up directly.
    # Refs: https://cursor.com/docs/skills, https://www.agensi.io/learn/where-are-cursor-skills-stored
    loc_idx = _choose(
        "Where should the Cursor skills be installed?",
        [
            "Project        —  .cursor/skills/     (auto-loaded by Cursor in this repo)",
            "Staging cache  —  ~/.cursor/skills/   (master copy; copy into each project manually — Cursor has no global skills dir)",
        ],
        default_index=0,
    )
    dest_base = (
        Path.cwd() / ".cursor" / "skills"
        if loc_idx == 0
        else Path.home() / ".cursor" / "skills"
    )

    # 2. Select skills to install
    skill_labels = [
        f"{s['cursor_name']:<22}  {s['display']}" for s in CURSOR_SKILL_MAP
    ]
    selected_indices = _multiselect(
        "Select the skills to install (all are compatible with Cursor):",
        skill_labels,
    )
    selected = [CURSOR_SKILL_MAP[i] for i in selected_indices]

    if not selected:
        print("\n  Nothing selected — aborting.")
        return

    # 3. Check for skills that already exist
    existing = [s for s in selected if (dest_base / s["cursor_name"]).exists()]
    overwrite = True
    if existing:
        names = ", ".join(s["cursor_name"] for s in existing)
        print(f"\n  The following skills already exist at {dest_base}/: {names}")
        ow_idx = _choose(
            "What should be done with existing skills?",
            ["Overwrite (replace with latest version)", "Skip (keep existing)"],
            default_index=0,
        )
        overwrite = ow_idx == 0

    # 4. Install
    print(f"\n  Installing {len(selected)} skill(s) to {dest_base}/\n")
    dest_base.mkdir(parents=True, exist_ok=True)

    installed = 0
    skipped = 0
    errors: list[str] = []

    for entry in selected:
        dest_dir = dest_base / entry["cursor_name"]
        if dest_dir.exists() and not overwrite:
            print(f"  - {entry['cursor_name']:<22}  skipped (already exists)")
            skipped += 1
            continue
        try:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            _install_skill(entry, dest_base)
            print(f"  + {entry['cursor_name']}")
            installed += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{entry['cursor_name']}: {exc}")
            print(f"  ! {entry['cursor_name']}  ERROR: {exc}")

    # 5. Summary
    print()
    print(f"  Installed : {installed}")
    if skipped:
        print(f"  Skipped   : {skipped}")
    if errors:
        print(f"  Errors    : {len(errors)}")
        for err in errors:
            print(f"    - {err}")
        return

    print(f"\n  Skills installed to: {dest_base}")
    print()
    print("  Cursor will automatically apply these skills when relevant to the conversation.")
    print("  You can also mention a skill explicitly, e.g.: 'run a codereview on my changes'.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print("  ╔═══════════════════════════════════════════╗")
    print("  ║    Chewiesoft Marketplace  —  Installer   ║")
    print("  ╚═══════════════════════════════════════════╝")

    note = (
        "\n  NOTE: The 'statusline' plugin is Claude Code only and is not available\n"
        "  for Cursor (it uses the Claude Code status line API).\n"
    )
    print(note)

    platform_idx = _choose(
        "Which platform are you installing for?",
        ["Claude Code", "Cursor", "Both"],
        default_index=2,
    )

    if platform_idx in (0, 2):  # Claude Code or Both
        print(_CLAUDE_CODE_INSTRUCTIONS)

    if platform_idx in (1, 2):  # Cursor or Both
        _cursor_install_flow()

    print("\n  Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Installation cancelled.")
        sys.exit(0)
