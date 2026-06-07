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

**The `.env` false positive.** Step 3 may report a couple of "missing" `.env` files — check their paths. If they live **inside an excluded dir** — classically `node_modules/psl/.env` (shipped by the `psl` npm package), or a packaged example like `.venv/.../langsmith/cli/.env.example` inside an excluded `.venv`/`venv` — they are dependency internals, not your config, and are recreated on `npm install` / `pip install`. That is expected and harmless. Only worry about `.env` files that are real project config. Diff by *path* so you can tell the difference — a raw count comparison can't. (A clean signal: if a per-repo `rsync -an` dry-run reports **0 file transfers** but your `.env` diff still flags one, that flagged file is necessarily inside an excluded dir — rsync would have copied it otherwise.)

## Delete the Windows source (only after validation, and confirm first)

This is the one irreversible step. Confirm with the user, then prefer PowerShell's native delete (much faster than `rm -rf` over `/mnt/c`):

```powershell
Remove-Item -LiteralPath "C:\Users\<you>\source\repos" -Recurse -Force
```

If the user chose "copy, keep Windows as backup," skip this entirely and let them delete later once they've confirmed everything runs in WSL.

### The reserved-name trap: a `nul` file makes `Remove-Item` fail

A repo created or edited from the Linux side can contain a file whose name is a **Windows reserved device name** — `nul`, `con`, `prn`, `aux`, `com1`–`com9`, `lpt1`–`lpt9` (e.g. a `nul` left behind by a `> nul` redirect written under a different convention). Linux has no such restriction, so the file exists on disk; but Win32 path parsing treats `nul` as the null device, so `Remove-Item`/`del`/`rd` can't address it and fail with:

```
Remove-Item : Cannot remove item C:\...\repo\nul: Incorrect function.
```

Worse, with `-ErrorAction Stop` that error **aborts the whole directory delete**, so the source is *kept* even though everything copied fine — easy to misread as "the migration didn't work." The validated WSL copy is intact; only the Windows-side delete failed.

**Fix: the `\\?\` extended-length path prefix**, which bypasses Win32 name parsing (including reserved-name handling), so the `nul` inside is treated as an ordinary file:

```powershell
Remove-Item -LiteralPath "\\?\C:\Users\<you>\source\repos\<repo>" -Recurse -Force
# fallback if Remove-Item still balks:
cmd /c rd /s /q "\\?\C:\Users\<you>\source\repos\<repo>"
```

The same `\\?\` prefix also clears other Windows-illegal names a Linux checkout can produce (trailing-dot/space names, paths over `MAX_PATH`). If a normal delete fails with "Incorrect function" or "could not find," reach for `\\?\` before assuming the directory is in use.

## Tight disk: migrate one repo at a time (copy → validate → delete per repo)

The default flow copies the **whole** `repos` folder, validates, then deletes the source — fine when the drive has room to hold both copies at once. But the WSL `ext4.vhdx` **lives on `C:` by default** (`%LOCALAPPDATA%\Packages\…Ubuntu…\LocalState\ext4.vhdx`) and **grows on demand** as you write into the Linux filesystem. So copying into WSL *consumes `C:`* while the Windows source still occupies `C:` — transiently you need space for both. On a tight `C:`, copying everything before deleting anything can fill the disk (which is often exactly the half-finished state you're called in to rescue).

Two facts that drive the math:

- **`df -h ~` shows the vhdx's *virtual max* (often ~1 TB), not real usage.** Don't trust that "Avail" — check `C:` free on the Windows side (`Get-PSDrive C`). The real budget is `C:` free.
- Because the copy **excludes** `node_modules`/venvs/build dirs, the bytes written into WSL are *smaller* than the bytes freed when you delete the full Windows source. So per repo, the net effect on `C:` is **downward** — the only risk is the transient peak, which the one-at-a-time loop caps at a single repo.

**The loop** — copy one repo, validate it in isolation, delete its Windows source, then move on:

```bash
SRC=/mnt/c/Users/<you>/source/repos
DST=~/repos
EXCLUDES=(--exclude=node_modules/ --exclude=.venv/ --exclude=venv/ \
  --exclude=__pycache__/ --exclude=.next/ --exclude=dist/ --exclude=build/ \
  --exclude=target/ --exclude=bin/ --exclude=obj/ --exclude=.gradle/)

for name in "$SRC"/*/; do
  repo=$(basename "$name")
  mkdir -p "$DST/$repo"
  rsync -a "${EXCLUDES[@]}" "$SRC/$repo/" "$DST/$repo/"
  # validate THIS repo: 0 real file transfers still pending == fully in sync
  pending=$(rsync -an --itemize-changes "${EXCLUDES[@]}" "$SRC/$repo/" "$DST/$repo/" \
            | grep -cE '^[<>]f')
  sg=$(find "$SRC/$repo" -maxdepth 3 -type d -name .git | wc -l)
  dg=$(find "$DST/$repo" -maxdepth 3 -type d -name .git | wc -l)
  if [ "$pending" -eq 0 ] && [ "$sg" = "$dg" ]; then
    echo "CLEAN $repo — safe to delete Windows source"
    # delete from PowerShell (native, fast); use \\?\ if it has reserved-name files
    powershell.exe -NoProfile -Command \
      "Remove-Item -LiteralPath '\\?\\C:\\Users\\<you>\\source\\repos\\$repo' -Recurse -Force"
  else
    echo "DIRTY $repo (pending=$pending git=$sg/$dg) — KEEP, investigate"
  fi
done
```

Why this shape:

- **The per-repo `rsync -an` dry-run is the gate.** Counting `^[<>]f` itemize lines (file transfers, ignoring dir/permission noise) gives an exact "is this repo fully copied?" answer — far more reliable than top-level counts, and it's what makes the delete safe to automate. **0 = synced.**
- **It resumes an interrupted migration for free.** A repo already fully copied makes `rsync` a near-no-op and validates `pending=0` immediately, so re-running is safe and cheap. A repo left half-copied (e.g. an empty placeholder dir from a previous crash) shows `pending>0` and is finished, not skipped.
- **Never delete on a DIRTY result.** Skip and report it; a non-zero `pending` or a `.git` count mismatch means the copy isn't trustworthy yet.
- **Order CLEAN/already-synced repos first** so their deletes free `C:` early, giving the slower fresh copies more headroom.

Calling `powershell.exe` from inside the WSL loop keeps copy→validate→delete in one place while still using the **native** Windows delete (much faster than `rm -rf` over `/mnt/c`, especially for big `node_modules`). Keep the human confirmation up front — authorize the loop once, with validation gating every individual delete.

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

## Pushing a migrated repo from WSL

If you migrate a repo and then try to `git push`, two things bite — both observed in practice:

### 1. HTTPS push hangs (no credential helper in WSL)

A fresh WSL distro has no git credential helper, no `gh`, and no SSH key, so an HTTPS `git push` to GitHub **hangs forever** waiting for credentials it can't prompt for non-interactively. The clean fix is to **reuse the Windows Git Credential Manager** (Git for Windows ships it), so auth pops a normal Windows window/browser and the credential is cached:

```bash
git config credential.helper '!"/mnt/c/Program Files/Git/mingw64/bin/git-credential-manager.exe"'
```

Two parsing traps make this finicky — get the quoting exactly right:

- The path has **spaces**, so it must be quoted. But a bare quoted path (`"/mnt/c/.../...exe"`) makes git think the value isn't an absolute path (it starts with `"`) and it tries to run `git credential-"/mnt/c/..."` → "is not a git command."
- The working form is the **`!` shell-command prefix** with the path quoted inside: `!"/mnt/c/Program Files/Git/mingw64/bin/git-credential-manager.exe"`. The `!` tells git "run this as a shell command," and the inner quotes survive the space.

First push then triggers GCM's auth UI on Windows; after you complete it once, the credential is cached and subsequent pushes are silent. (SSH is the alternative — `git remote set-url` to the `git@github.com:...` form and add a key — but the GCM bridge reuses what Windows already has.)

### 2. The migrated copy may be behind the real remote

The Windows checkout you migrated from may have been **stale** relative to GitHub (someone pushed more commits since). So your first push is rejected with *"Updates were rejected because the remote contains work that you do not have locally."* Don't force — integrate:

```bash
git fetch origin
git rev-list --left-right --count main...origin/main   # see how far each side diverged
git rebase origin/main                                  # replay your commit(s) on top of the remote
git push origin main
```

Caveat: `git rebase` refuses to start while the working tree is "dirty" — and right after migration it's dirty with the CRLF/filemode noise described above. Since that noise is **not real changes** (verify: `git diff --ignore-cr-at-eol --stat` is empty, and a per-file CR-stripped `diff` of blob vs working tree shows nothing), it's safe to clean it first with `git checkout -- .` (restores the LF blobs), then rebase. If your commit and the remote both edited shared files like `marketplace.json`/`README.md`, the 3-way merge usually still applies cleanly when your edits are additions in different regions — but always re-validate the result (e.g. `python -m json.tool` on any JSON) before pushing.
