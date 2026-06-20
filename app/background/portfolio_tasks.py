from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.db.models import (
    CashTransaction,
    Portfolio,
    PortfolioSettings,
    PortfolioValuationSnapshot,
    Position,
    PositionLot,
    TradeTransaction,
)

CASH_INFLOW_TYPES = {"deposit", "transfer_in", "dividend", "interest", "adjustment_in"}
CASH_OUTFLOW_TYPES = {"withdrawal", "transfer_out", "fee", "tax", "adjustment_out"}
EXTERNAL_CONTRIBUTION_TYPES = {"deposit", "transfer_in", "adjustment_in"}
EXTERNAL_WITHDRAWAL_TYPES = {"withdrawal", "transfer_out", "adjustment_out"}


def create_position_lot(payload: dict[str, Any]) -> PositionLot:
    purchased_at = _coerce_datetime(payload.get("purchased_at") or datetime.now(timezone.utc))
    purchase_price = float(payload["purchase_price"])
    current_price = float(payload.get("current_price") or purchase_price)
    quantity = float(payload["quantity"])

    return PositionLot(
        id=str(uuid4()),
        symbol=str(payload["ticker"]).strip().upper(),
        quantity=quantity,
        remaining_quantity=float(payload.get("remaining_quantity") or quantity),
        purchase_price=purchase_price,
        current_price=current_price,
        fees=float(payload.get("fees") or 0),
        asset_class=str(payload.get("asset_class") or "equity").strip().lower(),
        purchased_at=purchased_at,
        source=str(payload.get("source") or "manual"),
        notes=payload.get("notes"),
    )


def create_lots_from_aggregate_positions(positions: list[Position]) -> list[PositionLot]:
    return [
        PositionLot(
            id=str(uuid4()),
            symbol=position.symbol,
            quantity=position.quantity,
            remaining_quantity=position.quantity,
            purchase_price=position.average_cost or position.price,
            current_price=position.price,
            asset_class=position.asset_class,
            fees=0,
            source="aggregate_position",
        )
        for position in positions
        if position.quantity > 0
    ]


def record_manual_lots(
    repository: Any,
    portfolio_id: str,
    lot_payloads: list[dict[str, Any]],
) -> Portfolio:
    job = repository.enqueue_background_job(
        portfolio_id,
        "manual_lot_rollup",
        message="Queued cost-basis rollup after manual lot entry.",
    )
    try:
        lots = [create_position_lot(payload) for payload in lot_payloads]
        repository.add_lots(portfolio_id, lots)
        portfolio = rebuild_portfolio_positions(repository, portfolio_id)
        create_valuation_snapshot(
            repository,
            portfolio_id,
            metadata={"event": "manual_lot_rollup", "lots_added": len(lots)},
        )
        repository.complete_background_job(
            portfolio_id,
            job.id,
            status="completed",
            message=f"Rolled up {len(lots)} manual lot(s).",
        )
        return portfolio
    except Exception as exc:
        repository.complete_background_job(
            portfolio_id,
            job.id,
            status="failed",
            message=str(exc),
        )
        raise


def record_cash_transaction(
    repository: Any,
    portfolio_id: str,
    payload: dict[str, Any],
) -> Portfolio:
    portfolio = _portfolio_or_error(repository, portfolio_id)
    transaction = create_cash_transaction(
        portfolio_id=portfolio_id,
        base_currency=portfolio.base_currency,
        payload=payload,
    )
    repository.add_cash_transaction(transaction)
    updated = repository.update_cash(portfolio_id, portfolio.cash + cash_transaction_cash_delta(transaction))
    create_valuation_snapshot(
        repository,
        portfolio_id,
        metadata={"event": "cash_transaction", "transaction_id": transaction.id},
    )
    return updated


def create_cash_transaction(
    *,
    portfolio_id: str,
    base_currency: str,
    payload: dict[str, Any],
) -> CashTransaction:
    transaction_type = str(payload["transaction_type"]).strip().lower()
    if transaction_type not in CASH_INFLOW_TYPES | CASH_OUTFLOW_TYPES:
        raise ValueError(f"Unsupported cash transaction type: {transaction_type}.")
    amount = float(payload["amount"])
    if amount <= 0:
        raise ValueError("Cash transaction amount must be positive.")
    currency = str(payload.get("currency") or base_currency).strip().upper()
    if len(currency) != 3:
        raise ValueError("Cash transaction currency must be a 3-letter code.")
    return CashTransaction(
        id=str(uuid4()),
        portfolio_id=portfolio_id,
        transaction_type=transaction_type,
        amount=amount,
        currency=currency,
        occurred_at=_coerce_datetime(payload.get("occurred_at") or datetime.now(timezone.utc)),
        source=str(payload.get("source") or "manual"),
        notes=payload.get("notes"),
    )


def record_manual_trade(
    repository: Any,
    portfolio_id: str,
    payload: dict[str, Any],
) -> Portfolio:
    portfolio = _portfolio_or_error(repository, portfolio_id)
    side = str(payload["side"]).strip().lower()
    if side not in {"buy", "sell"}:
        raise ValueError("Trade side must be buy or sell.")

    symbol = str(payload["ticker"]).strip().upper()
    quantity = float(payload["quantity"])
    price = float(payload["price"])
    fees = float(payload.get("fees") or 0)
    if quantity <= 0 or price <= 0:
        raise ValueError("Trade quantity and price must be positive.")
    if fees < 0:
        raise ValueError("Trade fees cannot be negative.")

    occurred_at = _coerce_datetime(payload.get("occurred_at") or datetime.now(timezone.utc))
    asset_class = str(payload.get("asset_class") or "equity").strip().lower()
    notes = payload.get("notes")

    if side == "buy":
        lot = create_position_lot(
            {
                "ticker": symbol,
                "quantity": quantity,
                "purchase_price": price,
                "current_price": float(payload.get("current_price") or price),
                "fees": fees,
                "purchased_at": occurred_at,
                "asset_class": asset_class,
                "source": "manual_trade",
                "notes": notes,
            }
        )
        repository.add_lots(portfolio_id, [lot])
        transaction = TradeTransaction(
            id=str(uuid4()),
            portfolio_id=portfolio_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            fees=fees,
            asset_class=asset_class,
            occurred_at=occurred_at,
            lot_ids=[lot.id],
            notes=notes,
        )
        repository.add_trade_transaction(transaction)
        repository.update_cash(portfolio_id, portfolio.cash + transaction.cash_delta)
        updated = rebuild_portfolio_positions(repository, portfolio_id)
        create_valuation_snapshot(
            repository,
            portfolio_id,
            metadata={"event": "manual_trade", "trade_id": transaction.id},
        )
        return updated

    all_lots = repository.list_lots(portfolio_id)
    updated_lots, realized_gain_loss, consumed_lot_ids, asset_class = _apply_fifo_sale(
        all_lots,
        symbol=symbol,
        quantity=quantity,
        price=price,
        fees=fees,
        fallback_asset_class=asset_class,
    )
    transaction = TradeTransaction(
        id=str(uuid4()),
        portfolio_id=portfolio_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        fees=fees,
        asset_class=asset_class,
        occurred_at=occurred_at,
        realized_gain_loss=realized_gain_loss,
        lot_ids=consumed_lot_ids,
        notes=notes,
    )
    repository.replace_lots(portfolio_id, updated_lots)
    repository.add_trade_transaction(transaction)
    repository.update_cash(portfolio_id, portfolio.cash + transaction.cash_delta)
    updated = rebuild_portfolio_positions(repository, portfolio_id)
    create_valuation_snapshot(
        repository,
        portfolio_id,
        metadata={"event": "manual_trade", "trade_id": transaction.id},
    )
    return updated


def apply_market_quotes_to_portfolio(
    repository: Any,
    portfolio_id: str,
    quotes: list[Any],
) -> Portfolio:
    portfolio = _portfolio_or_error(repository, portfolio_id)
    quote_prices = {
        str(quote.ticker).strip().upper(): float(quote.price)
        for quote in quotes
        if getattr(quote, "price", None) is not None and float(quote.price) > 0
    }
    if not quote_prices:
        return portfolio

    if portfolio.lots:
        updated_lots: list[PositionLot] = []
        changed = False
        for lot in portfolio.lots:
            price = quote_prices.get(lot.symbol)
            if price is not None and abs(lot.current_price - price) > 1e-9:
                lot.current_price = price
                changed = True
            updated_lots.append(lot)

        if not changed:
            return portfolio
        repository.replace_lots(portfolio_id, updated_lots)
        updated = rebuild_portfolio_positions(repository, portfolio_id)
    else:
        updated_positions: list[Position] = []
        changed = False
        for position in portfolio.positions:
            price = quote_prices.get(position.symbol)
            if price is not None and abs(position.price - price) > 1e-9:
                position.price = price
                position.unrealized_gain_loss = position.market_value - position.cost_basis
                changed = True
            updated_positions.append(position)

        if not changed:
            return portfolio
        updated = repository.update_positions(portfolio_id, updated_positions)

    create_valuation_snapshot(
        repository,
        portfolio_id,
        metadata={"event": "market_price_refresh", "tickers": sorted(quote_prices)},
    )
    return updated


def delete_position_lot(
    repository: Any,
    portfolio_id: str,
    lot_id: str,
) -> Portfolio:
    portfolio = _portfolio_or_error(repository, portfolio_id)
    remaining_lots = [lot for lot in portfolio.lots if lot.id != lot_id]
    if len(remaining_lots) == len(portfolio.lots):
        raise KeyError(f"Lot {lot_id!r} was not found.")
    repository.replace_lots(portfolio_id, remaining_lots)
    updated = rebuild_portfolio_positions(repository, portfolio_id)
    create_valuation_snapshot(
        repository,
        portfolio_id,
        metadata={"event": "lot_deleted", "lot_id": lot_id},
    )
    return updated


def delete_portfolio_position(
    repository: Any,
    portfolio_id: str,
    symbol: str,
) -> Portfolio:
    portfolio = _portfolio_or_error(repository, portfolio_id)
    normalized = str(symbol).strip().upper()
    if not normalized:
        raise ValueError("Position symbol is required.")

    matching_lots = [lot for lot in portfolio.lots if lot.symbol == normalized]
    if matching_lots:
        repository.replace_lots(portfolio_id, [lot for lot in portfolio.lots if lot.symbol != normalized])
        updated = rebuild_portfolio_positions(repository, portfolio_id)
    else:
        remaining_positions = [position for position in portfolio.positions if position.symbol != normalized]
        if len(remaining_positions) == len(portfolio.positions):
            raise KeyError(f"Position {normalized!r} was not found.")
        updated = repository.update_positions(portfolio_id, remaining_positions)

    create_valuation_snapshot(
        repository,
        portfolio_id,
        metadata={"event": "position_deleted", "symbol": normalized},
    )
    return updated


def update_portfolio_settings(
    repository: Any,
    portfolio_id: str,
    payload: dict[str, Any],
) -> PortfolioSettings:
    _portfolio_or_error(repository, portfolio_id)
    settings = repository.get_portfolio_settings(portfolio_id)
    if "risk_free_rate" in payload and payload["risk_free_rate"] is not None:
        settings.risk_free_rate = float(payload["risk_free_rate"])
    if "benchmark_symbols" in payload and payload["benchmark_symbols"] is not None:
        settings.benchmark_symbols = _normalize_unique_symbols(payload["benchmark_symbols"])
    if "cash_target_pct" in payload:
        value = payload["cash_target_pct"]
        settings.cash_target_pct = float(value) if value is not None else None
    if "risk_tolerance_score" in payload and payload["risk_tolerance_score"] is not None:
        score = int(payload["risk_tolerance_score"])
        if not 1 <= score <= 10:
            raise ValueError("risk_tolerance_score must be between 1 and 10.")
        settings.risk_tolerance_score = score
    if "bond_watchlist" in payload and payload["bond_watchlist"] is not None:
        settings.bond_watchlist = _normalize_unique_symbols(payload["bond_watchlist"])
    return repository.upsert_portfolio_settings(settings)


def create_valuation_snapshot(
    repository: Any,
    portfolio_id: str,
    *,
    as_of: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> PortfolioValuationSnapshot:
    portfolio = _portfolio_or_error(repository, portfolio_id)
    totals = portfolio_cost_basis_totals(portfolio)
    net_contributions = sum(
        cash_transaction_external_flow(transaction)
        for transaction in repository.list_cash_transactions(portfolio_id)
    )
    snapshot = PortfolioValuationSnapshot(
        id=str(uuid4()),
        portfolio_id=portfolio_id,
        as_of=as_of or datetime.now(timezone.utc),
        market_value=totals["market_value"],
        cash=totals["cash"],
        total_equity=totals["total_equity"],
        net_contributions=net_contributions,
        metadata=metadata or {},
    )
    return repository.add_valuation_snapshot(snapshot)


def rebuild_portfolio_positions(
    repository: Any,
    portfolio_id: str,
) -> Portfolio:
    portfolio = repository.get(portfolio_id)
    if portfolio is None:
        raise KeyError(f"Portfolio {portfolio_id!r} was not found.")

    grouped: defaultdict[str, list[PositionLot]] = defaultdict(list)
    for lot in portfolio.lots:
        if (lot.remaining_quantity or 0) > 0:
            grouped[lot.symbol].append(lot)

    positions: list[Position] = []
    for symbol, lots in sorted(grouped.items()):
        quantity = sum(lot.remaining_quantity or 0 for lot in lots)
        market_value = sum(lot.market_value for lot in lots)
        cost_basis = sum(lot.remaining_cost_basis for lot in lots)
        price = market_value / quantity if quantity else 0
        average_cost = cost_basis / quantity if quantity else 0
        asset_class = _dominant_asset_class(lots)
        positions.append(
            Position(
                symbol=symbol,
                quantity=quantity,
                price=price,
                asset_class=asset_class,
                cost_basis=cost_basis,
                average_cost=average_cost,
                unrealized_gain_loss=market_value - cost_basis,
                lots_count=len(lots),
            )
        )

    return repository.update_positions(portfolio_id, positions)


def portfolio_cost_basis_totals(portfolio: Portfolio) -> dict[str, float]:
    market_value = sum(position.market_value for position in portfolio.positions)
    cost_basis = sum(position.cost_basis for position in portfolio.positions)
    unrealized_gain_loss = market_value - cost_basis
    return {
        "market_value": market_value,
        "cost_basis": cost_basis,
        "cash": portfolio.cash,
        "total_equity": market_value + portfolio.cash,
        "unrealized_gain_loss": unrealized_gain_loss,
        "unrealized_gain_loss_pct": unrealized_gain_loss / cost_basis if cost_basis else 0,
    }


def cash_transaction_cash_delta(transaction: CashTransaction) -> float:
    if transaction.transaction_type in CASH_INFLOW_TYPES:
        return transaction.amount
    if transaction.transaction_type in CASH_OUTFLOW_TYPES:
        return -transaction.amount
    return 0


def cash_transaction_external_flow(transaction: CashTransaction) -> float:
    if transaction.transaction_type in EXTERNAL_CONTRIBUTION_TYPES:
        return transaction.amount
    if transaction.transaction_type in EXTERNAL_WITHDRAWAL_TYPES:
        return -transaction.amount
    return 0


def _apply_fifo_sale(
    lots: list[PositionLot],
    *,
    symbol: str,
    quantity: float,
    price: float,
    fees: float,
    fallback_asset_class: str,
) -> tuple[list[PositionLot], float, list[str], str]:
    remaining_to_sell = quantity
    consumed_cost_basis = 0.0
    consumed_lot_ids: list[str] = []
    asset_class = fallback_asset_class

    matching_lots = sorted(
        [lot for lot in lots if lot.symbol == symbol and (lot.remaining_quantity or 0) > 0],
        key=lambda lot: (lot.purchased_at, lot.id),
    )
    total_available = sum(lot.remaining_quantity or 0 for lot in matching_lots)
    if total_available + 1e-8 < quantity:
        raise ValueError(
            f"Cannot sell {quantity:g} {symbol}; only {total_available:g} share(s) are available."
        )

    for lot in matching_lots:
        if remaining_to_sell <= 1e-9:
            break
        available = lot.remaining_quantity or 0
        consumed = min(available, remaining_to_sell)
        if consumed <= 0:
            continue
        asset_class = lot.asset_class
        consumed_lot_ids.append(lot.id)
        cost_ratio = consumed / lot.quantity if lot.quantity else 0
        consumed_cost_basis += (consumed * lot.purchase_price) + (lot.fees * cost_ratio)
        lot.remaining_quantity = max(0.0, available - consumed)
        lot.current_price = price
        remaining_to_sell -= consumed

    if remaining_to_sell > 1e-8:
        available = quantity - remaining_to_sell
        raise ValueError(
            f"Cannot sell {quantity:g} {symbol}; only {available:g} share(s) are available."
        )

    for lot in lots:
        if lot.symbol == symbol and (lot.remaining_quantity or 0) > 0:
            lot.current_price = price

    net_proceeds = (quantity * price) - fees
    realized_gain_loss = net_proceeds - consumed_cost_basis
    return lots, realized_gain_loss, consumed_lot_ids, asset_class


def _dominant_asset_class(lots: list[PositionLot]) -> str:
    by_quantity: defaultdict[str, float] = defaultdict(float)
    for lot in lots:
        by_quantity[lot.asset_class] += lot.remaining_quantity or 0
    if not by_quantity:
        return "equity"
    return max(by_quantity.items(), key=lambda item: item[1])[0]


def _portfolio_or_error(repository: Any, portfolio_id: str) -> Portfolio:
    portfolio = repository.get(portfolio_id)
    if portfolio is None:
        raise KeyError(f"Portfolio {portfolio_id!r} was not found.")
    return portfolio


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _normalize_unique_symbols(symbols: list[Any]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        clean = str(symbol).strip().upper()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized
