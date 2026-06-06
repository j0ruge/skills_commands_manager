# Changelog — `wsl-windows-onboarding`

## 0.1.0 — 2026-06-06

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
