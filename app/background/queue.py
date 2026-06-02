from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


class BackgroundQueueError(RuntimeError):
    """Raised when the Redis background queue cannot be used."""


@dataclass(frozen=True, slots=True)
class QueuedBackgroundJob:
    job_id: str
    portfolio_id: str
    job_type: str
    payload: dict[str, Any]


def background_queue_name() -> str:
    return os.getenv("BACKGROUND_QUEUE_NAME", "portfolio-jobs")


def redis_client_from_env():
    try:
        from redis import Redis
    except ModuleNotFoundError as exc:
        raise BackgroundQueueError(
            "Redis background jobs require the 'redis' package. Install project dependencies or run through Docker."
        ) from exc

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(redis_url, decode_responses=True)


def enqueue_background_job_message(
    job: Any,
    *,
    payload: dict[str, Any] | None = None,
    client: Any | None = None,
    queue_name: str | None = None,
) -> None:
    redis_client = client or redis_client_from_env()
    redis_client.rpush(
        queue_name or background_queue_name(),
        json.dumps(
            {
                "job_id": job.id,
                "portfolio_id": job.portfolio_id,
                "job_type": job.job_type,
                "payload": payload or {},
            },
            separators=(",", ":"),
            sort_keys=True,
        ),
    )


def dequeue_background_job_message(
    *,
    block_timeout_seconds: int = 5,
    client: Any | None = None,
    queue_name: str | None = None,
) -> QueuedBackgroundJob | None:
    redis_client = client or redis_client_from_env()
    try:
        from redis.exceptions import TimeoutError as RedisTimeoutError
    except ModuleNotFoundError:
        RedisTimeoutError = TimeoutError

    try:
        item = redis_client.blpop([queue_name or background_queue_name()], timeout=block_timeout_seconds)
    except (RedisTimeoutError, TimeoutError):
        return None

    if item is None:
        return None

    try:
        _, raw_message = item
    except (TypeError, ValueError) as exc:
        raise BackgroundQueueError("Redis returned an invalid queue item.") from exc
    return parse_background_job_message(raw_message)


def parse_background_job_message(raw_message: str | bytes) -> QueuedBackgroundJob:
    if isinstance(raw_message, bytes):
        raw_message = raw_message.decode("utf-8")
    try:
        parsed = json.loads(raw_message)
    except json.JSONDecodeError as exc:
        raise BackgroundQueueError("Background job message is not valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise BackgroundQueueError("Background job message must be a JSON object.")

    payload = parsed.get("payload") or {}
    if not isinstance(payload, dict):
        raise BackgroundQueueError("Background job payload must be a JSON object.")

    try:
        return QueuedBackgroundJob(
            job_id=str(parsed["job_id"]),
            portfolio_id=str(parsed["portfolio_id"]),
            job_type=str(parsed["job_type"]),
            payload=payload,
        )
    except KeyError as exc:
        raise BackgroundQueueError(f"Background job message is missing {exc.args[0]!r}.") from exc
