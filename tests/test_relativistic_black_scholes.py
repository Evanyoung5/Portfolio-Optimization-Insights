import pytest

from datetime import date, timedelta

from app.quant.relativistic_black_scholes import (
    black_scholes_price,
    make_option_chain_surface,
    make_surface,
    relativistic_bs_price_approx,
)
from app.quant.options_suite import (
    build_baseline_volatility_guide,
    build_cumulative_volume_profile,
    build_gamma_exposure_profile,
    build_iv_surface_points,
    build_volatility_smile,
)


def test_black_scholes_call_is_positive():
    price = black_scholes_price(100, 100, 0.5, 0.05, 0.15, "call")

    assert price > 0


def test_relativistic_price_converges_to_black_scholes_for_large_cm():
    bs_price = black_scholes_price(100, 100, 0.5, 0.05, 0.15, "call")
    relativistic_price = relativistic_bs_price_approx(
        100,
        100,
        0.5,
        0.05,
        0.15,
        1_000_000,
        "call",
        floor_at_intrinsic=False,
    )

    assert relativistic_price == pytest.approx(bs_price)


def test_surface_rows_include_price_and_iv_diagnostics():
    rows = make_surface(100, [80, 100, 120], 0.5, 0.05, 0.15, 2.5, "call")

    assert len(rows) == 3
    assert {
        "strike",
        "bs_price",
        "relativistic_price",
        "price_correction",
        "paper_iv_approx",
        "bs_implied_vol_from_rel_price",
    }.issubset(rows[0])

def test_option_chain_surface_includes_call_and_put_sides():
    rows = make_option_chain_surface(100, [95, 100, 105], 0.5, 0.05, 0.15, 2.5)

    assert len(rows) == 3
    assert rows[1]["strike"] == 100
    assert rows[1]["call"]["relativistic_price"] > 0
    assert rows[1]["put"]["relativistic_price"] > 0
    assert rows[1]["call"]["bs_price"] != rows[1]["put"]["bs_price"]



def _sample_chain_rows():
    return [
        {
            "strike": 95.0,
            "call": {"market_iv": 0.31, "volume": 10, "open_interest": 80},
            "put": {"market_iv": 0.34, "volume": 15, "open_interest": 90},
        },
        {
            "strike": 100.0,
            "call": {"market_iv": 0.28, "volume": 30, "open_interest": 120},
            "put": {"market_iv": 0.29, "volume": 25, "open_interest": 110},
        },
        {
            "strike": 105.0,
            "call": {"market_iv": 0.32, "volume": 18, "open_interest": 70},
            "put": {"market_iv": 0.30, "volume": 12, "open_interest": 60},
        },
    ]


def test_options_suite_builds_volatility_smile_volume_and_gamma():
    rows = _sample_chain_rows()

    smile = build_volatility_smile(spot=100, baseline_sigma=0.25, chain_rows=rows)
    volume = build_cumulative_volume_profile(rows)
    gamma = build_gamma_exposure_profile(
        spot=100,
        tau=0.5,
        rate=0.04,
        baseline_sigma=0.25,
        chain_rows=rows,
    )

    assert [point["strike"] for point in smile] == [95.0, 100.0, 105.0]
    assert smile[1]["average_iv"] == pytest.approx(0.285)
    assert volume[-1]["cumulative_call_volume"] == pytest.approx(58)
    assert volume[-1]["cumulative_put_volume"] == pytest.approx(52)
    assert gamma[1]["call_gamma_exposure"] > 0
    assert gamma[1]["put_gamma_exposure"] < 0
    assert gamma[1]["net_gamma_exposure"] == pytest.approx(
        gamma[1]["call_gamma_exposure"] + gamma[1]["put_gamma_exposure"]
    )


def test_options_suite_builds_baseline_volatility_and_iv_surface():
    rows = _sample_chain_rows()
    today = date.today()
    history = [(today - timedelta(days=idx), 100 + idx * 0.2) for idx in range(80, 0, -1)]

    guide = build_baseline_volatility_guide(
        spot=100,
        selected_sigma=0.25,
        chain_rows=rows,
        price_history=history,
    )
    surface = build_iv_surface_points(
        spot=100,
        snapshots=[
            {
                "expiry": today + timedelta(days=30),
                "calls": [{"strike": 95, "implied_volatility": 0.31}, {"strike": 100, "implied_volatility": 0.28}],
                "puts": [{"strike": 95, "implied_volatility": 0.34}, {"strike": 100, "implied_volatility": 0.29}],
            },
            {
                "expiry": today + timedelta(days=90),
                "calls": [{"strike": 95, "implied_volatility": 0.33}, {"strike": 100, "implied_volatility": 0.30}],
                "puts": [{"strike": 95, "implied_volatility": 0.35}, {"strike": 100, "implied_volatility": 0.31}],
            },
        ],
        as_of=today,
    )

    assert guide["recommended_sigma"] == pytest.approx(0.285)
    assert {estimate["source"] for estimate in guide["estimates"]} >= {"option_chain", "historical_prices"}
    assert len(surface) == 4
    assert surface[0]["expiry_date"] == (today + timedelta(days=30)).isoformat()
    assert surface[0]["average_iv"] == pytest.approx((0.31 + 0.34) / 2)


def test_options_suite_omits_provider_iv_sentinels_and_far_surface_strikes():
    today = date.today()
    rows = [
        {"strike": 50.0, "call": {"market_iv": 0.00001}, "put": {"market_iv": 4.5}},
        {"strike": 95.0, "call": {"market_iv": 0.31}, "put": {"market_iv": 0.34}},
        {"strike": 100.0, "call": {"market_iv": float("inf")}, "put": {"market_iv": 0.29}},
        {"strike": 105.0, "call": {"market_iv": 0.32}, "put": {"market_iv": 0.30}},
    ]

    smile = build_volatility_smile(spot=100, baseline_sigma=0.25, chain_rows=rows)
    surface = build_iv_surface_points(
        spot=100,
        snapshots=[
            {
                "expiry": today + timedelta(days=30),
                "calls": [
                    {"strike": 50, "implied_volatility": 0.00001},
                    {"strike": 95, "implied_volatility": 0.31},
                    {"strike": 100, "implied_volatility": float("inf")},
                    {"strike": 105, "implied_volatility": 0.32},
                ],
                "puts": [
                    {"strike": 50, "implied_volatility": 4.5},
                    {"strike": 95, "implied_volatility": 0.34},
                    {"strike": 100, "implied_volatility": 0.29},
                    {"strike": 105, "implied_volatility": 0.30},
                ],
            }
        ],
        as_of=today,
    )

    assert smile[0]["strike"] == 95
    assert smile[1]["call_iv"] is None
    assert smile[1]["average_iv"] == pytest.approx(0.29)
    assert {point["strike"] for point in surface} == {95, 100, 105}
