#!/usr/bin/env bash
# Reset a local Zitadel docker-compose deployment to a clean state.
# Wipes the Zitadel Postgres volume and the /current-dir volume that holds
# the PAT files. Then fixes the volume permissions so the next boot can
# write the FirstInstance PAT (uid 1000 = the Zitadel container user).
#
# Usage: ./reset-zitadel.sh [path/to/docker-compose.zitadel.yml] [path/to/zitadel/local]
# Defaults assume CWD = infra/docker (the conventional location).
set -euo pipefail

COMPOSE_FILE="${1:-docker-compose.zitadel.yml}"
LOCAL_DIR="${2:-zitadel/local}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

echo "[reset-zitadel] tearing down stack + volumes…"
docker compose -f "$COMPOSE_FILE" down -v

echo "[reset-zitadel] resetting volume permissions on $LOCAL_DIR (uid 1000)…"
mkdir -p "$LOCAL_DIR"
docker run --rm -v "$(realpath "$LOCAL_DIR"):/work" alpine sh -c \
  "rm -rf /work/* /work/.* 2>/dev/null || true; chown 1000:1000 /work && chmod 0777 /work"

echo "[reset-zitadel] starting stack…"
docker compose -f "$COMPOSE_FILE" up -d

echo "[reset-zitadel] waiting for zitadel container to become healthy…"
ZITADEL_CONTAINER=$(docker compose -f "$COMPOSE_FILE" ps -q zitadel)
until docker inspect --format '{{.State.Health.Status}}' "$ZITADEL_CONTAINER" 2>/dev/null | grep -q "healthy"; do
  sleep 3
  printf "."
done
echo ""

PAT_FILE="$LOCAL_DIR/admin.pat"
if [[ -s "$PAT_FILE" ]]; then
  echo "[reset-zitadel] OK — PAT written at $PAT_FILE"
else
  echo "[reset-zitadel] FAIL — PAT not at $PAT_FILE."
  echo "  Likely cause: ZITADEL_FIRSTINSTANCE_* envs are on the wrong service in your"
  echo "  compose file. They must be on the 'zitadel' service (which runs setup),"
  echo "  not on 'zitadel-init' (schema only). See the docker-compose-bootstrap.md"
  echo "  reference in this skill, §1."
  exit 2
fi
