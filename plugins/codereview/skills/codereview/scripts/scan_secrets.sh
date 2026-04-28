#!/usr/bin/env bash
# Wrapper para scan_secrets.py — ponto de entrada estável citado pelo SKILL.md
# Phase A. Encaminha argumentos e stdin para o script Python.
#
# Uso:
#   git diff <base>...HEAD --unified=0 | bash scan_secrets.sh
#   bash scan_secrets.sh --base origin/main
#   bash scan_secrets.sh --diff /tmp/x.diff

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/scan_secrets.py" "$@"
