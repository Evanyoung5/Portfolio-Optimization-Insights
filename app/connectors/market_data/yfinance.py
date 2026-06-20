from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from math import isfinite
from typing import Any

from app.db.models import MarketQuote


@dataclass(frozen=True, slots=True)
class OptionContract:
    option_type: str
    strike: float
    contract_symbol: str | None = None
    last_price: float | None = None
    bid: float | None = None
    ask: float | None = None
    implied_volatility: float | None = None
    volume: float | None = None
    open_interest: float | None = None
    in_the_money: bool | None = None


@dataclass(frozen=True, slots=True)
class OptionChainSnapshot:
    ticker: str
    provider_ticker: str
    requested_expiry: date
    expiry: date | None
    provider: str
    fetched_at: datetime
    calls: list[OptionContract]
    puts: list[OptionContract]
    warnings: list[str]






@dataclass(frozen=True, slots=True)
class PriceHistoryPoint:
    as_of: datetime
    close: float


@dataclass(frozen=True, slots=True)
class PriceHistorySeries:
    ticker: str
    provider_ticker: str
    provider: str
    period: str
    interval: str
    fetched_at: datetime
    points: list[PriceHistoryPoint]
    warnings: list[str]

@dataclass(frozen=True, slots=True)
class PriceHistorySnapshot:
    ticker: str
    provider_ticker: str
    provider: str
    fetched_at: datetime
    prices: list[tuple[date, float]]
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class OptionSuiteSnapshot:
    ticker: str
    provider_ticker: str
    provider: str
    fetched_at: datetime
    requested_expiry: date
    current_chain: OptionChainSnapshot | None
    surface_chains: list[OptionChainSnapshot]
    price_history: PriceHistorySnapshot | None
    warnings: list[str]

class YFinanceMarketDataConnector:
    provider = "yfinance"

    def fetch_quotes(self, tickers: list[str]) -> list[MarketQuote]:
        normalized = _normalize_tickers(tickers)
        if not normalized:
            return []
        try:
            import yfinance as yf
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "yfinance market data requires the 'yfinance' package. Install dependencies or run through Docker."
            ) from exc

        provider_by_ticker = {ticker: _provider_ticker(ticker) for ticker in normalized}
        provider_tickers = list(dict.fromkeys(provider_by_ticker.values()))
        raw = yf.download(
            tickers=provider_tickers,
            period="2d",
            interval="5m",
            group_by="ticker",
            auto_adjust=False,
            prepost=False,
            progress=False,
            threads=True,
        )
        return _quotes_from_download(raw, normalized, provider=self.provider, provider_by_ticker=provider_by_ticker)


    def fetch_price_history(
        self,
        tickers: list[str],
        *,
        period: str = "5y",
        interval: str = "1d",
    ) -> list[PriceHistorySeries]:
        normalized = _normalize_tickers(tickers)
        if not normalized:
            return []
        try:
            import yfinance as yf
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "yfinance price history requires the 'yfinance' package. Install dependencies or run through Docker."
            ) from exc

        provider_by_ticker = {ticker: _provider_ticker(ticker) for ticker in normalized}
        provider_tickers = list(dict.fromkeys(provider_by_ticker.values()))
        fetched_at = datetime.now(timezone.utc)
        raw = yf.download(
            tickers=provider_tickers,
            period=period,
            interval=interval,
            group_by="ticker",
            auto_adjust=True,
            prepost=False,
            progress=False,
            threads=True,
        )

        series: list[PriceHistorySeries] = []
        for ticker in normalized:
            provider_ticker = provider_by_ticker[ticker]
            points = _price_history_points_from_download(raw, provider_ticker)
            if not points and provider_ticker != ticker:
                points = _price_history_points_from_download(raw, ticker)
            warnings = [] if points else [f"Historical prices were unavailable for {ticker}."]
            series.append(
                PriceHistorySeries(
                    ticker=ticker,
                    provider_ticker=provider_ticker,
                    provider=self.provider,
                    period=period,
                    interval=interval,
                    fetched_at=fetched_at,
                    points=points,
                    warnings=warnings,
                )
            )
        return series

    def fetch_option_chain(self, ticker: str, expiry: date) -> OptionChainSnapshot:
        normalized = _normalize_tickers([ticker])
        if not normalized:
            raise ValueError("ticker is required.")
        normalized_ticker = normalized[0]
        provider_ticker = _provider_ticker(normalized_ticker)
        try:
            import yfinance as yf
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "yfinance option chains require the 'yfinance' package. Install dependencies or run through Docker."
            ) from exc

        fetched_at = datetime.now(timezone.utc)
        ticker_obj = yf.Ticker(provider_ticker)
        expiries = list(getattr(ticker_obj, "options", []) or [])
        selected_expiry, warnings = _select_option_expiry(expiry, expiries)
        if selected_expiry is None:
            warnings.append(f"No yfinance option expirations were available for {normalized_ticker}.")
            return OptionChainSnapshot(
                ticker=normalized_ticker,
                provider_ticker=provider_ticker,
                requested_expiry=expiry,
                expiry=None,
                provider=self.provider,
                fetched_at=fetched_at,
                calls=[],
                puts=[],
                warnings=warnings,
            )

        chain = ticker_obj.option_chain(selected_expiry.isoformat())
        return OptionChainSnapshot(
            ticker=normalized_ticker,
            provider_ticker=provider_ticker,
            requested_expiry=expiry,
            expiry=selected_expiry,
            provider=self.provider,
            fetched_at=fetched_at,
            calls=_contracts_from_frame(getattr(chain, "calls", None), "call"),
            puts=_contracts_from_frame(getattr(chain, "puts", None), "put"),
            warnings=warnings,
        )


    def fetch_option_suite(
        self,
        ticker: str,
        expiry: date,
        *,
        max_expiries: int = 4,
        history_period: str = "1y",
    ) -> OptionSuiteSnapshot:
        normalized = _normalize_tickers([ticker])
        if not normalized:
            raise ValueError("ticker is required.")
        normalized_ticker = normalized[0]
        provider_ticker = _provider_ticker(normalized_ticker)
        try:
            import yfinance as yf
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "yfinance option-suite data requires the 'yfinance' package. Install dependencies or run through Docker."
            ) from exc

        fetched_at = datetime.now(timezone.utc)
        warnings: list[str] = []
        ticker_obj = yf.Ticker(provider_ticker)
        expiries = list(getattr(ticker_obj, "options", []) or [])
        selected_expiry, expiry_warnings = _select_option_expiry(expiry, expiries)
        warnings.extend(expiry_warnings)
        surface_expiries = _surface_expiries(expiry, expiries, max_expiries)
        current_chain: OptionChainSnapshot | None = None
        surface_chains: list[OptionChainSnapshot] = []

        if selected_expiry is None:
            warnings.append(f"No yfinance option expirations were available for {normalized_ticker}.")
        else:
            chain_by_expiry: dict[date, OptionChainSnapshot] = {}
            for chain_expiry in surface_expiries or [selected_expiry]:
                try:
                    chain = ticker_obj.option_chain(chain_expiry.isoformat())
                    snapshot = OptionChainSnapshot(
                        ticker=normalized_ticker,
                        provider_ticker=provider_ticker,
                        requested_expiry=expiry if chain_expiry == selected_expiry else chain_expiry,
                        expiry=chain_expiry,
                        provider=self.provider,
                        fetched_at=fetched_at,
                        calls=_contracts_from_frame(getattr(chain, "calls", None), "call"),
                        puts=_contracts_from_frame(getattr(chain, "puts", None), "put"),
                        warnings=expiry_warnings if chain_expiry == selected_expiry else [],
                    )
                    chain_by_expiry[chain_expiry] = snapshot
                    surface_chains.append(snapshot)
                except Exception as exc:
                    warnings.append(f"Could not fetch option chain for {chain_expiry.isoformat()}: {exc}.")
            current_chain = chain_by_expiry.get(selected_expiry)
            if current_chain is None and selected_expiry is not None:
                current_chain = OptionChainSnapshot(
                    ticker=normalized_ticker,
                    provider_ticker=provider_ticker,
                    requested_expiry=expiry,
                    expiry=selected_expiry,
                    provider=self.provider,
                    fetched_at=fetched_at,
                    calls=[],
                    puts=[],
                    warnings=expiry_warnings,
                )

        price_history = _fetch_price_history(
            yf,
            normalized_ticker=normalized_ticker,
            provider_ticker=provider_ticker,
            provider=self.provider,
            period=history_period,
            fetched_at=fetched_at,
        )
        warnings.extend(price_history.warnings if price_history else [])
        return OptionSuiteSnapshot(
            ticker=normalized_ticker,
            provider_ticker=provider_ticker,
            provider=self.provider,
            fetched_at=fetched_at,
            requested_expiry=expiry,
            current_chain=current_chain,
            surface_chains=surface_chains,
            price_history=price_history,
            warnings=warnings,
        )

def _quotes_from_download(
    raw: Any,
    tickers: list[str],
    *,
    provider: str,
    provider_by_ticker: dict[str, str] | None = None,
) -> list[MarketQuote]:
    if raw is None or getattr(raw, "empty", True):
        return []

    quotes: list[MarketQuote] = []
    fetched_at = datetime.now(timezone.utc)
    provider_by_ticker = provider_by_ticker or {ticker: ticker for ticker in tickers}
    for ticker in tickers:
        provider_ticker = provider_by_ticker.get(ticker, ticker)
        close_series = _close_series(raw, provider_ticker)
        if close_series is None and provider_ticker != ticker:
            close_series = _close_series(raw, ticker)
        if close_series is None:
            continue
        close_series = close_series.dropna()
        if len(close_series) == 0:
            continue

        price = float(close_series.iloc[-1])
        previous_close = _previous_close(close_series)
        daily_return_pct = None
        if previous_close is not None and previous_close > 0:
            daily_return_pct = ((price / previous_close) - 1.0) * 100.0

        quotes.append(
            MarketQuote(
                ticker=ticker,
                provider=provider,
                price=price,
                previous_close=previous_close,
                daily_return_pct=daily_return_pct,
                fetched_at=fetched_at,
                updated_at=fetched_at,
            )
        )
    return quotes


def _close_series(raw: Any, ticker: str):
    try:
        if getattr(raw.columns, "nlevels", 1) > 1:
            first_level = set(raw.columns.get_level_values(0))
            if ticker in first_level:
                return raw[ticker]["Close"]
            second_level = set(raw.columns.get_level_values(1))
            if ticker in second_level:
                return raw["Close"][ticker]
        return raw["Close"]
    except Exception:
        return None


def _previous_close(close_series: Any) -> float | None:
    try:
        by_day = close_series.groupby(close_series.index.date)
        day_keys = list(by_day.groups.keys())
        if len(day_keys) >= 2:
            return float(by_day.get_group(day_keys[-2]).iloc[-1])
    except Exception:
        pass
    if len(close_series) >= 2:
        return float(close_series.iloc[-2])
    return None


def _provider_ticker(ticker: str) -> str:
    return ticker.replace("_", "-")


def _normalize_tickers(tickers: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        clean = str(ticker).strip().upper()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized


def _fetch_price_history(
    yf: Any,
    *,
    normalized_ticker: str,
    provider_ticker: str,
    provider: str,
    period: str,
    fetched_at: datetime,
) -> PriceHistorySnapshot | None:
    warnings: list[str] = []
    try:
        raw = yf.download(
            tickers=provider_ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception as exc:
        return PriceHistorySnapshot(
            ticker=normalized_ticker,
            provider_ticker=provider_ticker,
            provider=provider,
            fetched_at=fetched_at,
            prices=[],
            warnings=[f"Could not fetch historical prices for volatility guidance: {exc}."],
        )
    prices = _price_history_from_download(raw, provider_ticker)
    if not prices:
        warnings.append("Historical prices were unavailable for volatility guidance.")
    return PriceHistorySnapshot(
        ticker=normalized_ticker,
        provider_ticker=provider_ticker,
        provider=provider,
        fetched_at=fetched_at,
        prices=prices,
        warnings=warnings,
    )


def _price_history_from_download(raw: Any, ticker: str) -> list[tuple[date, float]]:
    points = _price_history_points_from_download(raw, ticker)
    by_date: dict[date, float] = {}
    for point in points:
        by_date[point.as_of.date()] = point.close
    return sorted(by_date.items(), key=lambda item: item[0])


def _price_history_points_from_download(raw: Any, ticker: str) -> list[PriceHistoryPoint]:
    if raw is None or getattr(raw, "empty", True):
        return []
    close_series = _close_series(raw, ticker)
    if close_series is None:
        return []
    try:
        close_series = close_series.dropna()
    except Exception:
        return []
    points: list[PriceHistoryPoint] = []
    for index, close in _series_items(close_series):
        try:
            close_value = float(close)
            if close_value <= 0 or close_value != close_value:
                continue
            as_of = _history_index_datetime(index)
        except Exception:
            continue
        points.append(PriceHistoryPoint(as_of=as_of, close=close_value))
    return sorted(points, key=lambda point: point.as_of)


def _series_items(series: Any):
    if hasattr(series, "items"):
        try:
            yield from series.items()
            return
        except Exception:
            pass
    values = getattr(series, "values", [])
    index = getattr(series, "index", None)
    dates = getattr(index, "date", None) if index is not None else None
    if dates is None:
        dates = list(range(len(values)))
    for item_date, value in zip(dates, values):
        yield item_date, value


def _history_index_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif hasattr(value, "to_pydatetime"):
        parsed = value.to_pydatetime()
    else:
        raw = str(value)
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            parsed = datetime.combine(date.fromisoformat(raw[:10]), time.min)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _surface_expiries(requested: date, expiries: list[str], max_expiries: int) -> list[date]:
    parsed = _parse_option_expiries(expiries)
    if not parsed:
        return []
    future = [value for value in parsed if value >= requested]
    selected = future or parsed
    return selected[: max(1, max_expiries)]


def _parse_option_expiries(expiries: list[str]) -> list[date]:
    parsed: list[date] = []
    for value in expiries:
        try:
            parsed.append(date.fromisoformat(str(value)))
        except ValueError:
            continue
    return sorted(set(parsed))

def _select_option_expiry(requested: date, expiries: list[str]) -> tuple[date | None, list[str]]:
    parsed = _parse_option_expiries(expiries)
    if not parsed:
        return None, []
    if requested in parsed:
        return requested, []

    future = [value for value in parsed if value >= requested]
    selected = min(future or parsed, key=lambda value: abs((value - requested).days))
    return selected, [
        f"Requested expiry {requested.isoformat()} was not listed by yfinance; using {selected.isoformat()} instead."
    ]


def _contracts_from_frame(frame: Any, option_type: str) -> list[OptionContract]:
    if frame is None or getattr(frame, "empty", True):
        return []
    contracts: list[OptionContract] = []
    for row in frame.to_dict(orient="records"):
        strike = _optional_float(row.get("strike"))
        if strike is None or strike <= 0:
            continue
        contracts.append(
            OptionContract(
                option_type=option_type,
                strike=strike,
                contract_symbol=_optional_str(row.get("contractSymbol")),
                last_price=_optional_float(row.get("lastPrice")),
                bid=_optional_float(row.get("bid")),
                ask=_optional_float(row.get("ask")),
                implied_volatility=_optional_float(row.get("impliedVolatility")),
                volume=_optional_float(row.get("volume")),
                open_interest=_optional_float(row.get("openInterest")),
                in_the_money=_optional_bool(row.get("inTheMoney")),
            )
        )
    return contracts


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


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None
