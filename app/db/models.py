from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any


@dataclass(slots=True)
class User:
    id: str
    email: str
    password_hash: str
    email_verified_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class AuthTokenRecord:
    id: str
    user_id: str
    token_hash: str
    token_type: str
    expires_at: datetime
    consumed_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_active(self) -> bool:
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return self.consumed_at is None and self.revoked_at is None and expires_at > now


@dataclass(slots=True)
class MarketQuote:
    ticker: str
    price: float
    provider: str = "manual"
    previous_close: float | None = None
    daily_return_pct: float | None = None
    currency: str | None = None
    sector: str | None = None
    industry: str | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class OptionChainHistorySnapshot:
    id: str
    ticker: str
    provider: str
    expiry: date
    fetched_at: datetime
    snapshot_hash: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class PositionLot:
    id: str
    symbol: str
    quantity: float
    purchase_price: float
    current_price: float
    asset_class: str = "equity"
    fees: float = 0
    remaining_quantity: float | None = None
    purchased_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "manual"
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity

    @property
    def remaining_cost_basis(self) -> float:
        if self.quantity <= 0 or self.remaining_quantity is None:
            return 0
        remaining_ratio = self.remaining_quantity / self.quantity
        return (self.remaining_quantity * self.purchase_price) + (self.fees * remaining_ratio)

    @property
    def market_value(self) -> float:
        return (self.remaining_quantity or 0) * self.current_price

    @property
    def unrealized_gain_loss(self) -> float:
        return self.market_value - self.remaining_cost_basis


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: float
    price: float
    asset_class: str = "equity"
    cost_basis: float = 0
    average_cost: float = 0
    unrealized_gain_loss: float = 0
    lots_count: int = 0

    @property
    def market_value(self) -> float:
        return self.quantity * self.price


@dataclass(slots=True)
class BackgroundJob:
    id: str
    portfolio_id: str
    job_type: str
    status: str = "pending"
    message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class CashTransaction:
    id: str
    portfolio_id: str
    transaction_type: str
    amount: float
    currency: str = "USD"
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "manual"
    notes: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class TradeTransaction:
    id: str
    portfolio_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    fees: float = 0
    asset_class: str = "equity"
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    realized_gain_loss: float | None = None
    lot_ids: list[str] = field(default_factory=list)
    source: str = "manual"
    notes: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def notional(self) -> float:
        return self.quantity * self.price

    @property
    def cash_delta(self) -> float:
        if self.side == "buy":
            return -(self.notional + self.fees)
        return self.notional - self.fees


@dataclass(slots=True)
class PortfolioSettings:
    portfolio_id: str
    risk_free_rate: float = 0.02
    benchmark_symbols: list[str] = field(default_factory=list)
    cash_target_pct: float | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class PortfolioValuationSnapshot:
    id: str
    portfolio_id: str
    as_of: datetime
    market_value: float
    cash: float
    total_equity: float
    net_contributions: float
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class Portfolio:
    id: str
    name: str
    base_currency: str
    user_id: str | None = None
    cash: float = 0
    positions: list[Position] = field(default_factory=list)
    lots: list[PositionLot] = field(default_factory=list)
    background_jobs: list[BackgroundJob] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
