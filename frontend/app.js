const CLIENT_BUILD_ID = "client-home-2026-06-20-5";
const THEME_STORAGE_KEY = "portfolio_theme";
const SIDEBAR_STORAGE_KEY = "portfolio_sidebar_collapsed";
const GRAPH_VISIBILITY_STORAGE_KEY = "portfolio_graph_visibility";
const DEMO_SESSION_STORAGE_KEY = "portfolio_demo_session";

const ASSET_MODEL = {
  cash: { return: 0.02, vol: 0.01, beta: 0 },
  bond: { return: 0.04, vol: 0.05, beta: 0.18 },
  fixed_income: { return: 0.04, vol: 0.05, beta: 0.18 },
  equity: { return: 0.08, vol: 0.16, beta: 1 },
  etf: { return: 0.075, vol: 0.14, beta: 0.92 },
  commodity: { return: 0.055, vol: 0.22, beta: 0.55 },
  crypto: { return: 0.12, vol: 0.65, beta: 1.45 },
};

const RISK_SCORE_TARGETS = {
  1: ["Capital preservation", 0.04, 0.10, 0.70, 0.20],
  2: ["Very conservative", 0.06, 0.20, 0.65, 0.15],
  3: ["Conservative", 0.08, 0.30, 0.60, 0.10],
  4: ["Conservative growth", 0.10, 0.40, 0.50, 0.10],
  5: ["Balanced", 0.12, 0.50, 0.45, 0.05],
  6: ["Balanced growth", 0.14, 0.60, 0.35, 0.05],
  7: ["Growth", 0.17, 0.70, 0.25, 0.05],
  8: ["High growth", 0.20, 0.80, 0.15, 0.05],
  9: ["Aggressive", 0.24, 0.90, 0.07, 0.03],
  10: ["Very aggressive", 0.30, 0.95, 0.03, 0.02],
};

const SERIES_COLORS = ["#0f766e", "#a35f00", "#8b1e3f", "#2f6f9f", "#5f5d1f", "#6d3b8f"];

const PERFORMANCE_RANGES = {
  day: { label: "Day", days: 1 },
  week: { label: "Week", days: 7 },
  month: { label: "Month", days: 31 },
  ytd: { label: "YTD", ytd: true },
  year: { label: "Year", days: 365 },
  five_year: { label: "5Y", days: 365 * 5 },
  max: { label: "Max", start: new Date("2005-01-03T00:00:00Z") },
};

const PERFORMANCE_RESOLUTIONS = {
  auto: { label: "Auto", bucketMs: null },
  "5m": { label: "5-minute", bucketMs: 5 * 60 * 1000 },
  "15m": { label: "15-minute", bucketMs: 15 * 60 * 1000 },
  "1h": { label: "Hourly", bucketMs: 60 * 60 * 1000 },
  "1d": { label: "Daily", bucketMs: 24 * 60 * 60 * 1000 },
  "1wk": { label: "Weekly", bucketMs: 7 * 24 * 60 * 60 * 1000 },
  "1mo": { label: "Monthly", bucketMs: 30 * 24 * 60 * 60 * 1000 },
};

const PERFORMANCE_RESOLUTION_ORDER = ["5m", "15m", "1h", "1d", "1wk", "1mo"];

const MAJOR_INDEXES = [
  { symbol: "SPY", label: "S&P 500" },
  { symbol: "QQQ", label: "Nasdaq 100" },
  { symbol: "DIA", label: "Dow" },
  { symbol: "IWM", label: "Russell 2000" },
  { symbol: "VTI", label: "US Total Market" },
  { symbol: "EFA", label: "Developed Intl" },
];

const INDEX_ANNUAL_RETURNS = {
  SPY: [[2005,0.0483],[2006,0.1561],[2007,0.0548],[2008,-0.3681],[2009,0.2636],[2010,0.1506],[2011,0.0189],[2012,0.16],[2013,0.3231],[2014,0.1346],[2015,0.0125],[2016,0.12],[2017,0.217],[2018,-0.0456],[2019,0.3122],[2020,0.1837],[2021,0.2875],[2022,-0.1817],[2023,0.2618],[2024,0.2489],[2025,0.1635],[2026,0.0934]],
  QQQ: [[2005,0.015],[2006,0.069],[2007,0.196],[2008,-0.416],[2009,0.544],[2010,0.199],[2011,0.034],[2012,0.183],[2013,0.367],[2014,0.192],[2015,0.094],[2016,0.071],[2017,0.329],[2018,-0.003],[2019,0.389],[2020,0.484],[2021,0.269],[2022,-0.326],[2023,0.548],[2024,0.255],[2025,0.2016],[2026,0.168]],
  DIA: [[2005,0.017],[2006,0.19],[2007,0.083],[2008,-0.32],[2009,0.225],[2010,0.141],[2011,0.08],[2012,0.102],[2013,0.299],[2014,0.098],[2015,-0.006],[2016,0.165],[2017,0.282],[2018,-0.033],[2019,0.251],[2020,0.097],[2021,0.209],[2022,-0.068],[2023,0.161],[2024,0.151],[2025,0.1294],[2026,0.0532]],
  IWM: [[2005,0.047],[2006,0.183],[2007,-0.014],[2008,-0.337],[2009,0.273],[2010,0.268],[2011,-0.043],[2012,0.163],[2013,0.389],[2014,0.048],[2015,-0.044],[2016,0.215],[2017,0.145],[2018,-0.112],[2019,0.254],[2020,0.199],[2021,0.146],[2022,-0.205],[2023,0.169],[2024,0.112],[2025,0.1266],[2026,0.1496]],
  VTI: [[2005,0.062],[2006,0.158],[2007,0.055],[2008,-0.37],[2009,0.287],[2010,0.172],[2011,0.01],[2012,0.163],[2013,0.335],[2014,0.125],[2015,0.004],[2016,0.126],[2017,0.214],[2018,-0.052],[2019,0.306],[2020,0.209],[2021,0.257],[2022,-0.195],[2023,0.264],[2024,0.236],[2025,0.1569],[2026,0.094]],
  EFA: [[2005,0.141],[2006,0.264],[2007,0.115],[2008,-0.434],[2009,0.315],[2010,0.077],[2011,-0.12],[2012,0.172],[2013,0.226],[2014,-0.052],[2015,-0.006],[2016,0.013],[2017,0.251],[2018,-0.137],[2019,0.222],[2020,0.08],[2021,0.113],[2022,-0.142],[2023,0.181],[2024,0.036],[2025,0.18],[2026,0.12]],
};

const appState = {
  token: localStorage.getItem("access_token") || "",
  refreshToken: localStorage.getItem("refresh_token") || "",
  user: null,
  portfolios: [],
  selectedPortfolioId: localStorage.getItem("selected_portfolio_id") || "",
  portfolio: null,
  marketData: { quotes: [], missing_tickers: [] },
  riskAnalysis: null,
  heatmap: null,
  optimization: null,
  simpleImpact: null,
  riskSimulation: null,
  relativisticBs: null,
  relativisticBsHistory: null,
  strategyLab: null,
  riskTolerance: null,
  riskReweight: null,
  bondAssets: null,
  bondStrategy: null,
  bondRungs: [],
  performanceRange: localStorage.getItem("performance_range") || "max",
  performanceResolution: localStorage.getItem("performance_resolution") || "auto",
  selectedBenchmarks: JSON.parse(localStorage.getItem("performance_benchmarks") || "[\"SPY\",\"QQQ\"]"),
  performanceHistory: {},
  performanceHistoryPending: {},
  performanceZoom: null,
  runtime: null,
  apiAvailable: false,
  theme: document.documentElement.dataset.theme || localStorage.getItem(THEME_STORAGE_KEY) || "light",
  sidebarCollapsed: localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true",
  mobileViewport: window.innerWidth <= 700,
  mobileSidebarPrimed: false,
  graphVisibility: JSON.parse(localStorage.getItem(GRAPH_VISIBILITY_STORAGE_KEY) || "{}"),
  demoMode: false,
  demoTourActive: false,
  demoTourStep: 0,
  demoOptionsInput: null,
  onboardingLotRowCounter: 0,
};

const DEMO_TOUR_STEPS = [
  {
    tab: "dashboard",
    selector: "#demo-banner",
    title: "Demo Sandbox",
    body: "This is a temporary browser-only workspace. You can inspect the sample portfolio, record demo trades, and leave without saving anything.",
  },
  {
    tab: "dashboard",
    selector: ".performance-panel",
    title: "Performance And Benchmarks",
    body: "The main chart compares the portfolio against major indexes. Change the range, zoom directly on the chart, and toggle benchmarks to see how the sample account behaved over time.",
  },
  {
    tab: "dashboard",
    selector: "#holdings-table",
    title: "Holdings And Cost Basis",
    body: "This table ties together quantity, current price, cost basis, and return. In the demo, try selling or adding to one of these existing symbols to watch the dashboard update.",
  },
  {
    tab: "entry",
    selector: ".entry-guide",
    title: "Manual Entry",
    body: "This is where the live product records lots, trades, and cash movements. In the demo, manual trades update the sample account immediately, but the changes disappear once the session ends.",
  },
  {
    tab: "risk",
    selector: ".risk-tolerance-panel",
    title: "Risk Profile",
    body: "The risk tab summarizes correlation, covariance, and a saved risk score. Use it to see how the current mix lines up with a conservative or growth-oriented allocation target.",
  },
  {
    tab: "bonds",
    selector: "#bond-assets-table",
    title: "Bond Monitor",
    body: "The bond monitor collects public fixed-income ETFs and structures them into ladders or barbells. The demo shows the layout and sample calculations without hitting the live market-data pipeline.",
  },
  {
    tab: "relativistic-bs",
    selector: "#relativistic-bs-chart",
    title: "Options Suite",
    body: "The options suite compares market pricing, Black-Scholes, and the relativistic adjustment across the chain, then follows implied volatility, gamma, and volume through time.",
  },
  {
    tab: "strategy-lab",
    selector: ".strategy-lab-chart-panel",
    title: "Strategy Lab",
    body: "This isolated lab runs lightweight scenarios from cached history without altering the account. It is a good place to test rebalancing ideas before building anything heavier.",
  },
  {
    tab: "heatmap",
    selector: "#heatmap-grid",
    title: "Portfolio Heatmap",
    body: "The heatmap sizes each tile by portfolio weight and colors it by the latest daily move. It is meant to give you the fastest glance at concentration and today's winners or laggards.",
  },
  {
    tab: "optimize",
    selector: "#optimization-results",
    title: "Optimization",
    body: "Optimization compares the current mix with model targets so visitors can see how different objectives change the recommended weights without risking a real account.",
  },
  {
    tab: "simulate",
    selector: "#simple-impact-results",
    title: "Trade Simulation",
    body: "Simulation estimates how a proposed trade would change weights, concentration, and portfolio risk before anything is committed. In demo mode it is fully local and disposable.",
  },
  {
    tab: "market",
    selector: "#quotes-table",
    title: "Market Data",
    body: "The live app uses cached quotes, background jobs, and rate limits. The demo shows the output shape while keeping market requests turned off.",
  },
  {
    tab: "account",
    selector: "#account-profile",
    title: "Account Controls",
    body: "Real accounts add persistence, privacy, and email-based recovery. From the top bar you can replay this walkthrough or exit the demo and return to the login screen.",
  },
];

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

window.addEventListener("DOMContentLoaded", () => {
  applyTheme(appState.theme, { persist: false, redraw: false });
  applySidebarState({ persist: false });
  applyGraphVisibility();
  normalizeNumericInputs();
  bindEvents();
  resetOnboardingLotRows();
  setDefaultRelativisticBSExpiry();
  boot();
});

async function boot() {
  await checkHealth();
  if (loadStoredDemoSession()) {
    enterDemoMode({ restartTour: false });
  } else {
    await loadWorkspace({ quietUnauthorized: true });
  }
}

function handleThemeToggle() {
  const nextTheme = appState.theme === "dark" ? "light" : "dark";
  applyTheme(nextTheme, { persist: true, redraw: true });
}

function applyTheme(theme, options = {}) {
  const normalized = theme === "dark" ? "dark" : "light";
  appState.theme = normalized;
  document.documentElement.dataset.theme = normalized;
  if (options.persist !== false) localStorage.setItem(THEME_STORAGE_KEY, normalized);
  renderThemeControl();
  if (options.redraw) redrawThemeSensitiveViews();
}

function renderThemeControl() {
  const toggle = $("#theme-toggle");
  const status = $("#theme-status");
  if (!toggle || !status) return;
  const dark = appState.theme === "dark";
  status.textContent = dark ? "Dark mode" : "Light mode";
  toggle.textContent = dark ? "Switch to light" : "Switch to dark";
  toggle.setAttribute("aria-pressed", String(dark));
}

function redrawThemeSensitiveViews() {
  if (appState.portfolio) {
    renderDashboard();
    renderRelativisticBS();
    renderStrategyLab();
    renderHeatmap();
  }
}

function handleSidebarToggle() {
  appState.sidebarCollapsed = !appState.sidebarCollapsed;
  applySidebarState({ persist: true });
}

function isMobileViewport() {
  return window.innerWidth <= 700;
}

function syncResponsiveWorkspaceChrome() {
  const mobile = isMobileViewport();
  const authed = Boolean((appState.user && !appState.demoMode) || appState.demoMode);
  const viewportChanged = mobile !== appState.mobileViewport;
  appState.mobileViewport = mobile;
  if (!authed) return;
  if (mobile && (viewportChanged || !appState.mobileSidebarPrimed)) {
    appState.sidebarCollapsed = true;
    appState.mobileSidebarPrimed = true;
    applySidebarState({ persist: false });
    return;
  }
  if (!mobile && viewportChanged) {
    applySidebarState({ persist: false });
  }
}

function collapseSidebarForMobile() {
  if (!isMobileViewport()) return;
  appState.sidebarCollapsed = true;
  appState.mobileSidebarPrimed = true;
  applySidebarState({ persist: false });
}

function applySidebarState(options = {}) {
  const shell = $("#app-shell");
  const toggle = $("#sidebar-toggle");
  if (!shell || !toggle) return;
  shell.classList.toggle("sidebar-collapsed", appState.sidebarCollapsed);
  toggle.setAttribute("aria-pressed", String(appState.sidebarCollapsed));
  toggle.setAttribute("aria-label", appState.sidebarCollapsed ? "Expand portfolio sidebar" : "Collapse portfolio sidebar");
  toggle.title = appState.sidebarCollapsed ? "Expand portfolio sidebar" : "Collapse portfolio sidebar";
  if (options.persist !== false) localStorage.setItem(SIDEBAR_STORAGE_KEY, String(appState.sidebarCollapsed));
}

function handleGraphVisibilityChange(event) {
  const input = event.target instanceof HTMLInputElement ? event.target.closest("input[data-graph-toggle]") : null;
  if (!input) return;
  appState.graphVisibility[input.dataset.graphToggle] = input.checked;
  localStorage.setItem(GRAPH_VISIBILITY_STORAGE_KEY, JSON.stringify(appState.graphVisibility));
  applyGraphVisibility();
}

function applyGraphVisibility() {
  $$("input[data-graph-toggle]").forEach((input) => {
    const visible = appState.graphVisibility[input.dataset.graphToggle] !== false;
    input.checked = visible;
  });
  $$("[data-graph-panel]").forEach((panel) => {
    panel.hidden = appState.graphVisibility[panel.dataset.graphPanel] === false;
  });
}

function bindEvents() {
  ["#bond-strategy-form", "#relativistic-bs-form"].forEach((selector) => {
    const form = $(selector);
    if (form) form.noValidate = true;
  });
  $("#login-form").addEventListener("submit", handleLogin);
  $("#register-form").addEventListener("submit", handleRegister);
  $("#password-reset-request-form").addEventListener("submit", handlePasswordResetRequest);
  $("#password-reset-confirm-form").addEventListener("submit", handlePasswordResetConfirm);
  $("#demo-start").addEventListener("click", () => enterDemoMode({ restartTour: true }));
  $("#landing-demo-top")?.addEventListener("click", () => enterDemoMode({ restartTour: true }));
  $("#home-access-demo")?.addEventListener("click", () => enterDemoMode({ restartTour: true }));
  $("#landing-nav-overview")?.addEventListener("click", () => scrollToLandingSection("#home-overview"));
  $("#landing-nav-process")?.addEventListener("click", () => scrollToLandingSection("#home-process"));
  $("#landing-nav-access")?.addEventListener("click", () => scrollToLandingSection("#home-access"));
  $("#home-signin-button")?.addEventListener("click", () => scrollToLandingSection("#home-access"));
  $("#verification-confirm-form").addEventListener("submit", handleVerificationConfirm);
  $("#request-verification").addEventListener("click", handleVerificationRequest);
  $("#theme-toggle").addEventListener("click", handleThemeToggle);
  $("#sidebar-toggle").addEventListener("click", handleSidebarToggle);
  $("#demo-tour-button").addEventListener("click", startDemoTour);
  $("#demo-exit-button").addEventListener("click", exitDemoMode);
  $("#demo-banner-tour").addEventListener("click", startDemoTour);
  $("#demo-banner-exit").addEventListener("click", exitDemoMode);
  $("#demo-tour-next").addEventListener("click", advanceDemoTour);
  $("#demo-tour-back").addEventListener("click", rewindDemoTour);
  $("#demo-tour-exit").addEventListener("click", exitDemoMode);
  document.addEventListener("change", handleGraphVisibilityChange);
  document.addEventListener("input", handleNumericInputNormalization, true);
  document.addEventListener("change", handleNumericInputNormalization, true);
  document.addEventListener("keydown", handleDemoTourKeydown);
  $("#logout-button").addEventListener("click", logout);
  $("#refresh-workspace").addEventListener("click", () => loadWorkspace());
  $("#create-portfolio-form").addEventListener("submit", handleCreatePortfolio);
  $("#create-portfolio-import-form").addEventListener("submit", handleCreatePortfolioFromCsv);
  $("#create-portfolio-lots-form").addEventListener("submit", handleCreatePortfolioWithStarterLots);
  $("#create-portfolio-empty-form").addEventListener("submit", handleCreateEmptyPortfolio);
  $("#portfolio-onboarding-add-row").addEventListener("click", handleAddOnboardingLotRow);
  $("#portfolio-onboarding-lot-rows").addEventListener("click", handleOnboardingLotRowClick);
  $("#lot-form").addEventListener("submit", handleAddLot);
  $("#cash-form").addEventListener("submit", handleAddCashTransaction);
  $("#trade-form").addEventListener("submit", handleAddTrade);
  $("#settings-form").addEventListener("submit", handleSaveSettings);
  $("#csv-form").addEventListener("submit", handleCsvUpload);
  $("#risk-form").addEventListener("submit", handleRiskAnalysis);
  $("#risk-tolerance-form").addEventListener("submit", handleRiskTolerance);
  $("#risk-tolerance-score").addEventListener("input", renderRiskTolerance);
  $("#bond-refresh").addEventListener("click", handleBondRefresh);
  $("#bond-category-filter").addEventListener("change", renderBonds);
  $("#bond-watchlist-only").addEventListener("change", renderBonds);
  $("#bond-assets-table").addEventListener("change", handleBondWatchlistChange);
  $("#bond-save-watchlist").addEventListener("click", handleBondSaveWatchlist);
  $("#bond-load-recommendation").addEventListener("click", loadRecommendedBondStructure);
  $("#bond-strategy-type").addEventListener("change", loadRecommendedBondStructure);
  $("#bond-add-rung").addEventListener("click", handleAddBondRung);
  $("#bond-rung-rows").addEventListener("click", handleRemoveBondRung);
  $("#bond-strategy-form").addEventListener("submit", handleBondStrategy);
  $("#relativistic-bs-form").addEventListener("submit", handleRelativisticBSRefresh);
  $("#relativistic-bs-force-refresh").addEventListener("click", handleRelativisticBSForceRefresh);
  $("#relativistic-bs-history-resolution").addEventListener("change", loadRelativisticBSHistory);
  $("#relativistic-bs-history-lookback").addEventListener("change", loadRelativisticBSHistory);
  $("#relativistic-bs-surface-expiry-min").addEventListener("change", handleRelbsSurfaceFilterChange);
  $("#relativistic-bs-surface-expiry-max").addEventListener("change", handleRelbsSurfaceFilterChange);
  $("#relativistic-bs-surface-moneyness-min").addEventListener("change", handleRelbsSurfaceFilterChange);
  $("#relativistic-bs-surface-moneyness-max").addEventListener("change", handleRelbsSurfaceFilterChange);
  $("#relativistic-bs-surface-reset").addEventListener("click", resetRelbsSurfaceFilters);
  $("#relativistic-bs-vol-guide").addEventListener("click", handleUseVolatilityEstimate);
  $("#strategy-lab-form").addEventListener("submit", handleStrategyLab);
  $("#strategy-lab-universe").addEventListener("change", handleStrategyLabUniverseChange);
  $("#heatmap-form").addEventListener("submit", handleHeatmap);
  $("#optimization-form").addEventListener("submit", handleOptimization);
  $("#optimization-form").addEventListener("change", () => {
    appState.optimization = null;
    renderOptimization();
  });
  $("#simple-impact-form").addEventListener("submit", handleSimpleImpact);
  $("#risk-simulation-form").addEventListener("submit", handleRiskSimulation);
  $("#market-refresh").addEventListener("click", handleMarketRefresh);
  $("#dashboard-refresh-market").addEventListener("click", handleMarketRefresh);
  $("#performance-range").addEventListener("click", handlePerformanceRange);
  $("#performance-resolution").addEventListener("change", handlePerformanceResolution);
  $("#performance-reset-zoom").addEventListener("click", resetPerformanceZoom);
  $("#benchmark-selector").addEventListener("change", handleBenchmarkSelection);
  $("#risk-correlation-threshold").addEventListener("input", renderRisk);
  $("#holdings-table").addEventListener("click", handleDeleteClick);
  $("#lots-table").addEventListener("click", handleDeleteClick);

  $("#portfolio-list").addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target ? target.closest("button[data-portfolio-id]") : null;
    if (!button) return;
    selectPortfolio(button.dataset.portfolioId);
  });

  $$(".tab").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tab));
  });
  window.addEventListener("resize", () => {
    syncResponsiveWorkspaceChrome();
    if (appState.portfolio && $("#dashboard")?.classList.contains("active")) renderDashboard();
    if (appState.portfolio && $("#strategy-lab")?.classList.contains("active")) renderStrategyLab();
    if (appState.demoTourActive) positionDemoTour();
  });
}

function handleNumericInputNormalization(event) {
  const input = event.target instanceof HTMLInputElement ? event.target.closest('input[type="number"]') : null;
  if (!input) return;
  normalizeNumericInput(input, { coerceStep: event.type === "change" });
}

function normalizeNumericInputs(root = document) {
  $$('input[type="number"]', root).forEach((input) => normalizeNumericInput(input));
}

function normalizeNumericInput(input, options = {}) {
  const raw = String(input.value || "").trim();
  if (!raw) return;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    input.value = "";
    return;
  }
  let normalized = parsed;
  const step = String(input.step || "").toLowerCase();
  const min = Number(input.min);
  if (options.coerceStep && step && step !== "any") {
    const stepValue = Number(step);
    if (Number.isFinite(stepValue) && stepValue > 0) {
      const base = Number.isFinite(min) ? min : 0;
      const units = Math.round((normalized - base) / stepValue);
      normalized = base + (units * stepValue);
    }
  }
  input.value = normalizedNumberString(normalized, step);
}

function normalizedNumberString(value, step = "") {
  if (!Number.isFinite(value)) return "";
  const normalizedStep = String(step || "").toLowerCase();
  if (!normalizedStep || normalizedStep === "any") return String(value);
  const decimal = normalizedStep.includes(".") ? normalizedStep.split(".")[1].length : 0;
  return decimal ? value.toFixed(decimal) : String(Math.round(value));
}

async function checkHealth() {
  try {
    const payload = await api("/health", { auth: false });
    appState.apiAvailable = payload.status === "ok";
  } catch (error) {
    appState.apiAvailable = false;
  }

  renderAuthState();
  await refreshRuntime({ retries: 3 });
}

function scrollToLandingSection(selector) {
  const target = $(selector);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
}

function loadStoredDemoSession() {
  try {
    const raw = localStorage.getItem(DEMO_SESSION_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    localStorage.removeItem(DEMO_SESSION_STORAGE_KEY);
    return null;
  }
}

function persistDemoSession() {
  if (!appState.demoMode || !appState.portfolio) return;
  const snapshot = {
    portfolio: appState.portfolio,
    selectedBenchmarks: appState.selectedBenchmarks,
    optionsInput: appState.demoOptionsInput || currentDemoOptionsInput(),
    performanceRange: appState.performanceRange,
    performanceResolution: appState.performanceResolution,
  };
  localStorage.setItem(DEMO_SESSION_STORAGE_KEY, JSON.stringify(snapshot));
}

function clearDemoSession() {
  localStorage.removeItem(DEMO_SESSION_STORAGE_KEY);
}

function currentDemoOptionsInput() {
  const symbol = $("#relativistic-bs-symbol")?.value?.trim().toUpperCase() || appState.relativisticBs?.symbol || appState.portfolio?.positions?.[0]?.ticker || "MSFT";
  const expiryDate = $("#relativistic-bs-expiry-date")?.value || appState.relativisticBs?.actual_expiry_date || "2026-12-18";
  return {
    symbol,
    expiry_date: expiryDate,
    rate: relativisticBSNumber("#relativistic-bs-rate", appState.portfolio?.settings?.risk_free_rate ?? 0.02),
    sigma: relativisticBSNumber("#relativistic-bs-sigma", appState.relativisticBs?.parameters?.sigma ?? 0.24),
    c_m: relativisticBSNumber("#relativistic-bs-cm", appState.relativisticBs?.parameters?.c_m ?? 2.65),
    option_type: $("#relativistic-bs-option-type")?.value || "call",
    strike_min_pct: relativisticBSNumber("#relativistic-bs-strike-min-pct", 0.85),
    strike_max_pct: relativisticBSNumber("#relativistic-bs-strike-max-pct", 1.18),
    strike_detail: $("#relativistic-bs-strike-detail")?.value || "auto",
  };
}

function applyDemoWorkspace(workspace, options = {}) {
  appState.demoMode = true;
  appState.demoTourActive = options.keepTour ? appState.demoTourActive : false;
  appState.user = workspace.user;
  appState.portfolios = workspace.portfolios || [];
  appState.selectedPortfolioId = workspace.selectedPortfolioId;
  appState.portfolio = workspace.portfolio;
  appState.marketData = workspace.marketData || { quotes: [], missing_tickers: [] };
  appState.performanceHistory = workspace.performanceHistory || {};
  appState.performanceHistoryPending = {};
  appState.performanceZoom = null;
  appState.selectedBenchmarks = workspace.selectedBenchmarks || appState.selectedBenchmarks;
  appState.riskAnalysis = workspace.riskAnalysis || null;
  appState.heatmap = workspace.heatmap || null;
  appState.optimization = workspace.optimization || null;
  appState.simpleImpact = workspace.simpleImpact || null;
  appState.riskSimulation = workspace.riskSimulation || null;
  appState.relativisticBs = workspace.relativisticBs || null;
  appState.relativisticBsHistory = workspace.relativisticBsHistory || null;
  appState.strategyLab = null;
  appState.riskTolerance = workspace.riskTolerance || null;
  appState.riskReweight = workspace.riskReweight || null;
  appState.bondAssets = workspace.bondAssets || null;
  appState.bondStrategy = workspace.bondStrategy || null;
  appState.bondRungs = [];
  appState.demoOptionsInput = workspace.optionsInput || currentDemoOptionsInput();
  appState.performanceRange = workspace.performanceRange || appState.performanceRange;
  appState.performanceResolution = workspace.performanceResolution || appState.performanceResolution;
  renderAuthState();
  renderAll();
  syncDemoOptionsForm();
  persistDemoSession();
}

function syncDemoOptionsForm() {
  if (!appState.demoOptionsInput) return;
  const fields = appState.demoOptionsInput;
  if ($("#relativistic-bs-symbol")) $("#relativistic-bs-symbol").value = fields.symbol || "MSFT";
  if ($("#relativistic-bs-expiry-date")) $("#relativistic-bs-expiry-date").value = fields.expiry_date || $("#relativistic-bs-expiry-date").value;
  if ($("#relativistic-bs-rate")) $("#relativistic-bs-rate").value = fields.rate ?? $("#relativistic-bs-rate").value;
  if ($("#relativistic-bs-sigma")) $("#relativistic-bs-sigma").value = fields.sigma ?? $("#relativistic-bs-sigma").value;
  if ($("#relativistic-bs-cm")) $("#relativistic-bs-cm").value = fields.c_m ?? $("#relativistic-bs-cm").value;
  if ($("#relativistic-bs-option-type")) $("#relativistic-bs-option-type").value = fields.option_type || "call";
  if ($("#relativistic-bs-strike-min-pct")) $("#relativistic-bs-strike-min-pct").value = fields.strike_min_pct ?? 0.85;
  if ($("#relativistic-bs-strike-max-pct")) $("#relativistic-bs-strike-max-pct").value = fields.strike_max_pct ?? 1.18;
  if ($("#relativistic-bs-strike-detail")) $("#relativistic-bs-strike-detail").value = fields.strike_detail || "auto";
}

function enterDemoMode({ restartTour = true } = {}) {
  const snapshot = loadStoredDemoSession();
  const workspace = window.PORTFOLIO_DEMO.buildWorkspace(snapshot || undefined);
  if (snapshot?.performanceRange) appState.performanceRange = snapshot.performanceRange;
  if (snapshot?.performanceResolution) appState.performanceResolution = snapshot.performanceResolution;
  applyDemoWorkspace(workspace);
  activateTab("dashboard");
  if (restartTour) {
    window.setTimeout(() => startDemoTour(), 100);
  } else {
    stopDemoTour();
  }
  toast("Demo workspace loaded.");
}

function exitDemoMode() {
  stopDemoTour();
  clearDemoSession();
  appState.demoMode = false;
  appState.demoOptionsInput = null;
  clearAuth();
  renderAuthState();
  renderAll();
  toast("Returned to the sign-in screen.");
}

function refreshDemoWorkspace(portfolioOverride, options = {}) {
  if (!appState.demoMode) return;
  const snapshot = {
    portfolio: portfolioOverride || appState.portfolio,
    selectedBenchmarks: appState.selectedBenchmarks,
    optionsInput: options.optionsInput || appState.demoOptionsInput || currentDemoOptionsInput(),
    performanceRange: appState.performanceRange,
    performanceResolution: appState.performanceResolution,
  };
  const workspace = window.PORTFOLIO_DEMO.buildWorkspace(snapshot);
  applyDemoWorkspace(workspace, { keepTour: true });
  if (options.tabId) activateTab(options.tabId);
}

function startDemoTour() {
  if (!appState.demoMode) return;
  appState.demoTourActive = true;
  appState.demoTourStep = 0;
  showDemoTourStep();
}

function stopDemoTour() {
  appState.demoTourActive = false;
  const overlay = $("#demo-tour-overlay");
  const popover = $("#demo-tour-popover");
  if (overlay) overlay.hidden = true;
  if (popover) popover.hidden = true;
  $(".demo-tour-target")?.classList.remove("demo-tour-target");
  $$(".demo-tour-target").forEach((node) => node.classList.remove("demo-tour-target"));
}

function advanceDemoTour() {
  if (!appState.demoTourActive) return;
  if (appState.demoTourStep >= DEMO_TOUR_STEPS.length - 1) {
    stopDemoTour();
    toast("The walkthrough can be replayed from the top bar any time.");
    return;
  }
  appState.demoTourStep += 1;
  showDemoTourStep();
}

function rewindDemoTour() {
  if (!appState.demoTourActive) return;
  appState.demoTourStep = Math.max(0, appState.demoTourStep - 1);
  showDemoTourStep();
}

function handleDemoTourKeydown(event) {
  if (!appState.demoTourActive) return;
  if (event.key === "Escape") stopDemoTour();
  if (event.key === "ArrowRight" || event.key === "Enter") advanceDemoTour();
  if (event.key === "ArrowLeft") rewindDemoTour();
}

function showDemoTourStep() {
  const step = DEMO_TOUR_STEPS[appState.demoTourStep];
  if (!step) return;
  if (step.tab) {
    if (step.selector && step.selector.includes("sidebar")) {
      appState.sidebarCollapsed = false;
      applySidebarState({ persist: true });
    }
    activateTab(step.tab);
  }
  const target = $(step.selector);
  const overlay = $("#demo-tour-overlay");
  const popover = $("#demo-tour-popover");
  if (!target || !overlay || !popover) return;
  $$(".demo-tour-target").forEach((node) => node.classList.remove("demo-tour-target"));
  target.classList.add("demo-tour-target");
  target.scrollIntoView({ block: "center", behavior: "smooth" });
  $("#demo-tour-title").textContent = step.title;
  $("#demo-tour-body").textContent = step.body;
  $("#demo-tour-step").textContent = `${appState.demoTourStep + 1} / ${DEMO_TOUR_STEPS.length}`;
  $("#demo-tour-back").disabled = appState.demoTourStep === 0;
  $("#demo-tour-next").textContent = appState.demoTourStep === DEMO_TOUR_STEPS.length - 1 ? "Finish" : "Next";
  overlay.hidden = false;
  popover.hidden = false;
  window.setTimeout(() => positionDemoTour(), 60);
}

function positionDemoTour() {
  if (!appState.demoTourActive) return;
  const step = DEMO_TOUR_STEPS[appState.demoTourStep];
  const target = step ? $(step.selector) : null;
  const popover = $("#demo-tour-popover");
  if (!target || !popover) return;
  const margin = 16;
  const rect = target.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  popover.style.maxHeight = `${Math.max(280, viewportHeight - (margin * 2))}px`;
  const popoverRect = popover.getBoundingClientRect();
  const hasRoomBelow = rect.bottom + 18 + popoverRect.height <= viewportHeight - margin;
  const hasRoomAbove = rect.top - 18 - popoverRect.height >= margin;
  let top;
  if (hasRoomBelow) {
    top = rect.bottom + 18;
  } else if (hasRoomAbove) {
    top = rect.top - popoverRect.height - 18;
  } else {
    top = Math.round((viewportHeight - popoverRect.height) / 2);
  }
  top = Math.min(Math.max(top, margin), viewportHeight - popoverRect.height - margin);
  const desiredLeft = rect.left + (rect.width / 2) - (popoverRect.width / 2);
  const left = Math.min(Math.max(desiredLeft, margin), viewportWidth - popoverRect.width - margin);
  popover.style.top = `${Math.round(top)}px`;
  popover.style.left = `${Math.round(left)}px`;
}

async function api(path, options = {}) {
  const request = { method: options.method || "GET", headers: {}, credentials: "same-origin" };
  const useAuth = options.auth !== false;
  if (appState.demoMode && useAuth) {
    throw new Error("This action needs a signed-in account. The demo keeps changes only in this browser session.");
  }
  if (useAuth && appState.token) {
    request.headers.Authorization = `Bearer ${appState.token}`;
  }

  if (options.body instanceof FormData) {
    request.body = options.body;
  } else if (options.body !== undefined) {
    request.headers["Content-Type"] = "application/json";
    request.body = JSON.stringify(options.body);
  }

  let response = await fetch(path, request);
  if (
    response.status === 401
    && useAuth
    && options.retryOnAuthFailure !== false
    && !path.startsWith("/auth/")
  ) {
    const refreshed = await refreshSession().catch(() => false);
    if (refreshed) {
      if (appState.token) request.headers.Authorization = `Bearer ${appState.token}`;
      else delete request.headers.Authorization;
      response = await fetch(path, request);
    }
  }
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (error) {
      payload = text;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && useAuth) {
      clearAuth();
      renderAuthState();
    }
    const detail = payload && payload.detail ? payload.detail : `Request failed with ${response.status}`;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg || item).join("; ") : detail);
  }
  return payload;
}

async function refreshSession() {
  if (appState.demoMode) return false;
  const request = { method: "POST", headers: {}, credentials: "same-origin" };
  if (appState.refreshToken) {
    request.headers["Content-Type"] = "application/json";
    request.body = JSON.stringify({ refresh_token: appState.refreshToken });
  }
  const response = await fetch("/auth/refresh", request);
  if (!response.ok) {
    throw new Error("Session refresh failed.");
  }
  const auth = await response.json();
  setAuth(auth);
  clearLegacyAuthStorage();
  return true;
}

async function handleLogin(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formObject(form);
  try {
    const auth = await api("/auth/login", { method: "POST", body: payload, auth: false });
    setAuth(auth);
    await loadWorkspace();
    toast(appState.portfolios.length ? "Logged in." : "Logged in. Choose a starting path for your first portfolio below.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formObject(form);
  try {
    const auth = await api("/auth/register", { method: "POST", body: payload, auth: false });
    setAuth(auth);
    await loadWorkspace();
    toast(appState.portfolios.length ? "Account created." : "Account created. Start by importing a brokerage file or typing in your first holdings below.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handlePasswordResetRequest(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const payload = formObject(form);
    const result = await api("/auth/password-reset/request", { method: "POST", body: payload, auth: false });
    toast(result.dev_token ? `Reset token: ${result.dev_token}` : result.message);
  } catch (error) {
    toast(error.message, true);
  }
}

async function handlePasswordResetConfirm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const payload = formObject(form);
    const result = await api("/auth/password-reset/confirm", { method: "POST", body: payload, auth: false });
    form.reset();
    toast(result.message);
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleVerificationRequest() {
  try {
    const result = await api("/auth/email-verification/request", { method: "POST" });
    toast(result.dev_token ? `Verification token: ${result.dev_token}` : result.message);
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleVerificationConfirm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const result = await api("/auth/email-verification/confirm", {
      method: "POST",
      body: formObject(form),
      auth: false,
    });
    appState.user = result;
    renderAccount();
    toast("Email verified.");
  } catch (error) {
    toast(error.message, true);
  }
}

function setAuth(auth) {
  clearDemoSession();
  stopDemoTour();
  appState.demoMode = false;
  appState.token = auth.access_token;
  appState.refreshToken = auth.refresh_token;
  appState.user = auth.user;
  clearLegacyAuthStorage();
}

function clearAuth() {
  appState.demoMode = false;
  appState.demoTourActive = false;
  appState.demoTourStep = 0;
  appState.demoOptionsInput = null;
  appState.token = "";
  appState.refreshToken = "";
  appState.user = null;
  appState.portfolios = [];
  appState.portfolio = null;
  appState.performanceHistory = {};
  appState.performanceHistoryPending = {};
  appState.performanceZoom = null;
  appState.riskTolerance = null;
  appState.riskReweight = null;
  appState.bondAssets = null;
  appState.bondStrategy = null;
  appState.bondRungs = [];
  clearLegacyAuthStorage();
  localStorage.removeItem("selected_portfolio_id");
}

function clearLegacyAuthStorage() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

async function logout() {
  try {
    await api("/auth/logout", {
      method: "POST",
      body: appState.refreshToken ? { refresh_token: appState.refreshToken } : undefined,
      retryOnAuthFailure: false,
    });
  } catch (error) {
    // Logout is local even if the token was already revoked.
  }
  clearAuth();
  renderAuthState();
  toast("Logged out.");
}

async function loadWorkspace(options = {}) {
  if (appState.demoMode) {
    refreshDemoWorkspace(appState.portfolio);
    return;
  }
  try {
    appState.user = await api("/me");
    const portfolioPayload = await api("/me/portfolios");
    appState.portfolios = portfolioPayload.portfolios || [];
    if (!appState.selectedPortfolioId && appState.portfolios.length) {
      appState.selectedPortfolioId = appState.portfolios[0].id;
    }
    if (appState.selectedPortfolioId && !appState.portfolios.some((item) => item.id === appState.selectedPortfolioId)) {
      appState.selectedPortfolioId = appState.portfolios[0]?.id || "";
    }
    renderAuthState();
    renderPortfolioList();
    if (appState.selectedPortfolioId) {
      await loadPortfolio(appState.selectedPortfolioId);
    } else {
      appState.portfolio = null;
      renderAll();
    }
  } catch (error) {
    if (!options.quietUnauthorized || !/login is required|invalid or expired token|access token has expired/i.test(String(error.message).toLowerCase())) {
      toast(error.message, true);
    }
    clearAuth();
    renderAuthState();
  }
}

async function selectPortfolio(portfolioId) {
  if (appState.demoMode) return;
  appState.selectedPortfolioId = portfolioId;
  localStorage.setItem("selected_portfolio_id", portfolioId);
  await loadPortfolio(portfolioId);
  collapseSidebarForMobile();
}

async function loadPortfolio(portfolioId) {
  if (appState.demoMode) return;
  appState.portfolio = await api(`/portfolios/${portfolioId}`);
  appState.marketData = await api(`/portfolios/${portfolioId}/market-data`).catch(() => ({ quotes: [], missing_tickers: [] }));
  appState.riskTolerance = await api(`/portfolios/${portfolioId}/risk-tolerance`).catch(() => null);
  appState.heatmap = null;
  appState.performanceHistory = {};
  appState.performanceHistoryPending = {};
  appState.performanceZoom = null;
  appState.optimization = null;
  appState.simpleImpact = null;
  appState.riskSimulation = null;
  appState.relativisticBs = null;
  appState.relativisticBsHistory = null;
  appState.strategyLab = null;
  appState.riskReweight = null;
  appState.bondAssets = null;
  appState.bondStrategy = null;
  appState.bondRungs = [];
  renderAll();
  maybeQueueMissingMarketData();
}

async function handleDeleteClick(event) {
  const target = event.target instanceof Element ? event.target : null;
  const button = target ? target.closest("button[data-delete-kind]") : null;
  if (!button || !requirePortfolio()) return;
  const kind = button.dataset.deleteKind;
  const id = button.dataset.deleteId;
  const label = button.dataset.deleteLabel || id;
  if (!window.confirm(`Delete ${label}?`)) return;
  if (appState.demoMode) {
    try {
      const nextPortfolio = kind === "lot"
        ? window.PORTFOLIO_DEMO.deleteLot(appState.portfolio, id)
        : window.PORTFOLIO_DEMO.deletePosition(appState.portfolio, id);
      refreshDemoWorkspace(nextPortfolio, { tabId: kind === "lot" ? "entry" : "dashboard" });
      toast(`${label} removed from the demo session.`);
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const path = kind === "lot"
      ? `/portfolios/${appState.selectedPortfolioId}/lots/${encodeURIComponent(id)}`
      : `/portfolios/${appState.selectedPortfolioId}/positions/${encodeURIComponent(id)}`;
    appState.portfolio = await api(path, { method: "DELETE" });
    appState.heatmap = null;
    invalidatePerformanceHistory();
    await refreshSelected(false);
    toast(`${label} removed.`);
  } catch (error) {
    toast(error.message, true);
  }
}

function handlePerformanceRange(event) {
  const target = event.target instanceof Element ? event.target.closest("button[data-range]") : null;
  if (!target) return;
  appState.performanceRange = target.dataset.range;
  appState.performanceZoom = null;
  localStorage.setItem("performance_range", appState.performanceRange);
  renderDashboard();
}

function handlePerformanceResolution(event) {
  appState.performanceResolution = event.currentTarget.value || "auto";
  localStorage.setItem("performance_resolution", appState.performanceResolution);
  renderDashboard();
}

function handleBenchmarkSelection() {
  appState.selectedBenchmarks = $$("#benchmark-selector input:checked").map((item) => item.value);
  appState.performanceZoom = null;
  localStorage.setItem("performance_benchmarks", JSON.stringify(appState.selectedBenchmarks));
  if (appState.demoMode) {
    refreshDemoWorkspace(appState.portfolio, { tabId: "dashboard" });
    return;
  }
  renderDashboard();
}

function resetPerformanceZoom() {
  appState.performanceZoom = null;
  renderDashboard();
}

async function handleCreatePortfolio(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (appState.demoMode) {
    toast("The demo uses a single temporary portfolio. Sign in to create persistent portfolios.", true);
    return;
  }
  try {
    const payload = basePortfolioPayload(form);
    const created = await api("/portfolios", { method: "POST", body: payload });
    resetManualForm(form, { base_currency: "USD", cash: "0" });
    await finishPortfolioCreation(created.id, { tabId: "entry" });
    toast("Empty account created. Add holdings or import a brokerage file from the Entry tab whenever you're ready.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleCreateEmptyPortfolio(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (appState.demoMode) {
    toast("The demo uses a single temporary portfolio. Sign in to create persistent portfolios.", true);
    return;
  }
  try {
    const payload = basePortfolioPayload(form);
    const created = await api("/portfolios", { method: "POST", body: payload });
    resetManualForm(form, { base_currency: "USD", cash: "0" });
    await finishPortfolioCreation(created.id, { tabId: "entry" });
    toast("Account created. You can add lots, trades, or a brokerage upload whenever you're ready.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleCreatePortfolioWithStarterLots(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (appState.demoMode) {
    toast("The demo uses a single temporary portfolio. Sign in to create persistent portfolios.", true);
    return;
  }
  try {
    const payload = basePortfolioPayload(form);
    payload.lots = readOnboardingLots(form);
    if (!payload.lots.length) throw new Error("Add at least one holding row, or use the empty-account option instead.");
    const created = await api("/portfolios", { method: "POST", body: payload });
    resetManualForm(form, { base_currency: "USD", cash: "0" });
    resetOnboardingLotRows();
    await finishPortfolioCreation(created.id, { tabId: "dashboard" });
    toast("Account created with starter lots. Quotes and performance will begin filling in automatically.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleCreatePortfolioFromCsv(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (appState.demoMode) {
    toast("CSV import is disabled in the demo. Sign in to import a real portfolio.", true);
    return;
  }

  let createdId = "";
  const resultBox = $("#onboarding-import-result");
  try {
    if (resultBox) resultBox.textContent = "Creating the account and reading your brokerage file...";
    const payload = basePortfolioPayload(form);
    const file = form.elements.file?.files?.[0];
    if (!file) throw new Error("Choose a brokerage export file to import.");

    const created = await api("/portfolios", { method: "POST", body: payload });
    createdId = created.id;
    const data = new FormData();
    data.append("file", file);
    const result = await api(`/api/v1/portfolios/${createdId}/upload-csv`, {
      method: "POST",
      body: data,
    });
    resetManualForm(form, { base_currency: "USD", cash: "0" });
    if (resultBox) {
      const source = String(result.detected_format || "generic").replace(/^./, (letter) => letter.toUpperCase());
      const warningText = (result.warnings || []).join(" ");
      resultBox.innerHTML = `<strong>${escapeHtml(source)} import complete.</strong><span>Imported ${result.imported_positions} position${result.imported_positions === 1 ? "" : "s"} from ${result.rows_read || 0} row${result.rows_read === 1 ? "" : "s"}.</span>${warningText ? `<span>${escapeHtml(warningText)}</span>` : ""}`;
    }
    await finishPortfolioCreation(createdId, { tabId: "dashboard" });
    toast("Account created and brokerage file imported. Quote refresh will run automatically.");
  } catch (error) {
    if (createdId) {
      await finishPortfolioCreation(createdId, { tabId: "entry" }).catch(() => {});
      if (resultBox) resultBox.textContent = `${error.message} The account shell was still created, so you can retry the import from the Entry tab.`;
      toast(`${error.message} The account shell was created, so you can retry the import from the Entry tab.`, true);
      return;
    }
    if (resultBox) resultBox.textContent = error.message;
    toast(error.message, true);
  }
}

async function handleAddLot(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    try {
      const data = formObject(form);
      const nextPortfolio = window.PORTFOLIO_DEMO.addLot(appState.portfolio, {
        ticker: data.ticker,
        quantity: numberValue(data.quantity),
        purchase_price: numberValue(data.purchase_price),
        fees: numberValue(data.fees),
        asset_class: data.asset_class || "equity",
        purchased_at: data.purchased_at ? dateToIso(data.purchased_at) : new Date().toISOString(),
        notes: data.notes || null,
      });
      resetManualForm(form, { asset_class: "equity", fees: "0" });
      refreshDemoWorkspace(nextPortfolio, { tabId: "entry" });
      toast("Demo lot added.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const data = formObject(form);
    const lot = {
      ticker: data.ticker,
      quantity: numberValue(data.quantity),
      purchase_price: numberValue(data.purchase_price),
      fees: numberValue(data.fees),
      asset_class: data.asset_class || "equity",
    };
    if (data.purchased_at) lot.purchased_at = dateToIso(data.purchased_at);
    if (data.notes) lot.notes = data.notes;
    appState.portfolio = await api(`/portfolios/${appState.selectedPortfolioId}/lots`, {
      method: "POST",
      body: { lots: [lot] },
    });
    invalidatePerformanceHistory();
    resetManualForm(form, { asset_class: "equity", fees: "0" });
    await refreshSelected(false);
    pollLatestMarketRefresh();
    toast("Lot added. Quote refresh will run automatically.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleAddCashTransaction(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    try {
      const data = formObject(form);
      const nextPortfolio = window.PORTFOLIO_DEMO.addCashTransaction(appState.portfolio, {
        transaction_type: data.transaction_type,
        amount: numberValue(data.amount),
        currency: data.currency ? data.currency.toUpperCase() : "USD",
        occurred_at: data.occurred_at ? dateToIso(data.occurred_at) : new Date().toISOString(),
        notes: data.notes || null,
      });
      resetManualForm(form);
      refreshDemoWorkspace(nextPortfolio, { tabId: "entry" });
      toast("Demo cash entry added.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const data = formObject(form);
    const payload = {
      transaction_type: data.transaction_type,
      amount: numberValue(data.amount),
    };
    if (data.currency) payload.currency = data.currency.toUpperCase();
    if (data.occurred_at) payload.occurred_at = dateToIso(data.occurred_at);
    if (data.notes) payload.notes = data.notes;
    appState.portfolio = await api(`/portfolios/${appState.selectedPortfolioId}/cash-transactions`, {
      method: "POST",
      body: payload,
    });
    invalidatePerformanceHistory();
    resetManualForm(form);
    await refreshSelected(false);
    toast("Cash entry added.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleAddTrade(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    try {
      const data = formObject(form);
      const nextPortfolio = window.PORTFOLIO_DEMO.recordTrade(appState.portfolio, {
        ticker: data.ticker,
        side: data.side,
        quantity: numberValue(data.quantity),
        price: numberValue(data.price),
        fees: numberValue(data.fees),
        asset_class: data.asset_class || "equity",
        occurred_at: data.occurred_at ? dateToIso(data.occurred_at) : new Date().toISOString(),
        notes: data.notes || null,
      });
      resetManualForm(form, { asset_class: "equity", fees: "0" });
      refreshDemoWorkspace(nextPortfolio, { tabId: "dashboard" });
      toast("Demo trade recorded.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const data = formObject(form);
    const payload = {
      ticker: data.ticker,
      side: data.side,
      quantity: numberValue(data.quantity),
      price: numberValue(data.price),
      fees: numberValue(data.fees),
      asset_class: data.asset_class || "equity",
    };
    if (data.occurred_at) payload.occurred_at = dateToIso(data.occurred_at);
    if (data.notes) payload.notes = data.notes;
    appState.portfolio = await api(`/portfolios/${appState.selectedPortfolioId}/trades`, {
      method: "POST",
      body: payload,
    });
    invalidatePerformanceHistory();
    resetManualForm(form, { asset_class: "equity", fees: "0" });
    await refreshSelected(false);
    toast("Trade recorded. Quote refresh will run automatically.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleSaveSettings(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    try {
      const data = formObject(form);
      const settings = {};
      if (data.risk_free_rate !== "") settings.risk_free_rate = numberValue(data.risk_free_rate);
      if (data.benchmark_symbols !== "") settings.benchmark_symbols = splitSymbols(data.benchmark_symbols);
      if (data.cash_target_pct !== "") settings.cash_target_pct = numberValue(data.cash_target_pct);
      const nextPortfolio = window.PORTFOLIO_DEMO.saveSettings(appState.portfolio, settings);
      if (settings.benchmark_symbols?.length) appState.selectedBenchmarks = settings.benchmark_symbols.filter((symbol) => MAJOR_INDEXES.some((item) => item.symbol === symbol));
      refreshDemoWorkspace(nextPortfolio, { tabId: "entry" });
      toast("Demo settings updated.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const data = formObject(form);
    const payload = {};
    if (data.risk_free_rate !== "") payload.risk_free_rate = numberValue(data.risk_free_rate);
    if (data.benchmark_symbols !== "") payload.benchmark_symbols = splitSymbols(data.benchmark_symbols);
    if (data.cash_target_pct !== "") payload.cash_target_pct = numberValue(data.cash_target_pct);
    const settings = await api(`/portfolios/${appState.selectedPortfolioId}/settings`, {
      method: "PATCH",
      body: payload,
    });
    appState.portfolio.settings = settings;
    await refreshSelected(true);
    toast("Settings saved.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleCsvUpload(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    toast("CSV import is disabled in the demo. Sign in to import a real portfolio.", true);
    return;
  }
  try {
    const resultBox = $("#csv-import-result");
    if (resultBox) resultBox.textContent = "Reading brokerage export...";
    const data = new FormData(form);
    const result = await api(`/api/v1/portfolios/${appState.selectedPortfolioId}/upload-csv`, {
      method: "POST",
      body: data,
    });
    resetManualForm(form);
    await refreshSelected(false);
    const source = String(result.detected_format || "generic").replace(/^./, (letter) => letter.toUpperCase());
    const warningText = (result.warnings || []).join(" ");
    if (resultBox) {
      resultBox.innerHTML = `<strong>${escapeHtml(source)} format detected.</strong> Imported ${result.imported_positions} position${result.imported_positions === 1 ? "" : "s"} from ${result.rows_read || 0} row${result.rows_read === 1 ? "" : "s"}.${warningText ? `<span>${escapeHtml(warningText)}</span>` : ""}`;
    }
    toast(`Imported ${result.imported_positions} ${source} position${result.imported_positions === 1 ? "" : "s"}. Quote refresh will run automatically.`);
  } catch (error) {
    const resultBox = $("#csv-import-result");
    if (resultBox) resultBox.textContent = error.message;
    toast(error.message, true);
  }
}

async function handleRiskAnalysis(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    appState.riskAnalysis = window.PORTFOLIO_DEMO.buildWorkspace({
      portfolio: appState.portfolio,
      selectedBenchmarks: appState.selectedBenchmarks,
      optionsInput: appState.demoOptionsInput || currentDemoOptionsInput(),
    }).riskAnalysis;
    renderRisk();
    renderDashboard();
    toast("Risk view refreshed from the demo portfolio.");
    return;
  }
  try {
    const data = formObject(form);
    const portfolioTickers = appState.portfolio.positions.map((item) => item.ticker).join(",");
    const tickers = splitSymbols(data.tickers || portfolioTickers);
    if (!tickers.length) throw new Error("Add portfolio positions before running risk analysis.");

    const manualPrices = String(data.prices || "").trim();
    let prices;
    if (manualPrices) {
      prices = parsePriceRows(manualPrices);
    } else {
      const rangeName = data.history_range || "year";
      await loadPerformanceHistoryRange(appState.selectedPortfolioId, rangeName, []);
      const history = combinedPerformanceHistory(appState.selectedPortfolioId, []);
      prices = buildRiskPriceRowsFromHistory(tickers, history, rangeName);
      if (prices.length < 3) {
        throw new Error("Market history is still being cached for risk analysis. Wait for the market-data job to finish, then run risk again.");
      }
    }

    appState.riskAnalysis = await api(`/portfolios/${appState.selectedPortfolioId}/analyze`, {
      method: "POST",
      body: {
        price_history: { tickers, prices },
        use_rmt_cleaning: data.use_rmt_cleaning === "on",
      },
    });
    renderRisk();
    renderDashboard();
    toast("Risk analysis updated.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleRiskTolerance(event) {
  event.preventDefault();
  if (!requirePortfolio()) return;
  const form = event.currentTarget;
  if (appState.demoMode) {
    try {
      const data = formObject(form);
      const riskScore = Math.round(numberValue(data.risk_tolerance_score));
      const bondSymbols = splitSymbols(data.bond_symbols || "");
      const nextPortfolio = window.PORTFOLIO_DEMO.saveSettings(appState.portfolio, {
        risk_tolerance_score: riskScore,
        bond_watchlist: bondSymbols,
      });
      $("#bond-risk-score").value = riskScore;
      refreshDemoWorkspace(nextPortfolio, { tabId: "risk" });
      toast("Demo risk profile updated.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const data = formObject(form);
    const riskScore = Math.round(numberValue(data.risk_tolerance_score));
    const bondSymbols = splitSymbols(data.bond_symbols || "");
    const settings = await api(`/portfolios/${appState.selectedPortfolioId}/settings`, {
      method: "PATCH",
      body: { risk_tolerance_score: riskScore, bond_watchlist: bondSymbols },
    });
    appState.portfolio.settings = settings;
    (appState.bondAssets?.assets || []).forEach((asset) => {
      asset.monitored = bondSymbols.includes(asset.ticker);
    });
    appState.riskTolerance = await api(`/portfolios/${appState.selectedPortfolioId}/risk-tolerance`);
    appState.riskReweight = await api(`/portfolios/${appState.selectedPortfolioId}/risk-tolerance/reweight`, {
      method: "POST",
      body: {
        risk_score: riskScore,
        bond_symbols: bondSymbols,
        max_position_weight: numberValue(data.max_position_weight),
      },
    });
    $("#bond-risk-score").value = riskScore;
    renderRiskTolerance();
    toast("Risk tolerance saved and target allocation updated.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function loadBondAssets(options = {}) {
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    renderBonds();
    renderBondStrategy();
    return;
  }
  try {
    appState.bondAssets = await api(`/portfolios/${appState.selectedPortfolioId}/bond-assets`);
    if (!appState.bondRungs.length) setRecommendedBondRungs();
    renderBonds();
    if (options.autoRefresh && (appState.bondAssets.missing_tickers || []).length) {
      maybeQueueBondRefresh();
    }
  } catch (error) {
    toast(error.message, true);
  }
}

async function maybeQueueBondRefresh() {
  const portfolioId = appState.selectedPortfolioId;
  if (!portfolioId || !(appState.bondAssets?.missing_tickers || []).length) return;
  const throttleKey = `auto_bond_refresh_${portfolioId}`;
  const lastAttempt = Number(sessionStorage.getItem(throttleKey) || 0);
  if (Date.now() - lastAttempt < 60_000) return;
  sessionStorage.setItem(throttleKey, String(Date.now()));
  const monitored = bondMonitoredTickers();
  const tickers = monitored.length ? monitored : appState.bondAssets.missing_tickers;
  try {
    const job = await api(`/portfolios/${portfolioId}/bond-assets/refresh`, {
      method: "POST",
      body: { tickers },
    });
    pollBondRefresh(job.id);
    toast(`Queued cached bond prices for ${tickers.length} asset${tickers.length === 1 ? "" : "s"}.`);
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleBondRefresh() {
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    toast("The demo bond catalog is fixed. Sign in to queue live bond market refreshes.");
    return;
  }
  const tickers = bondMonitoredTickers();
  try {
    const job = await api(`/portfolios/${appState.selectedPortfolioId}/bond-assets/refresh`, {
      method: "POST",
      body: { tickers },
    });
    pollBondRefresh(job.id);
    toast(tickers.length ? "Refreshing monitored bond prices." : "Refreshing the public bond catalog.");
  } catch (error) {
    toast(error.message, true);
  }
}

function pollBondRefresh(jobId, attempt = 0) {
  if (!jobId || attempt >= 30 || !appState.selectedPortfolioId) return;
  window.setTimeout(async () => {
    try {
      await refreshSelected(true);
      await loadBondAssets({ autoRefresh: false });
      const job = latestBackgroundJob("refresh_bond_market_data", jobId);
      if (job && ["pending", "running"].includes(job.status)) pollBondRefresh(jobId, attempt + 1);
    } catch (error) {
      toast(error.message, true);
    }
  }, 2000);
}

function handleBondWatchlistChange(event) {
  const input = event.target instanceof HTMLInputElement ? event.target.closest("input[data-bond-monitor]") : null;
  if (!input || !appState.bondAssets) return;
  const asset = appState.bondAssets.assets.find((item) => item.ticker === input.dataset.bondMonitor);
  if (asset) asset.monitored = input.checked;
}

async function handleBondSaveWatchlist() {
  if (!requirePortfolio() || !appState.bondAssets) return;
  if (appState.demoMode) {
    try {
      const bondWatchlist = bondMonitoredTickers();
      const nextPortfolio = window.PORTFOLIO_DEMO.saveSettings(appState.portfolio, { bond_watchlist: bondWatchlist });
      refreshDemoWorkspace(nextPortfolio, { tabId: "bonds" });
      $("#risk-tolerance-form").elements.bond_symbols.value = bondWatchlist.join(", ");
      toast("Demo bond watchlist updated.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const bondWatchlist = bondMonitoredTickers();
    const settings = await api(`/portfolios/${appState.selectedPortfolioId}/settings`, {
      method: "PATCH",
      body: { bond_watchlist: bondWatchlist },
    });
    appState.portfolio.settings = settings;
    $("#risk-tolerance-form").elements.bond_symbols.value = bondWatchlist.join(", ");
    toast("Bond watchlist saved.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function loadRecommendedBondStructure() {
  if (!appState.bondAssets) await loadBondAssets({ autoRefresh: false });
  setRecommendedBondRungs();
  renderBondRungRows();
}

function setRecommendedBondRungs() {
  const strategyType = $("#bond-strategy-type")?.value || "ladder";
  const riskScore = Math.max(1, Math.min(10, Math.round(finiteNumber($("#bond-risk-score")?.value, 5))));
  const savedRiskScore = appState.portfolio?.settings?.risk_tolerance_score ?? 5;
  const serverSource = strategyType === "barbell"
    ? appState.bondAssets?.recommended_barbell
    : appState.bondAssets?.recommended_ladder;
  const source = riskScore === savedRiskScore ? serverSource : riskFitBondRungs(riskScore, strategyType);
  appState.bondRungs = (source || riskFitBondRungs(riskScore, strategyType)).map((rung) => ({ ...rung }));
}

function handleAddBondRung() {
  if ($$("#bond-rung-rows tr").length) appState.bondRungs = bondRungsFromForm();
  const last = appState.bondRungs.at(-1);
  const years = Math.min(50, finiteNumber(last?.years_to_maturity, 0) + 1 || 1);
  appState.bondRungs.push({
    label: `${Number(years).toFixed(Number.isInteger(years) ? 0 : 1)}-year rung`,
    years_to_maturity: years,
    coupon_rate: 0.04,
    yield_to_maturity: 0.04,
    market_price_pct: 100,
    face_value: 1000,
    allocation_weight: 0,
    payments_per_year: 2,
  });
  renderBondRungRows();
}

function handleRemoveBondRung(event) {
  const target = event.target instanceof Element ? event.target.closest("button[data-bond-rung-remove]") : null;
  if (!target) return;
  const index = Number(target.dataset.bondRungRemove);
  if (!Number.isInteger(index)) return;
  appState.bondRungs = bondRungsFromForm();
  appState.bondRungs.splice(index, 1);
  if (!appState.bondRungs.length) handleAddBondRung();
  else renderBondRungRows();
}

async function handleBondStrategy(event) {
  event.preventDefault();
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    appState.bondStrategy = window.PORTFOLIO_DEMO.buildBondStrategy();
    renderBondStrategy();
    toast("Demo bond strategy refreshed.");
    return;
  }
  try {
    const form = event.currentTarget;
    const data = formObject(form);
    const payload = {
      strategy_type: data.strategy_type,
      capital: numberValue(data.capital),
      risk_score: Math.round(numberValue(data.risk_score)),
      rungs: bondRungsFromForm(),
    };
    appState.bondStrategy = await api(`/portfolios/${appState.selectedPortfolioId}/bond-strategies/analyze`, {
      method: "POST",
      body: payload,
    });
    renderBondStrategy();
    toast("Bond strategy calculated.");
  } catch (error) {
    toast(error.message, true);
  }
}

function relativisticBSNumber(id, fallback) {
  const value = Number($(id)?.value);
  return Number.isFinite(value) ? value : fallback;
}

function dateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function setDefaultRelativisticBSExpiry() {
  const input = $("#relativistic-bs-expiry-date");
  if (!input) return;

  const today = new Date();
  const minDate = new Date(today);
  minDate.setDate(minDate.getDate() + 1);
  input.min = dateInputValue(minDate);

  if (!input.value) {
    const defaultExpiry = new Date(today);
    defaultExpiry.setMonth(defaultExpiry.getMonth() + 6);
    if (defaultExpiry <= minDate) defaultExpiry.setTime(minDate.getTime());
    input.value = dateInputValue(defaultExpiry);
  }
}

function relativisticBSQuery(options = {}) {
  setDefaultRelativisticBSExpiry();
  const symbol = $("#relativistic-bs-symbol").value.trim();
  const expiryDate = $("#relativistic-bs-expiry-date").value;
  const strikeDetail = $("#relativistic-bs-strike-detail")?.value || "auto";
  const nStrikes = strikeDetail === "dense" ? 200 : strikeDetail === "listed" ? 41 : 101;
  const params = new URLSearchParams({
    expiry_date: expiryDate,
    rate: String(relativisticBSNumber("#relativistic-bs-rate", 0.05)),
    sigma: String(relativisticBSNumber("#relativistic-bs-sigma", 0.15)),
    c_m: String(relativisticBSNumber("#relativistic-bs-cm", 2.5)),
    option_type: $("#relativistic-bs-option-type").value,
    use_market_chain: $("#relativistic-bs-live-chain")?.checked ? "true" : "false",
    strike_min_pct: String(relativisticBSNumber("#relativistic-bs-strike-min-pct", 0.7)),
    strike_max_pct: String(relativisticBSNumber("#relativistic-bs-strike-max-pct", 1.3)),
    n_strikes: String(nStrikes),
    surface_expiries: String(Math.round(relativisticBSNumber("#relativistic-bs-surface-expiries", 4))),
    history_period: $("#relativistic-bs-history-period")?.value || "1y",
  });
  if (options.force) params.set("force_market_chain", "true");
  if (symbol) params.set("symbol", symbol.toUpperCase());
  return params.toString();
}

async function handleRelativisticBSRefresh(event) {
  event.preventDefault();
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    try {
      appState.demoOptionsInput = currentDemoOptionsInput();
      appState.relativisticBs = window.PORTFOLIO_DEMO.runOptionsScenario(appState.demoOptionsInput, appState.portfolio, appState.marketData.quotes || []);
      appState.relativisticBsHistory = window.PORTFOLIO_DEMO.buildOptionsHistory(appState.relativisticBs);
      renderRelativisticBS();
      persistDemoSession();
      toast("Demo options suite updated.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const query = relativisticBSQuery();
    appState.relativisticBs = await api(`/portfolios/${appState.selectedPortfolioId}/relativistic-bs?${query}`);
    renderRelativisticBS();
    await loadRelativisticBSHistory();
    toast("Options suite updated.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleRelativisticBSForceRefresh() {
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    appState.demoOptionsInput = currentDemoOptionsInput();
    appState.relativisticBs = window.PORTFOLIO_DEMO.runOptionsScenario(appState.demoOptionsInput, appState.portfolio, appState.marketData.quotes || []);
    appState.relativisticBsHistory = window.PORTFOLIO_DEMO.buildOptionsHistory(appState.relativisticBs);
    renderRelativisticBS();
    persistDemoSession();
    toast("Demo chain refreshed locally. Live cache refreshes are available after sign-in.");
    return;
  }
  try {
    const query = relativisticBSQuery({ force: true });
    appState.relativisticBs = await api(`/portfolios/${appState.selectedPortfolioId}/relativistic-bs?${query}`);
    renderRelativisticBS();
    await loadRelativisticBSHistory();
    toast("Fresh live option-chain snapshot captured.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function loadRelativisticBSHistory() {
  if (appState.demoMode) {
    renderRelativisticBSHistory();
    return;
  }
  const payload = appState.relativisticBs;
  if (!payload || !appState.selectedPortfolioId) {
    appState.relativisticBsHistory = null;
    renderRelativisticBSHistory();
    return;
  }
  const params = new URLSearchParams({
    symbol: payload.symbol,
    expiry_date: payload.actual_expiry_date || payload.parameters?.expiry_date || "",
    resolution: $("#relativistic-bs-history-resolution")?.value || "auto",
    lookback_days: $("#relativistic-bs-history-lookback")?.value || "365",
    rate: String(payload.parameters?.rate ?? 0.05),
    sigma: String(payload.parameters?.sigma ?? 0.15),
    c_m: String(payload.parameters?.c_m ?? 2.5),
  });
  if (!params.get("expiry_date")) params.delete("expiry_date");
  try {
    appState.relativisticBsHistory = await api(`/portfolios/${appState.selectedPortfolioId}/relativistic-bs/history?${params}`);
  } catch (error) {
    appState.relativisticBsHistory = null;
    toast(error.message, true);
  }
  renderRelativisticBSHistory();
}

function handleUseVolatilityEstimate(event) {
  const target = event.target instanceof Element ? event.target : null;
  const button = target ? target.closest("button[data-volatility-value]") : null;
  if (!button) return;
  const value = Number(button.dataset.volatilityValue);
  if (!Number.isFinite(value) || value <= 0) return;
  const input = $("#relativistic-bs-sigma");
  if (input) input.value = value.toFixed(4);
  toast(`Baseline volatility set to ${pct(value)}. Run the suite again to reprice.`);
}

function handleRelbsSurfaceFilterChange() {
  if (appState.relativisticBs) renderRelbsIVSurface($("#relativistic-bs-iv-surface-chart"), appState.relativisticBs);
}

function resetRelbsSurfaceFilters() {
  $("#relativistic-bs-surface-expiry-min").value = "";
  $("#relativistic-bs-surface-expiry-max").value = "";
  $("#relativistic-bs-surface-moneyness-min").value = "0.75";
  $("#relativistic-bs-surface-moneyness-max").value = "1.25";
  handleRelbsSurfaceFilterChange();
}

function handleStrategyLabUniverseChange() {
  const form = $("#strategy-lab-form");
  if (!form) return;
  const universe = form.elements.universe.value;
  const tickers = strategyLabDefaultTickers(universe);
  if (universe !== "custom") form.elements.tickers.value = tickers.join(", ");
  if (!form.elements.options_symbol.value || !tickers.includes(form.elements.options_symbol.value.trim().toUpperCase())) {
    form.elements.options_symbol.value = strategyLabOptionSymbol(formObject(form), tickers);
  }
  renderStrategyLab();
}

async function handleStrategyLab(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  try {
    const data = formObject(form);
    const tickers = strategyLabRequestedTickers(data);
    if (!tickers.length) throw new Error("Choose at least one ticker for the strategy lab.");
    if (tickers.length > 8) throw new Error("Use eight or fewer symbols in the lightweight strategy lab.");

    const rangeName = data.strategy_range || "year";
    const historySymbols = Array.from(new Set([...selectedBenchmarks(appState.portfolio), ...tickers]));
    await loadPerformanceHistoryRange(appState.selectedPortfolioId, rangeName, historySymbols);
    const history = combinedPerformanceHistory(appState.selectedPortfolioId, historySymbols) || activePerformanceHistory();
    appState.strategyLab = buildStrategyLabResult(data, { tickers, rangeName, history });
    renderStrategyLab();
    const status = appState.strategyLab.points.length >= 2 ? "Strategy scenario updated." : "Strategy lab is waiting for cached history.";
    toast(status, appState.strategyLab.points.length < 2);
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleHeatmap(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    appState.heatmap = window.PORTFOLIO_DEMO.buildHeatmap(appState.portfolio, appState.marketData.quotes || []);
    renderHeatmap();
    toast("Demo heatmap rebuilt.");
    return;
  }
  const data = formObject(form);
  try {
    appState.marketData = await api(`/portfolios/${appState.selectedPortfolioId}/market-data`).catch(() => appState.marketData);
    appState.heatmap = await api(`/portfolios/${appState.selectedPortfolioId}/heatmap`, {
      method: "POST",
      body: { group_by: data.group_by || "sector" },
    });
    renderQuoteSnapshots();
    renderHeatmap();
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleOptimization(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    try {
      const data = formObject(form);
      appState.optimization = window.PORTFOLIO_DEMO.buildOptimization(
        appState.portfolio,
        data.objective,
        numberValue(data.min_weight),
        numberValue(data.max_weight),
        data.risk_free_rate === "" ? appState.portfolio.settings.risk_free_rate : numberValue(data.risk_free_rate),
      );
      renderOptimization();
      toast("Demo optimization updated.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const data = formObject(form);
    $("#optimization-results").innerHTML = `<div class="activity-item"><strong>Running ${escapeHtml(data.objective)}</strong><span>Calculating target weights.</span></div>`;
    appState.optimization = await api(`/api/v1/portfolios/${appState.selectedPortfolioId}/optimize`, {
      method: "POST",
      body: {
        objective: data.objective,
        min_weight: numberValue(data.min_weight),
        max_weight: numberValue(data.max_weight),
        risk_free_rate: data.risk_free_rate === "" ? appState.portfolio.settings.risk_free_rate : numberValue(data.risk_free_rate),
      },
    });
    renderOptimization();
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleSimpleImpact(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    try {
      const data = formObject(form);
      appState.simpleImpact = window.PORTFOLIO_DEMO.buildSimpleImpact(appState.portfolio, {
        symbol: data.symbol,
        side: data.side,
        quantity: numberValue(data.quantity),
        price: numberValue(data.price),
        estimated_slippage_bps: numberValue(data.estimated_slippage_bps),
        fee_rate_bps: numberValue(data.fee_rate_bps),
      });
      renderSimulation();
      toast("Demo trade impact estimated.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const data = formObject(form);
    appState.simpleImpact = await api(`/api/v1/portfolios/${appState.selectedPortfolioId}/simulate-trade-impact`, {
      method: "POST",
      body: {
        symbol: data.symbol,
        side: data.side,
        quantity: numberValue(data.quantity),
        price: numberValue(data.price),
        estimated_slippage_bps: numberValue(data.estimated_slippage_bps),
        fee_rate_bps: numberValue(data.fee_rate_bps),
      },
    });
    renderSimulation();
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleRiskSimulation(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    try {
      const data = formObject(form);
      const trade = { ticker: data.ticker, side: data.side };
      if (data.quantity) trade.quantity = numberValue(data.quantity);
      if (data.notional) trade.notional = numberValue(data.notional);
      const covariance = data.covariance ? JSON.parse(data.covariance) : defaultCovariance(appState.portfolio);
      appState.riskSimulation = window.PORTFOLIO_DEMO.buildRiskSimulation(appState.portfolio, trade, covariance);
      renderSimulation();
      toast("Demo risk simulation updated.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  try {
    const data = formObject(form);
    const trade = { ticker: data.ticker, side: data.side };
    if (data.quantity) trade.quantity = numberValue(data.quantity);
    if (data.notional) trade.notional = numberValue(data.notional);
    const covariance = data.covariance ? JSON.parse(data.covariance) : defaultCovariance(appState.portfolio);
    appState.riskSimulation = await api(`/portfolios/${appState.selectedPortfolioId}/simulate-trade`, {
      method: "POST",
      body: { trades: [trade], covariance },
    });
    renderSimulation();
  } catch (error) {
    toast(error.message, true);
  }
}

async function handleMarketRefresh() {
  if (!requirePortfolio()) return;
  if (appState.demoMode) {
    toast("Live market refresh is disabled in the demo. Sign in to use the cached quote worker.");
    return;
  }
  try {
    const job = await api(`/portfolios/${appState.selectedPortfolioId}/market-data/refresh`, { method: "POST" });
    invalidatePerformanceHistory();
    await refreshSelected(false);
    pollMarketRefresh(job.id);
    toast(`${job.status === "completed" ? "Refreshed" : "Queued"} ${job.job_type}.`);
  } catch (error) {
    toast(error.message, true);
  }
}

async function maybeQueueMissingMarketData() {
  if (appState.demoMode) return;
  const portfolioId = appState.selectedPortfolioId;
  const missing = appState.marketData?.missing_tickers || [];
  if (!portfolioId || missing.length === 0 || hasActiveMarketRefresh()) return;

  const throttleKey = `auto_quote_refresh_${portfolioId}`;
  const lastAttempt = Number(sessionStorage.getItem(throttleKey) || 0);
  if (Date.now() - lastAttempt < 60_000) return;
  sessionStorage.setItem(throttleKey, String(Date.now()));

  try {
    const job = await api(`/portfolios/${portfolioId}/market-data/refresh`, { method: "POST" });
    pollMarketRefresh(job.id);
    toast(`Queued quote refresh for ${missing.length} missing ticker${missing.length === 1 ? "" : "s"}.`);
  } catch (error) {
    toast(error.message, true);
  }
}

function hasActiveMarketRefresh() {
  const jobs = appState.portfolio?.background_jobs || [];
  return jobs.some((job) => job.job_type === "refresh_market_data" && ["pending", "running"].includes(job.status));
}

async function maybeLoadPerformanceHistory() {
  if (appState.demoMode) return;
  const portfolio = appState.portfolio;
  if (!portfolio?.portfolio_id && !appState.selectedPortfolioId) return;
  const portfolioId = appState.selectedPortfolioId || portfolio.portfolio_id;
  const benchmarks = selectedBenchmarks(portfolio);
  const zoomSpan = currentPerformanceZoomSpan();
  performanceHistoryRangesForZoom(appState.performanceRange, zoomSpan).forEach((rangeName) => {
    loadPerformanceHistoryRange(portfolioId, rangeName, benchmarks);
  });
}

async function loadPerformanceHistoryRange(portfolioId, rangeName, benchmarks) {
  if (appState.demoMode) {
    const cacheKey = performanceHistoryCacheKey(portfolioId, rangeName, benchmarks);
    if (!appState.performanceHistory[cacheKey]) {
      const workspace = window.PORTFOLIO_DEMO.buildWorkspace({
        portfolio: appState.portfolio,
        selectedBenchmarks: benchmarks?.length ? benchmarks : appState.selectedBenchmarks,
        optionsInput: appState.demoOptionsInput || currentDemoOptionsInput(),
      });
      Object.assign(appState.performanceHistory, workspace.performanceHistory || {});
    }
    return appState.performanceHistory[cacheKey] || null;
  }
  const cacheKey = performanceHistoryCacheKey(portfolioId, rangeName, benchmarks);
  if (appState.performanceHistory[cacheKey]) return appState.performanceHistory[cacheKey];
  if (appState.performanceHistoryPending[cacheKey]) return appState.performanceHistoryPending[cacheKey];

  const request = (async () => {
    try {
      const query = new URLSearchParams({
        range_name: rangeName,
        benchmark_symbols: benchmarks.join(","),
      });
      const payload = await api(`/portfolios/${portfolioId}/performance-history?${query}`);
      const normalized = normalizePerformanceHistoryPayload(payload);
      appState.performanceHistory[cacheKey] = normalized;
      renderDashboard();
      if (payload.queued_job && ["pending", "running"].includes(payload.queued_job.status)) {
        pollPerformanceHistoryRefresh(payload.queued_job.id);
      }
      return normalized;
    } catch (error) {
      return null;
    } finally {
      delete appState.performanceHistoryPending[cacheKey];
    }
  })();

  appState.performanceHistoryPending[cacheKey] = request;
  return request;
}

function performanceHistoryCacheKey(portfolioId, rangeName, benchmarks) {
  return `${portfolioId}:${rangeName}:${(benchmarks || []).join(",")}`;
}

function invalidatePerformanceHistory(portfolioId = appState.selectedPortfolioId) {
  if (!portfolioId) {
    appState.performanceHistory = {};
    appState.performanceHistoryPending = {};
  } else {
    const prefix = `${portfolioId}:`;
    Object.keys(appState.performanceHistory).forEach((key) => {
      if (key.startsWith(prefix)) delete appState.performanceHistory[key];
    });
    Object.keys(appState.performanceHistoryPending).forEach((key) => {
      if (key.startsWith(prefix)) delete appState.performanceHistoryPending[key];
    });
  }
  appState.performanceZoom = null;
}

function activePerformanceHistory() {
  const portfolio = appState.portfolio;
  if (!portfolio) return null;
  const portfolioId = appState.selectedPortfolioId || portfolio.portfolio_id;
  return combinedPerformanceHistory(portfolioId, selectedBenchmarks(portfolio));
}

function combinedPerformanceHistory(portfolioId, benchmarks = []) {
  if (!portfolioId) return null;
  const suffix = `:${(benchmarks || []).join(",")}`;
  const prefix = `${portfolioId}:`;
  const seriesByTicker = new Map();
  const portfolioPoints = new Map();
  let coverage = null;
  Object.entries(appState.performanceHistory).forEach(([key, payload]) => {
    if (!key.startsWith(prefix) || !key.endsWith(suffix)) return;
    (payload.portfolio_series || []).forEach((point) => portfolioPoints.set(point.date.getTime(), point));
    if (payload.coverage?.effective_start && (!coverage?.effective_start || new Date(payload.coverage.effective_start) > new Date(coverage.effective_start))) {
      coverage = payload.coverage;
    } else if (!coverage && payload.coverage) {
      coverage = payload.coverage;
    }
    (payload.series || []).forEach((line) => {
      const ticker = String(line.ticker || "").toUpperCase();
      if (!ticker) return;
      const existing = seriesByTicker.get(ticker) || { ...line, points: [] };
      existing.points.push(...(line.points || []));
      seriesByTicker.set(ticker, existing);
    });
  });
  if (!seriesByTicker.size && !portfolioPoints.size) return null;
  return {
    series: Array.from(seriesByTicker.values()).map((line) => {
      const byTime = new Map();
      line.points.forEach((point) => byTime.set(point.date.getTime(), point));
      return { ...line, points: Array.from(byTime.values()).sort((a, b) => a.date - b.date) };
    }),
    portfolio_series: Array.from(portfolioPoints.values()).sort((a, b) => a.date - b.date),
    coverage,
  };
}

function performanceHistoryRangesForZoom(rangeName, zoomSpan = null) {
  const primary = PERFORMANCE_RANGES[rangeName] ? rangeName : "max";
  const resolution = effectivePerformanceResolution(primary, zoomSpan);
  const ranges = new Set([primary, "year"]);
  if (["15m", "1h"].includes(resolution.effective)) ranges.add("week");
  if (resolution.effective === "5m") ranges.add("day");
  return Array.from(ranges);
}

function currentPerformanceZoomSpan() {
  const zoom = appState.performanceZoom;
  return zoom && zoom.rangeName === appState.performanceRange ? zoom.end - zoom.start : null;
}

function effectivePerformanceResolution(rangeName, zoomSpan = null) {
  const requested = PERFORMANCE_RESOLUTIONS[appState.performanceResolution] ? appState.performanceResolution : "auto";
  const range = performanceWindow(rangeName);
  const spanMs = Math.max(zoomSpan || (range.end - range.start), 1);
  const finest = finestAllowedPerformanceResolution(spanMs);
  const automatic = automaticPerformanceResolution(spanMs);
  const desired = requested === "auto" ? automatic : requested;
  const effective = coarserPerformanceResolution(desired, finest);
  return {
    requested,
    effective,
    limited: requested !== "auto" && requested !== effective,
    label: PERFORMANCE_RESOLUTIONS[effective].label,
    bucketMs: PERFORMANCE_RESOLUTIONS[effective].bucketMs,
    spanMs,
  };
}

function finestAllowedPerformanceResolution(spanMs) {
  const day = 24 * 60 * 60 * 1000;
  if (spanMs <= 2 * day) return "5m";
  if (spanMs <= 60 * day) return "15m";
  if (spanMs <= 400 * day) return "1d";
  if (spanMs <= 6 * 365 * day) return "1wk";
  return "1mo";
}

function automaticPerformanceResolution(spanMs) {
  const day = 24 * 60 * 60 * 1000;
  if (spanMs <= 2 * day) return "5m";
  if (spanMs <= 14 * day) return "15m";
  if (spanMs <= 60 * day) return "1h";
  if (spanMs <= 400 * day) return "1d";
  if (spanMs <= 6 * 365 * day) return "1wk";
  return "1mo";
}

function coarserPerformanceResolution(requested, finest) {
  const requestedIndex = PERFORMANCE_RESOLUTION_ORDER.indexOf(requested);
  const finestIndex = PERFORMANCE_RESOLUTION_ORDER.indexOf(finest);
  if (requestedIndex < 0) return finest;
  return PERFORMANCE_RESOLUTION_ORDER[Math.max(requestedIndex, finestIndex)];
}

function normalizePerformanceHistoryPayload(payload) {
  return {
    ...payload,
    portfolio_series: (payload.portfolio_series || []).map((point) => ({ date: new Date(point.as_of), value: Number(point.value) })).filter((point) => Number.isFinite(point.date.getTime()) && Number.isFinite(point.value)),
    series: (payload.series || []).map((line) => ({
      ...line,
      points: (line.points || []).map((point) => ({ date: new Date(point.as_of), close: Number(point.close) })).filter((point) => Number.isFinite(point.date.getTime()) && Number.isFinite(point.close)),
    })),
  };
}

function pollPerformanceHistoryRefresh(jobId, attempt = 0) {
  if (!jobId || attempt >= 60 || !appState.selectedPortfolioId) return;
  window.setTimeout(async () => {
    try {
      await refreshSelected(true);
      const job = latestBackgroundJob("refresh_market_history", jobId);
      if (job && ["pending", "running"].includes(job.status)) {
        pollPerformanceHistoryRefresh(jobId, attempt + 1);
        return;
      }
      appState.performanceHistory = {};
      appState.performanceHistoryPending = {};
      maybeLoadPerformanceHistory();
    } catch (error) {
      toast(error.message, true);
    }
  }, 3000);
}

async function refreshSelected(keepMarket) {
  if (appState.demoMode) {
    refreshDemoWorkspace(appState.portfolio);
    return;
  }
  const id = appState.selectedPortfolioId;
  if (!id) return;
  const previousQuoteKey = quoteStateKey(appState.marketData);
  appState.portfolio = await api(`/portfolios/${id}`);
  const portfolioPayload = await api("/me/portfolios").catch(() => ({ portfolios: appState.portfolios }));
  appState.portfolios = portfolioPayload.portfolios || appState.portfolios;
  if (!keepMarket) {
    appState.marketData = await api(`/portfolios/${id}/market-data`).catch(() => ({ quotes: [], missing_tickers: [] }));
    if (quoteStateKey(appState.marketData) !== previousQuoteKey) appState.heatmap = null;
  }
  renderPortfolioList();
  renderAll();
  refreshRuntime();
}

async function refreshRuntime({ retries = 0 } = {}) {
  let lastError = null;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    for (const basePath of ["/runtime", "/api/v1/runtime"]) {
      try {
        appState.runtime = await api(`${basePath}?t=${Date.now()}`, { auth: false });
        renderRuntime();
        return appState.runtime;
      } catch (error) {
        lastError = error;
      }
    }
    appState.runtime = null;
    renderRuntime(lastError);
    if (attempt < retries) await delay(750);
  }
  return null;
}

function renderRuntime(error = null) {
  const pill = $("#runtime-pill");
  if (!pill) return;
  const runtime = appState.runtime;
  if (!runtime) {
    const detail = error?.message ? ` (${error.message})` : "";
    pill.textContent = `UI ${CLIENT_BUILD_ID} - API unknown${detail}`;
    pill.className = "pill muted";
    return;
  }
  const database = runtime.database || {};
  const redis = runtime.redis || {};
  const users = database.users ?? "?";
  const portfolios = database.portfolios ?? "?";
  const quotes = database.market_quotes ?? "?";
  pill.textContent = `UI ${CLIENT_BUILD_ID} | API ${runtime.build_id} | DB ${users}u/${portfolios}p/${quotes}q | Redis ${redis.ok ? "ok" : "off"}`;
  pill.className = redis.ok ? "pill" : "pill muted";
}

function renderAuthState() {
  const realAuthed = Boolean(appState.user && !appState.demoMode);
  const authed = realAuthed || appState.demoMode;
  const quickCreateSection = $("#create-portfolio-form")?.closest(".sidebar-section");
  document.body.dataset.view = authed ? "workspace" : "landing";
  $("#auth-screen").hidden = authed;
  $("#app-shell").hidden = !authed;
  $("#auth-screen").setAttribute("aria-hidden", String(authed));
  $("#app-shell").setAttribute("aria-hidden", String(!authed));
  $("#logout-button").hidden = !realAuthed;
  $("#demo-tour-button").hidden = !appState.demoMode;
  $("#demo-exit-button").hidden = !appState.demoMode;
  $("#demo-banner").hidden = !appState.demoMode;
  if (quickCreateSection) quickCreateSection.hidden = appState.demoMode || !appState.portfolios.length;
  $("#user-pill").textContent = authed ? (appState.demoMode ? "Demo session" : appState.user.email) : "Signed out";
  $("#user-pill").className = authed ? "pill" : "pill muted";
  $("#api-status").textContent = authed ? (appState.apiAvailable ? "Service available" : "Service unavailable") : "Private portfolio workspace";
  syncResponsiveWorkspaceChrome();
  if (authed) renderAccount();
}

function renderAll() {
  const hasPortfolio = Boolean(appState.portfolio);
  $("#no-portfolio").hidden = hasPortfolio;
  $("#pages").hidden = !hasPortfolio;
  renderPortfolioList();
  if (!hasPortfolio) return;
  fillPortfolioForms();
  renderDashboard();
  renderEntry();
  renderRisk();
  renderRiskTolerance();
  renderBonds();
  renderRelativisticBS();
  renderStrategyLab();
  renderHeatmap();
  renderQuoteSnapshots();
  renderOptimization();
  renderSimulation();
  renderMarket();
  renderAccount();
  applyGraphVisibility();
  normalizeNumericInputs();
}

function renderPortfolioList() {
  const list = $("#portfolio-list");
  if (!appState.portfolios.length) {
    list.innerHTML = `<div class="activity-item"><strong>No portfolios yet</strong><span>Use the guided setup in the main workspace to import a file or add your first holdings.</span></div>`;
    return;
  }
  list.innerHTML = appState.portfolios.map((portfolio) => `
    <button class="portfolio-item ${portfolio.id === appState.selectedPortfolioId ? "active" : ""}" data-portfolio-id="${escapeHtml(portfolio.id)}" type="button">
      <strong>${escapeHtml(portfolio.name)}</strong>
      <span>${money(portfolio.total_equity)} total equity</span>
      <span>${portfolio.positions_count} positions</span>
    </button>`).join("");
}

function renderDashboard() {
  const portfolio = appState.portfolio;
  if (!portfolio) return;
  const analytics = estimateAnalytics(portfolio);
  $("#portfolio-title").textContent = portfolio.name;
  $("#portfolio-subtitle").textContent = `${portfolio.base_currency} account - ${portfolio.positions.length} positions`;
  $("#metric-grid").innerHTML = [
    metricCard("Total Equity", money(portfolio.totals.total_equity)),
    metricCard("Cost Basis", money(portfolio.totals.cost_basis)),
    metricCard("Unrealized P/L", signedMoney(portfolio.totals.unrealized_gain_loss)),
    metricCard("Return vs Cost", signedPct(portfolio.totals.unrealized_gain_loss_pct)),
    metricCard("Beta", fixed(analytics.beta, 2)),
    metricCard("Sharpe", fixed(analytics.sharpe, 2)),
    metricCard("Volatility", pct(analytics.volatility)),
    metricCard("Idle Cash", money(portfolio.performance.idle_cash)),
  ].join("");
  $("#analytics-note").textContent = analytics.note;

  renderPerformanceControls(portfolio);
  renderTableHtml($("#holdings-table"), ["Ticker", "Qty", "Avg Cost", "Price", "Cost Basis", "Value", "Weight", "Return", ""], portfolio.positions.map((position) => [
    escapeHtml(position.ticker),
    fixed(position.quantity, 4),
    money(position.average_cost),
    money(position.current_price),
    money(position.cost_basis),
    money(position.market_value),
    pct(position.market_value / Math.max(portfolio.totals.total_equity, 1)),
    `${signedMoney(position.unrealized_gain_loss)} (${signedPct(position.unrealized_gain_loss_pct)})`,
    `<button class="danger-link" type="button" data-delete-kind="position" data-delete-id="${escapeHtml(position.ticker)}" data-delete-label="${escapeHtml(position.ticker)}">Delete</button>`,
  ]));
  renderBars($("#allocation-bars"), portfolio.charts.allocation_by_ticker.map((point) => ({ label: point.label, value: point.value, display: pct(point.value) })));
  renderActivity();
  const performanceSeries = buildPerformanceSeries(portfolio);
  renderPerformanceOverview(performanceSeries);
  drawPerformanceChart($("#performance-chart"), performanceSeries);
  maybeLoadPerformanceHistory();
}

function renderPerformanceControls(portfolio) {
  const selected = selectedBenchmarks(portfolio);
  $("#benchmark-chips").innerHTML = selected.map((symbol) => `<span class="chip">${escapeHtml(benchmarkLabel(symbol))}</span>`).join("") || `<span class="pill muted">No benchmarks</span>`;
  $$("#performance-range button").forEach((button) => {
    button.classList.toggle("active", button.dataset.range === appState.performanceRange);
  });
  const resolution = effectivePerformanceResolution(appState.performanceRange, currentPerformanceZoomSpan());
  const resolutionSelect = $("#performance-resolution");
  resolutionSelect.value = appState.performanceResolution;
  Array.from(resolutionSelect.options).forEach((option) => {
    option.disabled = option.value !== "auto" && coarserPerformanceResolution(option.value, finestAllowedPerformanceResolution(resolution.spanMs)) !== option.value;
  });
  $("#performance-resolution-note").textContent = resolution.limited
    ? `${PERFORMANCE_RESOLUTIONS[resolution.requested].label} data is too dense for this visible time span. The chart is using ${resolution.label.toLowerCase()} points to keep market-data requests bounded.`
    : `Chart resolution: ${resolution.label}. Intraday views compress overnight and weekend market closures.`;
  $("#benchmark-selector").innerHTML = MAJOR_INDEXES.map((index) => {
    const checked = selected.includes(index.symbol);
    return `<label class="benchmark-option ${checked ? "active" : ""}"><input type="checkbox" value="${escapeHtml(index.symbol)}" ${checked ? "checked" : ""} aria-label="${escapeHtml(index.label)}"><span class="benchmark-check" aria-hidden="true"></span><span class="benchmark-name">${escapeHtml(index.label)}</span></label>`;
  }).join("");
}

function renderEntry() {
  const portfolio = appState.portfolio;
  if (!portfolio) return;
  renderTableHtml($("#lots-table"), ["Ticker", "Open Qty", "Cost", "Price", "Value", "Date", ""], portfolio.lots.map((lot) => [
    escapeHtml(lot.ticker),
    fixed(lot.remaining_quantity, 4),
    money(lot.cost_basis),
    money(lot.current_price),
    money(lot.market_value),
    shortDate(lot.purchased_at),
    `<button class="danger-link" type="button" data-delete-kind="lot" data-delete-id="${escapeHtml(lot.id)}" data-delete-label="${escapeHtml(lot.ticker)} lot">Delete</button>`,
  ]));
  renderTable($("#trade-table"), ["Date", "Ticker", "Side", "Qty", "Price", "Cash", "Realized"], portfolio.trade_history.map((trade) => [
    shortDate(trade.occurred_at),
    trade.ticker,
    trade.side,
    fixed(trade.quantity, 4),
    money(trade.price),
    signedMoney(trade.cash_delta),
    trade.realized_gain_loss == null ? "-" : signedMoney(trade.realized_gain_loss),
  ]));
}

function renderRelativisticBS() {
  if (!appState.portfolio) return;
  const summary = $("#relativistic-bs-summary");
  const warnings = $("#relativistic-bs-warnings");
  const diagnostics = $("#relativistic-bs-diagnostics");
  const surface = $("#relativistic-bs-surface");
  const chart = $("#relativistic-bs-chart");
  const volGuide = $("#relativistic-bs-vol-guide");
  const smileChart = $("#relativistic-bs-smile-chart");
  const volumeChart = $("#relativistic-bs-volume-chart");
  const gammaChart = $("#relativistic-bs-gamma-chart");
  const ivSurfaceChart = $("#relativistic-bs-iv-surface-chart");
  if (!summary || !warnings || !diagnostics || !surface || !chart || !volGuide || !smileChart || !volumeChart || !gammaChart || !ivSurfaceChart) return;

  if (!appState.relativisticBs) {
    summary.innerHTML = `<div class="activity-item"><strong>No model run</strong><span>Run the suite to price a holding with the backend spot price.</span></div>`;
    warnings.innerHTML = "";
    diagnostics.innerHTML = "";
    surface.innerHTML = "";
    volGuide.innerHTML = `<div class="activity-item"><strong>No volatility guide</strong><span>Run with live chains enabled to compare market IV and realized volatility.</span></div>`;
    chart.innerHTML = `<div class="activity-item"><strong>No chain</strong><span>Run the suite to draw call and put curves.</span></div>`;
    smileChart.innerHTML = `<div class="activity-item"><strong>No smile</strong><span>Listed IV will appear here after a live chain fetch.</span></div>`;
    volumeChart.innerHTML = `<div class="activity-item"><strong>No volume</strong><span>Listed option volume will appear here after a live chain fetch.</span></div>`;
    gammaChart.innerHTML = `<div class="activity-item"><strong>No gamma exposure</strong><span>Open-interest gamma exposure will appear here after a live chain fetch.</span></div>`;
    ivSurfaceChart.innerHTML = `<div class="activity-item"><strong>No IV surface</strong><span>Multiple listed expiries will appear here after a live suite fetch.</span></div>`;
    renderRelativisticBSHistory();
    return;
  }

  const payload = appState.relativisticBs;
  const chain = payload.option_chain || [];
  summary.innerHTML = payload.summary.map((item) => metricCard(item.label, relbsMetricValue(item))).join("");
  warnings.innerHTML = (payload.warnings || []).map((warning) => (
    `<div class="activity-item"><strong>Note</strong><span>${escapeHtml(warning)}</span></div>`
  )).join("");

  const closest = chain.reduce((best, row) => {
    if (!best) return row;
    return Math.abs(row.strike - payload.spot) < Math.abs(best.strike - payload.spot) ? row : best;
  }, null);
  diagnostics.innerHTML = closest ? [
    resultItem("Symbol", payload.symbol),
    resultItem("Chain Source", relbsChainSource(payload.chain_source)),
    resultItem("Requested Expiry", payload.parameters?.expiry_date || "Year fraction"),
    resultItem("Actual Expiry", payload.actual_expiry_date || payload.parameters?.expiry_date || "Generated"),
    resultItem("Time to Expiry", `${fixed(payload.parameters?.tau, 4)} years`),
    resultItem("Backend Spot", money(payload.spot)),
    resultItem("Nearest Strike", money(closest.strike)),
    resultItem("Call Rel - BS", signedMoney(closest.call.price_correction)),
    resultItem("Put Rel - BS", signedMoney(closest.put.price_correction)),
  ].join("") : "";

  renderRelbsVolatilityGuide(volGuide, payload);
  renderRelativisticBSChart(chart, payload);
  renderRelbsVolatilitySmile(smileChart, payload);
  renderRelbsCumulativeVolume(volumeChart, payload);
  renderRelbsGammaExposure(gammaChart, payload);
  renderRelbsIVSurface(ivSurfaceChart, payload);
  renderTableHtml(surface, [
    "Call IV",
    "Call Rel",
    "Call BS",
    "Call Mkt",
    "Strike",
    "Put Mkt",
    "Put BS",
    "Put Rel",
    "Put IV",
  ], chain.map((row) => [
    escapeHtml(relativisticBSPct(row.call.market_iv ?? row.call.bs_implied_vol_from_rel_price)),
    escapeHtml(money(row.call.relativistic_price)),
    escapeHtml(money(row.call.bs_price)),
    escapeHtml(relbsMarketPrice(row.call)),
    `<strong>${escapeHtml(money(row.strike))}</strong>`,
    relbsMarketPrice(row.put),
    money(row.put.bs_price),
    money(row.put.relativistic_price),
    relativisticBSPct(row.put.market_iv ?? row.put.bs_implied_vol_from_rel_price),
  ]), chain.map((row) => Math.abs(row.strike - payload.spot) === Math.min(...chain.map((item) => Math.abs(item.strike - payload.spot))) ? "atm-row" : ""));
  normalizeNumericInputs($("#relativistic-bs"));
  renderRelativisticBSHistory();
}

function renderStrategyLab() {
  if (!appState.portfolio) return;
  const form = $("#strategy-lab-form");
  const summary = $("#strategy-lab-summary");
  const notes = $("#strategy-lab-notes");
  const legend = $("#strategy-lab-legend");
  const status = $("#strategy-lab-status");
  const chart = $("#strategy-lab-chart");
  if (!form || !summary || !notes || !legend || !status || !chart) return;

  if (!form.elements.tickers.value) {
    form.elements.tickers.value = strategyLabDefaultTickers(form.elements.universe.value).join(", ");
  }
  if (!form.elements.options_symbol.value) {
    form.elements.options_symbol.value = strategyLabOptionSymbol(formObject(form), strategyLabDefaultTickers(form.elements.universe.value));
  }

  const result = appState.strategyLab;
  if (!result) {
    const optionSymbol = appState.relativisticBs?.symbol || "No symbol loaded";
    summary.innerHTML = [
      resultItem("Status", "Ready"),
      resultItem("Default Universe", strategyLabDefaultTickers(form.elements.universe.value).join(", ") || "No holdings"),
      resultItem("Data Source", "Cached history"),
      resultItem("Option Underlying", form.elements.options_symbol.value || optionSymbol),
      resultItem("Option Engine", "Covered calls and covered puts ready"),
    ].join("");
    notes.innerHTML = [
      `<div class="activity-item"><strong>First run</strong><span>Choose a universe and run a scenario. If history is still being cached, the lab will tell you which symbols are missing.</span></div>`,
      `<div class="activity-item"><strong>Strategy logic</strong><span>${escapeHtml(strategyLabStrategyDescription(form.elements.strategy_type.value || "buy_hold"))}</span></div>`,
      `<div class="activity-item"><strong>Overlay engine</strong><span>Covered calls keep the linked stock sleeve and cap upside above the call strike. Covered puts are modeled here as cash-secured short puts on the linked underlying sleeve.</span></div>`,
      `<div class="activity-item"><strong>Isolation</strong><span>Scenario output stays local to this tab and does not change holdings, lots, cash, saved option chains, or optimization inputs.</span></div>`,
    ].join("");
    legend.innerHTML = "";
    status.textContent = "Ready";
    status.className = "pill muted";
    drawStrategyLabChart(chart, [], form.elements.strategy_range.value || "year");
    return;
  }

  const metrics = result.metrics || {};
  summary.innerHTML = [
    resultItem("Strategy", strategyLabStrategyLabel(result.strategyType)),
    resultItem("Symbols", result.tickers.join(", ")),
    resultItem("Option Overlay", result.overlay?.summaryLabel || "None"),
    resultItem("Overlay Source", result.overlay?.active ? result.overlay.source : "Not used"),
    resultItem("Return", formatReturnAxis(metrics.returnPct)),
    resultItem("Annualized Vol", pct(metrics.annualizedVolatility)),
    resultItem("Max Drawdown", formatReturnAxis(metrics.maxDrawdownPct)),
    resultItem("Latest Value", money(metrics.latestValue)),
    resultItem("Observations", String(metrics.observations || 0)),
    resultItem("Overlay Detail", result.overlay?.active ? `${result.overlay.symbol} · ${result.overlay.detailLabel}` : "None"),
  ].join("");
  notes.innerHTML = result.notes.map((note) => (
    `<div class="activity-item"><strong>${escapeHtml(note.title)}</strong><span>${escapeHtml(note.body)}</span></div>`
  )).join("");
  legend.innerHTML = result.series.map((line, index) => {
    const value = lineReturnPct(line);
    const dash = index > 0 ? " dashed" : "";
    return `<div class="legend-item"><span class="legend-swatch${dash}" style="--series-color:${escapeHtml(line.color)}"></span><span>${escapeHtml(line.label)}</span><strong class="${returnClass(value)}">${Number.isFinite(value) ? formatReturnAxis(value) : "--"}</strong></div>`;
  }).join("");
  status.textContent = result.points.length >= 2 ? "Scenario ready" : "Needs history";
  status.className = result.points.length >= 2 ? "pill" : "pill muted";
  drawStrategyLabChart(chart, result.series, result.rangeName);
}

function renderRelativisticBSHistory() {
  const payload = appState.relativisticBsHistory;
  const points = relbsValidHistoryPoints(payload?.points || []);
  const captureCount = new Set(points.map((point) => new Date(point.as_of).getTime())).size;
  const note = $("#relativistic-bs-history-note");
  if (note) {
    const base = payload?.note || "Run the live suite to begin capturing dated option-chain snapshots.";
    note.textContent = `${base} Saved captures matching this expiry: ${captureCount}.`;
  }
  const charts = [
    ["#relativistic-bs-history-iv-chart", "ATM Implied Volatility", "atm_iv", ".1%", "#0f766e", "%{y:.1%}"],
    ["#relativistic-bs-history-gamma-chart", "Net Gamma Exposure", "total_gamma_exposure", ",.0f", "#8b1e3f", "%{y:,.0f}"],
    ["#relativistic-bs-history-volume-chart", "Total Chain Volume", "total_volume", ",.0f", "#2f6f9f", "%{y:,.0f}"],
  ];
  charts.forEach(([selector, title, field, tickformat, color, hoverValue]) => {
    const container = $(selector);
    if (!container) return;
    const trace = relbsDatedTrace(title, points, field, color, "solid", hoverValue);
    if (captureCount < 2 || trace.x.length < 2) {
      renderRelbsNoData(container, `No ${title.toLowerCase()} trend yet`, "Refresh the live chain later to add a second saved capture.");
      return;
    }
    renderRelbsDatedPlot(container, title, [trace], { tickformat });
  });
  const priceContainer = $("#relativistic-bs-history-price-chart");
  if (!priceContainer) return;
  const priceTraces = [
    relbsDatedTrace("Market midpoint", points, "atm_market_price", "#2f6f9f", "solid", "%{y:$,.2f}"),
    relbsDatedTrace("Black-Scholes", points, "atm_bs_price", "#0f766e", "dash", "%{y:$,.2f}"),
    relbsDatedTrace("Relativistic", points, "atm_relativistic_price", "#8b1e3f", "solid", "%{y:$,.2f}"),
  ].filter((trace) => trace.x.length >= 2);
  if (captureCount < 2 || !priceTraces.length) {
    renderRelbsNoData(priceContainer, "No ATM pricing history trend yet", "Refresh the live chain later to add a second saved capture.");
    return;
  }
  renderRelbsDatedPlot(priceContainer, "ATM Call Pricing History", priceTraces, { tickprefix: "$" });
}

function renderRelbsDatedPlot(container, title, traces, yOverrides = {}) {
  renderRelbsPlot(container, traces, {
    title,
    xaxis: relbsDateAxis("Captured At"),
    yaxis: relbsAxis(title, yOverrides),
    hovermode: "x unified",
  });
}

function renderRelativisticBSChart(container, payload) {
  const chain = payload.option_chain || [];
  if (!chain.length) {
    container.innerHTML = `<div class="activity-item"><strong>No option chain</strong><span>No strikes were available for the selected settings.</span></div>`;
    return;
  }
  if (!window.Plotly) {
    container.innerHTML = `<div class="activity-item"><strong>Chart unavailable</strong><span>The table below contains the same call and put model prices.</span></div>`;
    return;
  }

  const strikes = chain.map((row) => row.strike);
  const callMarket = chain.map((row) => relbsNumericMarketPrice(row.call));
  const putMarket = chain.map((row) => relbsNumericMarketPrice(row.put));
  const traces = [
    relbsTrace("Call Relativistic", strikes, chain.map((row) => row.call.relativistic_price), "#0f766e"),
    relbsTrace("Call Black-Scholes", strikes, chain.map((row) => row.call.bs_price), "#0f766e", "dash"),
    relbsTrace("Put Relativistic", strikes, chain.map((row) => row.put.relativistic_price), "#8b1e3f"),
    relbsTrace("Put Black-Scholes", strikes, chain.map((row) => row.put.bs_price), "#8b1e3f", "dash"),
  ];
  if (callMarket.some((value) => Number.isFinite(value))) {
    traces.push(relbsMarkerTrace("Call Market", strikes, callMarket, "#2f6f9f"));
  }
  if (putMarket.some((value) => Number.isFinite(value))) {
    traces.push(relbsMarkerTrace("Put Market", strikes, putMarket, "#a35f00"));
  }

  container.innerHTML = "";
  const plot = document.createElement("div");
  plot.className = "relbs-plot";
  container.appendChild(plot);
  const theme = chartTheme();
  try {
    window.Plotly.newPlot(plot, traces, {
      title: `${payload.symbol} Option Chain: Model Price by Strike`,
      height: 460,
      margin: { t: 52, r: 24, b: 56, l: 64 },
      paper_bgcolor: theme.surface,
      plot_bgcolor: theme.plotBg,
      font: { color: theme.text },
      xaxis: relbsStrikeAxis("Strike Price", { tickprefix: "$" }),
      yaxis: { title: "Option Price", tickprefix: "$", rangemode: "tozero", zeroline: false, gridcolor: theme.gridLine, linecolor: theme.border },
      legend: { orientation: "h", y: -0.22 },
      hovermode: "x unified",
      hoverlabel: { bgcolor: theme.surface, bordercolor: theme.border, font: { color: theme.text } },
    }, { responsive: true, displayModeBar: true, scrollZoom: true, modeBarButtonsToRemove: ["select2d", "lasso2d"] });
  } catch (error) {
    container.innerHTML = `<div class="activity-item"><strong>Chart unavailable</strong><span>The option-chain table is still available below.</span></div>`;
  }
}

function renderRelbsVolatilityGuide(container, payload) {
  const guide = payload.baseline_volatility || {};
  const estimates = guide.estimates || [];
  const selected = Number(guide.selected_sigma ?? payload.parameters?.sigma ?? 0);
  const recommended = Number(guide.recommended_sigma ?? selected);
  const cards = [
    relbsVolatilityCard("Current model sigma", selected, "Manual input currently used by Black-Scholes and the relativistic correction.", false),
    relbsVolatilityCard("Recommended baseline", recommended, "Best available automatic reference from ATM IV, chain IV, or realized volatility.", true),
  ].concat(estimates.map((estimate) => relbsVolatilityCard(estimate.label, estimate.value, estimate.detail, true)));
  const notes = (guide.notes || []).map((note) => `<div class="activity-item"><strong>Guide</strong><span>${escapeHtml(note)}</span></div>`).join("");
  container.innerHTML = cards.join("") + notes;
}

function relbsVolatilityCard(label, value, detail, actionable) {
  const numeric = Number(value);
  const button = actionable && Number.isFinite(numeric) && numeric > 0
    ? `<button class="button secondary vol-use-button" type="button" data-volatility-value="${numeric}">Use in model</button>`
    : "";
  return `<div class="vol-estimate-card">
    <span>${escapeHtml(label)}</span>
    <strong>${relativisticBSPct(numeric)}</strong>
    <p>${escapeHtml(detail || "Volatility estimate.")}</p>
    ${button}
  </div>`;
}

function renderRelbsVolatilitySmile(container, payload) {
  const rows = payload.volatility_smile || [];
  if (!rows.length) {
    renderRelbsNoData(container, "No volatility smile", "Run with live chains enabled; generated chains do not contain listed market IV.");
    return;
  }
  const x = rows.map((row) => row.strike);
  const traces = [
    relbsNumericTrace("Call IV", x, rows.map((row) => row.call_iv), "#0f766e", "solid", relbsPctHover()),
    relbsNumericTrace("Put IV", x, rows.map((row) => row.put_iv), "#8b1e3f", "solid", relbsPctHover()),
    relbsNumericTrace("Average IV", x, rows.map((row) => row.average_iv), "#2f6f9f", "solid", relbsPctHover()),
    relbsNumericTrace("Baseline sigma", x, rows.map((row) => row.baseline_iv), "#a35f00", "dash", relbsPctHover()),
  ].filter((trace) => trace.x.length);
  renderRelbsPlot(container, traces, {
    title: `${payload.symbol} Volatility Smile`,
    xaxis: relbsStrikeAxis("Strike", { tickprefix: "$" }),
    yaxis: relbsAxis("Implied Volatility", { tickformat: ".0%" }),
    hovermode: "x unified",
  });
}

function renderRelbsCumulativeVolume(container, payload) {
  const rows = payload.cumulative_volume || [];
  const hasVolume = rows.some((row) => Number(row.call_volume) || Number(row.put_volume));
  if (!rows.length || !hasVolume) {
    renderRelbsNoData(container, "No volume data", "The selected chain did not include volume. Open interest may still appear in the gamma exposure chart.");
    return;
  }
  const x = rows.map((row) => row.strike);
  const traces = [
    { name: "Call volume", x, y: rows.map((row) => row.call_volume), type: "bar", marker: { color: "#0f766e" }, yaxis: "y" },
    { name: "Put volume", x, y: rows.map((row) => row.put_volume), type: "bar", marker: { color: "#8b1e3f" }, yaxis: "y" },
    relbsTrace("Cum call volume", x, rows.map((row) => row.cumulative_call_volume), "#2f6f9f", "solid", relbsNumberHover()),
    relbsTrace("Cum put volume", x, rows.map((row) => row.cumulative_put_volume), "#a35f00", "solid", relbsNumberHover()),
  ];
  traces[2].yaxis = "y2";
  traces[3].yaxis = "y2";
  renderRelbsPlot(container, traces, {
    title: `${payload.symbol} Volume By Strike`,
    barmode: "group",
    xaxis: relbsStrikeAxis("Strike", { tickprefix: "$" }),
    yaxis: relbsAxis("Daily Volume"),
    yaxis2: { ...relbsAxis("Cumulative Volume"), overlaying: "y", side: "right" },
    hovermode: "x unified",
  });
}

function renderRelbsGammaExposure(container, payload) {
  const rows = payload.gamma_exposure || [];
  const hasExposure = rows.some((row) => Number(row.gross_gamma_exposure));
  if (!rows.length || !hasExposure) {
    renderRelbsNoData(container, "No gamma exposure", "Gamma exposure needs listed open interest. If the chain is thin or generated, exposure is zero.");
    return;
  }
  const x = rows.map((row) => row.strike);
  const traces = [
    { name: "Call GEX", x, y: rows.map((row) => row.call_gamma_exposure), type: "bar", marker: { color: "#0f766e" } },
    { name: "Put GEX", x, y: rows.map((row) => row.put_gamma_exposure), type: "bar", marker: { color: "#8b1e3f" } },
    relbsTrace("Net GEX", x, rows.map((row) => row.net_gamma_exposure), "#2f6f9f", "solid", relbsNumberHover()),
  ];
  renderRelbsPlot(container, traces, {
    title: `${payload.symbol} Estimated Gamma Exposure`,
    barmode: "relative",
    xaxis: relbsStrikeAxis("Strike", { tickprefix: "$" }),
    yaxis: relbsAxis("$ per 1% spot move"),
    hovermode: "x unified",
  });
}

function renderRelbsIVSurface(container, payload) {
  updateRelbsSurfaceFilterBounds(payload.iv_surface || []);
  const filters = relbsSurfaceFilters();
  const rows = relbsFiniteSurfaceRows(payload.iv_surface || [], filters);
  const note = $("#relativistic-bs-surface-filter-note");
  if (note) note.textContent = relbsSurfaceFilterNote(rows, filters);
  if (!rows.length) {
    renderRelbsNoData(container, "No IV surface in this view", "Adjust the expiry or moneyness range. The IV surface needs multiple yfinance expirations with listed implied volatility.");
    return;
  }
  const grid = relbsIVSurfaceGrid(rows);
  const theme = chartTheme();
  const trace = grid.moneyness.length >= 2 && grid.days.length >= 2 ? {
    type: "surface",
    x: grid.moneyness,
    y: grid.days,
    z: grid.values,
    colorscale: "Viridis",
    colorbar: { title: { text: "IV", font: { color: theme.text } }, tickformat: ".0%", tickfont: { color: theme.text } },
    hovertemplate: "Moneyness %{x:.2f}<br>DTE %{y:.0f}<br>IV %{z:.1%}<extra></extra>",
  } : {
    type: "scatter3d",
    mode: "markers",
    x: grid.points.map((row) => row.moneyness),
    y: grid.points.map((row) => row.days),
    z: grid.points.map((row) => row.averageIv),
    marker: { size: 5, color: grid.points.map((row) => row.averageIv), colorscale: "Viridis", colorbar: { title: { text: "IV", font: { color: theme.text } }, tickformat: ".0%", tickfont: { color: theme.text } } },
    hovertemplate: "Moneyness %{x:.2f}<br>DTE %{y:.0f}<br>IV %{z:.1%}<extra></extra>",
  };
  renderRelbsPlot(container, [trace], {
    title: `${payload.symbol} Implied Volatility Surface`,
    scene: {
      xaxis: relbsSceneAxis("Moneyness"),
      yaxis: relbsSceneAxis("Days to expiry"),
      zaxis: relbsSceneAxis("Implied Volatility", { tickformat: ".0%" }),
    },
    height: 640,
    margin: { t: 48, r: 8, b: 8, l: 8 },
  });
}

function relbsIVSurfaceGrid(rows) {
  const points = relbsFiniteSurfaceRows(rows).map((row) => ({
    moneyness: Number(row.moneyness),
    days: Math.max(1, Math.round(Number(row.tau) * 365.25)),
    averageIv: Number(row.average_iv),
  }));
  const profiles = new Map();
  points.forEach((point) => {
    const profile = profiles.get(point.days) || [];
    profile.push(point);
    profiles.set(point.days, profile);
  });
  const usableProfiles = Array.from(profiles.entries()).map(([day, profile]) => [
    day,
    profile.sort((left, right) => left.moneyness - right.moneyness),
  ]).filter(([, profile]) => profile.length >= 2).sort(([left], [right]) => left - right);
  if (usableProfiles.length < 2) return { moneyness: [], days: [], values: [], points };
  const minMoneyness = Math.max(...usableProfiles.map(([, profile]) => profile[0].moneyness));
  const maxMoneyness = Math.min(...usableProfiles.map(([, profile]) => profile[profile.length - 1].moneyness));
  if (!Number.isFinite(minMoneyness) || !Number.isFinite(maxMoneyness) || maxMoneyness - minMoneyness < 0.04) {
    return { moneyness: [], days: [], values: [], points };
  }
  const steps = 30;
  const moneyness = Array.from({ length: steps + 1 }, (_, index) => (
    minMoneyness + ((maxMoneyness - minMoneyness) * index / steps)
  ));
  const days = usableProfiles.map(([day]) => day);
  return {
    moneyness,
    days,
    values: usableProfiles.map(([, profile]) => moneyness.map((moneyValue) => relbsInterpolatedIV(profile, moneyValue))),
    points,
  };
}

function relbsInterpolatedIV(profile, moneyness) {
  if (!profile.length || moneyness < profile[0].moneyness || moneyness > profile[profile.length - 1].moneyness) return null;
  for (let index = 0; index < profile.length; index += 1) {
    const right = profile[index];
    if (Math.abs(right.moneyness - moneyness) < 1e-9) return right.averageIv;
    if (right.moneyness < moneyness || index === 0) continue;
    const left = profile[index - 1];
    const span = right.moneyness - left.moneyness;
    if (span <= 0) return right.averageIv;
    const ratio = (moneyness - left.moneyness) / span;
    return left.averageIv + (right.averageIv - left.averageIv) * ratio;
  }
  return profile[profile.length - 1].averageIv;
}

function relbsFiniteSurfaceRows(rows, filters = {}) {
  const minMoneyness = finiteNumber(filters.minMoneyness, 0.5);
  const maxMoneyness = finiteNumber(filters.maxMoneyness, 1.5);
  return rows.filter((row) => {
    const moneyness = Number(row.moneyness);
    const tau = Number(row.tau);
    const averageIv = Number(row.average_iv);
    const expiry = String(row.expiry_date || "");
    return Number.isFinite(moneyness) && moneyness >= minMoneyness && moneyness <= maxMoneyness
      && Number.isFinite(tau) && tau > 0
      && Number.isFinite(averageIv) && averageIv >= 0.02 && averageIv <= 3
      && (!filters.expiryMin || expiry >= filters.expiryMin)
      && (!filters.expiryMax || expiry <= filters.expiryMax);
  });
}

function relbsSurfaceFilters() {
  const rawMin = finiteNumber($("#relativistic-bs-surface-moneyness-min")?.value, 0.75);
  const rawMax = finiteNumber($("#relativistic-bs-surface-moneyness-max")?.value, 1.25);
  return {
    expiryMin: $("#relativistic-bs-surface-expiry-min")?.value || "",
    expiryMax: $("#relativistic-bs-surface-expiry-max")?.value || "",
    minMoneyness: Math.max(0.5, Math.min(rawMin, rawMax)),
    maxMoneyness: Math.min(1.5, Math.max(rawMin, rawMax)),
  };
}

function updateRelbsSurfaceFilterBounds(rows) {
  const expiries = rows.map((row) => String(row.expiry_date || "")).filter(Boolean).sort();
  const minExpiry = expiries[0] || "";
  const maxExpiry = expiries[expiries.length - 1] || "";
  ["#relativistic-bs-surface-expiry-min", "#relativistic-bs-surface-expiry-max"].forEach((selector) => {
    const input = $(selector);
    if (!input) return;
    input.min = minExpiry;
    input.max = maxExpiry;
  });
}

function relbsSurfaceFilterNote(rows, filters) {
  const expiries = Array.from(new Set(rows.map((row) => row.expiry_date))).filter(Boolean).sort();
  const expiryText = expiries.length ? `${expiries[0]} through ${expiries[expiries.length - 1]}` : "no matching expiries";
  return `Showing ${rows.length} listed IV observations across ${expiryText}, with moneyness ${filters.minMoneyness.toFixed(2)} to ${filters.maxMoneyness.toFixed(2)}. View controls use loaded snapshot data only.`;
}

function renderRelbsPlot(container, traces, layoutOverrides = {}) {
  if (!window.Plotly) {
    renderRelbsNoData(container, "Chart unavailable", "Plotly is not available, but the option-chain table is still available below.");
    return;
  }
  container.innerHTML = "";
  const plot = document.createElement("div");
  plot.className = "relbs-plot";
  container.appendChild(plot);
  const theme = chartTheme();
  const layout = {
    height: 420,
    margin: { t: 48, r: 28, b: 58, l: 64 },
    paper_bgcolor: theme.surface,
    plot_bgcolor: theme.plotBg,
    font: { color: theme.text },
    hoverlabel: { bgcolor: theme.surface, bordercolor: theme.border, font: { color: theme.text } },
    legend: { orientation: "h", y: -0.22 },
    ...layoutOverrides,
  };
  try {
    window.Plotly.newPlot(plot, traces, layout, { responsive: true, displayModeBar: true, scrollZoom: true, modeBarButtonsToRemove: ["select2d", "lasso2d"] });
  } catch (error) {
    renderRelbsNoData(container, "Chart unavailable", "The option-chain table is still available below.");
  }
}

function relbsAxis(title, overrides = {}) {
  const theme = chartTheme();
  return { title, zeroline: false, gridcolor: theme.gridLine, linecolor: theme.border, tickfont: { color: theme.text }, ...overrides };
}

function relbsStrikeAxis(title, overrides = {}) {
  return relbsAxis(title, { rangeslider: { visible: true, thickness: 0.08 }, fixedrange: false, ...overrides });
}

function relbsDateAxis(title, overrides = {}) {
  return relbsAxis(title, { type: "date", rangeslider: { visible: true, thickness: 0.08 }, fixedrange: false, ...overrides });
}

function relbsSceneAxis(title, overrides = {}) {
  const theme = chartTheme();
  return { title, gridcolor: theme.gridLine, linecolor: theme.border, tickfont: { color: theme.text }, ...overrides };
}

function renderRelbsNoData(container, title, message) {
  container.innerHTML = `<div class="activity-item"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(message)}</span></div>`;
}

function relbsTrace(name, x, y, color, dash = "solid", hovertemplate = "%{x:$,.2f}<br>%{y:$,.2f}<extra></extra>") {
  return {
    name,
    x,
    y,
    type: "scatter",
    mode: "lines",
    line: { color, width: 2.5, dash },
    hovertemplate,
  };
}

function relbsNumericTrace(name, x, y, color, dash = "solid", hovertemplate = "%{x:$,.2f}<br>%{y:$,.2f}<extra></extra>") {
  const points = x.map((value, index) => ({ x: Number(value), y: Number(y[index]) }))
    .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y));
  return {
    ...relbsTrace(name, points.map((point) => point.x), points.map((point) => point.y), color, dash, hovertemplate),
    mode: "lines+markers",
    marker: { color, size: 5 },
    connectgaps: true,
  };
}

function relbsDatedTrace(name, points, field, color, dash = "solid", valueTemplate = "%{y:,.2f}") {
  const clean = points.map((point) => ({
    x: point.as_of,
    time: new Date(point.as_of).getTime(),
    y: Number(point[field]),
  })).filter((point) => Number.isFinite(point.time) && Number.isFinite(point.y));
  return relbsTrace(
    name,
    clean.map((point) => point.x),
    clean.map((point) => point.y),
    color,
    dash,
    `%{x|%b %d, %Y %H:%M}<br>${valueTemplate}<extra></extra>`,
  );
}

function relbsValidHistoryPoints(points) {
  return points.filter((point) => Number.isFinite(new Date(point.as_of).getTime()))
    .sort((left, right) => new Date(left.as_of) - new Date(right.as_of));
}

function relbsPctHover() {
  return "%{x:$,.2f}<br>%{y:.1%}<extra></extra>";
}

function relbsNumberHover() {
  return "%{x:$,.2f}<br>%{y:,.0f}<extra></extra>";
}

function relbsMarkerTrace(name, x, y, color) {
  return {
    name,
    x,
    y,
    type: "scatter",
    mode: "markers",
    marker: { color, size: 7, symbol: "circle-open" },
    hovertemplate: "%{x:$,.2f}<br>%{y:$,.2f}<extra></extra>",
  };
}

function relbsMetricValue(item) {
  return item.label.includes("IV") ? relativisticBSPct(item.value) : fixed(item.value, 4);
}

function relbsNumericMarketPrice(side) {
  const bid = Number(side?.bid);
  const ask = Number(side?.ask);
  if (Number.isFinite(bid) && Number.isFinite(ask) && bid > 0 && ask > 0) return (bid + ask) / 2;
  const last = Number(side?.market_last);
  return Number.isFinite(last) ? last : NaN;
}

function relbsMarketPrice(side) {
  const value = relbsNumericMarketPrice(side);
  return Number.isFinite(value) ? money(value) : "--";
}

function relbsChainSource(value) {
  if (value === "yfinance-cache") return "YFinance cache";
  if (value === "yfinance") return "YFinance live";
  return "Generated strikes";
}

function relativisticBSPct(value) {
  return Number.isFinite(Number(value)) ? pct(Number(value)) : "--";
}

function renderRisk() {
  const risk = appState.riskAnalysis?.charts?.risk;
  const rawCorrelation = $("#raw-correlation-heatmap");
  const insights = $("#risk-correlation-insights");
  const threshold = riskCorrelationThreshold();
  const thresholdOutput = $("#risk-correlation-threshold-value");
  if (thresholdOutput) thresholdOutput.textContent = threshold.toFixed(2);
  if (!risk) {
    $("#risk-summary").innerHTML = `<div class="activity-item"><strong>No risk run</strong><span>Run analysis from cached market history. Manual price rows are optional.</span></div>`;
    $("#risk-volatility").innerHTML = `<div class="activity-item"><strong>No volatility estimate</strong><span>Use one year of cached prices for a practical first pass.</span></div>`;
    $("#correlation-heatmap").innerHTML = "";
    $("#risk-covariance-heatmap").innerHTML = "";
    if (rawCorrelation) rawCorrelation.innerHTML = "";
    if (insights) insights.innerHTML = `<div class="activity-item"><strong>No pair scan yet</strong><span>Run risk analysis to rank the strongest relationships.</span></div>`;
    return;
  }

  const summary = riskSummary(risk);
  const annualization = finiteNumber(risk.annualization_factor, 252);
  const pairSamples = minimumPairwiseObservations(risk.pairwise_observations);
  $("#risk-summary").innerHTML = [
    resultItem("Annualized Portfolio Vol", pct(summary.portfolioVolatility * Math.sqrt(annualization))),
    resultItem("Daily Portfolio Vol", pct(summary.portfolioVolatility)),
    resultItem("Observations", String(risk.observations || 0)),
    resultItem("Minimum Pair Samples", String(pairSamples)),
    resultItem("Highest Single-Asset Vol", summary.highestVolatilityLabel),
    resultItem("Average Correlation", fixed(summary.averageCorrelation, 2)),
    resultItem("Strongest Pair", summary.strongestPairLabel),
    resultItem("Correlation View", risk.cleaned_correlation ? "RMT cleaned" : "Raw"),
  ].join("");
  renderBars($("#risk-volatility"), risk.volatility_by_ticker.map((point) => {
    const annualized = finiteNumber(point.value, 0) * Math.sqrt(annualization);
    return { label: point.label, value: annualized, display: pct(annualized) };
  }));
  const correlationOptions = {
    digits: 2,
    threshold,
    hideWeakLabels: true,
    color: (value, meta) => correlationTemperatureColor(value, threshold, meta.diagonal),
    titleFormatter: (value, meta) => `${meta.rowTicker} / ${meta.columnTicker}: correlation ${value.toFixed(3)}${!meta.diagonal && Math.abs(value) < threshold ? " (muted by display threshold)" : ""}`,
  };
  const displayCorrelation = risk.cleaned_correlation || risk.correlation;
  renderMatrix($("#correlation-heatmap"), displayCorrelation, correlationOptions);
  if (rawCorrelation) renderMatrix(rawCorrelation, risk.correlation, correlationOptions);
  renderMatrix($("#risk-covariance-heatmap"), risk.cleaned_covariance || risk.covariance, {
    transform: (value) => value * annualization,
    formatter: (value, meta) => meta.diagonal ? `${pct(Math.sqrt(Math.max(value, 0)))} vol` : formatCovariance(value),
    titleFormatter: (value, meta) => meta.diagonal
      ? `${meta.rowTicker} annualized variance ${formatCovariance(value)}; annualized volatility ${pct(Math.sqrt(Math.max(value, 0)))}`
      : `${meta.rowTicker} / ${meta.columnTicker}: annualized covariance ${formatCovariance(value)}`,
    normalizeColor: true,
  });
  if (insights) insights.innerHTML = correlationInsightsHtml(displayCorrelation, threshold);
}

function renderRiskTolerance() {
  const form = $("#risk-tolerance-form");
  const summary = $("#risk-profile-summary");
  const description = $("#risk-profile-description");
  const results = $("#risk-reweight-results");
  const status = $("#risk-tolerance-status");
  if (!form || !summary || !description || !results || !status || !appState.portfolio) return;
  const score = Math.max(1, Math.min(10, Math.round(finiteNumber(form.elements.risk_tolerance_score.value, 5))));
  $("#risk-tolerance-score-value").textContent = String(score);
  const savedProfile = appState.riskTolerance?.profile;
  const profile = savedProfile?.score === score ? savedProfile : riskProfilePreview(score);
  const current = appState.riskTolerance?.current_model;
  const target = profile.target_allocation;
  summary.innerHTML = [
    resultItem("Selected Score", `${score} - ${profile.label}`),
    resultItem("Target Volatility", pct(profile.target_volatility)),
    resultItem("Target Equity", pct(target.equity)),
    resultItem("Target Bonds", pct(target.bonds)),
    resultItem("Target Cash", pct(target.cash)),
    resultItem("Current Model Vol", current ? pct(current.model_volatility) : "--"),
    resultItem("Current Model Score", current ? String(current.estimated_score) : "--"),
  ].join("");
  description.innerHTML = [
    `<div class="activity-item"><strong>What this score means</strong><span>${escapeHtml(profile.description)}</span></div>`,
    `<div class="activity-item"><strong>How to read volatility</strong><span>${escapeHtml(profile.volatility_explanation)}</span></div>`,
  ].join("");
  const savedScore = appState.portfolio.settings?.risk_tolerance_score ?? 5;
  status.textContent = score === savedScore ? `Saved score ${savedScore}` : `Preview score ${score}`;
  status.className = score === savedScore ? "pill" : "pill muted";

  const reweight = appState.riskReweight;
  if (!reweight) {
    results.innerHTML = `<div class="activity-item"><strong>No target preview yet</strong><span>Save the score to calculate target values and estimated trade deltas. No trades are executed.</span></div>`;
    return;
  }
  const notes = (reweight.notes || []).map((note) => `<div class="activity-item"><strong>Allocation note</strong><span>${escapeHtml(note)}</span></div>`).join("");
  const table = document.createElement("div");
  renderTableHtml(table, ["Asset", "Bucket", "Current", "Target", "Value Delta", "Estimated Units"], reweight.allocations.map((item) => [
    `<strong>${escapeHtml(item.symbol)}</strong>`,
    escapeHtml(item.risk_bucket),
    `${pct(item.current_weight)} (${money(item.current_value)})`,
    `${pct(item.target_weight)} (${money(item.target_value)})`,
    `<span class="${item.trade_value_delta >= 0 ? "positive" : "negative"}">${signedMoney(item.trade_value_delta)}</span>`,
    item.estimated_quantity_delta == null ? "--" : fixed(item.estimated_quantity_delta, 3),
  ]));
  results.innerHTML = `${notes}${table.innerHTML}`;
}

function riskProfilePreview(score) {
  const [label, targetVolatility, equity, bonds, cash] = RISK_SCORE_TARGETS[score] || RISK_SCORE_TARGETS[5];
  let description;
  if (score <= 2) description = "Prioritizes smaller modeled drawdowns and liquidity. Most capital is assigned to bonds and cash, so long-run upside may be lower.";
  else if (score <= 4) description = "Accepts limited fluctuations while keeping a substantial fixed-income cushion. Bond prices can still fall when rates or credit spreads rise.";
  else if (score <= 6) description = "Balances growth and stability. Temporary double-digit declines remain plausible in diversified portfolios.";
  else if (score <= 8) description = "Prioritizes growth and accepts larger market swings and potentially prolonged recovery periods.";
  else description = "Accepts very large fluctuations for maximum modeled growth exposure. Severe drawdowns are possible.";
  return {
    score,
    label,
    description,
    target_volatility: targetVolatility,
    target_allocation: { equity, bonds, cash },
    volatility_explanation: "Target volatility estimates typical annual variability; it is not a maximum loss, guarantee, or confidence boundary.",
  };
}

function renderBonds() {
  const table = $("#bond-assets-table");
  const note = $("#bond-market-note");
  if (!table || !note) return;
  const payload = appState.bondAssets;
  if (!payload) {
    note.textContent = "Open this tab to load the public bond catalog and cached prices.";
    table.innerHTML = `<div class="activity-item"><strong>Catalog not loaded</strong><span>Bond assets load only when this tab is opened.</span></div>`;
    renderBondStrategy();
    return;
  }
  note.textContent = payload.note;
  const category = $("#bond-category-filter").value;
  const monitoredOnly = $("#bond-watchlist-only").checked;
  const assets = payload.assets.filter((asset) => (
    (category === "all" || asset.category === category) && (!monitoredOnly || asset.monitored)
  ));
  renderTableHtml(table, ["Monitor", "Ticker", "Asset", "Category", "Term Proxy", "Risk", "Price", "Day", "Fetched", "Details"], assets.map((asset) => [
    `<input type="checkbox" data-bond-monitor="${escapeHtml(asset.ticker)}" ${asset.monitored ? "checked" : ""} aria-label="Monitor ${escapeHtml(asset.ticker)}">`,
    `<strong>${escapeHtml(asset.ticker)}</strong>`,
    `<span class="bond-asset-name">${escapeHtml(asset.name)}</span><small>${escapeHtml(asset.description)}</small>`,
    escapeHtml(asset.category),
    `${escapeHtml(asset.duration_bucket)} (${fixed(asset.term_proxy_years, 2)}y)`,
    `${asset.risk_level}/10`,
    asset.price == null ? "--" : money(asset.price),
    asset.daily_return_pct == null ? "--" : `<span class="${asset.daily_return_pct >= 0 ? "positive" : "negative"}">${signedPct(asset.daily_return_pct / 100)}</span>`,
    asset.fetched_at ? shortDateTime(asset.fetched_at) : "Not cached",
    `<a href="${escapeHtml(asset.issuer_url)}" target="_blank" rel="noopener noreferrer">Issuer page</a>`,
  ]));
  if (!appState.bondRungs.length) setRecommendedBondRungs();
  if (!$("#bond-rung-rows").children.length) renderBondRungRows();
  renderBondStrategy();
}

function renderBondRungRows() {
  const container = $("#bond-rung-rows");
  if (!container) return;
  container.innerHTML = appState.bondRungs.map((rung, index) => `
    <tr data-bond-rung="${index}">
      <td><input data-field="label" value="${escapeHtml(rung.label || `Rung ${index + 1}`)}" aria-label="Rung label"></td>
      <td><input data-field="years_to_maturity" type="number" min="0.25" max="50" step="0.25" value="${finiteNumber(rung.years_to_maturity, 1)}" aria-label="Years to maturity"></td>
      <td><input data-field="coupon_rate" type="number" min="0" max="100" step="0.01" value="${fixed(finiteNumber(rung.coupon_rate, 0.04) * 100, 2)}" aria-label="Coupon percent"></td>
      <td><input data-field="yield_to_maturity" type="number" min="-99" max="100" step="0.01" value="${fixed(finiteNumber(rung.yield_to_maturity, 0.04) * 100, 2)}" aria-label="Yield to maturity percent"></td>
      <td><input data-field="market_price_pct" type="number" min="0.01" max="1000" step="0.01" value="${fixed(finiteNumber(rung.market_price_pct, 100), 2)}" aria-label="Market price per 100"></td>
      <td><input data-field="allocation_weight" type="number" min="0" max="100" step="0.1" value="${fixed(finiteNumber(rung.allocation_weight, 0) * 100, 1)}" aria-label="Allocation weight percent"></td>
      <td><select data-field="payments_per_year" aria-label="Coupon payments per year"><option value="1" ${Number(rung.payments_per_year) === 1 ? "selected" : ""}>Annual</option><option value="2" ${Number(rung.payments_per_year || 2) === 2 ? "selected" : ""}>Semiannual</option><option value="4" ${Number(rung.payments_per_year) === 4 ? "selected" : ""}>Quarterly</option><option value="12" ${Number(rung.payments_per_year) === 12 ? "selected" : ""}>Monthly</option></select></td>
      <td><button class="icon-button danger-link" type="button" data-bond-rung-remove="${index}" title="Remove rung" aria-label="Remove rung">X</button></td>
    </tr>`).join("");
  normalizeNumericInputs(container);
}

function renderBondStrategy() {
  const summary = $("#bond-strategy-summary");
  const notes = $("#bond-strategy-notes");
  const results = $("#bond-strategy-results");
  const cashFlows = $("#bond-cash-flow-results");
  if (!summary || !notes || !results || !cashFlows) return;
  const strategy = appState.bondStrategy;
  if (!strategy) {
    summary.innerHTML = "";
    notes.innerHTML = `<div class="activity-item"><strong>No calculation yet</strong><span>Load a risk-fit structure, adjust the assumptions, and calculate the strategy.</span></div>`;
    results.innerHTML = "";
    cashFlows.innerHTML = "";
    return;
  }
  const metrics = strategy.summary;
  summary.innerHTML = [
    metricCard("Allocated", money(metrics.allocated_capital)),
    metricCard("Annual Income", money(metrics.annual_income)),
    metricCard("Current Yield", pct(metrics.portfolio_current_yield)),
    metricCard("Weighted YTM", pct(metrics.weighted_yield_to_maturity)),
    metricCard("Modified Duration", fixed(metrics.weighted_modified_duration, 2)),
    metricCard("Modeled Annual Return", pct(metrics.weighted_annualized_return)),
  ].join("");
  notes.innerHTML = (strategy.notes || []).map((item) => `<div class="activity-item"><strong>Model note</strong><span>${escapeHtml(item)}</span></div>`).join("");
  renderTableHtml(results, ["Rung", "Weight", "Price / $100", "Model Price", "Coupon", "YTM", "Duration", "Annual Income", "Annualized Return"], strategy.rungs.map((rung) => [
    escapeHtml(rung.label),
    pct(rung.weight),
    fixed(rung.market_price_pct, 2),
    fixed(rung.theoretical_price_pct, 2),
    pct(rung.coupon_rate),
    pct(rung.yield_to_maturity),
    fixed(rung.modified_duration, 2),
    money(rung.annual_income),
    pct(rung.annualized_return),
  ]));
  renderTable(cashFlows, ["Year", "Coupon Income", "Principal", "Total Cash Flow"], strategy.cash_flow_schedule.map((item) => [
    String(item.year),
    money(item.coupon_income),
    money(item.principal),
    money(item.total_cash_flow),
  ]));
}

async function renderHeatmap() {
  const container = $("#heatmap-grid");
  if (!appState.heatmap && appState.selectedPortfolioId && (appState.portfolio?.positions || []).length) {
    try {
      appState.heatmap = await api(`/portfolios/${appState.selectedPortfolioId}/heatmap`);
    } catch (error) {
      // Fall through to the local tile fallback.
    }
  }

  const heatmap = appState.heatmap;
  const holdings = heatmap?.holdings || (appState.portfolio?.positions || []).map((position) => {
    const dailyReturn = quoteDailyReturnPct(quoteForTicker(position.ticker));
    return {
      label: position.ticker,
      ticker: position.ticker,
      market_value: position.market_value,
      cost_basis: position.cost_basis,
      portfolio_weight_pct: position.market_value / Math.max(appState.portfolio.totals.market_value, 1) * 100,
      daily_return_pct: Number.isFinite(dailyReturn) ? dailyReturn : null,
      unrealized_pnl: position.unrealized_gain_loss,
      unrealized_return_pct: Number(position.unrealized_gain_loss_pct) * 100,
    };
  });
  if (heatmap && window.Plotly) {
    renderPlotlyHeatmap(container, heatmap);
    return;
  }
  renderHtmlHeatmap(container, holdings);
}

function renderOptimization() {
  const result = appState.optimization;
  if (!result) {
    $("#optimization-results").innerHTML = `<div class="activity-item"><strong>No optimization run</strong><span>Select an objective to produce target weights.</span></div>`;
    return;
  }
  const table = document.createElement("div");
  renderTable(table, ["Ticker", "Current", "Target", "Delta"], result.allocations.map((item) => [
    item.symbol,
    pct(item.current_weight),
    pct(item.target_weight),
    signedMoney(item.trade_value_delta),
  ]));
  $("#optimization-results").innerHTML = `
    <div class="activity-item"><strong>${escapeHtml(result.objective)}</strong><span>${escapeHtml((result.notes || []).join(" "))}</span></div>
    ${table.innerHTML}`;
}

function renderSimulation() {
  const simple = appState.simpleImpact;
  $("#simple-impact-result").innerHTML = simple ? [
    resultItem("Notional", money(simple.notional)),
    resultItem("Fees", money(simple.estimated_fees)),
    resultItem("Slippage", money(simple.estimated_slippage)),
    resultItem("Cash Delta", signedMoney(simple.cash_delta)),
    resultItem("Post Equity", money(simple.post_trade_equity)),
    resultItem("Resulting Weight", pct(simple.resulting_weight)),
  ].join("") : `<div class="activity-item"><strong>No impact simulation</strong><span>Run a trade scenario.</span></div>`;

  const risk = appState.riskSimulation;
  if (!risk) {
    $("#risk-simulation-result").innerHTML = `<div class="activity-item"><strong>No risk simulation</strong><span>Use covariance JSON or the generated default.</span></div>`;
    const covariance = $("#risk-simulation-form textarea[name='covariance']");
    if (appState.portfolio && !covariance.value) covariance.value = JSON.stringify(defaultCovariance(appState.portfolio), null, 2);
    return;
  }
  const contribution = risk.charts.component_risk_contribution_pct.map((item) => ({ label: item.ticker, value: item.after, display: pct(item.after) }));
  $("#risk-simulation-result").innerHTML = `
    <div class="result-grid">
      ${resultItem("Before Vol", pct(risk.before_volatility))}
      ${resultItem("After Vol", pct(risk.after_volatility))}
      ${resultItem("Vol Delta", pct(risk.volatility_delta))}
    </div>
    <div class="bar-list">${barsHtml(contribution)}</div>`;
}

function renderMarket() {
  const quotes = appState.marketData?.quotes || [];
  renderTable($("#quotes-table"), ["Ticker", "Price", "Prev Close", "Daily", "Fetched"], quotes.map((quote) => [
    quote.ticker,
    money(quote.price),
    quote.previous_close == null ? "-" : money(quote.previous_close),
    quote.daily_return_pct == null ? "-" : pct(quote.daily_return_pct / 100),
    shortDateTime(quote.fetched_at),
  ]));
  const jobs = appState.portfolio?.background_jobs || [];
  $("#jobs-list").innerHTML = jobs.slice().reverse().map((job) => `
    <div class="activity-item">
      <strong>${escapeHtml(job.job_type)} - ${escapeHtml(job.status)}</strong>
      <span>${escapeHtml(job.message || "")}</span>
      <span>${shortDateTime(job.updated_at)}</span>
    </div>`).join("") || `<div class="activity-item"><strong>No jobs</strong><span>Queued tasks will appear here.</span></div>`;
}


function renderQuoteSnapshots() {
  renderQuoteSnapshot("#dashboard-quote-snapshot", "#dashboard-quote-status");
  renderQuoteSnapshot("#heatmap-quote-snapshot", "#heatmap-quote-status");
}

function renderQuoteSnapshot(containerSelector, statusSelector) {
  const container = $(containerSelector);
  const status = $(statusSelector);
  if (!container || !status) return;
  const portfolio = appState.portfolio;
  if (!portfolio || !(portfolio.positions || []).length) {
    container.innerHTML = `<div class="activity-item"><strong>No holdings</strong><span>No quote snapshot available.</span></div>`;
    status.textContent = "No holdings";
    status.className = "pill muted";
    return;
  }

  const rows = portfolio.positions.map(quoteSnapshotRow);
  const missing = rows.filter((row) => row.missingQuote).length;
  const latestFetched = latestQuoteFetchedAt(rows);
  status.textContent = missing ? `${missing} missing` : latestFetched ? `Fetched ${shortDateTime(latestFetched)}` : "No quotes";
  status.className = missing ? "pill muted" : "pill";
  container.innerHTML = rows.map(quoteCard).join("");
}

function quoteSnapshotRow(position) {
  const quote = quoteForTicker(position.ticker);
  const price = finiteNumber(quote?.price, position.current_price);
  const previousClose = finiteNumber(quote?.previous_close, null);
  const quantity = finiteNumber(position.quantity, 0);
  const costBasis = finiteNumber(position.cost_basis, 0);
  const averageCost = finiteNumber(position.average_cost, quantity > 0 ? costBasis / quantity : null);
  const dayPct = quoteDailyReturnPct(quote);
  const dayDollar = Number.isFinite(previousClose) ? (price - previousClose) * quantity : null;
  const costPct = Number.isFinite(averageCost) && averageCost > 0 ? (price / averageCost) - 1 : null;
  const costDollar = costBasis > 0 ? (price * quantity) - costBasis : finiteNumber(position.unrealized_gain_loss, null);
  return { ticker: position.ticker, price, previousClose, dayPct, dayDollar, averageCost, costPct, costDollar, fetchedAt: quote?.fetched_at || null, missingQuote: !quote };
}

function quoteCard(row) {
  const dayClass = row.dayPct == null ? "muted-text" : row.dayPct >= 0 ? "good" : "bad";
  const costClass = row.costPct == null ? "muted-text" : row.costPct >= 0 ? "good" : "bad";
  return `<div class="quote-card ${row.missingQuote ? "missing" : ""}">
    <div class="quote-card-head"><strong>${escapeHtml(row.ticker)}</strong><span>${row.missingQuote ? "No live quote" : shortDateTime(row.fetchedAt)}</span></div>
    <div class="quote-price">${money(row.price)}</div>
    <div class="quote-metrics">
      <span>Prev ${row.previousClose == null ? "-" : money(row.previousClose)}</span>
      <span class="${dayClass}">Day ${row.dayPct == null ? "-" : signedPct(row.dayPct / 100)}</span>
      <span>Avg Cost ${row.averageCost == null ? "-" : money(row.averageCost)}</span>
      <span class="${costClass}">Cost ${row.costPct == null ? "-" : signedPct(row.costPct)}</span>
      <span class="${costClass}">P/L ${row.costDollar == null ? "-" : signedMoney(row.costDollar)}</span>
    </div>
  </div>`;
}

function latestQuoteFetchedAt(rows) {
  const times = rows.map((row) => row.fetchedAt ? new Date(row.fetchedAt).getTime() : NaN).filter(Number.isFinite);
  if (!times.length) return null;
  return new Date(Math.max(...times)).toISOString();
}

function pollLatestMarketRefresh() {
  const job = latestMarketRefreshJob();
  if (job) pollMarketRefresh(job.id);
}

function pollMarketRefresh(jobId, attempt = 0) {
  if (!jobId || attempt >= 30 || !appState.selectedPortfolioId) return;
  window.setTimeout(async () => {
    try {
      await refreshSelected(false);
      const job = latestMarketRefreshJob(jobId);
      if (job && ["pending", "running"].includes(job.status)) pollMarketRefresh(jobId, attempt + 1);
    } catch (error) {
      toast(error.message, true);
    }
  }, 2000);
}

function latestBackgroundJob(jobType, jobId = null) {
  const jobs = (appState.portfolio?.background_jobs || []).filter((job) => job.job_type === jobType);
  if (jobId) return jobs.find((job) => job.id === jobId) || null;
  return jobs.slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0] || null;
}

function latestMarketRefreshJob(jobId = null) {
  return latestBackgroundJob("refresh_market_data", jobId);
}

function quoteStateKey(marketData) {
  return (marketData?.quotes || []).map((quote) => `${quote.ticker}:${quote.price}:${quote.previous_close}:${quote.daily_return_pct}:${quote.fetched_at}`).sort().join("|");
}

function renderAccount() {
  if (!appState.user) return;
  $("#account-profile").innerHTML = [
    resultItem("Email", appState.user.email),
    resultItem("Verified", appState.demoMode ? "Demo session" : (appState.user.email_verified ? "Yes" : "No")),
    resultItem("Created", shortDate(appState.user.created_at)),
  ].join("");
  $("#request-verification").hidden = appState.demoMode;
  $("#verification-confirm-form").hidden = appState.demoMode;
  renderThemeControl();
}

function renderActivity() {
  const portfolio = appState.portfolio;
  const cash = (portfolio.cash_transactions || []).map((item) => ({
    date: item.occurred_at,
    title: item.transaction_type,
    value: signedMoney(item.cash_delta),
  }));
  const trades = (portfolio.trade_history || []).map((item) => ({
    date: item.occurred_at,
    title: `${item.side} ${item.ticker}`,
    value: `${fixed(item.quantity, 3)} @ ${money(item.price)}`,
  }));
  const entries = cash.concat(trades).sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 8);
  $("#activity-feed").innerHTML = entries.map((entry) => `
    <div class="activity-item"><strong>${escapeHtml(entry.title)}</strong><span>${escapeHtml(entry.value)}</span><span>${shortDate(entry.date)}</span></div>`).join("") || `<div class="activity-item"><strong>No activity</strong><span>Manual entries will appear here.</span></div>`;
}

function fillPortfolioForms() {
  const portfolio = appState.portfolio;
  if (!portfolio) return;
  const settingsForm = $("#settings-form");
  settingsForm.elements.risk_free_rate.value = portfolio.settings.risk_free_rate ?? "";
  settingsForm.elements.benchmark_symbols.value = selectedBenchmarks(portfolio).join(", ");
  settingsForm.elements.cash_target_pct.value = portfolio.settings.cash_target_pct ?? "";
  const riskToleranceForm = $("#risk-tolerance-form");
  const riskScore = portfolio.settings.risk_tolerance_score ?? 5;
  riskToleranceForm.elements.risk_tolerance_score.value = riskScore;
  riskToleranceForm.elements.bond_symbols.value = (portfolio.settings.bond_watchlist || []).join(", ");
  $("#bond-risk-score").value = riskScore;
  const optRf = $("#optimization-form").elements.risk_free_rate;
  if (!optRf.value) optRf.value = portfolio.settings.risk_free_rate ?? 0.02;
  const riskTickers = $("#risk-form").elements.tickers;
  if (!riskTickers.value) riskTickers.value = portfolio.positions.map((item) => item.ticker).join(", ");
  const strategyForm = $("#strategy-lab-form");
  const strategyTickers = strategyForm?.elements.tickers;
  if (strategyTickers && !strategyTickers.value) strategyTickers.value = portfolio.positions.map((item) => item.ticker).join(", ");
  const strategyOptionSymbol = strategyForm?.elements.options_symbol;
  if (strategyOptionSymbol && !strategyOptionSymbol.value) {
    strategyOptionSymbol.value = appState.relativisticBs?.symbol || portfolio.positions[0]?.ticker || "";
  }
}

function activateTab(tabId) {
  $$(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === tabId));
  $$(".page").forEach((page) => page.classList.toggle("active", page.id === tabId));
  if (tabId === "dashboard" && appState.portfolio) renderDashboard();
  if (tabId === "risk") renderRiskTolerance();
  if (tabId === "bonds") loadBondAssets({ autoRefresh: true });
  if (tabId === "relativistic-bs") renderRelativisticBS();
  if (tabId === "strategy-lab") renderStrategyLab();
  if (tabId === "heatmap" && !appState.heatmap) renderHeatmap();
  if (tabId === "simulate") renderSimulation();
}

function estimateAnalytics(portfolio) {
  return estimateHistoricalAnalytics(portfolio) || estimateModelAnalytics(portfolio);
}

function estimateHistoricalAnalytics(portfolio) {
  const history = activePerformanceHistory();
  if (!history) return null;
  const benchmarkSymbol = performanceBenchmarkSymbol(portfolio, history);
  if (!benchmarkSymbol) return null;

  const range = performanceWindow("year");
  const accountPoints = accountHistoricalPerformancePoints(portfolio, range, history);
  const benchmarkPrices = performanceHistoryByTicker(history).get(benchmarkSymbol) || [];
  if (!accountPoints?.length || benchmarkPrices.length < 2) return null;

  const accountReturns = dailyReturnMap(accountPoints);
  const benchmarkReturns = dailyReturnMap(benchmarkPrices.map((point) => ({ date: point.date, value: point.close })));
  const dates = Array.from(accountReturns.keys()).filter((date) => benchmarkReturns.has(date)).sort();
  if (dates.length < 20) return null;

  const account = dates.map((date) => accountReturns.get(date));
  const benchmark = dates.map((date) => benchmarkReturns.get(date));
  const volatility = sampleStdDev(account) * Math.sqrt(252);
  const benchmarkVariance = sampleVariance(benchmark);
  const beta = benchmarkVariance > 0 ? sampleCovariance(account, benchmark) / benchmarkVariance : 0;
  const expectedReturn = annualizedCompoundReturn(account);
  const benchmarkReturn = annualizedCompoundReturn(benchmark);
  const riskFree = finiteNumber(portfolio.settings?.risk_free_rate, 0.02);
  const alpha = expectedReturn - (riskFree + beta * (benchmarkReturn - riskFree));
  const sharpe = volatility > 0 ? (expectedReturn - riskFree) / volatility : 0;
  return {
    expectedReturn,
    beta,
    alpha,
    sharpe,
    volatility,
    source: "history",
    note: `Beta, volatility, and Sharpe use ${dates.length} aligned daily observations against ${benchmarkLabel(benchmarkSymbol)}.`,
  };
}

function estimateModelAnalytics(portfolio) {
  const total = Math.max(portfolio.totals.total_equity, 1);
  const riskFree = portfolio.settings.risk_free_rate ?? 0.02;
  let expectedReturn = (portfolio.totals.cash / total) * riskFree;
  let beta = 0;
  let volSquared = Math.pow((portfolio.totals.cash / total) * ASSET_MODEL.cash.vol, 2);
  portfolio.positions.forEach((position) => {
    const model = ASSET_MODEL[position.asset_class] || ASSET_MODEL.equity;
    const weight = position.market_value / total;
    expectedReturn += weight * model.return;
    beta += weight * model.beta;
    const riskVol = riskVolOverride(position.ticker) || model.vol;
    volSquared += Math.pow(weight * riskVol, 2);
  });
  const volatility = Math.sqrt(volSquared) * 1.18;
  const benchmarkReturn = benchmarkReturnEstimate(portfolio);
  const alpha = expectedReturn - (riskFree + beta * (benchmarkReturn - riskFree));
  const sharpe = volatility > 0 ? (expectedReturn - riskFree) / volatility : 0;
  return {
    expectedReturn,
    beta,
    alpha,
    sharpe,
    volatility,
    source: "fallback",
    note: "Historical analytics are still being cached. Beta and volatility currently use conservative asset-class estimates and will update automatically when enough daily history is available.",
  };
}

function performanceBenchmarkSymbol(portfolio, history) {
  const byTicker = performanceHistoryByTicker(history);
  const selected = selectedBenchmarks(portfolio);
  if (selected.includes("SPY") && byTicker.has("SPY")) return "SPY";
  return selected.find((symbol) => byTicker.has(symbol)) || null;
}

function dailyReturnMap(points) {
  const closingByDay = new Map();
  validChartPoints(points).sort((a, b) => a.date - b.date).forEach((point) => {
    closingByDay.set(point.date.toISOString().slice(0, 10), Number(point.value));
  });
  const closes = Array.from(closingByDay.entries()).sort(([left], [right]) => left.localeCompare(right));
  const returns = new Map();
  for (let index = 1; index < closes.length; index += 1) {
    const previous = closes[index - 1][1];
    const current = closes[index][1];
    if (Number.isFinite(previous) && previous > 0 && Number.isFinite(current)) returns.set(closes[index][0], current / previous - 1);
  }
  return returns;
}

function sampleVariance(values) {
  if (values.length < 2) return 0;
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  return values.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / (values.length - 1);
}

function sampleCovariance(left, right) {
  if (left.length !== right.length || left.length < 2) return 0;
  const leftMean = left.reduce((sum, value) => sum + value, 0) / left.length;
  const rightMean = right.reduce((sum, value) => sum + value, 0) / right.length;
  return left.reduce((sum, value, index) => sum + (value - leftMean) * (right[index] - rightMean), 0) / (left.length - 1);
}

function sampleStdDev(values) {
  return Math.sqrt(Math.max(sampleVariance(values), 0));
}

function annualizedCompoundReturn(values) {
  if (!values.length) return 0;
  const compound = values.reduce((total, value) => total * (1 + value), 1);
  if (!Number.isFinite(compound) || compound <= 0) return -1;
  return Math.pow(compound, 252 / values.length) - 1;
}

function riskVolOverride(ticker) {
  const points = appState.riskAnalysis?.charts?.risk?.volatility_by_ticker || [];
  const match = points.find((item) => item.label === ticker);
  return match?.value ? Number(match.value) * Math.sqrt(252) : null;
}

function benchmarkReturnEstimate(portfolio) {
  const symbols = portfolio.settings.benchmark_symbols || [];
  const quotes = appState.marketData?.quotes || [];
  const dailyReturns = symbols.map((symbol) => quotes.find((quote) => quote.ticker === symbol)?.daily_return_pct).filter((value) => Number.isFinite(value));
  if (dailyReturns.length) {
    return (dailyReturns.reduce((sum, value) => sum + value, 0) / dailyReturns.length / 100) * 252;
  }
  return 0.08;
}

function buildPerformanceSeries(portfolio) {
  const range = performanceWindow(appState.performanceRange);
  const history = activePerformanceHistory();
  const historicalAccount = accountHistoricalPerformancePoints(portfolio, range, history);
  const hasServerCoverage = Boolean(history?.coverage);
  const mayUseLocalFallback = range.name === "day" || !hasServerCoverage;
  const accountPoints = historicalAccount?.length
    ? historicalAccount
    : mayUseLocalFallback
      ? accountPerformancePoints(portfolio, range)
      : [];
  const coverageStart = history?.coverage?.effective_start ? new Date(history.coverage.effective_start) : null;
  const alignedStart = accountPoints[0]?.date || (Number.isFinite(coverageStart?.getTime()) ? coverageStart : range.start);
  const alignedRange = { ...range, start: alignedStart > range.start ? alignedStart : range.start };
  const series = [{ label: "Portfolio", color: SERIES_COLORS[0], points: accountPoints }];
  selectedBenchmarks(portfolio).forEach((symbol, index) => {
    series.push({
      label: benchmarkLabel(symbol),
      color: SERIES_COLORS[(index + 1) % SERIES_COLORS.length],
      points: benchmarkPoints(symbol, alignedRange, history),
    });
  });
  return series;
}

function strategyLabDefaultTickers(universe) {
  const portfolio = appState.portfolio;
  if (!portfolio) return [];
  if (universe === "options_symbol") {
    const symbol = String(appState.relativisticBs?.symbol || $("#relativistic-bs-symbol")?.value || "").trim().toUpperCase();
    return symbol ? [symbol] : (portfolio.positions || []).slice(0, 1).map((position) => position.ticker);
  }
  if (universe === "benchmarks") return selectedBenchmarks(portfolio);
  if (universe === "custom") return splitSymbols($("#strategy-lab-tickers")?.value || "");
  return (portfolio.positions || []).map((position) => position.ticker);
}

function strategyLabRequestedTickers(data) {
  const explicit = splitSymbols(data.tickers || "");
  return explicit.length ? explicit : strategyLabDefaultTickers(data.universe || "portfolio");
}

function strategyLabOptionSymbol(data, tickers) {
  const explicit = String(data.options_symbol || "").trim().toUpperCase();
  if (explicit) return explicit;
  const suiteSymbol = String(appState.relativisticBs?.symbol || $("#relativistic-bs-symbol")?.value || "").trim().toUpperCase();
  if (suiteSymbol) return suiteSymbol;
  return tickers[0] || "";
}

function strategyLabOverlayProfile(data, tickers) {
  const overlayType = data.options_overlay || "none";
  if (overlayType === "none") {
    return {
      active: false,
      type: "none",
      symbol: "",
      summaryLabel: "None",
      note: "No option overlay is applied.",
    };
  }

  const symbol = strategyLabOptionSymbol(data, tickers);
  const linkedIndex = tickers.indexOf(symbol);
  if (linkedIndex < 0) {
    return {
      active: false,
      type: overlayType,
      symbol,
      summaryLabel: "Not linked",
      error: `${symbol || "The option overlay symbol"} must be one of the selected strategy tickers.`,
    };
  }

  const side = overlayType === "covered_call" ? "call" : "put";
  const payload = appState.relativisticBs?.symbol === symbol ? appState.relativisticBs : null;
  const chain = payload?.option_chain || [];
  const liveSpot = finiteNumber(payload?.spot, currentPortfolioPrice(appState.portfolio, symbol));
  const fallbackVol = Math.max(0.08, finiteNumber(riskVolOverride(symbol), ASSET_MODEL[(appState.portfolio?.positions || []).find((position) => position.ticker === symbol)?.asset_class]?.vol || ASSET_MODEL.equity.vol));
  const rate = finiteNumber(payload?.parameters?.rate, finiteNumber(appState.portfolio?.settings?.risk_free_rate, 0.02));
  const fallbackTauYears = 30 / 365.25;

  if (Number.isFinite(liveSpot) && liveSpot > 0 && chain.length) {
    const chosen = strategyLabChainOverlayContract(chain, liveSpot, side);
    if (chosen) {
      const contract = chosen[side];
      const rawPremium = relbsNumericMarketPrice(contract);
      const strike = finiteNumber(chosen.strike, liveSpot);
      const sigma = Math.max(0.05, finiteNumber(contract.market_iv, finiteNumber(payload?.parameters?.sigma, fallbackVol)));
      const tauYears = Math.max(7 / 365.25, finiteNumber(payload?.parameters?.tau, fallbackTauYears));
      const modelPrice = strategyLabBlackScholesPrice(liveSpot, strike, rate, sigma, tauYears, side);
      const premium = Math.max(0.01, finiteNumber(rawPremium, modelPrice));
      const scale = modelPrice > 0 ? clamp(premium / modelPrice, 0.65, 1.6) : 1;
      const strikeRatio = strike / liveSpot;
      return {
        active: true,
        type: overlayType,
        symbol,
        linkedIndex,
        side,
        strikeRatio,
        strikeAtLoad: strike,
        loadedSpot: liveSpot,
        sigma,
        rate,
        tauYears,
        termDays: Math.max(7, Math.round(tauYears * 365.25)),
        premiumAtLoad: premium,
        scale,
        source: `Loaded ${relbsChainSource(payload?.chain_source)}`,
        summaryLabel: `${strategyLabOverlayLabel(overlayType)} on ${symbol}`,
        detailLabel: strategyLabOverlayDetailLabel(overlayType, strikeRatio),
        note: `${strategyLabOverlayLabel(overlayType)} uses the loaded Options Suite chain for ${symbol}, reprices the short option each observation, and rolls after roughly ${Math.max(7, Math.round(tauYears * 365.25))} days.`,
      };
    }
  }

  const modelSpot = Number.isFinite(liveSpot) && liveSpot > 0 ? liveSpot : 100;
  const strikeRatio = overlayType === "covered_call" ? 1.05 : 0.95;
  const strike = modelSpot * strikeRatio;
  const sigma = fallbackVol;
  const tauYears = fallbackTauYears;
  const premium = strategyLabBlackScholesPrice(modelSpot, strike, rate, sigma, tauYears, side);
  return {
    active: true,
    type: overlayType,
    symbol,
    linkedIndex,
    side,
    strikeRatio,
    strikeAtLoad: strike,
    loadedSpot: modelSpot,
    sigma,
    rate,
    tauYears,
    termDays: Math.max(7, Math.round(tauYears * 365.25)),
    premiumAtLoad: premium,
    scale: 1,
    source: "Model fallback",
    summaryLabel: `${strategyLabOverlayLabel(overlayType)} on ${symbol}`,
    detailLabel: strategyLabOverlayDetailLabel(overlayType, strikeRatio),
    note: `${strategyLabOverlayLabel(overlayType)} uses a modeled 30-day contract for ${symbol} because no matching Options Suite chain is loaded.`,
  };
}

function strategyLabChainOverlayContract(chain, spot, side) {
  if (!Array.isArray(chain) || !chain.length || !Number.isFinite(spot) || spot <= 0) return null;
  const sideRows = chain
    .map((row) => ({ row, price: relbsNumericMarketPrice(row?.[side]) }))
    .filter((item) => Number.isFinite(item.price) && item.price > 0 && Number.isFinite(item.row?.strike));
  if (!sideRows.length) return null;
  const preferred = sideRows
    .filter((item) => side === "call" ? item.row.strike >= spot : item.row.strike <= spot)
    .sort((left, right) => Math.abs(left.row.strike - spot) - Math.abs(right.row.strike - spot));
  return (preferred[0] || sideRows.sort((left, right) => Math.abs(left.row.strike - spot) - Math.abs(right.row.strike - spot))[0])?.row || null;
}

function strategyLabBlackScholesPrice(spot, strike, rate, sigma, tau, optionType) {
  const safeSpot = Math.max(finiteNumber(spot, 0), 0.0001);
  const safeStrike = Math.max(finiteNumber(strike, 0), 0.0001);
  const safeTau = Math.max(finiteNumber(tau, 0), 1 / 365.25);
  const safeSigma = Math.max(finiteNumber(sigma, 0), 0.01);
  const sqrtTau = Math.sqrt(safeTau);
  const d1 = (Math.log(safeSpot / safeStrike) + (rate + (safeSigma * safeSigma) / 2) * safeTau) / (safeSigma * sqrtTau);
  const d2 = d1 - safeSigma * sqrtTau;
  if (optionType === "put") {
    return (safeStrike * Math.exp(-rate * safeTau) * strategyLabNormalCdf(-d2)) - (safeSpot * strategyLabNormalCdf(-d1));
  }
  return (safeSpot * strategyLabNormalCdf(d1)) - (safeStrike * Math.exp(-rate * safeTau) * strategyLabNormalCdf(d2));
}

function strategyLabNormalCdf(value) {
  return 0.5 * (1 + strategyLabErf(value / Math.sqrt(2)));
}

function strategyLabErf(value) {
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

function strategyLabOverlayPremium(overlay, basePrice) {
  const strike = basePrice * overlay.strikeRatio;
  return Math.max(0, strategyLabBlackScholesPrice(basePrice, strike, overlay.rate, overlay.sigma, overlay.tauYears, overlay.side) * overlay.scale);
}

function strategyLabOverlayOptionValue(overlay, basePrice, currentPrice, elapsedDays) {
  const strike = basePrice * overlay.strikeRatio;
  const intrinsic = overlay.side === "call"
    ? Math.max(currentPrice - strike, 0)
    : Math.max(strike - currentPrice, 0);
  const remainingTau = Math.max(0, overlay.tauYears - (Math.max(0, elapsedDays) / 365.25));
  if (remainingTau <= 0) return intrinsic;
  const theoretical = strategyLabBlackScholesPrice(currentPrice, strike, overlay.rate, overlay.sigma, remainingTau, overlay.side) * overlay.scale;
  return Math.max(intrinsic, theoretical);
}

function strategyLabOverlayMultiplier(overlay, basePrice, currentPrice, elapsedDays) {
  if (!overlay?.active || basePrice <= 0) return currentPrice / Math.max(basePrice, 0.0001);
  const premium = strategyLabOverlayPremium(overlay, basePrice);
  const optionValue = strategyLabOverlayOptionValue(overlay, basePrice, currentPrice, elapsedDays);
  if (overlay.type === "covered_put") {
    return Math.max(0, (basePrice + premium - optionValue) / basePrice);
  }
  return Math.max(0, (currentPrice + premium - optionValue) / basePrice);
}

function strategyLabShouldRollOverlay(overlay, segmentStartDate, currentDate) {
  if (!overlay?.active || !segmentStartDate || !currentDate) return false;
  return (currentDate.getTime() - segmentStartDate.getTime()) >= overlay.termDays * 24 * 60 * 60 * 1000;
}

function buildStrategyLabResult(data, options) {
  const tickers = options.tickers;
  const rangeName = options.rangeName || "year";
  const range = performanceWindow(rangeName);
  const history = options.history;
  const capital = Math.max(1, numberValue(data.capital || 10000));
  const requestedMaxWeight = Math.max(0.05, Math.min(1, numberValue(data.max_weight || 0.35)));
  const maxWeight = Math.max(requestedMaxWeight, 1 / Math.max(tickers.length, 1));
  const priceData = strategyLabPriceData(tickers, history, range);
  const overlay = strategyLabOverlayProfile(data, tickers);
  if (overlay.error) throw new Error(overlay.error);
  const points = priceData.rows.length >= 2
    ? simulateStrategyLab(data, tickers, priceData.rows, capital, maxWeight, overlay)
    : [];
  const optionsContext = overlay.summaryLabel;
  const notes = strategyLabNotes(data, {
    tickers,
    rangeName,
    history,
    priceData,
    optionsContext,
    overlay,
    maxWeight,
    requestedMaxWeight,
  });
  const metrics = strategyLabMetrics(points, capital);
  const series = strategyLabSeries(points, range, history);
  return {
    tickers,
    rangeName,
    strategyType: data.strategy_type || "buy_hold",
    overlay,
    optionsContext,
    points,
    series,
    metrics,
    notes,
  };
}

function strategyLabPriceData(tickers, history, range) {
  const byTicker = performanceHistoryByTicker(history);
  const seriesByTicker = new Map();
  const missing = [];
  tickers.forEach((ticker) => {
    const direct = (byTicker.get(ticker) || [])
      .filter((point) => point.date >= range.start && point.date <= range.end && Number.isFinite(point.close) && point.close > 0)
      .map((point) => ({ date: point.date, close: point.close }));
    if (direct.length >= 2) {
      seriesByTicker.set(ticker, direct);
      return;
    }
    if (INDEX_ANNUAL_RETURNS[ticker]) {
      const fallback = benchmarkPoints(ticker, range, history)
        .map((point) => ({ date: point.date, close: point.value }))
        .filter((point) => Number.isFinite(point.close) && point.close > 0);
      if (fallback.length >= 2) {
        seriesByTicker.set(ticker, fallback);
        return;
      }
    }
    missing.push(ticker);
  });
  if (missing.length) return { rows: [], missing };

  const times = Array.from(new Set(Array.from(seriesByTicker.values()).flatMap((points) => points.map((point) => point.date.getTime()))))
    .filter((time) => time >= range.start.getTime() && time <= range.end.getTime())
    .sort((left, right) => left - right);
  const rows = times.map((time) => {
    const prices = tickers.map((ticker) => strategyLabPriceAt(seriesByTicker.get(ticker), time));
    return { date: new Date(time), prices };
  }).filter((row) => row.prices.every((price) => Number.isFinite(price) && price > 0));
  return { rows, missing };
}

function strategyLabPriceAt(points, time) {
  if (!points?.length || time < points[0].date.getTime()) return null;
  let low = 0;
  let high = points.length - 1;
  let best = null;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    const pointTime = points[middle].date.getTime();
    if (pointTime <= time) {
      best = points[middle];
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return best?.close ?? null;
}

function simulateStrategyLab(data, tickers, rows, capital, maxWeight, overlay) {
  const strategyType = data.strategy_type || "buy_hold";
  const rebalance = strategyType === "buy_hold" ? "none" : (data.rebalance || "monthly");
  let segmentCapital = capital;
  let bases = rows[0].prices.slice();
  let segmentStartDate = rows[0].date;
  let weights = strategyType === "buy_hold"
    ? strategyLabInitialWeights(data.universe, tickers, maxWeight)
    : strategyLabEqualWeights(tickers.length, maxWeight);
  const points = [];

  rows.forEach((row, index) => {
    const rebalanceDue = index > 0 && shouldStrategyLabRebalance(rows[index - 1].date, row.date, rebalance);
    const overlayRollDue = index > 0 && strategyLabShouldRollOverlay(overlay, segmentStartDate, row.date);
    if (rebalanceDue || overlayRollDue) {
      segmentCapital = strategyLabSegmentValue(segmentCapital, weights, bases, row.prices, overlay, segmentStartDate, row.date);
      weights = strategyType === "momentum_tilt"
        ? strategyLabMomentumWeights(rows, index, maxWeight)
        : rebalanceDue
          ? strategyLabEqualWeights(tickers.length, maxWeight)
          : weights;
      bases = row.prices.slice();
      segmentStartDate = row.date;
    }
    const value = strategyLabSegmentValue(segmentCapital, weights, bases, row.prices, overlay, segmentStartDate, row.date);
    points.push({ date: row.date, value: (value / capital) * 100 });
  });
  return normalizePointsToWindow(points, { ...performanceWindow(data.strategy_range || "year"), start: rows[0].date });
}

function strategyLabSegmentValue(segmentCapital, weights, bases, prices, overlay, segmentStartDate, currentDate) {
  const elapsedDays = segmentStartDate && currentDate ? Math.max(0, (currentDate.getTime() - segmentStartDate.getTime()) / (24 * 60 * 60 * 1000)) : 0;
  const growth = weights.reduce((sum, weight, index) => {
    const base = bases[index] || prices[index] || 1;
    const currentPrice = prices[index];
    const multiplier = overlay?.active && overlay.linkedIndex === index
      ? strategyLabOverlayMultiplier(overlay, base, currentPrice, elapsedDays)
      : currentPrice / base;
    return sum + weight * multiplier;
  }, 0);
  return segmentCapital * growth;
}

function strategyLabInitialWeights(universe, tickers, maxWeight) {
  if (universe === "portfolio") {
    const positions = appState.portfolio?.positions || [];
    const scores = tickers.map((ticker) => finiteNumber(positions.find((position) => position.ticker === ticker)?.market_value, 0));
    if (scores.some((score) => score > 0)) return strategyLabWeightsFromScores(scores, maxWeight);
  }
  return strategyLabEqualWeights(tickers.length, maxWeight);
}

function strategyLabEqualWeights(count, maxWeight) {
  return strategyLabWeightsFromScores(Array.from({ length: count }, () => 1), maxWeight);
}

function strategyLabMomentumWeights(rows, index, maxWeight) {
  const lookback = Math.max(0, index - 20);
  const current = rows[index].prices;
  const previous = rows[lookback].prices;
  const scores = current.map((price, column) => Math.max(0, price / previous[column] - 1));
  return strategyLabWeightsFromScores(scores.some((score) => score > 0) ? scores : current.map(() => 1), maxWeight);
}

function strategyLabWeightsFromScores(scores, maxWeight) {
  const count = scores.length;
  if (!count) return [];
  const cap = Math.max(1 / count, Math.min(1, maxWeight));
  const cleanScores = scores.map((score) => Math.max(0, finiteNumber(score, 0)));
  const active = new Set(cleanScores.map((_, index) => index));
  const weights = Array(count).fill(0);
  let remaining = 1;

  for (let guard = 0; guard < count && active.size; guard += 1) {
    const activeScores = Array.from(active).map((index) => cleanScores[index]);
    const rawScoreSum = activeScores.reduce((sum, value) => sum + value, 0);
    const useEqual = rawScoreSum <= 0;
    const scoreSum = useEqual ? active.size : rawScoreSum;
    let cappedAny = false;
    active.forEach((index) => {
      const score = useEqual ? 1 : cleanScores[index];
      const proposed = remaining * score / scoreSum;
      if (proposed > cap) {
        weights[index] = cap;
        remaining -= cap;
        active.delete(index);
        cappedAny = true;
      }
    });
    if (!cappedAny) {
      active.forEach((index) => {
        const score = useEqual ? 1 : cleanScores[index];
        weights[index] = remaining * score / scoreSum;
      });
      active.clear();
    }
  }

  const total = weights.reduce((sum, value) => sum + value, 0);
  return total > 0 ? weights.map((weight) => weight / total) : Array.from({ length: count }, () => 1 / count);
}

function shouldStrategyLabRebalance(previousDate, currentDate, cadence) {
  if (cadence === "none") return false;
  if (cadence === "quarterly") {
    const previousQuarter = previousDate.getUTCFullYear() * 4 + Math.floor(previousDate.getUTCMonth() / 3);
    const currentQuarter = currentDate.getUTCFullYear() * 4 + Math.floor(currentDate.getUTCMonth() / 3);
    return currentQuarter !== previousQuarter;
  }
  return previousDate.getUTCFullYear() !== currentDate.getUTCFullYear() || previousDate.getUTCMonth() !== currentDate.getUTCMonth();
}

function strategyLabSeries(points, range, history) {
  const series = [];
  if (points.length >= 2) {
    series.push({ label: "Strategy", color: SERIES_COLORS[0], points });
  }
  const alignedRange = points[0] ? { ...range, start: points[0].date } : range;
  const portfolioPoints = appState.portfolio
    ? (accountHistoricalPerformancePoints(appState.portfolio, alignedRange, history) || accountPerformancePoints(appState.portfolio, alignedRange))
    : [];
  if (portfolioPoints?.length >= 2) {
    series.push({ label: "Portfolio", color: SERIES_COLORS[1], points: portfolioPoints });
  }
  selectedBenchmarks(appState.portfolio).slice(0, 2).forEach((symbol, index) => {
    const benchmark = benchmarkPoints(symbol, alignedRange, history);
    if (benchmark.length >= 2) {
      series.push({ label: benchmarkLabel(symbol), color: SERIES_COLORS[index + 2], points: benchmark });
    }
  });
  return series;
}

function strategyLabMetrics(points, capital) {
  if (points.length < 2) {
    return { returnPct: null, annualizedVolatility: 0, maxDrawdownPct: null, latestValue: capital, observations: 0 };
  }
  const latest = latestPoint(points);
  return {
    returnPct: lineReturnPct({ points }),
    annualizedVolatility: strategyLabAnnualizedVolatility(points),
    maxDrawdownPct: strategyLabMaxDrawdownPct(points),
    latestValue: latest ? capital * (latest.value / 100) : capital,
    observations: points.length,
  };
}

function strategyLabAnnualizedVolatility(points) {
  const sorted = validChartPoints(points).sort((left, right) => left.date - right.date);
  const returns = [];
  const gaps = [];
  for (let index = 1; index < sorted.length; index += 1) {
    const previous = sorted[index - 1];
    const current = sorted[index];
    if (previous.value > 0) returns.push(current.value / previous.value - 1);
    gaps.push(current.date.getTime() - previous.date.getTime());
  }
  if (returns.length < 2) return 0;
  const medianGap = gaps.sort((left, right) => left - right)[Math.floor(gaps.length / 2)] || 24 * 60 * 60 * 1000;
  const periodsPerYear = Math.max(1, Math.min(252, (365 * 24 * 60 * 60 * 1000) / medianGap));
  return sampleStdDev(returns) * Math.sqrt(periodsPerYear);
}

function strategyLabMaxDrawdownPct(points) {
  let peak = -Infinity;
  let drawdown = 0;
  validChartPoints(points).forEach((point) => {
    peak = Math.max(peak, point.value);
    if (peak > 0) drawdown = Math.min(drawdown, (point.value / peak - 1) * 100);
  });
  return drawdown;
}

function strategyLabNotes(data, context) {
  const notes = [];
  if (context.priceData.missing.length) {
    notes.push({
      title: "Missing history",
      body: `Cached history is not ready for ${context.priceData.missing.join(", ")}. Refresh market history from the dashboard or wait for the background job, then run again.`,
    });
  } else if (context.priceData.rows.length < 2) {
    notes.push({
      title: "Insufficient points",
      body: "The selected range does not have enough cached price points for the chosen symbols.",
    });
  } else {
    notes.push({
      title: "Data coverage",
      body: `Scenario uses ${context.priceData.rows.length} aligned cached observations over ${PERFORMANCE_RANGES[context.rangeName]?.label || context.rangeName}.`,
    });
  }
  if (context.requestedMaxWeight < context.maxWeight) {
    notes.push({
      title: "Weight cap adjusted",
      body: `The requested cap was below the feasible equal weight for ${context.tickers.length} symbols, so the lab used ${pct(context.maxWeight)}.`,
    });
  }
  notes.push({
    title: "Strategy logic",
    body: strategyLabStrategyDescription(data.strategy_type || "buy_hold"),
  });
  if (context.overlay?.active) {
    notes.push({
      title: "Options overlay",
      body: `${context.overlay.summaryLabel}. ${context.overlay.note} Source: ${context.overlay.source}.`,
    });
  } else if (data.options_overlay && data.options_overlay !== "none") {
    notes.push({
      title: "Options overlay",
      body: "No option overlay could be linked to the selected universe.",
    });
  }
  if (data.notes) {
    notes.push({ title: "Thesis", body: data.notes });
  }
  notes.push({
    title: "Isolation guard",
    body: "Runs in this lab do not alter portfolios, trades, lots, cash ledger, saved options snapshots, or optimization state.",
  });
  if (context.history?.coverage?.note) notes.push({ title: "Portfolio coverage", body: context.history.coverage.note });
  return notes;
}

function strategyLabStrategyLabel(value) {
  if (value === "equal_rebalance") return "Equal-weight rebalance";
  if (value === "momentum_tilt") return "Simple momentum tilt";
  return "Buy and hold";
}

function strategyLabStrategyDescription(value) {
  if (value === "equal_rebalance") {
    return "Equal-weight rebalance starts from an even split and resets back to equal weights on the selected cadence, which trims relative winners and adds to laggards.";
  }
  if (value === "momentum_tilt") {
    return "Momentum tilt reviews the latest twenty aligned observations at each rebalance date and pushes more weight toward the strongest recent performers, while the max-position cap prevents one name from taking over the whole test.";
  }
  return "Buy and hold uses the opening allocation once and then lets weights drift naturally with market performance, without scheduled resets.";
}

function strategyLabOverlayLabel(value) {
  if (value === "covered_call") return "Covered call";
  if (value === "covered_put") return "Covered put (cash-secured)";
  return "No overlay";
}

function strategyLabOverlayDetailLabel(type, strikeRatio) {
  if (type === "covered_put") return `${pct(1 - strikeRatio)} below spot strike`;
  return `${pct(strikeRatio - 1)} above spot strike`;
}

function selectedBenchmarks(portfolio) {
  const fromState = (appState.selectedBenchmarks || []).filter((symbol) => INDEX_ANNUAL_RETURNS[symbol]);
  if (fromState.length) return fromState;
  const fromSettings = (portfolio.settings?.benchmark_symbols || []).filter((symbol) => INDEX_ANNUAL_RETURNS[symbol]);
  return fromSettings.length ? fromSettings : ["SPY", "QQQ"];
}

function benchmarkLabel(symbol) {
  return MAJOR_INDEXES.find((index) => index.symbol === symbol)?.label || symbol;
}

function performanceWindow(rangeName) {
  const now = new Date();
  const option = PERFORMANCE_RANGES[rangeName] || PERFORMANCE_RANGES.max;
  let start;
  if (option.ytd) start = new Date(Date.UTC(now.getUTCFullYear(), 0, 1));
  else if (option.start) start = new Date(option.start);
  else start = new Date(now.getTime() - option.days * 24 * 60 * 60 * 1000);
  return { start, end: now, name: rangeName };
}

function accountPerformancePoints(portfolio, range) {
  if (range.name === "day") {
    const dailyReturn = portfolioDailyReturnFromCachedQuotes(portfolio);
    if (Number.isFinite(dailyReturn)) {
      return [
        { date: range.start, value: 100 },
        { date: range.end, value: 100 * (1 + dailyReturn) },
      ];
    }
  }

  const snapshots = (portfolio.valuation_snapshots || []).map((snapshot) => ({
    date: new Date(snapshot.as_of),
    value: snapshot.net_contributions ? (snapshot.total_equity / snapshot.net_contributions) * 100 : 100,
  })).filter((point) => Number.isFinite(point.value));

  if (!snapshots.length) {
    snapshots.push(...eventPerformancePoints(portfolio));
  }
  snapshots.sort((a, b) => a.date - b.date);

  const currentValue = portfolio.performance.net_contributions ? (portfolio.totals.total_equity / portfolio.performance.net_contributions) * 100 : 100;
  snapshots.push({ date: new Date(), value: currentValue });

  return normalizePointsToWindow(snapshots, range);
}

function accountHistoricalPerformancePoints(portfolio, range, history) {
  const backendPoints = (history?.portfolio_series || []).filter((point) => point.date >= range.start && point.date <= range.end);
  if (backendPoints.length >= 2) {
    return normalizePointsToWindow(backendPoints, { ...range, start: backendPoints[0].date });
  }
  if (history?.coverage) return null;
  const byTicker = performanceHistoryByTicker(history);
  const heldTickers = (portfolio.positions || []).map((position) => position.ticker).filter((ticker) => byTicker.has(ticker));
  if (!heldTickers.length) return null;

  const times = Array.from(new Set(heldTickers.flatMap((ticker) => (
    byTicker.get(ticker).filter((point) => point.date >= range.start && point.date <= range.end).map((point) => point.date.getTime())
  )))).sort((a, b) => a - b);
  if (times.length < 2) return null;

  const events = portfolioTimelineEvents(portfolio);
  const staticHoldings = new Map((portfolio.positions || []).map((position) => [position.ticker, finiteNumber(position.quantity, 0)]));
  const latestCash = finiteNumber(portfolio.totals?.cash, 0);
  const latestExternal = finiteNumber(portfolio.performance?.net_contributions, finiteNumber(portfolio.totals?.total_equity, 0));
  const useEventHoldings = tradeHistoryMatchesCurrentHoldings(events, staticHoldings);
  const firstEventTime = useEventHoldings ? (events[0]?.date?.getTime() || range.start.getTime()) : range.start.getTime();
  const effectiveStart = useEventHoldings ? new Date(Math.max(range.start.getTime(), firstEventTime)) : range.start;

  let cash = 0;
  let external = 0;
  let eventIndex = 0;
  const holdings = new Map();
  const rawPoints = [];

  times.forEach((time) => {
    if (events.length) {
      while (eventIndex < events.length && events[eventIndex].date.getTime() <= time) {
        const event = events[eventIndex];
        if (event.type === "cash") {
          cash += finiteNumber(event.cash_delta, 0);
          external += finiteNumber(event.external_flow, 0);
        } else {
          cash += finiteNumber(event.cash_delta, 0);
          const quantity = finiteNumber(holdings.get(event.ticker), 0);
          holdings.set(event.ticker, Math.max(0, quantity + (event.side === "buy" ? finiteNumber(event.quantity, 0) : -finiteNumber(event.quantity, 0))));
        }
        eventIndex += 1;
      }
    }
    const activeHoldings = useEventHoldings ? holdings : staticHoldings;
    const accountCash = useEventHoldings ? cash : latestCash;
    const contributions = useEventHoldings ? external : latestExternal;
    const equity = accountCash + Array.from(activeHoldings.entries()).reduce((sum, [ticker, quantity]) => {
      if (!quantity) return sum;
      const price = historicalPriceAt(byTicker.get(ticker) || [], time) ?? currentPortfolioPrice(portfolio, ticker);
      return sum + quantity * finiteNumber(price, 0);
    }, 0);
    const denominator = contributions || latestExternal || equity;
    if (denominator > 0 && time >= effectiveStart.getTime()) {
      rawPoints.push({ date: new Date(time), value: (equity / denominator) * 100 });
    }
  });

  if (rawPoints.length < 2) return null;
  return normalizePointsToWindow(rawPoints, { ...range, start: effectiveStart });
}

function tradeHistoryMatchesCurrentHoldings(events, staticHoldings) {
  const tradeEvents = events.filter((event) => event.type === "trade");
  if (!tradeEvents.length) return false;
  const eventHoldings = new Map();
  tradeEvents.forEach((event) => {
    const quantity = finiteNumber(eventHoldings.get(event.ticker), 0);
    eventHoldings.set(event.ticker, Math.max(0, quantity + (event.side === "buy" ? finiteNumber(event.quantity, 0) : -finiteNumber(event.quantity, 0))));
  });
  const tickers = new Set([...eventHoldings.keys(), ...staticHoldings.keys()]);
  return Array.from(tickers).every((ticker) => Math.abs(finiteNumber(eventHoldings.get(ticker), 0) - finiteNumber(staticHoldings.get(ticker), 0)) < 0.0001);
}

function performanceHistoryByTicker(history) {
  const byTicker = new Map();
  (history?.series || []).forEach((line) => {
    const ticker = String(line.ticker || "").toUpperCase();
    const points = (line.points || []).filter((point) => point.date instanceof Date && Number.isFinite(point.date.getTime()) && Number.isFinite(point.close));
    if (ticker && points.length) byTicker.set(ticker, points.sort((a, b) => a.date - b.date));
  });
  return byTicker;
}

function buildRiskPriceRowsFromHistory(tickers, history, rangeName) {
  const byTicker = performanceHistoryByTicker(history);
  const missing = tickers.filter((ticker) => !byTicker.has(ticker));
  if (missing.length) throw new Error(`Market history is not ready for ${missing.join(", ")}.`);

  const range = performanceWindow(rangeName || "year");
  const closeByTicker = new Map(tickers.map((ticker) => [
    ticker,
    dailyCloseByDate((byTicker.get(ticker) || []).filter((point) => point.date >= range.start && point.date <= range.end)),
  ]));
  const firstTickerDates = Array.from(closeByTicker.get(tickers[0])?.keys() || []);
  const sharedDates = firstTickerDates.filter((dateKey) => tickers.every((ticker) => closeByTicker.get(ticker)?.has(dateKey))).sort();
  const rows = sharedDates.map((dateKey) => tickers.map((ticker) => closeByTicker.get(ticker).get(dateKey)))
    .filter((row) => row.every((value) => Number.isFinite(value) && value > 0));
  return thinRows(rows, 750);
}

function dailyCloseByDate(points) {
  const closes = new Map();
  points.forEach((point) => {
    if (Number.isFinite(point.close)) closes.set(point.date.toISOString().slice(0, 10), point.close);
  });
  return closes;
}

function thinRows(rows, maxRows) {
  if (rows.length <= maxRows) return rows;
  const stride = Math.ceil(rows.length / maxRows);
  return rows.filter((_, index) => index % stride === 0 || index === rows.length - 1);
}

function riskSummary(risk) {
  const tickers = risk.covariance?.tickers || [];
  const values = risk.covariance?.values || [];
  const portfolio = appState.portfolio;
  const totalMarketValue = Math.max(finiteNumber(portfolio?.totals?.market_value, 0), 0);
  const weights = tickers.map((ticker) => {
    const position = (portfolio?.positions || []).find((item) => item.ticker === ticker);
    return totalMarketValue > 0 ? finiteNumber(position?.market_value, 0) / totalMarketValue : 1 / Math.max(tickers.length, 1);
  });
  let variance = 0;
  values.forEach((row, i) => row.forEach((value, j) => {
    variance += finiteNumber(value, 0) * finiteNumber(weights[i], 0) * finiteNumber(weights[j], 0);
  }));

  const volRows = risk.volatility_by_ticker || [];
  const highest = volRows.reduce((best, row) => (finiteNumber(row.value, 0) > finiteNumber(best.value, -Infinity) ? row : best), { label: "--", value: 0 });
  const correlations = [];
  let strongest = { label: "--", value: 0 };
  (risk.correlation?.values || []).forEach((row, i) => row.forEach((value, j) => {
    if (j <= i) return;
    const clean = finiteNumber(value, 0);
    correlations.push(clean);
    if (Math.abs(clean) > Math.abs(strongest.value)) strongest = { label: `${risk.correlation.tickers[i]} / ${risk.correlation.tickers[j]} ${fixed(clean, 2)}`, value: clean };
  }));
  const averageCorrelation = correlations.length ? correlations.reduce((sum, value) => sum + value, 0) / correlations.length : 0;
  const annualization = finiteNumber(risk.annualization_factor, 252);
  return {
    portfolioVolatility: Math.sqrt(Math.max(variance, 0)),
    highestVolatilityLabel: `${highest.label || "--"} ${pct(finiteNumber(highest.value, 0) * Math.sqrt(annualization))}`,
    averageCorrelation,
    strongestPairLabel: strongest.label,
  };
}

function riskCorrelationThreshold() {
  return Math.max(0, Math.min(0.9, finiteNumber($("#risk-correlation-threshold")?.value, 0.2)));
}

function minimumPairwiseObservations(matrix) {
  const values = matrix?.values || [];
  if (!values.length) return 0;
  const offDiagonal = [];
  values.forEach((row, rowIndex) => row.forEach((value, columnIndex) => {
    if (rowIndex !== columnIndex) offDiagonal.push(Math.max(0, Math.round(finiteNumber(value, 0))));
  }));
  if (offDiagonal.length) return Math.min(...offDiagonal);
  return Math.max(0, Math.round(finiteNumber(values[0]?.[0], 0)));
}

function correlationInsightsHtml(matrix, threshold) {
  if (!matrix?.values?.length) return `<div class="activity-item"><strong>No pair scan</strong><span>Correlation pairs will appear after risk analysis.</span></div>`;
  const pairs = [];
  matrix.values.forEach((row, rowIndex) => row.forEach((value, columnIndex) => {
    if (columnIndex <= rowIndex) return;
    const correlation = finiteNumber(value, 0);
    if (Math.abs(correlation) < threshold) return;
    pairs.push({
      left: matrix.tickers[rowIndex],
      right: matrix.tickers[columnIndex],
      value: correlation,
    });
  }));
  pairs.sort((left, right) => Math.abs(right.value) - Math.abs(left.value));
  if (!pairs.length) return `<div class="activity-item"><strong>No pairs above ${threshold.toFixed(2)}</strong><span>Lower the temperature threshold to reveal weaker relationships.</span></div>`;
  return pairs.slice(0, 10).map((pair) => `
    <div class="correlation-pair">
      <strong>${escapeHtml(pair.left)} / ${escapeHtml(pair.right)}</strong>
      <span class="${pair.value >= 0 ? "positive" : "negative"}">${pair.value >= 0 ? "+" : ""}${pair.value.toFixed(2)}</span>
    </div>`).join("");
}


function historicalPriceAt(points, time) {
  if (!points?.length) return null;
  let low = 0;
  let high = points.length - 1;
  let best = null;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    const pointTime = points[middle].date.getTime();
    if (pointTime <= time) {
      best = points[middle];
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return best?.close ?? points[0]?.close ?? null;
}

function currentPortfolioPrice(portfolio, ticker) {
  const position = (portfolio.positions || []).find((item) => item.ticker === ticker);
  return finiteNumber(quoteForTicker(ticker)?.price, finiteNumber(position?.current_price, null));
}

function portfolioTimelineEvents(portfolio) {
  const events = [];
  (portfolio.cash_transactions || []).forEach((item) => events.push({ type: "cash", date: new Date(item.occurred_at), ...item }));
  (portfolio.trade_history || []).forEach((item) => events.push({ type: "trade", date: new Date(item.occurred_at), ...item }));
  return events.filter((event) => Number.isFinite(event.date.getTime())).sort((a, b) => a.date - b.date);
}

function portfolioDailyReturnFromCachedQuotes(portfolio) {
  const positions = portfolio.positions || [];
  const totalMarketValue = positions.reduce((sum, position) => sum + (Number(position.market_value) || 0), 0);
  if (!totalMarketValue) return null;

  let weightedReturn = 0;
  let coveredValue = 0;
  positions.forEach((position) => {
    const quoteReturn = quoteDailyReturnPct(quoteForTicker(position.ticker));
    if (!Number.isFinite(quoteReturn)) return;
    const marketValue = Number(position.market_value) || 0;
    weightedReturn += (marketValue / totalMarketValue) * (quoteReturn / 100);
    coveredValue += marketValue;
  });

  return coveredValue > 0 ? weightedReturn : null;
}

function eventPerformancePoints(portfolio) {
  const events = portfolioTimelineEvents(portfolio);

  let cash = 0;
  let external = 0;
  const holdings = new Map();
  const prices = new Map();
  const points = [];

  events.forEach((event) => {
    if (event.type === "cash") {
      cash += event.cash_delta;
      external += event.external_flow;
    } else {
      cash += event.cash_delta;
      const quantity = holdings.get(event.ticker) || 0;
      holdings.set(event.ticker, Math.max(0, quantity + (event.side === "buy" ? event.quantity : -event.quantity)));
      prices.set(event.ticker, event.price);
    }
    const equity = cash + Array.from(holdings.entries()).reduce((sum, [ticker, quantity]) => sum + quantity * (prices.get(ticker) || 0), 0);
    points.push({ date: new Date(event.occurred_at), value: external ? (equity / external) * 100 : 100 });
  });
  return points;
}

function normalizePointsToWindow(points, range) {
  const sorted = points.filter((point) => point.date <= range.end).sort((a, b) => a.date - b.date);
  const beforeStart = [...sorted].reverse().find((point) => point.date <= range.start);
  const inside = sorted.filter((point) => point.date >= range.start && point.date <= range.end);
  const seed = beforeStart || inside[0] || { date: range.start, value: 100 };
  const windowPoints = [{ date: range.start, value: seed.value }, ...inside];
  const last = windowPoints[windowPoints.length - 1] || seed;
  if (last.date.getTime() < range.end.getTime()) {
    windowPoints.push({ date: range.end, value: last.value });
  }
  const base = windowPoints[0]?.value || 100;
  return windowPoints.map((point) => ({
    date: point.date,
    value: base ? (point.value / base) * 100 : 100,
  }));
}

function benchmarkPoints(symbol, range, history) {
  const historyPoints = performanceHistoryByTicker(history).get(symbol);
  if (historyPoints?.length) {
    const points = historyPoints.map((point) => ({ date: point.date, value: point.close }));
    return normalizePointsToWindow(points, range);
  }
  if (range.name === "day") {
    const quoteReturn = quoteDailyReturnPct(quoteForTicker(symbol));
    const move = Number.isFinite(quoteReturn) ? quoteReturn / 100 : 0;
    return [{ date: range.start, value: 100 }, { date: range.end, value: 100 * (1 + move) }];
  }

  const annual = INDEX_ANNUAL_RETURNS[symbol] || INDEX_ANNUAL_RETURNS.SPY;
  const points = benchmarkAnchorPoints(annual, symbol);
  return normalizePointsToWindow(points, range);
}

function benchmarkAnchorPoints(annualReturns, symbol) {
  const points = [];
  let value = 100;
  const now = new Date();
  annualReturns.forEach(([year, annualReturn]) => {
    const months = year === now.getUTCFullYear() ? now.getUTCMonth() + 1 : 12;
    const monthly = Math.pow(1 + annualReturn, 1 / Math.max(months, 1)) - 1;
    for (let month = 0; month < months; month += 1) {
      const cycle = Math.sin((year * 12 + month + symbol.length) * 0.7) * 0.0025;
      value *= 1 + monthly + cycle;
      points.push({ date: new Date(Date.UTC(year, month, 1)), value });
    }
  });
  const latest = points[points.length - 1];
  if (latest && latest.date < new Date()) points.push({ date: new Date(), value: latest.value });
  return points;
}

function renderPerformanceOverview(series) {
  const summary = $("#performance-summary");
  const legend = $("#performance-legend");
  if (!summary || !legend) return;

  const account = series[0];
  const benchmarkLines = series.slice(1);
  const accountReturn = lineReturnPct(account);
  const bestBenchmark = benchmarkLines
    .map((line) => ({ line, value: lineReturnPct(line) }))
    .filter((item) => Number.isFinite(item.value))
    .sort((a, b) => b.value - a.value)[0];
  const history = activePerformanceHistory();
  const demoStart = appState.demoMode
    ? shortDate((appState.portfolio?.lots || []).reduce((earliest, lot) => (
      !earliest || new Date(lot.purchased_at) < new Date(earliest) ? lot.purchased_at : earliest
    ), null))
    : "--";
  const coverageStart = history?.coverage?.effective_start ? shortDate(history.coverage.effective_start) : demoStart;
  const label = PERFORMANCE_RANGES[appState.performanceRange]?.label || "Max";

  summary.innerHTML = [
    performanceStat("Portfolio return", Number.isFinite(accountReturn) ? formatReturnAxis(accountReturn) : "--", returnClass(accountReturn)),
    performanceStat("Coverage start", coverageStart),
    performanceStat("Range", label),
    performanceStat("Best benchmark", bestBenchmark ? `${escapeHtml(bestBenchmark.line.label)} ${formatReturnAxis(bestBenchmark.value)}` : "None", bestBenchmark ? returnClass(bestBenchmark.value) : ""),
  ].join("");
  $("#performance-coverage-note").textContent = appState.demoMode
    ? "Demo history is preloaded locally from dated trades and benchmark price paths, so visitors can zoom, compare, and place temporary demo trades without touching the backend."
    : history?.coverage?.note || "Long-range coverage improves as dated lots, trades, cash movements, and cached market prices accumulate.";

  legend.innerHTML = series.map((line, index) => {
    const value = lineReturnPct(line);
    const dash = index === 0 ? "" : " dashed";
    return `<div class="legend-item"><span class="legend-swatch${dash}" style="--series-color:${escapeHtml(line.color)}"></span><span>${escapeHtml(line.label)}</span><strong class="${returnClass(value)}">${Number.isFinite(value) ? formatReturnAxis(value) : "--"}</strong></div>`;
  }).join("");
}

function performanceStat(label, value, className = "") {
  return `<div class="performance-stat"><span>${escapeHtml(label)}</span><strong class="${escapeHtml(className)}">${value}</strong></div>`;
}

function drawPerformanceChart(canvas, series) {
  if (!canvas) return;
  bindPerformanceChartEvents(canvas);
  canvas._performanceSeries = series;

  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(480, rect.width) * dpr;
  canvas.height = Math.max(360, rect.height) * dpr;
  const width = canvas.width / dpr;
  const height = canvas.height / dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const padding = { left: 20, right: 76, top: 30, bottom: 58 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const plotBottom = padding.top + plotHeight;
  const plotRight = width - padding.right;
  const allPoints = series.flatMap((item) => item.points || []).filter((point) => point.date instanceof Date && Number.isFinite(point.date.getTime()) && Number.isFinite(normalizedReturnPct(point)));
  const tooltip = $("#performance-tooltip");
  if (!allPoints.length) {
    const theme = chartTheme();
    hidePerformanceTooltip(tooltip);
    ctx.fillStyle = theme.muted;
    ctx.font = "13px system-ui";
    ctx.fillText("No performance data", padding.left, height / 2);
    drawChartAxisLabels(ctx, width, height, padding, appState.performanceRange);
    return;
  }

  const dateValues = allPoints.map((point) => point.date.getTime());
  const fullMinDate = Math.min(...dateValues);
  const fullMaxDate = Math.max(...dateValues, fullMinDate + 1);
  const visibleWindow = performanceVisibleWindow(fullMinDate, fullMaxDate);
  const minDate = visibleWindow.start;
  const maxDate = visibleWindow.end;
  const granularity = dateGranularityForSpan(maxDate - minDate);
  const displaySeries = series.map((line) => ({
    ...line,
    points: chartDisplayPoints(line.points || [], minDate, maxDate, plotWidth),
  }));
  const visiblePoints = displaySeries.flatMap((item) => item.points || []).filter((point) => point.date instanceof Date && Number.isFinite(point.date.getTime()) && Number.isFinite(normalizedReturnPct(point)));
  const plottedPoints = visiblePoints.length ? visiblePoints : allPoints;
  const rawValues = plottedPoints.map((point) => normalizedReturnPct(point));
  const yTicks = niceReturnTicks(Math.min(...rawValues), Math.max(...rawValues), 7);
  const yMin = yTicks[0];
  const yMax = yTicks[yTicks.length - 1];

  const xAxis = createPerformanceXScale(visiblePoints, minDate, maxDate, padding.left, plotWidth, granularity);
  const xScale = xAxis.scale;
  const yScale = (value) => padding.top + ((yMax - value) / (yMax - yMin || 1)) * plotHeight;

  canvas._performanceChart = { minDate, maxDate, fullMinDate, fullMaxDate, padding, plotRight, plotBottom, xUnscale: xAxis.unscale };
  drawPerformanceGrid(ctx, width, height, padding, yTicks, yScale, minDate, maxDate, xScale, granularity, xAxis.tickDates);

  displaySeries.forEach((line, index) => {
    const points = validChartPoints(line.points || []).sort((a, b) => a.date - b.date);
    if (!points.length) return;
    const mapped = points.map((point) => ({ point, x: xScale(point.date), y: yScale(normalizedReturnPct(point)) }));

    if (index === 0 && mapped.length > 1) {
      const baseline = yMin <= 0 && yMax >= 0 ? yScale(0) : plotBottom;
      const gradient = ctx.createLinearGradient(0, padding.top, 0, plotBottom);
      gradient.addColorStop(0, "rgba(15, 118, 110, 0.18)");
      gradient.addColorStop(1, "rgba(15, 118, 110, 0.02)");
      ctx.beginPath();
      ctx.moveTo(mapped[0].x, baseline);
      mapped.forEach((item) => ctx.lineTo(item.x, item.y));
      ctx.lineTo(mapped[mapped.length - 1].x, baseline);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();
    }

    ctx.strokeStyle = line.color;
    ctx.lineWidth = index === 0 ? 2.8 : 2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.setLineDash(index === 0 ? [] : [5, 5]);
    ctx.beginPath();
    mapped.forEach((item, pointIndex) => {
      if (pointIndex === 0) ctx.moveTo(item.x, item.y);
      else ctx.lineTo(item.x, item.y);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    const last = mapped[mapped.length - 1];
    ctx.fillStyle = line.color;
    ctx.beginPath();
    ctx.arc(last.x, last.y, index === 0 ? 4 : 3, 0, Math.PI * 2);
    ctx.fill();
  });

  const resolution = effectivePerformanceResolution(appState.performanceRange, maxDate - minDate);
  drawChartAxisLabels(ctx, width, height, padding, appState.performanceRange, performanceResolutionLabel(resolution, Boolean(appState.performanceZoom)));
  drawPerformanceHover(ctx, canvas, displaySeries, { minDate, maxDate, xScale, xUnscale: xAxis.unscale, yScale, padding, plotRight, plotBottom, yMin, yMax, granularity });
}

function drawStrategyLabChart(canvas, series, rangeName) {
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(480, rect.width) * dpr;
  canvas.height = Math.max(340, rect.height) * dpr;
  const width = canvas.width / dpr;
  const height = canvas.height / dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const padding = { left: 20, right: 76, top: 30, bottom: 58 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const plotBottom = padding.top + plotHeight;
  const allPoints = series.flatMap((line) => line.points || [])
    .filter((point) => point.date instanceof Date && Number.isFinite(point.date.getTime()) && Number.isFinite(normalizedReturnPct(point)));
  if (!allPoints.length) {
    const theme = chartTheme();
    ctx.fillStyle = theme.muted;
    ctx.font = "13px system-ui";
    ctx.fillText("Run a strategy scenario to draw a return curve.", padding.left, height / 2);
    drawChartAxisLabels(ctx, width, height, padding, rangeName || "year", "strategy lab");
    return;
  }

  const minDate = Math.min(...allPoints.map((point) => point.date.getTime()));
  const maxDate = Math.max(...allPoints.map((point) => point.date.getTime()), minDate + 1);
  const granularity = dateGranularityForSpan(maxDate - minDate);
  const xScale = (date) => padding.left + ((date.getTime() - minDate) / (maxDate - minDate || 1)) * plotWidth;
  const displaySeries = series.map((line) => ({
    ...line,
    points: strategyLabDisplayPoints(line.points || [], plotWidth),
  }));
  const visiblePoints = displaySeries.flatMap((line) => line.points || [])
    .filter((point) => Number.isFinite(normalizedReturnPct(point)));
  const rawValues = visiblePoints.map((point) => normalizedReturnPct(point));
  const yTicks = niceReturnTicks(Math.min(...rawValues), Math.max(...rawValues), 7);
  const yMin = yTicks[0];
  const yMax = yTicks[yTicks.length - 1];
  const yScale = (value) => padding.top + ((yMax - value) / (yMax - yMin || 1)) * plotHeight;

  drawPerformanceGrid(ctx, width, height, padding, yTicks, yScale, minDate, maxDate, xScale, granularity);
  displaySeries.forEach((line, index) => {
    const points = validChartPoints(line.points || []).sort((left, right) => left.date - right.date);
    if (!points.length) return;
    ctx.strokeStyle = line.color || SERIES_COLORS[index % SERIES_COLORS.length];
    ctx.lineWidth = index === 0 ? 2.8 : 2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.setLineDash(index === 0 ? [] : [5, 5]);
    ctx.beginPath();
    points.forEach((point, pointIndex) => {
      const x = xScale(point.date);
      const y = yScale(normalizedReturnPct(point));
      if (pointIndex === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
    const last = points[points.length - 1];
    ctx.fillStyle = line.color || SERIES_COLORS[index % SERIES_COLORS.length];
    ctx.beginPath();
    ctx.arc(xScale(last.date), yScale(normalizedReturnPct(last)), index === 0 ? 4 : 3, 0, Math.PI * 2);
    ctx.fill();
  });
  drawChartAxisLabels(ctx, width, height, padding, rangeName || "year", "strategy lab");
}

function strategyLabDisplayPoints(points, plotWidth) {
  const sorted = validChartPoints(points).sort((left, right) => left.date - right.date);
  const maxPoints = Math.max(90, Math.floor(plotWidth * 1.4));
  if (sorted.length <= maxPoints) return sorted;
  const stride = Math.ceil(sorted.length / maxPoints);
  return sorted.filter((_, index) => index % stride === 0 || index === sorted.length - 1);
}

function bindPerformanceChartEvents(canvas) {
  if (canvas.dataset.performanceBound === "true") return;
  canvas.dataset.performanceBound = "true";
  canvas.addEventListener("mousemove", (event) => {
    if (canvas._performancePan) return;
    const rect = canvas.getBoundingClientRect();
    canvas._performanceHover = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    drawPerformanceChart(canvas, canvas._performanceSeries || []);
  });
  canvas.addEventListener("mouseleave", () => {
    if (canvas._performancePan) return;
    canvas._performanceHover = null;
    hidePerformanceTooltip($("#performance-tooltip"));
    drawPerformanceChart(canvas, canvas._performanceSeries || []);
  });
  canvas.addEventListener("wheel", (event) => {
    const chart = canvas._performanceChart;
    if (!chart) return;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    if (x < chart.padding.left || x > chart.plotRight) return;
    event.preventDefault();
    const ratio = (x - chart.padding.left) / (chart.plotRight - chart.padding.left || 1);
    const focus = chart.xUnscale ? chart.xUnscale(ratio) : chart.minDate + ratio * (chart.maxDate - chart.minDate);
    const span = chart.maxDate - chart.minDate;
    const factor = event.deltaY < 0 ? 0.72 : 1.35;
    const nextSpan = Math.max(minPerformanceZoomSpan(), Math.min(chart.fullMaxDate - chart.fullMinDate, span * factor));
    setPerformanceZoomWindow(focus - nextSpan * ratio, focus + nextSpan * (1 - ratio), chart.fullMinDate, chart.fullMaxDate);
    drawPerformanceChart(canvas, canvas._performanceSeries || []);
  }, { passive: false });
  canvas.addEventListener("mousedown", (event) => {
    const chart = canvas._performanceChart;
    if (!chart || event.button !== 0) return;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    if (x < chart.padding.left || x > chart.plotRight) return;
    canvas._performancePan = { startX: event.clientX, startMin: chart.minDate, startMax: chart.maxDate, chart };
    canvas.classList.add("is-panning");
  });
  window.addEventListener("mousemove", (event) => {
    const pan = canvas._performancePan;
    if (!pan) return;
    const pixels = pan.chart.plotRight - pan.chart.padding.left || 1;
    const span = pan.startMax - pan.startMin;
    const deltaMs = -((event.clientX - pan.startX) / pixels) * span;
    setPerformanceZoomWindow(pan.startMin + deltaMs, pan.startMax + deltaMs, pan.chart.fullMinDate, pan.chart.fullMaxDate);
    drawPerformanceChart(canvas, canvas._performanceSeries || []);
  });
  window.addEventListener("mouseup", () => {
    if (!canvas._performancePan) return;
    canvas._performancePan = null;
    canvas.classList.remove("is-panning");
  });
  canvas.addEventListener("dblclick", () => resetPerformanceZoom());
}

function performanceVisibleWindow(fullMinDate, fullMaxDate) {
  const zoom = appState.performanceZoom;
  if (!zoom || zoom.rangeName !== appState.performanceRange || !Number.isFinite(zoom.start) || !Number.isFinite(zoom.end)) {
    return { start: fullMinDate, end: fullMaxDate };
  }
  const fullSpan = Math.max(fullMaxDate - fullMinDate, 1);
  let start = Math.max(fullMinDate, Math.min(zoom.start, fullMaxDate - minPerformanceZoomSpan()));
  let end = Math.min(fullMaxDate, Math.max(zoom.end, start + minPerformanceZoomSpan()));
  if (end - start >= fullSpan * 0.995) return { start: fullMinDate, end: fullMaxDate };
  return { start, end };
}

function setPerformanceZoomWindow(start, end, fullMinDate, fullMaxDate) {
  const fullSpan = Math.max(fullMaxDate - fullMinDate, 1);
  const minSpan = Math.min(minPerformanceZoomSpan(), fullSpan);
  let nextStart = start;
  let nextEnd = end;
  if (nextEnd - nextStart < minSpan) {
    const middle = (nextStart + nextEnd) / 2;
    nextStart = middle - minSpan / 2;
    nextEnd = middle + minSpan / 2;
  }
  if (nextStart < fullMinDate) {
    nextEnd += fullMinDate - nextStart;
    nextStart = fullMinDate;
  }
  if (nextEnd > fullMaxDate) {
    nextStart -= nextEnd - fullMaxDate;
    nextEnd = fullMaxDate;
  }
  nextStart = Math.max(fullMinDate, nextStart);
  nextEnd = Math.min(fullMaxDate, nextEnd);
  if (nextEnd - nextStart >= fullSpan * 0.995) {
    appState.performanceZoom = null;
    maybeLoadPerformanceHistory();
    return;
  }
  appState.performanceZoom = { rangeName: appState.performanceRange, start: nextStart, end: nextEnd };
  maybeLoadPerformanceHistory();
}

function minPerformanceZoomSpan() {
  return 5 * 60 * 1000;
}

function chartDisplayPoints(points, minDate, maxDate, plotWidth) {
  const sorted = validChartPoints(points).sort((a, b) => a.date - b.date);
  if (!sorted.length) return [];
  const before = [...sorted].reverse().find((point) => point.date.getTime() < minDate);
  const inside = sorted.filter((point) => point.date.getTime() >= minDate && point.date.getTime() <= maxDate);
  const after = sorted.find((point) => point.date.getTime() > maxDate);
  const candidates = [];
  if (before) candidates.push({ ...before, date: new Date(minDate) });
  candidates.push(...inside);
  if (after) candidates.push({ ...after, date: new Date(maxDate) });
  return resamplePerformancePoints(candidates, minDate, maxDate, plotWidth);
}

function resamplePerformancePoints(points, minDate, maxDate, plotWidth) {
  const bucketMs = performanceBucketMs(maxDate - minDate);
  const shouldBucket = appState.performanceResolution !== "auto" || points.length > Math.max(120, plotWidth * 1.4);
  if (!bucketMs || !shouldBucket) return points;
  const buckets = new Map();
  points.forEach((point) => {
    const bucket = Math.floor((point.date.getTime() - minDate) / bucketMs);
    buckets.set(bucket, point);
  });
  const sampled = Array.from(buckets.values()).sort((a, b) => a.date - b.date);
  const first = points[0];
  const last = points[points.length - 1];
  if (sampled[0]?.date.getTime() !== first.date.getTime()) sampled.unshift(first);
  if (sampled.at(-1)?.date.getTime() !== last.date.getTime()) sampled.push(last);
  return sampled;
}

function performanceBucketMs(spanMs) {
  return effectivePerformanceResolution(appState.performanceRange, spanMs).bucketMs;
}

function createPerformanceXScale(points, minDate, maxDate, left, plotWidth, granularity) {
  const wallClock = {
    scale: (date) => left + ((date.getTime() - minDate) / (maxDate - minDate || 1)) * plotWidth,
    unscale: (ratio) => minDate + Math.max(0, Math.min(1, ratio)) * (maxDate - minDate),
    tickDates: null,
  };
  if (!["minute", "hour"].includes(granularity)) return wallClock;
  const timeline = Array.from(new Set(points
    .map((point) => point.date?.getTime())
    .filter((time) => Number.isFinite(time) && time >= minDate && time <= maxDate)))
    .sort((a, b) => a - b);
  if (timeline.length < 2) return wallClock;

  const indexAt = (time) => {
    if (time <= timeline[0]) return 0;
    if (time >= timeline.at(-1)) return timeline.length - 1;
    let low = 0;
    let high = timeline.length - 1;
    while (low + 1 < high) {
      const middle = Math.floor((low + high) / 2);
      if (timeline[middle] <= time) low = middle;
      else high = middle;
    }
    const span = timeline[high] - timeline[low] || 1;
    return low + (time - timeline[low]) / span;
  };
  return {
    scale: (date) => left + (indexAt(date.getTime()) / (timeline.length - 1)) * plotWidth,
    unscale: (ratio) => timeline[Math.round(Math.max(0, Math.min(1, ratio)) * (timeline.length - 1))],
    tickDates: evenlySpacedTradingTicks(timeline, 7),
  };
}

function evenlySpacedTradingTicks(timeline, count) {
  const last = timeline.length - 1;
  return Array.from(new Set(Array.from({ length: Math.min(count, timeline.length) }, (_, index) => {
    const ratio = count <= 1 ? 0 : index / (count - 1);
    return timeline[Math.round(ratio * last)];
  }))).map((time) => new Date(time));
}

function dateGranularityForSpan(spanMs) {
  const day = 24 * 60 * 60 * 1000;
  if (spanMs <= 2 * 60 * 60 * 1000) return "minute";
  if (spanMs <= 2 * day) return "hour";
  if (spanMs <= 45 * day) return "day";
  if (spanMs <= 400 * day) return "month";
  return "year";
}

function performanceResolutionLabel(resolution, zoomed) {
  return `${zoomed ? "zoom" : "view"}, ${resolution.label.toLowerCase()} points`;
}

function drawPerformanceGrid(ctx, width, height, padding, yTicks, yScale, minDate, maxDate, xScale, granularity, tickDates = null) {
  const theme = chartTheme();
  const plotHeight = height - padding.top - padding.bottom;
  const plotRight = width - padding.right;
  const plotBottom = padding.top + plotHeight;

  ctx.fillStyle = theme.plotBg;
  ctx.fillRect(padding.left, padding.top, plotRight - padding.left, plotHeight);

  ctx.font = "12px system-ui";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  yTicks.forEach((value) => {
    const y = yScale(value);
    ctx.strokeStyle = value === 0 ? theme.gridStrong : theme.gridLine;
    ctx.lineWidth = value === 0 ? 1.2 : 1;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(plotRight, y);
    ctx.stroke();
    ctx.fillStyle = theme.muted;
    ctx.fillText(formatReturnAxis(value), plotRight + 10, y);
  });

  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  (tickDates || buildDateTicks(new Date(minDate), new Date(maxDate), granularity)).forEach((date) => {
    const x = xScale(date);
    if (x < padding.left - 1 || x > plotRight + 1) return;
    ctx.strokeStyle = theme.gridLine;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, padding.top);
    ctx.lineTo(x, plotBottom);
    ctx.stroke();
    ctx.fillStyle = theme.muted;
    ctx.fillText(formatAxisDate(date, granularity), x, plotBottom + 13);
  });

  ctx.strokeStyle = theme.border;
  ctx.beginPath();
  ctx.moveTo(padding.left, plotBottom);
  ctx.lineTo(plotRight, plotBottom);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(plotRight, padding.top);
  ctx.lineTo(plotRight, plotBottom);
  ctx.stroke();
}

function drawPerformanceHover(ctx, canvas, series, chart) {
  const hover = canvas._performanceHover;
  const tooltip = $("#performance-tooltip");
  if (!hover || hover.x < chart.padding.left || hover.x > chart.plotRight || hover.y < chart.padding.top || hover.y > chart.plotBottom) {
    hidePerformanceTooltip(tooltip);
    return;
  }

  const hoverRatio = (hover.x - chart.padding.left) / (chart.plotRight - chart.padding.left || 1);
  const hoverTime = chart.xUnscale ? chart.xUnscale(hoverRatio) : chart.minDate + hoverRatio * (chart.maxDate - chart.minDate);
  const rows = series.map((line) => {
    const point = nearestPointByTime(validChartPoints(line.points || []), hoverTime);
    if (!point) return null;
    return { line, point, value: normalizedReturnPct(point), x: chart.xScale(point.date), y: chart.yScale(normalizedReturnPct(point)) };
  }).filter(Boolean);
  if (!rows.length) {
    hidePerformanceTooltip(tooltip);
    return;
  }

  const anchor = rows.reduce((best, item) => Math.abs(item.point.date.getTime() - hoverTime) < Math.abs(best.point.date.getTime() - hoverTime) ? item : best, rows[0]);
  ctx.strokeStyle = chartTheme().hoverLine;
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 4]);
  ctx.beginPath();
  ctx.moveTo(anchor.x, chart.padding.top);
  ctx.lineTo(anchor.x, chart.plotBottom);
  ctx.stroke();
  ctx.setLineDash([]);

  rows.forEach((item) => {
    ctx.fillStyle = chartTheme().plotBg;
    ctx.strokeStyle = item.line.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(item.x, item.y, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  });

  if (!tooltip) return;
  tooltip.hidden = false;
  tooltip.innerHTML = `<strong>${escapeHtml(formatTooltipDate(anchor.point.date, chart.granularity))}</strong>${rows.map((item) => `<div><span><i style="background:${escapeHtml(item.line.color)}"></i>${escapeHtml(item.line.label)}</span><b class="${returnClass(item.value)}">${formatReturnAxis(item.value)}</b></div>`).join("")}`;
  const left = Math.min(Math.max(anchor.x + 12, 8), canvas.clientWidth - 238);
  const top = Math.min(Math.max(chart.padding.top + 8, anchor.y - 24), canvas.clientHeight - 120);
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function hidePerformanceTooltip(tooltip) {
  if (tooltip) tooltip.hidden = true;
}

function validChartPoints(points) {
  return points.filter((point) => point.date instanceof Date && Number.isFinite(point.date.getTime()) && Number.isFinite(normalizedReturnPct(point)));
}

function latestPoint(points) {
  return validChartPoints(points).sort((a, b) => a.date - b.date).at(-1) || null;
}

function nearestPointByTime(points, time) {
  return points.reduce((best, point) => {
    if (!best) return point;
    return Math.abs(point.date.getTime() - time) < Math.abs(best.date.getTime() - time) ? point : best;
  }, null);
}

function lineReturnPct(line) {
  const latest = latestPoint(line?.points || []);
  return latest ? normalizedReturnPct(latest) : null;
}

function normalizedReturnPct(point) {
  return (Number(point.value) || 100) - 100;
}

function niceReturnTicks(minValue, maxValue, desiredCount = 6) {
  let min = Number.isFinite(minValue) ? minValue : -1;
  let max = Number.isFinite(maxValue) ? maxValue : 1;
  if (min === max) {
    min -= 1;
    max += 1;
  }
  min = Math.min(min, 0);
  max = Math.max(max, 0);
  const rawStep = Math.max((max - min) / Math.max(desiredCount - 1, 1), 0.01);
  const step = niceStep(rawStep);
  const niceMin = Math.floor(min / step) * step;
  const niceMax = Math.ceil(max / step) * step;
  const ticks = [];
  for (let value = niceMin; value <= niceMax + step / 2; value += step) {
    ticks.push(Number(value.toFixed(6)));
  }
  return ticks.length >= 2 ? ticks : [niceMin, niceMax];
}

function niceStep(rawStep) {
  const exponent = Math.floor(Math.log10(rawStep));
  const magnitude = Math.pow(10, exponent);
  const fraction = rawStep / magnitude;
  const niceFraction = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 2.5 ? 2.5 : fraction <= 5 ? 5 : 10;
  return niceFraction * magnitude;
}

function formatReturnAxis(value) {
  if (!Number.isFinite(value)) return "--";
  const abs = Math.abs(value);
  const digits = abs !== 0 && abs < 10 ? 1 : 0;
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

function returnClass(value) {
  if (!Number.isFinite(value) || value === 0) return "flat";
  return value > 0 ? "positive" : "negative";
}

function buildDateTicks(start, end, granularity) {
  const startMs = start.getTime();
  const endMs = end.getTime();
  const span = Math.max(endMs - startMs, 1);
  const maxTicks = 7;
  const step = dateTickStep(span, granularity);
  const ticks = [];
  let cursor = alignDateTick(start, step);
  if (cursor.getTime() < startMs) cursor = addDateTick(cursor, step);
  while (cursor.getTime() <= endMs && ticks.length < maxTicks + 2) {
    ticks.push(new Date(cursor));
    cursor = addDateTick(cursor, step);
  }
  if (!ticks.length || ticks[0].getTime() - startMs > span * 0.18) ticks.unshift(new Date(startMs));
  const last = ticks[ticks.length - 1];
  if (!last || endMs - last.getTime() > span * 0.18) ticks.push(new Date(endMs));
  return ticks.slice(0, maxTicks + 1);
}

function dateTickStep(spanMs, granularity) {
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (granularity === "minute") return { unit: "minute", count: spanMs <= 45 * minute ? 5 : 15 };
  if (granularity === "hour") return { unit: "hour", count: spanMs <= 12 * hour ? 2 : 6 };
  if (granularity === "day") return { unit: "day", count: spanMs <= 10 * day ? 1 : 7 };
  if (granularity === "month") return { unit: "month", count: spanMs <= 190 * day ? 1 : 3 };
  return { unit: "year", count: spanMs <= 4 * 365 * day ? 1 : 2 };
}

function alignDateTick(date, step) {
  const aligned = new Date(date);
  aligned.setUTCSeconds(0, 0);
  if (step.unit === "minute") {
    aligned.setUTCMinutes(Math.floor(aligned.getUTCMinutes() / step.count) * step.count, 0, 0);
  } else if (step.unit === "hour") {
    aligned.setUTCMinutes(0, 0, 0);
    aligned.setUTCHours(Math.floor(aligned.getUTCHours() / step.count) * step.count);
  } else if (step.unit === "day") {
    aligned.setUTCHours(0, 0, 0, 0);
    if (step.count > 1) {
      const day = aligned.getUTCDate();
      aligned.setUTCDate(day - ((day - 1) % step.count));
    }
  } else if (step.unit === "month") {
    aligned.setUTCHours(0, 0, 0, 0);
    aligned.setUTCDate(1);
    aligned.setUTCMonth(Math.floor(aligned.getUTCMonth() / step.count) * step.count);
  } else {
    aligned.setUTCHours(0, 0, 0, 0);
    aligned.setUTCMonth(0, 1);
    aligned.setUTCFullYear(aligned.getUTCFullYear() - (aligned.getUTCFullYear() % step.count));
  }
  return aligned;
}

function addDateTick(date, step) {
  const next = new Date(date);
  if (step.unit === "minute") next.setUTCMinutes(next.getUTCMinutes() + step.count);
  else if (step.unit === "hour") next.setUTCHours(next.getUTCHours() + step.count);
  else if (step.unit === "day") next.setUTCDate(next.getUTCDate() + step.count);
  else if (step.unit === "month") next.setUTCMonth(next.getUTCMonth() + step.count);
  else next.setUTCFullYear(next.getUTCFullYear() + step.count);
  return next;
}

function formatAxisDate(date, granularity) {
  if (["minute", "hour"].includes(granularity)) {
    return new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" }).format(date);
  }
  if (granularity === "day") {
    return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
  }
  if (granularity === "month") {
    return new Intl.DateTimeFormat("en-US", { month: "short", year: "2-digit" }).format(date);
  }
  return new Intl.DateTimeFormat("en-US", { year: "numeric" }).format(date);
}

function formatTooltipDate(date, granularity) {
  if (["minute", "hour"].includes(granularity)) {
    return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(date);
  }
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(date);
}

function drawChartAxisLabels(ctx, width, height, padding, rangeName, detail = "") {
  ctx.fillStyle = chartTheme().text;
  ctx.font = "12px system-ui";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText("Cumulative Return (%)", padding.left, 8);

  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  const label = PERFORMANCE_RANGES[rangeName]?.label || "Max";
  ctx.fillText(`Date (${label}${detail ? `, ${detail}` : ""})`, padding.left + (width - padding.left - padding.right) / 2, height - 8);
}

function renderTableHtml(container, headers, rows, rowClasses = []) {
  if (!rows.length) {
    container.innerHTML = `<div class="activity-item"><strong>No rows</strong><span>Data will appear here.</span></div>`;
    return;
  }
  container.innerHTML = `<table><thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead><tbody>${rows.map((row, index) => `<tr class="${escapeHtml(rowClasses[index] || "")}">${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function renderTable(container, headers, rows) {
  if (!rows.length) {
    container.innerHTML = `<div class="activity-item"><strong>No rows</strong><span>Data will appear here.</span></div>`;
    return;
  }
  container.innerHTML = `<table><thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function renderBars(container, rows) {
  container.innerHTML = barsHtml(rows) || `<div class="activity-item"><strong>No data</strong><span>Values will appear here.</span></div>`;
}

function barsHtml(rows) {
  const max = Math.max(...rows.map((row) => Math.abs(row.value)), 0.000001);
  return rows.map((row) => `
    <div class="bar-row">
      <div class="bar-meta"><span>${escapeHtml(row.label)}</span><span>${escapeHtml(row.display)}</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, Math.abs(row.value) / max * 100)}%"></div></div>
    </div>`).join("");
}

function renderMatrix(container, matrix, options = {}) {
  if (!container) return;
  if (!matrix?.values?.length) {
    container.innerHTML = `<div class="activity-item"><strong>No matrix</strong><span>Run risk analysis first.</span></div>`;
    return;
  }
  const transform = options.transform || ((value) => value);
  const formatter = options.formatter || ((value) => fixed(value, options.digits ?? 2));
  const values = matrix.values.map((row) => row.map((value) => transform(finiteNumber(value, 0))));
  const maxAbs = Math.max(...values.flat().map((value) => Math.abs(value)), 0.000001);
  const n = matrix.tickers.length;
  container.style.gridTemplateColumns = `repeat(${n + 1}, minmax(54px, 1fr))`;
  const header = [`<div></div>`].concat(matrix.tickers.map((ticker) => `<div class="matrix-label">${escapeHtml(ticker)}</div>`));
  const cells = [];
  values.forEach((row, r) => {
    cells.push(`<div class="matrix-label">${escapeHtml(matrix.tickers[r])}</div>`);
    row.forEach((value, c) => {
      const meta = {
        rowIndex: r,
        columnIndex: c,
        rowTicker: matrix.tickers[r],
        columnTicker: matrix.tickers[c],
        diagonal: r === c,
      };
      const colorValue = options.normalizeColor ? value / maxAbs : value;
      const background = options.color ? options.color(value, meta, maxAbs) : matrixColor(colorValue);
      const weak = options.hideWeakLabels && !meta.diagonal && Math.abs(value) < finiteNumber(options.threshold, 0);
      const display = weak ? "" : formatter(value, meta);
      const title = options.titleFormatter ? options.titleFormatter(value, meta) : `${meta.rowTicker} / ${meta.columnTicker}: ${formatter(value, meta)}`;
      cells.push(`<div class="matrix-cell${weak ? " weak" : ""}${meta.diagonal ? " diagonal" : ""}" style="background:${escapeHtml(background)}" title="${escapeHtml(title)}">${escapeHtml(display)}</div>`);
    });
  });
  container.innerHTML = header.concat(cells).join("");
}

function formatCovariance(value) {
  const numeric = finiteNumber(value, 0);
  return numeric !== 0 && Math.abs(numeric) < 0.0001 ? numeric.toExponential(2) : numeric.toFixed(4);
}

function renderHtmlHeatmap(container, holdings) {
  container.classList.add("fallback-heatmap");
  const sorted = [...(holdings || [])].sort((a, b) => finiteNumber(b.market_value, 0) - finiteNumber(a.market_value, 0));
  container.innerHTML = sorted.map(heatTile).join("") || `<div class="activity-item"><strong>No holdings</strong><span>Add lots or trades to populate the heatmap.</span></div>`;
}

function heatTile(node) {
  const weight = Math.max(0.1, finiteNumber(node.portfolio_weight_pct, 0.1));
  const marketValue = finiteNumber(node.market_value, 0);
  const dailyReturn = node.daily_return_pct == null ? null : Number(node.daily_return_pct);
  const unrealizedReturn = node.unrealized_return_pct == null ? null : Number(node.unrealized_return_pct);
  const dailyDisplay = Number.isFinite(dailyReturn) ? signedPct(dailyReturn / 100) : "Daily n/a";
  const returnDisplay = Number.isFinite(unrealizedReturn) ? signedPct(unrealizedReturn / 100) : "Return n/a";
  return `<div class="heat-tile" style="flex:${Math.max(1, marketValue)} 1 ${Math.max(96, weight * 10)}px;background:${returnColor(dailyReturn)}">
    <strong>${escapeHtml(node.label || node.ticker)}</strong>
    <span>${money(marketValue)} · ${fixed(weight, 2)}% weight</span>
    <span>Cost ${money(node.cost_basis)}</span>
    <span>${escapeHtml(dailyDisplay)} · ${escapeHtml(returnDisplay)}</span>
  </div>`;
}

function resultItem(label, value) {
  return `<div class="result-item"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function metricCard(label, value) {
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function defaultCovariance(portfolio) {
  const tickers = portfolio.positions.map((position) => position.ticker);
  const covariance = {};
  portfolio.positions.forEach((rowPosition) => {
    covariance[rowPosition.ticker] = {};
    portfolio.positions.forEach((colPosition) => {
      const rowVol = (ASSET_MODEL[rowPosition.asset_class] || ASSET_MODEL.equity).vol;
      const colVol = (ASSET_MODEL[colPosition.asset_class] || ASSET_MODEL.equity).vol;
      const corr = rowPosition.ticker === colPosition.ticker ? 1 : 0.35;
      covariance[rowPosition.ticker][colPosition.ticker] = rowVol * colVol * corr;
    });
  });
  return tickers.length ? covariance : { CASH: { CASH: 0.0001 } };
}

function resetManualForm(form, defaults = {}) {
  form.reset();
  Object.entries(defaults).forEach(([name, value]) => {
    if (form.elements[name]) form.elements[name].value = value;
  });
}


function renderPlotlyHeatmap(container, heatmap) {
  container.classList.remove("fallback-heatmap");
  container.innerHTML = "";
  const plot = document.createElement("div");
  plot.className = "plotly-heatmap";
  container.appendChild(plot);
  const theme = chartTheme();
  const trace = {
    ...heatmap.plotly,
    type: "treemap",
    marker: {
      colors: heatmap.plotly.colors,
      colorscale: heatmap.plotly.colorscale,
      cmid: 0,
      cmin: -5,
      cmax: 5,
      colorbar: { title: { text: "Daily %", font: { color: theme.text } }, tickfont: { color: theme.text } },
    },
    tiling: { packing: "squarify" },
  };
  const fallback = () => renderHtmlHeatmap(container, heatmap.holdings || []);
  try {
    const plotPromise = window.Plotly.newPlot(plot, [trace], {
      title: "Personal Portfolio Heatmap - Sized by Portfolio Weight",
      autosize: true,
      margin: { t: 60, l: 10, r: 10, b: 10 },
      paper_bgcolor: theme.surface,
      plot_bgcolor: theme.plotBg,
      font: { color: theme.text },
      hoverlabel: { bgcolor: theme.surface, bordercolor: theme.border, font: { color: theme.text } },
    }, { responsive: true, displayModeBar: false });
    if (plotPromise && typeof plotPromise.catch === "function") plotPromise.catch(fallback);
  } catch (error) {
    fallback();
  }
}

function formObject(form) {
  const object = {};
  new FormData(form).forEach((value, key) => {
    object[key] = typeof value === "string" ? value.trim() : value;
  });
  return object;
}

function basePortfolioPayload(form) {
  const payload = formObject(form);
  return {
    name: payload.name,
    base_currency: normalizeCurrency(payload.base_currency),
    cash: numberValue(payload.cash),
  };
}

function normalizeCurrency(value) {
  return String(value || "USD").trim().toUpperCase() || "USD";
}

async function finishPortfolioCreation(portfolioId, options = {}) {
  appState.selectedPortfolioId = portfolioId;
  localStorage.setItem("selected_portfolio_id", portfolioId);
  await loadWorkspace();
  if (options.tabId) activateTab(options.tabId);
}

function handleAddOnboardingLotRow() {
  appendOnboardingLotRow();
}

function handleOnboardingLotRowClick(event) {
  const target = event.target instanceof Element ? event.target : null;
  const button = target ? target.closest("button[data-onboarding-remove-row]") : null;
  if (!button) return;
  const rows = $$("#portfolio-onboarding-lot-rows tr");
  if (rows.length <= 1) {
    resetOnboardingLotRows(1);
    return;
  }
  button.closest("tr")?.remove();
}

function resetOnboardingLotRows(count = 3) {
  const body = $("#portfolio-onboarding-lot-rows");
  if (!body) return;
  appState.onboardingLotRowCounter = 0;
  body.innerHTML = "";
  Array.from({ length: count }, () => appendOnboardingLotRow());
}

function appendOnboardingLotRow(values = {}) {
  const body = $("#portfolio-onboarding-lot-rows");
  if (!body) return;
  appState.onboardingLotRowCounter += 1;
  body.insertAdjacentHTML("beforeend", onboardingLotRowHtml(appState.onboardingLotRowCounter, values));
  normalizeNumericInputs(body);
}

function onboardingLotRowHtml(rowId, values = {}) {
  return `
    <tr class="onboarding-lot-row" data-row-id="${rowId}">
      <td><input data-lot-field="ticker" placeholder="AAPL" value="${escapeHtml(values.ticker || "")}"></td>
      <td><input data-lot-field="quantity" type="number" min="0" step="0.0001" inputmode="decimal" placeholder="10" value="${escapeHtml(values.quantity || "")}"></td>
      <td><input data-lot-field="purchase_price" type="number" min="0" step="0.01" inputmode="decimal" placeholder="182.50" value="${escapeHtml(values.purchase_price || "")}"></td>
      <td><input data-lot-field="purchased_at" type="date" value="${escapeHtml(values.purchased_at || "")}"></td>
      <td><button class="icon-button" type="button" data-onboarding-remove-row="true" title="Remove row" aria-label="Remove starter lot row">-</button></td>
    </tr>`;
}

function readOnboardingLots(form) {
  const rows = $$("#portfolio-onboarding-lot-rows tr", form);
  const lots = [];
  rows.forEach((row) => {
    const ticker = row.querySelector('[data-lot-field="ticker"]')?.value?.trim().toUpperCase() || "";
    const quantityRaw = row.querySelector('[data-lot-field="quantity"]')?.value?.trim() || "";
    const purchasePriceRaw = row.querySelector('[data-lot-field="purchase_price"]')?.value?.trim() || "";
    const purchasedAt = row.querySelector('[data-lot-field="purchased_at"]')?.value?.trim() || "";
    const touched = Boolean(ticker || quantityRaw || purchasePriceRaw || purchasedAt);
    if (!touched) return;
    if (!ticker || !quantityRaw || !purchasePriceRaw) {
      throw new Error("Each starter lot row needs a ticker, share count, and cost per share, or it should be left blank.");
    }
    const lot = {
      ticker,
      quantity: numberValue(quantityRaw),
      purchase_price: numberValue(purchasePriceRaw),
      asset_class: "equity",
    };
    if (purchasedAt) lot.purchased_at = dateToIso(purchasedAt);
    lots.push(lot);
  });
  return lots;
}

function parsePriceRows(raw) {
  const rows = String(raw || "").split(/\n+/).map((line) => line.trim()).filter(Boolean);
  if (rows.length < 2) throw new Error("At least two price rows are required.");
  return rows.map((line) => line.split(/,|\t/).map((value) => {
    const parsed = Number(value.trim());
    if (!Number.isFinite(parsed)) throw new Error("Price rows must contain numbers only.");
    return parsed;
  }));
}

function splitSymbols(value) {
  return String(value || "").split(/,|\s+/).map((symbol) => symbol.trim().toUpperCase()).filter(Boolean).filter((symbol, index, list) => list.indexOf(symbol) === index);
}

function bondMonitoredTickers() {
  return (appState.bondAssets?.assets || []).filter((asset) => asset.monitored).map((asset) => asset.ticker);
}

function defaultBondRungs(strategyType) {
  return riskFitBondRungs(5, strategyType);
}

function riskFitBondRungs(riskScore, strategyType) {
  let terms;
  let weights;
  if (strategyType === "barbell") {
    if (riskScore <= 3) [terms, weights] = [[1, 7], [0.70, 0.30]];
    else if (riskScore <= 6) [terms, weights] = [[1, 10], [0.55, 0.45]];
    else [terms, weights] = [[2, 20], [0.35, 0.65]];
  } else {
    if (riskScore <= 3) terms = [1, 2, 3, 4, 5];
    else if (riskScore <= 6) terms = [1, 3, 5, 7, 10];
    else terms = [2, 5, 10, 15, 20];
    weights = terms.map(() => 1 / terms.length);
  }
  return terms.map((years, index) => ({
    label: `${years}-year rung`,
    years_to_maturity: years,
    coupon_rate: 0.04,
    yield_to_maturity: 0.04,
    market_price_pct: 100,
    face_value: 1000,
    allocation_weight: weights[index],
    payments_per_year: 2,
  }));
}

function bondRungsFromForm() {
  const rows = $$("#bond-rung-rows tr");
  if (!rows.length) throw new Error("Add at least one bond rung.");
  return rows.map((row, index) => {
    const value = (field) => row.querySelector(`[data-field="${field}"]`)?.value;
    return {
      label: value("label") || `Rung ${index + 1}`,
      allocation_weight: numberValue(value("allocation_weight")) / 100,
      face_value: 1000,
      market_price_pct: numberValue(value("market_price_pct")),
      coupon_rate: numberValue(value("coupon_rate")) / 100,
      yield_to_maturity: numberValue(value("yield_to_maturity")) / 100,
      years_to_maturity: numberValue(value("years_to_maturity")),
      payments_per_year: Math.round(numberValue(value("payments_per_year"))),
    };
  });
}

function numberValue(value) {
  const parsed = Number(value || 0);
  if (!Number.isFinite(parsed)) throw new Error("Numeric input is invalid.");
  return parsed;
}

function dateToIso(value) {
  return new Date(`${value}T00:00:00Z`).toISOString();
}

function cssVar(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function chartTheme() {
  return {
    bg: cssVar("--bg", "#f6f7f9"),
    surface: cssVar("--surface", "#ffffff"),
    plotBg: cssVar("--plot-bg", "#ffffff"),
    text: cssVar("--text", "#17201d"),
    muted: cssVar("--muted", "#66736f"),
    border: cssVar("--border", "#d9e0de"),
    gridLine: cssVar("--grid-line", "#edf1ef"),
    gridStrong: cssVar("--grid-strong", "#b8c3bf"),
    hoverLine: appState.theme === "dark" ? "rgba(197, 210, 206, 0.45)" : "rgba(50, 65, 61, 0.32)",
  };
}

function requirePortfolio() {
  if (!appState.selectedPortfolioId) {
    toast("Select or create a portfolio first.", true);
    return false;
  }
  return true;
}

function matrixColor(value) {
  const bounded = Math.max(-1, Math.min(1, Number(value) || 0));
  if (bounded >= 0) {
    const light = 42 - bounded * 15;
    return `hsl(173 65% ${light}%)`;
  }
  const light = 42 - Math.abs(bounded) * 12;
  return `hsl(6 66% ${light}%)`;
}

function correlationTemperatureColor(value, threshold, diagonal = false) {
  const bounded = Math.max(-1, Math.min(1, finiteNumber(value, 0)));
  if (diagonal) return appState.theme === "dark" ? "hsl(173 55% 30%)" : "hsl(173 52% 34%)";
  const magnitude = Math.abs(bounded);
  if (magnitude < threshold) return appState.theme === "dark" ? "hsl(165 10% 20%)" : "hsl(165 14% 90%)";
  const intensity = Math.min(1, (magnitude - threshold) / Math.max(1 - threshold, 0.001));
  const light = appState.theme === "dark" ? 30 + intensity * 12 : 72 - intensity * 40;
  return bounded >= 0 ? `hsl(173 62% ${light}%)` : `hsl(6 66% ${light}%)`;
}

function finiteNumber(value, fallback = null) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function quoteForTicker(ticker) {
  const symbol = String(ticker || "").trim().toUpperCase();
  return (appState.marketData?.quotes || []).find((quote) => quote.ticker === symbol) || null;
}

function quoteDailyReturnPct(quote) {
  if (!quote) return null;
  if (quote.daily_return_pct != null) {
    const direct = Number(quote.daily_return_pct);
    if (Number.isFinite(direct)) return direct;
  }
  const price = Number(quote.price);
  const previousClose = Number(quote.previous_close);
  if (Number.isFinite(price) && Number.isFinite(previousClose) && previousClose > 0) {
    return ((price / previousClose) - 1) * 100;
  }
  return null;
}

function returnColor(value) {
  if (!Number.isFinite(value)) return "#4b5563";
  const bounded = Math.max(-5, Math.min(5, Number(value)));
  if (bounded >= 0) return `hsl(148 54% ${34 - bounded * 1.8}%)`;
  return `hsl(6 64% ${38 - Math.abs(bounded) * 1.5}%)`;
}

function money(value) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(Number(value) || 0);
}

function signedMoney(value) {
  const amount = Number(value) || 0;
  return `${amount >= 0 ? "+" : "-"}${money(Math.abs(amount))}`;
}

function pct(value) {
  return `${((Number(value) || 0) * 100).toFixed(2)}%`;
}

function signedPct(value) {
  const amount = Number(value) || 0;
  return `${amount >= 0 ? "+" : ""}${(amount * 100).toFixed(2)}%`;
}

function fixed(value, digits) {
  return (Number(value) || 0).toFixed(digits);
}

function shortDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "2-digit", year: "numeric" }).format(new Date(value));
}

function shortDateTime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[char]));
}

let toastTimer = null;
function toast(message, isError = false) {
  const box = $("#toast");
  box.textContent = message;
  box.style.background = isError ? "#8f1d16" : "#17201d";
  box.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => box.classList.remove("show"), 4200);
}
