#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


def request_json(
    url: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    headers: dict | None = None,
    allow_insecure_localhost: bool = False,
) -> dict:
    data = None
    request_headers = {"Content-Type": "application/json"} if body is not None else {}
    if headers:
        request_headers.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, method=method, data=data, headers=request_headers)
    context = None
    parsed = urllib.parse.urlparse(url)
    if allow_insecure_localhost and parsed.scheme == "https" and parsed.hostname in {"localhost", "127.0.0.1"}:
        context = ssl._create_unverified_context()
    with urllib.request.urlopen(request, timeout=20, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Basic smoke test for the production deployment.")
    parser.add_argument("--base-url", default="http://localhost", help="Public base URL for the deployed app.")
    parser.add_argument("--email", help="Optional smoke-test user email.")
    parser.add_argument("--password", help="Optional smoke-test user password.")
    parser.add_argument(
        "--allow-insecure-localhost",
        action="store_true",
        help="Allow self-signed localhost HTTPS during local deployment drills.",
    )
    args = parser.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    parsed_base = urllib.parse.urlparse(base_url)
    local_base = parsed_base.hostname in {"localhost", "127.0.0.1"}
    checks = []

    try:
        health = request_json(
            f"{base_url}/health",
            allow_insecure_localhost=args.allow_insecure_localhost or local_base,
        )
        checks.append(("health", health.get("status") == "ok", health))
    except Exception as exc:
        checks.append(("health", False, str(exc)))

    try:
        runtime = request_json(
            f"{base_url}/runtime",
            allow_insecure_localhost=args.allow_insecure_localhost or local_base,
        )
        checks.append(("runtime", runtime.get("status") == "ok", runtime))
    except Exception as exc:
        checks.append(("runtime", False, str(exc)))

    if args.email and args.password:
        try:
            payload = request_json(
                f"{base_url}/auth/login",
                method="POST",
                body={"email": args.email, "password": args.password},
                allow_insecure_localhost=args.allow_insecure_localhost or local_base,
            )
            checks.append(("auth_login", bool(payload.get("user", {}).get("email")), payload.get("user", {})))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            checks.append(("auth_login", False, detail))
        except Exception as exc:
            checks.append(("auth_login", False, str(exc)))

    failed = [name for name, ok, _ in checks if not ok]
    for name, ok, payload in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {payload}")

    if failed:
        print(f"Smoke test failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
