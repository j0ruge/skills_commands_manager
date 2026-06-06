# Phase 2 — Install rtk

rtk (https://github.com/rtk-ai/rtk) is a **single Rust binary with zero runtime dependencies**. On Windows the project recommends WSL, because on Linux rtk has full support for the hook-based auto-rewrite mode (on native Windows it falls back to CLAUDE.md injection). So we install it *inside* WSL.

## What rtk does and does NOT need

- It does **not** need Node, Python, Go, Ruby, or Docker to run. Those only matter if you later want rtk to filter *their* command output (e.g. `rtk npm run build`, `rtk pytest`).
- It does **not** need the Rust toolchain — the install script fetches a prebuilt binary. Do **not** `apt install cargo`/rustup just for rtk; that's wasted time and disk.
- The only real prerequisites are `curl` (to fetch the install script) and `bash`. `git` is useful because rtk filters dev-command output.

## Install (inside WSL)

```bash
# 1. Fetch and run the official install script (prebuilt binary, no Rust needed)
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh

# 2. Put ~/.local/bin on PATH — the script installs there but does NOT edit your PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 3. Verify
rtk --version
```

### The PATH gotcha (the #1 reason "it didn't work")

The installer prints something like:

```
[INFO] Successfully installed rtk to /home/<you>/.local/bin/rtk
[WARN] Binary installed but not in PATH. Add to your shell profile:
[WARN]   export PATH="$HOME/.local/bin:$PATH"
```

If you skip step 2, `rtk` is "command not found" even though it installed perfectly. Add the line to `~/.bashrc` and open a new shell (or `source ~/.bashrc`). Don't reinstall — it's only PATH.

> **If you later switch to zsh:** this PATH line lives in `~/.bashrc`, which zsh does **not** read — `rtk` will be "not found" again in zsh until you add the same `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc`. On Ubuntu the system profile won't add `~/.local/bin` for a zsh login shell either, so the explicit line is required. See `references/shell-setup.md`.

## Alternative install methods

- **Homebrew** (if installed): `brew install rtk`
- **Cargo** (only if you already have Rust): `cargo install --git https://github.com/rtk-ai/rtk`
- **Manual binary**: download from https://github.com/rtk-ai/rtk/releases (Linux musl tarball for WSL)

Prefer the install script — it's the least-dependency path.

## Using rtk

rtk **prefixes** dev commands to filter/condense their output (token savings):

```bash
rtk --help
rtk gain              # token-savings stats
rtk cargo test
rtk npm run build
rtk pytest
```

On WSL/Linux the hook-based auto-rewrite is available (it isn't on native Windows) — one more reason the WSL path is the recommended one.

## Per-project or global? (a common question)

**You install rtk once, not per project.** The binary lives at `~/.local/bin/rtk` and, being on PATH, is available to every project and every shell for that WSL user. There is nothing to install inside each repo.

Two ways to use it, neither of which re-installs anything:

- **Prefix commands manually** — `rtk npm test`, `rtk pytest` — works in any directory with zero config.
- **Auto-integrate with Claude Code** via the hook (Linux/WSL) or CLAUDE.md injection. The *integration config* can be global (`~/.claude/`) or per-project (`.claude/`), but that is just wiring — the rtk binary itself remains a single global install. So "does it serve everything I do in Claude Code?" — yes: install once, and it applies everywhere; the only per-project choice is whether you also want the automatic hook wired in that repo.
