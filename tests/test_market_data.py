from datetime import datetime, timezone

import pytest

from app.api.routes import portfolio_repository
from app.background.queue import QueuedBackgroundJob
from app.background.worker import process_background_job
from app.connectors.market_data.limiter import InMemoryRateLimiter, RateLimitExceeded, RateLimitResult, acquire_provider_fetch_slot
from app.connectors.market_data.service import refresh_market_data_quotes
from app.db.models import MarketQuote, Position


class _FakeIloc:
    def __init__(self, series):
        self._series = series

    def __getitem__(self, index):
        return self._series.values[index]


class _FakeIndex:
    def __init__(self, dates):
        self.date = dates


class _FakeGroupBy:
    def __init__(self, series, keys):
        self._series = series
        self.groups = {}
        for index, key in enumerate(keys):
            self.groups.setdefault(key, []).append(index)

    def get_group(self, key):
        indexes = self.groups[key]
        return _FakeSeries(
            [self._series.values[index] for index in indexes],
            [self._series.index.date[index] for index in indexes],
        )


class _FakeSeries:
    def __init__(self, values, dates):
        self.values = values
        self.index = _FakeIndex(dates)
        self.iloc = _FakeIloc(self)

    def __len__(self):
        return len(self.values)

    def dropna(self):
        pairs = [(value, date) for value, date in zip(self.values, self.index.date) if value is not None]
        return _FakeSeries([value for value, _ in pairs], [date for _, date in pairs])

    def groupby(self, keys):
        return _FakeGroupBy(self, keys)


class _FakeColumns:
    nlevels = 1


class _FakeYFinanceDownload:
    empty = False
    columns = _FakeColumns()

    def __getitem__(self, key):
        if key != "Close":
            raise KeyError(key)
        return _FakeSeries([100.0, 102.0, 103.0], ["2026-05-25", "2026-05-26", "2026-05-26"])


def test_yfinance_connector_uses_intraday_download_for_live_day_change(monkeypatch):
    import sys
    from types import SimpleNamespace

    from app.connectors.market_data.yfinance import YFinanceMarketDataConnector

    captured = {}

    def fake_download(**kwargs):
        captured.update(kwargs)
        return _FakeYFinanceDownload()

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=fake_download))

    quotes = YFinanceMarketDataConnector().fetch_quotes(["aapl"])

    assert captured["tickers"] == ["AAPL"]
    assert captured["period"] == "2d"
    assert captured["interval"] == "5m"
    assert captured["group_by"] == "ticker"
    assert captured["prepost"] is False
    assert quotes[0].ticker == "AAPL"
    assert quotes[0].price == pytest.approx(103)
    assert quotes[0].previous_close == pytest.approx(100)
    assert quotes[0].daily_return_pct == pytest.approx(3)


def test_yfinance_connector_maps_app_tickers_to_provider_symbols(monkeypatch):
    import sys
    from types import SimpleNamespace

    from app.connectors.market_data.yfinance import YFinanceMarketDataConnector

    captured = {}

    def fake_download(**kwargs):
        captured.update(kwargs)
        return _FakeYFinanceDownload()

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=fake_download))

    quotes = YFinanceMarketDataConnector().fetch_quotes(["brk_b"])

    assert captured["tickers"] == ["BRK-B"]
    assert quotes[0].ticker == "BRK_B"
    assert quotes[0].price == pytest.approx(103)




def test_yfinance_connector_fetches_price_history(monkeypatch):
    import sys
    from types import SimpleNamespace

    from app.connectors.market_data.yfinance import YFinanceMarketDataConnector

    captured = {}

    def fake_download(**kwargs):
        captured.update(kwargs)
        return _FakeYFinanceDownload()

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=fake_download))

    series = YFinanceMarketDataConnector().fetch_price_history(["brk_b"], period="5y", interval="1d")

    assert captured["tickers"] == ["BRK-B"]
    assert captured["period"] == "5y"
    assert captured["interval"] == "1d"
    assert captured["group_by"] == "ticker"
    assert series[0].ticker == "BRK_B"
    assert series[0].provider_ticker == "BRK-B"
    assert [point.close for point in series[0].points] == [100.0, 102.0, 103.0]


def test_performance_history_endpoint_returns_cached_series_and_queues_missing(client, auth_headers, monkeypatch):
    from app.connectors.market_data.history import PriceHistoryBundle
    from app.connectors.market_data.yfinance import PriceHistoryPoint, PriceHistorySeries

    queued = []
    now = datetime.now(timezone.utc)
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "History", "positions": [{"symbol": "AAPL", "quantity": 2, "price": 100}]},
    ).json()

    def fake_cached(tickers, *, range_name, cache=None):
        return PriceHistoryBundle(
            range_name="max",
            period="max",
            interval="1d",
            series=[
                PriceHistorySeries(
                    ticker="AAPL",
                    provider_ticker="AAPL",
                    provider="test",
                    period="max",
                    interval="1d",
                    fetched_at=now,
                    points=[PriceHistoryPoint(as_of=now, close=123)],
                    warnings=[],
                )
            ],
            missing_tickers=["SPY"],
        )

    monkeypatch.setattr("app.api.routes.get_cached_price_history", fake_cached)
    monkeypatch.setattr(
        "app.api.routes.enqueue_background_job_message",
        lambda job, **kwargs: queued.append((job, kwargs)),
    )

    response = client.get(
        f"/portfolios/{created['id']}/performance-history?range_name=max&benchmark_symbols=SPY,QQQ",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == created["id"]
    assert payload["range_name"] == "max"
    assert payload["series"][0]["ticker"] == "AAPL"
    assert payload["missing_tickers"] == ["SPY"]
    assert payload["queued_job"]["job_type"] == "refresh_market_history"
    queued_payload = queued[0][1]["payload"]
    assert queued_payload["ranges"] == ["max", "year"]
    assert queued_payload["tickers"] == ["AAPL", "SPY", "QQQ"]
    assert queued_payload["provider_signature"].startswith("account-")


def test_performance_history_rejects_too_many_benchmarks(client, auth_headers, monkeypatch):
    monkeypatch.setenv("MARKET_DATA_MAX_BENCHMARK_TICKERS", "1")
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "Benchmark Cap", "positions": [{"symbol": "AAPL", "quantity": 2, "price": 100}]},
    ).json()

    response = client.get(
        f"/portfolios/{created['id']}/performance-history?range_name=max&benchmark_symbols=SPY,QQQ",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "benchmark comparison is limited to 1 ticker" in response.json()["detail"]


def test_performance_history_includes_tickers_from_manual_trade_ledger(client, auth_headers, monkeypatch):
    from app.connectors.market_data.history import PriceHistoryBundle

    captured = {}
    queued = []
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={
            "name": "Sold Ticker History",
            "lots": [
                {"ticker": "AAPL", "quantity": 1, "purchase_price": 100, "purchased_at": "2024-01-02T00:00:00Z"},
                {"ticker": "BND", "quantity": 1, "purchase_price": 50, "purchased_at": "2024-01-02T00:00:00Z"},
            ],
        },
    ).json()
    trade_response = client.post(
        f"/portfolios/{created['id']}/trades",
        headers=auth_headers,
        json={"ticker": "BND", "side": "sell", "quantity": 1, "price": 55, "occurred_at": "2024-01-03T00:00:00Z"},
    )
    assert trade_response.status_code == 201
    assert [position["ticker"] for position in trade_response.json()["positions"]] == ["AAPL"]

    def fake_cached(tickers, *, range_name, cache=None):
        captured["tickers"] = tickers
        return PriceHistoryBundle(
            range_name="max",
            period="max",
            interval="1d",
            series=[],
            missing_tickers=list(tickers),
        )

    monkeypatch.setattr("app.api.routes.get_cached_price_history", fake_cached)
    monkeypatch.setattr(
        "app.api.routes.enqueue_background_job_message",
        lambda job, **kwargs: queued.append((job, kwargs)),
    )

    response = client.get(
        f"/portfolios/{created['id']}/performance-history?range_name=max&benchmark_symbols=SPY",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert captured["tickers"] == ["AAPL", "BND", "SPY"]
    assert queued[0][1]["payload"]["tickers"] == ["AAPL", "BND", "SPY"]


def test_worker_processes_market_history_refresh_job(monkeypatch):
    from app.connectors.market_data.history import PriceHistoryBundle

    calls = []

    def fake_refresh(tickers, *, range_name, force=False, wait_for_rate_limit=False, provider_signature=None):
        calls.append((tickers, range_name, force, wait_for_rate_limit, provider_signature))
        return PriceHistoryBundle(range_name=range_name, period="max", interval="1d", series=[], missing_tickers=[])

    monkeypatch.setattr("app.background.worker.refresh_price_history", fake_refresh)
    portfolio = portfolio_repository.create(
        name="Worker History",
        base_currency="USD",
        cash=0,
        positions=[Position(symbol="AAPL", quantity=2, price=100)],
        lots=[],
        user_id="user-history",
    )
    job = portfolio_repository.enqueue_background_job(portfolio.id, "refresh_market_history")

    result = process_background_job(
        portfolio_repository,
        QueuedBackgroundJob(
            job_id=job.id,
            portfolio_id=portfolio.id,
            job_type="refresh_market_history",
            payload={"tickers": ["AAPL", "SPY"], "ranges": ["max", "day"], "force": False},
        ),
    )

    assert result.status == "completed"
    assert "Cached max, day market history" in (result.message or "")
    assert calls[0][:4] == (["AAPL", "SPY"], "max", False, True)
    assert calls[1][1] == "day"
    assert calls[0][4].startswith("account-")


def test_market_data_endpoint_returns_cached_quotes(client, auth_headers):
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={
            "name": "Cached Quotes",
            "positions": [{"symbol": "AAPL", "quantity": 2, "price": 100}],
        },
    ).json()
    portfolio_repository.upsert_market_quotes(
        [
            MarketQuote(
                ticker="AAPL",
                provider="test",
                price=125,
                previous_close=100,
                daily_return_pct=25,
                sector="Technology",
                fetched_at=datetime.now(timezone.utc),
            )
        ]
    )

    response = client.get(f"/portfolios/{created['id']}/market-data", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == created["id"]
    assert payload["quotes"][0]["ticker"] == "AAPL"
    assert payload["quotes"][0]["price"] == pytest.approx(125)
    assert payload["missing_tickers"] == []


def test_heatmap_get_uses_cached_market_data(client, auth_headers):
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={
            "name": "Cached Heatmap",
            "positions": [{"symbol": "AAPL", "quantity": 2, "price": 100}],
        },
    ).json()
    portfolio_repository.upsert_market_quotes(
        [MarketQuote(ticker="AAPL", provider="test", price=150, previous_close=100, daily_return_pct=50)]
    )

    response = client.get(f"/portfolios/{created['id']}/heatmap", headers=auth_headers)

    assert response.status_code == 200
    holding = response.json()["holdings"][0]
    assert holding["ticker"] == "AAPL"
    assert holding["market_value"] == pytest.approx(300)
    assert holding["daily_return_pct"] == pytest.approx(50)


def test_market_data_refresh_route_rate_limits_and_enqueues(client, auth_headers, monkeypatch):
    queued = []
    limiter = InMemoryRateLimiter()

    monkeypatch.setattr(
        "app.api.routes.enforce_market_data_refresh_limits",
        lambda *, user_id, portfolio_id: limiter.check(
            key=f"test:{user_id}:{portfolio_id}", limit=1, window_seconds=300
        )
        and None,
    )
    monkeypatch.setattr(
        "app.api.routes.enqueue_background_job_message",
        lambda job, **kwargs: queued.append((job, kwargs)),
    )
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "Refresh Quotes", "positions": []},
    ).json()
    portfolio_repository.replace_positions(
        created["id"],
        [Position(symbol="AAPL", quantity=2, price=100, cost_basis=200, average_cost=100, lots_count=1)],
    )

    response = client.post(f"/portfolios/{created['id']}/market-data/refresh", headers=auth_headers)

    assert response.status_code == 202
    assert response.json()["job_type"] == "refresh_market_data"
    payload = queued[0][1]["payload"]
    assert payload["automatic"] is False
    assert payload["force"] is True
    assert payload["defer_on_rate_limit"] is True
    assert payload["provider_signature"].startswith("account-")


def test_market_data_refresh_route_reuses_running_refresh_job(client, auth_headers, monkeypatch):
    queued = []
    monkeypatch.setattr(
        "app.api.routes.enqueue_background_job_message",
        lambda job, **kwargs: queued.append((job, kwargs)),
    )
    monkeypatch.setattr(
        "app.api.routes.enforce_market_data_refresh_limits",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("limiter should not run")),
    )
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "Reuse Running Refresh", "positions": []},
    ).json()
    portfolio_repository.replace_positions(
        created["id"],
        [Position(symbol="AAPL", quantity=1, price=100, cost_basis=100, average_cost=100, lots_count=1)],
    )
    running = portfolio_repository.enqueue_background_job(created["id"], "refresh_market_data")
    portfolio_repository.complete_background_job(
        created["id"],
        running.id,
        status="running",
        message="Worker started refresh_market_data.",
    )

    response = client.post(f"/portfolios/{created['id']}/market-data/refresh", headers=auth_headers)

    assert response.status_code == 202
    assert response.json()["id"] == running.id
    assert response.json()["status"] == "running"
    assert queued == []


def test_market_data_refresh_route_requeues_pending_refresh_job(client, auth_headers, monkeypatch):
    queued = []
    monkeypatch.setattr(
        "app.api.routes.enqueue_background_job_message",
        lambda job, **kwargs: queued.append((job, kwargs)),
    )
    monkeypatch.setattr(
        "app.api.routes.enforce_market_data_refresh_limits",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("limiter should not run")),
    )
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "Requeue Pending Refresh", "positions": []},
    ).json()
    portfolio_repository.replace_positions(
        created["id"],
        [Position(symbol="AAPL", quantity=1, price=100, cost_basis=100, average_cost=100, lots_count=1)],
    )
    pending = portfolio_repository.enqueue_background_job(created["id"], "refresh_market_data")

    response = client.post(f"/portfolios/{created['id']}/market-data/refresh", headers=auth_headers)

    assert response.status_code == 202
    assert response.json()["id"] == pending.id
    assert response.json()["status"] == "pending"
    assert queued[0][0].id == pending.id
    assert queued[0][1]["payload"]["force"] is True


def test_market_data_refresh_route_returns_429(client, auth_headers, monkeypatch):
    def reject(**kwargs):
        raise RateLimitExceeded("slow down", retry_after_seconds=17)

    monkeypatch.setattr("app.api.routes.enforce_market_data_refresh_limits", reject)
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "Limited", "positions": []},
    ).json()
    portfolio_repository.replace_positions(
        created["id"],
        [Position(symbol="AAPL", quantity=2, price=100, cost_basis=200, average_cost=100, lots_count=1)],
    )

    response = client.post(f"/portfolios/{created['id']}/market-data/refresh", headers=auth_headers)

    assert response.status_code == 429
    assert response.headers["retry-after"] == "17"


def test_market_data_refresh_route_ignores_limiter_runtime_failure_by_default(client, auth_headers, monkeypatch):
    queued = []

    def broken_limiter(**kwargs):
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("app.api.routes.enforce_market_data_refresh_limits", broken_limiter)
    monkeypatch.setattr(
        "app.api.routes.enqueue_background_job_message",
        lambda job, **kwargs: queued.append((job, kwargs)),
    )
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "Limiter Soft Failure", "positions": [{"symbol": "AAPL", "quantity": 2, "price": 100}]},
    ).json()

    response = client.post(f"/portfolios/{created['id']}/market-data/refresh", headers=auth_headers)

    assert response.status_code == 202
    assert queued


def test_market_data_refresh_limiter_falls_back_when_redis_unavailable(client, auth_headers, monkeypatch):
    class BrokenLimiter:
        def check(self, **kwargs):
            raise RuntimeError("redis unavailable")

    queued = []
    monkeypatch.setattr("app.api.routes.create_rate_limiter", lambda: BrokenLimiter(), raising=False)
    monkeypatch.setattr("app.connectors.market_data.limiter.create_rate_limiter", lambda: BrokenLimiter())
    monkeypatch.setattr(
        "app.api.routes.enqueue_background_job_message",
        lambda job, **kwargs: queued.append((job, kwargs)),
    )
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "Limiter Fallback", "positions": []},
    ).json()
    portfolio_repository.replace_positions(
        created["id"],
        [Position(symbol="AAPL", quantity=1, price=100, cost_basis=100, average_cost=100, lots_count=1)],
    )

    response = client.post(f"/portfolios/{created['id']}/market-data/refresh", headers=auth_headers)

    assert response.status_code == 202
    assert queued


def test_manual_lot_auto_queues_market_data_refresh(client, auth_headers, monkeypatch):
    queued = []
    monkeypatch.setattr(
        "app.api.routes.enqueue_background_job_message",
        lambda job, **kwargs: queued.append((job, kwargs)),
    )
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "Auto Refresh", "positions": []},
    ).json()

    response = client.post(
        f"/portfolios/{created['id']}/lots",
        headers=auth_headers,
        json={"lots": [{"ticker": "AAPL", "quantity": 2, "purchase_price": 100}]},
    )

    assert response.status_code == 201
    refresh_jobs = [item for item in queued if item[0].job_type == "refresh_market_data"]
    assert len(refresh_jobs) == 1
    payload = refresh_jobs[0][1]["payload"]
    assert payload["automatic"] is True
    assert payload["force"] is False
    assert payload["defer_on_rate_limit"] is True
    assert payload["provider_signature"].startswith("account-")


def test_refresh_market_data_waits_for_provider_rate_limit():
    class FakeCache:
        def get_many(self, tickers):
            return []

        def set_many(self, quotes, ttl_seconds):
            return None

    class FakeConnector:
        provider = "fake"

        def __init__(self):
            self.fetched = []

        def fetch_quotes(self, tickers):
            self.fetched.append(tickers)
            return [MarketQuote(ticker=ticker, provider=self.provider, price=100) for ticker in tickers]

    class OneRetryLimiter:
        def __init__(self):
            self.calls = 0
            self.keys = []

        def check(self, *, key, limit, window_seconds, cost=1):
            self.calls += 1
            self.keys.append(key)
            if self.calls == 1:
                return RateLimitResult(False, key, limit, 0, 17, cost=cost)
            return RateLimitResult(True, key, limit, 0, 0, cost=cost)

    slept = []
    limiter = OneRetryLimiter()
    connector = FakeConnector()

    quotes = refresh_market_data_quotes(
        ["AAPL"],
        portfolio_repository,
        connector=connector,
        cache=FakeCache(),
        wait_for_rate_limit=True,
        provider_signature="account-alpha",
        rate_limiter=limiter,
        sleep=lambda seconds: slept.append(seconds),
    )

    assert slept == [17]
    assert connector.fetched == [["AAPL"]]
    assert quotes[0].ticker == "AAPL"
    assert limiter.keys == [
        "market-data:provider:fake:global:minute",
        "market-data:provider:fake:global:minute",
        "market-data:provider:fake:signature:account-alpha:minute",
    ]


def test_provider_rate_limit_is_partitioned_by_account_signature(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER_FETCH_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("MARKET_DATA_PROVIDER_GLOBAL_FETCH_LIMIT_PER_MINUTE", "10")
    limiter = InMemoryRateLimiter()

    first = acquire_provider_fetch_slot(
        provider="fake",
        provider_signature="account-alpha",
        limiter=limiter,
    )
    second = acquire_provider_fetch_slot(
        provider="fake",
        provider_signature="account-beta",
        limiter=limiter,
    )

    assert first.allowed is True
    assert second.allowed is True
    with pytest.raises(RateLimitExceeded):
        acquire_provider_fetch_slot(
            provider="fake",
            provider_signature="account-alpha",
            limiter=limiter,
        )


def test_provider_global_rate_limit_caps_multiple_accounts(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER_FETCH_LIMIT_PER_MINUTE", "10")
    monkeypatch.setenv("MARKET_DATA_PROVIDER_GLOBAL_FETCH_LIMIT_PER_MINUTE", "2")
    limiter = InMemoryRateLimiter()

    acquire_provider_fetch_slot(provider="fake", provider_signature="account-alpha", limiter=limiter)
    acquire_provider_fetch_slot(provider="fake", provider_signature="account-beta", limiter=limiter)

    with pytest.raises(RateLimitExceeded):
        acquire_provider_fetch_slot(provider="fake", provider_signature="account-gamma", limiter=limiter)


def test_provider_rate_limit_charges_weighted_cost(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER_FETCH_LIMIT_PER_MINUTE", "3")
    monkeypatch.setenv("MARKET_DATA_PROVIDER_GLOBAL_FETCH_LIMIT_PER_MINUTE", "10")
    limiter = InMemoryRateLimiter()

    acquire_provider_fetch_slot(provider="fake", provider_signature="account-alpha", limiter=limiter, cost=2)

    with pytest.raises(RateLimitExceeded):
        acquire_provider_fetch_slot(provider="fake", provider_signature="account-alpha", limiter=limiter, cost=2)


def test_refresh_market_data_rejects_too_many_tickers(monkeypatch):
    class FakeCache:
        def get_many(self, tickers):
            return []

    class FakeConnector:
        provider = "fake"

        def fetch_quotes(self, tickers):
            raise AssertionError("fetch_quotes should not run")

    monkeypatch.setenv("MARKET_DATA_MAX_REFRESH_TICKERS", "1")

    with pytest.raises(ValueError, match="market-data refresh is limited to 1 ticker"):
        refresh_market_data_quotes(
            ["AAPL", "MSFT"],
            portfolio_repository,
            connector=FakeConnector(),
            cache=FakeCache(),
            rate_limiter=InMemoryRateLimiter(),
        )


def test_worker_requeues_rate_limited_account_without_blocking_queue(monkeypatch):
    requeued = []

    def fake_refresh(*args, **kwargs):
        raise RateLimitExceeded("wait", retry_after_seconds=23)

    monkeypatch.setattr("app.background.worker.refresh_market_data_quotes", fake_refresh)
    monkeypatch.setattr(
        "app.background.worker.enqueue_background_job_message",
        lambda job, **kwargs: requeued.append((job, kwargs)),
    )
    portfolio = portfolio_repository.create(
        name="Deferred Market Data",
        base_currency="USD",
        cash=0,
        positions=[Position(symbol="AAPL", quantity=2, price=100)],
        lots=[],
        user_id="user-deferred",
    )
    job = portfolio_repository.enqueue_background_job(portfolio.id, "refresh_market_data")

    result = process_background_job(
        portfolio_repository,
        QueuedBackgroundJob(
            job_id=job.id,
            portfolio_id=portfolio.id,
            job_type="refresh_market_data",
            payload={"force": False, "defer_on_rate_limit": True},
        ),
    )

    assert result.status == "pending"
    assert "Waiting 23 second" in (result.message or "")
    assert len(requeued) == 1
    payload = requeued[0][1]["payload"]
    assert payload["defer_on_rate_limit"] is True
    assert payload["provider_signature"].startswith("account-")
    assert payload["deferred_until"]


def test_worker_processes_market_data_refresh_job(monkeypatch):
    calls = []

    def fake_refresh(tickers, repository, force=False, wait_for_rate_limit=False, provider_signature=None):
        calls.append((tickers, force, wait_for_rate_limit, provider_signature))
        quote = MarketQuote(ticker="AAPL", provider="fake", price=123)
        repository.upsert_market_quotes([quote])
        return [quote]

    monkeypatch.setattr("app.background.worker.refresh_market_data_quotes", fake_refresh)
    portfolio = portfolio_repository.create(
        name="Worker Market Data",
        base_currency="USD",
        cash=0,
        positions=[Position(symbol="AAPL", quantity=2, price=100)],
        lots=[],
        user_id="user-1",
    )
    job = portfolio_repository.enqueue_background_job(portfolio.id, "refresh_market_data")

    result = process_background_job(
        portfolio_repository,
        QueuedBackgroundJob(
            job_id=job.id,
            portfolio_id=portfolio.id,
            job_type="refresh_market_data",
            payload={"tickers": ["AAPL"], "force": True},
        ),
    )

    assert result.status == "completed"
    assert result.message == "Refreshed market data for 1 ticker(s); repriced 1 holding(s)."
    assert calls[0][:3] == (["AAPL"], True, True)
    assert calls[0][3].startswith("account-")
    assert portfolio_repository.get_market_quotes(["AAPL"])[0].price == pytest.approx(123)


def test_market_quote_application_reprices_manual_lots():
    from app.background.portfolio_tasks import apply_market_quotes_to_portfolio, record_manual_lots
    from app.db.models import MarketQuote

    portfolio = portfolio_repository.create(
        name="Reprice",
        base_currency="USD",
        cash=0,
        positions=[],
        lots=[],
        user_id="user-1",
    )
    portfolio = record_manual_lots(
        portfolio_repository,
        portfolio.id,
        [{"ticker": "AAPL", "quantity": 2, "purchase_price": 100}],
    )
    assert portfolio.positions[0].market_value == 200

    updated = apply_market_quotes_to_portfolio(
        portfolio_repository,
        portfolio.id,
        [MarketQuote(ticker="AAPL", price=125, provider="test")],
    )

    assert updated.positions[0].price == 125
    assert updated.positions[0].market_value == 250
    assert updated.lots[0].current_price == 125


def test_heatmap_plotly_customdata_has_numeric_parent_weights(client, auth_headers):
    created = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "Heatmap Plotly", "positions": [{"symbol": "AAPL", "quantity": 2, "price": 100}]},
    ).json()

    response = client.get(f"/portfolios/{created['id']}/heatmap", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    root_customdata = payload["plotly"]["customdata"][0]
    assert root_customdata[1] == pytest.approx(payload["total_market_value"])
    assert root_customdata[3] == pytest.approx(100)
