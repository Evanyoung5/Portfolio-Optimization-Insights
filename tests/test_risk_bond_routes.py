import pytest

import app.api.routes as routes
from app.api.routes import portfolio_repository
from app.db.models import MarketQuote


def _portfolio(client, auth_headers):
    response = client.post(
        "/portfolios",
        headers=auth_headers,
        json={
            "name": "Risk and Bonds",
            "cash": 1000,
            "positions": [
                {"symbol": "AAPL", "quantity": 10, "price": 200, "asset_class": "equity"},
                {"symbol": "AGG", "quantity": 20, "price": 100, "asset_class": "bond"},
            ],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_risk_tolerance_is_private_persistent_setting_and_drives_reweighting(client, auth_headers):
    portfolio_id = _portfolio(client, auth_headers)
    settings = client.patch(
        f"/portfolios/{portfolio_id}/settings",
        headers=auth_headers,
        json={"risk_tolerance_score": 3, "bond_watchlist": ["shy", "agg"]},
    )
    assert settings.status_code == 200
    assert settings.json()["risk_tolerance_score"] == 3
    assert settings.json()["bond_watchlist"] == ["SHY", "AGG"]

    state = client.get(f"/portfolios/{portfolio_id}/risk-tolerance", headers=auth_headers)
    assert state.status_code == 200
    assert state.json()["profile"]["label"] == "Conservative"

    result = client.post(
        f"/portfolios/{portfolio_id}/risk-tolerance/reweight",
        headers=auth_headers,
        json={"bond_symbols": ["SHY", "AGG"], "max_position_weight": 0.50},
    )
    assert result.status_code == 200
    assert sum(item["target_weight"] for item in result.json()["allocations"]) == pytest.approx(1.0)


def test_bond_catalog_returns_cached_public_prices_and_risk_fit_defaults(client, auth_headers):
    portfolio_id = _portfolio(client, auth_headers)
    client.patch(
        f"/portfolios/{portfolio_id}/settings",
        headers=auth_headers,
        json={"risk_tolerance_score": 4, "bond_watchlist": ["SHY"]},
    )
    portfolio_repository.upsert_market_quotes(
        [MarketQuote(ticker="SHY", price=82.25, provider="test", previous_close=82.0, daily_return_pct=0.3049)]
    )

    response = client.get(f"/portfolios/{portfolio_id}/bond-assets", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    shy = next(item for item in payload["assets"] if item["ticker"] == "SHY")
    assert shy["price"] == pytest.approx(82.25)
    assert shy["monitored"] is True
    assert len(payload["recommended_ladder"]) == 5
    assert len(payload["recommended_barbell"]) == 2


def test_bond_strategy_route_calculates_income_and_duration(client, auth_headers):
    portfolio_id = _portfolio(client, auth_headers)
    response = client.post(
        f"/portfolios/{portfolio_id}/bond-strategies/analyze",
        headers=auth_headers,
        json={
            "strategy_type": "barbell",
            "capital": 15_000,
            "risk_score": 6,
            "rungs": [
                {
                    "label": "Short",
                    "allocation_weight": 0.55,
                    "face_value": 1000,
                    "market_price_pct": 100,
                    "coupon_rate": 0.04,
                    "yield_to_maturity": 0.04,
                    "years_to_maturity": 1,
                },
                {
                    "label": "Long",
                    "allocation_weight": 0.45,
                    "face_value": 1000,
                    "market_price_pct": 98,
                    "coupon_rate": 0.05,
                    "yield_to_maturity": 0.052,
                    "years_to_maturity": 10,
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["annual_income"] > 0
    assert payload["summary"]["weighted_modified_duration"] > 0
    assert payload["strategy_type"] == "barbell"


def test_bond_refresh_queues_only_catalog_tickers_through_background_worker(client, auth_headers, monkeypatch):
    portfolio_id = _portfolio(client, auth_headers)
    captured = {}

    def fake_enqueue(job, payload=None):
        captured["job_type"] = job.job_type
        captured["payload"] = payload

    monkeypatch.setattr(routes, "enqueue_background_job_message", fake_enqueue)
    monkeypatch.setattr(routes, "_enforce_market_data_refresh_limits", lambda **kwargs: None)

    response = client.post(
        f"/portfolios/{portfolio_id}/bond-assets/refresh",
        headers=auth_headers,
        json={"tickers": ["SHY", "IEF"]},
    )

    assert response.status_code == 202
    assert captured["job_type"] == "refresh_bond_market_data"
    assert captured["payload"]["tickers"] == ["SHY", "IEF"]
    assert captured["payload"]["provider_signature"].startswith("account-")
