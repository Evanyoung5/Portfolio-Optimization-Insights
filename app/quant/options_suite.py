"""Option-suite analytics built on option-chain snapshots.

The functions here avoid provider-specific objects so they can be tested with plain
Python dictionaries and reused by FastAPI services without putting quant logic in
route files.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from math import exp, isfinite, log, pi, sqrt
from statistics import median
from typing import Any

import numpy as np

TRADING_DAYS_PER_YEAR = 252.0
CONTRACT_MULTIPLIER = 100.0
MIN_MARKET_IV = 0.02
MAX_MARKET_IV = 3.0
MIN_SURFACE_MONEYNESS = 0.50
MAX_SURFACE_MONEYNESS = 1.50


def historical_volatility_estimates(
    price_history: list[tuple[date, float]],
    *,
    windows: tuple[int, ...] = (20, 60, 120, 252),
) -> list[dict[str, object]]:
    """Return annualized realized-vol estimates from daily close history."""
    cleaned = [(item_date, float(close)) for item_date, close in price_history if close and close > 0]
    cleaned.sort(key=lambda item: item[0])
    if len(cleaned) < 6:
        return []

    closes = np.asarray([close for _, close in cleaned], dtype=float)
    returns = np.diff(np.log(closes))
    estimates: list[dict[str, object]] = []
    for window in windows:
        if returns.size < max(5, min(window, 10)):
            continue
        sample = returns[-min(window, returns.size):]
        volatility = float(np.nanstd(sample, ddof=1) * sqrt(TRADING_DAYS_PER_YEAR))
        if not isfinite(volatility) or volatility <= 0:
            continue
        estimates.append(
            {
                "label": f"{window}D realized vol",
                "value": volatility,
                "source": "historical_prices",
                "detail": f"Annualized standard deviation of the last {min(window, returns.size)} daily log returns.",
            }
        )
    return estimates


def build_baseline_volatility_guide(
    *,
    spot: float,
    selected_sigma: float,
    chain_rows: list[dict[str, Any]],
    price_history: list[tuple[date, float]],
) -> dict[str, object]:
    """Combine realized and market-implied volatility estimates for the UI."""
    estimates = historical_volatility_estimates(price_history)
    market_ivs = _market_ivs(chain_rows)
    if market_ivs:
        estimates.append(
            {
                "label": "Chain median IV",
                "value": float(median(market_ivs)),
                "source": "option_chain",
                "detail": "Median listed implied volatility across calls and puts in the selected chain.",
            }
        )

    atm_ivs = _atm_market_ivs(chain_rows, spot)
    if atm_ivs:
        estimates.insert(
            0,
            {
                "label": "ATM market IV",
                "value": float(sum(atm_ivs) / len(atm_ivs)),
                "source": "option_chain",
                "detail": "Average call/put implied volatility from the strike nearest the current stock price.",
            },
        )

    recommendation = _recommended_volatility(selected_sigma, estimates)
    notes = [
        "Use market IV when the chain is liquid; it reflects what traders are currently paying for optionality.",
        "Use realized volatility when option quotes are sparse, stale, or unusually wide.",
    ]
    if not estimates:
        notes.append("No live volatility reference was available; the model is using the manually entered baseline volatility.")

    return {
        "selected_sigma": selected_sigma,
        "recommended_sigma": recommendation,
        "estimates": estimates,
        "notes": notes,
    }


def build_volatility_smile(
    *,
    spot: float,
    baseline_sigma: float,
    chain_rows: list[dict[str, Any]],
) -> list[dict[str, float | None]]:
    """Return strike-by-strike market IV data for a volatility-smile chart."""
    if spot <= 0:
        return []
    rows: list[dict[str, float | None]] = []
    for row in sorted(chain_rows, key=lambda item: float(item["strike"])):
        strike = float(row["strike"])
        call_iv = _market_iv(_side_float(row, "call", "market_iv"))
        put_iv = _market_iv(_side_float(row, "put", "market_iv"))
        average_iv = _average_present([call_iv, put_iv])
        if average_iv is None and call_iv is None and put_iv is None:
            continue
        rows.append(
            {
                "strike": strike,
                "moneyness": strike / spot,
                "call_iv": call_iv,
                "put_iv": put_iv,
                "average_iv": average_iv,
                "baseline_iv": baseline_sigma,
            }
        )
    return rows


def build_cumulative_volume_profile(chain_rows: list[dict[str, Any]]) -> list[dict[str, float]]:
    """Return call/put volume and open-interest accumulation by strike."""
    rows: list[dict[str, float]] = []
    cumulative_call = 0.0
    cumulative_put = 0.0
    for row in sorted(chain_rows, key=lambda item: float(item["strike"])):
        strike = float(row["strike"])
        call_volume = max(_side_float(row, "call", "volume") or 0.0, 0.0)
        put_volume = max(_side_float(row, "put", "volume") or 0.0, 0.0)
        call_oi = max(_side_float(row, "call", "open_interest") or 0.0, 0.0)
        put_oi = max(_side_float(row, "put", "open_interest") or 0.0, 0.0)
        cumulative_call += call_volume
        cumulative_put += put_volume
        rows.append(
            {
                "strike": strike,
                "call_volume": call_volume,
                "put_volume": put_volume,
                "total_volume": call_volume + put_volume,
                "cumulative_call_volume": cumulative_call,
                "cumulative_put_volume": cumulative_put,
                "call_open_interest": call_oi,
                "put_open_interest": put_oi,
            }
        )
    return rows


def build_gamma_exposure_profile(
    *,
    spot: float,
    tau: float,
    rate: float,
    baseline_sigma: float,
    chain_rows: list[dict[str, Any]],
) -> list[dict[str, float]]:
    """Estimate listed gamma exposure by strike.

    Exposure is scaled to approximate dollars per 1% spot move using open interest.
    Calls are shown as positive exposure and puts as negative exposure for an
    intuitive net profile.
    """
    rows: list[dict[str, float]] = []
    for row in sorted(chain_rows, key=lambda item: float(item["strike"])):
        strike = float(row["strike"])
        call_iv = _valid_vol(_side_float(row, "call", "market_iv"), baseline_sigma)
        put_iv = _valid_vol(_side_float(row, "put", "market_iv"), baseline_sigma)
        call_oi = max(_side_float(row, "call", "open_interest") or 0.0, 0.0)
        put_oi = max(_side_float(row, "put", "open_interest") or 0.0, 0.0)
        call_gex = _gamma_exposure(spot, strike, tau, rate, call_iv, call_oi)
        put_gex = -_gamma_exposure(spot, strike, tau, rate, put_iv, put_oi)
        rows.append(
            {
                "strike": strike,
                "call_gamma_exposure": call_gex,
                "put_gamma_exposure": put_gex,
                "net_gamma_exposure": call_gex + put_gex,
                "gross_gamma_exposure": abs(call_gex) + abs(put_gex),
            }
        )
    return rows


def build_iv_surface_points(
    *,
    spot: float,
    snapshots: list[dict[str, Any]],
    as_of: date | None = None,
    max_points_per_expiry: int = 35,
) -> list[dict[str, float | str | None]]:
    """Return sparse IV-surface points across expiries and strikes."""
    if spot <= 0:
        return []
    valuation_date = as_of or datetime.now(timezone.utc).date()
    points: list[dict[str, float | str | None]] = []
    for snapshot in snapshots:
        expiry = snapshot.get("expiry")
        if not isinstance(expiry, date):
            continue
        tau = max((expiry - valuation_date).days / 365.25, 1.0 / 365.25)
        rows = _snapshot_chain_rows(snapshot)
        rows = [row for row in rows if _surface_row_is_usable(row, spot)]
        rows = _thin_surface_rows(rows, spot, max_points_per_expiry)
        for row in rows:
            strike = float(row["strike"])
            call_iv = _market_iv(_side_float(row, "call", "market_iv"))
            put_iv = _market_iv(_side_float(row, "put", "market_iv"))
            average_iv = _average_present([call_iv, put_iv])
            if average_iv is None:
                continue
            points.append(
                {
                    "expiry_date": expiry.isoformat(),
                    "tau": tau,
                    "strike": strike,
                    "moneyness": strike / spot,
                    "call_iv": call_iv,
                    "put_iv": put_iv,
                    "average_iv": average_iv,
                }
            )
    return points


def _snapshot_chain_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    by_strike: dict[float, dict[str, Any]] = {}
    for side_name in ("call", "put"):
        contracts = snapshot.get(f"{side_name}s", []) or []
        for contract in contracts:
            strike = round(float(contract["strike"]), 2)
            row = by_strike.setdefault(strike, {"strike": strike, "call": {}, "put": {}})
            row[side_name] = {
                "market_iv": contract.get("implied_volatility"),
                "volume": contract.get("volume"),
                "open_interest": contract.get("open_interest"),
            }
    return list(by_strike.values())


def _thin_surface_rows(rows: list[dict[str, Any]], spot: float, limit: int) -> list[dict[str, Any]]:
    if len(rows) <= limit:
        return sorted(rows, key=lambda item: float(item["strike"]))
    ranked = sorted(rows, key=lambda item: abs(float(item["strike"]) / spot - 1.0))[:limit]
    return sorted(ranked, key=lambda item: float(item["strike"]))


def _surface_row_is_usable(row: dict[str, Any], spot: float) -> bool:
    strike = float(row["strike"])
    moneyness = strike / spot
    if not MIN_SURFACE_MONEYNESS <= moneyness <= MAX_SURFACE_MONEYNESS:
        return False
    return any(
        _market_iv(_side_float(row, side, "market_iv")) is not None
        for side in ("call", "put")
    )


def _gamma_exposure(
    spot: float,
    strike: float,
    tau: float,
    rate: float,
    sigma: float,
    open_interest: float,
) -> float:
    if open_interest <= 0 or sigma <= 0 or tau <= 0:
        return 0.0
    d1 = (log(spot / strike) + (rate + 0.5 * sigma * sigma) * tau) / (sigma * sqrt(tau))
    density = exp(-0.5 * d1 * d1) / sqrt(2.0 * pi)
    gamma = density / (spot * sigma * sqrt(tau))
    return float(gamma * open_interest * CONTRACT_MULTIPLIER * spot * spot * 0.01)


def _market_ivs(chain_rows: list[dict[str, Any]]) -> list[float]:
    values: list[float] = []
    for row in chain_rows:
        for side in ("call", "put"):
            value = _market_iv(_side_float(row, side, "market_iv"))
            if value is not None:
                values.append(value)
    return values


def _atm_market_ivs(chain_rows: list[dict[str, Any]], spot: float) -> list[float]:
    candidates = [
        row
        for row in chain_rows
        if _average_present(
            [
                _market_iv(_side_float(row, "call", "market_iv")),
                _market_iv(_side_float(row, "put", "market_iv")),
            ]
        )
        is not None
    ]
    if not candidates:
        return []
    atm = min(candidates, key=lambda row: abs(float(row["strike"]) - spot))
    return [
        value
        for value in (
            _market_iv(_side_float(atm, "call", "market_iv")),
            _market_iv(_side_float(atm, "put", "market_iv")),
        )
        if value is not None
    ]


def _recommended_volatility(selected_sigma: float, estimates: list[dict[str, object]]) -> float:
    for source in ("option_chain", "historical_prices"):
        for estimate in estimates:
            if estimate.get("source") == source:
                value = estimate.get("value")
                if isinstance(value, (int, float)) and value > 0:
                    return float(value)
    return selected_sigma


def _side_float(row: dict[str, Any], side: str, field: str) -> float | None:
    side_payload = row.get(side) or {}
    value = side_payload.get(field)
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(parsed):
        return None
    return parsed


def _average_present(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None and isfinite(value)]
    if not present:
        return None
    return float(sum(present) / len(present))


def _valid_vol(value: float | None, fallback: float) -> float:
    if value is not None and MIN_MARKET_IV <= value <= MAX_MARKET_IV:
        return value
    return fallback


def _market_iv(value: float | None) -> float | None:
    if value is None or not MIN_MARKET_IV <= value <= MAX_MARKET_IV:
        return None
    return value
