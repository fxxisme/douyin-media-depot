#!/usr/bin/env bash
set -euo pipefail

WAIT=0
PRUNE=0
TIMEOUT=600
INTERVAL=15

usage() {
  cat <<'EOF'
Usage: ./scripts/update.sh [--wait] [--prune] [--timeout SECONDS] [--interval SECONDS]

Options:
  --wait              Wait until docker compose pull gets a different image ID.
  --prune             Run docker image prune -f after the update.
  --timeout SECONDS   Max wait time for --wait. Default: 600.
  --interval SECONDS  Pull retry interval for --wait. Default: 15.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --wait)
      WAIT=1
      shift
      ;;
    --prune)
      PRUNE=1
      shift
      ;;
    --timeout)
      TIMEOUT="${2:?Missing value for --timeout}"
      shift 2
      ;;
    --interval)
      INTERVAL="${2:?Missing value for --interval}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_DIR="$(cd -- "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd)"
cd "$REPO_DIR"

echo "==> Updating repository"
git pull --ff-only

IMAGE_NAME="$(docker compose config --images | head -n 1)"
if [[ -z "$IMAGE_NAME" ]]; then
  echo "Unable to resolve compose image name" >&2
  exit 1
fi

image_id() {
  docker image inspect "$IMAGE_NAME" --format '{{.Id}}' 2>/dev/null || true
}

BEFORE_ID="$(image_id)"
echo "==> Compose image: $IMAGE_NAME"
if [[ -n "$BEFORE_ID" ]]; then
  echo "==> Current image: ${BEFORE_ID#sha256:}"
else
  echo "==> Current image: not found locally"
fi

if [[ "$WAIT" -eq 1 ]]; then
  echo "==> Waiting for a new image, timeout ${TIMEOUT}s"
  START_TS="$(date +%s)"
  while true; do
    docker compose pull
    AFTER_ID="$(image_id)"

    if [[ -n "$AFTER_ID" && "$AFTER_ID" != "$BEFORE_ID" ]]; then
      echo "==> New image pulled: ${AFTER_ID#sha256:}"
      break
    fi

    NOW_TS="$(date +%s)"
    ELAPSED=$((NOW_TS - START_TS))
    if (( ELAPSED >= TIMEOUT )); then
      echo "Timed out waiting for a new image. GitHub Actions may still be building." >&2
      echo "Run again later, or run without --wait if you intentionally want the currently available image." >&2
      exit 1
    fi

    echo "==> Image unchanged, retrying in ${INTERVAL}s"
    sleep "$INTERVAL"
  done
else
  echo "==> Pulling latest configured image"
  docker compose pull
fi

echo "==> Recreating container"
docker compose up -d --remove-orphans

if [[ "$PRUNE" -eq 1 ]]; then
  echo "==> Pruning unused images"
  docker image prune -f
fi

echo "==> Update complete"
