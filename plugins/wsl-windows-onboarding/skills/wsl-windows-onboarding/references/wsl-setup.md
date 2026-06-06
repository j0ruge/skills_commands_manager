# Phase 1 — Diagnose and prepare WSL

Goal: before touching anything, understand the machine. Most Windows dev boxes that run Docker **already have WSL2** — so the first move is to check, not to install.

## 1. Check what already exists (run in PowerShell / Windows Terminal)

```powershell
wsl --version          # WSL version + kernel; absence ⇒ WSL not installed
wsl --list --verbose   # distros and their WSL version (1 or 2)
```

Typical output on a machine that already has it:

```
  NAME              STATE      VERSION
* Ubuntu            Running    2
  docker-desktop    Stopped    2
```

Read this carefully:

- **`VERSION` must be `2`.** WSL1 lacks the full Linux kernel and the performance characteristics we rely on. If a distro is on 1: `wsl --set-version <name> 2`.
- **`docker-desktop` (and `docker-desktop-data`) is NOT a working distro.** It's the backend Docker Desktop runs in. Do your work in the real distro (here, `Ubuntu`). Accidentally `wsl -d docker-desktop` and installing tools there is a common, confusing mistake — that distro is managed by Docker and gets reset.
- The `*` marks the default distro that bare `wsl` enters.

### Encoding gotcha

`wsl ...` output piped through the Windows console can come back with spaced-out / garbled accented characters (it's UTF-16). Prefer **Windows Terminal** (UTF-8). When scripting, don't try to parse the pretty table — query inside the distro instead (see the diagnose script).

## 2. If WSL is not installed

```powershell
wsl --install            # installs WSL2 + Ubuntu by default; reboot when asked
```

After reboot, launch Ubuntu once to create your Linux user.

## 3. Inspect the distro from the inside

```bash
wsl -d Ubuntu -e bash -lc '
  whoami; echo "HOME=$HOME";
  lsb_release -d;
  df -h ~ | tail -1;          # free space on the LINUX filesystem (where projects will go)
  for c in git curl rsync; do command -v "$c" >/dev/null && echo "$c: ok" || echo "$c: MISSING"; done
'
```

`scripts/wsl-diagnose.sh` automates exactly this and is read-only. If `git`/`curl`/`rsync` are missing:

```bash
sudo apt update && sudo apt install -y git curl rsync
```

## 4. Accessing Windows files from WSL — and why you shouldn't stay there

The Windows drives are mounted under `/mnt/`:

```bash
cd /mnt/c/Users/<you>/source/repos
```

This works, but the `/mnt/c` bridge is **slow** for anything file-heavy (git status on a big repo, `npm install`, `du`, builds) because every file op crosses the Windows↔Linux boundary. That slowness is the whole reason Phase 3 moves projects onto the native Linux filesystem (`~`). Use `/mnt/c` for occasional access and for the one-time migration copy — not as your daily working directory.

A convenience alias (point it at the *final* Linux location after migration, not `/mnt/c`):

```bash
echo 'alias repos="cd ~/repos"' >> ~/.bashrc && source ~/.bashrc
```

## 5. Docker ↔ WSL integration (optional, manual, GUI-only)

If `docker` isn't found inside your distro, it's because Docker Desktop's WSL integration is off for that distro. This is **not required for rtk** and not required for the migration. Enable it only if you actually want to run `docker` from inside WSL:

1. Docker Desktop → **Settings → Resources → WSL Integration**
2. Enable the toggle for your distro (e.g. `Ubuntu`)
3. **Apply & Restart**, then verify with `docker --version` inside WSL.

It's a GUI step — you cannot flip it from the CLI, so hand it to the user with these instructions.
