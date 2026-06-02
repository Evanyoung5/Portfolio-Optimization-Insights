from datetime import date, timedelta

import pytest


def _create_portfolio(client, auth_headers):
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Chart Portfolio",
            "cash": 500,
            "positions": [
                {"symbol": "AAPL", "quantity": 10, "price": 100, "asset_class": "equity"},
                {"symbol": "MSFT", "quantity": 5, "price": 200, "asset_class": "equity"},
                {"symbol": "BND", "quantity": 20, "price": 50, "asset_class": "bond"},
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_analyze_route_returns_frontend_chart_payload(client, auth_headers):
    portfolio = _create_portfolio(client, auth_headers)

    response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/analyze",
        headers=auth_headers,
        json={
            "price_history": {
                "tickers": ["AAPL", "MSFT", "BND"],
                "prices": [
                    [100, 200, 50],
                    [102, 198, 50.5],
                    [101, 202, 51],
                    [104, 205, 50.75],
                ],
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == portfolio["id"]
    assert payload["summary"]["total_market_value"] == 3000
    assert payload["summary"]["total_equity"] == 3500

    weights = {point["label"]: point["value"] for point in payload["charts"]["weights"]}
    assert weights == pytest.approx({"AAPL": 2 / 7, "MSFT": 2 / 7, "BND": 2 / 7})

    exposure = {point["label"]: point["value"] for point in payload["charts"]["asset_class_exposure"]}
    assert exposure == pytest.approx({"equity": 4 / 7, "bond": 2 / 7, "cash": 1 / 7})

    risk = payload["charts"]["risk"]
    assert risk["covariance"]["tickers"] == ["AAPL", "MSFT", "BND"]
    assert len(risk["covariance"]["values"]) == 3
    assert len(risk["correlation"]["heatmap"]) == 9
    assert risk["cleaned_correlation"] is not None
    assert risk["cleaned_covariance"] is not None
    assert risk["observations"] == 3
    assert risk["annualization_factor"] == 252.0
    assert [point["label"] for point in risk["volatility_by_ticker"]] == ["AAPL", "MSFT", "BND"]


def test_analyze_route_rejects_bad_price_history_shape(client, auth_headers):
    portfolio = _create_portfolio(client, auth_headers)

    response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/analyze",
        headers=auth_headers,
        json={
            "price_history": {
                "tickers": ["AAPL", "MSFT"],
                "prices": [[100, 200], [101]],
            }
        },
    )

    assert response.status_code == 422


def test_simulate_trade_route_returns_frontend_chart_payload(client, auth_headers):
    portfolio = _create_portfolio(client, auth_headers)
    covariance = {
        "AAPL": {"AAPL": 0.04, "MSFT": 0.01, "BND": 0.0},
        "MSFT": {"AAPL": 0.01, "MSFT": 0.09, "BND": 0.0},
        "BND": {"AAPL": 0.0, "MSFT": 0.0, "BND": 0.01},
    }

    response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/simulate-trade",
        headers=auth_headers,
        json={
            "trades": [
                {"ticker": "AAPL", "side": "buy", "notional": 500},
                {"ticker": "MSFT", "side": "sell", "quantity": 1},
            ],
            "covariance": covariance,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == portfolio["id"]
    assert payload["before_volatility"] > 0
    assert payload["after_volatility"] > 0
    assert payload["volatility_delta"] == pytest.approx(
        payload["after_volatility"] - payload["before_volatility"]
    )

    weights = {point["ticker"]: point for point in payload["charts"]["weights"]}
    assert weights["AAPL"]["before"] == pytest.approx(1 / 3)
    assert weights["AAPL"]["after"] == pytest.approx(1500 / 3300)
    assert weights["MSFT"]["after"] == pytest.approx(800 / 3300)

    component_contributions = payload["charts"]["component_risk_contributions"]
    assert {point["ticker"] for point in component_contributions} == {"AAPL", "MSFT", "BND"}
    assert payload["charts"]["concentration"]["after"]["largest_position_ticker"] == "AAPL"


def test_simulate_trade_route_rejects_invalid_trade_payload(client, auth_headers):
    portfolio = _create_portfolio(client, auth_headers)
    covariance = {
        "AAPL": {"AAPL": 0.04, "MSFT": 0.01, "BND": 0.0},
        "MSFT": {"AAPL": 0.01, "MSFT": 0.09, "BND": 0.0},
        "BND": {"AAPL": 0.0, "MSFT": 0.0, "BND": 0.01},
    }

    response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/simulate-trade",
        headers=auth_headers,
        json={
            "trades": [
                {"ticker": "AAPL", "side": "buy", "quantity": 1, "notional": 100}
            ],
            "covariance": covariance,
        },
    )

    assert response.status_code == 422



def test_requested_unversioned_routes_are_available(client, auth_headers):
    create_response = client.post(
        "/portfolios",
        headers=auth_headers,
        json={
            "name": "Unversioned Portfolio",
            "positions": [
                {"symbol": "AAPL", "quantity": 10, "price": 100},
                {"symbol": "BND", "quantity": 20, "price": 50},
            ],
        },
    )
    assert create_response.status_code == 201
    portfolio = create_response.json()

    analyze_response = client.post(f"/portfolios/{portfolio['id']}/analyze", headers=auth_headers, json={})
    assert analyze_response.status_code == 200
    assert analyze_response.json()["charts"]["risk"] is None

    simulate_response = client.post(
        f"/portfolios/{portfolio['id']}/simulate-trade",
        headers=auth_headers,
        json={
            "trades": [{"ticker": "AAPL", "side": "buy", "notional": 100}],
            "covariance": {
                "AAPL": {"AAPL": 0.04, "BND": 0.0},
                "BND": {"AAPL": 0.0, "BND": 0.01},
            },
        },
    )
    assert simulate_response.status_code == 200
    assert simulate_response.json()["charts"]["weights"][0]["ticker"] == "AAPL"


def test_relativistic_black_scholes_route_prices_portfolio_holding(client, auth_headers):
    portfolio = _create_portfolio(client, auth_headers)

    expiry_date = (date.today() + timedelta(days=365)).isoformat()
    response = client.get(
        f"/api/v1/portfolios/{portfolio['id']}/relativistic-bs?symbol=AAPL&n_strikes=5&expiry_date={expiry_date}&use_market_chain=false",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == portfolio["id"]
    assert payload["symbol"] == "AAPL"
    assert payload["spot"] == pytest.approx(100)
    assert payload["parameters"]["expiry_date"] == expiry_date
    assert payload["parameters"]["tau"] == pytest.approx(365 / 365.25)
    assert payload["chain_source"] == "generated"
    assert len(payload["rows"]) == len(payload["option_chain"])
    assert payload["baseline_volatility"]["selected_sigma"] == pytest.approx(0.15)
    assert payload["baseline_volatility"]["recommended_sigma"] == pytest.approx(0.15)
    assert payload["cumulative_volume"]
    assert payload["gamma_exposure"]
    assert payload["volatility_smile"] == []
    assert payload["iv_surface"] == []
    assert payload["option_chain"][0]["call"]["bs_price"] > 0
    assert payload["option_chain"][0]["put"]["bs_price"] > 0
    assert all((row["strike"] * 2) == pytest.approx(round(row["strike"] * 2)) for row in payload["option_chain"])
    assert {item["label"] for item in payload["summary"]} >= {
        "Backend Spot",
        "ATM Black-Scholes",
        "ATM Relativistic",
    }


def test_relativistic_black_scholes_route_rejects_missing_symbol(client, auth_headers):
    portfolio = _create_portfolio(client, auth_headers)

    response = client.get(
        f"/portfolios/{portfolio['id']}/relativistic-bs?symbol=TSLA",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "TSLA" in response.json()["detail"]

def test_relativistic_black_scholes_route_rejects_past_expiry(client, auth_headers):
    portfolio = _create_portfolio(client, auth_headers)
    expiry_date = (date.today() - timedelta(days=1)).isoformat()

    response = client.get(
        f"/portfolios/{portfolio['id']}/relativistic-bs?symbol=AAPL&expiry_date={expiry_date}",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "expiry_date" in response.json()["detail"]
