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

## 2. If no usable distro exists — install Ubuntu

If `wsl -l -v` shows only `docker-desktop` (or nothing), you need a real distro:

```powershell
wsl --install Ubuntu      # installs the latest Ubuntu LTS
```

**Name trap:** on current WSL, `wsl --list --online` only lists the *generic* name
`Ubuntu`. Passing a versioned name like `wsl --install Ubuntu-24.04` fails with
`WSL_E_DISTRO_NOT_FOUND` — use the bare `Ubuntu` (it resolves to the latest LTS).
If WSL itself is missing too, `wsl --install` with no argument installs WSL2 +
Ubuntu; reboot when asked.

### Creating the first user — the OOBE only works in a real terminal

On first launch the distro runs an interactive setup (OOBE) that asks for a UNIX
username + password. **That prompt needs a real TTY.** Driving the launcher through
anything non-interactive — a piped shell, a background job, an agent's `!`-prefixed
command — makes it loop forever on `Enter new UNIX username:` (you'll see a flood of
that line plus `fatal: Only one or two names allowed`) and leaves the distro
registered as **root only**. Two ways out:

- **Open Ubuntu in a real Windows Terminal tab** and answer the prompts, or
- **Register non-interactively** and create the user by hand (the path to use when
  scripting / automating):

```powershell
wsl --install Ubuntu --no-launch        # download + register, skip the OOBE
# create a non-root user with sudo (root is the OOBE-skip default — not for daily use):
wsl -d Ubuntu -u root -- bash -c 'useradd -m -s /bin/bash <user>; usermod -aG sudo <user>; echo "<user>:<password>" | chpasswd'
# make that user the default login:
wsl -d Ubuntu -u root -- bash -c 'printf "[user]\ndefault=<user>\n" > /etc/wsl.conf'
wsl --terminate Ubuntu                   # REQUIRED for /etc/wsl.conf to take effect
wsl -d Ubuntu -- whoami                  # → <user>
```

`/etc/wsl.conf [user] default` is the generic mechanism; `ubuntu config
--default-user <user>` (the Ubuntu launcher) is the app-specific alternative.
**Always create a non-root user with sudo** for daily work — running as root inside
WSL is a footgun.

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

## 5. Docker ↔ WSL integration (optional)

If `docker` inside your distro reports *"The command 'docker' could not be found in
this WSL 2 distro… activate the WSL integration"*, Docker Desktop's integration is
off for that distro. This is **not required for rtk** and not required for the
migration — enable it only if you want to run `docker` from inside WSL.

The supported path is the GUI:

1. Docker Desktop → **Settings → Resources → WSL Integration**
2. Enable the toggle for your distro (e.g. `Ubuntu`)
3. **Apply & Restart**, then verify with `docker version` inside WSL.

How the integration is actually keyed (useful when scripting or debugging) — it
lives in `%APPDATA%\Docker\settings-store.json`:

- `EnableIntegrationWithDefaultWslDistro: true` integrates with whatever the
  **default** WSL distro is. So once your real distro is the default
  (`wsl --set-default Ubuntu`), Docker integrates with it automatically — no
  per-distro toggle needed.
- `IntegratedWslDistros: ["Ubuntu", …]` is the explicit list for **non-default**
  distros.

Either way Docker Desktop must be **(re)started** to inject the `docker` shim into
the distro. Edit `settings-store.json` only while Docker Desktop is **stopped** (a
running Docker rewrites the file on exit and would clobber your change). Verify:

```powershell
wsl -d Ubuntu -- docker version    # Server.Version present ⇒ integration is live
```
