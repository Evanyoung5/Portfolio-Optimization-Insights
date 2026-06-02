import csv
import os
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from io import StringIO

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from pydantic import ValidationError

from app.api.health import health_payload
from app.auth.security import (
    AuthError,
    create_access_token,
    create_opaque_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.background.queue import enqueue_background_job_message
from app.background.portfolio_tasks import (
    create_lots_from_aggregate_positions,
    create_valuation_snapshot,
    delete_portfolio_position,
    delete_position_lot,
    rebuild_portfolio_positions,
    record_cash_transaction,
    record_manual_lots,
    record_manual_trade,
    update_portfolio_settings,
)
from app.api.schemas import (
    AuthTokenResponse,
    BackgroundJobResponse,
    CSVUploadResponse,
    CashTransactionInput,
    CashTransactionsResponse,
    EmailVerificationRequest,
    LogoutRequest,
    ManualLotsRequest,
    ManualPortfolioStateResponse,
    ManualTradeInput,
    MessageResponse,
    OptimizationRequest,
    OptimizationResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PortfolioAnalysisResponse,
    PortfolioAnalyzeRequest,
    PortfolioAnalyzeResponse,
    PortfolioCreate,
    PortfolioHeatmapRequest,
    PortfolioHeatmapResponse,
    PortfolioMarketDataResponse,
    PortfolioPerformanceHistoryResponse,
    PortfolioRelativisticBSResponse,
    PortfolioRelativisticBSHistoryResponse,
    PortfolioResponse,
    PortfolioSettingsResponse,
    PortfolioSettingsUpdate,
    RefreshTokenRequest,
    PositionInput,
    PositionResponse,
    UserLoginRequest,
    UserPortfolioSummary,
    UserPortfoliosResponse,
    UserRegisterRequest,
    UserResponse,
    TokenRequestResponse,
    TradeImpactRequest,
    TradeImpactResponse,
    TradeSimulationRequest,
    TradeTransactionsResponse,
    PortfolioTradeSimulationResponse,
)
from app.api.services import (
    build_background_job_response,
    build_cash_transactions_response,
    build_manual_portfolio_state,
    build_market_data_response,
    build_performance_history_response,
    build_portfolio_analysis,
    build_portfolio_heatmap_response,
    build_portfolio_settings_response,
    build_relativistic_bs_analysis,
    build_relativistic_bs_history_response,
    build_trade_simulation,
    build_trade_transactions_response,
)
from app.connectors.market_data.limiter import RateLimitExceeded, enforce_market_data_refresh_limits
from app.connectors.market_data.history import PriceHistoryBundle, get_cached_price_history, history_spec_for_range
from app.connectors.market_data.service import get_cached_market_data_for_portfolio, portfolio_tickers
from app.connectors.email import send_email_verification_email, send_password_reset_email
from app.db.models import BackgroundJob, Portfolio, Position, User
from app.db.repository import create_portfolio_repository
from app.quant.portfolio import analyze_portfolio, optimize_portfolio, simulate_trade_impact

router = APIRouter()
portfolio_repository = create_portfolio_repository()


def _optional_current_user(authorization: str | None = Header(default=None)) -> User | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use a bearer token.",
        )
    try:
        payload = decode_access_token(token)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = portfolio_repository.get_user(str(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")
    return user


def _current_user(current_user: User | None = Depends(_optional_current_user)) -> User:
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login is required.")
    return current_user


def _get_portfolio_or_404(portfolio_id: str, current_user: User | None = None) -> Portfolio:
    portfolio = portfolio_repository.get(portfolio_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio '{portfolio_id}' was not found.",
        )
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login is required.")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio was not found.")
    return portfolio


def _queue_market_data_refresh(
    portfolio: Portfolio,
    *,
    force: bool,
    automatic: bool,
    raise_on_queue_error: bool,
) -> BackgroundJob | None:
    latest = portfolio_repository.get(portfolio.id) or portfolio
    if not latest.positions:
        return None

    pending = _pending_market_data_refresh(latest)
    if pending is not None:
        if pending.status == "pending":
            return _enqueue_market_data_refresh_message(
                latest,
                pending,
                force=force,
                automatic=automatic,
                raise_on_queue_error=raise_on_queue_error,
            )
        return pending

    job = portfolio_repository.enqueue_background_job(
        latest.id,
        "refresh_market_data",
        message=(
            "Queued automatic market-data refresh."
            if automatic
            else "Queued market-data refresh."
        ),
    )
    return _enqueue_market_data_refresh_message(
        latest,
        job,
        force=force,
        automatic=automatic,
        raise_on_queue_error=raise_on_queue_error,
    )


def _enqueue_market_data_refresh_message(
    portfolio: Portfolio,
    job: BackgroundJob,
    *,
    force: bool,
    automatic: bool,
    raise_on_queue_error: bool,
) -> BackgroundJob:
    try:
        enqueue_background_job_message(
            job,
            payload={
                "automatic": automatic,
                "force": force,
                "defer_on_rate_limit": True,
                "provider_signature": _market_data_account_signature(portfolio.user_id),
            },
        )
    except Exception as exc:
        failed = portfolio_repository.complete_background_job(
            portfolio.id,
            job.id,
            status="failed",
            message=f"Could not enqueue Redis worker job: {exc}",
        )
        if raise_on_queue_error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Background worker queue is unavailable.",
            ) from exc
        return failed
    return job


def _queue_automatic_market_data_refresh(portfolio: Portfolio) -> BackgroundJob | None:
    return _queue_market_data_refresh(
        portfolio,
        force=False,
        automatic=True,
        raise_on_queue_error=False,
    )


def _market_data_account_signature(user_id: str | None) -> str:
    if not user_id:
        return "account-global"
    return f"account-{hash_token(f'market-data:{user_id}')[:24]}"


def _enforce_market_data_refresh_limits(user_id: str, portfolio_id: str) -> None:
    try:
        enforce_market_data_refresh_limits(user_id=user_id, portfolio_id=portfolio_id)
    except RateLimitExceeded:
        raise
    except Exception:
        if os.getenv("MARKET_DATA_REQUIRE_REDIS_LIMITER", "false").strip().lower() in {"1", "true", "yes", "on"}:
            raise


def _pending_market_data_refresh(portfolio: Portfolio) -> BackgroundJob | None:
    pending = [
        job
        for job in portfolio.background_jobs
        if job.job_type == "refresh_market_data" and job.status in {"pending", "running"}
    ]
    if not pending:
        return None
    return sorted(pending, key=lambda job: (job.created_at, job.id))[-1]


def _queue_market_history_refresh(
    portfolio: Portfolio,
    *,
    range_name: str,
    tickers: list[str],
    raise_on_queue_error: bool,
) -> BackgroundJob | None:
    normalized_tickers = _normalize_unique_symbols(tickers)
    if not normalized_tickers:
        return None
    latest = portfolio_repository.get(portfolio.id) or portfolio
    pending = _pending_market_history_refresh(latest)
    if pending is not None:
        if pending.status == "pending":
            return _enqueue_market_history_refresh_message(
                latest,
                pending,
                range_name=range_name,
                tickers=normalized_tickers,
                raise_on_queue_error=raise_on_queue_error,
            )
        return pending
    job = portfolio_repository.enqueue_background_job(
        latest.id,
        "refresh_market_history",
        message="Queued market-history refresh for zoomable performance charts.",
    )
    return _enqueue_market_history_refresh_message(
        latest,
        job,
        range_name=range_name,
        tickers=normalized_tickers,
        raise_on_queue_error=raise_on_queue_error,
    )


def _enqueue_market_history_refresh_message(
    portfolio: Portfolio,
    job: BackgroundJob,
    *,
    range_name: str,
    tickers: list[str],
    raise_on_queue_error: bool,
) -> BackgroundJob:
    try:
        enqueue_background_job_message(
            job,
            payload={
                "range_name": history_spec_for_range(range_name).range_name,
                "ranges": _history_ranges_for_zoom(range_name),
                "tickers": tickers,
                "force": False,
                "defer_on_rate_limit": True,
                "provider_signature": _market_data_account_signature(portfolio.user_id),
            },
        )
    except Exception as exc:
        failed = portfolio_repository.complete_background_job(
            portfolio.id,
            job.id,
            status="failed",
            message=f"Could not enqueue Redis worker job: {exc}",
        )
        if raise_on_queue_error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Background worker queue is unavailable.",
            ) from exc
        return failed
    return job


def _pending_market_history_refresh(portfolio: Portfolio) -> BackgroundJob | None:
    pending = [
        job
        for job in portfolio.background_jobs
        if job.job_type == "refresh_market_history" and job.status in {"pending", "running"}
    ]
    if not pending:
        return None
    return sorted(pending, key=lambda job: (job.created_at, job.id))[-1]


def _normalize_unique_symbols(symbols: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        clean = str(symbol).strip().upper()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized


def _history_ranges_for_zoom(range_name: str) -> list[str]:
    primary = history_spec_for_range(range_name).range_name
    # Cache the requested view and a daily one-year baseline for dashboard risk
    # statistics. Fine intraday history is only queued after the user selects or
    # zooms into a short view, so a max-range chart never triggers 5-minute data.
    companions = {
        "max": ["max", "year"],
        "five_year": ["five_year", "year"],
        "year": ["year"],
        "ytd": ["ytd"],
        "month": ["month", "year"],
        "week": ["week", "year"],
        "day": ["day", "year"],
    }
    return list(dict.fromkeys(companions.get(primary, [primary])))


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return health_payload()


@router.post(
    "/auth/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
def register_user(payload: UserRegisterRequest) -> AuthTokenResponse:
    try:
        user = portfolio_repository.create_user(
            email=payload.email,
            password_hash=hash_password(payload.password),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _auth_response(user)


@router.post("/auth/login", response_model=AuthTokenResponse, tags=["auth"])
def login_user(payload: UserLoginRequest) -> AuthTokenResponse:
    user = portfolio_repository.get_user_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    return _auth_response(user)


@router.post("/auth/refresh", response_model=AuthTokenResponse, tags=["auth"])
def refresh_auth_token(payload: RefreshTokenRequest) -> AuthTokenResponse:
    record = _active_token_or_401(payload.refresh_token, "refresh")
    portfolio_repository.revoke_auth_token(record.id)
    user = portfolio_repository.get_user(record.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")
    return _auth_response(user)


@router.post("/auth/logout", response_model=MessageResponse, tags=["auth"])
def logout_user(payload: LogoutRequest) -> MessageResponse:
    record = portfolio_repository.get_auth_token(
        token_hash=hash_token(payload.refresh_token),
        token_type="refresh",
    )
    if record is not None and record.revoked_at is None:
        portfolio_repository.revoke_auth_token(record.id)
    return MessageResponse(message="Logged out.")


@router.post("/auth/password-reset/request", response_model=TokenRequestResponse, tags=["auth"])
def request_password_reset(payload: PasswordResetRequest) -> TokenRequestResponse:
    user = portfolio_repository.get_user_by_email(payload.email)
    dev_token = None
    if user is not None:
        token = _create_auth_token(user.id, "password_reset", _password_reset_seconds())
        send_password_reset_email(to_email=user.email, token=token)
        dev_token = token if _expose_dev_tokens() else None
    return TokenRequestResponse(
        message="If an account exists for that email, a password reset link has been prepared.",
        dev_token=dev_token,
    )


@router.post("/auth/password-reset/confirm", response_model=MessageResponse, tags=["auth"])
def confirm_password_reset(payload: PasswordResetConfirmRequest) -> MessageResponse:
    record = _active_token_or_400(payload.token, "password_reset")
    portfolio_repository.update_user_password(record.user_id, hash_password(payload.new_password))
    portfolio_repository.consume_auth_token(record.id)
    portfolio_repository.revoke_user_tokens(user_id=record.user_id, token_type="refresh")
    return MessageResponse(message="Password has been reset.")


@router.post("/auth/email-verification/request", response_model=TokenRequestResponse, tags=["auth"])
def request_email_verification(current_user: User = Depends(_current_user)) -> TokenRequestResponse:
    token = _create_auth_token(current_user.id, "email_verification", _email_verification_seconds())
    send_email_verification_email(to_email=current_user.email, token=token)
    return TokenRequestResponse(
        message="Email verification link has been prepared.",
        dev_token=token if _expose_dev_tokens() else None,
    )


@router.post("/auth/email-verification/confirm", response_model=UserResponse, tags=["auth"])
def confirm_email_verification(payload: EmailVerificationRequest) -> UserResponse:
    record = _active_token_or_400(payload.token, "email_verification")
    user = portfolio_repository.mark_user_email_verified(record.user_id)
    portfolio_repository.consume_auth_token(record.id)
    return _serialize_user(user)


@router.get("/me", response_model=UserResponse, tags=["auth"])
def get_me(current_user: User = Depends(_current_user)) -> UserResponse:
    return _serialize_user(current_user)


@router.get("/me/portfolios", response_model=UserPortfoliosResponse, tags=["portfolios"])
def list_my_portfolios(current_user: User = Depends(_current_user)) -> UserPortfoliosResponse:
    return UserPortfoliosResponse(
        portfolios=[_portfolio_summary(portfolio) for portfolio in portfolio_repository.list_portfolios(user_id=current_user.id)]
    )


@router.post(
    "/portfolios",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["portfolios"],
)
def create_portfolio(
    payload: PortfolioCreate,
    current_user: User = Depends(_current_user),
) -> PortfolioResponse:
    positions = [
        Position(
            symbol=position.symbol,
            quantity=position.quantity,
            price=position.price,
            asset_class=position.asset_class,
            cost_basis=position.quantity * position.price,
            average_cost=position.price if position.quantity else 0,
            unrealized_gain_loss=0,
            lots_count=1 if position.quantity else 0,
        )
        for position in payload.positions
    ]
    lots = create_lots_from_aggregate_positions(positions) if positions and not payload.lots else []
    portfolio = portfolio_repository.create(
        name=payload.name,
        base_currency=payload.base_currency,
        cash=0,
        positions=positions,
        lots=lots,
        user_id=current_user.id if current_user else None,
    )
    if payload.lots:
        portfolio = record_manual_lots(
            portfolio_repository,
            portfolio.id,
            [lot.model_dump(exclude_none=True) for lot in payload.lots],
        )
    elif lots:
        portfolio = rebuild_portfolio_positions(portfolio_repository, portfolio.id)
    if portfolio.positions:
        create_valuation_snapshot(
            portfolio_repository,
            portfolio.id,
            metadata={"event": "portfolio_created"},
        )
    if payload.cash > 0:
        portfolio = record_cash_transaction(
            portfolio_repository,
            portfolio.id,
            {
                "transaction_type": "deposit",
                "amount": payload.cash,
                "currency": payload.base_currency,
                "source": "initial_cash_balance",
                "notes": "Initial manually entered idle cash balance.",
            },
        )
    _queue_automatic_market_data_refresh(portfolio)
    return _serialize_portfolio(portfolio)


@router.post(
    "/portfolios/{portfolio_id}/upload-csv",
    response_model=CSVUploadResponse,
    tags=["portfolios"],
)
async def upload_positions_csv(
    portfolio_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(_current_user),
) -> CSVUploadResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    raw_content = await file.read()

    try:
        decoded = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV must be UTF-8 encoded.",
        ) from exc

    positions, warnings = _parse_positions_csv(decoded)
    if not positions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV did not contain any valid positions.",
        )

    updated = portfolio_repository.replace_positions(portfolio.id, positions)
    create_valuation_snapshot(
        portfolio_repository,
        portfolio.id,
        metadata={"event": "csv_positions_uploaded", "positions": len(positions)},
    )
    _queue_automatic_market_data_refresh(updated)
    return CSVUploadResponse(
        portfolio_id=updated.id,
        imported_positions=len(positions),
        total_market_value=sum(position.market_value for position in updated.positions),
        warnings=warnings,
    )


@router.get(
    "/portfolios/{portfolio_id}/analysis",
    response_model=PortfolioAnalysisResponse,
    tags=["analysis"],
)
def get_portfolio_analysis(
    portfolio_id: str,
    current_user: User = Depends(_current_user),
) -> dict[str, object]:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    return analyze_portfolio(portfolio)


@router.get(
    "/portfolios/{portfolio_id}",
    response_model=ManualPortfolioStateResponse,
    tags=["portfolios"],
)
def get_manual_portfolio_state(
    portfolio_id: str,
    current_user: User = Depends(_current_user),
) -> ManualPortfolioStateResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    return build_manual_portfolio_state(portfolio, portfolio_repository)


@router.post(
    "/portfolios/{portfolio_id}/lots",
    response_model=ManualPortfolioStateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["portfolios"],
)
def add_manual_position_lots(
    portfolio_id: str,
    payload: ManualLotsRequest,
    current_user: User = Depends(_current_user),
) -> ManualPortfolioStateResponse:
    _get_portfolio_or_404(portfolio_id, current_user)
    try:
        portfolio = record_manual_lots(
            portfolio_repository,
            portfolio_id,
            [lot.model_dump(exclude_none=True) for lot in payload.lots],
        )
        _queue_automatic_market_data_refresh(portfolio)
        portfolio = portfolio_repository.get(portfolio_id) or portfolio
        return build_manual_portfolio_state(portfolio, portfolio_repository)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete(
    "/portfolios/{portfolio_id}/lots/{lot_id}",
    response_model=ManualPortfolioStateResponse,
    tags=["portfolios"],
)
def remove_manual_position_lot(
    portfolio_id: str,
    lot_id: str,
    current_user: User = Depends(_current_user),
) -> ManualPortfolioStateResponse:
    _get_portfolio_or_404(portfolio_id, current_user)
    try:
        portfolio = delete_position_lot(portfolio_repository, portfolio_id, lot_id)
        portfolio = portfolio_repository.get(portfolio_id) or portfolio
        return build_manual_portfolio_state(portfolio, portfolio_repository)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/portfolios/{portfolio_id}/positions/{symbol}",
    response_model=ManualPortfolioStateResponse,
    tags=["portfolios"],
)
def remove_portfolio_position(
    portfolio_id: str,
    symbol: str,
    current_user: User = Depends(_current_user),
) -> ManualPortfolioStateResponse:
    _get_portfolio_or_404(portfolio_id, current_user)
    try:
        portfolio = delete_portfolio_position(portfolio_repository, portfolio_id, symbol)
        portfolio = portfolio_repository.get(portfolio_id) or portfolio
        return build_manual_portfolio_state(portfolio, portfolio_repository)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/portfolios/{portfolio_id}/cash-transactions",
    response_model=CashTransactionsResponse,
    tags=["portfolios"],
)
def list_cash_transactions(
    portfolio_id: str,
    current_user: User = Depends(_current_user),
) -> CashTransactionsResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    return build_cash_transactions_response(portfolio, portfolio_repository)


@router.post(
    "/portfolios/{portfolio_id}/cash-transactions",
    response_model=ManualPortfolioStateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["portfolios"],
)
def add_cash_transaction(
    portfolio_id: str,
    payload: CashTransactionInput,
    current_user: User = Depends(_current_user),
) -> ManualPortfolioStateResponse:
    _get_portfolio_or_404(portfolio_id, current_user)
    try:
        portfolio = record_cash_transaction(
            portfolio_repository,
            portfolio_id,
            payload.model_dump(exclude_none=True),
        )
        return build_manual_portfolio_state(portfolio, portfolio_repository)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/portfolios/{portfolio_id}/trades",
    response_model=TradeTransactionsResponse,
    tags=["portfolios"],
)
def list_manual_trades(
    portfolio_id: str,
    current_user: User = Depends(_current_user),
) -> TradeTransactionsResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    return build_trade_transactions_response(portfolio, portfolio_repository)


@router.post(
    "/portfolios/{portfolio_id}/trades",
    response_model=ManualPortfolioStateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["portfolios"],
)
def add_manual_trade(
    portfolio_id: str,
    payload: ManualTradeInput,
    current_user: User = Depends(_current_user),
) -> ManualPortfolioStateResponse:
    _get_portfolio_or_404(portfolio_id, current_user)
    try:
        portfolio = record_manual_trade(
            portfolio_repository,
            portfolio_id,
            payload.model_dump(exclude_none=True),
        )
        if payload.side == "buy":
            _queue_automatic_market_data_refresh(portfolio)
            portfolio = portfolio_repository.get(portfolio_id) or portfolio
        return build_manual_portfolio_state(portfolio, portfolio_repository)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/portfolios/{portfolio_id}/settings",
    response_model=PortfolioSettingsResponse,
    tags=["portfolios"],
)
def get_portfolio_settings(
    portfolio_id: str,
    current_user: User = Depends(_current_user),
) -> PortfolioSettingsResponse:
    _get_portfolio_or_404(portfolio_id, current_user)
    return build_portfolio_settings_response(portfolio_repository.get_portfolio_settings(portfolio_id))


@router.patch(
    "/portfolios/{portfolio_id}/settings",
    response_model=PortfolioSettingsResponse,
    tags=["portfolios"],
)
def patch_portfolio_settings(
    portfolio_id: str,
    payload: PortfolioSettingsUpdate,
    current_user: User = Depends(_current_user),
) -> PortfolioSettingsResponse:
    _get_portfolio_or_404(portfolio_id, current_user)
    try:
        settings = update_portfolio_settings(
            portfolio_repository,
            portfolio_id,
            payload.model_dump(exclude_unset=True),
        )
        return build_portfolio_settings_response(settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/portfolios/{portfolio_id}/jobs/rebuild-positions",
    response_model=BackgroundJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["jobs"],
)
def enqueue_position_rebuild_job(
    portfolio_id: str,
    current_user: User = Depends(_current_user),
) -> BackgroundJobResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    job = portfolio_repository.enqueue_background_job(
        portfolio.id,
        "rebuild_positions",
        message="Queued position rebuild for background worker.",
    )
    try:
        enqueue_background_job_message(job)
    except Exception as exc:
        portfolio_repository.complete_background_job(
            portfolio.id,
            job.id,
            status="failed",
            message=f"Could not enqueue Redis worker job: {exc}",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background worker queue is unavailable.",
        ) from exc
    return build_background_job_response(job)


@router.get(
    "/portfolios/{portfolio_id}/market-data",
    response_model=PortfolioMarketDataResponse,
    tags=["market-data"],
)
def get_portfolio_market_data(
    portfolio_id: str,
    current_user: User = Depends(_current_user),
) -> PortfolioMarketDataResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    quotes = get_cached_market_data_for_portfolio(portfolio, portfolio_repository)
    benchmark_quotes = portfolio_repository.get_market_quotes(
        _portfolio_benchmark_tickers(portfolio),
        max_age_seconds=None,
    )
    by_ticker = {quote.ticker: quote for quote in quotes + benchmark_quotes}
    return build_market_data_response(portfolio, list(by_ticker.values()))


@router.get(
    "/portfolios/{portfolio_id}/performance-history",
    response_model=PortfolioPerformanceHistoryResponse,
    tags=["market-data"],
)
def get_portfolio_performance_history(
    portfolio_id: str,
    range_name: str = Query("max", description="Chart range to cache: day, week, month, ytd, year, five_year, or max."),
    benchmark_symbols: str | None = Query(None, description="Comma-separated benchmark tickers selected in the UI."),
    current_user: User = Depends(_current_user),
) -> PortfolioPerformanceHistoryResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    benchmarks = _parse_symbol_csv(benchmark_symbols) or _portfolio_benchmark_tickers(portfolio)
    tickers = _portfolio_history_tickers(portfolio, benchmarks)
    spec = history_spec_for_range(range_name)
    try:
        bundle = get_cached_price_history(tickers, range_name=spec.range_name)
    except Exception:
        bundle = PriceHistoryBundle(
            range_name=spec.range_name,
            period=spec.period,
            interval=spec.interval,
            series=[],
            missing_tickers=tickers,
        )
    queued_job = None
    if bundle.missing_tickers:
        queued_job = _queue_market_history_refresh(
            portfolio,
            range_name=bundle.range_name,
            tickers=tickers,
            raise_on_queue_error=False,
        )
    return build_performance_history_response(
        portfolio,
        bundle,
        repository=portfolio_repository,
        queued_job=queued_job,
    )


@router.post(
    "/portfolios/{portfolio_id}/market-data/refresh",
    response_model=BackgroundJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["market-data"],
)
def enqueue_market_data_refresh_job(
    portfolio_id: str,
    current_user: User = Depends(_current_user),
) -> BackgroundJobResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    existing = _pending_market_data_refresh(portfolio)
    if existing is not None:
        if existing.status == "pending":
            job = _queue_market_data_refresh(
                portfolio,
                force=True,
                automatic=False,
                raise_on_queue_error=True,
            )
            if job is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Portfolio has no tickers to refresh.")
            return build_background_job_response(job)
        return build_background_job_response(existing)

    try:
        _enforce_market_data_refresh_limits(user_id=current_user.id, portfolio_id=portfolio.id)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    job = _queue_market_data_refresh(
        portfolio,
        force=True,
        automatic=False,
        raise_on_queue_error=True,
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Portfolio has no tickers to refresh.")
    return build_background_job_response(job)


@router.get(
    "/portfolios/{portfolio_id}/relativistic-bs",
    response_model=PortfolioRelativisticBSResponse,
    tags=["relativistic-bs"],
)
def get_portfolio_relativistic_bs(
    portfolio_id: str,
    symbol: str | None = Query(None, description="Optional holding symbol; defaults to first priced holding."),
    expiry_date: date | None = Query(None, description="Option expiry date as YYYY-MM-DD."),
    tau: float | None = Query(None, gt=0, description="Legacy time to expiry in years; ignored when expiry_date is supplied."),
    rate: float = Query(0.05, description="Continuously compounded risk-free rate."),
    sigma: float = Query(0.15, gt=0, description="Baseline Black-Scholes volatility."),
    c_m: float = Query(2.5, gt=0, description="Effective maximum log-return velocity."),
    option_type: Literal["call", "put"] = Query("call"),
    use_market_chain: bool = Query(False, description="Fetch a cached/rate-limited yfinance option chain when possible."),
    strike_min_pct: float = Query(0.7, gt=0, lt=5),
    strike_max_pct: float = Query(1.3, gt=0, lt=5),
    n_strikes: int = Query(41, ge=5, le=200),
    surface_expiries: int = Query(4, ge=1, le=8, description="Maximum listed expiries to include in the IV surface."),
    history_period: str = Query("1y", description="Historical yfinance period for realized volatility guidance."),
    force_market_chain: bool = Query(False, description="Bypass Redis cache and capture a new rate-limited yfinance snapshot."),
    current_user: User = Depends(_current_user),
) -> PortfolioRelativisticBSResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    quotes = get_cached_market_data_for_portfolio(portfolio, portfolio_repository)
    model_tau = _relativistic_bs_tau(expiry_date, tau)
    try:
        return build_relativistic_bs_analysis(
            portfolio,
            symbol=symbol,
            tau=model_tau,
            expiry_date=expiry_date,
            rate=rate,
            sigma=sigma,
            c_m=c_m,
            option_type=option_type,
            strike_min_pct=strike_min_pct,
            strike_max_pct=strike_max_pct,
            n_strikes=n_strikes,
            cached_quotes=quotes,
            use_market_chain=use_market_chain,
            provider_signature=f"account-{hash_token(f'options:{current_user.id}')[:24]}",
            surface_expiries=surface_expiries,
            history_period=history_period,
            snapshot_repository=portfolio_repository,
            force_market_chain=force_market_chain,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/portfolios/{portfolio_id}/relativistic-bs/history",
    response_model=PortfolioRelativisticBSHistoryResponse,
    tags=["relativistic-bs"],
)
def get_portfolio_relativistic_bs_history(
    portfolio_id: str,
    symbol: str,
    expiry_date: date | None = Query(None, description="Optional listed expiry to filter."),
    resolution: Literal["auto", "raw", "hour", "day", "week"] = Query("auto"),
    lookback_days: int = Query(365, ge=1, le=365),
    rate: float = Query(0.05),
    sigma: float = Query(0.15, gt=0),
    c_m: float = Query(2.5, gt=0),
    current_user: User = Depends(_current_user),
) -> PortfolioRelativisticBSHistoryResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="symbol is required.")
    records = portfolio_repository.list_option_chain_snapshots(
        normalized_symbol,
        expiry=expiry_date,
        since=datetime.now(timezone.utc) - timedelta(days=lookback_days),
    )
    return build_relativistic_bs_history_response(
        portfolio,
        records,
        symbol=normalized_symbol,
        expiry_date=expiry_date,
        requested_resolution=resolution,
        lookback_days=lookback_days,
        rate=rate,
        sigma=sigma,
        c_m=c_m,
    )


def _relativistic_bs_tau(expiry_date: date | None, tau: float | None) -> float:
    if expiry_date is None:
        return tau if tau is not None else 0.5

    today = date.today()
    days_to_expiry = (expiry_date - today).days
    if days_to_expiry <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expiry_date must be after today's date.",
        )
    return days_to_expiry / 365.25


@router.get(
    "/portfolios/{portfolio_id}/heatmap",
    response_model=PortfolioHeatmapResponse,
    tags=["heatmap"],
)
def get_portfolio_heatmap(
    portfolio_id: str,
    current_user: User = Depends(_current_user),
) -> PortfolioHeatmapResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    quotes = get_cached_market_data_for_portfolio(portfolio, portfolio_repository)
    return build_portfolio_heatmap_response(portfolio, PortfolioHeatmapRequest(), cached_quotes=quotes)


@router.post(
    "/portfolios/{portfolio_id}/heatmap",
    response_model=PortfolioHeatmapResponse,
    tags=["heatmap"],
)
def create_portfolio_heatmap(
    portfolio_id: str,
    payload: PortfolioHeatmapRequest | None = None,
    current_user: User = Depends(_current_user),
) -> PortfolioHeatmapResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    request = payload or PortfolioHeatmapRequest()
    quotes = get_cached_market_data_for_portfolio(portfolio, portfolio_repository)
    return build_portfolio_heatmap_response(portfolio, request, cached_quotes=quotes)


@router.post(
    "/portfolios/{portfolio_id}/analyze",
    response_model=PortfolioAnalyzeResponse,
    tags=["analysis"],
)
def analyze_portfolio_for_charts(
    portfolio_id: str,
    payload: PortfolioAnalyzeRequest | None = None,
    current_user: User = Depends(_current_user),
) -> PortfolioAnalyzeResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    payload = payload or PortfolioAnalyzeRequest()
    try:
        return build_portfolio_analysis(portfolio, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/portfolios/{portfolio_id}/simulate-trade",
    response_model=PortfolioTradeSimulationResponse,
    tags=["simulation"],
)
def simulate_trade_for_charts(
    portfolio_id: str,
    payload: TradeSimulationRequest,
    current_user: User = Depends(_current_user),
) -> PortfolioTradeSimulationResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    try:
        return build_trade_simulation(portfolio, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/portfolios/{portfolio_id}/optimize",
    response_model=OptimizationResponse,
    tags=["optimization"],
)
def optimize_portfolio_endpoint(
    portfolio_id: str,
    payload: OptimizationRequest,
    current_user: User = Depends(_current_user),
) -> dict[str, object]:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    try:
        return optimize_portfolio(
            portfolio=portfolio,
            objective=payload.objective,
            min_weight=payload.min_weight,
            max_weight=payload.max_weight,
            risk_free_rate=payload.risk_free_rate,
            target_return=payload.target_return,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/portfolios/{portfolio_id}/simulate-trade-impact",
    response_model=TradeImpactResponse,
    tags=["simulation"],
)
def simulate_trade_impact_endpoint(
    portfolio_id: str,
    payload: TradeImpactRequest,
    current_user: User = Depends(_current_user),
) -> dict[str, object]:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    try:
        return simulate_trade_impact(
            portfolio=portfolio,
            symbol=payload.symbol,
            side=payload.side,
            quantity=payload.quantity,
            price=payload.price,
            estimated_slippage_bps=payload.estimated_slippage_bps,
            fee_rate_bps=payload.fee_rate_bps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _portfolio_benchmark_tickers(portfolio: Portfolio) -> list[str]:
    try:
        return portfolio_repository.get_portfolio_settings(portfolio.id).benchmark_symbols
    except Exception:
        return []


def _portfolio_history_tickers(portfolio: Portfolio, benchmark_symbols: list[str]) -> list[str]:
    return _normalize_unique_symbols(portfolio_tickers(portfolio) + list(benchmark_symbols))


def _parse_symbol_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return _normalize_unique_symbols([item for item in value.split(",")])


def _serialize_user(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at.isoformat(),
        email_verified=user.email_verified_at is not None,
    )


def _auth_response(user: User) -> AuthTokenResponse:
    return AuthTokenResponse(
        access_token=create_access_token(
            user_id=user.id,
            email=user.email,
            expires_in_seconds=_access_token_seconds(),
        ),
        refresh_token=_create_auth_token(user.id, "refresh", _refresh_token_seconds()),
        user=_serialize_user(user),
    )


def _create_auth_token(user_id: str, token_type: str, expires_in_seconds: int) -> str:
    token = create_opaque_token()
    portfolio_repository.create_auth_token(
        user_id=user_id,
        token_hash=hash_token(token),
        token_type=token_type,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds),
    )
    return token


def _active_token_or_401(token: str, token_type: str):
    record = portfolio_repository.get_auth_token(
        token_hash=hash_token(token),
        token_type=token_type,
    )
    if record is None or not record.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    return record


def _active_token_or_400(token: str, token_type: str):
    record = portfolio_repository.get_auth_token(
        token_hash=hash_token(token),
        token_type=token_type,
    )
    if record is None or not record.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token.")
    return record


def _access_token_seconds() -> int:
    return int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", str(60 * 60 * 24 * 7)))


def _refresh_token_seconds() -> int:
    return int(os.getenv("REFRESH_TOKEN_EXPIRE_SECONDS", str(60 * 60 * 24 * 30)))


def _password_reset_seconds() -> int:
    return int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_SECONDS", "900"))


def _email_verification_seconds() -> int:
    return int(os.getenv("EMAIL_VERIFICATION_TOKEN_EXPIRE_SECONDS", str(60 * 60 * 24)))


def _expose_dev_tokens() -> bool:
    return os.getenv("AUTH_DEV_EXPOSE_TOKENS", "false").strip().lower() in {"1", "true", "yes", "on"}


def _portfolio_summary(portfolio: Portfolio) -> UserPortfolioSummary:
    total_market_value = sum(position.market_value for position in portfolio.positions)
    return UserPortfolioSummary(
        id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_currency,
        cash=portfolio.cash,
        total_market_value=total_market_value,
        total_equity=total_market_value + portfolio.cash,
        positions_count=len(portfolio.positions),
        updated_at=portfolio.updated_at.isoformat(),
    )


def _serialize_portfolio(portfolio: Portfolio) -> PortfolioResponse:
    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_currency,
        cash=portfolio.cash,
        positions=[
            PositionResponse(
                symbol=position.symbol,
                quantity=position.quantity,
                price=position.price,
                asset_class=position.asset_class,
                market_value=position.market_value,
            )
            for position in portfolio.positions
        ],
        created_at=portfolio.created_at.isoformat(),
        updated_at=portfolio.updated_at.isoformat(),
    )


def _parse_positions_csv(decoded: str) -> tuple[list[Position], list[str]]:
    reader = csv.DictReader(StringIO(decoded))
    if reader.fieldnames is None:
        return [], ["CSV is missing a header row."]

    fieldnames = {field.strip().lower(): field for field in reader.fieldnames if field}
    symbol_field = fieldnames.get("symbol") or fieldnames.get("ticker")
    quantity_field = fieldnames.get("quantity") or fieldnames.get("shares")
    price_field = fieldnames.get("price") or fieldnames.get("current_price")
    missing = [
        label
        for label, field in (
            ("symbol", symbol_field),
            ("quantity", quantity_field),
            ("price", price_field),
        )
        if field is None
    ]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"CSV is missing required column(s): {', '.join(missing)}.")

    positions: list[Position] = []
    warnings: list[str] = []
    for line_number, row in enumerate(reader, start=2):
        try:
            symbol = str(row.get(symbol_field, "")).strip().upper()
            quantity = float(row.get(quantity_field, "") or 0)
            price = float(row.get(price_field, "") or 0)
            asset_class = str(row.get(fieldnames.get("asset_class", ""), "equity") or "equity").strip().lower()
            if not symbol or quantity <= 0 or price <= 0:
                raise ValueError("symbol, quantity, and price must be positive/present")
            positions.append(
                Position(
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    asset_class=asset_class,
                    cost_basis=quantity * price,
                    average_cost=price,
                    unrealized_gain_loss=0,
                    lots_count=1,
                )
            )
        except (TypeError, ValueError) as exc:
            warnings.append(f"Line {line_number} skipped: {exc}.")
    return positions, warnings


public_router = APIRouter()
public_router.include_router(router)
