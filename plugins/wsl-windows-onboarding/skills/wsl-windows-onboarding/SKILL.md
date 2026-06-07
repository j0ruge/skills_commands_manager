---
name: wsl-windows-onboarding
metadata:
  version: 0.4.0
description: "End-to-end onboarding of a Windows machine to WSL2 — diagnose/enable WSL, install rtk (rtk-ai/rtk), migrate dev projects from C:\\Users\\...\\repos into the Linux filesystem with rsync that keeps .git and .env and validates before deleting, and optionally set up zsh + JetBrains Mono. Built from a real migration, so it knows the traps: rtk 'not found' because ~/.local/bin isn't on PATH, /mnt/c being slow, the whole git tree looking modified after migration (CRLF/filemode), and ~/.bashrc config not carrying to ~/.zshrc. Triggers — install rtk on Windows, move or migrate projects to WSL, set up WSL for development, access Windows files from Ubuntu, slow WSL builds, rtk not on PATH, zsh on WSL, JetBrains Mono ligatures, migrate repos with C: nearly full, one-repo-at-a-time copy-validate-delete, resume an interrupted WSL migration, Remove-Item nul Incorrect function."
---

# WSL Windows Onboarding — diagnose WSL · install rtk · migrate projects

This skill takes a Windows developer from "I have a Windows box (probably with Docker)" to "my projects run fast inside WSL2 and rtk is installed." It is built from a real migration and bakes in the traps that cost time the first time around.

It covers four phases that usually run in sequence, but each is independently useful:

1. **Diagnose / prepare WSL** → `references/wsl-setup.md` + `scripts/wsl-diagnose.sh`
2. **Install rtk** → `references/rtk-install.md`
3. **Migrate projects from Windows into WSL** → `references/project-migration.md` + `scripts/migrate-repos.sh`
4. **(Optional) Set up the shell — zsh + font** → `references/shell-setup.md`

## When to invoke

Use it whenever the user wants any of these, even if they don't name "WSL":

- "Install rtk on my Windows machine" (rtk recommends WSL — this is the supported path)
- "Move / migrate my projects into WSL for speed"
- "How do I access my Windows folder from Ubuntu?" / "why are my builds so slow in WSL?"
- "Set up WSL for development on this Windows PC"

## Non-negotiable safety principles

These exist because each one, skipped, caused a real problem:

- **Copy → validate → only then delete.** The deletion of the Windows source is the one irreversible step. Never delete before the copy is validated. When the user says "move," still copy first; delete last, after confirmation. See `references/project-migration.md`.
- **Never exclude `.git`.** It carries history and any uncommitted work. Excluding it to "save space" silently destroys the repo's value.
- **`.env` is why you rsync, not re-clone.** `.env`/secrets are gitignored, so a fresh `git clone` does NOT bring them. rsync the working tree (keeping `.env`) instead of re-cloning. This is the single most important reason the migration uses rsync.
- **Confirm before destructive or outward steps.** Deleting the source, pushing, overwriting an existing target — confirm with the user first.

## Phase 1 — Diagnose / prepare WSL

Run `scripts/wsl-diagnose.sh` (read-only — it mutates nothing) or the manual checks in `references/wsl-setup.md`. The goal is to learn, before doing anything: is WSL2 installed, which distro is the real working distro, is there enough disk, are `git`/`curl`/`rsync` present.

Key things to get right (full detail in `references/wsl-setup.md`):

- **Docker users almost always already have WSL2** — check `wsl -l -v` and `wsl --version` before installing anything.
- The **`docker-desktop` distro is Docker's backend, not your workspace.** Work inside the real distro (e.g. `Ubuntu`). Picking `docker-desktop` is a classic mistake.
- **If there's no real distro, install one** with `wsl --install Ubuntu` (the bare name — `Ubuntu-24.04` fails with `WSL_E_DISTRO_NOT_FOUND` on current WSL). The first-run user prompt (OOBE) needs a real terminal; when scripting, register non-interactively and create a **non-root user with sudo**, set as default via `/etc/wsl.conf [user] default`. Full recipe in `references/wsl-setup.md`.
- Your Windows files are at `/mnt/c/...`, but working there is **slow** (cross-filesystem). The payoff of this whole skill is moving projects onto the Linux filesystem (`~`).

## Phase 2 — Install rtk

**Optional / skippable.** If the user only wants the migration or only asked about WSL access, skip straight to Phase 3 — don't install rtk unprompted. Do this phase when the user actually wants rtk.

Full recipe in `references/rtk-install.md`. The essentials:

- rtk is a **single Rust binary with zero runtime dependencies** — do NOT install Node/Python/Go/Docker/Rust just to run it. The install script downloads a prebuilt binary.
- The install script drops the binary in `~/.local/bin`, which is **usually not on PATH** — you must add it to `~/.bashrc`, or `rtk` will be "not found" even though it installed fine.
- rtk does **not** need Docker. Docker↔WSL integration is a separate, optional step, relevant only if you want rtk to filter `docker` command output.
- **For the usual goal — Claude Code in WSL with rtk wired in globally:** install Claude Code (`curl -fsSL https://claude.ai/install.sh | bash`, also lands in `~/.local/bin`, so the same PATH fix covers both) **first**, then `rtk init -g --auto-patch` (use `--auto-patch` — plain `rtk init -g` prompts to patch an existing `~/.claude/settings.json` and defaults to N in a non-interactive shell). See `references/rtk-install.md`.

## Phase 3 — Migrate projects into WSL

Use `scripts/migrate-repos.sh` (it rsyncs with the right excludes and then validates; it deliberately **never deletes** anything) and follow `references/project-migration.md` for the copy → validate → delete sequence and the post-migration cleanup.

The migration, in short:

1. **Copy** `C:\...\repos` → `~/repos` with rsync, **keeping `.git` and `.env`**, excluding only rebuildable dirs (`node_modules`, `.venv`/`venv`, build outputs, caches). Run it in the background — over `/mnt/c` it is slow.
2. **Validate** by *diffing file paths*, not just counts: top-level folders match, `.git` repo count matches, every real `.env` is present. Mind the false positive: `.env` files inside `node_modules` (e.g. the `psl` npm package) will appear "missing" — that's correct and harmless.
3. **Delete** the Windows source only after validation, and prefer PowerShell's native `Remove-Item` (faster than `rm` over `/mnt/c`). If it fails with `Cannot remove item …\nul: Incorrect function`, the repo has a **reserved-name** file (`nul`/`con`/`aux`/…) a Linux checkout can create — delete via the `\\?\` extended-length path prefix. See `references/project-migration.md`.
4. **Clean up:** fix shell aliases that pointed at `/mnt/c`, and reinstall dependencies per stack (`npm install`, `pip install -r`, `dotnet restore`, `mix deps.get`).

**Tight disk?** When `C:` is nearly full (the WSL `ext4.vhdx` lives on `C:` and grows as you copy, so you transiently need room for both copies), don't copy the whole tree first. Migrate **one repo at a time** — copy → validate that single repo with a `rsync -an` dry-run (0 file transfers = synced) → delete its Windows source to free space → next. This caps the peak to a single repo and resumes a half-finished migration cleanly. Full loop in `references/project-migration.md`.

### Expect a "whole tree modified" surprise after migrating a git repo

After migration, `git status` inside a migrated repo may show **every file as modified** with **zero untracked files**. This is almost never real edits — it's a **CRLF/LF mismatch**: the working tree was checked out on Windows (`core.autocrlf=true` → CRLF on disk) while the committed blobs are LF, and the Linux git (`autocrlf=false`) flags the whole tree. Confirm with:

```bash
git diff --ignore-cr-at-eol --stat   # empty output ⇒ pure line-ending artifact, no real changes
```

If it's empty, the fix is a line-ending normalization (`.gitattributes` with `* text=auto eol=lf` + `git add --renormalize .`), not a panic. `references/project-migration.md` has the full diagnosis and fix, including how to scope a commit cleanly while the tree is in this state.

## Phase 4 — (Optional) Set up the shell (zsh + font)

**Optional.** Only when the user wants it. Full, source-validated recipe in `references/shell-setup.md` (install zsh + oh-my-zsh, set the default shell with `chsh`, passwordless sudo trade-off, the Docker completion warning, and JetBrains Mono Nerd Font + ligatures on Windows Terminal).

The one trap that bites everyone:

- **`~/.bashrc` config does NOT carry to zsh.** zsh reads `~/.zshrc`, never `~/.bashrc`. So the **rtk PATH** (`~/.local/bin`) and any aliases you added during onboarding are invisible in zsh until you re-add them to `~/.zshrc` — and on Ubuntu the system profile won't add `~/.local/bin` for you (its `/etc/zsh/zprofile` is empty), so the explicit `export` is required, not redundant. See the cross-reference in `references/rtk-install.md`.
- The **font and ligatures live on Windows**, not in WSL — the Windows-side terminal renders text. Install the **JetBrainsMono Nerd Font** on Windows and enable ligatures via Windows Terminal's per-profile `font.features`.
- **Windows Terminal profile (icon + default):** a new distro only shows after the Terminal re-scans (restart, or just saving `settings.json`); set an explicit `"icon"` (copy the package PNG to a stable path) and the top-level `"defaultProfile"` to open Ubuntu by default — which is separate from `wsl --set-default`. Don't hand-guess the profile GUID on WT Preview (it uses the Store-app source). See `references/shell-setup.md`.
