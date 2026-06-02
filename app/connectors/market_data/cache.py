from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from app.background.queue import redis_client_from_env
from app.db.models import MarketQuote


class InMemoryMarketDataCache:
    def __init__(self) -> None:
        self._quotes: dict[str, MarketQuote] = {}

    def get_many(self, tickers: list[str]) -> list[MarketQuote]:
        return [self._quotes[ticker] for ticker in _normalize_tickers(tickers) if ticker in self._quotes]

    def set_many(self, quotes: list[MarketQuote], *, ttl_seconds: int) -> None:
        for quote in quotes:
            self._quotes[quote.ticker.strip().upper()] = quote


class RedisMarketDataCache:
    def __init__(self, *, client: Any | None = None, key_prefix: str = "market-data:quote") -> None:
        self.client = client or redis_client_from_env()
        self.key_prefix = key_prefix

    def get_many(self, tickers: list[str]) -> list[MarketQuote]:
        normalized = _normalize_tickers(tickers)
        if not normalized:
            return []
        values = self.client.mget([self._key(ticker) for ticker in normalized])
        quotes: list[MarketQuote] = []
        for value in values:
            if not value:
                continue
            quotes.append(_quote_from_json(value))
        return quotes

    def set_many(self, quotes: list[MarketQuote], *, ttl_seconds: int) -> None:
        if not quotes:
            return
        pipe = self.client.pipeline()
        for quote in quotes:
            pipe.setex(self._key(quote.ticker), ttl_seconds, _quote_to_json(quote))
        pipe.execute()

    def _key(self, ticker: str) -> str:
        return f"{self.key_prefix}:{ticker.strip().upper()}"


def create_market_data_cache() -> RedisMarketDataCache:
    return RedisMarketDataCache()


def market_quote_to_dict(quote: MarketQuote) -> dict[str, Any]:
    return {
        "ticker": quote.ticker,
        "provider": quote.provider,
        "price": quote.price,
        "previous_close": quote.previous_close,
        "daily_return_pct": quote.daily_return_pct,
        "currency": quote.currency,
        "sector": quote.sector,
        "industry": quote.industry,
        "fetched_at": quote.fetched_at.isoformat(),
        "updated_at": quote.updated_at.isoformat(),
    }


def _quote_to_json(quote: MarketQuote) -> str:
    return json.dumps(market_quote_to_dict(quote), separators=(",", ":"), sort_keys=True)


def _quote_from_json(raw: str | bytes) -> MarketQuote:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    payload = json.loads(raw)
    return MarketQuote(
        ticker=str(payload["ticker"]),
        provider=str(payload.get("provider") or "cache"),
        price=float(payload["price"]),
        previous_close=float(payload["previous_close"]) if payload.get("previous_close") is not None else None,
        daily_return_pct=float(payload["daily_return_pct"]) if payload.get("daily_return_pct") is not None else None,
        currency=payload.get("currency"),
        sector=payload.get("sector"),
        industry=payload.get("industry"),
        fetched_at=datetime.fromisoformat(str(payload["fetched_at"]).replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(str(payload["updated_at"]).replace("Z", "+00:00")),
    )


def market_data_cache_ttl_seconds() -> int:
    return int(os.getenv("MARKET_DATA_CACHE_TTL_SECONDS", "900"))


def _normalize_tickers(tickers: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        clean = str(ticker).strip().upper()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized
