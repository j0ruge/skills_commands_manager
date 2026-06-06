#!/usr/bin/env bash
# migrate-repos.sh — copy a Windows projects folder into the WSL Linux filesystem,
# keeping .git and .env, excluding rebuildable dirs, then VALIDATE.
#
# This script NEVER deletes anything. Deleting the Windows source is the one
# irreversible step and is left to the human, AFTER reviewing the validation.
#
# Usage (inside WSL):
#   bash migrate-repos.sh <SRC> <DST>
#   bash migrate-repos.sh /mnt/c/Users/you/source/repos ~/repos
#   bash migrate-repos.sh --dry-run /mnt/c/Users/you/source/repos ~/repos
set -euo pipefail

DRY=""
if [ "${1:-}" = "--dry-run" ]; then DRY="--dry-run"; shift; fi

SRC="${1:-}"
DST="${2:-}"
if [ -z "$SRC" ] || [ -z "$DST" ]; then
  echo "usage: bash migrate-repos.sh [--dry-run] <SRC> <DST>" >&2
  echo "  e.g. bash migrate-repos.sh /mnt/c/Users/you/source/repos ~/repos" >&2
  exit 2
fi
# expand a leading ~ in DST
DST="${DST/#\~/$HOME}"

if [ ! -d "$SRC" ]; then echo "SRC does not exist: $SRC" >&2; exit 1; fi

echo "== Free space on destination filesystem =="
df -h "$(dirname "$DST")" 2>/dev/null | awk 'NR==1 || NR==2'
echo "  (Not sizing SRC with du — du over /mnt/c is pathologically slow.)"
echo

# Warn if the destination already has content — rsync -a MERGES and overwrites
# silently, so re-running into a populated DST can clobber. Caller should confirm.
if [ -d "$DST" ] && [ -n "$(ls -A "$DST" 2>/dev/null)" ]; then
  echo "!! WARNING: destination $DST is not empty — rsync will merge/overwrite into it."
  echo "   If that is not intended, stop and pick a fresh DST (or review it first)."
  echo
fi

# Don't create the destination on a dry-run — a dry-run must touch nothing.
[ -z "$DRY" ] && mkdir -p "$DST"

EXCLUDES=(
  --exclude=node_modules/
  --exclude=.venv/ --exclude=venv/
  --exclude=__pycache__/ --exclude='*.pyc'
  --exclude=.pytest_cache/ --exclude=.mypy_cache/ --exclude=.ruff_cache/
  --exclude=.next/ --exclude=.nuxt/
  --exclude=dist/ --exclude=build/
  --exclude=target/
  --exclude=bin/ --exclude=obj/
  --exclude=.gradle/
)

echo "== rsync ${DRY:+(dry-run) }$SRC/  ->  $DST/ =="
echo "   keeping .git and .env; excluding rebuildable dirs"
# --info=progress2 gives a single live progress line; over /mnt/c this is slow,
# so the caller will usually launch this whole script in the background.
rsync -a $DRY --info=progress2 --stats "${EXCLUDES[@]}" "$SRC"/ "$DST"/

if [ -n "$DRY" ]; then
  echo
  echo "Dry-run only — nothing was written. Re-run without --dry-run to copy."
  exit 0
fi

echo
echo "================ VALIDATION ================"

echo "-- top-level entries (diff; empty == identical) --"
if diff <(ls -A "$SRC" | sort) <(ls -A "$DST" | sort); then
  echo "   OK: identical top-level entries"
else
  echo "   !! top-level differs (review < only-in-SRC, > only-in-DST)"
fi

echo "-- git repositories --"
src_git=$(find "$SRC" -maxdepth 2 -type d -name .git 2>/dev/null | wc -l)
dst_git=$(find "$DST" -maxdepth 2 -type d -name .git 2>/dev/null | wc -l)
echo "   src=$src_git  dst=$dst_git $([ "$src_git" = "$dst_git" ] && echo OK || echo '!! MISMATCH')"

echo "-- .env files present in SRC but missing in DST (by path) --"
missing=$(diff <(cd "$SRC" && find . -name '.env*' -type f 2>/dev/null | sort) \
               <(cd "$DST" && find . -name '.env*' -type f 2>/dev/null | sort) | grep '^<' || true)
if [ -z "$missing" ]; then
  echo "   OK: every .env present"
else
  echo "$missing" | sed 's/^< /   missing: /'
  echo "   NOTE: paths inside node_modules (e.g. node_modules/psl/.env) are dependency"
  echo "         internals, recreated on install — harmless. Worry only about real config."
fi

echo
echo "============================================"
echo "Copy complete and validated. NOTHING was deleted."
echo "Next steps (do by hand, after reviewing the above):"
echo "  1. Confirm projects run from $DST."
echo "  2. THEN delete the Windows source if you chose 'move':"
echo "       PowerShell> Remove-Item -LiteralPath '<windows path>' -Recurse -Force"
echo "  3. Reinstall deps per stack (npm install / pip install -r / dotnet restore / mix deps.get)."
echo "  4. Repoint any shell alias from /mnt/c/... to $DST."
