from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.background.queue import redis_client_from_env
from app.connectors.market_data.limiter import acquire_provider_fetch_slot
from app.connectors.market_data.yfinance import PriceHistoryPoint, PriceHistorySeries, YFinanceMarketDataConnector


@dataclass(frozen=True, slots=True)
class PriceHistorySpec:
    range_name: str
    period: str
    interval: str
    ttl_seconds: int


@dataclass(frozen=True, slots=True)
class PriceHistoryBundle:
    range_name: str
    period: str
    interval: str
    series: list[PriceHistorySeries]
    missing_tickers: list[str]


_HISTORY_SPECS = {
    "day": PriceHistorySpec("day", "5d", "5m", 15 * 60),
    "week": PriceHistorySpec("week", "60d", "15m", 30 * 60),
    "month": PriceHistorySpec("month", "6mo", "1d", 6 * 60 * 60),
    "ytd": PriceHistorySpec("ytd", "2y", "1d", 6 * 60 * 60),
    "year": PriceHistorySpec("year", "2y", "1d", 6 * 60 * 60),
    "five_year": PriceHistorySpec("five_year", "5y", "1d", 12 * 60 * 60),
    "max": PriceHistorySpec("max", "max", "1d", 24 * 60 * 60),
}


class InMemoryPriceHistoryCache:
    def __init__(self) -> None:
        self._series: dict[str, PriceHistorySeries] = {}

    def get_many(self, tickers: list[str], *, period: str, interval: str) -> list[PriceHistorySeries]:
        return [
            self._series[key]
            for ticker in _normalize_tickers(tickers)
            if (key := _history_cache_key(ticker, period, interval)) in self._series
        ]

    def set_many(self, series: list[PriceHistorySeries], *, ttl_seconds: int) -> None:
        for item in series:
            self._series[_history_cache_key(item.ticker, item.period, item.interval)] = item


class RedisPriceHistoryCache:
    def __init__(self, *, client: Any | None = None, key_prefix: str = "market-data:history") -> None:
        self.client = client or redis_client_from_env()
        self.key_prefix = key_prefix

    def get_many(self, tickers: list[str], *, period: str, interval: str) -> list[PriceHistorySeries]:
        normalized = _normalize_tickers(tickers)
        if not normalized:
            return []
        keys = [self._key(ticker, period, interval) for ticker in normalized]
        values = self.client.mget(keys)
        series: list[PriceHistorySeries] = []
        for value in values:
            if not value:
                continue
            try:
                series.append(_series_from_json(value))
            except Exception:
                continue
        return series

    def set_many(self, series: list[PriceHistorySeries], *, ttl_seconds: int) -> None:
        if not series:
            return
        pipe = self.client.pipeline()
        for item in series:
            pipe.setex(self._key(item.ticker, item.period, item.interval), ttl_seconds, _series_to_json(item))
        pipe.execute()

    def _key(self, ticker: str, period: str, interval: str) -> str:
        return f"{self.key_prefix}:{_history_cache_key(ticker, period, interval)}"


def create_price_history_cache() -> RedisPriceHistoryCache:
    return RedisPriceHistoryCache()


def history_spec_for_range(range_name: str) -> PriceHistorySpec:
    return _HISTORY_SPECS.get(str(range_name or "max").strip().lower(), _HISTORY_SPECS["max"])


def get_cached_price_history(
    tickers: list[str],
    *,
    range_name: str,
    cache: Any | None = None,
) -> PriceHistoryBundle:
    spec = history_spec_for_range(range_name)
    normalized = _normalize_tickers(tickers)
    if not normalized:
        return PriceHistoryBundle(spec.range_name, spec.period, spec.interval, [], [])
    cache = cache or create_price_history_cache()
    cached = cache.get_many(normalized, period=spec.period, interval=spec.interval)
    cached_by_ticker = {item.ticker: item for item in cached}
    missing = [ticker for ticker in normalized if ticker not in cached_by_ticker]
    return PriceHistoryBundle(
        range_name=spec.range_name,
        period=spec.period,
        interval=spec.interval,
        series=[cached_by_ticker[ticker] for ticker in normalized if ticker in cached_by_ticker],
        missing_tickers=missing,
    )


def refresh_price_history(
    tickers: list[str],
    *,
    range_name: str,
    connector: YFinanceMarketDataConnector | None = None,
    cache: Any | None = None,
    force: bool = False,
    wait_for_rate_limit: bool = False,
    provider_signature: str | None = None,
    rate_limiter: Any | None = None,
    sleep: Any | None = None,
) -> PriceHistoryBundle:
    spec = history_spec_for_range(range_name)
    normalized = _normalize_tickers(tickers)
    if not normalized:
        return PriceHistoryBundle(spec.range_name, spec.period, spec.interval, [], [])

    connector = connector or YFinanceMarketDataConnector()
    cache = cache or create_price_history_cache()
    cached = [] if force else cache.get_many(normalized, period=spec.period, interval=spec.interval)
    cached_by_ticker = {item.ticker: item for item in cached}
    missing = [ticker for ticker in normalized if ticker not in cached_by_ticker]

    fetched: list[PriceHistorySeries] = []
    if missing:
        acquire_provider_fetch_slot(
            provider=connector.provider,
            provider_signature=provider_signature,
            limiter=rate_limiter,
            wait=wait_for_rate_limit,
            sleep=sleep,
        )
        fetched = connector.fetch_price_history(missing, period=spec.period, interval=spec.interval)
        cache.set_many(fetched, ttl_seconds=spec.ttl_seconds)

    merged = {item.ticker: item for item in cached}
    merged.update({item.ticker: item for item in fetched})
    return PriceHistoryBundle(
        range_name=spec.range_name,
        period=spec.period,
        interval=spec.interval,
        series=[merged[ticker] for ticker in normalized if ticker in merged],
        missing_tickers=[ticker for ticker in normalized if ticker not in merged or not merged[ticker].points],
    )


def price_history_to_dict(series: PriceHistorySeries) -> dict[str, Any]:
    return {
        "ticker": series.ticker,
        "provider_ticker": series.provider_ticker,
        "provider": series.provider,
        "period": series.period,
        "interval": series.interval,
        "fetched_at": series.fetched_at.isoformat(),
        "points": [
            {"as_of": point.as_of.isoformat(), "close": point.close}
            for point in series.points
        ],
        "warnings": list(series.warnings),
    }


def _series_to_json(series: PriceHistorySeries) -> str:
    return json.dumps(price_history_to_dict(series), separators=(",", ":"), sort_keys=True)


def _series_from_json(raw: str | bytes) -> PriceHistorySeries:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    payload = json.loads(raw)
    return PriceHistorySeries(
        ticker=str(payload["ticker"]).strip().upper(),
        provider_ticker=str(payload.get("provider_ticker") or payload["ticker"]),
        provider=str(payload.get("provider") or "yfinance"),
        period=str(payload.get("period") or "max"),
        interval=str(payload.get("interval") or "1d"),
        fetched_at=_parse_datetime(payload.get("fetched_at")),
        points=[
            PriceHistoryPoint(as_of=_parse_datetime(item["as_of"]), close=float(item["close"]))
            for item in payload.get("points", [])
            if item.get("close") is not None
        ],
        warnings=[str(item) for item in payload.get("warnings", [])],
    )


def _parse_datetime(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        from datetime import timezone

        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _history_cache_key(ticker: str, period: str, interval: str) -> str:
    clean_ticker = "".join(char for char in str(ticker).strip().upper() if char.isalnum() or char in {"_", "-"})
    clean_period = "".join(char for char in str(period).strip().lower() if char.isalnum())
    clean_interval = "".join(char for char in str(interval).strip().lower() if char.isalnum())
    return f"{clean_ticker}:{clean_period}:{clean_interval}"


def _normalize_tickers(tickers: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        clean = str(ticker).strip().upper()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized
