from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4

from app.background.queue import redis_client_from_env
from app.connectors.market_data.limiter import acquire_provider_fetch_slot
from app.connectors.market_data.yfinance import (
    OptionChainSnapshot,
    OptionContract,
    OptionSuiteSnapshot,
    PriceHistorySnapshot,
    YFinanceMarketDataConnector,
)
from app.db.models import OptionChainHistorySnapshot


def fetch_option_chain_with_cache(
    ticker: str,
    expiry: date,
    *,
    provider_signature: str | None = None,
    connector: YFinanceMarketDataConnector | None = None,
    force: bool = False,
) -> tuple[OptionChainSnapshot | None, bool]:
    normalized = _normalize_ticker(ticker)
    if not normalized:
        return None, False
    if not force:
        cached = _get_cached_option_chain(normalized, expiry)
        if cached is not None:
            return cached, True

    connector = connector or YFinanceMarketDataConnector()
    acquire_provider_fetch_slot(
        provider=f"{connector.provider}-options",
        provider_signature=provider_signature,
    )
    snapshot = connector.fetch_option_chain(normalized, expiry)
    _set_cached_option_chain(snapshot)
    return snapshot, False



def fetch_option_suite_with_cache(
    ticker: str,
    expiry: date,
    *,
    provider_signature: str | None = None,
    connector: YFinanceMarketDataConnector | None = None,
    max_expiries: int = 4,
    history_period: str = "1y",
    force: bool = False,
    snapshot_repository: Any | None = None,
) -> tuple[OptionSuiteSnapshot | None, bool]:
    normalized = _normalize_ticker(ticker)
    if not normalized:
        return None, False
    if not force:
        cached = _get_cached_option_suite(normalized, expiry, max_expiries, history_period)
        if cached is not None:
            return cached, True

    connector = connector or YFinanceMarketDataConnector()
    acquire_provider_fetch_slot(
        provider=f"{connector.provider}-options-suite",
        provider_signature=provider_signature,
    )
    snapshot = connector.fetch_option_suite(
        normalized,
        expiry,
        max_expiries=max_expiries,
        history_period=history_period,
    )
    _set_cached_option_suite(snapshot, max_expiries=max_expiries, history_period=history_period)
    for chain in snapshot.surface_chains:
        _set_cached_option_chain(chain)
    if snapshot_repository is not None:
        persist_option_suite_snapshots(snapshot_repository, snapshot)
    return snapshot, False


def persist_option_suite_snapshots(repository: Any, suite: OptionSuiteSnapshot) -> list[OptionChainHistorySnapshot]:
    stored: list[OptionChainHistorySnapshot] = []
    spot = _latest_suite_spot(suite)
    seen_expiries: set[date] = set()
    for chain in ([suite.current_chain] if suite.current_chain is not None else []) + list(suite.surface_chains):
        if chain.expiry is None or chain.expiry in seen_expiries:
            continue
        seen_expiries.add(chain.expiry)
        payload = {
            "spot": spot,
            "chain": _snapshot_to_payload(chain),
            "suite_warnings": list(suite.warnings),
        }
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        record = OptionChainHistorySnapshot(
            id=str(uuid4()),
            ticker=suite.ticker.strip().upper(),
            provider=suite.provider,
            expiry=chain.expiry,
            fetched_at=suite.fetched_at,
            snapshot_hash=sha256(encoded.encode("utf-8")).hexdigest(),
            payload=payload,
        )
        stored.append(repository.add_option_chain_snapshot(record))
    repository.purge_option_chain_snapshots(before=datetime.now(timezone.utc) - timedelta(days=365))
    return stored


def _latest_suite_spot(suite: OptionSuiteSnapshot) -> float | None:
    history = suite.price_history
    if history is None or not history.prices:
        return None
    return float(history.prices[-1][1])

def _get_cached_option_chain(ticker: str, expiry: date) -> OptionChainSnapshot | None:
    try:
        raw = redis_client_from_env().get(_cache_key(ticker, expiry))
    except Exception:
        return None
    if not raw:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return _snapshot_from_json(str(raw))
    except Exception:
        return None


def _set_cached_option_chain(snapshot: OptionChainSnapshot) -> None:
    try:
        redis_client_from_env().setex(
            _cache_key(snapshot.ticker, snapshot.requested_expiry),
            _options_chain_cache_ttl_seconds(),
            _snapshot_to_json(snapshot),
        )
    except Exception:
        pass



def _get_cached_option_suite(
    ticker: str,
    expiry: date,
    max_expiries: int,
    history_period: str,
) -> OptionSuiteSnapshot | None:
    try:
        raw = redis_client_from_env().get(_suite_cache_key(ticker, expiry, max_expiries, history_period))
    except Exception:
        return None
    if not raw:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return _suite_from_json(str(raw))
    except Exception:
        return None


def _set_cached_option_suite(
    snapshot: OptionSuiteSnapshot,
    *,
    max_expiries: int,
    history_period: str,
) -> None:
    try:
        redis_client_from_env().setex(
            _suite_cache_key(snapshot.ticker, snapshot.requested_expiry, max_expiries, history_period),
            _options_chain_cache_ttl_seconds(),
            _suite_to_json(snapshot),
        )
    except Exception:
        pass


def _suite_to_json(snapshot: OptionSuiteSnapshot) -> str:
    payload = {
        "ticker": snapshot.ticker,
        "provider_ticker": snapshot.provider_ticker,
        "provider": snapshot.provider,
        "fetched_at": snapshot.fetched_at.isoformat(),
        "requested_expiry": snapshot.requested_expiry.isoformat(),
        "current_chain": _snapshot_to_payload(snapshot.current_chain) if snapshot.current_chain else None,
        "surface_chains": [_snapshot_to_payload(chain) for chain in snapshot.surface_chains],
        "price_history": _history_to_payload(snapshot.price_history) if snapshot.price_history else None,
        "warnings": snapshot.warnings,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _suite_from_json(raw: str) -> OptionSuiteSnapshot:
    payload = json.loads(raw)
    return OptionSuiteSnapshot(
        ticker=str(payload["ticker"]),
        provider_ticker=str(payload["provider_ticker"]),
        provider=str(payload.get("provider") or "yfinance"),
        fetched_at=datetime.fromisoformat(str(payload["fetched_at"]).replace("Z", "+00:00")),
        requested_expiry=date.fromisoformat(str(payload["requested_expiry"])),
        current_chain=_snapshot_from_payload(payload["current_chain"]) if payload.get("current_chain") else None,
        surface_chains=[_snapshot_from_payload(item) for item in payload.get("surface_chains", [])],
        price_history=_history_from_payload(payload["price_history"]) if payload.get("price_history") else None,
        warnings=[str(item) for item in payload.get("warnings", [])],
    )


def _history_to_payload(snapshot: PriceHistorySnapshot) -> dict[str, Any]:
    return {
        "ticker": snapshot.ticker,
        "provider_ticker": snapshot.provider_ticker,
        "provider": snapshot.provider,
        "fetched_at": snapshot.fetched_at.isoformat(),
        "prices": [[item_date.isoformat(), close] for item_date, close in snapshot.prices],
        "warnings": snapshot.warnings,
    }


def _history_from_payload(payload: dict[str, Any]) -> PriceHistorySnapshot:
    return PriceHistorySnapshot(
        ticker=str(payload["ticker"]),
        provider_ticker=str(payload["provider_ticker"]),
        provider=str(payload.get("provider") or "yfinance"),
        fetched_at=datetime.fromisoformat(str(payload["fetched_at"]).replace("Z", "+00:00")),
        prices=[(date.fromisoformat(str(item[0])), float(item[1])) for item in payload.get("prices", [])],
        warnings=[str(item) for item in payload.get("warnings", [])],
    )

def _snapshot_to_json(snapshot: OptionChainSnapshot) -> str:
    return json.dumps(_snapshot_to_payload(snapshot), separators=(",", ":"), sort_keys=True)


def _snapshot_to_payload(snapshot: OptionChainSnapshot) -> dict[str, Any]:
    return {
        "ticker": snapshot.ticker,
        "provider_ticker": snapshot.provider_ticker,
        "requested_expiry": snapshot.requested_expiry.isoformat(),
        "expiry": snapshot.expiry.isoformat() if snapshot.expiry else None,
        "provider": snapshot.provider,
        "fetched_at": snapshot.fetched_at.isoformat(),
        "calls": [_contract_to_dict(contract) for contract in snapshot.calls],
        "puts": [_contract_to_dict(contract) for contract in snapshot.puts],
        "warnings": snapshot.warnings,
    }


def _snapshot_from_json(raw: str) -> OptionChainSnapshot:
    return _snapshot_from_payload(json.loads(raw))


def _snapshot_from_payload(payload: dict[str, Any]) -> OptionChainSnapshot:
    return OptionChainSnapshot(
        ticker=str(payload["ticker"]),
        provider_ticker=str(payload["provider_ticker"]),
        requested_expiry=date.fromisoformat(str(payload["requested_expiry"])),
        expiry=date.fromisoformat(str(payload["expiry"])) if payload.get("expiry") else None,
        provider=str(payload.get("provider") or "yfinance"),
        fetched_at=datetime.fromisoformat(str(payload["fetched_at"]).replace("Z", "+00:00")),
        calls=[_contract_from_dict(item, "call") for item in payload.get("calls", [])],
        puts=[_contract_from_dict(item, "put") for item in payload.get("puts", [])],
        warnings=[str(item) for item in payload.get("warnings", [])],
    )


def _contract_to_dict(contract: OptionContract) -> dict[str, Any]:
    return {
        "option_type": contract.option_type,
        "strike": contract.strike,
        "contract_symbol": contract.contract_symbol,
        "last_price": contract.last_price,
        "bid": contract.bid,
        "ask": contract.ask,
        "implied_volatility": contract.implied_volatility,
        "volume": contract.volume,
        "open_interest": contract.open_interest,
        "in_the_money": contract.in_the_money,
    }


def _contract_from_dict(payload: dict[str, Any], fallback_type: str) -> OptionContract:
    return OptionContract(
        option_type=str(payload.get("option_type") or fallback_type),
        strike=float(payload["strike"]),
        contract_symbol=payload.get("contract_symbol"),
        last_price=_optional_float(payload.get("last_price")),
        bid=_optional_float(payload.get("bid")),
        ask=_optional_float(payload.get("ask")),
        implied_volatility=_optional_float(payload.get("implied_volatility")),
        volume=_optional_float(payload.get("volume")),
        open_interest=_optional_float(payload.get("open_interest")),
        in_the_money=payload.get("in_the_money"),
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return None if parsed != parsed else parsed


def _cache_key(ticker: str, expiry: date) -> str:
    return f"market-data:options:{_normalize_ticker(ticker)}:{expiry.isoformat()}"


def _suite_cache_key(ticker: str, expiry: date, max_expiries: int, history_period: str) -> str:
    clean_period = "".join(char for char in history_period.lower() if char.isalnum()) or "1y"
    return f"market-data:options-suite:{_normalize_ticker(ticker)}:{expiry.isoformat()}:{max_expiries}:{clean_period}"


def _normalize_ticker(ticker: str) -> str:
    return str(ticker).strip().upper()


def _options_chain_cache_ttl_seconds() -> int:
    return int(os.getenv("OPTIONS_CHAIN_CACHE_TTL_SECONDS", "3600"))
