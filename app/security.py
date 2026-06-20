from __future__ import annotations

import os
from urllib.parse import urlparse


class ConfigurationError(RuntimeError):
    """Raised when the app is not safely configured for the current environment."""


_PUBLIC_ENVS = {"production", "staging"}
_DEV_ONLY_MARKERS = {
    "",
    "change-me-to-a-long-random-secret",
    "change-me-to-a-long-random-encryption-key",
    "replace-with-a-long-random-auth-secret",
    "replace-with-a-long-random-data-encryption-secret",
    "dev-only-change-me",
}


def app_env() -> str:
    return os.getenv("APP_ENV", "development").strip().lower() or "development"


def is_public_app() -> bool:
    env = app_env()
    public_url = public_app_url()
    if public_url:
        parsed = urlparse(public_url)
        host = (parsed.hostname or "").lower()
        if host not in {"", "localhost", "127.0.0.1"}:
            return True
        if host in {"localhost", "127.0.0.1"}:
            return False
    return env in _PUBLIC_ENVS and not _flag("ALLOW_LOCAL_PRODUCTION_DRILL", default=False)


def public_app_url() -> str:
    return os.getenv("PUBLIC_APP_URL", "").strip()


def frontend_origins() -> list[str]:
    configured = os.getenv("FRONTEND_ORIGINS", "")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def trusted_hosts() -> list[str]:
    configured = os.getenv("APP_HOSTS", "")
    return [host.strip() for host in configured.split(",") if host.strip()]


def auth_cookie_secure() -> bool:
    configured = os.getenv("AUTH_COOKIE_SECURE", "").strip().lower()
    if configured:
        return configured in {"1", "true", "yes", "on"}
    return is_public_app() or public_app_url().startswith("https://")


def auth_cookie_domain() -> str | None:
    configured = os.getenv("AUTH_COOKIE_DOMAIN", "").strip()
    return configured or None


def auth_cookie_samesite() -> str:
    configured = os.getenv("AUTH_COOKIE_SAMESITE", "lax").strip().lower()
    if configured not in {"lax", "strict", "none"}:
        return "lax"
    return configured


def validate_runtime_configuration() -> None:
    if not is_public_app():
        return

    errors: list[str] = []

    if app_env() != "production":
        errors.append("Set APP_ENV=production for public hosting.")
    if not public_app_url().startswith("https://"):
        errors.append("PUBLIC_APP_URL must be an https:// URL in public deployments.")
    if not frontend_origins():
        errors.append("FRONTEND_ORIGINS must list the public site origin(s).")
    if not trusted_hosts():
        errors.append("APP_HOSTS must list the trusted public hostnames.")
    if os.getenv("PORTFOLIO_REPOSITORY", "memory").strip().lower() != "postgres":
        errors.append("PORTFOLIO_REPOSITORY must be 'postgres' for public deployments.")
    if not _secret_is_strong(os.getenv("AUTH_SECRET_KEY")):
        errors.append("AUTH_SECRET_KEY must be set to a strong secret of at least 32 characters.")
    if not _secret_is_strong(os.getenv("DATA_ENCRYPTION_KEY")):
        errors.append("DATA_ENCRYPTION_KEY must be set to a strong secret of at least 32 characters.")
    if _flag("AUTH_DEV_EXPOSE_TOKENS", default=False):
        errors.append("AUTH_DEV_EXPOSE_TOKENS must be false in public deployments.")
    if auth_cookie_samesite() == "none" and not auth_cookie_secure():
        errors.append("AUTH_COOKIE_SAMESITE=none requires AUTH_COOKIE_SECURE=true.")
    if not _smtp_is_configured():
        errors.append("SMTP credentials must be configured so password reset and email verification work publicly.")
    if not _flag("MARKET_DATA_REQUIRE_REDIS_LIMITER", default=False):
        errors.append("MARKET_DATA_REQUIRE_REDIS_LIMITER must be true in public deployments.")
    if not _flag("AUTH_REQUIRE_REDIS_LIMITER", default=False):
        errors.append("AUTH_REQUIRE_REDIS_LIMITER must be true in public deployments.")

    if errors:
        raise ConfigurationError("Unsafe public deployment configuration:\n- " + "\n- ".join(errors))


def default_security_headers() -> dict[str, str]:
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Content-Security-Policy": content_security_policy(),
    }
    if _flag("ENABLE_HSTS", default=False):
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return headers


def content_security_policy() -> str:
    directives = {
        "default-src": ["'self'"],
        "base-uri": ["'self'"],
        "frame-ancestors": ["'none'"],
        "object-src": ["'none'"],
        "form-action": ["'self'"],
        "script-src": ["'self'", "https://cdn.plot.ly"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:", "blob:"],
        "font-src": ["'self'", "data:"],
        "connect-src": ["'self'"],
    }
    if is_public_app():
        directives["upgrade-insecure-requests"] = []
    return "; ".join(
        directive if not values else f"{directive} {' '.join(values)}"
        for directive, values in directives.items()
    )


def redact_runtime_payload(payload: dict[str, object]) -> dict[str, object]:
    if not is_public_app():
        return payload
    redacted = dict(payload)
    database = dict(redacted.get("database") or {})
    redis = dict(redacted.get("redis") or {})
    for key in ("users", "portfolios", "market_quotes", "error"):
        database.pop(key, None)
    redis.pop("keys", None)
    redis.pop("error", None)
    redacted["database"] = database
    redacted["redis"] = redis
    return redacted


def _secret_is_strong(value: str | None) -> bool:
    candidate = (value or "").strip()
    return len(candidate) >= 32 and candidate not in _DEV_ONLY_MARKERS


def _smtp_is_configured() -> bool:
    required = [
        os.getenv("SMTP_HOST", "").strip(),
        os.getenv("SMTP_USERNAME", "").strip(),
        os.getenv("SMTP_PASSWORD", "").strip(),
        os.getenv("SMTP_FROM_EMAIL", "").strip(),
    ]
    return all(required)


def _flag(name: str, *, default: bool) -> bool:
    fallback = "true" if default else "false"
    return os.getenv(name, fallback).strip().lower() in {"1", "true", "yes", "on"}
