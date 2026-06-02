from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.connectors.market_data.base import MarketDataConnector
from app.connectors.market_data.cache import create_market_data_cache, market_data_cache_ttl_seconds
from app.connectors.market_data.limiter import acquire_provider_fetch_slot
from app.connectors.market_data.yfinance import YFinanceMarketDataConnector
from app.db.models import MarketQuote, Portfolio
from app.db.repository import create_portfolio_repository


def portfolio_tickers(portfolio: Portfolio) -> list[str]:
    tickers: list[str] = []
    seen: set[str] = set()
    for position in portfolio.positions:
        ticker = position.symbol.strip().upper()
        if ticker and ticker not in seen:
            tickers.append(ticker)
            seen.add(ticker)
    return tickers


def market_quotes_to_heatmap_data(quotes: list[MarketQuote]) -> list[dict[str, Any]]:
    return [
        {
            "ticker": quote.ticker,
            "price": quote.price,
            "previous_close": quote.previous_close,
            "daily_return_pct": quote.daily_return_pct,
            "sector": quote.sector,
            "industry": quote.industry,
        }
        for quote in quotes
    ]


def get_cached_market_data_for_portfolio(
    portfolio: Portfolio,
    repository: Any | None = None,
    *,
    max_age_seconds: int | None = None,
    cache: Any | None = None,
) -> list[MarketQuote]:
    repository = repository or create_portfolio_repository()
    tickers = portfolio_tickers(portfolio)
    if not tickers:
        return []

    redis_quotes: list[MarketQuote] = []
    try:
        quote_cache = cache or create_market_data_cache()
        redis_quotes = quote_cache.get_many(tickers)
    except Exception:
        redis_quotes = []

    by_ticker = {quote.ticker: quote for quote in redis_quotes}
    missing = [ticker for ticker in tickers if ticker not in by_ticker]
    if missing:
        max_age = max_age_seconds if max_age_seconds is not None else market_data_cache_ttl_seconds()
        db_quotes = repository.get_market_quotes(missing, max_age_seconds=max_age)
        by_ticker.update({quote.ticker: quote for quote in db_quotes})
        try:
            if db_quotes:
                (cache or create_market_data_cache()).set_many(
                    db_quotes,
                    ttl_seconds=market_data_cache_ttl_seconds(),
                )
        except Exception:
            pass
    return [by_ticker[ticker] for ticker in tickers if ticker in by_ticker]


def refresh_market_data_quotes(
    tickers: list[str],
    repository: Any | None = None,
    *,
    connector: MarketDataConnector | None = None,
    cache: Any | None = None,
    force: bool = False,
    wait_for_rate_limit: bool = False,
    provider_signature: str | None = None,
    rate_limiter: Any | None = None,
    sleep: Callable[[float], None] | None = None,
) -> list[MarketQuote]:
    repository = repository or create_portfolio_repository()
    connector = connector or YFinanceMarketDataConnector()
    cache = cache or create_market_data_cache()
    normalized = _normalize_tickers(tickers)
    if not normalized:
        return []

    ttl = market_data_cache_ttl_seconds()
    cached = cache.get_many(normalized) if not force else []
    cached_by_ticker = {quote.ticker: quote for quote in cached}
    missing = [ticker for ticker in normalized if ticker not in cached_by_ticker]

    fetched: list[MarketQuote] = []
    if missing:
        acquire_provider_fetch_slot(
            provider=connector.provider,
            provider_signature=provider_signature,
            limiter=rate_limiter,
            wait=wait_for_rate_limit,
            sleep=sleep,
        )
        fetched = connector.fetch_quotes(missing)
        repository.upsert_market_quotes(fetched)
        cache.set_many(fetched, ttl_seconds=ttl)

    merged = {quote.ticker: quote for quote in cached}
    merged.update({quote.ticker: quote for quote in fetched})
    return [merged[ticker] for ticker in normalized if ticker in merged]


def _normalize_tickers(tickers: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        clean = str(ticker).strip().upper()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized
