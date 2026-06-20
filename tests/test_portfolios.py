from pathlib import Path


def test_create_portfolio(client, auth_headers):
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Core Portfolio",
            "cash": 1_000,
            "positions": [
                {"symbol": "aapl", "quantity": 2, "price": 200, "asset_class": "equity"}
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"]
    assert payload["positions"][0]["symbol"] == "AAPL"
    assert payload["positions"][0]["market_value"] == 400


def test_upload_csv_and_analyze(client, auth_headers):
    portfolio = client.post("/api/v1/portfolios", headers=auth_headers, json={"name": "CSV Portfolio"}).json()

    response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/upload-csv",
        headers=auth_headers,
        files={
            "file": (
                "positions.csv",
                "symbol,quantity,price,asset_class\nMSFT,3,410,equity\nBND,4,70,bond\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["imported_positions"] == 2
    assert response.json()["detected_format"] == "generic"

    analysis = client.get(f"/api/v1/portfolios/{portfolio['id']}/analysis", headers=auth_headers)

    assert analysis.status_code == 200
    payload = analysis.json()
    assert payload["total_market_value"] == 1510
    assert payload["position_count"] == 2
    assert payload["asset_class_exposure"]["equity"] > payload["asset_class_exposure"]["bond"]


def test_upload_fidelity_positions_export(client, auth_headers):
    portfolio = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Fidelity Import",
            "lots": [{"ticker": "OLD", "quantity": 3, "purchase_price": 10}],
        },
    ).json()
    fixture = Path(__file__).parent / "fixtures" / "broker_csv" / "fidelity_positions.csv"

    response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/upload-csv",
        headers=auth_headers,
        files={"file": (fixture.name, fixture.read_bytes(), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_format"] == "fidelity"
    assert payload["imported_positions"] == 2
    state = client.get(f"/api/v1/portfolios/{portfolio['id']}", headers=auth_headers).json()
    apple = next(position for position in state["positions"] if position["ticker"] == "AAPL")
    assert apple["cost_basis"] == 1500
    assert apple["current_price"] == 210.25
    assert {lot["ticker"] for lot in state["lots"]} == {"AAPL", "BND"}


def test_optimize_portfolio(client, auth_headers):
    portfolio = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Optimization Portfolio",
            "positions": [
                {"symbol": "AAPL", "quantity": 2, "price": 200, "asset_class": "equity"},
                {"symbol": "BND", "quantity": 4, "price": 70, "asset_class": "bond"},
            ],
        },
    ).json()

    response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/optimize",
        json={"objective": "equal_weight"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["objective"] == "equal_weight"
    assert len(payload["allocations"]) == 2
    assert sum(item["target_weight"] for item in payload["allocations"]) == 1


def test_optimization_objectives_produce_distinct_targets(client, auth_headers):
    portfolio = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Distinct Objectives",
            "positions": [
                {"symbol": "AAPL", "quantity": 2, "price": 200, "asset_class": "equity"},
                {"symbol": "MSFT", "quantity": 2, "price": 180, "asset_class": "equity"},
                {"symbol": "BND", "quantity": 4, "price": 70, "asset_class": "bond"},
            ],
        },
    ).json()

    responses = {}
    for objective in ["equal_weight", "min_volatility", "max_sharpe"]:
        response = client.post(
            f"/api/v1/portfolios/{portfolio['id']}/optimize",
            json={"objective": objective},
            headers=auth_headers,
        )
        assert response.status_code == 200
        responses[objective] = [round(item["target_weight"], 6) for item in response.json()["allocations"]]

    assert responses["equal_weight"] != responses["min_volatility"]
    assert responses["min_volatility"] != responses["max_sharpe"]


def test_simulate_trade_impact(client, auth_headers):
    portfolio = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Simulation Portfolio",
            "cash": 1_000,
            "positions": [
                {"symbol": "AAPL", "quantity": 2, "price": 200, "asset_class": "equity"}
            ],
        },
    ).json()

    response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/simulate-trade-impact",
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "price": 210},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["cash_delta"] < -210
    assert payload["post_trade_equity"] < payload["pre_trade_equity"]
