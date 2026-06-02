from collections import defaultdict
from typing import Literal

from app.db.models import Portfolio, Position

Objective = Literal["max_sharpe", "min_volatility", "equal_weight"]
TradeSide = Literal["buy", "sell"]

ASSET_CLASS_RISK = {
    "cash": 0.01,
    "bond": 0.05,
    "fixed_income": 0.05,
    "equity": 0.16,
    "etf": 0.14,
    "commodity": 0.22,
    "crypto": 0.65,
}

ASSET_CLASS_EXPECTED_RETURN = {
    "cash": 0.02,
    "bond": 0.04,
    "fixed_income": 0.04,
    "equity": 0.08,
    "etf": 0.075,
    "commodity": 0.055,
    "crypto": 0.12,
}


def analyze_portfolio(portfolio: Portfolio) -> dict[str, object]:
    total_market_value = _positions_market_value(portfolio.positions)
    total_equity = total_market_value + portfolio.cash
    denominator = total_equity if total_equity > 0 else 1

    weights = [
        {
            "symbol": position.symbol,
            "asset_class": position.asset_class,
            "market_value": position.market_value,
            "weight": position.market_value / denominator,
        }
        for position in portfolio.positions
    ]

    exposure: defaultdict[str, float] = defaultdict(float)
    for position in portfolio.positions:
        exposure[position.asset_class] += position.market_value / denominator

    if portfolio.cash:
        exposure["cash"] += portfolio.cash / denominator

    return {
        "portfolio_id": portfolio.id,
        "total_market_value": total_market_value,
        "total_equity": total_equity,
        "cash": portfolio.cash,
        "position_count": len(portfolio.positions),
        "weights": weights,
        "asset_class_exposure": dict(exposure),
    }


def optimize_portfolio(
    *,
    portfolio: Portfolio,
    objective: Objective,
    min_weight: float,
    max_weight: float,
    risk_free_rate: float,
    target_return: float | None,
) -> dict[str, object]:
    if min_weight > max_weight:
        raise ValueError("min_weight must be less than or equal to max_weight.")

    positions = portfolio.positions
    if not positions:
        return {
            "portfolio_id": portfolio.id,
            "objective": objective,
            "total_equity": portfolio.cash,
            "allocations": [],
            "notes": ["Portfolio has no positions to optimize."],
        }

    total_equity = _positions_market_value(positions) + portfolio.cash
    if total_equity <= 0:
        raise ValueError("Portfolio must have positive equity before optimization.")

    raw_scores = _objective_scores(positions, objective, risk_free_rate)
    target_weights = _bounded_normalize(raw_scores, min_weight=min_weight, max_weight=max_weight)

    allocations = []
    for position in positions:
        current_value = position.market_value
        current_weight = current_value / total_equity
        target_weight = target_weights[position.symbol]
        target_value = target_weight * total_equity
        allocations.append(
            {
                "symbol": position.symbol,
                "current_weight": current_weight,
                "target_weight": target_weight,
                "current_value": current_value,
                "target_value": target_value,
                "trade_value_delta": target_value - current_value,
            }
        )

    notes = [
        "Optimization uses deterministic asset-class, cost-basis, and ticker-level assumptions until historical covariance models are added."
    ]
    if target_return is not None:
        notes.append("target_return is accepted for API compatibility but not enforced yet.")

    return {
        "portfolio_id": portfolio.id,
        "objective": objective,
        "total_equity": total_equity,
        "allocations": allocations,
        "notes": notes,
    }


def simulate_trade_impact(
    *,
    portfolio: Portfolio,
    symbol: str,
    side: TradeSide,
    quantity: float,
    price: float,
    estimated_slippage_bps: float,
    fee_rate_bps: float,
) -> dict[str, object]:
    current_position = _find_position(portfolio.positions, symbol)
    if side == "sell" and (current_position is None or current_position.quantity < quantity):
        raise ValueError("Cannot sell more shares than the current portfolio holds.")

    notional = quantity * price
    estimated_fees = notional * fee_rate_bps / 10_000
    estimated_slippage = notional * estimated_slippage_bps / 10_000
    cost = estimated_fees + estimated_slippage
    position_quantity_delta = quantity if side == "buy" else -quantity
    cash_delta = -(notional + cost) if side == "buy" else notional - cost

    pre_trade_equity = _positions_market_value(portfolio.positions) + portfolio.cash
    post_cash = portfolio.cash + cash_delta
    post_positions = _positions_after_trade(
        portfolio.positions,
        symbol=symbol,
        quantity_delta=position_quantity_delta,
        price=price,
    )
    post_trade_equity = _positions_market_value(post_positions) + post_cash
    resulting_position = _find_position(post_positions, symbol)
    resulting_market_value = resulting_position.market_value if resulting_position else 0
    resulting_weight = resulting_market_value / post_trade_equity if post_trade_equity > 0 else 0

    return {
        "portfolio_id": portfolio.id,
        "symbol": symbol,
        "side": side,
        "notional": notional,
        "estimated_fees": estimated_fees,
        "estimated_slippage": estimated_slippage,
        "cash_delta": cash_delta,
        "pre_trade_equity": pre_trade_equity,
        "post_trade_equity": post_trade_equity,
        "position_quantity_delta": position_quantity_delta,
        "resulting_weight": resulting_weight,
    }


def _positions_market_value(positions: list[Position]) -> float:
    return sum(position.market_value for position in positions)


def _objective_scores(
    positions: list[Position],
    objective: Objective,
    risk_free_rate: float,
) -> dict[str, float]:
    if objective == "equal_weight":
        return {position.symbol: 1 for position in positions}

    scores: dict[str, float] = {}
    for position in positions:
        risk = ASSET_CLASS_RISK.get(position.asset_class, ASSET_CLASS_RISK["equity"])
        risk *= _ticker_risk_multiplier(position.symbol)
        expected_return = ASSET_CLASS_EXPECTED_RETURN.get(
            position.asset_class,
            ASSET_CLASS_EXPECTED_RETURN["equity"],
        )
        expected_return *= _ticker_return_multiplier(position.symbol)
        momentum = _unrealized_return(position)

        if objective == "min_volatility":
            stability_bonus = 1 / (1 + min(abs(momentum), 1.0))
            scores[position.symbol] = stability_bonus / risk
        else:
            adjusted_return = expected_return + (0.08 * max(min(momentum, 1.0), -1.0))
            scores[position.symbol] = max(adjusted_return - risk_free_rate, 0.001) / risk

    return scores


def _unrealized_return(position: Position) -> float:
    if position.cost_basis > 0:
        return position.unrealized_gain_loss / position.cost_basis
    if position.average_cost > 0 and position.price > 0:
        return (position.price / position.average_cost) - 1
    return 0.0


def _ticker_risk_multiplier(symbol: str) -> float:
    bucket = _symbol_bucket(symbol, salt=17)
    return 0.82 + (bucket / 999) * 0.36


def _ticker_return_multiplier(symbol: str) -> float:
    bucket = _symbol_bucket(symbol, salt=53)
    return 0.88 + (bucket / 999) * 0.24


def _symbol_bucket(symbol: str, *, salt: int) -> int:
    total = salt
    for index, char in enumerate(symbol.upper(), start=1):
        total = (total * 33 + index * ord(char)) % 1000
    return total


def _bounded_normalize(
    scores: dict[str, float],
    *,
    min_weight: float,
    max_weight: float,
) -> dict[str, float]:
    symbols = list(scores)
    count = len(symbols)
    if count == 0:
        return {}
    if min_weight * count > 1:
        raise ValueError("min_weight is too high for the number of positions.")
    if max_weight * count < 1:
        raise ValueError("max_weight is too low for the number of positions.")

    total_score = sum(max(score, 0) for score in scores.values())
    if total_score <= 0:
        normalized = {symbol: 1 / count for symbol in symbols}
    else:
        normalized = {symbol: max(scores[symbol], 0) / total_score for symbol in symbols}

    weights = {symbol: min_weight for symbol in symbols}
    remaining = 1 - min_weight * count
    active = set(symbols)

    while active and remaining > 1e-12:
        active_score = sum(normalized[symbol] for symbol in active)
        if active_score <= 0:
            increment = remaining / len(active)
            proposed = {symbol: weights[symbol] + increment for symbol in active}
        else:
            proposed = {
                symbol: weights[symbol] + remaining * (normalized[symbol] / active_score)
                for symbol in active
            }

        capped = {symbol for symbol, value in proposed.items() if value > max_weight}
        if not capped:
            weights.update(proposed)
            remaining = 0
            break

        for symbol in capped:
            remaining -= max_weight - weights[symbol]
            weights[symbol] = max_weight
            active.remove(symbol)

    if remaining > 1e-9 and active:
        increment = remaining / len(active)
        for symbol in active:
            weights[symbol] += increment

    total_weight = sum(weights.values())
    return {symbol: weight / total_weight for symbol, weight in weights.items()}


def _find_position(positions: list[Position], symbol: str) -> Position | None:
    return next((position for position in positions if position.symbol == symbol), None)


def _positions_after_trade(
    positions: list[Position],
    *,
    symbol: str,
    quantity_delta: float,
    price: float,
) -> list[Position]:
    updated: list[Position] = []
    found = False
    for position in positions:
        if position.symbol != symbol:
            updated.append(position)
            continue

        found = True
        new_quantity = position.quantity + quantity_delta
        if new_quantity > 0:
            if quantity_delta > 0:
                new_price = (
                    (position.quantity * position.price) + (quantity_delta * price)
                ) / new_quantity
            else:
                new_price = position.price
            updated.append(
                Position(
                    symbol=position.symbol,
                    quantity=new_quantity,
                    price=new_price,
                    asset_class=position.asset_class,
                )
            )

    if not found and quantity_delta > 0:
        updated.append(Position(symbol=symbol, quantity=quantity_delta, price=price))

    return updated
