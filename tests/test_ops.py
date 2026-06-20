from __future__ import annotations

from pathlib import Path

from app.ops import healthcheck, smtp_check


def test_compose_prod_includes_health_checks():
    compose = Path("docker-compose.prod.yml").read_text()

    assert "healthcheck:" in compose
    assert 'python", "-m", "app.ops.healthcheck", "api"' in compose
    assert 'python", "-m", "app.ops.healthcheck", "worker"' in compose
    assert "pg_isready" in compose
    assert 'redis-cli", "ping"' in compose


def test_ops_scripts_exist():
    assert Path("scripts/prod_backup.sh").exists()
    assert Path("scripts/prod_restore.sh").exists()
    assert Path("scripts/prod_smoke_test.py").exists()


def test_healthcheck_api_success(monkeypatch):
    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"status":"ok"}'

    monkeypatch.setattr(healthcheck.urllib.request, "urlopen", lambda *args, **kwargs: DummyResponse())

    assert healthcheck.check_api("http://example.test/health") == 0


def test_smtp_check_requires_to_for_send_test(monkeypatch):
    class DummySmtp:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            return None

        def starttls(self):
            return None

        def login(self, username, password):
            return None

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setattr(smtp_check.smtplib, "SMTP", DummySmtp)

    assert smtp_check.verify_smtp(send_test=True, to_email=None) == 1
