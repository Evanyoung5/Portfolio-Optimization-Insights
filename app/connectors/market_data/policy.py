from __future__ import annotations

import os


def env_int(name: str, default: int, *, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(value, minimum)


def max_refresh_tickers() -> int:
    return env_int("MARKET_DATA_MAX_REFRESH_TICKERS", 50)


def max_history_tickers() -> int:
    return env_int("MARKET_DATA_MAX_HISTORY_TICKERS", 40)


def max_benchmark_tickers() -> int:
    return env_int("MARKET_DATA_MAX_BENCHMARK_TICKERS", 8)


def max_options_surface_expiries() -> int:
    return env_int("OPTIONS_CHAIN_MAX_SURFACE_EXPIRIES", 4)


def provider_cost_for_tickers(ticker_count: int) -> int:
    unit_size = env_int("MARKET_DATA_PROVIDER_TICKERS_PER_COST_UNIT", 5)
    return max(1, (max(int(ticker_count), 1) + unit_size - 1) // unit_size)


def provider_cost_for_option_chain() -> int:
    return env_int("OPTIONS_CHAIN_PROVIDER_COST", 2)


def provider_cost_for_option_suite(max_expiries: int) -> int:
    base_cost = env_int("OPTIONS_SUITE_PROVIDER_BASE_COST", 2)
    return base_cost + max(1, int(max_expiries))


def allowed_options_history_periods() -> set[str]:
    configured = os.getenv("OPTIONS_HISTORY_ALLOWED_PERIODS")
    if not configured:
        return {"1mo", "3mo", "6mo", "1y", "2y", "5y"}
    periods = {item.strip().lower() for item in configured.split(",") if item.strip()}
    return periods or {"1mo", "3mo", "6mo", "1y", "2y", "5y"}


def validate_ticker_budget(tickers: list[str], *, limit: int, label: str) -> None:
    if len(tickers) > limit:
        raise ValueError(f"{label} is limited to {limit} ticker(s); received {len(tickers)}.")


def validate_options_surface_expiries(value: int) -> int:
    max_expiries = max_options_surface_expiries()
    requested = max(1, int(value))
    if requested > max_expiries:
        raise ValueError(f"surface_expiries is limited to {max_expiries} in this environment.")
    return requested


def validate_options_history_period(value: str) -> str:
    period = str(value or "1y").strip().lower()
    allowed = allowed_options_history_periods()
    if period not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise ValueError(f"history_period must be one of: {allowed_text}.")
    return period
