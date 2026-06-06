---
name: wsl-windows-onboarding
metadata:
  version: 0.1.0
description: "End-to-end onboarding of a Windows machine to WSL2 — diagnose/enable WSL, install rtk (rtk-ai/rtk), and safely migrate dev projects from C:\\Users\\...\\repos into the Linux filesystem with rsync that keeps .git and .env, excludes rebuildable deps, and validates before any deletion. Encodes the non-obvious gotchas (rtk installs to ~/.local/bin but not on PATH and one global install serves every project, git clone drops .env, /mnt/c is slow, CRLF+filemode make the whole tree look modified, docker-desktop is not your distro). Triggers — wsl, wsl2, ubuntu wsl, install rtk, rtk-ai, move projects to wsl, migrate repos to wsl, /mnt/c slow, .local/bin not in PATH, whole git tree modified after migration, crlf wsl, docker desktop wsl integration."
---

# WSL Windows Onboarding — diagnose WSL · install rtk · migrate projects

This skill takes a Windows developer from "I have a Windows box (probably with Docker)" to "my projects run fast inside WSL2 and rtk is installed." It is built from a real migration and bakes in the traps that cost time the first time around.

It covers three phases that usually run in sequence, but each is independently useful:

1. **Diagnose / prepare WSL** → `references/wsl-setup.md` + `scripts/wsl-diagnose.sh`
2. **Install rtk** → `references/rtk-install.md`
3. **Migrate projects from Windows into WSL** → `references/project-migration.md` + `scripts/migrate-repos.sh`

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
- Your Windows files are at `/mnt/c/...`, but working there is **slow** (cross-filesystem). The payoff of this whole skill is moving projects onto the Linux filesystem (`~`).

## Phase 2 — Install rtk

**Optional / skippable.** If the user only wants the migration or only asked about WSL access, skip straight to Phase 3 — don't install rtk unprompted. Do this phase when the user actually wants rtk.

Full recipe in `references/rtk-install.md`. The essentials:

- rtk is a **single Rust binary with zero runtime dependencies** — do NOT install Node/Python/Go/Docker/Rust just to run it. The install script downloads a prebuilt binary.
- The install script drops the binary in `~/.local/bin`, which is **usually not on PATH** — you must add it to `~/.bashrc`, or `rtk` will be "not found" even though it installed fine.
- rtk does **not** need Docker. Docker↔WSL integration is a separate, optional, GUI-only step, relevant only if you want rtk to filter `docker` command output.

## Phase 3 — Migrate projects into WSL

Use `scripts/migrate-repos.sh` (it rsyncs with the right excludes and then validates; it deliberately **never deletes** anything) and follow `references/project-migration.md` for the copy → validate → delete sequence and the post-migration cleanup.

The migration, in short:

1. **Copy** `C:\...\repos` → `~/repos` with rsync, **keeping `.git` and `.env`**, excluding only rebuildable dirs (`node_modules`, `.venv`/`venv`, build outputs, caches). Run it in the background — over `/mnt/c` it is slow.
2. **Validate** by *diffing file paths*, not just counts: top-level folders match, `.git` repo count matches, every real `.env` is present. Mind the false positive: `.env` files inside `node_modules` (e.g. the `psl` npm package) will appear "missing" — that's correct and harmless.
3. **Delete** the Windows source only after validation, and prefer PowerShell's native `Remove-Item` (faster than `rm` over `/mnt/c`).
4. **Clean up:** fix shell aliases that pointed at `/mnt/c`, and reinstall dependencies per stack (`npm install`, `pip install -r`, `dotnet restore`, `mix deps.get`).

### Expect a "whole tree modified" surprise after migrating a git repo

After migration, `git status` inside a migrated repo may show **every file as modified** with **zero untracked files**. This is almost never real edits — it's a **CRLF/LF mismatch**: the working tree was checked out on Windows (`core.autocrlf=true` → CRLF on disk) while the committed blobs are LF, and the Linux git (`autocrlf=false`) flags the whole tree. Confirm with:

```bash
git diff --ignore-cr-at-eol --stat   # empty output ⇒ pure line-ending artifact, no real changes
```

If it's empty, the fix is a line-ending normalization (`.gitattributes` with `* text=auto eol=lf` + `git add --renormalize .`), not a panic. `references/project-migration.md` has the full diagnosis and fix, including how to scope a commit cleanly while the tree is in this state.
