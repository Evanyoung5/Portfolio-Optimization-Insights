import pytest

from app.db.models import Portfolio, Position
from app.quant.heatmap import build_portfolio_heatmap


def test_build_portfolio_heatmap_sizes_by_personal_position_value():
    portfolio = Portfolio(
        id="portfolio-1",
        name="Heatmap Portfolio",
        base_currency="USD",
        user_id="user-1",
        positions=[
            Position(
                symbol="AAPL",
                quantity=2,
                price=100,
                asset_class="equity",
                cost_basis=200,
                average_cost=100,
            ),
            Position(
                symbol="BND",
                quantity=10,
                price=50,
                asset_class="bond",
                cost_basis=500,
                average_cost=50,
            ),
        ],
    )

    heatmap = build_portfolio_heatmap(
        portfolio,
        group_by="sector",
        market_data=[
            {
                "ticker": "AAPL",
                "price": 120,
                "previous_close": 100,
                "sector": "Technology",
                "industry": "Consumer Electronics",
            },
            {
                "ticker": "BND",
                "price": 45,
                "previous_close": 50,
                "sector": "Fixed Income",
                "industry": "Bond Fund",
            },
        ],
    )

    assert heatmap["total_market_value"] == pytest.approx(690)
    assert heatmap["group_by"] == "sector"
    assert heatmap["size_metric"] == "market_value"
    assert heatmap["color_metric"] == "daily_return_pct"

    holdings = {holding["ticker"]: holding for holding in heatmap["holdings"]}
    assert holdings["AAPL"]["market_value"] == pytest.approx(240)
    assert holdings["AAPL"]["portfolio_weight_pct"] == pytest.approx(240 / 690 * 100)
    assert holdings["AAPL"]["daily_return_pct"] == pytest.approx(20)
    assert holdings["AAPL"]["unrealized_return_pct"] == pytest.approx(20)
    assert holdings["BND"]["daily_return_pct"] == pytest.approx(-10)

    root = heatmap["nodes"][0]
    assert root["label"] == "Portfolio"
    assert root["daily_return_pct"] == pytest.approx(((240 * 20) + (450 * -10)) / 690)
    assert "AAPL" in heatmap["plotly"]["labels"]
    assert "position:AAPL" in heatmap["plotly"]["ids"]
    assert heatmap["plotly"]["parents"][1] == "portfolio"
    assert heatmap["plotly"]["customdata"][0][1] == pytest.approx(690)
    assert heatmap["plotly"]["customdata"][0][3] == pytest.approx(100)
    assert heatmap["plotly"]["customdata"][0][5] == pytest.approx(700)


def test_heatmap_get_route_returns_frontend_treemap_payload(client, auth_headers):
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={
            "name": "Route Heatmap",
            "positions": [
                {"symbol": "AAPL", "quantity": 2, "price": 100, "asset_class": "equity"},
                {"symbol": "BND", "quantity": 10, "price": 50, "asset_class": "bond"},
            ],
        },
    ).json()

    response = client.get(f"/portfolios/{created['id']}/heatmap", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == created["id"]
    assert payload["total_market_value"] == pytest.approx(700)
    assert [holding["ticker"] for holding in payload["holdings"]] == ["BND", "AAPL"]
    assert payload["plotly"]["type"] == "treemap"
    assert payload["plotly"]["branchvalues"] == "total"
    assert payload["plotly"]["ids"][0] == "portfolio"


def test_heatmap_post_route_accepts_market_data_and_grouping(client, auth_headers):
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={
            "name": "Market Heatmap",
            "positions": [
                {"symbol": "AAPL", "quantity": 2, "price": 100, "asset_class": "equity"},
                {"symbol": "BND", "quantity": 10, "price": 50, "asset_class": "bond"},
            ],
        },
    ).json()

    response = client.post(
        f"/portfolios/{created['id']}/heatmap",
        headers=auth_headers,
        json={
            "group_by": "sector",
            "market_data": [
                {"ticker": "AAPL", "price": 120, "previous_close": 100, "sector": "Technology"},
                {"ticker": "BND", "price": 45, "previous_close": 50, "sector": "Fixed Income"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["group_by"] == "sector"
    assert payload["total_market_value"] == pytest.approx(690)
    groups = {node["label"]: node for node in payload["nodes"] if node["level"] == "group"}
    assert set(groups) == {"Technology", "Fixed Income"}
    holdings = {holding["ticker"]: holding for holding in payload["holdings"]}
    assert holdings["AAPL"]["price"] == pytest.approx(120)
    assert holdings["BND"]["daily_return_pct"] == pytest.approx(-10)
