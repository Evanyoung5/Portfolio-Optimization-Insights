from __future__ import annotations

import os
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from app.background.queue import redis_client_from_env


class RateLimitExceeded(RuntimeError):
    def __init__(self, message: str, *, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    key: str
    limit: int
    remaining: int
    retry_after_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._counts: dict[str, tuple[int, float]] = {}

    def check(self, *, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        import time

        now = time.time()
        count, reset_at = self._counts.get(key, (0, now + window_seconds))
        if now >= reset_at:
            count = 0
            reset_at = now + window_seconds
        count += 1
        self._counts[key] = (count, reset_at)
        retry_after = max(int(reset_at - now), 0)
        return RateLimitResult(
            allowed=count <= limit,
            key=key,
            limit=limit,
            remaining=max(limit - count, 0),
            retry_after_seconds=retry_after,
        )


_FALLBACK_LIMITER = InMemoryRateLimiter()


class RedisRateLimiter:
    def __init__(self, *, client: Any | None = None, key_prefix: str = "rate-limit") -> None:
        self.client = client or redis_client_from_env()
        self.key_prefix = key_prefix

    def check(self, *, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        redis_key = f"{self.key_prefix}:{key}"
        count = int(self.client.incr(redis_key))
        if count == 1:
            self.client.expire(redis_key, window_seconds)
        ttl = int(self.client.ttl(redis_key))
        retry_after = ttl if ttl > 0 else window_seconds
        return RateLimitResult(
            allowed=count <= limit,
            key=redis_key,
            limit=limit,
            remaining=max(limit - count, 0),
            retry_after_seconds=retry_after,
        )


def create_rate_limiter() -> Any:
    try:
        return RedisRateLimiter()
    except Exception:
        if _require_redis_limiter():
            raise
        return _FALLBACK_LIMITER


def _require_redis_limiter() -> bool:
    return os.getenv("MARKET_DATA_REQUIRE_REDIS_LIMITER", "false").strip().lower() in {"1", "true", "yes", "on"}


def _check_limiter(
    limiter: Any,
    *,
    key: str,
    limit: int,
    window_seconds: int,
) -> RateLimitResult:
    try:
        return limiter.check(key=key, limit=limit, window_seconds=window_seconds)
    except Exception:
        if _require_redis_limiter():
            raise
        return _FALLBACK_LIMITER.check(key=key, limit=limit, window_seconds=window_seconds)


def enforce_market_data_refresh_limits(
    *,
    user_id: str,
    portfolio_id: str,
    limiter: Any | None = None,
) -> None:
    limiter = limiter or create_rate_limiter()
    checks = [
        (
            f"market-data:user:{user_id}:minute",
            int(os.getenv("MARKET_DATA_USER_REFRESH_LIMIT_PER_MINUTE", "5")),
            60,
            "Too many market-data refresh requests. Try again shortly.",
        ),
        (
            f"market-data:user:{user_id}:day",
            int(os.getenv("MARKET_DATA_USER_REFRESH_LIMIT_PER_DAY", "100")),
            86_400,
            "Daily market-data refresh limit reached.",
        ),
        (
            f"market-data:portfolio:{portfolio_id}:refresh",
            1,
            int(os.getenv("MARKET_DATA_PORTFOLIO_REFRESH_MIN_SECONDS", "0")),
            "This portfolio was refreshed recently. Try again later.",
        ),
    ]
    for key, limit, window, message in checks:
        if limit <= 0 or window <= 0:
            continue
        result = _check_limiter(limiter, key=key, limit=limit, window_seconds=window)
        if not result.allowed:
            raise RateLimitExceeded(message, retry_after_seconds=result.retry_after_seconds)


def acquire_provider_fetch_slot(
    *,
    provider: str,
    provider_signature: str | None = None,
    limiter: Any | None = None,
    wait: bool = False,
    sleep: Callable[[float], None] | None = None,
) -> RateLimitResult:
    import time

    limiter = limiter or create_rate_limiter()
    sleep_fn = sleep or time.sleep
    while True:
        result = _check_limiter(
            limiter,
            key=f"market-data:provider:{provider}:signature:{_provider_signature_key(provider_signature)}:minute",
            limit=int(os.getenv("MARKET_DATA_PROVIDER_FETCH_LIMIT_PER_MINUTE", "1")),
            window_seconds=60,
        )
        if result.allowed:
            return result
        if not wait:
            raise RateLimitExceeded(
                "Market-data provider request budget is temporarily exhausted.",
                retry_after_seconds=result.retry_after_seconds,
            )
        sleep_fn(max(result.retry_after_seconds, 1))


def enforce_provider_fetch_limit(
    *,
    provider: str,
    provider_signature: str | None = None,
    limiter: Any | None = None,
) -> None:
    acquire_provider_fetch_slot(
        provider=provider,
        provider_signature=provider_signature,
        limiter=limiter,
        wait=False,
    )


def _provider_signature_key(provider_signature: str | None) -> str:
    clean = "".join(
        char
        for char in str(provider_signature or "global").strip().lower()
        if char.isalnum() or char in {"-", "_"}
    )
    return clean or "global"
