from datetime import date, datetime
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PositionInput(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    quantity: float = Field(..., ge=0)
    price: float = Field(..., ge=0)
    asset_class: str = Field(default="equity", min_length=1, max_length=50)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value: object) -> str:
        return str(value).strip().upper()

    @field_validator("asset_class", mode="before")
    @classmethod
    def normalize_asset_class(cls, value: object) -> str:
        return str(value).strip().lower()


class ManualPositionLotInput(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    quantity: float = Field(..., gt=0)
    purchase_price: float = Field(..., gt=0)
    current_price: float | None = Field(default=None, gt=0)
    fees: float = Field(default=0, ge=0)
    remaining_quantity: float | None = Field(default=None, gt=0)
    purchased_at: datetime | None = None
    asset_class: str = Field(default="equity", min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="before")
    @classmethod
    def accept_symbol_alias(cls, value: object) -> object:
        if isinstance(value, dict) and "ticker" not in value and "symbol" in value:
            value = {**value, "ticker": value["symbol"]}
        return value

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: object) -> str:
        return str(value).strip().upper()

    @field_validator("asset_class", mode="before")
    @classmethod
    def normalize_lot_asset_class(cls, value: object) -> str:
        return str(value).strip().lower()

    @model_validator(mode="after")
    def validate_remaining_quantity(self) -> "ManualPositionLotInput":
        if self.remaining_quantity is not None and self.remaining_quantity > self.quantity:
            raise ValueError("remaining_quantity cannot exceed quantity.")
        return self


class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    cash: float = Field(default=0, ge=0)
    positions: list[PositionInput] = Field(default_factory=list)
    lots: list[ManualPositionLotInput] = Field(default_factory=list)

    @field_validator("base_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> str:
        return str(value).strip().upper()


class PositionResponse(PositionInput):
    market_value: float


class PortfolioResponse(BaseModel):
    id: str
    name: str
    base_currency: str
    cash: float
    positions: list[PositionResponse]
    created_at: str
    updated_at: str


class CSVUploadResponse(BaseModel):
    portfolio_id: str
    imported_positions: int
    total_market_value: float
    detected_format: Literal["generic", "fidelity", "etrade", "schwab", "coinbase"] = "generic"
    rows_read: int = 0
    warnings: list[str] = Field(default_factory=list)


class PositionWeight(BaseModel):
    symbol: str
    asset_class: str
    market_value: float
    weight: float


class PortfolioAnalysisResponse(BaseModel):
    portfolio_id: str
    total_market_value: float
    total_equity: float
    cash: float
    position_count: int
    weights: list[PositionWeight]
    asset_class_exposure: dict[str, float]


class OptimizationRequest(BaseModel):
    objective: Literal["max_sharpe", "min_volatility", "equal_weight"] = "equal_weight"
    min_weight: float = Field(default=0, ge=0, le=1)
    max_weight: float = Field(default=1, ge=0, le=1)
    risk_free_rate: float = Field(default=0.02, ge=0)
    target_return: float | None = Field(default=None, ge=0)


class TargetAllocation(BaseModel):
    symbol: str
    current_weight: float
    target_weight: float
    current_value: float
    target_value: float
    trade_value_delta: float


class OptimizationResponse(BaseModel):
    portfolio_id: str
    objective: str
    total_equity: float
    allocations: list[TargetAllocation]
    notes: list[str] = Field(default_factory=list)


class VolatilityBandResponse(BaseModel):
    min_volatility: float
    max_volatility: float | None = None
    display_range: str
    narrative: str


class RiskToleranceProfileResponse(BaseModel):
    score: int
    label: str
    description: str
    target_volatility: float
    volatility_band: VolatilityBandResponse
    target_allocation: dict[str, float]
    volatility_explanation: str


class PortfolioRiskModelResponse(BaseModel):
    model_volatility: float
    estimated_score: int
    estimated_label: str
    volatility_band: VolatilityBandResponse
    asset_class_allocation: dict[str, float]


class RiskToleranceStateResponse(BaseModel):
    portfolio_id: str
    profile: RiskToleranceProfileResponse
    current_model: PortfolioRiskModelResponse


class RiskReweightRequest(BaseModel):
    risk_score: int | None = Field(default=None, ge=1, le=10)
    bond_symbols: list[str] = Field(default_factory=list, max_length=12)
    max_position_weight: float = Field(default=0.35, ge=0.05, le=1)

    @field_validator("bond_symbols", mode="before")
    @classmethod
    def normalize_bond_symbols(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = value.split(",")
        if not isinstance(value, list):
            raise ValueError("bond_symbols must be a list of symbols.")
        normalized: list[str] = []
        for symbol in value:
            clean = str(symbol).strip().upper()
            if clean and clean not in normalized:
                normalized.append(clean)
        return normalized


class RiskTargetAllocationResponse(BaseModel):
    symbol: str
    asset_class: str
    risk_bucket: str
    current_value: float
    current_weight: float
    target_value: float
    target_weight: float
    trade_value_delta: float
    price: float | None = None
    estimated_quantity_delta: float | None = None


class RiskReweightResponse(BaseModel):
    portfolio_id: str
    total_equity: float
    profile: RiskToleranceProfileResponse
    current_model: PortfolioRiskModelResponse
    allocations: list[RiskTargetAllocationResponse]
    notes: list[str] = Field(default_factory=list)


class BondRungInput(BaseModel):
    label: str | None = Field(default=None, max_length=80)
    ticker: str | None = Field(default=None, max_length=20)
    allocation_weight: float = Field(default=0, ge=0, le=1)
    face_value: float = Field(default=1000, gt=0, le=10_000_000)
    market_price_pct: float = Field(default=100, gt=0, le=1000)
    coupon_rate: float = Field(default=0.04, ge=0, le=1)
    yield_to_maturity: float = Field(default=0.04, gt=-1, le=1)
    years_to_maturity: float = Field(..., gt=0, le=50)
    payments_per_year: Literal[1, 2, 4, 12] = 2

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_optional_ticker(cls, value: object) -> str | None:
        clean = str(value or "").strip().upper()
        return clean or None


class BondStrategyRequest(BaseModel):
    strategy_type: Literal["ladder", "barbell"] = "ladder"
    capital: float = Field(default=10_000, gt=0, le=1_000_000_000)
    risk_score: int | None = Field(default=None, ge=1, le=10)
    rungs: list[BondRungInput] = Field(..., min_length=1, max_length=12)


class BondRungResultResponse(BaseModel):
    label: str
    ticker: str | None = None
    weight: float
    allocated_capital: float
    face_value: float
    market_price_pct: float
    market_price: float
    theoretical_price_pct: float
    coupon_rate: float
    yield_to_maturity: float
    years_to_maturity: float
    payments_per_year: int
    units: float
    annual_income: float
    current_yield: float
    maturity_principal: float
    projected_terminal_value: float
    total_return: float
    annualized_return: float
    macaulay_duration: float
    modified_duration: float


class BondStrategySummaryResponse(BaseModel):
    allocated_capital: float
    annual_income: float
    portfolio_current_yield: float
    weighted_yield_to_maturity: float
    weighted_modified_duration: float
    weighted_annualized_return: float
    projected_maturity_proceeds: float


class BondCashFlowResponse(BaseModel):
    year: int
    coupon_income: float
    principal: float
    total_cash_flow: float


class BondStrategyResponse(BaseModel):
    strategy_type: str
    risk_score: int
    capital: float
    summary: BondStrategySummaryResponse
    rungs: list[BondRungResultResponse]
    cash_flow_schedule: list[BondCashFlowResponse]
    notes: list[str] = Field(default_factory=list)


class BondAssetResponse(BaseModel):
    ticker: str
    name: str
    category: str
    duration_bucket: str
    term_proxy_years: float
    credit_quality: str
    risk_level: int
    model_volatility: float
    description: str
    issuer_url: str
    monitored: bool = False
    price: float | None = None
    previous_close: float | None = None
    daily_return_pct: float | None = None
    fetched_at: str | None = None


class BondAssetsResponse(BaseModel):
    portfolio_id: str
    assets: list[BondAssetResponse]
    missing_tickers: list[str]
    recommended_ladder: list[BondRungInput]
    recommended_barbell: list[BondRungInput]
    note: str
    recommendation_note: str = ""


class BondAssetRefreshRequest(BaseModel):
    tickers: list[str] = Field(default_factory=list, max_length=24)

    @field_validator("tickers", mode="before")
    @classmethod
    def normalize_tickers(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = value.split(",")
        if not isinstance(value, list):
            raise ValueError("tickers must be a list of symbols.")
        normalized: list[str] = []
        for symbol in value:
            clean = str(symbol).strip().upper()
            if clean and clean not in normalized:
                normalized.append(clean)
        return normalized


class TradeImpactRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: Literal["buy", "sell"]
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    estimated_slippage_bps: float = Field(default=5, ge=0)
    fee_rate_bps: float = Field(default=1, ge=0)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value: object) -> str:
        return str(value).strip().upper()


class TradeImpactResponse(BaseModel):
    portfolio_id: str
    symbol: str
    side: str
    notional: float
    estimated_fees: float
    estimated_slippage: float
    cash_delta: float
    pre_trade_equity: float
    post_trade_equity: float
    position_quantity_delta: float
    resulting_weight: float

    model_config = ConfigDict(protected_namespaces=())


class ChartPoint(BaseModel):
    label: str
    value: float


class MatrixCell(BaseModel):
    row: str
    column: str
    value: float


class MatrixChart(BaseModel):
    tickers: list[str]
    values: list[list[float]]
    heatmap: list[MatrixCell]


class PortfolioSummary(BaseModel):
    total_market_value: float
    total_equity: float
    cash: float
    position_count: int


class PriceHistoryInput(BaseModel):
    tickers: list[str] = Field(..., min_length=1)
    prices: list[list[float | None]] = Field(..., min_length=2)

    @field_validator("tickers", mode="before")
    @classmethod
    def normalize_tickers(cls, value: object) -> list[str]:
        if isinstance(value, str):
            raise ValueError("tickers must be a list of ticker symbols.")
        return [str(ticker).strip().upper() for ticker in value]

    @model_validator(mode="after")
    def validate_price_rows(self) -> "PriceHistoryInput":
        if len(set(self.tickers)) != len(self.tickers):
            raise ValueError("tickers must be unique.")
        if any(not ticker for ticker in self.tickers):
            raise ValueError("tickers cannot contain blanks.")
        expected_width = len(self.tickers)
        for index, row in enumerate(self.prices, start=1):
            if len(row) != expected_width:
                raise ValueError(
                    f"price row {index} has {len(row)} values; expected {expected_width}."
                )
        return self


class PortfolioAnalyzeRequest(BaseModel):
    price_history: PriceHistoryInput | None = None
    use_rmt_cleaning: bool = True


class PortfolioRiskCharts(BaseModel):
    covariance: MatrixChart
    correlation: MatrixChart
    pairwise_observations: MatrixChart
    cleaned_correlation: MatrixChart | None = None
    cleaned_covariance: MatrixChart | None = None
    volatility_by_ticker: list[ChartPoint]
    observations: int
    annualization_factor: float = 252.0


class PortfolioAnalysisCharts(BaseModel):
    weights: list[ChartPoint]
    asset_class_exposure: list[ChartPoint]
    risk: PortfolioRiskCharts | None = None


class PortfolioAnalyzeResponse(BaseModel):
    portfolio_id: str
    summary: PortfolioSummary
    charts: PortfolioAnalysisCharts


class HeatmapMarketDataInput(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    price: float | None = Field(default=None, gt=0)
    previous_close: float | None = Field(default=None, gt=0)
    daily_return_pct: float | None = None
    sector: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=120)

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: object) -> str:
        return str(value).strip().upper()


class PortfolioHeatmapRequest(BaseModel):
    market_data: list[HeatmapMarketDataInput] = Field(default_factory=list)
    group_by: Literal["asset_class", "sector", "industry"] = "sector"


class HeatmapNode(BaseModel):
    id: str
    label: str
    parent: str | None = None
    level: Literal["portfolio", "group", "position"]
    ticker: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_value: float
    cost_basis: float | None = None
    portfolio_weight: float
    portfolio_weight_pct: float
    daily_return_pct: float
    price: float | None = None
    previous_close: float | None = None
    unrealized_pnl: float | None = None
    unrealized_return_pct: float | None = None


class PortfolioHeatmapResponse(BaseModel):
    portfolio_id: str
    generated_at: str
    title: str
    size_metric: str
    color_metric: str
    group_by: Literal["asset_class", "sector", "industry"]
    total_market_value: float
    nodes: list[HeatmapNode]
    holdings: list[HeatmapNode]
    plotly: dict[str, object]


class TradeProposalInput(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    side: Literal["buy", "sell"]
    quantity: float | None = Field(default=None, gt=0)
    notional: float | None = Field(default=None, gt=0)
    price: float | None = Field(default=None, gt=0)

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: object) -> str:
        return str(value).strip().upper()

    @model_validator(mode="after")
    def validate_quantity_or_notional(self) -> "TradeProposalInput":
        has_quantity = self.quantity is not None
        has_notional = self.notional is not None
        if has_quantity == has_notional:
            raise ValueError("each trade must include exactly one of quantity or notional.")
        return self


class TradeSimulationRequest(BaseModel):
    trades: list[TradeProposalInput] = Field(..., min_length=1)
    covariance: dict[str, dict[str, float]] = Field(..., min_length=1)

    @model_validator(mode="after")
    def normalize_and_validate_covariance(self) -> "TradeSimulationRequest":
        normalized: dict[str, dict[str, float]] = {}
        for row_ticker, row in self.covariance.items():
            normalized_row_ticker = str(row_ticker).strip().upper()
            if not normalized_row_ticker:
                raise ValueError("covariance tickers cannot be blank.")
            if not row:
                raise ValueError(f"covariance row {normalized_row_ticker} cannot be empty.")
            normalized[normalized_row_ticker] = {
                str(column_ticker).strip().upper(): value
                for column_ticker, value in row.items()
            }

        tickers = set(normalized)
        if any(not ticker for ticker in tickers):
            raise ValueError("covariance tickers cannot be blank.")
        for row_ticker, row in normalized.items():
            if set(row) != tickers:
                raise ValueError("covariance must be square and indexed by the same tickers.")
            for value in row.values():
                if not isfinite(value):
                    raise ValueError("covariance entries must be finite numbers.")
            if row[row_ticker] < 0:
                raise ValueError("covariance diagonal entries must be non-negative.")

        self.covariance = normalized
        return self


class WeightComparisonPoint(BaseModel):
    ticker: str
    before: float
    after: float


class RiskContributionPoint(BaseModel):
    ticker: str
    before: float
    after: float


class ConcentrationComparison(BaseModel):
    before: dict[str, float | str | None | int]
    after: dict[str, float | str | None | int]


class TradeSimulationCharts(BaseModel):
    weights: list[WeightComparisonPoint]
    marginal_risk_contributions: list[RiskContributionPoint]
    component_risk_contributions: list[RiskContributionPoint]
    component_risk_contribution_pct: list[RiskContributionPoint]
    concentration: ConcentrationComparison


class PortfolioTradeSimulationResponse(BaseModel):
    portfolio_id: str
    before_volatility: float
    after_volatility: float
    volatility_delta: float
    charts: TradeSimulationCharts

    model_config = ConfigDict(protected_namespaces=())


class ManualLotsRequest(BaseModel):
    lots: list[ManualPositionLotInput] = Field(..., min_length=1)


class CashTransactionInput(BaseModel):
    transaction_type: Literal[
        "deposit",
        "withdrawal",
        "transfer_in",
        "transfer_out",
        "dividend",
        "interest",
        "fee",
        "tax",
        "adjustment_in",
        "adjustment_out",
    ]
    amount: float = Field(..., gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    occurred_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("transaction_type", mode="before")
    @classmethod
    def normalize_transaction_type(cls, value: object) -> str:
        return str(value).strip().lower()

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_cash_currency(cls, value: object) -> str | None:
        if value is None:
            return None
        return str(value).strip().upper()


class CashTransactionResponse(BaseModel):
    id: str
    transaction_type: str
    amount: float
    cash_delta: float
    external_flow: float
    currency: str
    occurred_at: str
    source: str
    notes: str | None = None
    created_at: str


class CashTransactionsResponse(BaseModel):
    portfolio_id: str
    current_cash: float
    net_contributions: float
    transactions: list[CashTransactionResponse]


class ManualTradeInput(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    side: Literal["buy", "sell"]
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    fees: float = Field(default=0, ge=0)
    occurred_at: datetime | None = None
    asset_class: str = Field(default="equity", min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="before")
    @classmethod
    def accept_symbol_alias(cls, value: object) -> object:
        if isinstance(value, dict) and "ticker" not in value and "symbol" in value:
            value = {**value, "ticker": value["symbol"]}
        return value

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_trade_ticker(cls, value: object) -> str:
        return str(value).strip().upper()

    @field_validator("side", mode="before")
    @classmethod
    def normalize_trade_side(cls, value: object) -> str:
        return str(value).strip().lower()

    @field_validator("asset_class", mode="before")
    @classmethod
    def normalize_trade_asset_class(cls, value: object) -> str:
        return str(value).strip().lower()


class TradeTransactionResponse(BaseModel):
    id: str
    ticker: str
    side: str
    quantity: float
    price: float
    notional: float
    fees: float
    cash_delta: float
    realized_gain_loss: float | None = None
    asset_class: str
    occurred_at: str
    source: str
    lot_ids: list[str]
    notes: str | None = None
    created_at: str


class TradeTransactionsResponse(BaseModel):
    portfolio_id: str
    trades: list[TradeTransactionResponse]


class PortfolioSettingsUpdate(BaseModel):
    risk_free_rate: float | None = Field(default=None, ge=-1, le=1)
    benchmark_symbols: list[str] | None = Field(default=None, max_length=20)
    cash_target_pct: float | None = Field(default=None, ge=0, le=1)
    risk_tolerance_score: int | None = Field(default=None, ge=1, le=10)
    bond_watchlist: list[str] | None = Field(default=None, max_length=12)

    @field_validator("benchmark_symbols", mode="before")
    @classmethod
    def normalize_benchmark_symbols(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise ValueError("benchmark_symbols must be a list of symbols.")
        normalized: list[str] = []
        seen: set[str] = set()
        for symbol in value:
            clean = str(symbol).strip().upper()
            if clean and clean not in seen:
                normalized.append(clean)
                seen.add(clean)
        return normalized

    @field_validator("bond_watchlist", mode="before")
    @classmethod
    def normalize_bond_watchlist(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.split(",")
        if not isinstance(value, list):
            raise ValueError("bond_watchlist must be a list of symbols.")
        normalized: list[str] = []
        for symbol in value:
            clean = str(symbol).strip().upper()
            if clean and clean not in normalized:
                normalized.append(clean)
        return normalized


class PortfolioSettingsResponse(BaseModel):
    portfolio_id: str
    risk_free_rate: float
    benchmark_symbols: list[str]
    cash_target_pct: float | None = None
    risk_tolerance_score: int = 5
    bond_watchlist: list[str] = Field(default_factory=list)
    updated_at: str


class PortfolioPerformanceSummary(BaseModel):
    invested_market_value: float
    idle_cash: float
    cash_weight: float
    net_contributions: float
    account_growth: float
    account_growth_pct: float
    risk_free_rate: float
    benchmark_symbols: list[str]


class PositionLotResponse(BaseModel):
    id: str
    ticker: str
    quantity: float
    remaining_quantity: float
    purchase_price: float
    current_price: float
    fees: float
    asset_class: str
    purchased_at: str
    cost_basis: float
    market_value: float
    unrealized_gain_loss: float
    source: str
    notes: str | None = None


class CostBasisPositionResponse(BaseModel):
    ticker: str
    asset_class: str
    quantity: float
    current_price: float
    market_value: float
    cost_basis: float
    average_cost: float
    unrealized_gain_loss: float
    unrealized_gain_loss_pct: float
    lots_count: int


class ManualPortfolioTotals(BaseModel):
    market_value: float
    cost_basis: float
    cash: float
    total_equity: float
    unrealized_gain_loss: float
    unrealized_gain_loss_pct: float


class ManualPortfolioCharts(BaseModel):
    allocation_by_ticker: list[ChartPoint]
    market_value_by_ticker: list[ChartPoint]
    cost_basis_by_ticker: list[ChartPoint]
    unrealized_gain_loss_by_ticker: list[ChartPoint]


class BackgroundJobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    message: str | None = None
    created_at: str
    updated_at: str


class MarketQuoteResponse(BaseModel):
    ticker: str
    provider: str
    price: float
    previous_close: float | None = None
    daily_return_pct: float | None = None
    currency: str | None = None
    sector: str | None = None
    industry: str | None = None
    fetched_at: str
    updated_at: str


class PortfolioMarketDataResponse(BaseModel):
    portfolio_id: str
    quotes: list[MarketQuoteResponse]
    missing_tickers: list[str] = Field(default_factory=list)


class MarketHistoryPointResponse(BaseModel):
    as_of: str
    close: float


class MarketHistorySeriesResponse(BaseModel):
    ticker: str
    provider_ticker: str
    provider: str
    period: str
    interval: str
    fetched_at: str
    points: list[MarketHistoryPointResponse]
    warnings: list[str] = Field(default_factory=list)


class PortfolioPerformancePointResponse(BaseModel):
    as_of: str
    value: float


class PortfolioHistoryCoverageResponse(BaseModel):
    effective_start: str | None = None
    end: str | None = None
    quality: Literal["complete_ledger", "reconstructed_opening_lots", "estimated_opening_snapshot", "partial_market_data", "unavailable"]
    partial_history: bool
    note: str


class PortfolioPerformanceHistoryResponse(BaseModel):
    portfolio_id: str
    range_name: str
    period: str
    interval: str
    series: list[MarketHistorySeriesResponse]
    portfolio_series: list[PortfolioPerformancePointResponse] = Field(default_factory=list)
    coverage: PortfolioHistoryCoverageResponse
    missing_tickers: list[str] = Field(default_factory=list)
    queued_job: BackgroundJobResponse | None = None


class RelativisticBSParameters(BaseModel):
    tau: float
    expiry_date: date | None = None
    rate: float
    sigma: float
    c_m: float
    option_type: Literal["call", "put"]
    strike_min_pct: float
    strike_max_pct: float
    n_strikes: int


class RelativisticBSRow(BaseModel):
    strike: float
    bs_price: float
    relativistic_price: float
    relativistic_price_unclipped: float
    price_correction: float
    paper_iv_approx: float | None = None
    bs_implied_vol_from_rel_price: float | None = None


class RelativisticBSOptionSide(BaseModel):
    bs_price: float
    relativistic_price: float
    relativistic_price_unclipped: float
    price_correction: float
    paper_iv_approx: float | None = None
    bs_implied_vol_from_rel_price: float | None = None
    market_last: float | None = None
    bid: float | None = None
    ask: float | None = None
    market_iv: float | None = None
    volume: float | None = None
    open_interest: float | None = None
    contract_symbol: str | None = None
    in_the_money: bool | None = None


class RelativisticBSOptionChainRow(BaseModel):
    strike: float
    call: RelativisticBSOptionSide
    put: RelativisticBSOptionSide




class RelativisticBSVolatilityEstimate(BaseModel):
    label: str
    value: float
    source: str
    detail: str


class RelativisticBSVolatilityGuide(BaseModel):
    selected_sigma: float
    recommended_sigma: float
    estimates: list[RelativisticBSVolatilityEstimate] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class RelativisticBSVolatilitySmilePoint(BaseModel):
    strike: float
    moneyness: float
    call_iv: float | None = None
    put_iv: float | None = None
    average_iv: float | None = None
    baseline_iv: float


class RelativisticBSCumulativeVolumePoint(BaseModel):
    strike: float
    call_volume: float
    put_volume: float
    total_volume: float
    cumulative_call_volume: float
    cumulative_put_volume: float
    call_open_interest: float
    put_open_interest: float


class RelativisticBSGammaExposurePoint(BaseModel):
    strike: float
    call_gamma_exposure: float
    put_gamma_exposure: float
    net_gamma_exposure: float
    gross_gamma_exposure: float


class RelativisticBSIVSurfacePoint(BaseModel):
    expiry_date: date
    tau: float
    strike: float
    moneyness: float
    call_iv: float | None = None
    put_iv: float | None = None
    average_iv: float | None = None


class PortfolioRelativisticBSResponse(BaseModel):
    portfolio_id: str
    model: str
    symbol: str
    spot: float
    parameters: RelativisticBSParameters
    summary: list[ChartPoint]
    rows: list[RelativisticBSRow]
    option_chain: list[RelativisticBSOptionChainRow] = Field(default_factory=list)
    baseline_volatility: RelativisticBSVolatilityGuide
    volatility_smile: list[RelativisticBSVolatilitySmilePoint] = Field(default_factory=list)
    cumulative_volume: list[RelativisticBSCumulativeVolumePoint] = Field(default_factory=list)
    gamma_exposure: list[RelativisticBSGammaExposurePoint] = Field(default_factory=list)
    iv_surface: list[RelativisticBSIVSurfacePoint] = Field(default_factory=list)
    chain_source: str = "generated"
    actual_expiry_date: date | None = None
    warnings: list[str] = Field(default_factory=list)


class RelativisticBSHistoryPoint(BaseModel):
    as_of: str
    expiry_date: date
    spot: float
    atm_strike: float
    atm_iv: float | None = None
    total_gamma_exposure: float
    total_volume: float
    atm_market_price: float | None = None
    atm_bs_price: float
    atm_relativistic_price: float


class PortfolioRelativisticBSHistoryResponse(BaseModel):
    portfolio_id: str
    symbol: str
    expiry_date: date | None = None
    requested_resolution: Literal["auto", "raw", "hour", "day", "week"]
    resolution: Literal["raw", "hour", "day", "week"]
    limited: bool
    lookback_days: int
    points: list[RelativisticBSHistoryPoint] = Field(default_factory=list)
    note: str


class ValuationSnapshotResponse(BaseModel):
    id: str
    as_of: str
    market_value: float
    cash: float
    total_equity: float
    net_contributions: float
    metadata: dict[str, object] = Field(default_factory=dict)


class ManualPortfolioStateResponse(BaseModel):
    portfolio_id: str
    name: str
    base_currency: str
    totals: ManualPortfolioTotals
    performance: PortfolioPerformanceSummary
    settings: PortfolioSettingsResponse
    positions: list[CostBasisPositionResponse]
    lots: list[PositionLotResponse]
    cash_transactions: list[CashTransactionResponse]
    trade_history: list[TradeTransactionResponse]
    charts: ManualPortfolioCharts
    valuation_snapshots: list[ValuationSnapshotResponse] = Field(default_factory=list)
    background_jobs: list[BackgroundJobResponse]


class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> str:
        normalized = str(value).strip().lower()
        if "@" not in normalized:
            raise ValueError("A valid email address is required.")
        return normalized


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> str:
        normalized = str(value).strip().lower()
        if "@" not in normalized:
            raise ValueError("A valid email address is required.")
        return normalized


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: str
    email_verified: bool = False


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=512)


class PasswordResetRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> str:
        normalized = str(value).strip().lower()
        if "@" not in normalized:
            raise ValueError("A valid email address is required.")
        return normalized


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)
    new_password: str = Field(..., min_length=8, max_length=256)


class EmailVerificationRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)


class TokenRequestResponse(BaseModel):
    message: str
    dev_token: str | None = None


class MessageResponse(BaseModel):
    message: str


class UserPortfolioSummary(BaseModel):
    id: str
    name: str
    base_currency: str
    cash: float
    total_market_value: float
    total_equity: float
    positions_count: int
    updated_at: str


class UserPortfoliosResponse(BaseModel):
    portfolios: list[UserPortfolioSummary]
