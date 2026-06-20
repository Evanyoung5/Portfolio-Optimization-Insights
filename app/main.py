import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

APP_BUILD_ID = "runtime-risk-bonds-2026-06-19"

from app.api.routes import portfolio_repository, public_router, router as api_router
from app.background.queue import redis_client_from_env
from app.security import (
    default_security_headers,
    frontend_origins,
    redact_runtime_payload,
    trusted_hosts,
    validate_runtime_configuration,
)


def _frontend_origins() -> list[str]:
    configured = frontend_origins()
    if configured:
        return configured
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def _trusted_hosts() -> list[str] | None:
    hosts = trusted_hosts()
    if not hosts:
        return None
    return hosts or None


@asynccontextmanager
async def _lifespan(_: FastAPI):
    validate_runtime_configuration()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Portfolio Optimization API",
        version="0.1.0",
        description="Backend API for portfolio analysis, optimization, and trade-impact simulation.",
        lifespan=_lifespan,
    )

    trusted_hosts = _trusted_hosts()
    if trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_frontend_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        for header, value in default_security_headers().items():
            response.headers.setdefault(header, value)
        return response

    @app.get("/runtime", tags=["health"])
    def runtime_check() -> dict[str, object]:
        return redact_runtime_payload(_runtime_payload())

    @app.get("/api/v1/runtime", tags=["health"])
    def api_runtime_check() -> dict[str, object]:
        return redact_runtime_payload(_runtime_payload())

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=frontend_dir), name="frontend-static")

        @app.get("/", include_in_schema=False)
        def frontend_index() -> FileResponse:
            return FileResponse(frontend_dir / "index.html", headers={"Cache-Control": "no-store"})

        @app.get("/app", include_in_schema=False)
        def frontend_app() -> FileResponse:
            return FileResponse(frontend_dir / "index.html", headers={"Cache-Control": "no-store"})

    app.include_router(public_router)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()


def _runtime_payload() -> dict[str, object]:
    repository = portfolio_repository
    payload: dict[str, object] = {
        "status": "ok",
        "build_id": os.getenv("APP_BUILD_ID", APP_BUILD_ID),
        "repository": type(repository).__name__,
        "database": _database_identity(),
        "redis": _redis_identity(),
    }
    return payload


def _database_identity() -> dict[str, object]:
    identity: dict[str, object] = {
        "kind": os.getenv("PORTFOLIO_REPOSITORY", "memory"),
        "url": _safe_database_url(os.getenv("DATABASE_URL")),
        "users": None,
        "portfolios": None,
        "market_quotes": None,
    }
    repository = portfolio_repository
    try:
        if hasattr(repository, "_connect"):
            with repository._connect() as conn:  # type: ignore[attr-defined]
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM users")
                    identity["users"] = int(cur.fetchone()[0])
                    cur.execute("SELECT COUNT(*) FROM portfolios")
                    identity["portfolios"] = int(cur.fetchone()[0])
                    cur.execute("SELECT COUNT(*) FROM market_quotes")
                    identity["market_quotes"] = int(cur.fetchone()[0])
        else:
            identity["users"] = len(getattr(repository, "_users", {}))
            identity["portfolios"] = len(getattr(repository, "_portfolios", {}))
            identity["market_quotes"] = len(getattr(repository, "_market_quotes", {}))
    except Exception as exc:
        identity["error"] = str(exc)
    return identity


def _safe_database_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    parsed = urlparse(raw_url)
    host = parsed.hostname or "localhost"
    port = f":{parsed.port}" if parsed.port else ""
    name = parsed.path.lstrip("/") or "default"
    return f"{parsed.scheme}://{host}{port}/{name}"


def _redis_identity() -> dict[str, object]:
    identity: dict[str, object] = {"url": _safe_redis_url(os.getenv("REDIS_URL")), "ok": False}
    try:
        client = redis_client_from_env()
        identity["ok"] = bool(client.ping())
        identity["keys"] = int(client.dbsize())
    except Exception as exc:
        identity["error"] = str(exc)
    return identity


def _safe_redis_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    parsed = urlparse(raw_url)
    host = parsed.hostname or "localhost"
    port = f":{parsed.port}" if parsed.port else ""
    db = parsed.path or "/0"
    return f"{parsed.scheme}://{host}{port}{db}"
