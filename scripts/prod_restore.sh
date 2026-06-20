#!/bin/sh
set -eu

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/prod_restore.sh <postgres_dump_path>" >&2
  exit 1
fi

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-}"
DUMP_PATH="$1"
POSTGRES_DB="${POSTGRES_DB:-portfolio}"
POSTGRES_USER="${POSTGRES_USER:-portfolio}"
TARGET_DATABASE="${TARGET_DATABASE:-$POSTGRES_DB}"
ALLOW_DROP="${ALLOW_DROP:-false}"

if [ ! -f "$DUMP_PATH" ]; then
  echo "Dump file not found: $DUMP_PATH" >&2
  exit 1
fi

compose() {
  if [ -n "$ENV_FILE" ]; then
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
  else
    docker compose -f "$COMPOSE_FILE" "$@"
  fi
}

restoring_primary=false
if [ "$TARGET_DATABASE" = "$POSTGRES_DB" ]; then
  restoring_primary=true
fi

if [ "$restoring_primary" = true ] && [ "$ALLOW_DROP" != "true" ]; then
  echo "Refusing to restore the primary database without ALLOW_DROP=true. This operation replaces live database contents." >&2
  exit 1
fi

if [ "$restoring_primary" = true ]; then
  echo "Stopping API and worker before restore"
  compose stop api worker
fi

echo "Resetting target database $TARGET_DATABASE"
compose exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $TARGET_DATABASE;"
compose exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $TARGET_DATABASE;"

echo "Restoring Postgres backup from $DUMP_PATH"
cat "$DUMP_PATH" | compose exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$TARGET_DATABASE" --clean --if-exists --no-owner --no-privileges

if [ "$restoring_primary" = true ]; then
  echo "Restarting migrate, api, and worker"
  compose up -d migrate
  compose up -d api worker
fi

echo "Restore complete into $TARGET_DATABASE."
