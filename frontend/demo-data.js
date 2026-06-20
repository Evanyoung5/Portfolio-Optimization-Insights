(function initPortfolioDemo(global) {
  const DAY_MS = 24 * 60 * 60 * 1000;
  const YEAR_MS = 365.25 * DAY_MS;
  const DEMO_PORTFOLIO_ID = "demo-balanced-growth";
  const DEFAULT_BENCHMARKS = ["SPY", "QQQ", "EFA"];
  const MAJOR_RANGES = ["day", "week", "month", "ytd", "year", "five_year", "max"];
  const NOW = new Date();
  const HISTORY_START = new Date("2010-01-04T00:00:00Z");

  const SYMBOL_CONFIG = {
    MSFT: { label: "Microsoft", asset_class: "equity", startPrice: 246, currentPrice: 482.15, previousClose: 476.08, vol: 0.022, beta: 1.08, drift: 0.00048, family: "equity" },
    VTI: { label: "Vanguard Total Stock Market", asset_class: "etf", startPrice: 212.3, currentPrice: 311.84, previousClose: 309.41, vol: 0.0128, beta: 0.99, drift: 0.00031, family: "equity" },
    VXUS: { label: "Vanguard Total Intl Stock", asset_class: "etf", startPrice: 55.7, currentPrice: 72.18, previousClose: 71.64, vol: 0.0117, beta: 0.82, drift: 0.00018, family: "equity" },
    AGG: { label: "iShares Core US Aggregate Bond", asset_class: "bond", startPrice: 99.1, currentPrice: 98.62, previousClose: 98.43, vol: 0.0041, beta: 0.12, drift: 0.00005, family: "bond" },
    GLD: { label: "SPDR Gold Shares", asset_class: "commodity", startPrice: 177.8, currentPrice: 248.06, previousClose: 245.91, vol: 0.0137, beta: 0.34, drift: 0.00022, family: "commodity" },
    VNQ: { label: "Vanguard Real Estate", asset_class: "etf", startPrice: 82.3, currentPrice: 91.47, previousClose: 90.23, vol: 0.0159, beta: 0.84, drift: 0.00014, family: "equity" },
    LQD: { label: "iShares Investment Grade Corporate Bond", asset_class: "bond", startPrice: 105.9, currentPrice: 110.24, previousClose: 109.66, vol: 0.0056, beta: 0.18, drift: 0.00008, family: "bond" },
    SPY: { label: "S&P 500", asset_class: "etf", startPrice: 383.6, currentPrice: 612.47, previousClose: 607.28, vol: 0.0125, beta: 1, drift: 0.00034, family: "benchmark" },
    QQQ: { label: "Nasdaq 100", asset_class: "etf", startPrice: 274.8, currentPrice: 541.18, previousClose: 534.72, vol: 0.0165, beta: 1.12, drift: 0.00043, family: "benchmark" },
    EFA: { label: "Developed Markets", asset_class: "etf", startPrice: 65.1, currentPrice: 91.83, previousClose: 91.22, vol: 0.0109, beta: 0.76, drift: 0.00018, family: "benchmark" },
    DIA: { label: "Dow Jones", asset_class: "etf", startPrice: 335.4, currentPrice: 458.12, previousClose: 454.44, vol: 0.0104, beta: 0.92, drift: 0.00024, family: "benchmark" },
    IWM: { label: "Russell 2000", asset_class: "etf", startPrice: 179.2, currentPrice: 247.66, previousClose: 245.11, vol: 0.0148, beta: 1.03, drift: 0.00021, family: "benchmark" },
  };

  const BASE_CORRELATIONS = {
    equity: { equity: 0.78, bond: 0.14, commodity: 0.18, benchmark: 0.82, cash: 0 },
    bond: { equity: 0.14, bond: 0.72, commodity: 0.08, benchmark: 0.12, cash: 0 },
    commodity: { equity: 0.18, bond: 0.08, commodity: 0.7, benchmark: 0.16, cash: 0 },
    benchmark: { equity: 0.82, bond: 0.12, commodity: 0.16, benchmark: 0.88, cash: 0 },
    cash: { equity: 0, bond: 0, commodity: 0, benchmark: 0, cash: 1 },
  };

  const RISK_TARGETS = {
    1: { label: "Capital preservation", targetVolatility: 0.04, equity: 0.1, bonds: 0.7, cash: 0.2 },
    2: { label: "Very conservative", targetVolatility: 0.06, equity: 0.2, bonds: 0.65, cash: 0.15 },
    3: { label: "Conservative", targetVolatility: 0.08, equity: 0.3, bonds: 0.6, cash: 0.1 },
    4: { label: "Conservative growth", targetVolatility: 0.1, equity: 0.4, bonds: 0.5, cash: 0.1 },
    5: { label: "Balanced", targetVolatility: 0.12, equity: 0.5, bonds: 0.45, cash: 0.05 },
    6: { label: "Balanced growth", targetVolatility: 0.14, equity: 0.6, bonds: 0.35, cash: 0.05 },
    7: { label: "Growth", targetVolatility: 0.17, equity: 0.7, bonds: 0.25, cash: 0.05 },
    8: { label: "High growth", targetVolatility: 0.2, equity: 0.8, bonds: 0.15, cash: 0.05 },
    9: { label: "Aggressive", targetVolatility: 0.24, equity: 0.9, bonds: 0.07, cash: 0.03 },
    10: { label: "Very aggressive", targetVolatility: 0.3, equity: 0.95, bonds: 0.03, cash: 0.02 },
  };

  const BOND_CATALOG = [
    { ticker: "BIL", name: "SPDR 1-3 Month T-Bill", category: "Treasury bills", duration_bucket: "0-1y", term_proxy_years: 0.2, risk_level: 1, price: 91.63, daily_return_pct: 0.04, issuer_url: "https://www.ssga.com/" },
    { ticker: "SHY", name: "iShares 1-3 Year Treasury", category: "Treasury", duration_bucket: "1-3y", term_proxy_years: 1.9, risk_level: 2, price: 82.94, daily_return_pct: 0.11, issuer_url: "https://www.ishares.com/" },
    { ticker: "IEF", name: "iShares 7-10 Year Treasury", category: "Treasury", duration_bucket: "7-10y", term_proxy_years: 8.0, risk_level: 4, price: 95.61, daily_return_pct: 0.29, issuer_url: "https://www.ishares.com/" },
    { ticker: "AGG", name: "iShares Core US Aggregate Bond", category: "Aggregate", duration_bucket: "5-7y", term_proxy_years: 6.2, risk_level: 3, price: 98.62, daily_return_pct: 0.19, issuer_url: "https://www.ishares.com/" },
    { ticker: "LQD", name: "iShares Investment Grade Corp", category: "Corporate", duration_bucket: "7-10y", term_proxy_years: 8.4, risk_level: 5, price: 110.24, daily_return_pct: 0.53, issuer_url: "https://www.ishares.com/" },
    { ticker: "TLT", name: "iShares 20+ Year Treasury", category: "Treasury", duration_bucket: "20+y", term_proxy_years: 16.8, risk_level: 6, price: 99.48, daily_return_pct: 0.74, issuer_url: "https://www.ishares.com/" },
    { ticker: "HYG", name: "iShares High Yield Corp", category: "High yield corporate", duration_bucket: "3-5y", term_proxy_years: 3.6, risk_level: 7, price: 79.42, daily_return_pct: 0.41, issuer_url: "https://www.ishares.com/" },
  ];

  function round(value, digits = 2) {
    const factor = Math.pow(10, digits);
    return Math.round(Number(value) * factor) / factor;
  }

  function deepClone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function symbolSeed(symbol) {
    return String(symbol || "").split("").reduce((sum, char) => sum + char.charCodeAt(0), 0);
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function businessDays(start, end) {
    const dates = [];
    const cursor = new Date(start);
    cursor.setUTCHours(0, 0, 0, 0);
    while (cursor <= end) {
      const day = cursor.getUTCDay();
      if (day !== 0 && day !== 6) dates.push(new Date(cursor));
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    return dates;
  }

  function isoDate(value) {
    return new Date(value).toISOString();
  }

  function uid(prefix) {
    return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function positionFamily(position) {
    const config = SYMBOL_CONFIG[position.ticker];
    if (config) return config.family;
    if (position.asset_class === "bond" || position.asset_class === "fixed_income") return "bond";
    if (position.asset_class === "commodity") return "commodity";
    return "equity";
  }

  function annualVolatilityFor(position) {
    return SYMBOL_CONFIG[position.ticker]?.vol ? SYMBOL_CONFIG[position.ticker].vol * Math.sqrt(252) : 0.18;
  }

  function currentConfigFor(symbol) {
    return SYMBOL_CONFIG[String(symbol || "").trim().toUpperCase()] || null;
  }

  function generateHistorySeries(symbol, startPrice, endPrice, drift, volScale, startDate = HISTORY_START, endDate = NOW) {
    const seed = symbolSeed(symbol);
    const dates = businessDays(startDate, endDate);
    const rawFactors = [1];
    let factor = 1;
    for (let index = 1; index < dates.length; index += 1) {
      const seasonal = Math.sin((index / (9 + (seed % 6))) + seed * 0.03) * 0.0075 * volScale;
      const swing = Math.cos((index / (23 + (seed % 5))) + seed * 0.07) * 0.0042 * volScale;
      const mean = drift + ((seed % 7) - 3) * 0.00002;
      const move = clamp(mean + seasonal + swing, -0.08, 0.08);
      factor *= 1 + move;
      rawFactors.push(factor);
    }
    const rawEnd = rawFactors[rawFactors.length - 1] || 1;
    const targetRatio = endPrice / Math.max(startPrice, 0.01);
    const scale = rawEnd > 0 ? targetRatio / rawEnd : 1;
    return rawFactors.map((raw, index) => {
      const progress = rawFactors.length > 1 ? index / (rawFactors.length - 1) : 1;
      const adjusted = startPrice * raw * Math.pow(scale, progress);
      return { as_of: dates[index].toISOString(), close: round(adjusted, 2) };
    });
  }

  function buildHistoryMap(portfolio, selectedBenchmarks) {
    const symbols = new Set([
      ...portfolio.lots.map((lot) => lot.ticker),
      ...selectedBenchmarks,
      "DIA",
      "IWM",
      "SPY",
      "QQQ",
      "EFA",
    ]);
    const map = new Map();
    symbols.forEach((symbol) => {
      const config = currentConfigFor(symbol);
      if (config) {
        map.set(symbol, generateHistorySeries(symbol, config.startPrice, config.currentPrice, config.drift, config.vol));
        return;
      }
      const lots = portfolio.lots.filter((lot) => lot.ticker === symbol);
      const firstLot = lots.sort((left, right) => new Date(left.purchased_at) - new Date(right.purchased_at))[0];
      const price = firstLot ? firstLot.purchase_price : 100;
      const startDate = firstLot ? new Date(firstLot.purchased_at) : new Date(NOW.getTime() - YEAR_MS);
      map.set(symbol, generateHistorySeries(symbol, price, price, 0.00005, 0.25, startDate, NOW));
    });
    return map;
  }

  function buildQuote(symbol, series) {
    const clean = series && series.length ? series : [{ as_of: NOW.toISOString(), close: 100 }];
    const current = clean[clean.length - 1];
    const previous = clean[Math.max(0, clean.length - 2)] || current;
    const price = Number(current.close) || 0;
    const previousClose = Number(previous.close) || price;
    const dailyReturnPct = previousClose > 0 ? ((price / previousClose) - 1) * 100 : 0;
    return {
      ticker: symbol,
      price: round(price, 2),
      previous_close: round(previousClose, 2),
      daily_return_pct: round(dailyReturnPct, 2),
      fetched_at: current.as_of || NOW.toISOString(),
    };
  }

  function lotCostBasis(lot) {
    const quantity = Number(lot.quantity) || 0;
    const remaining = Number(lot.remaining_quantity) || 0;
    const ratio = quantity > 0 ? remaining / quantity : 0;
    const fees = (Number(lot.fees) || 0) * ratio;
    return round((remaining * (Number(lot.purchase_price) || 0)) + fees, 2);
  }

  function quoteMap(quotes) {
    return new Map((quotes || []).map((quote) => [quote.ticker, quote]));
  }

  function rebuildPortfolioShape(sourcePortfolio, selectedBenchmarks) {
    const portfolio = deepClone(sourcePortfolio);
    portfolio.portfolio_id = portfolio.portfolio_id || DEMO_PORTFOLIO_ID;
    portfolio.settings = {
      portfolio_id: DEMO_PORTFOLIO_ID,
      risk_free_rate: 0.02,
      benchmark_symbols: DEFAULT_BENCHMARKS.slice(),
      cash_target_pct: 0.08,
      risk_tolerance_score: 6,
      bond_watchlist: ["AGG", "LQD", "SHY"],
      updated_at: NOW.toISOString(),
      ...(portfolio.settings || {}),
    };
    portfolio.lots = (portfolio.lots || []).map((lot) => ({
      id: lot.id || uid("demo-lot"),
      ticker: String(lot.ticker || "").trim().toUpperCase(),
      quantity: round(lot.quantity || 0, 4),
      remaining_quantity: round(lot.remaining_quantity == null ? lot.quantity : lot.remaining_quantity, 4),
      purchase_price: round(lot.purchase_price || 0, 4),
      current_price: round(lot.current_price || lot.purchase_price || 0, 4),
      fees: round(lot.fees || 0, 2),
      asset_class: lot.asset_class || currentConfigFor(lot.ticker)?.asset_class || "equity",
      purchased_at: lot.purchased_at || NOW.toISOString(),
      source: lot.source || "demo",
      notes: lot.notes || null,
    })).filter((lot) => Number(lot.remaining_quantity) > 0);
    portfolio.cash_transactions = (portfolio.cash_transactions || []).map((entry) => ({
      id: entry.id || uid("demo-cash"),
      transaction_type: entry.transaction_type || "deposit",
      amount: round(entry.amount || 0, 2),
      cash_delta: round(entry.cash_delta == null ? entry.amount : entry.cash_delta, 2),
      external_flow: round(entry.external_flow == null ? entry.amount : entry.external_flow, 2),
      currency: entry.currency || "USD",
      occurred_at: entry.occurred_at || NOW.toISOString(),
      source: entry.source || "demo",
      notes: entry.notes || null,
      created_at: entry.created_at || entry.occurred_at || NOW.toISOString(),
    }));
    portfolio.trade_history = (portfolio.trade_history || []).map((trade) => ({
      id: trade.id || uid("demo-trade"),
      ticker: String(trade.ticker || "").trim().toUpperCase(),
      side: trade.side || "buy",
      quantity: round(trade.quantity || 0, 4),
      price: round(trade.price || 0, 4),
      notional: round(trade.notional == null ? (trade.quantity || 0) * (trade.price || 0) : trade.notional, 2),
      fees: round(trade.fees || 0, 2),
      cash_delta: round(trade.cash_delta == null ? (trade.side === "sell" ? 1 : -1) * ((trade.quantity || 0) * (trade.price || 0)) - (trade.fees || 0) : trade.cash_delta, 2),
      realized_gain_loss: trade.realized_gain_loss == null ? null : round(trade.realized_gain_loss, 2),
      asset_class: trade.asset_class || currentConfigFor(trade.ticker)?.asset_class || "equity",
      occurred_at: trade.occurred_at || NOW.toISOString(),
      source: trade.source || "demo",
      lot_ids: Array.isArray(trade.lot_ids) ? trade.lot_ids : [],
      notes: trade.notes || null,
      created_at: trade.created_at || trade.occurred_at || NOW.toISOString(),
    }));
    portfolio.background_jobs = (portfolio.background_jobs || []).map((job) => ({
      ...job,
      id: job.id || uid("demo-job"),
      created_at: job.created_at || NOW.toISOString(),
      updated_at: job.updated_at || NOW.toISOString(),
    }));

    const history = buildHistoryMap(portfolio, selectedBenchmarks);
    const quotes = Array.from(new Set([...history.keys(), ...selectedBenchmarks, ...portfolio.lots.map((lot) => lot.ticker)])).map((symbol) => buildQuote(symbol, history.get(symbol)));
    const byTicker = quoteMap(quotes);

    portfolio.lots = portfolio.lots.map((lot) => {
      const quote = byTicker.get(lot.ticker);
      const currentPrice = Number(quote?.price) || lot.purchase_price || 0;
      const costBasis = lotCostBasis(lot);
      const marketValue = round((Number(lot.remaining_quantity) || 0) * currentPrice, 2);
      return {
        ...lot,
        current_price: round(currentPrice, 2),
        cost_basis: costBasis,
        market_value: marketValue,
        unrealized_gain_loss: round(marketValue - costBasis, 2),
      };
    });

    const positionsByTicker = new Map();
    portfolio.lots.forEach((lot) => {
      const current = positionsByTicker.get(lot.ticker) || {
        ticker: lot.ticker,
        asset_class: lot.asset_class || "equity",
        quantity: 0,
        cost_basis: 0,
        lots_count: 0,
      };
      current.quantity += Number(lot.remaining_quantity) || 0;
      current.cost_basis += Number(lot.cost_basis) || 0;
      current.lots_count += 1;
      positionsByTicker.set(lot.ticker, current);
    });

    const positions = Array.from(positionsByTicker.values()).map((position) => {
      const quote = byTicker.get(position.ticker);
      const currentPrice = Number(quote?.price) || currentConfigFor(position.ticker)?.currentPrice || 0;
      const marketValue = round((Number(position.quantity) || 0) * currentPrice, 2);
      const costBasis = round(position.cost_basis || 0, 2);
      const unrealized = round(marketValue - costBasis, 2);
      return {
        ticker: position.ticker,
        asset_class: position.asset_class,
        quantity: round(position.quantity, 4),
        current_price: round(currentPrice, 2),
        market_value: marketValue,
        cost_basis: costBasis,
        average_cost: position.quantity > 0 ? round(costBasis / position.quantity, 2) : 0,
        unrealized_gain_loss: unrealized,
        unrealized_gain_loss_pct: costBasis > 0 ? unrealized / costBasis : 0,
        lots_count: position.lots_count,
      };
    }).sort((left, right) => right.market_value - left.market_value);

    const marketValue = round(positions.reduce((sum, position) => sum + position.market_value, 0), 2);
    const totalCash = round(
      portfolio.cash_transactions.reduce((sum, item) => sum + (Number(item.cash_delta) || 0), 0)
      + portfolio.trade_history.reduce((sum, item) => sum + (Number(item.cash_delta) || 0), 0),
      2,
    );
    const totalEquity = round(marketValue + totalCash, 2);
    const totalCostBasis = round(positions.reduce((sum, position) => sum + position.cost_basis, 0), 2);
    const unrealized = round(positions.reduce((sum, position) => sum + position.unrealized_gain_loss, 0), 2);
    const netContributions = round(portfolio.cash_transactions.reduce((sum, item) => sum + (Number(item.external_flow) || 0), 0), 2);
    const accountGrowth = round(totalEquity - netContributions, 2);

    portfolio.positions = positions;
    portfolio.totals = {
      market_value: marketValue,
      cost_basis: totalCostBasis,
      cash: totalCash,
      total_equity: totalEquity,
      unrealized_gain_loss: unrealized,
      unrealized_gain_loss_pct: totalCostBasis > 0 ? unrealized / totalCostBasis : 0,
    };
    portfolio.performance = {
      invested_market_value: marketValue,
      idle_cash: totalCash,
      cash_weight: totalEquity > 0 ? totalCash / totalEquity : 0,
      net_contributions: netContributions,
      account_growth: accountGrowth,
      account_growth_pct: netContributions > 0 ? accountGrowth / netContributions : 0,
      risk_free_rate: Number(portfolio.settings.risk_free_rate) || 0.02,
      benchmark_symbols: selectedBenchmarks.slice(),
    };
    portfolio.charts = {
      allocation_by_ticker: positions.map((position) => ({ label: position.ticker, value: totalEquity > 0 ? position.market_value / totalEquity : 0 })),
      market_value_by_ticker: positions.map((position) => ({ label: position.ticker, value: position.market_value })),
      cost_basis_by_ticker: positions.map((position) => ({ label: position.ticker, value: position.cost_basis })),
      unrealized_gain_loss_by_ticker: positions.map((position) => ({ label: position.ticker, value: position.unrealized_gain_loss })),
    };
    return {
      portfolio,
      history,
      quotes,
    };
  }

  function buildSeedPortfolio() {
    return {
      portfolio_id: DEMO_PORTFOLIO_ID,
      name: "Demo Multi-Asset Portfolio",
      base_currency: "USD",
      settings: {
        portfolio_id: DEMO_PORTFOLIO_ID,
        risk_free_rate: 0.02,
        benchmark_symbols: DEFAULT_BENCHMARKS.slice(),
        cash_target_pct: 0.08,
        risk_tolerance_score: 6,
        bond_watchlist: ["AGG", "LQD", "SHY"],
        updated_at: NOW.toISOString(),
      },
      lots: [
        { id: "demo-lot-msft-1", ticker: "MSFT", quantity: 10, remaining_quantity: 10, purchase_price: 246, fees: 2, asset_class: "equity", purchased_at: "2010-01-06T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-vti-1", ticker: "VTI", quantity: 12, remaining_quantity: 12, purchase_price: 210, fees: 1, asset_class: "etf", purchased_at: "2011-03-14T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-vxus-1", ticker: "VXUS", quantity: 20, remaining_quantity: 20, purchase_price: 56, fees: 1, asset_class: "etf", purchased_at: "2012-06-11T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-agg-1", ticker: "AGG", quantity: 20, remaining_quantity: 20, purchase_price: 98, fees: 1, asset_class: "bond", purchased_at: "2013-02-19T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-gld-1", ticker: "GLD", quantity: 4, remaining_quantity: 4, purchase_price: 178, fees: 1, asset_class: "commodity", purchased_at: "2014-08-12T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-vnq-1", ticker: "VNQ", quantity: 10, remaining_quantity: 10, purchase_price: 82, fees: 1, asset_class: "etf", purchased_at: "2015-05-05T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-lqd-1", ticker: "LQD", quantity: 15, remaining_quantity: 15, purchase_price: 106, fees: 1, asset_class: "bond", purchased_at: "2017-09-18T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-msft-2", ticker: "MSFT", quantity: 5, remaining_quantity: 5, purchase_price: 338, fees: 2, asset_class: "equity", purchased_at: "2019-11-08T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-agg-2", ticker: "AGG", quantity: 8, remaining_quantity: 8, purchase_price: 95, fees: 1, asset_class: "bond", purchased_at: "2021-04-20T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-vti-2", ticker: "VTI", quantity: 10, remaining_quantity: 10, purchase_price: 250, fees: 1, asset_class: "etf", purchased_at: "2022-07-18T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-vnq-2", ticker: "VNQ", quantity: 6, remaining_quantity: 6, purchase_price: 88, fees: 1, asset_class: "etf", purchased_at: "2023-09-12T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-vxus-2", ticker: "VXUS", quantity: 15, remaining_quantity: 15, purchase_price: 61, fees: 1, asset_class: "etf", purchased_at: "2024-10-12T15:30:00Z", source: "demo_trade" },
        { id: "demo-lot-gld-2", ticker: "GLD", quantity: 2, remaining_quantity: 2, purchase_price: 213, fees: 1, asset_class: "commodity", purchased_at: "2025-01-08T15:30:00Z", source: "demo_trade" },
      ],
      cash_transactions: [
        { id: "demo-cash-1", transaction_type: "deposit", amount: 30000, cash_delta: 30000, external_flow: 30000, currency: "USD", occurred_at: "2010-01-04T14:30:00Z", source: "demo_seed", notes: "Initial cash funding.", created_at: "2010-01-04T14:30:00Z" },
        { id: "demo-cash-2", transaction_type: "deposit", amount: 5000, cash_delta: 5000, external_flow: 5000, currency: "USD", occurred_at: "2018-01-16T14:30:00Z", source: "demo_seed", notes: "Additional funding.", created_at: "2018-01-16T14:30:00Z" },
        { id: "demo-cash-3", transaction_type: "dividend", amount: 240, cash_delta: 240, external_flow: 0, currency: "USD", occurred_at: "2025-03-31T14:30:00Z", source: "demo_seed", notes: "Quarterly dividends collected.", created_at: "2025-03-31T14:30:00Z" },
      ],
      trade_history: [
        { id: "demo-trade-1", ticker: "MSFT", side: "buy", quantity: 10, price: 246, fees: 2, cash_delta: -2462, occurred_at: "2010-01-06T15:30:00Z", asset_class: "equity", source: "demo_seed", lot_ids: ["demo-lot-msft-1"] },
        { id: "demo-trade-2", ticker: "VTI", side: "buy", quantity: 12, price: 210, fees: 1, cash_delta: -2521, occurred_at: "2011-03-14T15:30:00Z", asset_class: "etf", source: "demo_seed", lot_ids: ["demo-lot-vti-1"] },
        { id: "demo-trade-3", ticker: "VXUS", side: "buy", quantity: 20, price: 56, fees: 1, cash_delta: -1121, occurred_at: "2012-06-11T15:30:00Z", asset_class: "etf", source: "demo_seed", lot_ids: ["demo-lot-vxus-1"] },
        { id: "demo-trade-4", ticker: "AGG", side: "buy", quantity: 20, price: 98, fees: 1, cash_delta: -1961, occurred_at: "2013-02-19T15:30:00Z", asset_class: "bond", source: "demo_seed", lot_ids: ["demo-lot-agg-1"] },
        { id: "demo-trade-5", ticker: "GLD", side: "buy", quantity: 4, price: 178, fees: 1, cash_delta: -713, occurred_at: "2014-08-12T15:30:00Z", asset_class: "commodity", source: "demo_seed", lot_ids: ["demo-lot-gld-1"] },
        { id: "demo-trade-6", ticker: "VNQ", side: "buy", quantity: 10, price: 82, fees: 1, cash_delta: -821, occurred_at: "2015-05-05T15:30:00Z", asset_class: "etf", source: "demo_seed", lot_ids: ["demo-lot-vnq-1"] },
        { id: "demo-trade-7", ticker: "LQD", side: "buy", quantity: 15, price: 106, fees: 1, cash_delta: -1591, occurred_at: "2017-09-18T15:30:00Z", asset_class: "bond", source: "demo_seed", lot_ids: ["demo-lot-lqd-1"] },
        { id: "demo-trade-8", ticker: "MSFT", side: "buy", quantity: 5, price: 338, fees: 2, cash_delta: -1692, occurred_at: "2019-11-08T15:30:00Z", asset_class: "equity", source: "demo_seed", lot_ids: ["demo-lot-msft-2"] },
        { id: "demo-trade-9", ticker: "AGG", side: "buy", quantity: 8, price: 95, fees: 1, cash_delta: -761, occurred_at: "2021-04-20T15:30:00Z", asset_class: "bond", source: "demo_seed", lot_ids: ["demo-lot-agg-2"] },
        { id: "demo-trade-10", ticker: "VTI", side: "buy", quantity: 10, price: 250, fees: 1, cash_delta: -2501, occurred_at: "2022-07-18T15:30:00Z", asset_class: "etf", source: "demo_seed", lot_ids: ["demo-lot-vti-2"] },
        { id: "demo-trade-11", ticker: "VNQ", side: "buy", quantity: 6, price: 88, fees: 1, cash_delta: -529, occurred_at: "2023-09-12T15:30:00Z", asset_class: "etf", source: "demo_seed", lot_ids: ["demo-lot-vnq-2"] },
        { id: "demo-trade-12", ticker: "VXUS", side: "buy", quantity: 15, price: 61, fees: 1, cash_delta: -916, occurred_at: "2024-10-12T15:30:00Z", asset_class: "etf", source: "demo_seed", lot_ids: ["demo-lot-vxus-2"] },
        { id: "demo-trade-13", ticker: "GLD", side: "buy", quantity: 2, price: 213, fees: 1, cash_delta: -427, occurred_at: "2025-01-08T15:30:00Z", asset_class: "commodity", source: "demo_seed", lot_ids: ["demo-lot-gld-2"] },
      ],
      background_jobs: [
        { id: "demo-job-1", job_type: "refresh_market_data", status: "completed", message: "Cached demo quotes were refreshed.", created_at: NOW.toISOString(), updated_at: NOW.toISOString() },
        { id: "demo-job-2", job_type: "refresh_market_history", status: "completed", message: "Demo performance history is loaded locally.", created_at: NOW.toISOString(), updated_at: NOW.toISOString() },
        { id: "demo-job-3", job_type: "option_snapshot_capture", status: "completed", message: "Demo options suite loaded an illustrative chain snapshot.", created_at: NOW.toISOString(), updated_at: NOW.toISOString() },
      ],
      valuation_snapshots: [],
    };
  }

  function correlationFor(left, right) {
    const leftFamily = BASE_CORRELATIONS[left] || BASE_CORRELATIONS.equity;
    return leftFamily[right] != null ? leftFamily[right] : 0.2;
  }

  function buildRiskAnalysis(portfolio) {
    const tickers = portfolio.positions.map((position) => position.ticker);
    const families = portfolio.positions.map((position) => positionFamily(position));
    const dailyVols = portfolio.positions.map((position) => round((annualVolatilityFor(position) / Math.sqrt(252)), 6));
    const correlationValues = tickers.map((ticker, rowIndex) => tickers.map((otherTicker, columnIndex) => {
      if (ticker === otherTicker) return 1;
      const base = correlationFor(families[rowIndex], families[columnIndex]);
      const tweak = ((symbolSeed(ticker) + symbolSeed(otherTicker)) % 11 - 5) * 0.01;
      return round(clamp(base + tweak, -0.35, 0.95), 3);
    }));
    const cleanedCorrelation = correlationValues.map((row, rowIndex) => row.map((value, columnIndex) => (
      rowIndex === columnIndex ? 1 : round(value * 0.93, 3)
    )));
    const covarianceValues = correlationValues.map((row, rowIndex) => row.map((value, columnIndex) => (
      round(value * dailyVols[rowIndex] * dailyVols[columnIndex], 8)
    )));
    const cleanedCovariance = cleanedCorrelation.map((row, rowIndex) => row.map((value, columnIndex) => (
      round(value * dailyVols[rowIndex] * dailyVols[columnIndex], 8)
    )));
    const observations = 252;
    return {
      charts: {
        risk: {
          observations,
          annualization_factor: 252,
          volatility_by_ticker: tickers.map((ticker, index) => ({ label: ticker, value: dailyVols[index] })),
          covariance: { tickers, values: covarianceValues },
          cleaned_covariance: { tickers, values: cleanedCovariance },
          correlation: { tickers, values: correlationValues },
          cleaned_correlation: { tickers, values: cleanedCorrelation },
          pairwise_observations: {
            tickers,
            values: tickers.map(() => tickers.map(() => observations)),
          },
        },
      },
    };
  }

  function buildPerformanceHistory(portfolio, historyMap, selectedBenchmarks) {
    const seriesSymbols = Array.from(new Set([...portfolio.positions.map((position) => position.ticker), ...selectedBenchmarks]));
    const lines = seriesSymbols.map((symbol) => ({
      ticker: symbol,
      points: (historyMap.get(symbol) || []).map((point) => ({ date: new Date(point.as_of), close: Number(point.close) })),
    }));
    const historyPayload = { series: lines, portfolio_series: [] };
    const history = {};
    MAJOR_RANGES.forEach((rangeName) => {
      history[`${portfolio.portfolio_id}:${rangeName}:${selectedBenchmarks.join(",")}`] = historyPayload;
    });
    return history;
  }

  function buildHeatmap(portfolio, quotes) {
    const byTicker = quoteMap(quotes);
    const totalMarketValue = Math.max(portfolio.totals.market_value, 1);
    const holdings = portfolio.positions.map((position) => {
      const quote = byTicker.get(position.ticker);
      return {
        label: position.ticker,
        ticker: position.ticker,
        market_value: position.market_value,
        cost_basis: position.cost_basis,
        portfolio_weight_pct: (position.market_value / totalMarketValue) * 100,
        daily_return_pct: quote?.daily_return_pct ?? null,
        unrealized_pnl: position.unrealized_gain_loss,
        unrealized_return_pct: position.unrealized_gain_loss_pct * 100,
      };
    });
    return {
      holdings,
      plotly: {
        labels: holdings.map((item) => item.label),
        parents: holdings.map(() => ""),
        values: holdings.map((item) => round(item.market_value, 2)),
        ids: holdings.map((item) => item.ticker),
        textinfo: "label+value+text",
        texttemplate: "%{label}<br>%{customdata[1]:.2f}% day<br>%{customdata[0]:.1f}% weight",
        customdata: holdings.map((item) => [item.portfolio_weight_pct, item.daily_return_pct ?? 0]),
        hovertemplate: "%{label}<br>Value $%{value:,.0f}<br>Weight %{customdata[0]:.1f}%<br>Daily %{customdata[1]:.2f}%<extra></extra>",
        colors: holdings.map((item) => round(item.daily_return_pct ?? 0, 2)),
        colorscale: [
          [0, "#a83732"],
          [0.25, "#cc6a47"],
          [0.5, "#5f6b68"],
          [0.75, "#2a8d67"],
          [1, "#14634a"],
        ],
      },
    };
  }

  function buildRiskTolerance(portfolio) {
    const score = clamp(Math.round(Number(portfolio.settings.risk_tolerance_score) || 6), 1, 10);
    const target = RISK_TARGETS[score];
    const weights = portfolio.positions.map((position) => position.market_value / Math.max(portfolio.totals.total_equity, 1));
    const volEstimate = Math.sqrt(weights.reduce((sum, weight, index) => sum + Math.pow(weight * annualVolatilityFor(portfolio.positions[index]), 2), 0));
    const estimatedScore = Object.entries(RISK_TARGETS).reduce((best, [candidate, config]) => (
      Math.abs(config.targetVolatility - volEstimate) < Math.abs(RISK_TARGETS[best].targetVolatility - volEstimate) ? Number(candidate) : best
    ), 5);
    return {
      profile: {
        score,
        label: target.label,
        description: score >= 7
          ? "Leans toward growth assets, accepts larger drawdowns, and uses bonds mostly as stabilizers."
          : score <= 3
            ? "Emphasizes principal stability, liquidity, and smaller expected swings."
            : "Balances equity growth with bond ballast and a modest cash reserve.",
        target_volatility: target.targetVolatility,
        target_allocation: { equity: target.equity, bonds: target.bonds, cash: target.cash },
        volatility_explanation: "Target volatility is an annualized estimate of typical variability, not a loss limit.",
      },
      current_model: {
        model_volatility: round(volEstimate, 4),
        estimated_score: estimatedScore,
      },
    };
  }

  function bucketForPosition(position) {
    const family = positionFamily(position);
    if (family === "bond") return "Bonds";
    if (family === "commodity") return "Diversifiers";
    return "Equities";
  }

  function normalizeWeights(weights, minWeight, maxWeight) {
    const count = weights.length;
    const minFloor = clamp(minWeight, 0, 1 / Math.max(count, 1));
    const maxCap = clamp(maxWeight, Math.max(minFloor, 1 / Math.max(count, 1)), 1);
    const result = Array(count).fill(minFloor);
    let remaining = 1 - (minFloor * count);
    const ranked = weights.map((weight, index) => ({ index, weight: Math.max(0, weight) }));
    ranked.sort((left, right) => right.weight - left.weight);
    const total = ranked.reduce((sum, item) => sum + item.weight, 0) || ranked.length;
    ranked.forEach((item) => {
      const proposed = remaining * ((total > 0 ? item.weight : 1) / total);
      result[item.index] += proposed;
    });
    let overflow = 0;
    result.forEach((value, index) => {
      if (value > maxCap) {
        overflow += value - maxCap;
        result[index] = maxCap;
      }
    });
    if (overflow > 0) {
      const flexible = result.map((value, index) => ({ index, value })).filter((item) => item.value < maxCap - 1e-6);
      const flexibleTotal = flexible.reduce((sum, item) => sum + item.value, 0) || flexible.length;
      flexible.forEach((item) => {
        result[item.index] += overflow * ((flexibleTotal > 0 ? item.value : 1) / flexibleTotal);
      });
    }
    const sum = result.reduce((accumulator, value) => accumulator + value, 0) || 1;
    return result.map((value) => value / sum);
  }

  function buildOptimization(portfolio, objective, minWeight, maxWeight, riskFreeRate) {
    const invested = Math.max(portfolio.totals.market_value, 1);
    const positions = portfolio.positions.slice();
    const scores = positions.map((position) => {
      const config = currentConfigFor(position.ticker) || {};
      const annualVol = annualVolatilityFor(position);
      if (objective === "equal_weight") return 1;
      if (objective === "min_volatility") return 1 / Math.max(annualVol, 0.01);
      const expectedReturn = config.drift ? (config.drift * 252) + 0.04 : 0.08;
      return Math.max(0.05, (expectedReturn - riskFreeRate) / Math.max(annualVol, 0.05));
    });
    const targetWeights = normalizeWeights(scores, minWeight, maxWeight);
    return {
      objective,
      allocations: positions.map((position, index) => {
        const currentWeight = position.market_value / invested;
        const targetWeight = targetWeights[index];
        return {
          symbol: position.ticker,
          current_weight: round(currentWeight, 6),
          target_weight: round(targetWeight, 6),
          trade_value_delta: round((targetWeight - currentWeight) * invested, 2),
        };
      }),
      notes: ["Demo optimization runs locally from simple risk and return estimates. Live optimization persists only for signed-in accounts."],
    };
  }

  function buildRiskReweight(portfolio) {
    const score = clamp(Math.round(Number(portfolio.settings.risk_tolerance_score) || 6), 1, 10);
    const target = RISK_TARGETS[score];
    const totalEquity = Math.max(portfolio.totals.total_equity, 1);
    const bondPositions = portfolio.positions.filter((position) => positionFamily(position) === "bond");
    const equityPositions = portfolio.positions.filter((position) => positionFamily(position) !== "bond" && positionFamily(position) !== "commodity");
    const diversifiers = portfolio.positions.filter((position) => positionFamily(position) === "commodity");
    const equityTarget = target.equity * 0.9;
    const diversifierTarget = target.equity * 0.1;
    const bondTarget = target.bonds;
    const rows = [];

    function distribute(positions, bucket, bucketTarget) {
      const bucketValue = positions.reduce((sum, position) => sum + position.market_value, 0);
      positions.forEach((position) => {
        const share = bucketValue > 0 ? position.market_value / bucketValue : 1 / Math.max(positions.length, 1);
        const targetWeight = bucketTarget * share;
        const currentWeight = position.market_value / totalEquity;
        rows.push({
          symbol: position.ticker,
          risk_bucket: bucket,
          current_weight: round(currentWeight, 6),
          target_weight: round(targetWeight, 6),
          current_value: round(position.market_value, 2),
          target_value: round(targetWeight * totalEquity, 2),
          trade_value_delta: round((targetWeight - currentWeight) * totalEquity, 2),
          estimated_quantity_delta: position.current_price > 0 ? round(((targetWeight - currentWeight) * totalEquity) / position.current_price, 3) : null,
        });
      });
    }

    distribute(equityPositions, "Equities", equityTarget);
    distribute(diversifiers, "Diversifiers", diversifierTarget);
    distribute(bondPositions, "Bonds", bondTarget);
    rows.push({
      symbol: "CASH",
      risk_bucket: "Cash",
      current_weight: round(portfolio.totals.cash / totalEquity, 6),
      target_weight: round(target.cash, 6),
      current_value: round(portfolio.totals.cash, 2),
      target_value: round(target.cash * totalEquity, 2),
      trade_value_delta: round((target.cash * totalEquity) - portfolio.totals.cash, 2),
      estimated_quantity_delta: null,
    });

    return {
      allocations: rows,
      notes: [
        `Score ${score} (${target.label}) shifts the demo mix toward ${Math.round(target.equity * 100)}% growth assets, ${Math.round(target.bonds * 100)}% bonds, and ${Math.round(target.cash * 100)}% cash.`,
      ],
    };
  }

  function buildBondAssets(portfolio) {
    const watchlist = new Set(portfolio.settings.bond_watchlist || []);
    return {
      note: "Demo bond prices are lightweight reference snapshots. They refresh only inside the full signed-in market-data workflow.",
      missing_tickers: [],
      assets: BOND_CATALOG.map((asset) => ({
        ...asset,
        monitored: watchlist.has(asset.ticker),
        description: asset.category === "treasury" ? "Government rate exposure." : asset.category === "credit" ? "Higher yield with higher credit risk." : "Broad investment-grade exposure.",
        fetched_at: NOW.toISOString(),
      })),
      recommended_ladder: [
        { label: "1-year rung", years_to_maturity: 1, coupon_rate: 0.04, yield_to_maturity: 0.041, market_price_pct: 100.2, face_value: 1000, allocation_weight: 0.2, payments_per_year: 2 },
        { label: "3-year rung", years_to_maturity: 3, coupon_rate: 0.041, yield_to_maturity: 0.042, market_price_pct: 99.8, face_value: 1000, allocation_weight: 0.2, payments_per_year: 2 },
        { label: "5-year rung", years_to_maturity: 5, coupon_rate: 0.042, yield_to_maturity: 0.043, market_price_pct: 99.1, face_value: 1000, allocation_weight: 0.2, payments_per_year: 2 },
        { label: "7-year rung", years_to_maturity: 7, coupon_rate: 0.043, yield_to_maturity: 0.044, market_price_pct: 98.4, face_value: 1000, allocation_weight: 0.2, payments_per_year: 2 },
        { label: "10-year rung", years_to_maturity: 10, coupon_rate: 0.044, yield_to_maturity: 0.045, market_price_pct: 97.7, face_value: 1000, allocation_weight: 0.2, payments_per_year: 2 },
      ],
      recommended_barbell: [
        { label: "2-year anchor", years_to_maturity: 2, coupon_rate: 0.04, yield_to_maturity: 0.041, market_price_pct: 100.1, face_value: 1000, allocation_weight: 0.4, payments_per_year: 2 },
        { label: "20-year anchor", years_to_maturity: 20, coupon_rate: 0.047, yield_to_maturity: 0.048, market_price_pct: 95.6, face_value: 1000, allocation_weight: 0.6, payments_per_year: 2 },
      ],
    };
  }

  function buildBondStrategy() {
    return {
      summary: {
        allocated_capital: 12000,
        annual_income: 528,
        portfolio_current_yield: 0.044,
        weighted_yield_to_maturity: 0.046,
        weighted_modified_duration: 5.8,
        weighted_annualized_return: 0.047,
      },
      notes: [
        "This demo ladder spreads reinvestment risk across several maturities.",
        "Longer rungs add sensitivity to rate changes but also raise carry.",
      ],
      rungs: [
        { label: "1-year rung", weight: 0.2, market_price_pct: 100.2, theoretical_price_pct: 100, coupon_rate: 0.04, yield_to_maturity: 0.041, modified_duration: 0.96, annual_income: 96, annualized_return: 0.041 },
        { label: "3-year rung", weight: 0.2, market_price_pct: 99.8, theoretical_price_pct: 99.9, coupon_rate: 0.041, yield_to_maturity: 0.042, modified_duration: 2.81, annual_income: 99, annualized_return: 0.042 },
        { label: "5-year rung", weight: 0.2, market_price_pct: 99.1, theoretical_price_pct: 99.2, coupon_rate: 0.042, yield_to_maturity: 0.043, modified_duration: 4.46, annual_income: 101, annualized_return: 0.043 },
        { label: "7-year rung", weight: 0.2, market_price_pct: 98.4, theoretical_price_pct: 98.7, coupon_rate: 0.043, yield_to_maturity: 0.044, modified_duration: 5.92, annual_income: 104, annualized_return: 0.044 },
        { label: "10-year rung", weight: 0.2, market_price_pct: 97.7, theoretical_price_pct: 98.1, coupon_rate: 0.044, yield_to_maturity: 0.045, modified_duration: 7.83, annual_income: 128, annualized_return: 0.045 },
      ],
      cash_flow_schedule: [
        { year: 1, coupon_income: 528, principal: 2400, total_cash_flow: 2928 },
        { year: 3, coupon_income: 432, principal: 2400, total_cash_flow: 2832 },
        { year: 5, coupon_income: 336, principal: 2400, total_cash_flow: 2736 },
        { year: 7, coupon_income: 240, principal: 2400, total_cash_flow: 2640 },
        { year: 10, coupon_income: 144, principal: 2400, total_cash_flow: 2544 },
      ],
    };
  }

  function normalCdf(value) {
    return 0.5 * (1 + erf(value / Math.sqrt(2)));
  }

  function erf(value) {
    const sign = value >= 0 ? 1 : -1;
    const x = Math.abs(value);
    const a1 = 0.254829592;
    const a2 = -0.284496736;
    const a3 = 1.421413741;
    const a4 = -1.453152027;
    const a5 = 1.061405429;
    const p = 0.3275911;
    const t = 1 / (1 + (p * x));
    const y = 1 - (((((a5 * t) + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
    return sign * y;
  }

  function blackScholesPrice(spot, strike, rate, sigma, tau, optionType) {
    const safeTau = Math.max(tau, 1 / 365);
    const safeSigma = Math.max(sigma, 0.01);
    const d1 = (Math.log(spot / strike) + (rate + (safeSigma * safeSigma) / 2) * safeTau) / (safeSigma * Math.sqrt(safeTau));
    const d2 = d1 - safeSigma * Math.sqrt(safeTau);
    if (optionType === "put") {
      return (strike * Math.exp(-rate * safeTau) * normalCdf(-d2)) - (spot * normalCdf(-d1));
    }
    return (spot * normalCdf(d1)) - (strike * Math.exp(-rate * safeTau) * normalCdf(d2));
  }

  function defaultOptionsInput(portfolio) {
    const firstTicker = portfolio.positions[0]?.ticker || "MSFT";
    return {
      symbol: firstTicker,
      expiry_date: "2026-12-18",
      rate: Number(portfolio.settings.risk_free_rate) || 0.02,
      sigma: 0.24,
      c_m: 2.65,
      option_type: "call",
      strike_min_pct: 0.85,
      strike_max_pct: 1.18,
      strike_detail: "auto",
    };
  }

  function runOptionsScenario(input, portfolio, quotes) {
    const params = { ...defaultOptionsInput(portfolio), ...(input || {}) };
    const symbol = String(params.symbol || defaultOptionsInput(portfolio).symbol).trim().toUpperCase();
    const spot = Number(quoteMap(quotes).get(symbol)?.price) || currentConfigFor(symbol)?.currentPrice || 100;
    const rate = Number(params.rate) || 0.02;
    const sigma = Number(params.sigma) || 0.24;
    const cM = Number(params.c_m) || 2.65;
    const expiryDate = params.expiry_date || "2026-12-18";
    const tau = Math.max(1 / 365, (new Date(`${expiryDate}T16:00:00Z`).getTime() - NOW.getTime()) / YEAR_MS);
    const detail = params.strike_detail || "auto";
    const pointCount = detail === "dense" ? 25 : detail === "listed" ? 13 : 17;
    const strikeMin = spot * (Number(params.strike_min_pct) || 0.85);
    const strikeMax = spot * (Number(params.strike_max_pct) || 1.18);
    const step = Math.max(5, Math.round((strikeMax - strikeMin) / Math.max(pointCount - 1, 1) / 5) * 5);
    const firstStrike = Math.floor(strikeMin / step) * step;
    const strikes = [];
    for (let strike = firstStrike; strike <= strikeMax + step; strike += step) strikes.push(strike);

    const optionChain = strikes.map((strike) => {
      const moneyness = strike / spot;
      const avgIv = clamp(sigma + 0.14 * Math.pow(moneyness - 1, 2) + (moneyness < 1 ? 0.025 : 0), 0.12, 0.6);
      const callIv = clamp(avgIv - 0.01 * (moneyness - 1), 0.1, 0.7);
      const putIv = clamp(avgIv + 0.015 * (1 - moneyness), 0.1, 0.75);
      const callBs = blackScholesPrice(spot, strike, rate, callIv, tau, "call");
      const putBs = blackScholesPrice(spot, strike, rate, putIv, tau, "put");
      const callCorrection = callBs * (0.01 + (0.02 * Math.exp(-Math.abs(moneyness - 1) * cM)));
      const putCorrection = putBs * (0.012 + (0.02 * Math.exp(-Math.abs(moneyness - 1) * cM)));
      const callRel = callBs + callCorrection;
      const putRel = putBs + putCorrection;
      const callMarket = callRel * (1 + Math.sin(strike * 0.03) * 0.012);
      const putMarket = putRel * (1 + Math.cos(strike * 0.027) * 0.011);
      const callSpread = Math.max(0.18, callMarket * 0.03);
      const putSpread = Math.max(0.18, putMarket * 0.03);
      return {
        strike: round(strike, 2),
        call: {
          bs_price: round(callBs, 4),
          relativistic_price: round(callRel, 4),
          price_correction: round(callCorrection, 4),
          market_iv: round(callIv, 4),
          bs_implied_vol_from_rel_price: round(callIv * 1.02, 4),
          bid: round(Math.max(0.01, callMarket - (callSpread / 2)), 4),
          ask: round(callMarket + (callSpread / 2), 4),
          market_last: round(callMarket, 4),
        },
        put: {
          bs_price: round(putBs, 4),
          relativistic_price: round(putRel, 4),
          price_correction: round(putCorrection, 4),
          market_iv: round(putIv, 4),
          bs_implied_vol_from_rel_price: round(putIv * 1.015, 4),
          bid: round(Math.max(0.01, putMarket - (putSpread / 2)), 4),
          ask: round(putMarket + (putSpread / 2), 4),
          market_last: round(putMarket, 4),
        },
      };
    });

    const nearest = optionChain.reduce((best, row) => (
      !best || Math.abs(row.strike - spot) < Math.abs(best.strike - spot) ? row : best
    ), null);
    const volumeRows = optionChain.map((row, index) => ({
      strike: row.strike,
      call_volume: Math.max(80, Math.round(1600 * Math.exp(-Math.abs((row.strike / spot) - 1) * 4.2) + (index * 11))),
      put_volume: Math.max(70, Math.round(1450 * Math.exp(-Math.abs((row.strike / spot) - 1) * 4.7) + (index * 9))),
    }));
    let cumulativeCall = 0;
    let cumulativePut = 0;
    const cumulativeVolume = volumeRows.map((row) => {
      cumulativeCall += row.call_volume;
      cumulativePut += row.put_volume;
      return { ...row, cumulative_call_volume: cumulativeCall, cumulative_put_volume: cumulativePut };
    });
    const gammaExposure = optionChain.map((row) => {
      const moneyness = row.strike / spot;
      const profile = Math.exp(-Math.pow((moneyness - 1) / 0.14, 2));
      const callGex = Math.round(profile * 220000 * (1 + Math.sin(row.strike * 0.02) * 0.12));
      const putGex = -Math.round(profile * 170000 * (1 + Math.cos(row.strike * 0.018) * 0.1));
      return {
        strike: row.strike,
        call_gamma_exposure: callGex,
        put_gamma_exposure: putGex,
        net_gamma_exposure: callGex + putGex,
        gross_gamma_exposure: Math.abs(callGex) + Math.abs(putGex),
      };
    });
    const smile = optionChain.map((row) => ({
      strike: row.strike,
      call_iv: row.call.market_iv,
      put_iv: row.put.market_iv,
      average_iv: round((row.call.market_iv + row.put.market_iv) / 2, 4),
      baseline_iv: round(sigma, 4),
    }));
    const surfaceExpiries = [
      { date: "2026-07-17", days: 28 },
      { date: "2026-09-18", days: 91 },
      { date: "2026-12-18", days: 182 },
      { date: "2027-03-19", days: 273 },
    ];
    const ivSurface = [];
    surfaceExpiries.forEach((expiry, expiryIndex) => {
      for (let moneyness = 0.8; moneyness <= 1.2 + 1e-6; moneyness += 0.05) {
        const term = 0.02 * expiryIndex;
        const skew = 0.16 * Math.pow(moneyness - 1, 2) + (moneyness < 1 ? 0.02 : 0);
        ivSurface.push({
          expiry_date: expiry.date,
          tau: round(expiry.days / 365.25, 6),
          moneyness: round(moneyness, 4),
          average_iv: round(clamp(sigma + term + skew, 0.12, 0.8), 4),
        });
      }
    });

    return {
      symbol,
      spot: round(spot, 2),
      chain_source: "demo",
      actual_expiry_date: expiryDate,
      parameters: {
        expiry_date: expiryDate,
        tau: round(tau, 6),
        rate: round(rate, 6),
        sigma: round(sigma, 6),
        c_m: round(cM, 6),
      },
      summary: [
        { label: "Spot", value: round(spot, 4) },
        { label: "ATM IV", value: nearest ? round((nearest.call.market_iv + nearest.put.market_iv) / 2, 4) : sigma },
        { label: "Rel correction", value: nearest ? round(nearest.call.price_correction, 4) : 0 },
        { label: "Tau", value: round(tau, 4) },
      ],
      warnings: ["This demo chain is illustrative and runs entirely in the browser. Sign in for cached live yfinance chains and saved snapshots."],
      baseline_volatility: {
        selected_sigma: sigma,
        recommended_sigma: round(sigma + 0.015, 4),
        estimates: [
          { label: "ATM IV snapshot", value: nearest ? round((nearest.call.market_iv + nearest.put.market_iv) / 2, 4) : sigma, detail: "Estimated from the nearest strike in the demo chain." },
          { label: "30-day realized", value: round(Math.max(0.12, sigma - 0.02), 4), detail: "Smoothed from the synthetic daily demo price path." },
          { label: "90-day realized", value: round(Math.max(0.12, sigma - 0.03), 4), detail: "Longer realized window, typically steadier than ATM IV." },
        ],
        notes: [
          "Use ATM IV when you want the model closest to the listed market surface.",
          "Use realized volatility when you want a quieter baseline that reacts less to short-lived option demand.",
        ],
      },
      option_chain: optionChain,
      volatility_smile: smile,
      cumulative_volume: cumulativeVolume,
      gamma_exposure: gammaExposure,
      iv_surface: ivSurface,
    };
  }

  function buildOptionsHistory(relativisticBs) {
    const points = [];
    const now = Date.now();
    for (let index = 24; index >= 0; index -= 1) {
      const asOf = new Date(now - (index * 14 * DAY_MS));
      const wave = Math.sin(index * 0.45);
      const drift = (24 - index) * 0.0008;
      const atmIv = clamp((relativisticBs.baseline_volatility?.selected_sigma || 0.24) + wave * 0.012 + drift, 0.14, 0.45);
      const gamma = 180000 + Math.round((Math.cos(index * 0.34) + 1.4) * 90000);
      const volume = 8200 + Math.round((Math.sin(index * 0.55) + 1.3) * 2400);
      const market = 28 + (Math.sin(index * 0.38) * 4.8) + drift * 35;
      const bs = market - 1.1;
      const rel = market + 0.6;
      points.push({
        as_of: asOf.toISOString(),
        atm_iv: round(atmIv, 4),
        total_gamma_exposure: gamma,
        total_volume: volume,
        atm_market_price: round(market, 4),
        atm_bs_price: round(bs, 4),
        atm_relativistic_price: round(rel, 4),
      });
    }
    return {
      note: "Demo snapshot history is already loaded, so zooming and resolution changes never fetch external data.",
      points,
    };
  }

  function buildSimpleImpact(portfolio, payload) {
    const side = payload.side === "sell" ? "sell" : "buy";
    const quantity = Math.max(0, Number(payload.quantity) || 0);
    const price = Math.max(0, Number(payload.price) || 0);
    const notional = quantity * price;
    const fees = notional * ((Number(payload.fee_rate_bps) || 0) / 10000);
    const slippage = notional * ((Number(payload.estimated_slippage_bps) || 0) / 10000);
    const direction = side === "sell" ? 1 : -1;
    const cashDelta = round((direction * notional) - fees - slippage, 2);
    const currentPosition = portfolio.positions.find((position) => position.ticker === payload.symbol.toUpperCase());
    const newValue = Math.max(0, (currentPosition?.market_value || 0) + ((side === "buy" ? 1 : -1) * notional));
    return {
      notional: round(notional, 2),
      estimated_fees: round(fees, 2),
      estimated_slippage: round(slippage, 2),
      cash_delta: cashDelta,
      post_trade_equity: round(portfolio.totals.total_equity - fees - slippage, 2),
      resulting_weight: portfolio.totals.total_equity > 0 ? newValue / portfolio.totals.total_equity : 0,
    };
  }

  function covarianceVector(tickers, covariance) {
    return tickers.map((rowTicker) => tickers.map((columnTicker) => Number(covariance?.[rowTicker]?.[columnTicker]) || 0));
  }

  function weightedVolatility(weights, matrix) {
    let variance = 0;
    for (let row = 0; row < weights.length; row += 1) {
      for (let column = 0; column < weights.length; column += 1) {
        variance += weights[row] * matrix[row][column] * weights[column];
      }
    }
    return Math.sqrt(Math.max(variance, 0));
  }

  function buildRiskSimulation(portfolio, payload, covariance) {
    const positions = portfolio.positions.slice();
    const tickers = positions.map((position) => position.ticker);
    const total = Math.max(portfolio.totals.market_value, 1);
    const beforeValues = positions.map((position) => position.market_value);
    const afterValues = beforeValues.slice();
    const ticker = String(payload.ticker || "").trim().toUpperCase();
    const index = tickers.indexOf(ticker);
    const deltaValue = Number(payload.notional) || ((Number(payload.quantity) || 0) * (Number(currentConfigFor(ticker)?.currentPrice) || Number(positions[index]?.current_price) || 0));
    if (index >= 0) afterValues[index] += (payload.side === "sell" ? -deltaValue : deltaValue);
    const beforeWeights = beforeValues.map((value) => value / total);
    const afterTotal = Math.max(afterValues.reduce((sum, value) => sum + value, 0), 1);
    const afterWeights = afterValues.map((value) => value / afterTotal);
    const matrix = covarianceVector(tickers, covariance);
    const beforeVol = weightedVolatility(beforeWeights, matrix);
    const afterVol = weightedVolatility(afterWeights, matrix);
    const afterMrc = afterWeights.map((_, rowIndex) => {
      const numerator = matrix[rowIndex].reduce((sum, value, columnIndex) => sum + (value * afterWeights[columnIndex]), 0);
      return afterVol > 0 ? numerator / afterVol : 0;
    });
    const beforeMrc = beforeWeights.map((_, rowIndex) => {
      const numerator = matrix[rowIndex].reduce((sum, value, columnIndex) => sum + (value * beforeWeights[columnIndex]), 0);
      return beforeVol > 0 ? numerator / beforeVol : 0;
    });
    return {
      before_volatility: round(beforeVol, 6),
      after_volatility: round(afterVol, 6),
      volatility_delta: round(afterVol - beforeVol, 6),
      charts: {
        component_risk_contribution_pct: tickers.map((currentTicker, rowIndex) => ({
          ticker: currentTicker,
          before: beforeVol > 0 ? round((beforeWeights[rowIndex] * beforeMrc[rowIndex]) / beforeVol, 6) : 0,
          after: afterVol > 0 ? round((afterWeights[rowIndex] * afterMrc[rowIndex]) / afterVol, 6) : 0,
        })),
      },
    };
  }

  function appendDemoJob(portfolio, jobType, message) {
    portfolio.background_jobs = portfolio.background_jobs || [];
    portfolio.background_jobs.push({
      id: uid("demo-job"),
      job_type: jobType,
      status: "completed",
      message,
      created_at: NOW.toISOString(),
      updated_at: NOW.toISOString(),
    });
  }

  function recordTrade(portfolio, payload) {
    const next = deepClone(portfolio);
    const ticker = String(payload.ticker || "").trim().toUpperCase();
    const side = payload.side === "sell" ? "sell" : "buy";
    const quantity = Math.max(0, Number(payload.quantity) || 0);
    const price = Math.max(0, Number(payload.price) || 0);
    const fees = round(Number(payload.fees) || 0, 2);
    const occurredAt = payload.occurred_at || NOW.toISOString();
    const assetClass = payload.asset_class || currentConfigFor(ticker)?.asset_class || "equity";
    const note = payload.notes || null;
    const notional = round(quantity * price, 2);
    const lotIds = [];

    if (side === "buy") {
      const lotId = uid("demo-lot");
      next.lots.push({
        id: lotId,
        ticker,
        quantity: round(quantity, 4),
        remaining_quantity: round(quantity, 4),
        purchase_price: round(price, 4),
        current_price: round(price, 4),
        fees,
        asset_class: assetClass,
        purchased_at: occurredAt,
        source: "demo_trade",
        notes: note,
      });
      lotIds.push(lotId);
    } else {
      let remaining = quantity;
      const openLots = next.lots.filter((lot) => lot.ticker === ticker).sort((left, right) => new Date(left.purchased_at) - new Date(right.purchased_at));
      const available = openLots.reduce((sum, lot) => sum + (Number(lot.remaining_quantity) || 0), 0);
      if (available + 1e-6 < quantity) {
        throw new Error(`Demo portfolio only has ${round(available, 4)} ${ticker} available to sell.`);
      }
      let realized = 0;
      openLots.forEach((lot) => {
        if (remaining <= 0) return;
        const lotRemaining = Number(lot.remaining_quantity) || 0;
        const used = Math.min(lotRemaining, remaining);
        if (used <= 0) return;
        const perShareFee = (Number(lot.fees) || 0) / Math.max(Number(lot.quantity) || 1, 1);
        realized += (price - (Number(lot.purchase_price) || 0)) * used - (perShareFee * used);
        lot.remaining_quantity = round(lotRemaining - used, 4);
        remaining = round(remaining - used, 4);
        lotIds.push(lot.id);
      });
      next.lots = next.lots.filter((lot) => Number(lot.remaining_quantity) > 0.0000001);
      payload.realized_gain_loss = round(realized - fees, 2);
    }

    next.trade_history.push({
      id: uid("demo-trade"),
      ticker,
      side,
      quantity: round(quantity, 4),
      price: round(price, 4),
      notional,
      fees,
      cash_delta: round((side === "sell" ? notional : -notional) - fees, 2),
      realized_gain_loss: payload.realized_gain_loss == null ? null : round(payload.realized_gain_loss, 2),
      asset_class: assetClass,
      occurred_at: occurredAt,
      source: "demo_trade",
      lot_ids: lotIds,
      notes: note,
      created_at: NOW.toISOString(),
    });
    appendDemoJob(next, "demo_trade", `${side === "buy" ? "Bought" : "Sold"} ${round(quantity, 4)} ${ticker} in the demo session.`);
    return next;
  }

  function addLot(portfolio, payload) {
    const next = deepClone(portfolio);
    next.lots.push({
      id: uid("demo-lot"),
      ticker: String(payload.ticker || "").trim().toUpperCase(),
      quantity: round(Number(payload.quantity) || 0, 4),
      remaining_quantity: round(Number(payload.quantity) || 0, 4),
      purchase_price: round(Number(payload.purchase_price) || 0, 4),
      current_price: round(Number(payload.purchase_price) || 0, 4),
      fees: round(Number(payload.fees) || 0, 2),
      asset_class: payload.asset_class || currentConfigFor(payload.ticker)?.asset_class || "equity",
      purchased_at: payload.purchased_at || NOW.toISOString(),
      source: "demo_lot",
      notes: payload.notes || null,
    });
    appendDemoJob(next, "demo_lot", `Added a dated holding lot for ${String(payload.ticker || "").toUpperCase()} in the demo session.`);
    return next;
  }

  function addCashTransaction(portfolio, payload) {
    const next = deepClone(portfolio);
    const type = payload.transaction_type || "deposit";
    const amount = round(Number(payload.amount) || 0, 2);
    const positive = ["deposit", "transfer_in", "dividend", "interest", "adjustment_in"].includes(type);
    const cashDelta = positive ? amount : -amount;
    const externalFlow = ["deposit", "transfer_in", "withdrawal", "transfer_out", "adjustment_in", "adjustment_out"].includes(type) ? cashDelta : 0;
    next.cash_transactions.push({
      id: uid("demo-cash"),
      transaction_type: type,
      amount,
      cash_delta: round(cashDelta, 2),
      external_flow: round(externalFlow, 2),
      currency: payload.currency || "USD",
      occurred_at: payload.occurred_at || NOW.toISOString(),
      source: "demo_cash",
      notes: payload.notes || null,
      created_at: NOW.toISOString(),
    });
    appendDemoJob(next, "demo_cash", `Recorded ${type.replace("_", " ")} cash movement in the demo session.`);
    return next;
  }

  function saveSettings(portfolio, payload) {
    const next = deepClone(portfolio);
    next.settings = {
      ...(next.settings || {}),
      ...payload,
      portfolio_id: next.portfolio_id || DEMO_PORTFOLIO_ID,
      updated_at: NOW.toISOString(),
    };
    appendDemoJob(next, "demo_settings", "Updated demo portfolio settings.");
    return next;
  }

  function deleteLot(portfolio, lotId) {
    const next = deepClone(portfolio);
    next.lots = next.lots.filter((lot) => lot.id !== lotId);
    appendDemoJob(next, "demo_delete", "Removed a lot from the demo portfolio.");
    return next;
  }

  function deletePosition(portfolio, ticker) {
    const next = deepClone(portfolio);
    const symbol = String(ticker || "").trim().toUpperCase();
    next.lots = next.lots.filter((lot) => lot.ticker !== symbol);
    appendDemoJob(next, "demo_delete", `Removed ${symbol} from the demo portfolio.`);
    return next;
  }

  function buildWorkspace(snapshot) {
    const seed = buildSeedPortfolio();
    const selectedBenchmarks = Array.isArray(snapshot?.selectedBenchmarks) && snapshot.selectedBenchmarks.length
      ? snapshot.selectedBenchmarks.map((symbol) => String(symbol).toUpperCase())
      : DEFAULT_BENCHMARKS.slice();
    const performanceRange = snapshot?.performanceRange || "max";
    const performanceResolution = snapshot?.performanceResolution || "1d";
    const sourcePortfolio = snapshot?.portfolio ? deepClone(snapshot.portfolio) : seed;
    const rebuilt = rebuildPortfolioShape(sourcePortfolio, selectedBenchmarks);
    const riskTolerance = buildRiskTolerance(rebuilt.portfolio);
    const riskReweight = buildRiskReweight(rebuilt.portfolio);
    const bondAssets = buildBondAssets(rebuilt.portfolio);
    const optionsInput = { ...defaultOptionsInput(rebuilt.portfolio), ...(snapshot?.optionsInput || {}) };
    const relativisticBs = runOptionsScenario(optionsInput, rebuilt.portfolio, rebuilt.quotes);
    return {
      demoMode: true,
      user: {
        email: "demo@portfolio.local",
        email_verified: true,
        created_at: "2026-01-03T14:30:00Z",
      },
      portfolios: [{
        id: rebuilt.portfolio.portfolio_id,
        name: rebuilt.portfolio.name,
        total_equity: rebuilt.portfolio.totals.total_equity,
        positions_count: rebuilt.portfolio.positions.length,
      }],
      selectedPortfolioId: rebuilt.portfolio.portfolio_id,
      portfolio: rebuilt.portfolio,
      marketData: {
        portfolio_id: rebuilt.portfolio.portfolio_id,
        quotes: rebuilt.quotes,
        missing_tickers: [],
      },
      performanceRange,
      performanceResolution,
      performanceHistory: buildPerformanceHistory(rebuilt.portfolio, rebuilt.history, selectedBenchmarks),
      selectedBenchmarks,
      riskAnalysis: buildRiskAnalysis(rebuilt.portfolio),
      heatmap: buildHeatmap(rebuilt.portfolio, rebuilt.quotes),
      riskTolerance,
      riskReweight,
      bondAssets,
      bondStrategy: buildBondStrategy(),
      optimization: buildOptimization(rebuilt.portfolio, "max_sharpe", 0, 1, Number(rebuilt.portfolio.settings.risk_free_rate) || 0.02),
      simpleImpact: null,
      riskSimulation: null,
      relativisticBs,
      relativisticBsHistory: buildOptionsHistory(relativisticBs),
      optionsInput,
    };
  }

  global.PORTFOLIO_DEMO = {
    defaultBenchmarks: DEFAULT_BENCHMARKS.slice(),
    buildWorkspace,
    buildHeatmap,
    buildRiskAnalysis,
    buildOptimization,
    buildSimpleImpact,
    buildRiskSimulation,
    buildRiskTolerance,
    buildRiskReweight,
    buildBondStrategy,
    runOptionsScenario,
    buildOptionsHistory,
    recordTrade,
    addLot,
    addCashTransaction,
    saveSettings,
    deleteLot,
    deletePosition,
  };
}(window));
