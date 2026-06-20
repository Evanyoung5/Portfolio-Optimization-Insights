from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from app.background.queue import background_queue_name, redis_client_from_env
from app.db.repository import create_portfolio_repository


def check_api(url: str | None = None) -> int:
    target = url or os.getenv("HEALTHCHECK_URL", "http://127.0.0.1:8000/health")
    try:
        with urllib.request.urlopen(target, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"API health check failed: {exc}", file=sys.stderr)
        return 1
    if payload.get("status") != "ok":
        print(f"API health check returned unexpected payload: {payload}", file=sys.stderr)
        return 1
    return 0


def check_worker() -> int:
    try:
        repository = create_portfolio_repository()
        if hasattr(repository, "_connect"):
            with repository._connect() as conn:  # type: ignore[attr-defined]
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    row = cur.fetchone()
                    if not row or row[0] != 1:
                        raise RuntimeError("Database probe did not return 1.")
    except Exception as exc:
        print(f"Worker database check failed: {exc}", file=sys.stderr)
        return 1

    try:
        client = redis_client_from_env()
        if not client.ping():
            raise RuntimeError("Redis ping returned false.")
        client.llen(background_queue_name())
    except Exception as exc:
        print(f"Worker Redis check failed: {exc}", file=sys.stderr)
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Health checks for production containers.")
    parser.add_argument("target", choices=("api", "worker"))
    parser.add_argument("--url", help="Override API health URL.")
    args = parser.parse_args(argv)

    if args.target == "api":
        return check_api(url=args.url)
    return check_worker()


if __name__ == "__main__":
    raise SystemExit(main())
