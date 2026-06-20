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
    cost: int = 1


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._counts: dict[str, tuple[int, float]] = {}

    def check(self, *, key: str, limit: int, window_seconds: int, cost: int = 1) -> RateLimitResult:
        import time

        cost = max(int(cost), 1)
        now = time.time()
        count, reset_at = self._counts.get(key, (0, now + window_seconds))
        if now >= reset_at:
            count = 0
            reset_at = now + window_seconds
        count += cost
        self._counts[key] = (count, reset_at)
        retry_after = max(int(reset_at - now), 0)
        return RateLimitResult(
            allowed=count <= limit,
            key=key,
            limit=limit,
            remaining=max(limit - count, 0),
            retry_after_seconds=retry_after,
            cost=cost,
        )

    def check_many(self, checks: list[dict[str, Any]]) -> list[RateLimitResult]:
        import time

        now = time.time()
        projected: list[tuple[str, int, int, int, float]] = []
        for item in checks:
            key = str(item["key"])
            limit = int(item["limit"])
            window_seconds = int(item["window_seconds"])
            cost = max(int(item.get("cost", 1)), 1)
            count, reset_at = self._counts.get(key, (0, now + window_seconds))
            if now >= reset_at:
                count = 0
                reset_at = now + window_seconds
            projected.append((key, limit, cost, count + cost, reset_at))

        denied = next((item for item in projected if item[3] > item[1]), None)
        if denied is not None:
            key, limit, cost, projected_count, reset_at = denied
            retry_after = max(int(reset_at - now), 0)
            return [
                RateLimitResult(
                    allowed=False,
                    key=key,
                    limit=limit,
                    remaining=max(limit - projected_count, 0),
                    retry_after_seconds=retry_after,
                    cost=cost,
                )
            ]

        results: list[RateLimitResult] = []
        for key, limit, cost, projected_count, reset_at in projected:
            self._counts[key] = (projected_count, reset_at)
            retry_after = max(int(reset_at - now), 0)
            results.append(
                RateLimitResult(
                    allowed=True,
                    key=key,
                    limit=limit,
                    remaining=max(limit - projected_count, 0),
                    retry_after_seconds=retry_after,
                    cost=cost,
                )
            )
        return results


_FALLBACK_LIMITER = InMemoryRateLimiter()


_CHECK_MANY_SCRIPT = """
local n = tonumber(ARGV[1])
for i = 1, n do
    local base = 1 + ((i - 1) * 3)
    local limit = tonumber(ARGV[base + 1])
    local window = tonumber(ARGV[base + 2])
    local cost = tonumber(ARGV[base + 3])
    local current = tonumber(redis.call('GET', KEYS[i]) or '0')
    local projected = current + cost
    if projected > limit then
        local ttl = redis.call('TTL', KEYS[i])
        if ttl < 0 then
            ttl = window
        end
        return {0, i, projected, limit, ttl, cost}
    end
end

local result = {1}
for i = 1, n do
    local base = 1 + ((i - 1) * 3)
    local limit = tonumber(ARGV[base + 1])
    local window = tonumber(ARGV[base + 2])
    local cost = tonumber(ARGV[base + 3])
    local count = tonumber(redis.call('INCRBY', KEYS[i], cost))
    if count == cost then
        redis.call('EXPIRE', KEYS[i], window)
    end
    local ttl = redis.call('TTL', KEYS[i])
    if ttl < 0 then
        ttl = window
    end
    table.insert(result, count)
    table.insert(result, limit)
    table.insert(result, ttl)
    table.insert(result, cost)
end
return result
"""


class RedisRateLimiter:
    def __init__(self, *, client: Any | None = None, key_prefix: str = "rate-limit") -> None:
        self.client = client or redis_client_from_env()
        self.key_prefix = key_prefix

    def check(self, *, key: str, limit: int, window_seconds: int, cost: int = 1) -> RateLimitResult:
        redis_key = f"{self.key_prefix}:{key}"
        cost = max(int(cost), 1)
        count = int(self.client.incrby(redis_key, cost))
        if count == cost:
            self.client.expire(redis_key, window_seconds)
        ttl = int(self.client.ttl(redis_key))
        retry_after = ttl if ttl > 0 else window_seconds
        return RateLimitResult(
            allowed=count <= limit,
            key=redis_key,
            limit=limit,
            remaining=max(limit - count, 0),
            retry_after_seconds=retry_after,
            cost=cost,
        )

    def check_many(self, checks: list[dict[str, Any]]) -> list[RateLimitResult]:
        prepared: list[tuple[str, str, int, int, int]] = []
        for item in checks:
            key = str(item["key"])
            prepared.append(
                (
                    key,
                    f"{self.key_prefix}:{key}",
                    int(item["limit"]),
                    int(item["window_seconds"]),
                    max(int(item.get("cost", 1)), 1),
                )
            )

        keys = [redis_key for _, redis_key, _, _, _ in prepared]
        args = [str(len(prepared))]
        for _, _, limit, window_seconds, cost in prepared:
            args.extend([str(limit), str(window_seconds), str(cost)])

        raw = self.client.eval(_CHECK_MANY_SCRIPT, len(keys), *keys, *args)
        values = [int(item) for item in raw]
        if values[0] == 0:
            denied_index = values[1] - 1
            _, redis_key, limit, _, cost = prepared[denied_index]
            projected = values[2]
            retry_after = values[4]
            return [
                RateLimitResult(
                    allowed=False,
                    key=redis_key,
                    limit=limit,
                    remaining=max(limit - projected, 0),
                    retry_after_seconds=retry_after,
                    cost=cost,
                )
            ]

        results: list[RateLimitResult] = []
        offset = 1
        for _, redis_key, _, _, _ in prepared:
            count = values[offset]
            limit = values[offset + 1]
            retry_after = values[offset + 2]
            cost = values[offset + 3]
            offset += 4
            results.append(
                RateLimitResult(
                    allowed=count <= limit,
                    key=redis_key,
                    limit=limit,
                    remaining=max(limit - count, 0),
                    retry_after_seconds=retry_after,
                    cost=cost,
                )
            )
        return results


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
    cost: int = 1,
) -> RateLimitResult:
    try:
        return limiter.check(key=key, limit=limit, window_seconds=window_seconds, cost=max(int(cost), 1))
    except TypeError:
        try:
            return limiter.check(key=key, limit=limit, window_seconds=window_seconds)
        except Exception:
            if _require_redis_limiter():
                raise
            return _FALLBACK_LIMITER.check(key=key, limit=limit, window_seconds=window_seconds, cost=max(int(cost), 1))
    except Exception:
        if _require_redis_limiter():
            raise
        return _FALLBACK_LIMITER.check(key=key, limit=limit, window_seconds=window_seconds, cost=max(int(cost), 1))


def _check_many_limiter(limiter: Any, checks: list[dict[str, Any]]) -> list[RateLimitResult]:
    try:
        check_many = getattr(limiter, "check_many")
    except Exception:
        check_many = None
    if check_many is not None:
        try:
            return check_many(checks)
        except Exception:
            if _require_redis_limiter():
                raise
    results: list[RateLimitResult] = []
    for item in checks:
        result = _check_limiter(
            limiter,
            key=str(item["key"]),
            limit=int(item["limit"]),
            window_seconds=int(item["window_seconds"]),
            cost=max(int(item.get("cost", 1)), 1),
        )
        results.append(result)
        if not result.allowed:
            break
    return results


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
    cost: int = 1,
) -> RateLimitResult:
    import time

    limiter = limiter or create_rate_limiter()
    sleep_fn = sleep or time.sleep
    request_cost = max(int(cost), 1)
    provider_key = str(provider).strip().lower() or "unknown"
    while True:
        results = _check_many_limiter(
            limiter,
            [
                {
                    "key": f"market-data:provider:{provider_key}:global:minute",
                    "limit": int(os.getenv("MARKET_DATA_PROVIDER_GLOBAL_FETCH_LIMIT_PER_MINUTE", "60")),
                    "window_seconds": 60,
                    "cost": request_cost,
                },
                {
                    "key": (
                        f"market-data:provider:{provider_key}:"
                        f"signature:{_provider_signature_key(provider_signature)}:minute"
                    ),
                    "limit": int(os.getenv("MARKET_DATA_PROVIDER_FETCH_LIMIT_PER_MINUTE", "10")),
                    "window_seconds": 60,
                    "cost": request_cost,
                },
            ],
        )
        blocked = next((item for item in results if not item.allowed), None)
        if blocked is None:
            return results[-1]
        if not wait:
            raise RateLimitExceeded(
                "Market-data provider request budget is temporarily exhausted.",
                retry_after_seconds=blocked.retry_after_seconds,
            )
        sleep_fn(max(blocked.retry_after_seconds, 1))


def enforce_provider_fetch_limit(
    *,
    provider: str,
    provider_signature: str | None = None,
    limiter: Any | None = None,
    cost: int = 1,
) -> None:
    acquire_provider_fetch_slot(
        provider=provider,
        provider_signature=provider_signature,
        limiter=limiter,
        wait=False,
        cost=cost,
    )


def _provider_signature_key(provider_signature: str | None) -> str:
    clean = "".join(
        char
        for char in str(provider_signature or "global").strip().lower()
        if char.isalnum() or char in {"-", "_"}
    )
    return clean or "global"
