import pytest

from app.db.models import Portfolio, Position
from app.quant.risk_profiles import estimate_portfolio_risk, reweight_portfolio_for_risk, risk_tolerance_profile


def test_risk_profiles_have_complete_allocations_and_increasing_volatility():
    prior_volatility = 0.0
    for score in range(1, 11):
        profile = risk_tolerance_profile(score)
        assert sum(profile["target_allocation"].values()) == pytest.approx(1.0)
        assert profile["target_volatility"] > prior_volatility
        assert profile["volatility_band"]["min_volatility"] <= profile["target_volatility"]
        upper = profile["volatility_band"]["max_volatility"]
        assert upper is None or profile["target_volatility"] <= upper
        assert profile["volatility_band"]["display_range"]
        assert profile["volatility_band"]["narrative"]
        prior_volatility = profile["target_volatility"]


def test_risk_reweighting_builds_trade_preview_without_mutating_portfolio():
    portfolio = Portfolio(
        id="portfolio-risk",
        name="Risk",
        base_currency="USD",
        cash=1000,
        positions=[
            Position(symbol="AAPL", quantity=10, price=200, asset_class="equity"),
            Position(symbol="AGG", quantity=20, price=100, asset_class="bond"),
        ],
    )

    result = reweight_portfolio_for_risk(
        portfolio,
        risk_score=3,
        bond_symbols=["SHY"],
        quote_prices={"SHY": 82},
        max_position_weight=0.50,
    )

    assert sum(item["target_weight"] for item in result["allocations"]) == pytest.approx(1.0)
    assert result["profile"]["target_allocation"]["bonds"] == pytest.approx(0.60)
    assert next(item for item in result["allocations"] if item["symbol"] == "SHY")["price"] == 82
    assert portfolio.positions[0].quantity == 10


def test_estimated_portfolio_risk_recognizes_bond_etf_symbols():
    portfolio = Portfolio(
        id="portfolio-bonds",
        name="Bonds",
        base_currency="USD",
        positions=[Position(symbol="TLT", quantity=10, price=90, asset_class="etf")],
    )

    model = estimate_portfolio_risk(portfolio)

    assert model["asset_class_allocation"]["bonds"] == pytest.approx(1.0)
    assert model["model_volatility"] > 0.10
    assert model["estimated_label"]
    assert model["volatility_band"]["display_range"]
