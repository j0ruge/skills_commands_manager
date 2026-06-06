# Phase 4 (optional) — Set up your shell (zsh) after onboarding

Once WSL is prepared, rtk is installed, and projects are migrated, many developers switch the WSL shell from bash to **zsh**. This is optional. The steps below were validated against current (2026) sources — each carries a verdict so you don't document advice that has gone stale. Where the research was inconclusive, that is called out.

> WSL has no GUI: the **font is rendered by the Windows-side terminal** (Windows Terminal), not by Linux. So the shell (zsh) is configured inside WSL, but the **font/ligatures are configured on Windows** — see the last section.

## 1. Install zsh + a framework

```bash
sudo apt update && sudo apt install -y zsh
```

**Framework — oh-my-zsh (still valid):** oh-my-zsh remains actively maintained and a reasonable default (≈188k stars, commits through mid-2026). Install unattended (don't let it change the shell or launch zsh — we handle those explicitly):

```bash
RUNZSH=no CHSH=no KEEP_ZSHRC=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
```

The emphasis has shifted toward **lighter prompts** for startup speed — most notably **Starship** (Rust, sub-10ms, cross-shell). Starship is a *prompt*, not a full framework, and composes with or replaces oh-my-zsh's theme. Offer it when the user cares about shell startup latency; otherwise oh-my-zsh's default is fine. (Verify the exact install flags against the current oh-my-zsh README — the project is actively developed.)

## 2. Make zsh the default shell

Use **`chsh`** — this is the correct, reliable mechanism on modern WSL2 (the old "chsh reverts to bash under WSL" folklore was tested and refuted):

```bash
chsh -s "$(command -v zsh)"        # run as the user, or: sudo chsh -s /usr/bin/zsh <user>
```

- **`/etc/wsl.conf` cannot do this.** It has no "shell" key — its `[user] default` only chooses *which user* the session starts as, not the login shell. Don't try to set the shell there.
- Standard `chsh` requires the target shell to be listed in **`/etc/shells`** (the `zsh` apt package adds it). If `chsh` rejects the shell, check that file.
- Alternative without touching the login shell: set the **Windows Terminal profile** `commandline` to `wsl.exe -d Ubuntu -- zsh`.

## 3. CRITICAL — your bash config does NOT carry over to zsh

This is the step that silently breaks things. **zsh does not read `~/.bashrc`** — it reads `~/.zshrc` (plus `~/.zshenv`/`~/.zprofile`). Anything you put in `~/.bashrc` during onboarding is invisible to zsh. In particular:

- The **rtk PATH** line (`export PATH="$HOME/.local/bin:$PATH"`) — without it, `rtk` is "command not found" in zsh even though it's installed. See `rtk-install.md`.
- Any **aliases** you added (e.g. `alias repos='cd ~/repos'`).

Replicate them in `~/.zshrc`:

```bash
grep -qE '^[^#]*export PATH=.*\.local/bin' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
grep -q 'alias repos=' ~/.zshrc || echo 'alias repos="cd ~/repos"' >> ~/.zshrc
```

Two real gotchas:

- **Don't rely on the system profile to add `~/.local/bin`.** On Ubuntu, a zsh *login* shell sources the (empty) `/etc/zsh/zprofile` instead of `/etc/profile`/`/etc/profile.d/*`, so the `~/.local/bin` entry that bash gets "for free" is **not** added for zsh. The explicit export above is genuinely needed — it is not redundant. (Ubuntu bug #1800280, confirmed through 24.04.)
- **A `grep` guard can be fooled by a comment.** The oh-my-zsh `.zshrc` template ships a *commented* `# export PATH=$HOME/bin:$HOME/.local/bin:...` line. A naive `grep -q '.local/bin' ~/.zshrc` matches that comment and skips adding the real line — so guard on an **active** (non-`#`) line as shown above (`^[^#]*export PATH=...`).

Verify in a real login shell:

```bash
zsh -lic 'command -v rtk && rtk --version && type repos'
```

## 4. Passwordless sudo (optional, security trade-off)

> Note: dedicated 2026 sources for this did not survive verification, so treat the following as standard, well-known guidance rather than a freshly-cited recommendation.

On a **single-user development** WSL box some prefer to drop the sudo password prompt. It's a deliberate trade-off: convenient, but it removes a barrier — avoid it on shared or network-exposed machines. Always write the rule to a file under `/etc/sudoers.d/` and **validate before trusting it** (a malformed sudoers file can lock you out of sudo — though in WSL you can always recover via `wsl -u root`):

```bash
echo "<user> ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/<user>
sudo chmod 0440 /etc/sudoers.d/<user>
sudo visudo -cf /etc/sudoers.d/<user>      # must print "... parsed OK" before you rely on it
```

## 5. Silence the Docker completion warning (if you use Docker Desktop)

If new zsh shells print `compinit: no such file or directory: /usr/share/zsh/vendor-completions/_docker`, that's a **known current issue**: Docker Desktop's WSL integration creates a `_docker` completion symlink pointing into a mount that only exists while Docker Desktop runs; when it quits, the symlink dangles. Removing it clears the warning:

```bash
[ -L /usr/share/zsh/vendor-completions/_docker ] && [ ! -e /usr/share/zsh/vendor-completions/_docker ] && sudo rm /usr/share/zsh/vendor-completions/_docker
```

Caveat: it can **reappear** the next time Docker Desktop starts. For a durable fix, use Docker's own completion path instead — add `FPATH="$HOME/.docker/completions:$FPATH"` (before `compinit`) and generate `docker completion zsh > ~/.docker/completions/_docker`. (docker/for-win #14056 / #8336, ohmyzsh #12154.)

## 6. Font — JetBrains Mono with ligatures (configured on Windows)

Because the WSL terminal is rendered Windows-side, the font is installed and selected **on Windows**, not in WSL. For programming ligatures *and* the powerline/oh-my-zsh glyphs, use the **Nerd Font** variant of JetBrains Mono — the patched variant preserves JetBrains Mono's ligatures (restored in Nerd Fonts v2.1.0 after a brief v2.0.0 regression), and a Nerd Font is required or themes show ▯ replacement boxes.

**Install on Windows** (winget verified live, v3.3.0):

```powershell
winget install -e --id DEVCOM.JetBrainsMonoNerdFont
# alternatives: scoop bucket add nerd-fonts; scoop install JetBrainsMono-NF
#               or download from https://www.nerdfonts.com/font-downloads and install the .ttf
```

**Enable in Windows Terminal** — `settings.json`, in the WSL profile (or under `profiles.defaults`). Windows Terminal toggles ligatures natively via the per-profile `font.features` object:

```jsonc
"profiles": {
  "defaults": {
    "font": {
      "face": "JetBrainsMono Nerd Font",
      "features": { "liga": 1, "calt": 1 }   // enable standard + contextual ligatures
    }
  }
}
```

Pick the **"JetBrainsMono Nerd Font"** face (the proportional/standard patched family) rather than the strict single-width **"JetBrainsMono Nerd Font Mono"** if you want ligatures to render most reliably.

## 7. Windows Terminal profile — make the distro appear, with an icon, as the default

A freshly installed distro often won't show in the Windows Terminal dropdown right
away, and when it does it may render **without an icon**. The knobs:

- **It only appears after a re-scan.** Windows Terminal generates WSL profiles at
  startup, so a distro installed while the Terminal was open won't show until it
  re-scans. Restarting the Terminal works; so does **saving `settings.json`** — the
  Terminal watches that file and live-reloads, regenerating the WSL profiles.
- **Don't hand-author the WSL profile by guessing its GUID — especially on
  Preview.** Windows Terminal **Preview** generates the Ubuntu profile from the
  *Store-app source* (`"source": "CanonicalGroupLimited.Ubuntu_…"`) with its own
  GUID, **not** from the legacy `Windows.Terminal.Wsl` generator (whose GUID is the
  UUIDv5 of the distro name, e.g. `{2c4de342-…}` for "Ubuntu"). If you add a profile
  with the legacy GUID by hand, you get **two** Ubuntu entries; the Terminal then
  marks one `"hidden": true` to dedupe. Let the Terminal generate the profile, then
  edit *that* entry.
- **Add an explicit icon.** Set `"icon"` on the generated profile to the Ubuntu
  logo. The package ships PNGs under
  `C:\Program Files\WindowsApps\CanonicalGroupLimited.Ubuntu_*\Assets\` — but that
  path is **version-stamped** (breaks on app update) and the `WindowsApps` root
  blocks wildcard listing. Resolve the exact dir via
  `(Get-AppxPackage CanonicalGroupLimited.Ubuntu*).InstallLocation`, then **copy the
  PNG to a stable location** and point at that:

  ```powershell
  $pkg = Get-AppxPackage CanonicalGroupLimited.Ubuntu*
  New-Item -ItemType Directory -Force "$HOME\.wsl-icons" | Out-Null
  Copy-Item (Join-Path $pkg.InstallLocation 'Assets\Square44x44Logo.targetsize-256.png') "$HOME\.wsl-icons\ubuntu.png"
  ```
  ```jsonc
  { "guid": "{…the generated GUID…}", "name": "Ubuntu",
    "source": "CanonicalGroupLimited.Ubuntu_79rhkp1fndgsc",
    "icon": "C:\\Users\\<you>\\.wsl-icons\\ubuntu.png",
    "startingDirectory": "~" }
  ```
- **"Default WSL distro" ≠ "default Terminal profile".** `wsl --set-default Ubuntu`
  only changes which distro bare `wsl` enters; it does **not** make the Terminal
  open Ubuntu by default. For that, set the top-level `"defaultProfile"` in
  `settings.json` to the Ubuntu profile's GUID. Two independent settings.

Validate the JSON after editing (`Get-Content settings.json -Raw | ConvertFrom-Json`)
— a trailing-comma typo silently reverts the Terminal to defaults.

---

### Sources (verified 2026)

- zsh login PATH / `/etc/zsh/zprofile` not sourcing `/etc/profile`: Ubuntu bug #1800280.
- `wsl.conf` has no shell key: Microsoft Learn — WSL config reference.
- Docker `_docker` dangling symlink: docker/for-win #14056, #8336; ohmyzsh #12154.
- Nerd Font ligatures preserved + needed for glyphs: ryanoasis/nerd-fonts JetBrainsMono README; Microsoft Learn — Terminal custom prompt setup.
- Windows Terminal `font.features`: Microsoft Learn — Terminal profile appearance.
- oh-my-zsh maintained / Starship as lighter prompt: github.com/ohmyzsh/ohmyzsh; starship.rs.
