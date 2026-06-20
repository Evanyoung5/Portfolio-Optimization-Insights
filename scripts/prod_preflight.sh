#!/bin/sh
set -eu

ENV_FILE="${1:-${ENV_FILE:-.env.production}}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Env file not found: $ENV_FILE" >&2
  echo "Usage: scripts/prod_preflight.sh [path-to-env-file]" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

warn() {
  echo "[WARN] $1" >&2
}

pass() {
  echo "[PASS] $1"
}

is_placeholder() {
  case "${1:-}" in
    ""|change-me-to-a-long-random-secret|change-me-to-a-long-random-encryption-key|replace-with-a-long-random-auth-secret|replace-with-a-long-random-data-encryption-secret|replace-with-a-long-random-password|replace-with-smtp-user|replace-with-smtp-password|dev-only-change-me)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

require_value() {
  name="$1"
  eval "value=\${$name:-}"
  if is_placeholder "$value"; then
    fail "$name is missing or still using a placeholder value."
  fi
  pass "$name is set"
}

require_secret_len() {
  name="$1"
  eval "value=\${$name:-}"
  if [ "${#value}" -lt 32 ]; then
    fail "$name must be at least 32 characters."
  fi
  pass "$name length looks strong"
}

require_contains() {
  name="$1"
  needle="$2"
  eval "value=\${$name:-}"
  case "$value" in
    *"$needle"*)
      pass "$name includes $needle"
      ;;
    *)
      fail "$name must include $needle"
      ;;
  esac
}

require_https_url() {
  name="$1"
  eval "value=\${$name:-}"
  case "$value" in
    https://*)
      pass "$name uses https"
      ;;
    *)
      fail "$name must start with https:// for public hosting."
      ;;
  esac
}

require_true() {
  name="$1"
  eval "value=\${$name:-}"
  case "$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on)
      pass "$name is enabled"
      ;;
    *)
      fail "$name must be true for public hosting."
      ;;
  esac
}

require_false() {
  name="$1"
  eval "value=\${$name:-}"
  case "$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')" in
    ""|0|false|no|off)
      pass "$name is disabled"
      ;;
    *)
      fail "$name must be false for public hosting."
      ;;
  esac
}

require_value APP_ENV
[ "${APP_ENV}" = "production" ] || fail "APP_ENV must be production."
pass "APP_ENV is production"

require_value APP_DOMAIN
require_value FRONTEND_ORIGINS
require_value APP_HOSTS
require_value PUBLIC_APP_URL
require_value PORTFOLIO_REPOSITORY
[ "${PORTFOLIO_REPOSITORY}" = "postgres" ] || fail "PORTFOLIO_REPOSITORY must be postgres."
pass "PORTFOLIO_REPOSITORY is postgres"

require_value POSTGRES_PASSWORD
require_value AUTH_SECRET_KEY
require_value DATA_ENCRYPTION_KEY
require_secret_len AUTH_SECRET_KEY
require_secret_len DATA_ENCRYPTION_KEY

require_https_url PUBLIC_APP_URL
require_contains PUBLIC_APP_URL "$APP_DOMAIN"
require_contains FRONTEND_ORIGINS "https://$APP_DOMAIN"
require_contains APP_HOSTS "$APP_DOMAIN"

require_true ENABLE_HSTS
require_true AUTH_COOKIE_SECURE
require_false AUTH_DEV_EXPOSE_TOKENS
require_true MARKET_DATA_REQUIRE_REDIS_LIMITER
require_true AUTH_REQUIRE_REDIS_LIMITER

require_value SMTP_HOST
require_value SMTP_USERNAME
require_value SMTP_PASSWORD
require_value SMTP_FROM_EMAIL

if [ "${AUTH_COOKIE_SAMESITE:-lax}" = "none" ] && [ "${AUTH_COOKIE_SECURE:-false}" != "true" ]; then
  fail "AUTH_COOKIE_SAMESITE=none requires AUTH_COOKIE_SECURE=true."
fi
pass "Auth cookie settings look coherent"

if [ "${PUBLIC_APP_URL#https://www.}" != "$PUBLIC_APP_URL" ] && [ -z "${AUTH_COOKIE_DOMAIN:-}" ]; then
  warn "PUBLIC_APP_URL uses a subdomain. Set AUTH_COOKIE_DOMAIN if you want shared cookies across apex/www."
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config >/dev/null
pass "docker compose config resolved successfully"

cat <<EOF

Preflight passed.
Next steps:
1. Point DNS A records for $APP_DOMAIN (and www if used) to the VPS.
2. Run: docker compose --env-file $ENV_FILE -f $COMPOSE_FILE up --build -d
3. Run: python3 scripts/prod_smoke_test.py --base-url ${PUBLIC_APP_URL}
4. Verify SMTP: docker compose --env-file $ENV_FILE -f $COMPOSE_FILE exec api python -m app.ops.smtp_check

Important: keep AUTH_SECRET_KEY and DATA_ENCRYPTION_KEY stable after launch. Rotating them casually will invalidate sessions and can make encrypted portfolio data unreadable.
EOF
