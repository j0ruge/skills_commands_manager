# Phase 3 — Migrate projects from Windows into WSL

The payoff: projects on the native Linux filesystem (`~/repos`) instead of `/mnt/c` run dramatically faster for git, installs, and builds. The risk: this is a file move that can lose `.env` secrets or delete the source prematurely if done naively. The sequence below is **copy → validate → delete**, with the only irreversible step (deletion) last.

`scripts/migrate-repos.sh` performs the copy and validation (and **never deletes**). This file explains the why, the validation, the deletion, and the post-migration surprises.

## Why rsync and not `git clone`

It is tempting to "just re-clone everything fresh on Linux." Don't, unless the user explicitly wants only what's committed:

- **`.env` and other secrets/config are gitignored.** `git clone` will NOT bring them. If the user "already has their envs configured," re-cloning silently drops that configuration. rsync of the working tree preserves it.
- Uncommitted work and local-only files are also lost by re-clone.

So we rsync the working tree, keeping `.git` (history) and `.env` (config), and only drop what's trivially rebuildable. Note that rsync preserves **all** local files, not just `.env` — `appsettings.Development.json`, `secrets.json`, `*.local`, local certs, etc. all come across too (anything `git clone` would have dropped). `.env` is just the most common example; validation focuses on it but the same reasoning covers every gitignored config file.

## Resolve the real source path first

The Windows username, the WSL username, and whatever the user typed can all differ — don't hardcode `<you>`. Discover the actual folder before copying anything:

```bash
ls -d /mnt/c/Users/*/source/repos    # find the real path; confirm it exists before rsync
```

## The copy

Prefer the bundled `scripts/migrate-repos.sh` (it carries the exclude list and validation, warns if the destination is non-empty, and **never deletes**). Because the copy reads from `/mnt/c` it is slow — launch it in the **background** and poll, rather than blocking:

```bash
# dry-run first (writes nothing), then the real copy in the background:
bash scripts/migrate-repos.sh --dry-run /mnt/c/Users/you/source/repos ~/repos
nohup bash scripts/migrate-repos.sh /mnt/c/Users/you/source/repos ~/repos > /tmp/migrate.log 2>&1 &
```

The raw rsync the script runs (equivalent, if you ever do it by hand):

```bash
SRC=/mnt/c/Users/<you>/source/repos
DST=~/repos
mkdir -p "$DST"
rsync -a --stats \
  --exclude=node_modules/ \
  --exclude=.venv/ --exclude=venv/ \
  --exclude=__pycache__/ --exclude='*.pyc' \
  --exclude=.pytest_cache/ --exclude=.mypy_cache/ --exclude=.ruff_cache/ \
  --exclude=.next/ --exclude=.nuxt/ \
  --exclude=dist/ --exclude=build/ \
  --exclude=target/ \
  --exclude=bin/ --exclude=obj/ \
  --exclude=.gradle/ \
  "$SRC"/ "$DST"/
```

Notes:

- **Keep `.git`.** Never add it to the excludes.
- **Excludes are only rebuildable dirs.** node_modules, virtualenvs, build outputs (`dist`/`build`/`target`/`bin`/`obj`/`.next`/`.gradle`), and caches. These are platform-specific (compiled for Windows) and would be wrong on Linux anyway — reinstall them natively after.
- **Run it in the background and poll.** Over `/mnt/c` this is slow (that's the disease we're curing). Don't try to size it first with `du` over `/mnt/c` — `du` there can hang for minutes. Check free space with `df -h ~` instead, which is instant.
- The Windows source is still intact at this point. Good.

## Validate (by paths, not just counts)

```bash
SRC=/mnt/c/Users/<you>/source/repos
DST=~/repos

# 1. Top-level entries identical?
diff <(ls -A "$SRC" | sort) <(ls -A "$DST" | sort) && echo "top-level OK"

# 2. Same number of git repos?
echo "git repos  src=$(find "$SRC" -maxdepth 2 -type d -name .git | wc -l) dst=$(find "$DST" -maxdepth 2 -type d -name .git | wc -l)"

# 3. Which .env files (if any) are in SRC but missing in DST?
diff <(cd "$SRC" && find . -name '.env*' -type f | sort) \
     <(cd "$DST" && find . -name '.env*' -type f | sort) | grep '^<'
```

**The `.env` false positive.** Step 3 may report a couple of "missing" `.env` files — check their paths. If they live **inside an excluded dir** (classically `node_modules/psl/.env`, shipped by the `psl` npm package), they are dependency internals, not your config, and are recreated on `npm install`. That is expected and harmless. Only worry about `.env` files that are real project config. Diff by *path* so you can tell the difference — a raw count comparison can't.

## Delete the Windows source (only after validation, and confirm first)

This is the one irreversible step. Confirm with the user, then prefer PowerShell's native delete (much faster than `rm -rf` over `/mnt/c`):

```powershell
Remove-Item -LiteralPath "C:\Users\<you>\source\repos" -Recurse -Force
```

If the user chose "copy, keep Windows as backup," skip this entirely and let them delete later once they've confirmed everything runs in WSL.

## Post-migration cleanup

- **Fix aliases.** Any alias pointing at `/mnt/c/...repos` now dangles — repoint it at `~/repos`.
- **Reinstall dependencies per stack**, inside WSL:
  - Node: `npm install` (or `pnpm install` / `yarn`)
  - Python: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
  - .NET: `dotnet restore`
  - Elixir: `mix deps.get`
- Your `.env` files are already present, so configuration/secrets carry over.

## The "whole tree modified" surprise (CRLF/LF) — and how to commit cleanly through it

Right after migrating, `git status` inside a repo may show **every tracked file modified** and **zero untracked files**. This is almost always **two artifacts of the move**, not real edits — and they stack:

1. **Line endings (CRLF/LF).** The working tree was checked out on Windows with `core.autocrlf=true` ⇒ files on disk have **CRLF**, while the committed blobs are **LF**. The Linux git (`core.autocrlf=false`) compares CRLF-on-disk against LF-blobs and flags the whole tree.
2. **File mode.** Files copied from `/mnt/c` arrive with permission **`0777`** (the Windows mount's default). With git's default `core.fileMode=true`, every file shows as a mode change (`100644 → 100755`). The tell: `git diff` shows **no content change** but `git status` still says modified.

**Diagnose (don't panic):**

```bash
git diff --ignore-cr-at-eol --stat     # EMPTY ⇒ no real content changes (only CRLF, if any)
git status -s | head                   # still " M"? then it's the file-mode artifact
# Confirm CRLF at the byte level on one file if unsure:
git show :README.md | wc -c            # blob size
wc -c README.md                        # working size; a delta == line count ⇒ +1 byte/line == CRLF
```

For the **file-mode** half, the standard non-destructive fix is to tell git to ignore mode on this checkout (a local `.git/config` setting, not committed, conventional for cross-OS repos):

```bash
git config core.fileMode false         # mode-only "changes" disappear from status
```

**Fix (repo-wide normalization, a deliberate separate change):**

```bash
printf '* text=auto eol=lf\n' >> .gitattributes
git add --renormalize .
git commit -m "chore: normalize line endings to LF after WSL migration"
```

**If you only want to commit a NEW thing right now and not the 150-file line-ending churn:** stage only your specific paths, and make those specific files LF first so their staged diff is just your real change, not the whole-file CRLF flip:

```bash
# normalize ONLY the files you're about to commit to LF
sed -i 's/\r$//' path/to/new_or_edited_file
git add path/to/new_or_edited_file
git diff --cached --stat        # verify the diff is scoped to your change, not the whole tree
```

The wider CRLF cleanup is a real decision for the repo owner — surface it, don't sweep 150 files into an unrelated commit.
