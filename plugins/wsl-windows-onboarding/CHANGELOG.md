# Changelog — `wsl-windows-onboarding`

## [0.3.0] — 2026-06-06

### Added

- **`references/wsl-setup.md` §2 rewritten — "Install Ubuntu + first user"** and **§5 Docker integration expanded.** The skill previously assumed a distro already existed; now it covers installing one and the first-user trap.
- **`references/shell-setup.md` §7 (new) — "Windows Terminal profile: icon + default profile."**
- **`references/rtk-install.md` — "Claude Code + the global rtk hook"** section: install Claude Code in WSL, then wire rtk in globally.
- **`SKILL.md`** gains pointers in Phase 1 (install distro + non-root user), Phase 2 (Claude Code + `rtk init -g`), and Phase 4 (Windows Terminal profile).

### Why / Origin

Captured from a real session that took a Docker-only Windows box all the way to a working Ubuntu dev environment. Each lesson cost time the first time:

- **`wsl --install Ubuntu-24.04` fails** — current WSL's `--list --online` only lists the generic `Ubuntu`; the versioned name returns `WSL_E_DISTRO_NOT_FOUND`. Use the bare `Ubuntu`.
- **The first-run user setup (OOBE) needs a real TTY.** Driving it through a pipe / background job / agent `!`-command loops forever on `Enter new UNIX username:` (plus `fatal: Only one or two names allowed`) and leaves the distro **root-only**. Fix: register `--no-launch`, then `useradd` + `usermod -aG sudo` + `chpasswd`, and set the default login via `/etc/wsl.conf [user] default` (needs `wsl --terminate` to apply). Always make a **non-root sudo user** for daily work.
- **Windows Terminal:** a distro installed while WT is open won't appear until it re-scans (restart, or just saving `settings.json` triggers a live reload). On **WT Preview** the Ubuntu profile comes from the *Store-app source* (`CanonicalGroupLimited.Ubuntu_…`), not the legacy `Windows.Terminal.Wsl` UUIDv5 GUID — hand-adding the legacy GUID **duplicates** the entry (WT then hides one). Set an explicit `"icon"` (the package PNG path is version-stamped and `WindowsApps` blocks wildcard listing, so resolve via `Get-AppxPackage … InstallLocation` and copy the PNG to a stable path). **`defaultProfile` ≠ `wsl --set-default`** — they're two independent knobs.
- **Docker ↔ WSL integration** follows `EnableIntegrationWithDefaultWslDistro` (the **default** distro) in `%APPDATA%\Docker\settings-store.json`; non-default distros go in `IntegratedWslDistros`. Edit it only while Docker Desktop is stopped (a running Docker rewrites the file on exit), then (re)start Docker.
- **Claude Code in WSL** installs to `~/.local/bin/claude` (same dir as rtk — one PATH line covers both; the installer prints the same PATH warning). Auth is interactive (browser, Pro/Max account) — not scriptable.
- **rtk global integration is `rtk init -g`** (hook + `RTK.md` + `~/.claude/CLAUDE.md` `@RTK.md` + `settings.json`). Install Claude Code **first** (it owns `~/.claude`). Use **`--auto-patch`**: plain `rtk init -g` *prompts* before patching an existing `settings.json` and **defaults to N** non-interactively, silently leaving the hook unwired; `rtk init --show` verifies.

## [0.2.1] — 2026-06-06

### Changed

- **Optimized the skill description for triggering.** Tightened from ~1,100 chars (which had ballooned across v0.1.0→v0.2.0 and risked silent truncation in the `/skills` list, hurting triggering) to ~540 chars: front-loaded the core capability, kept the distinctive traps, and replaced the long keyword dump with a compact, phrase-style `Triggers —` list. Mirrored across `SKILL.md`, `plugin.json`, and `marketplace.json`. The detailed prose stays in the README row (docs, not the trigger surface).

## [0.2.0] — 2026-06-06

### Added

- **`references/shell-setup.md` (new Phase 4 — optional shell setup)** — install zsh + oh-my-zsh, set the default shell with `chsh`, the passwordless-sudo trade-off, silencing the Docker completion warning, and **JetBrains Mono Nerd Font + ligatures** on Windows Terminal.
- **SKILL.md** gains a short Phase 4 section; **`references/rtk-install.md`** cross-links the zsh PATH caveat.

### Why / Origin

Captured from this session's shell setup (zsh + oh-my-zsh + passwordless sudo + default-shell change + font), then **validated via deep-research against 2026 sources** so the skill documents only what still holds:

- **`~/.bashrc` does NOT carry to zsh** — the rtk PATH and aliases added during onboarding are invisible in zsh until re-added to `~/.zshrc`. Confirmed (3-0) that on Ubuntu a zsh login shell sources the *empty* `/etc/zsh/zprofile` instead of `/etc/profile`/`/etc/profile.d/*` (Ubuntu bug #1800280), so the explicit `~/.local/bin` export is **required, not redundant** — and a `grep` guard must match an *active* (non-commented) line, since oh-my-zsh's template ships a commented PATH line.
- **`/etc/wsl.conf` cannot set the login shell** (no such key — Microsoft Learn); `chsh -s` is the correct, reliable mechanism (the "chsh reverts to bash under WSL" folklore was refuted 0-3).
- **oh-my-zsh still valid** (maintained, commits through mid-2026); Starship noted as the lighter modern prompt.
- **Docker `_docker` completion symlink** is a confirmed current issue; removing it fixes the `compinit` warning, but it can reappear when Docker Desktop restarts (durable fix: Docker's own `FPATH` completions).
- **JetBrainsMono Nerd Font** installs via winget `DEVCOM.JetBrainsMonoNerdFont` (verified live, v3.3.0); the patched variant preserves ligatures (v2.1.0+), a Nerd Font is needed for oh-my-zsh glyphs, and Windows Terminal toggles ligatures natively via per-profile `font.features { liga: 1 }`.
- **Passwordless sudo** (`/etc/sudoers.d` + `NOPASSWD`, validated with `visudo -cf`) is documented conservatively with a security caveat — dedicated 2026 sources did not survive verification, so it is presented as standard guidance, not a fresh citation.

## [0.1.1] — 2026-06-06

### Added

- **`references/project-migration.md` → "Pushing a migrated repo from WSL"** — two gotchas hit while publishing this very skill: (1) HTTPS `git push` from a fresh WSL distro **hangs** with no credential helper, fixed by bridging to the Windows Git Credential Manager via `credential.helper = !"/mnt/c/Program Files/Git/mingw64/bin/git-credential-manager.exe"` (the `!` prefix + inner quotes are required — a bare quoted path makes git treat it as a subcommand, an unquoted path breaks on the space); (2) the migrated local copy may be **behind** the real GitHub remote (the Windows checkout was stale), so the first push is rejected and you must `git fetch` + `git rebase origin/main` first — and clean the CRLF/filemode noise with `git checkout -- .` so rebase will start.

### Fixed

- **CURSOR_SKILL_MAP registration** in `install.py` — the plugin declared `cursor` in `platforms` but had no map entry, so `validate-versions.py` failed and Cursor users wouldn't see it.
- **CHANGELOG version format** — headings now use the `## [x.y.z]` bracket form the repo's `validate-versions.py` requires (the v0.1.0 entry was written as `## 0.1.0` and went unrecognized).

### Why / Origin

Same session as v0.1.0: the act of committing and pushing this skill from WSL surfaced the push-auth + stale-remote gotchas (now documented), and running the repo's own `validate-versions.py` caught the missing Cursor-map entry and the changelog format — fixed here so the marketplace stays green.

## [0.1.0] — 2026-06-06

Initial packaging of the Windows→WSL onboarding skill: diagnose/prepare WSL, install rtk, and migrate dev projects into the Linux filesystem.

### Added

- **`SKILL.md`** — three-phase workflow (diagnose WSL → install rtk → migrate projects) with the non-negotiable safety principles up front (copy→validate→delete; never exclude `.git`; rsync-not-clone because of `.env`; confirm destructive/outward steps).
- **`references/wsl-setup.md`** — WSL2 vs WSL1 check, the `docker-desktop`-is-not-your-distro trap, the UTF-16 console encoding gotcha, `/mnt/c` access + why it's slow, and the GUI-only Docker↔WSL integration step.
- **`references/rtk-install.md`** — rtk as a zero-dependency Rust binary, the install-script path, and the `~/.local/bin` PATH fix.
- **`references/project-migration.md`** — the full rsync recipe and exclude list, validation by path-diff, the deletion step, post-migration cleanup, and the CRLF/LF "whole tree modified" diagnosis + fix.
- **`scripts/wsl-diagnose.sh`** — read-only environment diagnostic (distro, disk, git/curl/rsync, rtk PATH, docker).
- **`scripts/migrate-repos.sh`** — parametrized rsync (`<SRC> <DST>`, `--dry-run`) with the exclude list and built-in validation; **deliberately never deletes** anything.

### Why / Origin

Captured from a real session migrating ~28 projects from `C:\Users\…\source\repos` to `~/repos` on WSL2 Ubuntu and installing rtk. Each lesson here cost real time the first time:

1. **The machine already had WSL2** (Docker Desktop installs it) — the right first move is to *check* (`wsl -l -v`), not to install. And the `docker-desktop` distro is Docker's backend, not a workspace.
2. **rtk installed fine but `rtk` was "not found"** — the installer drops the binary in `~/.local/bin`, which isn't on PATH by default. One `~/.bashrc` line fixes it; reinstalling doesn't.
3. **`git clone` would have dropped every `.env`** (gitignored). The user "already had envs configured," so the migration had to rsync the working tree, not re-clone.
4. **`du` over `/mnt/c` hung for minutes** — the very slowness that justifies the migration. Use `df` for space, run the rsync in the background.
5. **Validation by raw `.env` count gave a false mismatch** — the two "missing" files were `node_modules/psl/.env` (an npm package's internal file), correctly excluded and harmless. Diffing by *path* revealed that; a count couldn't.
6. **Deletion is the only irreversible step**, so it goes last, after validation and explicit confirmation, via PowerShell `Remove-Item` (faster than `rm` over `/mnt/c`).
7. **After migrating, `git status` flagged the entire tree as modified with zero untracked files** — two stacked artifacts of the move: (a) CRLF/LF (Windows checkout `autocrlf=true` → CRLF on disk vs LF blobs; Linux git `autocrlf=false`), and (b) file mode (`/mnt/c` files arrive `0777`, so `core.fileMode=true` sees `100644→100755` on every file). `git diff --ignore-cr-at-eol --stat` came back empty (no content change) while `git status` still showed `M` (the mode half), and `git config core.fileMode false` cleared the mode noise. The fix is line-ending renormalization + ignoring mode; a new skill commit must be scoped (LF-normalize only the touched files, `core.fileMode false`) rather than sweeping 150 files of CRLF/mode churn into an unrelated commit.
