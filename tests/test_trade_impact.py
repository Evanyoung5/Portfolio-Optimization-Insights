import numpy as np
import pytest

from app.quant.trade_impact import analyze_trade_impact, simulate_trade_impact


def _four_asset_covariance():
    variances = {
        "AAA": 0.04,
        "BBB": 0.09,
        "CCC": 0.0625,
        "DDD": 0.01,
    }
    return {
        row: {column: variances[row] if row == column else 0.0 for column in variances}
        for row in variances
    }


def _four_asset_holdings():
    return [
        {"ticker": "AAA", "quantity": 10, "price": 100},
        {"ticker": "BBB", "quantity": 20, "price": 50},
        {"ticker": "CCC", "quantity": 5, "price": 200},
        {"ticker": "DDD", "quantity": 100, "price": 10},
    ]


def test_analyze_trade_impact_four_asset_example():
    trades = [
        {"ticker": "AAA", "side": "buy", "notional": 1_000},
        {"ticker": "BBB", "side": "sell", "quantity": 5},
        {"ticker": "DDD", "side": "buy", "quantity": 50},
    ]

    result = analyze_trade_impact(
        current_holdings=_four_asset_holdings(),
        proposed_trades=trades,
        covariance_matrix=_four_asset_covariance(),
    )

    assert result["tickers"] == ["AAA", "BBB", "CCC", "DDD"]
    assert result["before_weights"] == pytest.approx(
        {"AAA": 0.25, "BBB": 0.25, "CCC": 0.25, "DDD": 0.25}
    )
    assert result["after_weights"] == pytest.approx(
        {
            "AAA": 2_000 / 5_250,
            "BBB": 750 / 5_250,
            "CCC": 1_000 / 5_250,
            "DDD": 1_500 / 5_250,
        }
    )

    before_weights = np.array([0.25, 0.25, 0.25, 0.25])
    after_weights = np.array([2_000 / 5_250, 750 / 5_250, 1_000 / 5_250, 1_500 / 5_250])
    diagonal_covariance = np.diag([0.04, 0.09, 0.0625, 0.01])
    expected_before_volatility = float(np.sqrt(before_weights @ diagonal_covariance @ before_weights))
    expected_after_volatility = float(np.sqrt(after_weights @ diagonal_covariance @ after_weights))

    assert result["before_volatility"] == pytest.approx(expected_before_volatility)
    assert result["after_volatility"] == pytest.approx(expected_after_volatility)
    assert result["volatility_delta"] == pytest.approx(
        expected_after_volatility - expected_before_volatility
    )

    before_components = result["component_risk_contributions"]["before"]
    after_components = result["component_risk_contributions"]["after"]
    assert sum(before_components.values()) == pytest.approx(result["before_volatility"])
    assert sum(after_components.values()) == pytest.approx(result["after_volatility"])

    expected_after_marginal = diagonal_covariance @ after_weights / expected_after_volatility
    assert result["marginal_risk_contributions"]["after"] == pytest.approx(
        {
            "AAA": expected_after_marginal[0],
            "BBB": expected_after_marginal[1],
            "CCC": expected_after_marginal[2],
            "DDD": expected_after_marginal[3],
        }
    )

    before_concentration = result["concentration_metrics"]["before"]
    after_concentration = result["concentration_metrics"]["after"]
    assert before_concentration["hhi"] == pytest.approx(0.25)
    assert before_concentration["effective_number_of_assets"] == pytest.approx(4.0)
    assert after_concentration["largest_position_ticker"] == "AAA"
    assert after_concentration["max_weight"] == pytest.approx(2_000 / 5_250)
    assert after_concentration["hhi"] == pytest.approx(float(after_weights @ after_weights))


def test_simulate_trade_impact_alias_matches_main_function():
    trades = [{"ticker": "AAA", "side": "buy", "notional": 500}]

    direct = analyze_trade_impact(_four_asset_holdings(), trades, _four_asset_covariance())
    alias = simulate_trade_impact(_four_asset_holdings(), trades, _four_asset_covariance())

    assert alias["after_weights"] == pytest.approx(direct["after_weights"])
    assert alias["after_volatility"] == pytest.approx(direct["after_volatility"])


def test_trade_impact_accepts_numpy_covariance_with_tickers():
    trades = [{"ticker": "CCC", "side": "sell", "notional": 250}]
    covariance = np.diag([0.04, 0.09, 0.0625, 0.01])

    result = analyze_trade_impact(
        _four_asset_holdings(),
        trades,
        covariance,
        tickers=["AAA", "BBB", "CCC", "DDD"],
    )

    assert result["after_weights"]["CCC"] == pytest.approx(750 / 3_750)
    assert result["concentration_metrics"]["after"]["long_position_count"] == 4


def test_trade_impact_rejects_oversized_sell():
    with pytest.raises(ValueError, match="sell more BBB quantity"):
        analyze_trade_impact(
            current_holdings=_four_asset_holdings(),
            proposed_trades=[{"ticker": "BBB", "side": "sell", "quantity": 25}],
            covariance_matrix=_four_asset_covariance(),
        )
