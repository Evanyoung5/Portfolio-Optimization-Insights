from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException, Request, status

from app.auth.security import normalize_email
from app.connectors.market_data.limiter import InMemoryRateLimiter, RedisRateLimiter

_AUTH_LIMITER: Any | None = None


def enforce_auth_rate_limit(
    action: str,
    *,
    request: Request,
    email: str | None = None,
    user_id: str | None = None,
) -> None:
    limiter = _auth_rate_limiter()
    checks = [
        {
            "key": f"{action}:ip:{client_ip(request)}",
            "limit": _limit(action, "IP_LIMIT", _default_ip_limit(action)),
            "window_seconds": _limit(action, "WINDOW_SECONDS", _default_window(action)),
            "cost": 1,
        }
    ]
    if email:
        checks.append(
            {
                "key": f"{action}:email:{normalize_email(email)}",
                "limit": _limit(action, "EMAIL_LIMIT", _default_email_limit(action)),
                "window_seconds": _limit(action, "WINDOW_SECONDS", _default_window(action)),
                "cost": 1,
            }
        )
    if user_id:
        checks.append(
            {
                "key": f"{action}:user:{user_id}",
                "limit": _limit(action, "USER_LIMIT", _default_user_limit(action)),
                "window_seconds": _limit(action, "WINDOW_SECONDS", _default_window(action)),
                "cost": 1,
            }
        )

    try:
        results = limiter.check_many(checks)
    except Exception:
        if _require_redis_limiter():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication rate limiter is unavailable.",
            )
        fallback = InMemoryRateLimiter()
        results = fallback.check_many(checks)

    denied = next((item for item in results if not item.allowed), None)
    if denied is None:
        return

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many authentication attempts. Please wait and try again.",
        headers={"Retry-After": str(max(int(denied.retry_after_seconds), 1))},
    )


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def _auth_rate_limiter() -> Any:
    global _AUTH_LIMITER
    if _AUTH_LIMITER is not None:
        return _AUTH_LIMITER
    try:
        _AUTH_LIMITER = RedisRateLimiter(key_prefix="auth-rate-limit")
    except Exception:
        if _require_redis_limiter():
            raise
        _AUTH_LIMITER = InMemoryRateLimiter()
    return _AUTH_LIMITER


def _require_redis_limiter() -> bool:
    return os.getenv("AUTH_REQUIRE_REDIS_LIMITER", "false").strip().lower() in {"1", "true", "yes", "on"}


def _limit(action: str, suffix: str, default: int) -> int:
    key = f"AUTH_RATE_LIMIT_{action.upper()}_{suffix}"
    return max(1, int(os.getenv(key, str(default))))


def _default_window(action: str) -> int:
    return {
        "login": 15 * 60,
        "register": 60 * 60,
        "refresh": 15 * 60,
        "logout": 15 * 60,
        "password_reset_request": 60 * 60,
        "password_reset_confirm": 60 * 60,
        "email_verification_request": 60 * 60,
        "email_verification_confirm": 60 * 60,
    }.get(action, 15 * 60)


def _default_ip_limit(action: str) -> int:
    return {
        "login": 20,
        "register": 10,
        "refresh": 40,
        "logout": 60,
        "password_reset_request": 8,
        "password_reset_confirm": 10,
        "email_verification_request": 8,
        "email_verification_confirm": 10,
    }.get(action, 20)


def _default_email_limit(action: str) -> int:
    return {
        "login": 8,
        "register": 4,
        "password_reset_request": 5,
    }.get(action, _default_ip_limit(action))


def _default_user_limit(action: str) -> int:
    return {
        "email_verification_request": 5,
        "refresh": 40,
        "logout": 60,
    }.get(action, _default_ip_limit(action))
