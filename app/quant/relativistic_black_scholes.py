"""Relativistic Black-Scholes pricing utilities.

Implements the 1 / c_m^2 approximation from Maciej Trzetrzelewski,
"Relativistic Black-Scholes model" (arXiv:1307.5122v3), especially Eq. (18)-(20).
This module is for research and education, not investment advice.
"""

from __future__ import annotations

from math import erf, exp, isfinite, log, pi, sqrt
from typing import Iterable, Literal

import numpy as np

OptionType = Literal["call", "put"]


def d1_d2(spot: float, strike: float, tau: float, rate: float, sigma: float) -> tuple[float, float, float]:
    """Return the paper's x, d1 and d2 parameters."""
    _validate_inputs(spot, strike, tau, rate, sigma)
    x = log(spot / strike) + (rate - 0.5 * sigma * sigma) * tau
    denom = sigma * sqrt(tau)
    d2 = x / denom
    d1 = (sigma * sigma * tau + x) / denom
    return x, d1, d2


def black_scholes_price(
    spot: float,
    strike: float,
    tau: float,
    rate: float,
    sigma: float,
    option_type: OptionType = "call",
) -> float:
    """European Black-Scholes price with no dividends."""
    _validate_inputs(spot, strike, tau, rate, sigma)
    _, d1, d2 = d1_d2(spot, strike, tau, rate, sigma)
    discounted_strike = strike * exp(-rate * tau)
    if option_type == "call":
        return float(spot * _norm_cdf(d1) - discounted_strike * _norm_cdf(d2))
    if option_type == "put":
        return float(discounted_strike * _norm_cdf(-d2) - spot * _norm_cdf(-d1))
    raise ValueError("option_type must be 'call' or 'put'.")


def paper_m(z: float | np.ndarray) -> float | np.ndarray:
    """M(z) = N(z) z^2 (z^2 + 2), as defined after Eq. (18)."""
    return _norm_cdf(z) * z * z * (z * z + 2.0)


def relativistic_call_correction_v(
    spot: float,
    strike: float,
    tau: float,
    rate: float,
    sigma: float,
) -> float:
    """The v term in Eq. (18), so call ~= Black-Scholes call + v / c_m^2."""
    _validate_inputs(spot, strike, tau, rate, sigma)
    _, d1, d2 = d1_d2(spot, strike, tau, rate, sigma)
    discounted_strike = strike * exp(-rate * tau)
    first = -(sigma * sigma) / (8.0 * tau)
    first *= spot * paper_m(d1) - discounted_strike * paper_m(d2)
    second = -spot * sigma * sigma / (8.0 * sqrt(2.0 * pi * tau))
    second *= exp(-0.5 * d1 * d1) * (
        1.0 + 1.5 * d1 * d1 + 1.5 * d2 * d2 - 0.5 * sigma * sigma * tau
    )
    return float(first + second)


def relativistic_bs_price_approx(
    spot: float,
    strike: float,
    tau: float,
    rate: float,
    sigma: float,
    c_m: float,
    option_type: OptionType = "call",
    *,
    floor_at_intrinsic: bool = True,
) -> float:
    """Return the 1 / c_m^2 corrected European option price."""
    _validate_inputs(spot, strike, tau, rate, sigma, c_m)
    bs_call = black_scholes_price(spot, strike, tau, rate, sigma, "call")
    call = bs_call + relativistic_call_correction_v(spot, strike, tau, rate, sigma) / (c_m * c_m)
    discounted_strike = strike * exp(-rate * tau)

    if option_type == "call":
        price = call
        lower_bound = max(0.0, spot - discounted_strike)
        upper_bound = spot
    elif option_type == "put":
        price = call - spot + discounted_strike
        lower_bound = max(0.0, discounted_strike - spot)
        upper_bound = discounted_strike
    else:
        raise ValueError("option_type must be 'call' or 'put'.")

    if floor_at_intrinsic:
        price = min(max(price, lower_bound), upper_bound)
    return float(price)


def vbar_for_implied_vol_shift(
    spot: float,
    strike: float,
    tau: float,
    rate: float,
    sigma: float,
) -> float:
    """The v-bar term in Eq. (19)."""
    _validate_inputs(spot, strike, tau, rate, sigma)
    x, d1, d2 = d1_d2(spot, strike, tau, rate, sigma)
    denom = sigma * sqrt(2.0 * pi * tau)
    term1 = spot * (sigma * sigma * tau - x) * sigma * exp(-0.5 * d1 * d1)
    term2 = strike * x * exp(-rate * tau - 0.5 * d2 * d2)
    return float((term1 + term2) / denom)


def paper_implied_vol_approx(
    spot: float,
    strike: float,
    tau: float,
    rate: float,
    sigma: float,
    c_m: float,
) -> float | None:
    """Paper's first-order implied-vol approximation, Eq. (20)."""
    _validate_inputs(spot, strike, tau, rate, sigma, c_m)
    v = relativistic_call_correction_v(spot, strike, tau, rate, sigma)
    vbar = vbar_for_implied_vol_shift(spot, strike, tau, rate, sigma)
    if abs(vbar) < 1e-12:
        return None
    value = sigma * (1.0 + v / (c_m * c_m * vbar))
    return float(value) if isfinite(value) else None


def black_scholes_implied_vol(
    market_price: float,
    spot: float,
    strike: float,
    tau: float,
    rate: float,
    option_type: OptionType = "call",
    *,
    low: float = 1e-6,
    high: float = 5.0,
) -> float | None:
    """Invert Black-Scholes using bisection to avoid adding SciPy as a dependency."""
    _validate_inputs(spot, strike, tau, rate, 0.2)
    if market_price <= 0:
        return 0.0

    def objective(volatility: float) -> float:
        return black_scholes_price(spot, strike, tau, rate, volatility, option_type) - market_price

    f_low = objective(low)
    f_high = objective(high)
    if f_low == 0:
        return low
    if f_high == 0:
        return high
    if f_low * f_high > 0:
        return None

    lo = low
    hi = high
    for _ in range(120):
        mid = (lo + hi) / 2.0
        f_mid = objective(mid)
        if abs(f_mid) < 1e-10 or (hi - lo) < 1e-10:
            return float(mid)
        if f_low * f_mid <= 0:
            hi = mid
            f_high = f_mid
        else:
            lo = mid
            f_low = f_mid
    return float((lo + hi) / 2.0)


def make_surface(
    spot: float,
    strikes: Iterable[float],
    tau: float,
    rate: float,
    sigma: float,
    c_m: float,
    option_type: OptionType = "call",
) -> list[dict[str, float | None]]:
    """Return strike-by-strike BS, relativistic, correction, and IV diagnostics."""
    rows: list[dict[str, float | None]] = []
    for strike in strikes:
        strike_value = float(strike)
        bs_price = black_scholes_price(spot, strike_value, tau, rate, sigma, option_type)
        rel_unclipped = relativistic_bs_price_approx(
            spot,
            strike_value,
            tau,
            rate,
            sigma,
            c_m,
            option_type,
            floor_at_intrinsic=False,
        )
        rel_price = relativistic_bs_price_approx(
            spot,
            strike_value,
            tau,
            rate,
            sigma,
            c_m,
            option_type,
            floor_at_intrinsic=True,
        )
        rows.append(
            {
                "strike": strike_value,
                "bs_price": bs_price,
                "relativistic_price": rel_price,
                "relativistic_price_unclipped": rel_unclipped,
                "price_correction": rel_unclipped - bs_price,
                "paper_iv_approx": paper_implied_vol_approx(
                    spot, strike_value, tau, rate, sigma, c_m
                ),
                "bs_implied_vol_from_rel_price": black_scholes_implied_vol(
                    rel_price, spot, strike_value, tau, rate, option_type
                ),
            }
        )
    return rows


def make_option_chain_surface(
    spot: float,
    strikes: Iterable[float],
    tau: float,
    rate: float,
    sigma: float,
    c_m: float,
) -> list[dict[str, object]]:
    """Return one row per strike with both call and put model diagnostics."""
    rows: list[dict[str, object]] = []
    for strike in strikes:
        strike_value = float(strike)
        rows.append(
            {
                "strike": strike_value,
                "call": _option_side_surface(spot, strike_value, tau, rate, sigma, c_m, "call"),
                "put": _option_side_surface(spot, strike_value, tau, rate, sigma, c_m, "put"),
            }
        )
    return rows


def _option_side_surface(
    spot: float,
    strike: float,
    tau: float,
    rate: float,
    sigma: float,
    c_m: float,
    option_type: OptionType,
) -> dict[str, float | None]:
    bs_price = black_scholes_price(spot, strike, tau, rate, sigma, option_type)
    rel_unclipped = relativistic_bs_price_approx(
        spot,
        strike,
        tau,
        rate,
        sigma,
        c_m,
        option_type,
        floor_at_intrinsic=False,
    )
    rel_price = relativistic_bs_price_approx(
        spot,
        strike,
        tau,
        rate,
        sigma,
        c_m,
        option_type,
        floor_at_intrinsic=True,
    )
    return {
        "bs_price": bs_price,
        "relativistic_price": rel_price,
        "relativistic_price_unclipped": rel_unclipped,
        "price_correction": rel_unclipped - bs_price,
        "paper_iv_approx": paper_implied_vol_approx(spot, strike, tau, rate, sigma, c_m),
        "bs_implied_vol_from_rel_price": black_scholes_implied_vol(
            rel_price, spot, strike, tau, rate, option_type
        ),
    }


def _validate_inputs(
    spot: float,
    strike: float,
    tau: float,
    rate: float,
    sigma: float,
    c_m: float | None = None,
) -> None:
    if spot <= 0:
        raise ValueError("spot must be positive.")
    if strike <= 0:
        raise ValueError("strike must be positive.")
    if tau <= 0:
        raise ValueError("tau must be positive, measured in years.")
    if sigma <= 0:
        raise ValueError("sigma must be positive.")
    if c_m is not None and c_m <= 0:
        raise ValueError("c_m must be positive.")


def _norm_cdf(value: float | np.ndarray) -> float | np.ndarray:
    if isinstance(value, np.ndarray):
        return np.vectorize(_norm_cdf_scalar, otypes=[float])(value)
    return _norm_cdf_scalar(float(value))


def _norm_cdf_scalar(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))
