from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Literal

from app.db.models import Portfolio, Position

GroupBy = Literal["asset_class", "sector", "industry"]

COLOR_SCALE = [
    [0.00, "#7f1d1d"],
    [0.35, "#dc2626"],
    [0.50, "#1f2937"],
    [0.65, "#16a34a"],
    [1.00, "#064e3b"],
]


def build_portfolio_heatmap(
    portfolio: Portfolio,
    *,
    market_data: list[dict[str, Any]] | None = None,
    group_by: GroupBy = "sector",
) -> dict[str, Any]:
    """Build frontend-ready treemap data sized by personal position value.

    Market data is optional. When provided, price and daily return fields are used to refresh
    position value and color. Without it, the current stored position price is used and color
    defaults to unrealized return when available, otherwise 0.
    """

    market_by_ticker = _market_data_by_ticker(market_data or [])
    holdings = [_holding_from_position(position, market_by_ticker.get(position.symbol, {}), group_by) for position in portfolio.positions]
    holdings = [holding for holding in holdings if holding["market_value"] > 0]
    holdings.sort(key=lambda holding: (-holding["market_value"], holding["ticker"]))

    total_market_value = sum(holding["market_value"] for holding in holdings)
    for holding in holdings:
        holding["portfolio_weight"] = _safe_divide(holding["market_value"], total_market_value)
        holding["portfolio_weight_pct"] = holding["portfolio_weight"] * 100.0

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for holding in holdings:
        grouped[holding["group_label"]].append(holding)

    nodes: list[dict[str, Any]] = []
    root_color = _weighted_metric(holdings, "daily_return_pct")
    nodes.append(
        {
            "id": "portfolio",
            "label": "Portfolio",
            "parent": None,
            "level": "portfolio",
            "ticker": None,
            "sector": None,
            "industry": None,
            "market_value": total_market_value,
            "cost_basis": sum(holding.get("cost_basis") or 0.0 for holding in holdings),
            "portfolio_weight": 1.0 if total_market_value else 0.0,
            "portfolio_weight_pct": 100.0 if total_market_value else 0.0,
            "daily_return_pct": root_color,
            "price": None,
            "previous_close": None,
            "unrealized_pnl": sum(holding["unrealized_pnl"] or 0.0 for holding in holdings),
            "unrealized_return_pct": _portfolio_unrealized_return(holdings),
        }
    )

    for group_label in sorted(grouped):
        group_holdings = sorted(grouped[group_label], key=lambda holding: (-holding["market_value"], holding["ticker"]))
        group_value = sum(holding["market_value"] for holding in group_holdings)
        group_id = f"group:{group_label}"
        nodes.append(
            {
                "id": group_id,
                "label": group_label,
                "parent": "portfolio",
                "level": "group",
                "ticker": None,
                "sector": group_holdings[0].get("sector"),
                "industry": None,
                "market_value": group_value,
                "cost_basis": sum(holding.get("cost_basis") or 0.0 for holding in group_holdings),
                "portfolio_weight": _safe_divide(group_value, total_market_value),
                "portfolio_weight_pct": _safe_divide(group_value, total_market_value) * 100.0,
                "daily_return_pct": _weighted_metric(group_holdings, "daily_return_pct"),
                "price": None,
                "previous_close": None,
                "unrealized_pnl": sum(holding["unrealized_pnl"] or 0.0 for holding in group_holdings),
                "unrealized_return_pct": _portfolio_unrealized_return(group_holdings),
            }
        )
        for holding in group_holdings:
            nodes.append(
                {
                    "id": f"position:{holding['ticker']}",
                    "label": holding["ticker"],
                    "parent": group_id,
                    "level": "position",
                    "ticker": holding["ticker"],
                    "sector": holding["sector"],
                    "industry": holding["industry"],
                    "market_value": holding["market_value"],
                    "cost_basis": holding["cost_basis"],
                    "portfolio_weight": holding["portfolio_weight"],
                    "portfolio_weight_pct": holding["portfolio_weight_pct"],
                    "daily_return_pct": holding["daily_return_pct"],
                    "price": holding["price"],
                    "previous_close": holding["previous_close"],
                    "unrealized_pnl": holding["unrealized_pnl"],
                    "unrealized_return_pct": holding["unrealized_return_pct"],
                }
            )

    return {
        "portfolio_id": portfolio.id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": "Personal Portfolio Heatmap",
        "size_metric": "market_value",
        "color_metric": "daily_return_pct",
        "group_by": group_by,
        "total_market_value": total_market_value,
        "nodes": nodes,
        "holdings": [node for node in nodes if node["level"] == "position"],
        "plotly": _plotly_payload(nodes),
    }


def _holding_from_position(position: Position, market: dict[str, Any], group_by: GroupBy) -> dict[str, Any]:
    ticker = position.symbol.strip().upper()
    price = _positive_float(market.get("price"), default=position.price)
    previous_close = _positive_float(market.get("previous_close"), default=None)
    daily_return_pct = _optional_float(market.get("daily_return_pct"))
    if daily_return_pct is None:
        daily_return_pct = _daily_return_pct(price, previous_close)

    quantity = max(float(position.quantity), 0.0)
    market_value = quantity * price
    cost_basis = float(position.cost_basis or 0.0)
    if cost_basis <= 0 and position.average_cost:
        cost_basis = quantity * float(position.average_cost)
    unrealized_pnl = market_value - cost_basis if cost_basis > 0 else None
    unrealized_return_pct = ((market_value / cost_basis) - 1.0) * 100.0 if cost_basis > 0 else None

    sector = _clean_label(market.get("sector"), fallback=position.asset_class or "Unclassified")
    industry = _clean_label(market.get("industry"), fallback="Unclassified")
    asset_class = _clean_label(position.asset_class, fallback="Unclassified")
    if group_by == "sector":
        group_label = sector
    elif group_by == "industry":
        group_label = industry
    else:
        group_label = asset_class

    return {
        "ticker": ticker,
        "quantity": quantity,
        "price": price,
        "previous_close": previous_close,
        "daily_return_pct": daily_return_pct if daily_return_pct is not None else (unrealized_return_pct or 0.0),
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_return_pct": unrealized_return_pct,
        "sector": sector,
        "industry": industry,
        "asset_class": asset_class,
        "group_label": group_label,
        "portfolio_weight": 0.0,
        "portfolio_weight_pct": 0.0,
    }


def _plotly_payload(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    customdata: list[list[Any]] = []
    for node in nodes:
        customdata.append(
            [
                node["price"],
                node["market_value"],
                node["daily_return_pct"],
                node["portfolio_weight_pct"],
                node["unrealized_return_pct"],
                node.get("cost_basis"),
                node.get("unrealized_pnl"),
            ]
        )

    return {
        "type": "treemap",
        "ids": [node["id"] for node in nodes],
        "labels": [node["label"] for node in nodes],
        "parents": [node["parent"] or "" for node in nodes],
        "values": [node["market_value"] for node in nodes],
        "colors": [node["daily_return_pct"] for node in nodes],
        "customdata": customdata,
        "branchvalues": "total",
        "colorscale": COLOR_SCALE,
        "texttemplate": "<b>%{label}</b><br>%{customdata[3]:.2f}% weight<br>%{customdata[2]:+.2f}% day",
        "hovertemplate": (
            "<b>%{label}</b><br>"
            "Price: $%{customdata[0]:,.2f}<br>"
            "Market Value: $%{customdata[1]:,.2f}<br>"
            "Daily Return: %{customdata[2]:+.2f}%<br>"
            "Portfolio Weight: %{customdata[3]:.2f}%<br>"
            "Cost Basis: $%{customdata[5]:,.2f}<br>"
            "Unrealized P/L: $%{customdata[6]:+,.2f}<br>"
            "Unrealized Return: %{customdata[4]:+.2f}%"
            "<extra></extra>"
        ),
    }


def _market_data_by_ticker(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    market: dict[str, dict[str, Any]] = {}
    for item in items:
        ticker = str(item.get("ticker") or "").strip().upper()
        if ticker:
            market[ticker] = item
    return market


def _weighted_metric(holdings: list[dict[str, Any]], metric: str) -> float:
    total_value = sum(holding["market_value"] for holding in holdings)
    if total_value <= 0:
        return 0.0
    return sum((holding.get(metric) or 0.0) * holding["market_value"] for holding in holdings) / total_value


def _portfolio_unrealized_return(holdings: list[dict[str, Any]]) -> float | None:
    cost_basis = sum(holding.get("cost_basis") or 0.0 for holding in holdings)
    if cost_basis <= 0:
        return None
    market_value = sum(holding["market_value"] for holding in holdings)
    return ((market_value / cost_basis) - 1.0) * 100.0


def _daily_return_pct(price: float, previous_close: float | None) -> float | None:
    if previous_close is None or previous_close <= 0:
        return None
    return ((price / previous_close) - 1.0) * 100.0


def _positive_float(value: Any, *, default: float | None) -> float:
    parsed = _optional_float(value)
    if parsed is None or parsed <= 0:
        return float(default or 0.0)
    return parsed


def _optional_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(parsed):
        return None
    return parsed


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _clean_label(value: Any, *, fallback: str) -> str:
    label = str(value or "").strip()
    return label if label else fallback
