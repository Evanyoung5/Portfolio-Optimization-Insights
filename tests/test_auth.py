import pytest


def _register(client, email="user@example.com", password="SufficientPass123"):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    payload = response.json()
    return payload, {"Authorization": f"Bearer {payload['access_token']}"}


def test_register_login_and_me_routes(client):
    registered, headers = _register(client, email="USER@Example.com")

    assert registered["token_type"] == "bearer"
    assert registered["access_token"]
    assert registered["user"]["email"] == "user@example.com"

    missing_auth = client.get("/me")
    assert missing_auth.status_code == 401

    me_response = client.get("/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json() == registered["user"]

    bad_login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401

    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "SufficientPass123"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"] == registered["user"]


def test_duplicate_registration_is_rejected(client):
    _register(client, email="duplicate@example.com")

    response = client.post(
        "/auth/register",
        json={"email": "duplicate@example.com", "password": "SufficientPass123"},
    )

    assert response.status_code == 409


def test_register_rejects_invalid_email(client):
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "SufficientPass123"},
    )

    assert response.status_code == 422


def test_authenticated_portfolio_is_private_to_owner(client):
    owner, owner_headers = _register(client, email="owner@example.com")
    _, other_headers = _register(client, email="other@example.com")

    create_response = client.post(
        "/portfolios",
        headers=owner_headers,
        json={
            "name": "Private Portfolio",
            "cash": 250,
            "positions": [
                {"symbol": "AAPL", "quantity": 2, "price": 100},
                {"symbol": "BND", "quantity": 4, "price": 50},
            ],
        },
    )
    assert create_response.status_code == 201
    portfolio = create_response.json()

    unauthenticated = client.get(f"/portfolios/{portfolio['id']}")
    assert unauthenticated.status_code == 401

    wrong_user = client.get(f"/portfolios/{portfolio['id']}", headers=other_headers)
    assert wrong_user.status_code == 404

    owner_response = client.get(f"/portfolios/{portfolio['id']}", headers=owner_headers)
    assert owner_response.status_code == 200
    assert owner_response.json()["name"] == "Private Portfolio"

    owner_list = client.get("/me/portfolios", headers=owner_headers)
    assert owner_list.status_code == 200
    owner_portfolios = owner_list.json()["portfolios"]
    assert len(owner_portfolios) == 1
    assert owner_portfolios[0]["id"] == portfolio["id"]
    assert owner_portfolios[0]["name"] == "Private Portfolio"
    assert owner_portfolios[0]["cash"] == pytest.approx(250)
    assert owner_portfolios[0]["total_market_value"] == pytest.approx(400)
    assert owner_portfolios[0]["total_equity"] == pytest.approx(650)
    assert owner_portfolios[0]["positions_count"] == 2
    assert owner_portfolios[0]["updated_at"]

    other_list = client.get("/me/portfolios", headers=other_headers)
    assert other_list.status_code == 200
    assert other_list.json()["portfolios"] == []

    wrong_user_analysis = client.post(
        f"/portfolios/{portfolio['id']}/analyze",
        headers=other_headers,
        json={},
    )
    assert wrong_user_analysis.status_code == 404
    assert owner["user"]["email"] == "owner@example.com"


def test_portfolio_creation_requires_login(client):
    response = client.post("/portfolios", json={"name": "Private Required"})

    assert response.status_code == 401


def test_refresh_token_rotates_and_logout_revokes(client):
    registered, _ = _register(client, email="refresh@example.com")
    refresh_token = registered["refresh_token"]

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    rotated = refresh_response.json()
    assert rotated["access_token"] != registered["access_token"]
    assert rotated["refresh_token"] != refresh_token

    old_token_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert old_token_response.status_code == 401

    logout_response = client.post("/auth/logout", json={"refresh_token": rotated["refresh_token"]})
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Logged out."

    revoked_response = client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert revoked_response.status_code == 401


def test_password_reset_uses_one_time_token_and_revokes_refresh_tokens(client, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_EXPOSE_TOKENS", "true")
    registered, _ = _register(
        client,
        email="reset@example.com",
        password="OriginalPass123",
    )

    request_response = client.post(
        "/auth/password-reset/request",
        json={"email": "reset@example.com"},
    )
    assert request_response.status_code == 200
    reset_token = request_response.json()["dev_token"]
    assert reset_token

    confirm_response = client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "NewPassword123"},
    )
    assert confirm_response.status_code == 200

    reused_response = client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "AnotherPass123"},
    )
    assert reused_response.status_code == 400

    old_login = client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "OriginalPass123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "NewPassword123"},
    )
    assert new_login.status_code == 200

    old_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )
    assert old_refresh.status_code == 401


def test_email_verification_token_marks_user_verified(client, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_EXPOSE_TOKENS", "true")
    registered, headers = _register(client, email="verify@example.com")
    assert registered["user"]["email_verified"] is False

    request_response = client.post("/auth/email-verification/request", headers=headers)
    assert request_response.status_code == 200
    verification_token = request_response.json()["dev_token"]
    assert verification_token

    confirm_response = client.post(
        "/auth/email-verification/confirm",
        json={"token": verification_token},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["email_verified"] is True

    me_response = client.get("/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email_verified"] is True
