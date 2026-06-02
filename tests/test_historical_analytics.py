from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.api.services import (
    build_performance_history_response,
    build_relativistic_bs_history_response,
)
from app.background.portfolio_tasks import (
    record_cash_transaction,
    record_manual_lots,
    record_manual_trade,
)
from app.connectors.market_data.history import PriceHistoryBundle
from app.connectors.market_data.options import persist_option_suite_snapshots
from app.connectors.market_data.yfinance import (
    OptionChainSnapshot,
    OptionContract,
    OptionSuiteSnapshot,
    PriceHistoryPoint,
    PriceHistorySeries,
    PriceHistorySnapshot,
)
from app.db.models import OptionChainHistorySnapshot
from app.db.repository import InMemoryPortfolioRepository


def _history_bundle(ticker: str, prices: list[tuple[datetime, float]]) -> PriceHistoryBundle:
    return PriceHistoryBundle(
        range_name="max",
        period="max",
        interval="1d",
        series=[
            PriceHistorySeries(
                ticker=ticker,
                provider_ticker=ticker,
                provider="test",
                period="max",
                interval="1d",
                fetched_at=datetime.now(timezone.utc),
                points=[PriceHistoryPoint(as_of=as_of, close=close) for as_of, close in prices],
                warnings=[],
            )
        ],
        missing_tickers=[],
    )


def test_portfolio_history_starts_at_dated_opening_lot_and_marks_partial_coverage():
    repository = InMemoryPortfolioRepository()
    portfolio = repository.create(name="Opening Lots", base_currency="USD", cash=0, positions=[])
    portfolio = record_manual_lots(
        repository,
        portfolio.id,
        [{"ticker": "AAPL", "quantity": 2, "purchase_price": 100, "purchased_at": "2024-01-02T00:00:00Z"}],
    )
    bundle = _history_bundle(
        "AAPL",
        [
            (datetime(2024, 1, 1, tzinfo=timezone.utc), 90),
            (datetime(2024, 1, 2, tzinfo=timezone.utc), 100),
            (datetime(2024, 1, 3, tzinfo=timezone.utc), 110),
        ],
    )

    response = build_performance_history_response(portfolio, bundle, repository=repository)

    assert response.coverage.quality == "reconstructed_opening_lots"
    assert response.coverage.partial_history is True
    assert response.coverage.effective_start.startswith("2024-01-02")
    assert [point.value for point in response.portfolio_series] == pytest.approx([100, 110])


def test_portfolio_history_does_not_double_count_lot_created_by_manual_trade():
    repository = InMemoryPortfolioRepository()
    portfolio = repository.create(name="Trade Ledger", base_currency="USD", cash=0, positions=[])
    portfolio = record_cash_transaction(
        repository,
        portfolio.id,
        {"transaction_type": "deposit", "amount": 1000, "occurred_at": "2024-01-01T00:00:00Z"},
    )
    portfolio = record_manual_trade(
        repository,
        portfolio.id,
        {"ticker": "AAPL", "side": "buy", "quantity": 1, "price": 100, "occurred_at": "2024-01-02T00:00:00Z"},
    )
    bundle = _history_bundle(
        "AAPL",
        [
            (datetime(2024, 1, 2, tzinfo=timezone.utc), 100),
            (datetime(2024, 1, 3, tzinfo=timezone.utc), 110),
        ],
    )

    response = build_performance_history_response(portfolio, bundle, repository=repository)

    assert response.coverage.quality == "complete_ledger"
    assert [point.value for point in response.portfolio_series] == pytest.approx([100, 101])


def test_portfolio_history_exposes_partial_market_data_without_fabricated_prices():
    repository = InMemoryPortfolioRepository()
    portfolio = repository.create(name="Missing Prices", base_currency="USD", cash=0, positions=[])
    portfolio = record_manual_lots(
        repository,
        portfolio.id,
        [
            {"ticker": "AAPL", "quantity": 1, "purchase_price": 100, "purchased_at": "2024-01-02T00:00:00Z"},
            {"ticker": "BND", "quantity": 1, "purchase_price": 50, "purchased_at": "2024-01-02T00:00:00Z"},
        ],
    )

    response = build_performance_history_response(
        portfolio,
        _history_bundle(
            "AAPL",
            [
                (datetime(2024, 1, 2, tzinfo=timezone.utc), 100),
                (datetime(2024, 1, 3, tzinfo=timezone.utc), 110),
            ],
        ),
        repository=repository,
    )

    assert response.portfolio_series == []
    assert response.coverage.quality == "unavailable"
    assert response.coverage.partial_history is True


def test_option_snapshot_repository_deduplicates_and_purges_old_records():
    repository = InMemoryPortfolioRepository()
    now = datetime.now(timezone.utc)
    recent = OptionChainHistorySnapshot(
        id="recent",
        ticker="AAPL",
        provider="test",
        expiry=date.today() + timedelta(days=30),
        fetched_at=now,
        snapshot_hash="same",
        payload={"chain": {}},
    )
    duplicate = OptionChainHistorySnapshot(
        id="duplicate",
        ticker="AAPL",
        provider="test",
        expiry=recent.expiry,
        fetched_at=now,
        snapshot_hash="same",
        payload={"chain": {}},
    )
    old = OptionChainHistorySnapshot(
        id="old",
        ticker="AAPL",
        provider="test",
        expiry=recent.expiry,
        fetched_at=now - timedelta(days=400),
        snapshot_hash="old",
        payload={"chain": {}},
    )

    assert repository.add_option_chain_snapshot(recent).id == "recent"
    assert repository.add_option_chain_snapshot(duplicate).id == "recent"
    repository.add_option_chain_snapshot(old)
    assert repository.purge_option_chain_snapshots(before=now - timedelta(days=365)) == 1
    assert [item.id for item in repository.list_option_chain_snapshots("aapl")] == ["recent"]


def test_option_snapshot_table_is_present_in_schema_and_alembic():
    assert "CREATE TABLE IF NOT EXISTS option_chain_snapshots" in Path("app/db/schema.sql").read_text()
    assert Path("alembic/versions/0003_option_chain_snapshots.py").exists()


def test_fresh_option_suite_capture_persists_surface_expiries_once():
    repository = InMemoryPortfolioRepository()
    fetched_at = datetime.now(timezone.utc)
    expiry = fetched_at.date() + timedelta(days=30)
    chain = OptionChainSnapshot(
        ticker="AAPL",
        provider_ticker="AAPL",
        requested_expiry=expiry,
        expiry=expiry,
        provider="test",
        fetched_at=fetched_at,
        calls=[OptionContract(option_type="call", strike=100, bid=4, ask=6)],
        puts=[OptionContract(option_type="put", strike=100, bid=3, ask=5)],
        warnings=[],
    )
    suite = OptionSuiteSnapshot(
        ticker="AAPL",
        provider_ticker="AAPL",
        provider="test",
        fetched_at=fetched_at,
        requested_expiry=expiry,
        current_chain=chain,
        surface_chains=[chain],
        price_history=PriceHistorySnapshot(
            ticker="AAPL",
            provider_ticker="AAPL",
            provider="test",
            fetched_at=fetched_at,
            prices=[(fetched_at.date(), 100)],
            warnings=[],
        ),
        warnings=[],
    )

    assert len(persist_option_suite_snapshots(repository, suite)) == 1
    assert len(persist_option_suite_snapshots(repository, suite)) == 1
    assert len(repository.list_option_chain_snapshots("AAPL", expiry=expiry)) == 1


def test_option_history_limits_raw_resolution_for_long_lookback():
    repository = InMemoryPortfolioRepository()
    portfolio = repository.create(name="Options", base_currency="USD", cash=0, positions=[])
    fetched_at = datetime.now(timezone.utc)
    expiry = fetched_at.date() + timedelta(days=30)
    record = OptionChainHistorySnapshot(
        id="snapshot",
        ticker="AAPL",
        provider="test",
        expiry=expiry,
        fetched_at=fetched_at,
        snapshot_hash="snapshot",
        payload={
            "spot": 100,
            "chain": {
                "calls": [{"strike": 100, "bid": 4, "ask": 6, "implied_volatility": 0.25, "volume": 10, "open_interest": 20}],
                "puts": [{"strike": 100, "bid": 3, "ask": 5, "implied_volatility": 0.27, "volume": 5, "open_interest": 30}],
            },
        },
    )

    response = build_relativistic_bs_history_response(
        portfolio,
        [record],
        symbol="AAPL",
        expiry_date=expiry,
        requested_resolution="raw",
        lookback_days=365,
        rate=0.05,
        sigma=0.2,
        c_m=2.5,
    )

    assert response.resolution == "day"
    assert response.limited is True
    assert response.points[0].atm_iv == pytest.approx(0.26)
    assert response.points[0].total_volume == pytest.approx(15)
    assert response.points[0].atm_market_price == pytest.approx(5)
