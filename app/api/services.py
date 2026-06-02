from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import numpy as np

from app.api.schemas import (
    BackgroundJobResponse,
    CashTransactionResponse,
    CashTransactionsResponse,
    ChartPoint,
    CostBasisPositionResponse,
    ManualPortfolioCharts,
    ManualPortfolioStateResponse,
    ManualPortfolioTotals,
    MarketHistoryPointResponse,
    MarketHistorySeriesResponse,
    MarketQuoteResponse,
    PortfolioMarketDataResponse,
    PortfolioPerformanceHistoryResponse,
    PortfolioPerformancePointResponse,
    PortfolioHistoryCoverageResponse,
    PortfolioRelativisticBSResponse,
    PortfolioRelativisticBSHistoryResponse,
    RelativisticBSHistoryPoint,
    RelativisticBSOptionChainRow,
    RelativisticBSParameters,
    RelativisticBSRow,
    MatrixCell,
    MatrixChart,
    PortfolioAnalyzeRequest,
    PortfolioAnalyzeResponse,
    PortfolioHeatmapRequest,
    PortfolioHeatmapResponse,
    PortfolioAnalysisCharts,
    PortfolioPerformanceSummary,
    PortfolioRiskCharts,
    PortfolioSettingsResponse,
    PortfolioSummary,
    PortfolioTradeSimulationResponse,
    PositionLotResponse,
    RiskContributionPoint,
    TradeSimulationCharts,
    TradeSimulationRequest,
    TradeTransactionResponse,
    ValuationSnapshotResponse,
    TradeTransactionsResponse,
    WeightComparisonPoint,
)
from app.background.portfolio_tasks import (
    cash_transaction_cash_delta,
    cash_transaction_external_flow,
    portfolio_cost_basis_totals,
)
from app.connectors.market_data.limiter import RateLimitExceeded
from app.connectors.market_data.options import fetch_option_suite_with_cache
from app.connectors.market_data.service import market_quotes_to_heatmap_data, portfolio_tickers
from app.connectors.market_data.yfinance import OptionChainSnapshot, OptionContract
from app.db.models import (
    CashTransaction,
    MarketQuote,
    OptionChainHistorySnapshot,
    Portfolio,
    PortfolioSettings,
    PortfolioValuationSnapshot,
    Position,
    PositionLot,
    TradeTransaction,
)
from app.quant.heatmap import build_portfolio_heatmap
from app.quant.portfolio import analyze_portfolio
from app.quant.rmt import (
    clean_correlation_rmt,
    compute_returns,
    covariance_from_clean_correlation,
    sample_correlation,
    sample_covariance,
)
from app.quant.trade_impact import analyze_trade_impact
from app.quant.relativistic_black_scholes import (
    black_scholes_price,
    make_option_chain_surface,
    make_surface,
    paper_implied_vol_approx,
    relativistic_bs_price_approx,
)
from app.quant.options_suite import (
    build_baseline_volatility_guide,
    build_cumulative_volume_profile,
    build_gamma_exposure_profile,
    build_iv_surface_points,
    build_volatility_smile,
)


def build_portfolio_analysis(
    portfolio: Portfolio,
    request: PortfolioAnalyzeRequest,
) -> PortfolioAnalyzeResponse:
    base_analysis = analyze_portfolio(portfolio)
    weights = [
        ChartPoint(label=str(item["symbol"]), value=float(item["weight"]))
        for item in base_analysis["weights"]
    ]
    asset_class_exposure = [
        ChartPoint(label=asset_class, value=float(weight))
        for asset_class, weight in base_analysis["asset_class_exposure"].items()
    ]

    risk_charts = None
    if request.price_history is not None:
        risk_charts = _build_risk_charts(
            tickers=request.price_history.tickers,
            prices=request.price_history.prices,
            use_rmt_cleaning=request.use_rmt_cleaning,
        )

    return PortfolioAnalyzeResponse(
        portfolio_id=portfolio.id,
        summary=PortfolioSummary(
            total_market_value=float(base_analysis["total_market_value"]),
            total_equity=float(base_analysis["total_equity"]),
            cash=float(base_analysis["cash"]),
            position_count=int(base_analysis["position_count"]),
        ),
        charts=PortfolioAnalysisCharts(
            weights=weights,
            asset_class_exposure=asset_class_exposure,
            risk=risk_charts,
        ),
    )


def build_portfolio_heatmap_response(
    portfolio: Portfolio,
    request: PortfolioHeatmapRequest,
    cached_quotes: list[MarketQuote] | None = None,
) -> PortfolioHeatmapResponse:
    market_data = [item.model_dump(exclude_none=True) for item in request.market_data]
    if not market_data and cached_quotes:
        market_data = market_quotes_to_heatmap_data(cached_quotes)
    payload = build_portfolio_heatmap(
        portfolio,
        market_data=market_data,
        group_by=request.group_by,
    )
    return PortfolioHeatmapResponse(**payload)


def build_relativistic_bs_analysis(
    portfolio: Portfolio,
    *,
    symbol: str | None,
    tau: float,
    expiry_date: date | None = None,
    rate: float,
    sigma: float,
    c_m: float,
    option_type: str,
    strike_min_pct: float,
    strike_max_pct: float,
    n_strikes: int,
    cached_quotes: list[MarketQuote] | None = None,
    use_market_chain: bool = False,
    provider_signature: str | None = None,
    surface_expiries: int = 4,
    history_period: str = "1y",
    snapshot_repository=None,
    force_market_chain: bool = False,
) -> PortfolioRelativisticBSResponse:
    if strike_min_pct >= strike_max_pct:
        raise ValueError("strike_min_pct must be less than strike_max_pct.")

    resolved_symbol, spot = _relativistic_bs_spot(portfolio, symbol, cached_quotes or [])
    warnings: list[str] = []
    chain_snapshot: OptionChainSnapshot | None = None
    surface_chain_snapshots: list[OptionChainSnapshot] = []
    price_history: list[tuple[date, float]] = []
    chain_source = "generated"

    if use_market_chain and expiry_date is not None:
        try:
            suite_snapshot, from_cache = fetch_option_suite_with_cache(
                resolved_symbol,
                expiry_date,
                provider_signature=provider_signature,
                max_expiries=surface_expiries,
                history_period=history_period,
                force=force_market_chain,
                snapshot_repository=snapshot_repository,
            )
            if suite_snapshot is not None:
                chain_snapshot = suite_snapshot.current_chain
                surface_chain_snapshots = suite_snapshot.surface_chains
                price_history = suite_snapshot.price_history.prices if suite_snapshot.price_history else []
                warnings.extend(suite_snapshot.warnings)
            if chain_snapshot is not None and (chain_snapshot.calls or chain_snapshot.puts):
                chain_source = "yfinance-cache" if from_cache else "yfinance"
                warnings.extend(chain_snapshot.warnings)
            else:
                warnings.append("No yfinance option contracts were available; using generated strikes.")
        except RateLimitExceeded as exc:
            warnings.append(
                f"Live option-suite fetch is rate-limited for about {exc.retry_after_seconds} second(s); using generated strikes."
            )
        except Exception as exc:
            warnings.append(f"Live yfinance option-suite fetch failed: {exc}. Using generated strikes.")
    elif not use_market_chain:
        warnings.append("Using generated strikes. Enable live chains to use yfinance option strikes when available.")

    strikes = _option_chain_strikes(
        spot,
        strike_min_pct,
        strike_max_pct,
        n_strikes,
        chain_snapshot if chain_source.startswith("yfinance") else None,
    )
    rows = [
        RelativisticBSRow(**row)
        for row in make_surface(spot, strikes, tau, rate, sigma, c_m, option_type)
    ]
    option_chain_rows = _option_chain_rows(
        spot,
        strikes,
        tau,
        rate,
        sigma,
        c_m,
        chain_snapshot if chain_source.startswith("yfinance") else None,
    )

    bs_price = black_scholes_price(spot, spot, tau, rate, sigma, option_type)
    rel_unclipped = relativistic_bs_price_approx(
        spot,
        spot,
        tau,
        rate,
        sigma,
        c_m,
        option_type,
        floor_at_intrinsic=False,
    )
    rel_price = relativistic_bs_price_approx(spot, spot, tau, rate, sigma, c_m, option_type)
    paper_iv = paper_implied_vol_approx(spot, spot, tau, rate, sigma, c_m)
    closest_chain = min(option_chain_rows, key=lambda row: abs(row.strike - spot)) if option_chain_rows else None

    if c_m < 1.0:
        warnings.append("c_m is small; the 1 / c_m^2 approximation may break down.")
    if abs(rel_price - rel_unclipped) > 1e-10:
        warnings.append("ATM relativistic price was clipped to basic no-arbitrage bounds.")
    if paper_iv is None:
        warnings.append("Paper implied-vol approximation was unavailable at the ATM strike.")

    summary = [
        ChartPoint(label="Backend Spot", value=spot),
        ChartPoint(label="ATM Black-Scholes", value=bs_price),
        ChartPoint(label="ATM Relativistic", value=rel_price),
        ChartPoint(label="ATM Correction", value=rel_unclipped - bs_price),
    ]
    if closest_chain is not None:
        summary.extend(
            [
                ChartPoint(label="ATM Call Rel", value=closest_chain.call.relativistic_price),
                ChartPoint(label="ATM Put Rel", value=closest_chain.put.relativistic_price),
            ]
        )
    if paper_iv is not None:
        summary.append(ChartPoint(label="Paper IV Approx", value=paper_iv))

    chain_dicts = [_option_chain_row_for_quant(row) for row in option_chain_rows]
    baseline_volatility = build_baseline_volatility_guide(
        spot=spot,
        selected_sigma=sigma,
        chain_rows=chain_dicts,
        price_history=price_history,
    )
    volatility_smile = build_volatility_smile(
        spot=spot,
        baseline_sigma=sigma,
        chain_rows=chain_dicts,
    )
    cumulative_volume = build_cumulative_volume_profile(chain_dicts)
    gamma_exposure = build_gamma_exposure_profile(
        spot=spot,
        tau=tau,
        rate=rate,
        baseline_sigma=sigma,
        chain_rows=chain_dicts,
    )
    iv_surface = build_iv_surface_points(
        spot=spot,
        snapshots=[_option_chain_snapshot_for_quant(snapshot) for snapshot in surface_chain_snapshots],
    )

    actual_expiry = chain_snapshot.expiry if chain_snapshot and chain_snapshot.expiry else expiry_date
    return PortfolioRelativisticBSResponse(
        portfolio_id=portfolio.id,
        model="relativistic_black_scholes_1_over_cm_squared",
        symbol=resolved_symbol,
        spot=spot,
        parameters=RelativisticBSParameters(
            tau=tau,
            expiry_date=expiry_date,
            rate=rate,
            sigma=sigma,
            c_m=c_m,
            option_type=option_type,  # type: ignore[arg-type]
            strike_min_pct=strike_min_pct,
            strike_max_pct=strike_max_pct,
            n_strikes=len(strikes),
        ),
        summary=summary,
        rows=rows,
        option_chain=option_chain_rows,
        baseline_volatility=baseline_volatility,
        volatility_smile=volatility_smile,
        cumulative_volume=cumulative_volume,
        gamma_exposure=gamma_exposure,
        iv_surface=iv_surface,
        chain_source=chain_source,
        actual_expiry_date=actual_expiry,
        warnings=warnings,
    )



def _option_chain_row_for_quant(row: RelativisticBSOptionChainRow) -> dict[str, object]:
    return {
        "strike": row.strike,
        "call": row.call.model_dump(),
        "put": row.put.model_dump(),
    }


def _option_chain_snapshot_for_quant(snapshot: OptionChainSnapshot) -> dict[str, object]:
    return {
        "expiry": snapshot.expiry,
        "calls": [_option_contract_for_quant(contract) for contract in snapshot.calls],
        "puts": [_option_contract_for_quant(contract) for contract in snapshot.puts],
    }


def _option_contract_for_quant(contract: OptionContract) -> dict[str, object | None]:
    return {
        "strike": contract.strike,
        "implied_volatility": contract.implied_volatility,
        "volume": contract.volume,
        "open_interest": contract.open_interest,
    }

def _option_chain_rows(
    spot: float,
    strikes: list[float],
    tau: float,
    rate: float,
    sigma: float,
    c_m: float,
    chain_snapshot: OptionChainSnapshot | None,
) -> list[RelativisticBSOptionChainRow]:
    call_contracts = _contracts_by_strike(chain_snapshot.calls if chain_snapshot else [])
    put_contracts = _contracts_by_strike(chain_snapshot.puts if chain_snapshot else [])
    rows: list[RelativisticBSOptionChainRow] = []
    for row in make_option_chain_surface(spot, strikes, tau, rate, sigma, c_m):
        strike = float(row["strike"])
        call = dict(row["call"])
        put = dict(row["put"])
        call.update(_contract_fields(call_contracts.get(strike)))
        put.update(_contract_fields(put_contracts.get(strike)))
        rows.append(RelativisticBSOptionChainRow(strike=strike, call=call, put=put))
    return rows


def _option_chain_strikes(
    spot: float,
    strike_min_pct: float,
    strike_max_pct: float,
    n_strikes: int,
    chain_snapshot: OptionChainSnapshot | None,
) -> list[float]:
    lower = spot * strike_min_pct
    upper = spot * strike_max_pct
    if chain_snapshot is not None:
        strikes = sorted(
            {
                contract.strike
                for contract in chain_snapshot.calls + chain_snapshot.puts
                if lower <= contract.strike <= upper
            }
        )
        if strikes:
            return strikes
    return _realistic_strike_grid(spot, strike_min_pct, strike_max_pct, n_strikes)


def _realistic_strike_grid(
    spot: float,
    strike_min_pct: float,
    strike_max_pct: float,
    n_strikes: int,
) -> list[float]:
    lower = spot * strike_min_pct
    upper = spot * strike_max_pct
    span = max(upper - lower, 0.5)
    step = max(_base_strike_increment(spot), _nice_strike_increment(span / max(n_strikes - 1, 1)))
    for _ in range(8):
        strikes = _strike_range(lower, upper, step)
        if len(strikes) <= max(n_strikes, 5) or len(strikes) <= 6:
            return strikes
        step = _next_strike_increment(step)
    return _strike_range(lower, upper, step)


def _strike_range(lower: float, upper: float, step: float) -> list[float]:
    import math

    start = math.ceil((lower - 1e-9) / step) * step
    end = math.floor((upper + 1e-9) / step) * step
    strikes: list[float] = []
    value = start
    while value <= end + 1e-9:
        strikes.append(round(value, 2))
        value += step
    if not strikes:
        strikes.append(round(max(step, round(lower / step) * step), 2))
    return strikes


def _base_strike_increment(spot: float) -> float:
    if spot < 25:
        return 0.5
    if spot < 200:
        return 1.0
    if spot < 500:
        return 2.5
    return 5.0


def _nice_strike_increment(raw_step: float) -> float:
    for step in (0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0):
        if raw_step <= step:
            return step
    return 100.0


def _next_strike_increment(step: float) -> float:
    increments = (0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0)
    for candidate in increments:
        if candidate > step:
            return candidate
    return step * 2.0


def _contracts_by_strike(contracts: list[OptionContract]) -> dict[float, OptionContract]:
    return {round(contract.strike, 2): contract for contract in contracts}


def _contract_fields(contract: OptionContract | None) -> dict[str, object | None]:
    if contract is None:
        return {}
    return {
        "market_last": contract.last_price,
        "bid": contract.bid,
        "ask": contract.ask,
        "market_iv": contract.implied_volatility,
        "volume": contract.volume,
        "open_interest": contract.open_interest,
        "contract_symbol": contract.contract_symbol,
        "in_the_money": contract.in_the_money,
    }


def _relativistic_bs_spot(
    portfolio: Portfolio,
    symbol: str | None,
    cached_quotes: list[MarketQuote],
) -> tuple[str, float]:
    if not portfolio.positions:
        raise ValueError("Portfolio has no holdings with available market prices.")

    quotes_by_ticker = {
        quote.ticker.strip().upper(): float(quote.price)
        for quote in cached_quotes
        if quote.price and quote.price > 0
    }
    requested = symbol.strip().upper() if symbol else None

    for position in portfolio.positions:
        position_symbol = position.symbol.strip().upper()
        if requested and position_symbol != requested:
            continue
        spot = quotes_by_ticker.get(position_symbol) or float(position.price)
        if spot > 0:
            return position_symbol, spot
        raise ValueError(f"{position_symbol} does not have a valid current price.")

    if requested:
        raise ValueError(f"Symbol {requested} was not found in this portfolio.")
    raise ValueError("Portfolio has no holdings with available market prices.")


def build_trade_simulation(
    portfolio: Portfolio,
    request: TradeSimulationRequest,
) -> PortfolioTradeSimulationResponse:
    result = analyze_trade_impact(
        current_holdings=_current_holdings(portfolio),
        proposed_trades=[trade.model_dump(exclude_none=True) for trade in request.trades],
        covariance_matrix=request.covariance,
    )
    tickers = result["tickers"]

    return PortfolioTradeSimulationResponse(
        portfolio_id=portfolio.id,
        before_volatility=float(result["before_volatility"]),
        after_volatility=float(result["after_volatility"]),
        volatility_delta=float(result["volatility_delta"]),
        charts=TradeSimulationCharts(
            weights=_weight_comparison_points(
                tickers,
                result["before_weights"],
                result["after_weights"],
            ),
            marginal_risk_contributions=_risk_comparison_points(
                tickers,
                result["marginal_risk_contributions"]["before"],
                result["marginal_risk_contributions"]["after"],
            ),
            component_risk_contributions=_risk_comparison_points(
                tickers,
                result["component_risk_contributions"]["before"],
                result["component_risk_contributions"]["after"],
            ),
            component_risk_contribution_pct=_risk_comparison_points(
                tickers,
                result["component_risk_contribution_pct"]["before"],
                result["component_risk_contribution_pct"]["after"],
            ),
            concentration={
                "before": result["concentration_metrics"]["before"],
                "after": result["concentration_metrics"]["after"],
            },
        ),
    )


def _build_risk_charts(
    *,
    tickers: list[str],
    prices: list[list[float | None]],
    use_rmt_cleaning: bool,
) -> PortfolioRiskCharts:
    price_array = np.asarray(prices, dtype=float)
    returns = compute_returns(price_array)
    covariance = sample_covariance(returns)
    correlation = sample_correlation(returns)
    volatilities = np.sqrt(np.clip(np.diag(covariance), 0.0, None))

    cleaned_correlation = None
    cleaned_covariance = None
    if use_rmt_cleaning:
        n_observations = max(int(np.asarray(returns).shape[0]), 1)
        cleaned_correlation = clean_correlation_rmt(correlation, n_observations=n_observations)
        cleaned_covariance = covariance_from_clean_correlation(cleaned_correlation, volatilities)

    return PortfolioRiskCharts(
        covariance=_matrix_chart(tickers, covariance),
        correlation=_matrix_chart(tickers, correlation),
        cleaned_correlation=_matrix_chart(tickers, cleaned_correlation)
        if cleaned_correlation is not None
        else None,
        cleaned_covariance=_matrix_chart(tickers, cleaned_covariance)
        if cleaned_covariance is not None
        else None,
        volatility_by_ticker=[
            ChartPoint(label=ticker, value=float(volatility))
            for ticker, volatility in zip(tickers, volatilities, strict=True)
        ],
        observations=int(np.asarray(returns).shape[0]),
        annualization_factor=252.0,
    )


def _matrix_chart(tickers: list[str], matrix: np.ndarray) -> MatrixChart:
    clean_matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    values = clean_matrix.astype(float).tolist()
    return MatrixChart(
        tickers=tickers,
        values=values,
        heatmap=[
            MatrixCell(row=row_ticker, column=column_ticker, value=float(clean_matrix[row, column]))
            for row, row_ticker in enumerate(tickers)
            for column, column_ticker in enumerate(tickers)
        ],
    )


def _current_holdings(portfolio: Portfolio) -> list[dict[str, float | str]]:
    return [
        {
            "ticker": position.symbol,
            "quantity": float(position.quantity),
            "price": float(position.price),
        }
        for position in portfolio.positions
    ]


def _weight_comparison_points(
    tickers: list[str],
    before: dict[str, float],
    after: dict[str, float],
) -> list[WeightComparisonPoint]:
    return [
        WeightComparisonPoint(
            ticker=ticker,
            before=float(before[ticker]),
            after=float(after[ticker]),
        )
        for ticker in tickers
    ]


def _risk_comparison_points(
    tickers: list[str],
    before: dict[str, float],
    after: dict[str, float],
) -> list[RiskContributionPoint]:
    return [
        RiskContributionPoint(
            ticker=ticker,
            before=float(before[ticker]),
            after=float(after[ticker]),
        )
        for ticker in tickers
    ]



def build_manual_portfolio_state(portfolio: Portfolio, repository=None) -> ManualPortfolioStateResponse:
    totals = portfolio_cost_basis_totals(portfolio)
    total_market_value = totals["market_value"]
    total_equity = totals["total_equity"]
    positions = [_cost_basis_position_response(position) for position in portfolio.positions]
    lots = [_position_lot_response(lot) for lot in sorted(portfolio.lots, key=lambda lot: (lot.symbol, lot.purchased_at))]

    cash_transactions: list[CashTransaction] = []
    trade_transactions: list[TradeTransaction] = []
    valuation_snapshots: list[PortfolioValuationSnapshot] = []
    settings = PortfolioSettings(portfolio_id=portfolio.id)
    if repository is not None:
        cash_transactions = repository.list_cash_transactions(portfolio.id)
        trade_transactions = repository.list_trade_transactions(portfolio.id)
        valuation_snapshots = repository.list_valuation_snapshots(portfolio.id)
        settings = repository.get_portfolio_settings(portfolio.id)

    net_contributions = sum(cash_transaction_external_flow(transaction) for transaction in cash_transactions)
    account_growth = total_equity - net_contributions
    account_growth_pct = account_growth / net_contributions if net_contributions else 0

    return ManualPortfolioStateResponse(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_currency,
        totals=ManualPortfolioTotals(**totals),
        performance=PortfolioPerformanceSummary(
            invested_market_value=total_market_value,
            idle_cash=totals["cash"],
            cash_weight=totals["cash"] / total_equity if total_equity else 0,
            net_contributions=net_contributions,
            account_growth=account_growth,
            account_growth_pct=account_growth_pct,
            risk_free_rate=settings.risk_free_rate,
            benchmark_symbols=settings.benchmark_symbols,
        ),
        settings=_portfolio_settings_response(settings),
        positions=positions,
        lots=lots,
        cash_transactions=[_cash_transaction_response(transaction) for transaction in cash_transactions],
        trade_history=[_trade_transaction_response(transaction) for transaction in trade_transactions],
        charts=ManualPortfolioCharts(
            allocation_by_ticker=[
                ChartPoint(
                    label=position.ticker,
                    value=position.market_value / total_market_value if total_market_value else 0,
                )
                for position in positions
            ],
            market_value_by_ticker=[
                ChartPoint(label=position.ticker, value=position.market_value)
                for position in positions
            ],
            cost_basis_by_ticker=[
                ChartPoint(label=position.ticker, value=position.cost_basis)
                for position in positions
            ],
            unrealized_gain_loss_by_ticker=[
                ChartPoint(label=position.ticker, value=position.unrealized_gain_loss)
                for position in positions
            ],
        ),
        valuation_snapshots=[_valuation_snapshot_response(snapshot) for snapshot in valuation_snapshots],
        background_jobs=[build_background_job_response(job) for job in portfolio.background_jobs],
    )


def _valuation_snapshot_response(snapshot: PortfolioValuationSnapshot) -> ValuationSnapshotResponse:
    return ValuationSnapshotResponse(
        id=snapshot.id,
        as_of=snapshot.as_of.isoformat(),
        market_value=snapshot.market_value,
        cash=snapshot.cash,
        total_equity=snapshot.total_equity,
        net_contributions=snapshot.net_contributions,
        metadata=snapshot.metadata,
    )


def build_cash_transactions_response(portfolio: Portfolio, repository) -> CashTransactionsResponse:
    transactions = repository.list_cash_transactions(portfolio.id)
    return CashTransactionsResponse(
        portfolio_id=portfolio.id,
        current_cash=portfolio.cash,
        net_contributions=sum(cash_transaction_external_flow(item) for item in transactions),
        transactions=[_cash_transaction_response(item) for item in transactions],
    )


def build_trade_transactions_response(portfolio: Portfolio, repository) -> TradeTransactionsResponse:
    return TradeTransactionsResponse(
        portfolio_id=portfolio.id,
        trades=[_trade_transaction_response(item) for item in repository.list_trade_transactions(portfolio.id)],
    )


def build_portfolio_settings_response(settings: PortfolioSettings) -> PortfolioSettingsResponse:
    return _portfolio_settings_response(settings)


def build_market_data_response(
    portfolio: Portfolio,
    quotes: list[MarketQuote],
) -> PortfolioMarketDataResponse:
    quote_tickers = {quote.ticker for quote in quotes}
    missing = [ticker for ticker in portfolio_tickers(portfolio) if ticker not in quote_tickers]
    return PortfolioMarketDataResponse(
        portfolio_id=portfolio.id,
        quotes=[build_market_quote_response(quote) for quote in quotes],
        missing_tickers=missing,
    )


def build_market_quote_response(quote: MarketQuote) -> MarketQuoteResponse:
    return MarketQuoteResponse(
        ticker=quote.ticker,
        provider=quote.provider,
        price=quote.price,
        previous_close=quote.previous_close,
        daily_return_pct=quote.daily_return_pct,
        currency=quote.currency,
        sector=quote.sector,
        industry=quote.industry,
        fetched_at=quote.fetched_at.isoformat(),
        updated_at=quote.updated_at.isoformat(),
    )


def build_performance_history_response(
    portfolio: Portfolio,
    bundle,
    *,
    repository=None,
    queued_job=None,
) -> PortfolioPerformanceHistoryResponse:
    portfolio_series, coverage = _reconstruct_portfolio_history(portfolio, bundle, repository)
    return PortfolioPerformanceHistoryResponse(
        portfolio_id=portfolio.id,
        range_name=bundle.range_name,
        period=bundle.period,
        interval=bundle.interval,
        series=[
            MarketHistorySeriesResponse(
                ticker=item.ticker,
                provider_ticker=item.provider_ticker,
                provider=item.provider,
                period=item.period,
                interval=item.interval,
                fetched_at=item.fetched_at.isoformat(),
                points=[
                    MarketHistoryPointResponse(as_of=point.as_of.isoformat(), close=point.close)
                    for point in item.points
                ],
                warnings=list(item.warnings),
            )
            for item in bundle.series
        ],
        portfolio_series=portfolio_series,
        coverage=coverage,
        missing_tickers=list(bundle.missing_tickers),
        queued_job=build_background_job_response(queued_job) if queued_job is not None else None,
    )


def _reconstruct_portfolio_history(portfolio: Portfolio, bundle, repository) -> tuple[list[PortfolioPerformancePointResponse], PortfolioHistoryCoverageResponse]:
    if repository is None:
        return [], _portfolio_history_coverage([], "unavailable", True, "Portfolio history is unavailable until the accounting ledger is loaded.")

    cash_transactions = repository.list_cash_transactions(portfolio.id)
    trades = repository.list_trade_transactions(portfolio.id)
    events: list[dict[str, object]] = []
    has_opening_lots = False
    for transaction in cash_transactions:
        events.append(
            {
                "as_of": _aware_datetime(transaction.occurred_at),
                "kind": "cash",
                "cash_delta": cash_transaction_cash_delta(transaction),
                "external_flow": cash_transaction_external_flow(transaction),
            }
        )
    for trade in trades:
        events.append(
            {
                "as_of": _aware_datetime(trade.occurred_at),
                "kind": "trade",
                "ticker": trade.symbol.strip().upper(),
                "quantity_delta": trade.quantity if trade.side == "buy" else -trade.quantity,
                "cash_delta": trade.cash_delta,
                "external_flow": 0.0,
            }
        )
    for lot in portfolio.lots:
        if lot.source == "manual_trade":
            continue
        has_opening_lots = True
        events.append(
            {
                "as_of": _aware_datetime(lot.purchased_at),
                "kind": "opening_lot",
                "ticker": lot.symbol.strip().upper(),
                "quantity_delta": float(lot.quantity),
                "cash_delta": 0.0,
                "external_flow": float(lot.quantity * lot.purchase_price + lot.fees),
            }
        )
    if not portfolio.lots:
        for position in portfolio.positions:
            if position.quantity <= 0:
                continue
            has_opening_lots = True
            events.append(
                {
                    "as_of": _aware_datetime(portfolio.created_at),
                    "kind": "opening_position",
                    "ticker": position.symbol.strip().upper(),
                    "quantity_delta": float(position.quantity),
                    "cash_delta": 0.0,
                    "external_flow": float(position.cost_basis or position.market_value),
                }
            )

    events.sort(key=lambda item: item["as_of"])
    prices = _bundle_prices_by_ticker(bundle)
    held_tickers = {
        str(event["ticker"])
        for event in events
        if event.get("ticker")
    }
    candidate_times = sorted(
        {
            _aware_datetime(point.as_of)
            for ticker in held_tickers
            for point in prices.get(ticker, [])
        }
    )
    if not events or len(candidate_times) < 2:
        note = "Cached market prices are still being collected for the dated holdings in this portfolio."
        return [], _portfolio_history_coverage([], "unavailable", True, note)

    event_index = 0
    cash = 0.0
    holdings: dict[str, float] = {}
    pending_external_flow = 0.0
    previous_equity: float | None = None
    index_value = 100.0
    points: list[PortfolioPerformancePointResponse] = []
    skipped_for_prices = False
    for as_of in candidate_times:
        while event_index < len(events) and events[event_index]["as_of"] <= as_of:
            event = events[event_index]
            cash += float(event.get("cash_delta") or 0.0)
            pending_external_flow += float(event.get("external_flow") or 0.0)
            ticker = event.get("ticker")
            if ticker:
                normalized = str(ticker)
                holdings[normalized] = max(0.0, holdings.get(normalized, 0.0) + float(event.get("quantity_delta") or 0.0))
            event_index += 1
        active = {ticker: quantity for ticker, quantity in holdings.items() if quantity > 1e-10}
        if not active and cash <= 0:
            continue
        market_value = 0.0
        supported = True
        for ticker, quantity in active.items():
            price = _historical_price_at_or_before(prices.get(ticker, []), as_of)
            if price is None:
                supported = False
                skipped_for_prices = True
                break
            market_value += quantity * price
        if not supported:
            continue
        equity = cash + market_value
        if previous_equity is None:
            index_value = 100.0
        elif previous_equity > 0:
            index_value *= max(0.0, (equity - pending_external_flow) / previous_equity)
        previous_equity = equity
        pending_external_flow = 0.0
        points.append(PortfolioPerformancePointResponse(as_of=as_of.isoformat(), value=index_value))

    quality = "complete_ledger"
    note = "Performance is reconstructed from dated cash movements and recorded trades."
    partial = skipped_for_prices
    if has_opening_lots:
        quality = "reconstructed_opening_lots"
        partial = True
        note = "Performance begins with dated opening lots contributed in kind, then follows recorded cash movements and trades."
    if skipped_for_prices:
        quality = "partial_market_data"
        note += " Some dates are omitted until cached prices exist for every active holding."
    if len(points) < 2:
        return [], _portfolio_history_coverage(points, "unavailable", True, note)
    return points, _portfolio_history_coverage(points, quality, partial, note)


def _portfolio_history_coverage(points, quality: str, partial: bool, note: str) -> PortfolioHistoryCoverageResponse:
    return PortfolioHistoryCoverageResponse(
        effective_start=points[0].as_of if points else None,
        end=points[-1].as_of if points else None,
        quality=quality,
        partial_history=partial,
        note=note,
    )


def _bundle_prices_by_ticker(bundle) -> dict[str, list[object]]:
    return {
        item.ticker.strip().upper(): sorted(item.points, key=lambda point: point.as_of)
        for item in bundle.series
        if item.points
    }


def _historical_price_at_or_before(points: list[object], as_of: datetime) -> float | None:
    for point in reversed(points):
        if _aware_datetime(point.as_of) <= as_of:
            close = float(point.close)
            return close if close > 0 else None
    return None


def _aware_datetime(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def build_relativistic_bs_history_response(
    portfolio: Portfolio,
    records: list[OptionChainHistorySnapshot],
    *,
    symbol: str,
    expiry_date: date | None,
    requested_resolution: str,
    lookback_days: int,
    rate: float,
    sigma: float,
    c_m: float,
) -> PortfolioRelativisticBSHistoryResponse:
    resolution, limited = _option_history_resolution(requested_resolution, lookback_days)
    raw_points: list[RelativisticBSHistoryPoint] = []
    for record in records:
        payload = dict(record.payload or {})
        chain = dict(payload.get("chain") or {})
        spot = float(payload.get("spot") or 0)
        calls = list(chain.get("calls") or [])
        puts = list(chain.get("puts") or [])
        strikes = sorted({float(item["strike"]) for item in calls + puts if item.get("strike") is not None})
        if spot <= 0 or not strikes:
            continue
        atm_strike = min(strikes, key=lambda strike: abs(strike - spot))
        call = _option_contract_payload_at_strike(calls, atm_strike)
        put = _option_contract_payload_at_strike(puts, atm_strike)
        atm_iv = _mean_optional([call.get("implied_volatility"), put.get("implied_volatility")])
        chain_rows = _stored_chain_rows(calls, puts)
        gamma = build_gamma_exposure_profile(
            spot=spot,
            tau=max((record.expiry - record.fetched_at.date()).days / 365.25, 1 / 365.25),
            rate=rate,
            baseline_sigma=atm_iv or sigma,
            chain_rows=chain_rows,
        )
        tau = max((record.expiry - record.fetched_at.date()).days / 365.25, 1 / 365.25)
        raw_points.append(
            RelativisticBSHistoryPoint(
                as_of=record.fetched_at.isoformat(),
                expiry_date=record.expiry,
                spot=spot,
                atm_strike=atm_strike,
                atm_iv=atm_iv,
                total_gamma_exposure=sum(float(item["net_gamma_exposure"]) for item in gamma),
                total_volume=sum(float(row["call"].get("volume") or 0) + float(row["put"].get("volume") or 0) for row in chain_rows),
                atm_market_price=_stored_market_price(call),
                atm_bs_price=black_scholes_price(spot, atm_strike, tau, rate, atm_iv or sigma, "call"),
                atm_relativistic_price=relativistic_bs_price_approx(spot, atm_strike, tau, rate, atm_iv or sigma, c_m, "call"),
            )
        )
    points = _aggregate_option_history(raw_points, resolution)
    note = (
        "Charts use saved public option-chain snapshots captured when this suite runs. "
        "Zoom and resolution changes read Postgres only and never call yfinance."
    )
    if limited:
        note += f" {requested_resolution.title()} detail was reduced to {resolution} for the selected lookback."
    return PortfolioRelativisticBSHistoryResponse(
        portfolio_id=portfolio.id,
        symbol=symbol.strip().upper(),
        expiry_date=expiry_date,
        requested_resolution=requested_resolution,  # type: ignore[arg-type]
        resolution=resolution,  # type: ignore[arg-type]
        limited=limited,
        lookback_days=lookback_days,
        points=points,
        note=note,
    )


def _option_history_resolution(requested: str, lookback_days: int) -> tuple[str, bool]:
    clean = requested if requested in {"auto", "raw", "hour", "day", "week"} else "auto"
    if clean == "auto":
        if lookback_days <= 7:
            return "raw", False
        if lookback_days <= 45:
            return "hour", False
        if lookback_days <= 180:
            return "day", False
        return "week", False
    effective = clean
    if effective == "raw" and lookback_days > 30:
        effective = "hour"
    if effective == "hour" and lookback_days > 90:
        effective = "day"
    if effective == "day" and lookback_days > 365:
        effective = "week"
    return effective, effective != clean


def _aggregate_option_history(points: list[RelativisticBSHistoryPoint], resolution: str) -> list[RelativisticBSHistoryPoint]:
    if resolution == "raw":
        return sorted(points, key=lambda point: point.as_of)
    buckets: dict[str, RelativisticBSHistoryPoint] = {}
    for point in sorted(points, key=lambda item: item.as_of):
        as_of = datetime.fromisoformat(point.as_of.replace("Z", "+00:00"))
        if resolution == "hour":
            key = as_of.strftime("%Y-%m-%dT%H")
        elif resolution == "day":
            key = as_of.strftime("%Y-%m-%d")
        else:
            iso_year, iso_week, _ = as_of.isocalendar()
            key = f"{iso_year}-W{iso_week:02d}"
        buckets[key] = point
    return list(buckets.values())


def _option_contract_payload_at_strike(contracts: list[dict[str, object]], strike: float) -> dict[str, object]:
    return next((item for item in contracts if abs(float(item.get("strike") or 0) - strike) < 1e-8), {})


def _stored_chain_rows(calls: list[dict[str, object]], puts: list[dict[str, object]]) -> list[dict[str, object]]:
    strikes = sorted({float(item["strike"]) for item in calls + puts if item.get("strike") is not None})
    return [
        {
            "strike": strike,
            "call": _stored_quant_contract(_option_contract_payload_at_strike(calls, strike)),
            "put": _stored_quant_contract(_option_contract_payload_at_strike(puts, strike)),
        }
        for strike in strikes
    ]


def _stored_quant_contract(contract: dict[str, object]) -> dict[str, object]:
    return {**contract, "market_iv": contract.get("implied_volatility")}


def _mean_optional(values: list[object]) -> float | None:
    present = [float(value) for value in values if value is not None and float(value) > 0]
    return sum(present) / len(present) if present else None


def _stored_market_price(contract: dict[str, object]) -> float | None:
    bid = contract.get("bid")
    ask = contract.get("ask")
    if bid is not None and ask is not None and float(ask) >= float(bid) >= 0:
        return (float(bid) + float(ask)) / 2
    last_price = contract.get("last_price")
    return float(last_price) if last_price is not None else None


def build_background_job_response(job) -> BackgroundJobResponse:
    return BackgroundJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        message=job.message,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


def _cost_basis_position_response(position: Position) -> CostBasisPositionResponse:
    market_value = position.market_value
    unrealized_gain_loss_pct = (
        position.unrealized_gain_loss / position.cost_basis if position.cost_basis else 0
    )
    return CostBasisPositionResponse(
        ticker=position.symbol,
        asset_class=position.asset_class,
        quantity=position.quantity,
        current_price=position.price,
        market_value=market_value,
        cost_basis=position.cost_basis,
        average_cost=position.average_cost,
        unrealized_gain_loss=position.unrealized_gain_loss,
        unrealized_gain_loss_pct=unrealized_gain_loss_pct,
        lots_count=position.lots_count,
    )


def _position_lot_response(lot: PositionLot) -> PositionLotResponse:
    return PositionLotResponse(
        id=lot.id,
        ticker=lot.symbol,
        quantity=lot.quantity,
        remaining_quantity=lot.remaining_quantity or 0,
        purchase_price=lot.purchase_price,
        current_price=lot.current_price,
        fees=lot.fees,
        asset_class=lot.asset_class,
        purchased_at=lot.purchased_at.isoformat(),
        cost_basis=lot.remaining_cost_basis,
        market_value=lot.market_value,
        unrealized_gain_loss=lot.unrealized_gain_loss,
        source=lot.source,
        notes=lot.notes,
    )


def _cash_transaction_response(transaction: CashTransaction) -> CashTransactionResponse:
    return CashTransactionResponse(
        id=transaction.id,
        transaction_type=transaction.transaction_type,
        amount=transaction.amount,
        cash_delta=cash_transaction_cash_delta(transaction),
        external_flow=cash_transaction_external_flow(transaction),
        currency=transaction.currency,
        occurred_at=transaction.occurred_at.isoformat(),
        source=transaction.source,
        notes=transaction.notes,
        created_at=transaction.created_at.isoformat(),
    )


def _trade_transaction_response(transaction: TradeTransaction) -> TradeTransactionResponse:
    return TradeTransactionResponse(
        id=transaction.id,
        ticker=transaction.symbol,
        side=transaction.side,
        quantity=transaction.quantity,
        price=transaction.price,
        notional=transaction.notional,
        fees=transaction.fees,
        cash_delta=transaction.cash_delta,
        realized_gain_loss=transaction.realized_gain_loss,
        asset_class=transaction.asset_class,
        occurred_at=transaction.occurred_at.isoformat(),
        source=transaction.source,
        lot_ids=transaction.lot_ids,
        notes=transaction.notes,
        created_at=transaction.created_at.isoformat(),
    )


def _portfolio_settings_response(settings: PortfolioSettings) -> PortfolioSettingsResponse:
    return PortfolioSettingsResponse(
        portfolio_id=settings.portfolio_id,
        risk_free_rate=settings.risk_free_rate,
        benchmark_symbols=settings.benchmark_symbols,
        cash_target_pct=settings.cash_target_pct,
        updated_at=settings.updated_at.isoformat(),
    )
