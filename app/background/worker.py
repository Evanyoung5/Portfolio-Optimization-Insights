from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Any

from app.background.portfolio_tasks import apply_market_quotes_to_portfolio, rebuild_portfolio_positions
from app.background.queue import QueuedBackgroundJob, dequeue_background_job_message, enqueue_background_job_message
from app.connectors.market_data.limiter import RateLimitExceeded
from app.connectors.market_data.history import refresh_price_history
from app.connectors.market_data.service import portfolio_tickers, refresh_market_data_quotes
from app.db.models import BackgroundJob
from app.db.repository import create_portfolio_repository

LOGGER = logging.getLogger(__name__)
SUPPORTED_JOB_TYPES = {"manual_lot_rollup", "rebuild_positions", "refresh_market_data", "refresh_market_history"}


def process_background_job(repository: Any, queued_job: QueuedBackgroundJob) -> BackgroundJob:
    portfolio = repository.get(queued_job.portfolio_id)
    current_job = None
    if portfolio is not None:
        current_job = next((job for job in portfolio.background_jobs if job.id == queued_job.job_id), None)
    if current_job is None:
        message = f"Dropped stale background job {queued_job.job_id}; no database record exists."
        LOGGER.warning(message)
        return _dropped_background_job(queued_job, message)
    if current_job.status not in {"pending", "running"}:
        message = f"Dropped already-finished background job {queued_job.job_id}; status is {current_job.status}."
        LOGGER.info(message)
        return _dropped_background_job(queued_job, message)

    try:
        repository.complete_background_job(
            queued_job.portfolio_id,
            queued_job.job_id,
            status="running",
            message=f"Worker started {queued_job.job_type}.",
        )
    except KeyError:
        message = f"Dropped stale background job {queued_job.job_id}; no database record exists."
        LOGGER.warning(message)
        return _dropped_background_job(queued_job, message)
    try:
        if queued_job.job_type not in SUPPORTED_JOB_TYPES:
            raise ValueError(f"Unsupported background job type: {queued_job.job_type}.")
        if queued_job.job_type == "refresh_market_history":
            portfolio = repository.get(queued_job.portfolio_id)
            if portfolio is None:
                raise KeyError(f"Portfolio {queued_job.portfolio_id!r} was not found.")
            deferred = _deferred_until(queued_job.payload)
            if deferred is not None:
                now = datetime.now(timezone.utc)
                if deferred > now:
                    import time

                    wait_seconds = max((deferred - now).total_seconds(), 1.0)
                    repository.complete_background_job(
                        queued_job.portfolio_id,
                        queued_job.job_id,
                        status="running",
                        message=f"Waiting for account market-history slot until {deferred.isoformat()}.",
                    )
                    time.sleep(wait_seconds)

            tickers = queued_job.payload.get("tickers") or _market_data_tickers(repository, portfolio)
            provider_signature = queued_job.payload.get("provider_signature") or _market_data_account_signature(portfolio)
            defer_on_rate_limit = bool(queued_job.payload.get("defer_on_rate_limit", True))
            ranges = queued_job.payload.get("ranges") or [queued_job.payload.get("range_name") or "max"]
            if isinstance(ranges, str):
                ranges = [ranges]
            completed: list[str] = []
            priced = 0
            try:
                for range_name in list(dict.fromkeys(str(item) for item in ranges)):
                    bundle = refresh_price_history(
                        list(tickers),
                        range_name=range_name,
                        force=bool(queued_job.payload.get("force", False)),
                        wait_for_rate_limit=defer_on_rate_limit or bool(queued_job.payload.get("wait_for_rate_limit", False)),
                        provider_signature=str(provider_signature),
                    )
                    completed.append(bundle.range_name)
                    priced = max(priced, len([item for item in bundle.series if item.points]))
            except RateLimitExceeded as exc:
                if not defer_on_rate_limit:
                    raise
                retry_at = datetime.now(timezone.utc).timestamp() + max(exc.retry_after_seconds, 1)
                remaining = [item for item in ranges if str(item) not in set(completed)]
                payload = {
                    **queued_job.payload,
                    "ranges": remaining,
                    "defer_on_rate_limit": True,
                    "deferred_until": datetime.fromtimestamp(retry_at, tz=timezone.utc).isoformat(),
                    "provider_signature": str(provider_signature),
                }
                return _requeue_market_data_job(
                    repository,
                    queued_job,
                    payload=payload,
                    message=f"Waiting {max(exc.retry_after_seconds, 1)} second(s) for account market-history slot.",
                )

            return repository.complete_background_job(
                queued_job.portfolio_id,
                queued_job.job_id,
                status="completed",
                message=f"Cached {', '.join(completed)} market history for {priced} ticker(s).",
            )

        if queued_job.job_type == "refresh_market_data":
            portfolio = repository.get(queued_job.portfolio_id)
            if portfolio is None:
                raise KeyError(f"Portfolio {queued_job.portfolio_id!r} was not found.")
            deferred = _deferred_until(queued_job.payload)
            if deferred is not None:
                now = datetime.now(timezone.utc)
                if deferred > now:
                    import time

                    wait_seconds = max((deferred - now).total_seconds(), 1.0)
                    repository.complete_background_job(
                        queued_job.portfolio_id,
                        queued_job.job_id,
                        status="running",
                        message=f"Waiting for account market-data slot until {deferred.isoformat()}.",
                    )
                    time.sleep(wait_seconds)

            tickers = queued_job.payload.get("tickers") or _market_data_tickers(repository, portfolio)
            provider_signature = queued_job.payload.get("provider_signature") or _market_data_account_signature(portfolio)
            defer_on_rate_limit = bool(queued_job.payload.get("defer_on_rate_limit", True))
            try:
                quotes = refresh_market_data_quotes(
                    list(tickers),
                    repository,
                    force=bool(queued_job.payload.get("force", False)),
                    wait_for_rate_limit=defer_on_rate_limit or bool(queued_job.payload.get("wait_for_rate_limit", False)),
                    provider_signature=str(provider_signature),
                )
            except RateLimitExceeded as exc:
                if not defer_on_rate_limit:
                    raise
                retry_at = datetime.now(timezone.utc).timestamp() + max(exc.retry_after_seconds, 1)
                payload = {
                    **queued_job.payload,
                    "defer_on_rate_limit": True,
                    "deferred_until": datetime.fromtimestamp(retry_at, tz=timezone.utc).isoformat(),
                    "provider_signature": str(provider_signature),
                }
                return _requeue_market_data_job(
                    repository,
                    queued_job,
                    payload=payload,
                    message=f"Waiting {max(exc.retry_after_seconds, 1)} second(s) for account market-data slot.",
                )

            updated = apply_market_quotes_to_portfolio(repository, queued_job.portfolio_id, quotes)
            priced_tickers = {quote.ticker for quote in quotes}
            repriced = sum(1 for position in updated.positions if position.symbol in priced_tickers)
            return repository.complete_background_job(
                queued_job.portfolio_id,
                queued_job.job_id,
                status="completed",
                message=f"Refreshed market data for {len(quotes)} ticker(s); repriced {repriced} holding(s).",
            )

        portfolio = rebuild_portfolio_positions(repository, queued_job.portfolio_id)
        return repository.complete_background_job(
            queued_job.portfolio_id,
            queued_job.job_id,
            status="completed",
            message=f"Rebuilt positions from {len(portfolio.lots)} lot(s).",
        )
    except Exception as exc:
        try:
            repository.complete_background_job(
                queued_job.portfolio_id,
                queued_job.job_id,
                status="failed",
                message=str(exc),
            )
        except KeyError:
            message = f"Dropped stale background job {queued_job.job_id} after failure: {exc}"
            LOGGER.warning(message)
            return _dropped_background_job(queued_job, message)
        raise


def _dropped_background_job(queued_job: QueuedBackgroundJob, message: str) -> BackgroundJob:
    now = datetime.now(timezone.utc)
    return BackgroundJob(
        id=queued_job.job_id,
        portfolio_id=queued_job.portfolio_id,
        job_type=queued_job.job_type,
        status="dropped",
        message=message,
        created_at=now,
        updated_at=now,
    )


def _deferred_until(payload: dict[str, Any]) -> datetime | None:
    raw_value = payload.get("deferred_until")
    if not raw_value:
        return None
    try:
        value = datetime.fromisoformat(str(raw_value))
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _requeue_market_data_job(
    repository: Any,
    queued_job: QueuedBackgroundJob,
    *,
    payload: dict[str, Any] | None = None,
    message: str,
) -> BackgroundJob:
    job = repository.complete_background_job(
        queued_job.portfolio_id,
        queued_job.job_id,
        status="pending",
        message=message,
    )
    enqueue_background_job_message(job, payload=payload or queued_job.payload)
    return job


def _market_data_account_signature(portfolio: Any) -> str:
    user_id = getattr(portfolio, "user_id", None)
    if not user_id:
        return "account-global"
    from app.auth.security import hash_token

    return f"account-{hash_token(f'market-data:{user_id}')[:24]}"


def _market_data_tickers(repository: Any, portfolio: Any) -> list[str]:
    tickers: list[str] = []
    seen: set[str] = set()
    settings = repository.get_portfolio_settings(portfolio.id)
    for ticker in portfolio_tickers(portfolio) + list(settings.benchmark_symbols):
        normalized = str(ticker).strip().upper()
        if normalized and normalized not in seen:
            tickers.append(normalized)
            seen.add(normalized)
    return tickers


def run_worker(*, once: bool = False, block_timeout_seconds: int = 5) -> BackgroundJob | None:
    repository = create_portfolio_repository()
    LOGGER.info("Portfolio background worker started.")
    while True:
        queued_job = dequeue_background_job_message(block_timeout_seconds=block_timeout_seconds)
        if queued_job is None:
            if once:
                return None
            continue

        try:
            result = process_background_job(repository, queued_job)
        except Exception:
            LOGGER.exception("Background job %s failed.", queued_job.job_id)
            if once:
                raise
            continue

        if once:
            return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the portfolio background worker.")
    parser.add_argument("--once", action="store_true", help="Process one queued job and exit.")
    parser.add_argument("--timeout", type=int, default=5, help="Redis BLPOP timeout in seconds.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_worker(once=args.once, block_timeout_seconds=args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
