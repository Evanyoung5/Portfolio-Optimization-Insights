from __future__ import annotations

from math import sqrt
from typing import Any

from app.db.models import Portfolio, Position
from app.quant.bonds import BOND_ASSET_BY_TICKER


RISK_PROFILES: dict[int, dict[str, Any]] = {
    1: {"label": "Capital preservation", "target_volatility": 0.04, "equity": 0.10, "bonds": 0.70, "cash": 0.20},
    2: {"label": "Very conservative", "target_volatility": 0.06, "equity": 0.20, "bonds": 0.65, "cash": 0.15},
    3: {"label": "Conservative", "target_volatility": 0.08, "equity": 0.30, "bonds": 0.60, "cash": 0.10},
    4: {"label": "Conservative growth", "target_volatility": 0.10, "equity": 0.40, "bonds": 0.50, "cash": 0.10},
    5: {"label": "Balanced", "target_volatility": 0.12, "equity": 0.50, "bonds": 0.45, "cash": 0.05},
    6: {"label": "Balanced growth", "target_volatility": 0.14, "equity": 0.60, "bonds": 0.35, "cash": 0.05},
    7: {"label": "Growth", "target_volatility": 0.17, "equity": 0.70, "bonds": 0.25, "cash": 0.05},
    8: {"label": "High growth", "target_volatility": 0.20, "equity": 0.80, "bonds": 0.15, "cash": 0.05},
    9: {"label": "Aggressive", "target_volatility": 0.24, "equity": 0.90, "bonds": 0.07, "cash": 0.03},
    10: {"label": "Very aggressive", "target_volatility": 0.30, "equity": 0.95, "bonds": 0.03, "cash": 0.02},
}


ASSET_CLASS_MODEL_VOLATILITY = {
    "cash": 0.01,
    "bond": 0.06,
    "fixed_income": 0.06,
    "equity": 0.17,
    "etf": 0.15,
    "commodity": 0.23,
    "crypto": 0.65,
}


def risk_tolerance_profile(score: int) -> dict[str, Any]:
    normalized = _normalize_score(score)
    source = RISK_PROFILES[normalized]
    band = _volatility_band(normalized)
    if normalized <= 2:
        description = "Prioritizes smaller modeled drawdowns and liquidity. Most capital is assigned to bonds and cash, so long-run upside may be lower."
    elif normalized <= 4:
        description = "Accepts limited fluctuations while keeping a substantial fixed-income cushion. Losses can still occur when rates or credit spreads rise."
    elif normalized <= 6:
        description = "Balances growth and stability. Temporary double-digit declines are plausible even when the long-run allocation is diversified."
    elif normalized <= 8:
        description = "Prioritizes growth and accepts larger market swings. The investor should be able to tolerate prolonged declines without selling."
    else:
        description = "Accepts very large fluctuations for maximum modeled growth exposure. Severe drawdowns and multi-year recovery periods are possible."
    return {
        "score": normalized,
        "label": source["label"],
        "description": description,
        "target_volatility": source["target_volatility"],
        "volatility_band": band,
        "target_allocation": {
            "equity": source["equity"],
            "bonds": source["bonds"],
            "cash": source["cash"],
        },
        "volatility_explanation": (
            f"Score {normalized} targets about {_format_volatility(source['target_volatility'])} annualized volatility, "
            f"roughly a {band['display_range']} band. {band['narrative']} "
            "It is a planning estimate of typical variability, not a maximum loss or drawdown limit."
        ),
    }


def estimate_portfolio_risk(portfolio: Portfolio) -> dict[str, Any]:
    total_equity = portfolio.cash + sum(position.market_value for position in portfolio.positions)
    if total_equity <= 0:
        band = _volatility_band(1)
        return {
            "model_volatility": 0.0,
            "estimated_score": 1,
            "estimated_label": RISK_PROFILES[1]["label"],
            "volatility_band": band,
            "asset_class_allocation": {"equity": 0.0, "bonds": 0.0, "cash": 0.0},
        }

    exposures = {"equity": 0.0, "bonds": 0.0, "cash": max(portfolio.cash, 0.0) / total_equity}
    weighted_volatilities: list[float] = []
    if portfolio.cash > 0:
        weighted_volatilities.append((portfolio.cash / total_equity) * ASSET_CLASS_MODEL_VOLATILITY["cash"])
    for position in portfolio.positions:
        bucket = risk_bucket(position)
        weight = max(position.market_value, 0.0) / total_equity
        exposures[bucket] += weight
        weighted_volatilities.append(weight * _position_model_volatility(position))

    correlation = 0.25
    variance = sum(value * value for value in weighted_volatilities)
    for left in range(len(weighted_volatilities)):
        for right in range(left + 1, len(weighted_volatilities)):
            variance += 2 * correlation * weighted_volatilities[left] * weighted_volatilities[right]
    model_volatility = sqrt(max(variance, 0.0))
    estimated_score = min(
        RISK_PROFILES,
        key=lambda score: abs(RISK_PROFILES[score]["target_volatility"] - model_volatility),
    )
    band = _volatility_band(estimated_score)
    return {
        "model_volatility": model_volatility,
        "estimated_score": estimated_score,
        "estimated_label": RISK_PROFILES[estimated_score]["label"],
        "volatility_band": band,
        "asset_class_allocation": exposures,
    }


def reweight_portfolio_for_risk(
    portfolio: Portfolio,
    *,
    risk_score: int,
    bond_symbols: list[str] | None = None,
    quote_prices: dict[str, float] | None = None,
    max_position_weight: float = 0.35,
) -> dict[str, Any]:
    profile = risk_tolerance_profile(risk_score)
    current_model = estimate_portfolio_risk(portfolio)
    total_equity = portfolio.cash + sum(position.market_value for position in portfolio.positions)
    if total_equity <= 0:
        raise ValueError("Portfolio must have positive equity before it can be reweighted.")

    prices = {str(symbol).upper(): float(price) for symbol, price in (quote_prices or {}).items() if price and price > 0}
    requested_bonds = _normalize_symbols(bond_symbols or [])
    existing_by_symbol = {position.symbol: position for position in portfolio.positions}
    candidates: dict[str, list[dict[str, Any]]] = {"equity": [], "bonds": [], "cash": []}
    for position in portfolio.positions:
        candidates[risk_bucket(position)].append(
            {
                "symbol": position.symbol,
                "asset_class": position.asset_class,
                "current_value": position.market_value,
                "price": position.price,
            }
        )

    for symbol in requested_bonds:
        if symbol in existing_by_symbol or symbol not in BOND_ASSET_BY_TICKER:
            continue
        candidates["bonds"].append(
            {
                "symbol": symbol,
                "asset_class": "bond_etf",
                "current_value": 0.0,
                "price": prices.get(symbol),
            }
        )

    candidates["cash"].append(
        {
            "symbol": "CASH",
            "asset_class": "cash",
            "current_value": max(portfolio.cash, 0.0),
            "price": 1.0,
        }
    )
    notes: list[str] = [
        "This is a target-allocation preview. It does not execute trades or account for taxes, spreads, or account restrictions."
    ]
    if not candidates["bonds"] and profile["target_allocation"]["bonds"] > 0:
        candidates["bonds"].append(
            {
                "symbol": "BOND_SLEEVE",
                "asset_class": "unallocated",
                "current_value": 0.0,
                "price": None,
            }
        )
        notes.append("Select one or more bond assets to replace the unallocated bond sleeve with tradable symbols.")
    if not candidates["equity"] and profile["target_allocation"]["equity"] > 0:
        candidates["equity"].append(
            {
                "symbol": "EQUITY_SLEEVE",
                "asset_class": "unallocated",
                "current_value": 0.0,
                "price": None,
            }
        )
        notes.append("The portfolio has no equity candidates, so the equity target remains an unallocated sleeve.")

    allocations: list[dict[str, Any]] = []
    for bucket, target_bucket_weight in profile["target_allocation"].items():
        bucket_candidates = candidates[bucket]
        target_weights = _bucket_target_weights(
            bucket_candidates,
            target_bucket_weight,
            max_position_weight=max_position_weight if bucket != "cash" else 1.0,
        )
        for candidate in bucket_candidates:
            target_weight = target_weights[candidate["symbol"]]
            target_value = target_weight * total_equity
            current_value = candidate["current_value"]
            price = candidate["price"]
            quantity_delta = (target_value - current_value) / price if price and price > 0 else None
            allocations.append(
                {
                    **candidate,
                    "risk_bucket": bucket,
                    "current_weight": current_value / total_equity,
                    "target_weight": target_weight,
                    "target_value": target_value,
                    "trade_value_delta": target_value - current_value,
                    "estimated_quantity_delta": quantity_delta,
                }
            )

    return {
        "portfolio_id": portfolio.id,
        "total_equity": total_equity,
        "profile": profile,
        "current_model": current_model,
        "allocations": sorted(allocations, key=lambda item: (item["risk_bucket"], -item["target_weight"], item["symbol"])),
        "notes": notes,
    }


def risk_bucket(position: Position) -> str:
    asset_class = str(position.asset_class or "equity").strip().lower()
    if asset_class == "cash":
        return "cash"
    if asset_class in {"bond", "bonds", "fixed_income", "fixed income", "bond_etf"}:
        return "bonds"
    if position.symbol.upper() in BOND_ASSET_BY_TICKER:
        return "bonds"
    return "equity"


def _position_model_volatility(position: Position) -> float:
    catalog = BOND_ASSET_BY_TICKER.get(position.symbol.upper())
    if catalog is not None:
        return float(catalog["model_volatility"])
    return ASSET_CLASS_MODEL_VOLATILITY.get(
        str(position.asset_class or "equity").strip().lower(),
        ASSET_CLASS_MODEL_VOLATILITY["equity"],
    )


def _bucket_target_weights(
    candidates: list[dict[str, Any]],
    target_bucket_weight: float,
    *,
    max_position_weight: float,
) -> dict[str, float]:
    if not candidates:
        return {}
    count = len(candidates)
    cap = max(float(max_position_weight), target_bucket_weight / count)
    scores = {candidate["symbol"]: max(float(candidate["current_value"]), 0.0) for candidate in candidates}
    if sum(scores.values()) <= 0:
        scores = {candidate["symbol"]: 1.0 for candidate in candidates}
    total_score = sum(scores.values())
    weights = {symbol: target_bucket_weight * score / total_score for symbol, score in scores.items()}
    active = set(weights)
    while active:
        capped = [symbol for symbol in active if weights[symbol] > cap + 1e-12]
        if not capped:
            break
        excess = 0.0
        for symbol in capped:
            excess += weights[symbol] - cap
            weights[symbol] = cap
            active.remove(symbol)
        if not active:
            break
        active_score = sum(scores[symbol] for symbol in active)
        for symbol in active:
            weights[symbol] += excess * (scores[symbol] / active_score if active_score else 1 / len(active))
    return weights


def _normalize_score(score: int) -> int:
    normalized = int(score)
    if not 1 <= normalized <= 10:
        raise ValueError("risk_score must be between 1 and 10.")
    return normalized


def _normalize_symbols(symbols: list[str]) -> list[str]:
    normalized: list[str] = []
    for symbol in symbols:
        clean = str(symbol).strip().upper()
        if clean and clean not in normalized:
            normalized.append(clean)
    return normalized


def _volatility_band(score: int) -> dict[str, Any]:
    normalized = _normalize_score(score)
    targets = {key: float(profile["target_volatility"]) for key, profile in RISK_PROFILES.items()}
    current = targets[normalized]
    lower = 0.0 if normalized == 1 else (targets[normalized - 1] + current) / 2
    upper = None if normalized == max(RISK_PROFILES) else (current + targets[normalized + 1]) / 2
    return {
        "min_volatility": lower,
        "max_volatility": upper,
        "display_range": _format_volatility_range(lower, upper),
        "narrative": _volatility_band_narrative(normalized, lower, upper),
    }


def _volatility_band_narrative(score: int, lower: float, upper: float | None) -> str:
    range_text = _format_volatility_range(lower, upper)
    if score <= 2:
        return (
            f"That is a lower-volatility range, usually around {range_text} annualized. "
            "It should feel relatively steady most of the time, although rate shocks can still hurt bond-heavy portfolios."
        )
    if score <= 4:
        return (
            f"That is a cautious range, usually around {range_text} annualized. "
            "Month-to-month swings should stay more muted than an equity-heavy portfolio, but down periods still happen."
        )
    if score <= 6:
        return (
            f"That is a moderate range, usually around {range_text} annualized. "
            "The portfolio should still experience meaningful swings and occasional double-digit losses in rough markets."
        )
    if score <= 8:
        return (
            f"That is a growth-oriented range, usually around {range_text} annualized. "
            "Regular double-digit drawdowns are plausible, and recovery periods can take time."
        )
    return (
        f"That is a high-volatility range, usually around {range_text} annualized. "
        "Sharp selloffs, deep drawdowns, and wide year-to-year performance swings should be expected."
    )


def _format_volatility_range(lower: float, upper: float | None) -> str:
    if upper is None:
        return f"{_format_volatility(lower)}+"
    return f"{_format_volatility(lower)} to {_format_volatility(upper)}"


def _format_volatility(value: float) -> str:
    percent = round(float(value) * 100, 1)
    text = f"{percent:.1f}".rstrip("0").rstrip(".")
    return f"{text}%"
