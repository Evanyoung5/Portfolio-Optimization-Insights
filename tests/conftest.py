import os

os.environ["PORTFOLIO_REPOSITORY"] = "memory"

import pytest
from fastapi.testclient import TestClient

from app.api.routes import portfolio_repository
from app.main import create_app


@pytest.fixture(autouse=True)
def reset_repository() -> None:
    portfolio_repository.clear()
    try:
        from app.auth import limiting as auth_limiting

        auth_limiting._AUTH_LIMITER = None
    except Exception:
        pass
    try:
        from app.background.queue import redis_client_from_env

        client = redis_client_from_env()
        keys = (
            list(client.scan_iter("market-data:quote:*"))
            + list(client.scan_iter("market-data:history:*"))
            + list(client.scan_iter("market-data:options:*"))
            + list(client.scan_iter("market-data:options-suite:*"))
        )
        if keys:
            client.delete(*keys)
    except Exception:
        pass


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())



@pytest.fixture
def auth_headers(client) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "SufficientPass123"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
