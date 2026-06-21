import pytest

from app.db.models import MarketQuote
from app.quant.bonds import analyze_bond_strategy, bond_duration, bond_price, recommended_bond_rungs


def test_par_bond_prices_at_face_value_when_coupon_equals_yield():
    price = bond_price(
        face_value=1000,
        coupon_rate=0.05,
        years_to_maturity=10,
        yield_to_maturity=0.05,
        payments_per_year=2,
    )

    assert price == pytest.approx(1000)


def test_longer_bond_has_more_rate_duration():
    short = bond_duration(
        face_value=1000,
        coupon_rate=0.04,
        years_to_maturity=2,
        yield_to_maturity=0.04,
    )
    long = bond_duration(
        face_value=1000,
        coupon_rate=0.04,
        years_to_maturity=20,
        yield_to_maturity=0.04,
    )

    assert long["modified_duration"] > short["modified_duration"]


def test_ladder_analysis_normalizes_weights_and_builds_cash_flows():
    result = analyze_bond_strategy(
        strategy_type="ladder",
        capital=20_000,
        risk_score=5,
        rungs=[
            {
                "label": "Two year",
                "allocation_weight": 2,
                "face_value": 1000,
                "market_price_pct": 99,
                "coupon_rate": 0.04,
                "yield_to_maturity": 0.045,
                "years_to_maturity": 2,
                "payments_per_year": 2,
            },
            {
                "label": "Five year",
                "allocation_weight": 1,
                "face_value": 1000,
                "market_price_pct": 101,
                "coupon_rate": 0.05,
                "yield_to_maturity": 0.047,
                "years_to_maturity": 5,
                "payments_per_year": 2,
            },
        ],
    )

    assert sum(rung["weight"] for rung in result["rungs"]) == pytest.approx(1.0)
    assert result["summary"]["allocated_capital"] == pytest.approx(20_000)
    assert result["summary"]["annual_income"] > 0
    assert result["cash_flow_schedule"][-1]["principal"] > 0


def test_recommended_barbell_changes_with_risk_score():
    conservative = recommended_bond_rungs(2, "barbell")
    aggressive = recommended_bond_rungs(9, "barbell")

    assert conservative[0]["allocation_weight"] > conservative[-1]["allocation_weight"]
    assert aggressive[0]["allocation_weight"] < aggressive[-1]["allocation_weight"]
    assert aggressive[-1]["years_to_maturity"] > conservative[-1]["years_to_maturity"]


def test_recommended_ladder_uses_curve_quotes_for_auto_filled_rungs():
    quotes = {
        "^IRX": MarketQuote(ticker="^IRX", price=4.20, provider="test"),
        "^FVX": MarketQuote(ticker="^FVX", price=38.00, provider="test"),
        "^TNX": MarketQuote(ticker="^TNX", price=43.50, provider="test"),
        "^TYX": MarketQuote(ticker="^TYX", price=47.80, provider="test"),
    }

    ladder = recommended_bond_rungs(5, "ladder", quotes)

    assert ladder[0]["label"] == "1-year Treasury bill"
    assert ladder[0]["coupon_rate"] == pytest.approx(0.0)
    assert ladder[0]["payments_per_year"] == 1
    assert ladder[0]["market_price_pct"] < 100
    assert ladder[2]["ticker"] == "IEI"
    assert ladder[-1]["yield_to_maturity"] > ladder[1]["yield_to_maturity"]
