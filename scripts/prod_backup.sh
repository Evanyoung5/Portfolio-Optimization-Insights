#!/bin/sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-}"
BACKUP_DIR="${1:-backups}"
STAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
POSTGRES_DB="${POSTGRES_DB:-portfolio}"
POSTGRES_USER="${POSTGRES_USER:-portfolio}"
INCLUDE_REDIS="${INCLUDE_REDIS:-false}"

mkdir -p "$BACKUP_DIR"

compose() {
  if [ -n "$ENV_FILE" ]; then
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
  else
    docker compose -f "$COMPOSE_FILE" "$@"
  fi
}

write_checksum() {
  target="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$target" > "$target.sha256"
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$target" > "$target.sha256"
  else
    python3 - "$target" <<'PY' > "$target.sha256"
import hashlib
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
digest = hashlib.sha256(path.read_bytes()).hexdigest()
print(f"{digest}  {path}")
PY
  fi
}

POSTGRES_OUT="$BACKUP_DIR/postgres_${STAMP}.dump"
echo "Creating Postgres backup at $POSTGRES_OUT"
compose exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$POSTGRES_OUT"

SHA_OUT="$POSTGRES_OUT.sha256"
write_checksum "$POSTGRES_OUT"
echo "Wrote checksum to $SHA_OUT"

if [ "$INCLUDE_REDIS" = "true" ]; then
  REDIS_OUT="$BACKUP_DIR/redis_${STAMP}.tar"
  echo "Creating optional Redis snapshot at $REDIS_OUT"
  compose exec -T redis sh -lc 'cd /data && tar -cf - .' > "$REDIS_OUT"
  write_checksum "$REDIS_OUT"
fi

echo "Backup complete."
