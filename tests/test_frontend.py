from pathlib import Path

def test_frontend_index_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Portfolio Optimization" in response.text
    assert "dashboard-quote-snapshot" in response.text
    assert "heatmap-quote-snapshot" in response.text
    assert "relativistic-bs-form" in response.text
    assert "relativistic-bs-expiry-date" in response.text
    assert "Relativistic Black-Scholes" in response.text
    assert "Normal Black-Scholes" in response.text
    assert "Use live option chain" in response.text
    assert "relativistic-bs-chart" in response.text
    assert "relativistic-bs-vol-guide" in response.text
    assert "relativistic-bs-smile-chart" in response.text
    assert "relativistic-bs-volume-chart" in response.text
    assert "relativistic-bs-gamma-chart" in response.text
    assert "relativistic-bs-iv-surface-chart" in response.text
    assert "Options Suite" in response.text
    assert "runtime-pill" in response.text
    assert "performance-summary" in response.text
    assert "performance-tooltip" in response.text
    assert "performance-reset-zoom" in response.text
    assert "risk-summary" in response.text
    assert "risk-covariance-heatmap" in response.text
    assert "raw-correlation-heatmap" in response.text
    assert "Customize graphs" in response.text
    assert "performance-resolution" in response.text
    assert "performance-coverage-note" in response.text
    assert "analytics-note" in response.text
    assert "client-history-options-ui-2026-06-01" in response.text
    assert "theme-toggle" in response.text
    assert "sidebar-toggle" in response.text
    assert "relativistic-bs-force-refresh" in response.text
    assert "relativistic-bs-history-resolution" in response.text
    assert "relativistic-bs-history-iv-chart" in response.text
    assert "portfolio_theme" in response.text
    assert response.headers["cache-control"] == "no-store"
    assert "plotly-2.32.0.min.js" in response.text
    assert "Current Price" not in response.text


def test_frontend_assets_are_served(client):
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "buildPerformanceSeries" in response.text
    assert "renderPlotlyHeatmap" in response.text
    assert "resetManualForm" in response.text
    assert "Return (%)" in response.text
    assert "quoteDailyReturnPct" in response.text
    assert "benchmark-check" in response.text
    assert "renderQuoteSnapshots" in response.text
    assert "quoteStateKey" in response.text
    assert "renderHtmlHeatmap" in response.text
    assert "combinedPerformanceHistory" in response.text
    assert "buildRiskPriceRowsFromHistory" in response.text
    assert "riskSummary" in response.text
    assert "CLIENT_BUILD_ID" in response.text
    assert "maybeQueueMissingMarketData" in response.text
    assert "niceReturnTicks" in response.text
    assert "renderPerformanceOverview" in response.text
    assert "maybeLoadPerformanceHistory" in response.text
    assert "performanceHistoryRangesForZoom" in response.text
    assert "effectivePerformanceResolution" in response.text
    assert "createPerformanceXScale" in response.text
    assert "estimateHistoricalAnalytics" in response.text
    assert "setPerformanceZoomWindow" in response.text
    assert "loadRelativisticBSHistory" in response.text
    assert "relbsDateAxis" in response.text
    assert "applySidebarState" in response.text
    assert "applyGraphVisibility" in response.text
    assert "renderRelativisticBS" in response.text
    assert "relativisticBSQuery" in response.text
    assert "setDefaultRelativisticBSExpiry" in response.text
    assert "relbsMarketPrice" in response.text
    assert "use_market_chain" in response.text
    assert "renderRelativisticBSChart" in response.text
    assert "renderRelbsVolatilitySmile" in response.text
    assert "renderRelbsGammaExposure" in response.text
    assert "renderRelbsIVSurface" in response.text
    assert "relbsStrikeAxis" in response.text
    assert "scrollZoom" in response.text
    assert "handleUseVolatilityEstimate" in response.text
    assert "applyTheme" in response.text
    assert "chartTheme" in response.text
    assert "/api/v1/runtime" in response.text


def test_dockerfile_includes_frontend_assets():
    dockerfile = Path("Dockerfile").read_text()

    assert "COPY frontend ./frontend" in dockerfile



def test_compose_project_name_is_stable():
    compose = Path("docker-compose.yml").read_text()

    assert compose.startswith("name: portfolio_optimization\n")


def test_runtime_endpoint_exposes_backend_identity(client):
    for path in ("/runtime", "/api/v1/runtime"):
        response = client.get(path)

        assert response.status_code == 200
        payload = response.json()
        assert payload["build_id"]
        assert payload["database"]["users"] == 0
        assert payload["database"]["portfolios"] == 0
        assert "redis" in payload
