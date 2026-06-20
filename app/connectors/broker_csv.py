from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from io import StringIO
from math import isfinite

from app.db.models import Position


MAX_IMPORT_ROWS = 50_000
CRYPTO_QUOTE_ASSETS = {"USD", "USDC", "USDT", "EUR", "GBP"}


class BrokerCSVError(ValueError):
    """Raised when an uploaded brokerage export cannot be interpreted safely."""


@dataclass(slots=True)
class BrokerCSVImport:
    source: str
    positions: list[Position]
    warnings: list[str] = field(default_factory=list)
    rows_read: int = 0


@dataclass(slots=True)
class _PositionRow:
    symbol: str
    quantity: float
    price: float
    asset_class: str
    cost_basis: float


@dataclass(slots=True)
class _CryptoLedger:
    quantity: float = 0.0
    cost_basis: float = 0.0
    latest_price: float = 0.0


def parse_brokerage_csv(decoded: str) -> BrokerCSVImport:
    """Auto-detect and parse a supported brokerage positions/transaction CSV."""
    if not decoded.strip():
        raise BrokerCSVError("The uploaded CSV is empty.")

    rows = _read_rows(decoded)
    header_index = _find_header_index(rows)
    if header_index is None:
        raise BrokerCSVError(
            "No supported brokerage header was found. Export a positions CSV from Fidelity, "
            "E*TRADE, or Schwab, a transaction-history CSV from Coinbase, or use columns "
            "symbol, quantity, and price."
        )

    headers = rows[header_index]
    records = _records(headers, rows[header_index + 1 :])
    normalized_headers = {_key(header) for header in headers}
    source = _detect_source(normalized_headers)
    if source == "coinbase":
        return _parse_coinbase(records)
    return _parse_positions(source, records)


def _read_rows(decoded: str) -> list[list[str]]:
    sample = decoded[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    rows: list[list[str]] = []
    for index, row in enumerate(csv.reader(StringIO(decoded), delimiter=delimiter), start=1):
        if index > MAX_IMPORT_ROWS + 50:
            raise BrokerCSVError(f"CSV exceeds the {MAX_IMPORT_ROWS:,}-row import limit.")
        if any(str(value).strip() for value in row):
            rows.append([str(value).strip() for value in row])
    return rows


def _find_header_index(rows: list[list[str]]) -> int | None:
    for index, row in enumerate(rows[:50]):
        keys = {_key(value) for value in row if value}
        coinbase = {"transactiontype", "asset", "quantitytransacted"}.issubset(keys)
        position = bool(keys & SYMBOL_FIELDS) and bool(keys & QUANTITY_FIELDS) and bool(
            keys & (PRICE_FIELDS | MARKET_VALUE_FIELDS | COST_BASIS_FIELDS | AVERAGE_COST_FIELDS)
        )
        if coinbase or position:
            return index
    return None


def _records(headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    unique_headers: list[str] = []
    seen: dict[str, int] = defaultdict(int)
    for index, header in enumerate(headers):
        key = _key(header) or f"column{index + 1}"
        seen[key] += 1
        unique_headers.append(key if seen[key] == 1 else f"{key}{seen[key]}")
    return [dict(zip(unique_headers, row, strict=False)) for row in rows]


def _detect_source(headers: set[str]) -> str:
    if {"transactiontype", "asset", "quantitytransacted"}.issubset(headers):
        return "coinbase"
    if "accountnumber" in headers and headers & {"currentvalue", "costbasistotal"}:
        return "fidelity"
    if headers & {"pricepaid", "qty"} and headers & {"lastprice", "marketvalue"}:
        return "etrade"
    if headers & {"costshare", "positiondollarvalue", "daychange"}:
        return "schwab"
    return "generic"


def _parse_positions(source: str, records: list[dict[str, str]]) -> BrokerCSVImport:
    parsed: list[_PositionRow] = []
    warnings: list[str] = []
    skipped = 0

    for line_number, record in enumerate(records, start=2):
        symbol = _normalize_symbol(_first(record, SYMBOL_FIELDS))
        quantity = _number(_first(record, QUANTITY_FIELDS))
        if _is_summary_row(symbol, record):
            continue
        if not symbol or quantity is None or quantity <= 0:
            skipped += 1
            continue

        price = _number(_first(record, PRICE_FIELDS))
        market_value = _number(_first(record, MARKET_VALUE_FIELDS))
        cost_basis = _number(_first(record, COST_BASIS_FIELDS))
        average_cost = _number(_first(record, AVERAGE_COST_FIELDS))
        if (price is None or price <= 0) and market_value is not None:
            price = abs(market_value / quantity)
        if (price is None or price <= 0) and average_cost is not None:
            price = abs(average_cost)
            warnings.append(f"{symbol}: current price was unavailable; average cost is used until quotes refresh.")
        if price is None or price <= 0:
            warnings.append(f"Line {line_number} ({symbol}) skipped because no usable price or market value was present.")
            continue

        if cost_basis is None or cost_basis < 0:
            cost_basis = quantity * (average_cost if average_cost is not None and average_cost > 0 else price)
        parsed.append(
            _PositionRow(
                symbol=symbol,
                quantity=quantity,
                price=price,
                asset_class=_asset_class(_first(record, ASSET_CLASS_FIELDS), symbol),
                cost_basis=cost_basis,
            )
        )

    positions = _aggregate_positions(parsed)
    if skipped:
        warnings.append(f"Skipped {skipped} blank, total, cash-only, or non-long position row(s).")
    if source in {"fidelity", "etrade", "schwab"}:
        warnings.append(
            "This positions export is a current snapshot. Cost basis is retained when supplied, but purchase dates require a lot-level export or manual entry."
        )
    return BrokerCSVImport(source=source, positions=positions, warnings=_unique(warnings), rows_read=len(records))


def _parse_coinbase(records: list[dict[str, str]]) -> BrokerCSVImport:
    ledgers: dict[str, _CryptoLedger] = defaultdict(_CryptoLedger)
    warnings: list[str] = []
    skipped = 0

    for record in records:
        action = _first(record, {"transactiontype", "type"}).strip().lower()
        asset = _normalize_crypto_asset(_first(record, {"asset"}))
        quantity = _number(_first(record, {"quantitytransacted", "quantity"}))
        spot = _number(_first(record, {"spotpriceattransaction", "priceattransaction", "usdspotpriceattransaction"}))
        total = _number(_first(record, {"totalinclusiveoffeesandorspread", "usdtotalinclusiveoffees", "total"}))

        if "convert" in action:
            converted = _parse_conversion(_first(record, {"notes"}))
            if converted is None:
                skipped += 1
                continue
            source_asset, source_quantity, target_asset, target_quantity = converted
            removed_basis = _remove_crypto(ledgers[source_asset], source_quantity)
            target = ledgers[target_asset]
            target.quantity += target_quantity
            target.cost_basis += removed_basis
            if target_quantity > 0 and removed_basis > 0:
                target.latest_price = removed_basis / target_quantity
            continue

        if not asset or asset in CRYPTO_QUOTE_ASSETS or quantity is None or quantity == 0:
            continue
        quantity = abs(quantity)
        ledger = ledgers[asset]
        if spot is not None and spot > 0:
            ledger.latest_price = spot

        if _action_matches(action, "sell", "send", "withdraw"):
            _remove_crypto(ledger, quantity)
        elif _action_matches(action, "buy", "receive", "reward", "earn", "staking", "interest", "deposit"):
            added_basis = abs(total) if total is not None and total != 0 else quantity * (spot or 0)
            ledger.quantity += quantity
            ledger.cost_basis += added_basis
        else:
            skipped += 1

    rows: list[_PositionRow] = []
    for asset, ledger in ledgers.items():
        if ledger.quantity <= 1e-12:
            continue
        symbol = f"{asset}-USD"
        price = ledger.latest_price or (ledger.cost_basis / ledger.quantity if ledger.cost_basis > 0 else 0)
        if price <= 0:
            warnings.append(f"{asset} skipped because its transaction history contained no usable USD price.")
            continue
        rows.append(
            _PositionRow(
                symbol=symbol,
                quantity=ledger.quantity,
                price=price,
                asset_class="crypto",
                cost_basis=max(ledger.cost_basis, 0),
            )
        )

    if skipped:
        warnings.append(f"Skipped {skipped} unsupported or ambiguous Coinbase transaction row(s).")
    warnings.append(
        "Coinbase holdings were reconstructed from transaction history. Transfers or activity outside the export can make balances and cost basis incomplete; verify the imported quantities."
    )
    return BrokerCSVImport(source="coinbase", positions=_aggregate_positions(rows), warnings=_unique(warnings), rows_read=len(records))


def _remove_crypto(ledger: _CryptoLedger, quantity: float) -> float:
    removed = min(quantity, max(ledger.quantity, 0))
    if ledger.quantity <= 0 or removed <= 0:
        return 0
    removed_basis = ledger.cost_basis * (removed / ledger.quantity)
    ledger.quantity -= removed
    ledger.cost_basis = max(ledger.cost_basis - removed_basis, 0)
    return removed_basis


def _parse_conversion(notes: str) -> tuple[str, float, str, float] | None:
    match = re.search(
        r"converted?\s+([\d,.]+)\s+([A-Za-z0-9]+)\s+to\s+([\d,.]+)\s+([A-Za-z0-9]+)",
        notes,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    source_quantity = _number(match.group(1))
    target_quantity = _number(match.group(3))
    if not source_quantity or not target_quantity:
        return None
    return (
        _normalize_crypto_asset(match.group(2)),
        source_quantity,
        _normalize_crypto_asset(match.group(4)),
        target_quantity,
    )


def _aggregate_positions(rows: list[_PositionRow]) -> list[Position]:
    grouped: dict[str, list[_PositionRow]] = defaultdict(list)
    for row in rows:
        grouped[row.symbol].append(row)

    positions: list[Position] = []
    for symbol in sorted(grouped):
        items = grouped[symbol]
        quantity = sum(item.quantity for item in items)
        cost_basis = sum(item.cost_basis for item in items)
        market_value = sum(item.quantity * item.price for item in items)
        if quantity <= 0:
            continue
        price = market_value / quantity
        average_cost = cost_basis / quantity if cost_basis > 0 else price
        positions.append(
            Position(
                symbol=symbol,
                quantity=quantity,
                price=price,
                asset_class=items[0].asset_class,
                cost_basis=cost_basis,
                average_cost=average_cost,
                unrealized_gain_loss=market_value - cost_basis,
                lots_count=len(items),
            )
        )
    return positions


def _first(record: dict[str, str], aliases: set[str]) -> str:
    for alias in sorted(aliases, key=lambda value: FIELD_PRIORITY.get(value, 10_000)):
        value = record.get(alias)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _number(value: object) -> float | None:
    text = str(value or "").strip()
    if not text or text.lower() in {"--", "n/a", "na", "none", "null"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    cleaned = re.sub(r"[^0-9eE+\-.]", "", text)
    if cleaned in {"", "+", "-", "."}:
        return None
    try:
        number = float(cleaned)
    except ValueError:
        return None
    if not isfinite(number):
        return None
    return -abs(number) if negative else number


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _normalize_symbol(value: str) -> str:
    symbol = value.strip().upper().replace("/", "-")
    symbol = re.sub(r"\*+$", "", symbol)
    if symbol in {"", "--", "N/A", "CASH", "TOTAL", "ACCOUNT TOTAL"}:
        return ""
    if re.fullmatch(r"[A-Z]{1,6}\.[A-Z]", symbol):
        symbol = symbol.replace(".", "_")
    return symbol[:20]


def _normalize_crypto_asset(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.strip().upper())[:12]


def _is_summary_row(symbol: str, record: dict[str, str]) -> bool:
    description = _first(record, {"description", "name", "securitydescription"}).lower()
    return not symbol or "account total" in description or description in {"total", "pending activity"}


def _asset_class(value: str, symbol: str) -> str:
    text = value.strip().lower()
    if "bond" in text or "fixed income" in text:
        return "bond"
    if "option" in text:
        return "option"
    if "crypto" in text:
        return "crypto"
    if "cash" in text or "money market" in text:
        return "cash"
    if "fund" in text or "etf" in text or "mutual" in text:
        return "fund"
    if symbol.endswith("-USD"):
        return "crypto"
    return "equity"


def _action_matches(action: str, *needles: str) -> bool:
    return any(needle in action for needle in needles)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


SYMBOL_FIELDS = {"symbol", "ticker", "securitysymbol"}
QUANTITY_FIELDS = {"quantity", "shares", "qty", "qtynumber", "positionquantity"}
PRICE_FIELDS = {
    "price",
    "currentprice",
    "lastprice",
    "lastpricedollar",
    "mostrecentprice",
    "shareprice",
    "marketprice",
}
MARKET_VALUE_FIELDS = {
    "marketvalue",
    "marketvaluedollar",
    "currentvalue",
    "mostrecentvalue",
    "positiondollarvalue",
    "value",
}
COST_BASIS_FIELDS = {"costbasis", "costbasistotal", "totalcostbasis", "cost", "costdollar"}
AVERAGE_COST_FIELDS = {
    "averagecostbasis",
    "averagecost",
    "costshare",
    "costpershare",
    "pricepaid",
    "pricepaiddollar",
}
ASSET_CLASS_FIELDS = {"assetclass", "investmenttype", "securitytype", "type", "positiontype"}

FIELD_PRIORITY = {
    name: index
    for index, name in enumerate(
        (
            "symbol",
            "ticker",
            "securitysymbol",
            "quantity",
            "shares",
            "qty",
            "positionquantity",
            "currentprice",
            "lastprice",
            "lastpricedollar",
            "mostrecentprice",
            "marketprice",
            "price",
            "currentvalue",
            "marketvalue",
            "marketvaluedollar",
            "positiondollarvalue",
            "costbasistotal",
            "totalcostbasis",
            "costbasis",
            "averagecostbasis",
            "averagecost",
            "costshare",
            "pricepaid",
            "assetclass",
            "investmenttype",
            "securitytype",
            "positiontype",
            "type",
        )
    )
}
