from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

_EPSILON = 1e-12


def analyze_trade_impact(
    current_holdings: Sequence[Mapping[str, Any]] | Mapping[str, Any],
    proposed_trades: Sequence[Mapping[str, Any]],
    covariance_matrix: Any,
    *,
    tickers: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Analyze portfolio risk before and after a set of proposed trades.

    Holdings should contain ticker, quantity, and price. Trades should contain
    ticker, side, and exactly one of notional or quantity. Covariance can be a
    dict-of-dicts keyed by ticker, a DataFrame-like object, or a NumPy array
    with the tickers argument supplied.
    """

    covariance_tickers, covariance = _coerce_covariance(covariance_matrix, tickers=tickers)
    ticker_to_index = {ticker: index for index, ticker in enumerate(covariance_tickers)}

    before_values, quantities, prices = _holding_vectors(
        current_holdings, covariance_tickers, ticker_to_index
    )
    after_values = before_values.copy()
    after_quantities = quantities.copy()

    for trade in proposed_trades:
        _apply_trade(
            trade=trade,
            values=after_values,
            quantities=after_quantities,
            prices=prices,
            ticker_to_index=ticker_to_index,
        )

    before_weights = _portfolio_weights(before_values)
    after_weights = _portfolio_weights(after_values)
    before_volatility = _portfolio_volatility(before_weights, covariance)
    after_volatility = _portfolio_volatility(after_weights, covariance)
    before_risk = _risk_contributions(before_weights, covariance, before_volatility)
    after_risk = _risk_contributions(after_weights, covariance, after_volatility)

    return {
        "tickers": covariance_tickers,
        "before_weights": _as_ticker_dict(covariance_tickers, before_weights),
        "after_weights": _as_ticker_dict(covariance_tickers, after_weights),
        "before_volatility": before_volatility,
        "after_volatility": after_volatility,
        "volatility_delta": after_volatility - before_volatility,
        "marginal_risk_contributions": {
            "before": _as_ticker_dict(covariance_tickers, before_risk["marginal"]),
            "after": _as_ticker_dict(covariance_tickers, after_risk["marginal"]),
        },
        "component_risk_contributions": {
            "before": _as_ticker_dict(covariance_tickers, before_risk["component"]),
            "after": _as_ticker_dict(covariance_tickers, after_risk["component"]),
        },
        "component_risk_contribution_pct": {
            "before": _as_ticker_dict(covariance_tickers, before_risk["component_pct"]),
            "after": _as_ticker_dict(covariance_tickers, after_risk["component_pct"]),
        },
        "concentration_metrics": {
            "before": _concentration_metrics(covariance_tickers, before_weights),
            "after": _concentration_metrics(covariance_tickers, after_weights),
        },
    }


def simulate_trade_impact(
    current_holdings: Sequence[Mapping[str, Any]] | Mapping[str, Any],
    proposed_trades: Sequence[Mapping[str, Any]],
    covariance_matrix: Any,
    *,
    tickers: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Compatibility alias for callers that prefer simulation naming."""

    return analyze_trade_impact(
        current_holdings=current_holdings,
        proposed_trades=proposed_trades,
        covariance_matrix=covariance_matrix,
        tickers=tickers,
    )


def _coerce_covariance(covariance_matrix: Any, *, tickers: Sequence[str] | None) -> tuple[list[str], np.ndarray]:
    if _is_dataframe_like(covariance_matrix):
        row_tickers = [_normalize_ticker(ticker) for ticker in list(covariance_matrix.index)]
        column_tickers = [_normalize_ticker(ticker) for ticker in list(covariance_matrix.columns)]
        if row_tickers != column_tickers:
            raise ValueError("covariance DataFrame index and columns must have the same ticker order.")
        covariance = np.asarray(covariance_matrix.to_numpy(), dtype=float)
        return row_tickers, _sanitize_covariance(covariance)

    if isinstance(covariance_matrix, Mapping):
        row_tickers = [_normalize_ticker(ticker) for ticker in covariance_matrix.keys()]
        if len(set(row_tickers)) != len(row_tickers):
            raise ValueError("covariance tickers must be unique after normalization.")

        rows = []
        for raw_row_ticker, row_ticker in zip(covariance_matrix.keys(), row_tickers, strict=True):
            row = covariance_matrix[raw_row_ticker]
            if not isinstance(row, Mapping):
                raise ValueError("mapping covariance must be a dict-of-dicts keyed by ticker.")
            rows.append([_required_numeric(row, column_ticker) for column_ticker in row_tickers])

        return row_tickers, _sanitize_covariance(np.asarray(rows, dtype=float))

    if isinstance(covariance_matrix, tuple) and len(covariance_matrix) == 2:
        tuple_tickers, matrix = covariance_matrix
        normalized_tickers = [_normalize_ticker(ticker) for ticker in tuple_tickers]
        return normalized_tickers, _sanitize_covariance(np.asarray(matrix, dtype=float))

    covariance = np.asarray(covariance_matrix, dtype=float)
    if tickers is None:
        raise ValueError("tickers must be supplied when covariance_matrix is a NumPy array.")
    normalized_tickers = [_normalize_ticker(ticker) for ticker in tickers]
    return normalized_tickers, _sanitize_covariance(covariance)


def _holding_vectors(
    holdings: Sequence[Mapping[str, Any]] | Mapping[str, Any],
    tickers: list[str],
    ticker_to_index: dict[str, int],
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    values = np.zeros(len(tickers), dtype=float)
    quantities = np.zeros(len(tickers), dtype=float)
    prices: dict[str, float] = {}

    for holding in _iter_holdings(holdings):
        ticker = _extract_ticker(holding)
        if ticker not in ticker_to_index:
            raise ValueError(f"holding ticker {ticker!r} is not present in the covariance matrix.")

        quantity = _non_negative_float(holding.get("quantity"), f"quantity for {ticker}")
        price = _non_negative_float(holding.get("price"), f"price for {ticker}")
        index = ticker_to_index[ticker]
        quantities[index] += quantity
        values[index] += quantity * price
        prices[ticker] = price

    return values, quantities, prices


def _apply_trade(
    *,
    trade: Mapping[str, Any],
    values: np.ndarray,
    quantities: np.ndarray,
    prices: dict[str, float],
    ticker_to_index: dict[str, int],
) -> None:
    ticker = _extract_ticker(trade)
    if ticker not in ticker_to_index:
        raise ValueError(f"trade ticker {ticker!r} is not present in the covariance matrix.")

    side = str(trade.get("side", "")).strip().lower()
    if side not in {"buy", "sell"}:
        raise ValueError("trade side must be either 'buy' or 'sell'.")

    has_notional = trade.get("notional") is not None
    has_quantity = trade.get("quantity") is not None
    if has_notional == has_quantity:
        raise ValueError("each trade must include exactly one of notional or quantity.")

    index = ticker_to_index[ticker]
    trade_price = _trade_price(trade, ticker, prices)
    if has_quantity:
        quantity = _positive_float(trade.get("quantity"), f"trade quantity for {ticker}")
        notional = quantity * trade_price
    else:
        quantity = None
        notional = _positive_float(trade.get("notional"), f"trade notional for {ticker}")

    signed_notional = notional if side == "buy" else -notional
    if side == "sell" and quantity is not None and quantities[index] - quantity < -_EPSILON:
        raise ValueError(f"trade would sell more {ticker} quantity than currently held.")
    if side == "sell" and values[index] + signed_notional < -_EPSILON:
        raise ValueError(f"trade would sell more {ticker} notional than currently held.")

    values[index] = max(values[index] + signed_notional, 0.0)

    if quantity is not None:
        quantity_delta = quantity if side == "buy" else -quantity
        quantities[index] = max(quantities[index] + quantity_delta, 0.0)
    elif trade_price > 0:
        quantity_delta = notional / trade_price
        if side == "sell":
            quantity_delta *= -1
        quantities[index] = max(quantities[index] + quantity_delta, 0.0)

    prices[ticker] = trade_price


def _portfolio_weights(values: np.ndarray) -> np.ndarray:
    total_value = float(values.sum())
    if total_value <= _EPSILON:
        return np.zeros_like(values, dtype=float)
    return values / total_value


def _portfolio_volatility(weights: np.ndarray, covariance: np.ndarray) -> float:
    variance = float(weights @ covariance @ weights)
    return float(np.sqrt(max(variance, 0.0)))


def _risk_contributions(
    weights: np.ndarray,
    covariance: np.ndarray,
    volatility: float,
) -> dict[str, np.ndarray]:
    if volatility <= _EPSILON:
        zeros = np.zeros_like(weights, dtype=float)
        return {"marginal": zeros, "component": zeros, "component_pct": zeros}

    marginal = covariance @ weights / volatility
    component = weights * marginal
    component_pct = component / volatility
    return {
        "marginal": np.nan_to_num(marginal, nan=0.0, posinf=0.0, neginf=0.0),
        "component": np.nan_to_num(component, nan=0.0, posinf=0.0, neginf=0.0),
        "component_pct": np.nan_to_num(component_pct, nan=0.0, posinf=0.0, neginf=0.0),
    }


def _concentration_metrics(tickers: list[str], weights: np.ndarray) -> dict[str, float | str | None | int]:
    positive_weights = np.clip(weights, 0.0, None)
    total_positive = float(positive_weights.sum())
    if total_positive <= _EPSILON:
        return {
            "hhi": 0.0,
            "effective_number_of_assets": 0.0,
            "max_weight": 0.0,
            "largest_position_ticker": None,
            "top_3_weight": 0.0,
            "long_position_count": 0,
        }

    normalized = positive_weights / total_positive
    hhi = float(normalized @ normalized)
    largest_index = int(np.argmax(normalized))
    sorted_weights = np.sort(normalized)[::-1]

    return {
        "hhi": hhi,
        "effective_number_of_assets": float(1.0 / hhi) if hhi > _EPSILON else 0.0,
        "max_weight": float(normalized[largest_index]),
        "largest_position_ticker": tickers[largest_index],
        "top_3_weight": float(sorted_weights[:3].sum()),
        "long_position_count": int(np.count_nonzero(normalized > _EPSILON)),
    }


def _sanitize_covariance(covariance: np.ndarray) -> np.ndarray:
    if covariance.ndim != 2 or covariance.shape[0] != covariance.shape[1]:
        raise ValueError("covariance matrix must be square.")

    sanitized = np.nan_to_num(covariance, nan=0.0, posinf=0.0, neginf=0.0)
    sanitized = (sanitized + sanitized.T) / 2.0
    diagonal = np.clip(np.diag(sanitized), 0.0, None)
    np.fill_diagonal(sanitized, diagonal)
    return sanitized


def _iter_holdings(holdings: Sequence[Mapping[str, Any]] | Mapping[str, Any]):
    if isinstance(holdings, Mapping):
        for ticker, payload in holdings.items():
            if isinstance(payload, Mapping):
                record = dict(payload)
            else:
                quantity, price = payload
                record = {"quantity": quantity, "price": price}
            record.setdefault("ticker", ticker)
            yield record
        return

    for holding in holdings:
        yield holding


def _extract_ticker(record: Mapping[str, Any]) -> str:
    raw_ticker = record.get("ticker", record.get("symbol"))
    if raw_ticker is None:
        raise ValueError("record is missing ticker.")
    return _normalize_ticker(raw_ticker)


def _trade_price(trade: Mapping[str, Any], ticker: str, prices: dict[str, float]) -> float:
    raw_price = trade.get("price")
    if raw_price is None:
        raw_price = prices.get(ticker)
    if raw_price is None:
        if trade.get("quantity") is None:
            return 0.0
        raise ValueError(f"quantity trade for {ticker} requires a trade price or current holding price.")
    return _positive_float(raw_price, f"price for {ticker}")


def _required_numeric(row: Mapping[str, Any], ticker: str) -> float:
    if ticker in row:
        return float(row[ticker])

    for key, value in row.items():
        if _normalize_ticker(key) == ticker:
            return float(value)

    raise ValueError(f"covariance row is missing ticker {ticker!r}.")


def _positive_float(value: Any, label: str) -> float:
    numeric = float(value)
    if not np.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{label} must be a positive finite value.")
    return numeric


def _non_negative_float(value: Any, label: str) -> float:
    numeric = float(value)
    if not np.isfinite(numeric) or numeric < 0:
        raise ValueError(f"{label} must be a non-negative finite value.")
    return numeric


def _normalize_ticker(ticker: Any) -> str:
    normalized = str(ticker).strip().upper()
    if not normalized:
        raise ValueError("ticker cannot be blank.")
    return normalized


def _is_dataframe_like(value: Any) -> bool:
    return all(hasattr(value, attribute) for attribute in ("index", "columns", "to_numpy"))


def _as_ticker_dict(tickers: list[str], values: np.ndarray) -> dict[str, float]:
    return {ticker: float(value) for ticker, value in zip(tickers, values, strict=True)}
