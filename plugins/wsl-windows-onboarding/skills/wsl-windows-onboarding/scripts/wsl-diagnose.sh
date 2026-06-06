#!/usr/bin/env bash
# wsl-diagnose.sh — read-only WSL/dev-environment diagnostic.
# Mutates nothing. Run INSIDE a WSL distro:
#   bash wsl-diagnose.sh
# or from Windows:
#   wsl -d Ubuntu -e bash -lc 'bash ~/path/to/wsl-diagnose.sh'
set -u

echo "== Distro =="
if command -v lsb_release >/dev/null 2>&1; then
  lsb_release -d | sed 's/Description:\t*/  /'
else
  grep -E '^PRETTY_NAME=' /etc/os-release 2>/dev/null | cut -d= -f2- | tr -d '"' | sed 's/^/  /'
fi
echo "  user: $(whoami)   home: $HOME"

# Warn if we appear to be inside Docker Desktop's backend distro rather than a real one.
if grep -qi 'docker-desktop' /etc/wsl.conf 2>/dev/null || [ "${HOME:-}" = "/root" ] && grep -qi docker /proc/version 2>/dev/null; then
  echo "  !! This looks like the docker-desktop backend distro — that is NOT your workspace."
  echo "     Work inside a real distro (e.g. Ubuntu): wsl -d Ubuntu"
fi

echo
echo "== Disk (Linux filesystem — where projects should live) =="
df -h "$HOME" | awk 'NR==1 || NR==2 {printf "  %s\n", $0}'

echo
echo "== Required tools =="
for c in git curl rsync; do
  if command -v "$c" >/dev/null 2>&1; then
    printf "  %-6s ok  (%s)\n" "$c" "$("$c" --version 2>&1 | head -n1)"
  else
    printf "  %-6s MISSING  -> sudo apt install -y %s\n" "$c" "$c"
  fi
done

echo
echo "== Optional: rtk =="
if command -v rtk >/dev/null 2>&1; then
  echo "  rtk installed: $(rtk --version 2>&1 | head -n1)"
else
  echo "  rtk not installed (see references/rtk-install.md)"
  if [ -x "$HOME/.local/bin/rtk" ]; then
    echo "  !! ~/.local/bin/rtk EXISTS but is not on PATH — add to ~/.bashrc:"
    echo '     export PATH="$HOME/.local/bin:$PATH"'
  fi
fi

echo
echo "== Optional: docker inside WSL =="
# Docker Desktop leaves a `docker` shim on PATH even when WSL integration is OFF;
# `command -v docker` then lies. Trust an actual successful version call instead.
if docker_v=$(docker --version 2>/dev/null) && printf '%s' "$docker_v" | grep -qi version; then
  echo "  docker usable: $docker_v"
else
  echo "  docker NOT usable in this distro (only needed if you want rtk to filter docker output)."
  echo "  If you use Docker Desktop, enable Settings -> Resources -> WSL Integration for this distro (GUI step)."
fi

echo
echo "Done. This script changed nothing."
