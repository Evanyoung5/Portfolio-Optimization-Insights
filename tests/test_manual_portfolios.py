import pytest


def _manual_lot_payload():
    return {
        "name": "Manual Cost Basis",
        "cash": 100,
        "lots": [
            {
                "ticker": "AAPL",
                "quantity": 10,
                "purchase_price": 100,
                "current_price": 130,
                "fees": 2,
                "purchased_at": "2024-01-15T00:00:00Z",
                "asset_class": "equity",
            },
            {
                "ticker": "AAPL",
                "quantity": 5,
                "purchase_price": 120,
                "current_price": 130,
                "fees": 1,
                "purchased_at": "2024-03-15T00:00:00Z",
                "asset_class": "equity",
            },
            {
                "ticker": "BND",
                "quantity": 20,
                "purchase_price": 50,
                "current_price": 48,
                "asset_class": "bond",
            },
        ],
    }


def test_create_portfolio_with_manual_lots_rolls_up_cost_basis(client, auth_headers):
    create_response = client.post("/api/v1/portfolios", headers=auth_headers, json=_manual_lot_payload())

    assert create_response.status_code == 201
    created = create_response.json()
    positions = {position["symbol"]: position for position in created["positions"]}
    assert positions["AAPL"]["quantity"] == 15
    assert positions["AAPL"]["price"] == pytest.approx(130)
    assert positions["BND"]["market_value"] == pytest.approx(960)

    state_response = client.get(f"/api/v1/portfolios/{created['id']}", headers=auth_headers)

    assert state_response.status_code == 200
    state = state_response.json()
    assert state["totals"]["market_value"] == pytest.approx(2910)
    assert state["totals"]["cost_basis"] == pytest.approx(2603)
    assert state["totals"]["unrealized_gain_loss"] == pytest.approx(307)

    cost_positions = {position["ticker"]: position for position in state["positions"]}
    assert cost_positions["AAPL"]["quantity"] == pytest.approx(15)
    assert cost_positions["AAPL"]["cost_basis"] == pytest.approx(1603)
    assert cost_positions["AAPL"]["average_cost"] == pytest.approx(1603 / 15)
    assert cost_positions["AAPL"]["lots_count"] == 2
    assert cost_positions["BND"]["unrealized_gain_loss"] == pytest.approx(-40)

    charts = state["charts"]
    allocation = {point["label"]: point["value"] for point in charts["allocation_by_ticker"]}
    assert allocation["AAPL"] == pytest.approx(1950 / 2910)
    assert allocation["BND"] == pytest.approx(960 / 2910)
    assert len(state["lots"]) == 3
    rollup_jobs = [job for job in state["background_jobs"] if job["job_type"] == "manual_lot_rollup"]
    assert rollup_jobs[-1]["status"] == "completed"


def test_add_manual_lot_to_existing_portfolio(client, auth_headers):
    created = client.post("/api/v1/portfolios", headers=auth_headers, json={"name": "Manual Add"}).json()

    response = client.post(
        f"/api/v1/portfolios/{created['id']}/lots",
        headers=auth_headers,
        json={
            "lots": [
                {
                    "symbol": "msft",
                    "quantity": 3,
                    "purchase_price": 200,
                    "current_price": 250,
                    "fees": 1.5,
                    "asset_class": "equity",
                }
            ]
        },
    )

    assert response.status_code == 201
    state = response.json()
    assert state["positions"][0]["ticker"] == "MSFT"
    assert state["positions"][0]["market_value"] == pytest.approx(750)
    assert state["positions"][0]["cost_basis"] == pytest.approx(601.5)
    assert state["positions"][0]["unrealized_gain_loss"] == pytest.approx(148.5)
    assert state["charts"]["cost_basis_by_ticker"][0]["value"] == pytest.approx(601.5)


def test_manual_lot_validation_rejects_impossible_remaining_quantity(client, auth_headers):
    created = client.post("/api/v1/portfolios", headers=auth_headers, json={"name": "Invalid Lot"}).json()

    response = client.post(
        f"/api/v1/portfolios/{created['id']}/lots",
        headers=auth_headers,
        json={
            "lots": [
                {
                    "ticker": "AAPL",
                    "quantity": 1,
                    "remaining_quantity": 2,
                    "purchase_price": 100,
                }
            ]
        },
    )

    assert response.status_code == 422


def test_manual_lots_feed_existing_analysis_endpoint(client, auth_headers):
    created = client.post("/api/v1/portfolios", headers=auth_headers, json=_manual_lot_payload()).json()

    response = client.get(f"/api/v1/portfolios/{created['id']}/analysis", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["position_count"] == 2
    assert payload["total_market_value"] == pytest.approx(2910)
    weights = {item["symbol"]: item["weight"] for item in payload["weights"]}
    assert weights["AAPL"] == pytest.approx(1950 / 3010)
    assert weights["BND"] == pytest.approx(960 / 3010)


def test_unversioned_manual_routes_are_available(client, auth_headers):
    created = client.post("/portfolios", headers=auth_headers, json={"name": "Frontend Manual"}).json()

    add_response = client.post(
        f"/portfolios/{created['id']}/lots",
        headers=auth_headers,
        json={"lots": [{"ticker": "AAPL", "quantity": 1, "purchase_price": 100}]},
    )
    assert add_response.status_code == 201

    get_response = client.get(f"/portfolios/{created['id']}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["positions"][0]["ticker"] == "AAPL"


def test_manual_accounting_tracks_cash_trades_settings_and_fifo_sales(client, auth_headers):
    created = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={"name": "Manual Accounting", "cash": 10_000},
    ).json()

    settings_response = client.patch(
        f"/api/v1/portfolios/{created['id']}/settings",
        headers=auth_headers,
        json={
            "risk_free_rate": 0.045,
            "benchmark_symbols": ["spy", "QQQ", "SPY"],
            "cash_target_pct": 0.05,
        },
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["benchmark_symbols"] == ["SPY", "QQQ"]

    buy_one = client.post(
        f"/api/v1/portfolios/{created['id']}/trades",
        headers=auth_headers,
        json={
            "ticker": "AAPL",
            "side": "buy",
            "quantity": 10,
            "price": 100,
            "fees": 1,
            "occurred_at": "2024-01-01T00:00:00Z",
            "asset_class": "equity",
        },
    )
    assert buy_one.status_code == 201

    buy_two = client.post(
        f"/api/v1/portfolios/{created['id']}/trades",
        headers=auth_headers,
        json={
            "ticker": "AAPL",
            "side": "buy",
            "quantity": 5,
            "price": 120,
            "fees": 1,
            "occurred_at": "2024-02-01T00:00:00Z",
            "asset_class": "equity",
        },
    )
    assert buy_two.status_code == 201

    sell = client.post(
        f"/api/v1/portfolios/{created['id']}/trades",
        headers=auth_headers,
        json={
            "ticker": "AAPL",
            "side": "sell",
            "quantity": 8,
            "price": 150,
            "fees": 2,
            "occurred_at": "2024-03-01T00:00:00Z",
        },
    )

    assert sell.status_code == 201
    state = sell.json()
    assert state["totals"]["cash"] == pytest.approx(9596)
    assert state["performance"]["net_contributions"] == pytest.approx(10_000)
    assert state["performance"]["risk_free_rate"] == pytest.approx(0.045)
    assert state["performance"]["benchmark_symbols"] == ["SPY", "QQQ"]

    position = state["positions"][0]
    assert position["ticker"] == "AAPL"
    assert position["quantity"] == pytest.approx(7)
    assert position["market_value"] == pytest.approx(1050)

    lots_by_date = sorted(state["lots"], key=lambda item: item["purchased_at"])
    assert lots_by_date[0]["remaining_quantity"] == pytest.approx(2)
    assert lots_by_date[1]["remaining_quantity"] == pytest.approx(5)

    trade_history = state["trade_history"]
    assert len(trade_history) == 3
    assert trade_history[-1]["realized_gain_loss"] == pytest.approx(397.2)
    assert trade_history[-1]["cash_delta"] == pytest.approx(1198)

    ledger = client.get(
        f"/api/v1/portfolios/{created['id']}/cash-transactions",
        headers=auth_headers,
    ).json()
    assert ledger["current_cash"] == pytest.approx(9596)
    assert ledger["net_contributions"] == pytest.approx(10_000)
    assert ledger["transactions"][0]["transaction_type"] == "deposit"


def test_manual_trade_rejects_overselling_without_changing_lots(client, auth_headers):
    created = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Oversell Guard",
            "lots": [{"ticker": "MSFT", "quantity": 1, "purchase_price": 200}],
        },
    ).json()

    response = client.post(
        f"/api/v1/portfolios/{created['id']}/trades",
        headers=auth_headers,
        json={"ticker": "MSFT", "side": "sell", "quantity": 2, "price": 210},
    )

    assert response.status_code == 400
    state = client.get(f"/api/v1/portfolios/{created['id']}", headers=auth_headers).json()
    assert state["positions"][0]["quantity"] == pytest.approx(1)
    assert state["lots"][0]["remaining_quantity"] == pytest.approx(1)
