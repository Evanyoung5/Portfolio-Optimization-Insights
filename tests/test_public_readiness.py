import pytest

from app.security import (
    ConfigurationError,
    auth_cookie_samesite,
    redact_runtime_payload,
    validate_runtime_configuration,
)


def test_public_runtime_validation_rejects_unsafe_defaults(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_APP_URL", "https://example.com")
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://example.com")
    monkeypatch.setenv("APP_HOSTS", "example.com")
    monkeypatch.setenv("PORTFOLIO_REPOSITORY", "postgres")
    monkeypatch.setenv("AUTH_SECRET_KEY", "dev-only-change-me")
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", "dev-only-change-me")
    monkeypatch.setenv("AUTH_DEV_EXPOSE_TOKENS", "true")
    monkeypatch.setenv("MARKET_DATA_REQUIRE_REDIS_LIMITER", "false")
    monkeypatch.setenv("AUTH_REQUIRE_REDIS_LIMITER", "false")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("SMTP_FROM_EMAIL", raising=False)

    with pytest.raises(ConfigurationError):
        validate_runtime_configuration()


def test_public_runtime_redacts_internal_counts(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    payload = {
        "status": "ok",
        "database": {"kind": "postgres", "users": 3, "portfolios": 7, "market_quotes": 12, "url": "postgresql://db/portfolio"},
        "redis": {"ok": True, "keys": 99, "url": "redis://redis:6379/0"},
    }

    redacted = redact_runtime_payload(payload)

    assert redacted["database"]["kind"] == "postgres"
    assert "users" not in redacted["database"]
    assert "portfolios" not in redacted["database"]
    assert "market_quotes" not in redacted["database"]
    assert "keys" not in redacted["redis"]


def test_public_runtime_rejects_insecure_samesite_none(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_APP_URL", "https://example.com")
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://example.com")
    monkeypatch.setenv("APP_HOSTS", "example.com")
    monkeypatch.setenv("PORTFOLIO_REPOSITORY", "postgres")
    monkeypatch.setenv("AUTH_SECRET_KEY", "A" * 40)
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", "B" * 40)
    monkeypatch.setenv("AUTH_DEV_EXPOSE_TOKENS", "false")
    monkeypatch.setenv("MARKET_DATA_REQUIRE_REDIS_LIMITER", "true")
    monkeypatch.setenv("AUTH_REQUIRE_REDIS_LIMITER", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "none")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")

    assert auth_cookie_samesite() == "none"
    with pytest.raises(ConfigurationError):
        validate_runtime_configuration()
