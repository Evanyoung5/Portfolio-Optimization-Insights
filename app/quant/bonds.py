from __future__ import annotations

from math import ceil
from typing import Any, Literal


BondStrategyType = Literal["ladder", "barbell"]


BOND_ASSET_CATALOG: list[dict[str, Any]] = [
    {
        "ticker": "BIL",
        "name": "State Street SPDR Bloomberg 1-3 Month T-Bill ETF",
        "category": "Treasury bills",
        "duration_bucket": "Ultra short",
        "term_proxy_years": 0.25,
        "credit_quality": "U.S. Treasury",
        "risk_level": 1,
        "model_volatility": 0.01,
        "description": "Very short Treasury-bill exposure with limited rate sensitivity.",
        "issuer_url": "https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-bloomberg-1-3-month-t-bill-etf-bil",
    },
    {
        "ticker": "SHY",
        "name": "iShares 1-3 Year Treasury Bond ETF",
        "category": "Treasury",
        "duration_bucket": "Short",
        "term_proxy_years": 2.0,
        "credit_quality": "U.S. Treasury",
        "risk_level": 2,
        "model_volatility": 0.035,
        "description": "Short Treasury exposure with modest interest-rate sensitivity.",
        "issuer_url": "https://www.ishares.com/us/products/239452/ishares-1-3-year-treasury-bond-etf",
    },
    {
        "ticker": "IEI",
        "name": "iShares 3-7 Year Treasury Bond ETF",
        "category": "Treasury",
        "duration_bucket": "Intermediate",
        "term_proxy_years": 5.0,
        "credit_quality": "U.S. Treasury",
        "risk_level": 3,
        "model_volatility": 0.06,
        "description": "Intermediate Treasury exposure between short and benchmark-duration funds.",
        "issuer_url": "https://www.ishares.com/us/products/239455/ishares-37-year-treasury-bond-etf",
    },
    {
        "ticker": "IEF",
        "name": "iShares 7-10 Year Treasury Bond ETF",
        "category": "Treasury",
        "duration_bucket": "Intermediate long",
        "term_proxy_years": 8.5,
        "credit_quality": "U.S. Treasury",
        "risk_level": 4,
        "model_volatility": 0.09,
        "description": "Benchmark Treasury exposure with meaningful sensitivity to rate changes.",
        "issuer_url": "https://www.ishares.com/us/products/239456/ishares-710-year-treasury-bond-etf",
    },
    {
        "ticker": "TLH",
        "name": "iShares 10-20 Year Treasury Bond ETF",
        "category": "Treasury",
        "duration_bucket": "Long",
        "term_proxy_years": 15.0,
        "credit_quality": "U.S. Treasury",
        "risk_level": 5,
        "model_volatility": 0.13,
        "description": "Long Treasury exposure with large price moves when interest rates change.",
        "issuer_url": "https://www.ishares.com/us/products/239453/ishares-1020-year-treasury-bond-etf",
    },
    {
        "ticker": "TLT",
        "name": "iShares 20+ Year Treasury Bond ETF",
        "category": "Treasury",
        "duration_bucket": "Very long",
        "term_proxy_years": 22.0,
        "credit_quality": "U.S. Treasury",
        "risk_level": 6,
        "model_volatility": 0.17,
        "description": "Very long Treasury exposure with high duration and potentially equity-like price swings.",
        "issuer_url": "https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond-etf",
    },
    {
        "ticker": "TIP",
        "name": "iShares TIPS Bond ETF",
        "category": "Inflation protected",
        "duration_bucket": "Intermediate",
        "term_proxy_years": 7.0,
        "credit_quality": "U.S. Treasury",
        "risk_level": 4,
        "model_volatility": 0.075,
        "description": "Treasury inflation-protected securities whose principal responds to inflation measures.",
        "issuer_url": "https://www.ishares.com/us/products/239467/ishares-tips-bond-etf",
    },
    {
        "ticker": "AGG",
        "name": "iShares Core U.S. Aggregate Bond ETF",
        "category": "Aggregate",
        "duration_bucket": "Intermediate",
        "term_proxy_years": 6.0,
        "credit_quality": "Investment grade",
        "risk_level": 3,
        "model_volatility": 0.06,
        "description": "Broad U.S. investment-grade bond-market exposure.",
        "issuer_url": "https://www.ishares.com/us/products/239458/ishares-core-total-us-bond-market-etf",
    },
    {
        "ticker": "LQD",
        "name": "iShares iBoxx $ Investment Grade Corporate Bond ETF",
        "category": "Corporate",
        "duration_bucket": "Intermediate long",
        "term_proxy_years": 8.0,
        "credit_quality": "Investment grade corporate",
        "risk_level": 5,
        "model_volatility": 0.10,
        "description": "Investment-grade corporate bonds with both rate and credit-spread risk.",
        "issuer_url": "https://www.ishares.com/us/products/239566/ishares-iboxx-investment-grade-corporate-bond-etf",
    },
    {
        "ticker": "HYG",
        "name": "iShares iBoxx $ High Yield Corporate Bond ETF",
        "category": "High yield corporate",
        "duration_bucket": "Intermediate",
        "term_proxy_years": 4.0,
        "credit_quality": "Below investment grade",
        "risk_level": 8,
        "model_volatility": 0.14,
        "description": "Below-investment-grade corporate bonds with elevated default and equity-market sensitivity.",
        "issuer_url": "https://www.ishares.com/us/products/239565/ishares-iboxx-high-yield-corporate-bond-etf",
    },
    {
        "ticker": "MUB",
        "name": "iShares National Muni Bond ETF",
        "category": "Municipal",
        "duration_bucket": "Intermediate",
        "term_proxy_years": 6.0,
        "credit_quality": "Investment grade municipal",
        "risk_level": 4,
        "model_volatility": 0.065,
        "description": "Broad investment-grade U.S. municipal-bond exposure; tax treatment depends on the investor.",
        "issuer_url": "https://www.ishares.com/us/products/239766/ishares-national-amtfree-muni-bond-etf",
    },
]

BOND_ASSET_BY_TICKER = {item["ticker"]: item for item in BOND_ASSET_CATALOG}


def bond_price(
    *,
    face_value: float,
    coupon_rate: float,
    years_to_maturity: float,
    yield_to_maturity: float,
    payments_per_year: int = 2,
) -> float:
    _validate_bond_inputs(face_value, coupon_rate, years_to_maturity, yield_to_maturity, payments_per_year)
    periods = max(1, round(years_to_maturity * payments_per_year))
    period_yield = yield_to_maturity / payments_per_year
    coupon = face_value * coupon_rate / payments_per_year
    discount_base = 1 + period_yield
    if discount_base <= 0:
        raise ValueError("yield_to_maturity is too negative for the payment frequency.")
    return sum(coupon / (discount_base**period) for period in range(1, periods + 1)) + face_value / (discount_base**periods)


def bond_duration(
    *,
    face_value: float,
    coupon_rate: float,
    years_to_maturity: float,
    yield_to_maturity: float,
    payments_per_year: int = 2,
) -> dict[str, float]:
    price = bond_price(
        face_value=face_value,
        coupon_rate=coupon_rate,
        years_to_maturity=years_to_maturity,
        yield_to_maturity=yield_to_maturity,
        payments_per_year=payments_per_year,
    )
    periods = max(1, round(years_to_maturity * payments_per_year))
    period_yield = yield_to_maturity / payments_per_year
    coupon = face_value * coupon_rate / payments_per_year
    weighted_present_value = 0.0
    for period in range(1, periods + 1):
        cash_flow = coupon + (face_value if period == periods else 0.0)
        time_years = period / payments_per_year
        weighted_present_value += time_years * cash_flow / ((1 + period_yield) ** period)
    macaulay = weighted_present_value / price if price > 0 else 0.0
    modified = macaulay / (1 + period_yield)
    return {"macaulay_duration": macaulay, "modified_duration": modified}


def analyze_bond_strategy(
    *,
    strategy_type: BondStrategyType,
    capital: float,
    risk_score: int,
    rungs: list[dict[str, Any]],
) -> dict[str, Any]:
    if strategy_type not in {"ladder", "barbell"}:
        raise ValueError("strategy_type must be ladder or barbell.")
    if capital <= 0:
        raise ValueError("capital must be positive.")
    if not 1 <= int(risk_score) <= 10:
        raise ValueError("risk_score must be between 1 and 10.")
    if not rungs:
        raise ValueError("At least one bond rung is required.")
    if len(rungs) > 12:
        raise ValueError("Bond strategies are limited to 12 rungs.")

    normalized_weights = _normalized_rung_weights(rungs, strategy_type=strategy_type, risk_score=int(risk_score))
    results: list[dict[str, Any]] = []
    cash_flows: dict[int, dict[str, float]] = {}
    for index, (rung, weight) in enumerate(zip(rungs, normalized_weights, strict=True), start=1):
        result = _analyze_rung(rung, capital=capital, weight=weight, index=index)
        results.append(result)
        maturity_year = max(1, ceil(result["years_to_maturity"]))
        for year in range(1, maturity_year + 1):
            entry = cash_flows.setdefault(year, {"year": year, "coupon_income": 0.0, "principal": 0.0, "total_cash_flow": 0.0})
            entry["coupon_income"] += result["annual_income"]
            if year == maturity_year:
                entry["principal"] += result["maturity_principal"]
            entry["total_cash_flow"] = entry["coupon_income"] + entry["principal"]

    total_allocated = sum(item["allocated_capital"] for item in results)
    annual_income = sum(item["annual_income"] for item in results)
    projected_proceeds = sum(item["projected_terminal_value"] for item in results)
    weighted_yield = sum(item["weight"] * item["yield_to_maturity"] for item in results)
    weighted_duration = sum(item["weight"] * item["modified_duration"] for item in results)
    weighted_annualized_return = sum(item["weight"] * item["annualized_return"] for item in results)
    return {
        "strategy_type": strategy_type,
        "risk_score": int(risk_score),
        "capital": capital,
        "summary": {
            "allocated_capital": total_allocated,
            "annual_income": annual_income,
            "portfolio_current_yield": annual_income / total_allocated if total_allocated else 0.0,
            "weighted_yield_to_maturity": weighted_yield,
            "weighted_modified_duration": weighted_duration,
            "weighted_annualized_return": weighted_annualized_return,
            "projected_maturity_proceeds": projected_proceeds,
        },
        "rungs": results,
        "cash_flow_schedule": [cash_flows[year] for year in sorted(cash_flows)],
        "notes": [
            "Projected returns assume all promised payments occur and coupons are reinvested at each rung's entered yield.",
            "ETF market prices are monitoring references only. The rung calculator models conventional bonds priced per $100 of face value.",
            "Taxes, defaults, calls, bid/ask spreads, and reinvestment-rate changes are not included.",
        ],
    }


def recommended_bond_rungs(risk_score: int, strategy_type: BondStrategyType) -> list[dict[str, Any]]:
    score = int(risk_score)
    if not 1 <= score <= 10:
        raise ValueError("risk_score must be between 1 and 10.")
    if strategy_type == "barbell":
        if score <= 3:
            terms, weights = [1.0, 7.0], [0.70, 0.30]
        elif score <= 6:
            terms, weights = [1.0, 10.0], [0.55, 0.45]
        else:
            terms, weights = [2.0, 20.0], [0.35, 0.65]
    else:
        if score <= 3:
            terms = [1.0, 2.0, 3.0, 4.0, 5.0]
        elif score <= 6:
            terms = [1.0, 3.0, 5.0, 7.0, 10.0]
        else:
            terms = [2.0, 5.0, 10.0, 15.0, 20.0]
        weights = [1 / len(terms)] * len(terms)
    return [
        {
            "label": f"{term:g}-year rung",
            "years_to_maturity": term,
            "allocation_weight": weight,
            "face_value": 1000.0,
            "market_price_pct": 100.0,
            "coupon_rate": 0.04,
            "yield_to_maturity": 0.04,
            "payments_per_year": 2,
        }
        for term, weight in zip(terms, weights, strict=True)
    ]


def _analyze_rung(rung: dict[str, Any], *, capital: float, weight: float, index: int) -> dict[str, Any]:
    face_value = float(rung.get("face_value", 1000.0))
    market_price_pct = float(rung.get("market_price_pct", 100.0))
    coupon_rate = float(rung.get("coupon_rate", 0.0))
    yield_to_maturity = float(rung.get("yield_to_maturity", 0.0))
    years_to_maturity = float(rung.get("years_to_maturity", 0.0))
    payments_per_year = int(rung.get("payments_per_year", 2))
    _validate_bond_inputs(face_value, coupon_rate, years_to_maturity, yield_to_maturity, payments_per_year)
    if market_price_pct <= 0:
        raise ValueError("market_price_pct must be positive.")

    market_price = face_value * market_price_pct / 100
    allocated = capital * weight
    units = allocated / market_price
    annual_income = units * face_value * coupon_rate
    maturity_principal = units * face_value
    theoretical_price = bond_price(
        face_value=face_value,
        coupon_rate=coupon_rate,
        years_to_maturity=years_to_maturity,
        yield_to_maturity=yield_to_maturity,
        payments_per_year=payments_per_year,
    )
    durations = bond_duration(
        face_value=face_value,
        coupon_rate=coupon_rate,
        years_to_maturity=years_to_maturity,
        yield_to_maturity=yield_to_maturity,
        payments_per_year=payments_per_year,
    )
    periods = max(1, round(years_to_maturity * payments_per_year))
    coupon_payment = units * face_value * coupon_rate / payments_per_year
    period_yield = yield_to_maturity / payments_per_year
    coupon_terminal_value = sum(coupon_payment * ((1 + period_yield) ** (periods - period)) for period in range(1, periods + 1))
    projected_terminal_value = maturity_principal + coupon_terminal_value
    annualized_return = (projected_terminal_value / allocated) ** (1 / years_to_maturity) - 1 if allocated > 0 else 0.0
    return {
        "label": str(rung.get("label") or f"Rung {index}"),
        "ticker": str(rung.get("ticker") or "").strip().upper() or None,
        "weight": weight,
        "allocated_capital": allocated,
        "face_value": face_value,
        "market_price_pct": market_price_pct,
        "market_price": market_price,
        "theoretical_price_pct": theoretical_price / face_value * 100,
        "coupon_rate": coupon_rate,
        "yield_to_maturity": yield_to_maturity,
        "years_to_maturity": years_to_maturity,
        "payments_per_year": payments_per_year,
        "units": units,
        "annual_income": annual_income,
        "current_yield": annual_income / allocated if allocated else 0.0,
        "maturity_principal": maturity_principal,
        "projected_terminal_value": projected_terminal_value,
        "total_return": projected_terminal_value / allocated - 1 if allocated else 0.0,
        "annualized_return": annualized_return,
        **durations,
    }


def _normalized_rung_weights(rungs: list[dict[str, Any]], *, strategy_type: BondStrategyType, risk_score: int) -> list[float]:
    raw = [max(float(rung.get("allocation_weight", 0.0)), 0.0) for rung in rungs]
    total = sum(raw)
    if total > 0:
        return [weight / total for weight in raw]
    if strategy_type == "barbell" and len(rungs) >= 2:
        short_weight = 0.70 if risk_score <= 3 else 0.55 if risk_score <= 6 else 0.35
        weights = [0.0] * len(rungs)
        weights[0] = short_weight
        weights[-1] = 1 - short_weight
        return weights
    return [1 / len(rungs)] * len(rungs)


def _validate_bond_inputs(
    face_value: float,
    coupon_rate: float,
    years_to_maturity: float,
    yield_to_maturity: float,
    payments_per_year: int,
) -> None:
    if face_value <= 0:
        raise ValueError("face_value must be positive.")
    if coupon_rate < 0 or coupon_rate > 1:
        raise ValueError("coupon_rate must be between 0 and 1.")
    if years_to_maturity <= 0 or years_to_maturity > 50:
        raise ValueError("years_to_maturity must be between 0 and 50.")
    if yield_to_maturity <= -1 or yield_to_maturity > 1:
        raise ValueError("yield_to_maturity must be greater than -1 and no more than 1.")
    if payments_per_year not in {1, 2, 4, 12}:
        raise ValueError("payments_per_year must be 1, 2, 4, or 12.")
