# Portfolio Optimization API

FastAPI backend scaffold for portfolio creation, CSV position uploads, portfolio analysis,
optimization, and trade-impact simulation.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The frontend is available at `http://localhost:8000/`, and API docs are available at `http://localhost:8000/docs`.


## Frontend

The first frontend lives in `frontend/` and is served directly by FastAPI, so there is no separate
Node build step yet:

```bash
uvicorn app.main:app --reload
# open http://localhost:8000/
```

The UI includes separate tabs for dashboard metrics, manual portfolio entry, risk analysis,
heatmap, optimization, trade simulation, market-data refreshes, and account security. The dashboard
shows total equity, beta, alpha, Sharpe ratio, volatility, idle cash, holdings, activity, and a
performance chart. Users can save benchmark tickers in portfolio settings; market-data refreshes
include those symbols so current quote movement is available for comparison while a future
historical benchmark endpoint is added.

## Docker

```bash
docker compose up --build
```

The compose stack includes:

- API on `localhost:8000`
- Postgres on `localhost:5432`
- Redis on `localhost:6379`
- Background worker consuming Redis jobs

For a production-style deployment with the reverse proxy, strict runtime validation, and container health checks:

```bash
docker compose -f docker-compose.prod.yml up --build -d
python3 scripts/prod_smoke_test.py --base-url http://localhost
docker compose -f docker-compose.prod.yml exec api python -m app.ops.smtp_check
```

For a local production rehearsal with a mail sandbox, use the included local env file shape and Mailpit profile:

```bash
cp .env.prod.local.example .env.prod.local
docker compose --env-file .env.prod.local -f docker-compose.prod.yml --profile local-drill up --build -d
python3 scripts/prod_smoke_test.py --base-url https://localhost --allow-insecure-localhost
docker compose --env-file .env.prod.local -f docker-compose.prod.yml exec api python -m app.ops.smtp_check --send-test --to you@example.com
```

Broker integrations are intentionally not implemented yet. The `app/connectors` package contains
only placeholders so the integration boundary is explicit without connecting to any brokerage.

## Endpoints

- `GET /health`
- `GET /api/v1/health`
- `POST /auth/register` and `POST /api/v1/auth/register`
- `POST /auth/login` and `POST /api/v1/auth/login`
- `POST /auth/refresh` and `POST /api/v1/auth/refresh`
- `POST /auth/logout` and `POST /api/v1/auth/logout`
- `POST /auth/password-reset/request` and `POST /api/v1/auth/password-reset/request`
- `POST /auth/password-reset/confirm` and `POST /api/v1/auth/password-reset/confirm`
- `POST /auth/email-verification/request` and `POST /api/v1/auth/email-verification/request`
- `POST /auth/email-verification/confirm` and `POST /api/v1/auth/email-verification/confirm`
- `GET /me` and `GET /api/v1/me`
- `GET /me/portfolios` and `GET /api/v1/me/portfolios`
- `POST /portfolios` and `POST /api/v1/portfolios`
- `GET /portfolios/{portfolio_id}` and `GET /api/v1/portfolios/{portfolio_id}`
- `POST /portfolios/{portfolio_id}/lots` and `POST /api/v1/portfolios/{portfolio_id}/lots`
- `GET /portfolios/{portfolio_id}/cash-transactions` and `GET /api/v1/portfolios/{portfolio_id}/cash-transactions`
- `POST /portfolios/{portfolio_id}/cash-transactions` and `POST /api/v1/portfolios/{portfolio_id}/cash-transactions`
- `GET /portfolios/{portfolio_id}/trades` and `GET /api/v1/portfolios/{portfolio_id}/trades`
- `POST /portfolios/{portfolio_id}/trades` and `POST /api/v1/portfolios/{portfolio_id}/trades`
- `GET /portfolios/{portfolio_id}/settings` and `GET /api/v1/portfolios/{portfolio_id}/settings`
- `PATCH /portfolios/{portfolio_id}/settings` and `PATCH /api/v1/portfolios/{portfolio_id}/settings`
- `POST /api/v1/portfolios/{portfolio_id}/upload-csv`
- `GET /api/v1/portfolios/{portfolio_id}/analysis`
- `POST /portfolios/{portfolio_id}/analyze` and `POST /api/v1/portfolios/{portfolio_id}/analyze`
- `GET /portfolios/{portfolio_id}/market-data` and `GET /api/v1/portfolios/{portfolio_id}/market-data`
- `POST /portfolios/{portfolio_id}/market-data/refresh` and `POST /api/v1/portfolios/{portfolio_id}/market-data/refresh`
- `GET /portfolios/{portfolio_id}/heatmap` and `GET /api/v1/portfolios/{portfolio_id}/heatmap`
- `POST /portfolios/{portfolio_id}/heatmap` and `POST /api/v1/portfolios/{portfolio_id}/heatmap`
- `POST /portfolios/{portfolio_id}/jobs/rebuild-positions` and `POST /api/v1/portfolios/{portfolio_id}/jobs/rebuild-positions`
- `POST /api/v1/portfolios/{portfolio_id}/optimize`
- `POST /portfolios/{portfolio_id}/simulate-trade` and `POST /api/v1/portfolios/{portfolio_id}/simulate-trade`
- `POST /api/v1/portfolios/{portfolio_id}/simulate-trade-impact`

## Login, Privacy, and Persistence

Register or sign in before creating a portfolio if it should be private and available when the
user returns:

```json
POST /auth/register
{
  "email": "you@example.com",
  "password": "SufficientPass123"
}
```

The response includes an access token and refresh token for compatibility, and the API also sets same-origin `HttpOnly` auth cookies on register, login, and refresh. Public deployments should prefer the cookie session so browser JavaScript does not need to persist bearer tokens across reloads.

If a custom client still sends bearer tokens explicitly, private requests accept:

```text
Authorization: Bearer <access_token>
```

Portfolio creation requires an authenticated session, either through the same-origin auth cookies
or an explicit bearer token. Reading, analyzing, adding lots, optimizing, uploading CSVs,
refreshing market data, and simulating trades require that same owner session.
Refresh tokens are stored hashed, rotated through `POST /auth/refresh`, and revoked by logout or password reset.
Password reset and email verification tokens are one-time hashed records. In production, keep
`AUTH_DEV_EXPOSE_TOKENS=false` and configure `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
`SMTP_FROM_EMAIL`, and `PUBLIC_APP_URL` so reset and verification links are delivered by email.

With Docker, `PORTFOLIO_REPOSITORY=postgres` stores users and portfolios in Postgres. Sensitive
fields are encrypted at the application layer before persistence, including user email, portfolio
name/cash, positions, and lots. Lookup fields use keyed HMAC hashes so the app can find a user or
ticker without storing those values in plaintext. Passwords are stored only as PBKDF2-SHA256 hashes.

Set stable, secret values for `AUTH_SECRET_KEY` and `DATA_ENCRYPTION_KEY` before using persistent
data. Changing `DATA_ENCRYPTION_KEY` later will make existing encrypted records unreadable.

## Background Worker

Docker runs a separate `worker` service with:

```bash
python -m app.background.worker
```

The API can enqueue private portfolio jobs into Redis, and the worker processes them against the
same encrypted Postgres store. The first queued job route is:

```text
POST /portfolios/{portfolio_id}/jobs/rebuild-positions
```

It returns a background job record with `pending`, `running`, `completed`, or `failed` status. The
frontend can poll `GET /portfolios/{portfolio_id}` to read `background_jobs` alongside totals,
positions, and lots.

Local development can still use inline behavior for manual lot entry. The Redis worker becomes
important for longer-running tasks such as large CSV imports, cost-basis rebuilds, risk analysis
refreshes, scheduled market-data updates, and anything the browser should not wait on.

## Production Operations

The repo includes lightweight deployment scripts:

- `scripts/prod_backup.sh [backup_dir]` creates a Postgres dump and SHA-256 checksum. Set `INCLUDE_REDIS=true` to capture an optional Redis snapshot tarball.
- `scripts/prod_restore.sh <dump_path>` restores Postgres from a dump. This requires `ALLOW_DROP=true` because it replaces the current database contents.
- `TARGET_DATABASE=portfolio_restore_check scripts/prod_restore.sh <dump_path>` restores into an isolated verification database without touching the live one.
- `scripts/prod_smoke_test.py --base-url https://your-domain` verifies `/health` and `/runtime`, and can also test login with `--email` and `--password`.
- `docker compose -f docker-compose.prod.yml exec api python -m app.ops.smtp_check` verifies SMTP config and connectivity without sending mail.
- `docker compose -f docker-compose.prod.yml exec api python -m app.ops.smtp_check --send-test --to you@example.com` sends a deployment-time test message.

The production compose file now includes health checks for `api`, `worker`, `postgres`, and `redis`.

## Market Data

Market data is behind `app/connectors/market_data` so yfinance is swappable later. The yfinance
adapter is only called by the worker path, not directly by heatmap rendering or normal page loads.
Quote snapshots are cached in Redis and persisted in the `market_quotes` table.

```text
POST /portfolios/{portfolio_id}/market-data/refresh
GET /portfolios/{portfolio_id}/market-data
```

Refresh requests are rate limited with Redis before a worker job is queued, and provider fetches
are throttled inside the worker with both a stable per-account yfinance signature and a provider-wide
budget. Larger ticker batches and option-suite refreshes spend more budget units than small quote
refreshes, so one public user cannot monopolize yfinance capacity.

- Per user per minute: `MARKET_DATA_USER_REFRESH_LIMIT_PER_MINUTE`
- Per user per day: `MARKET_DATA_USER_REFRESH_LIMIT_PER_DAY`
- Optional per portfolio queue cooldown: `MARKET_DATA_PORTFOLIO_REFRESH_MIN_SECONDS`
- Per-account provider budget units: `MARKET_DATA_PROVIDER_FETCH_LIMIT_PER_MINUTE`
- Global provider budget units: `MARKET_DATA_PROVIDER_GLOBAL_FETCH_LIMIT_PER_MINUTE`
- Batch weight: `MARKET_DATA_PROVIDER_TICKERS_PER_COST_UNIT`
- Request caps: `MARKET_DATA_MAX_REFRESH_TICKERS`, `MARKET_DATA_MAX_HISTORY_TICKERS`, `MARKET_DATA_MAX_BENCHMARK_TICKERS`
- Options caps: `OPTIONS_CHAIN_MAX_SURFACE_EXPIRIES`, `OPTIONS_HISTORY_ALLOWED_PERIODS`
- Set `MARKET_DATA_REQUIRE_REDIS_LIMITER=true` in production so refreshes fail closed when Redis is unavailable

Manual portfolio changes automatically queue a market-data refresh. The first uncached refresh for
an account signature runs immediately when both its account budget and the global provider budget
have capacity. Other accounts use their own signatures, while the global budget prevents a public
deployment from building an unlimited yfinance backlog. The heatmap `GET` endpoint uses cached
quotes and never calls yfinance directly.

## Portfolio Heatmap

The old standalone heatmap app has been refactored into authenticated portfolio endpoints. The
backend returns frontend-ready treemap JSON sized by personal position value, not company market
capitalization.

```text
GET /portfolios/{portfolio_id}/heatmap
```

Use `POST` to provide fresh market data from a frontend or future market-data connector:

```json
{
  "group_by": "sector",
  "market_data": [
    {
      "ticker": "AAPL",
      "price": 190.25,
      "previous_close": 187.80,
      "sector": "Technology",
      "industry": "Consumer Electronics"
    }
  ]
}
```

The response includes normalized `nodes`, position-level `holdings`, and a `plotly` treemap payload
with `ids`, `labels`, `parents`, `values`, `colors`, `customdata`, and color-scale settings. This
keeps chart rendering in the frontend while preserving private portfolio ownership in the API.

## CSV Format

CSV uploads expect these headers:

```csv
symbol,quantity,price,asset_class
AAPL,10,185.50,equity
BND,20,72.10,bond
```

`asset_class` is optional and defaults to `equity`.


## Manual Portfolio Entry

Manual entry supports multiple purchase lots per ticker, so cost basis remains flexible when
shares were bought at different prices or dates. You can create a portfolio with lots directly:

```json
{
  "name": "Taxable Brokerage",
  "cash": 1000,
  "lots": [
    {
      "ticker": "AAPL",
      "quantity": 10,
      "purchase_price": 100,
      "current_price": 130,
      "fees": 2,
      "purchased_at": "2024-01-15T00:00:00Z",
      "asset_class": "equity"
    },
    {
      "ticker": "AAPL",
      "quantity": 5,
      "purchase_price": 120,
      "current_price": 130
    }
  ]
}
```

Then add more lots later with:

```text
POST /portfolios/{portfolio_id}/lots
```

Manual entry also has an account ledger for external cash flows. Use deposits and withdrawals to
track user contributions separately from investment returns, so performance can still be measured
after a sale is reinvested into another position:

```json
POST /portfolios/{portfolio_id}/cash-transactions
{
  "transaction_type": "deposit",
  "amount": 5000,
  "occurred_at": "2024-01-01T00:00:00Z"
}
```

Use manual trades for dated buys and sells. Buys create new lots, sells consume existing lots FIFO,
update idle cash, and preserve realized gain/loss in trade history:

```json
POST /portfolios/{portfolio_id}/trades
{
  "ticker": "AAPL",
  "side": "buy",
  "quantity": 10,
  "price": 100,
  "fees": 1,
  "occurred_at": "2024-01-15T00:00:00Z"
}
```

Portfolio settings store user-entered assumptions for analysis and future performance charts:

```json
PATCH /portfolios/{portfolio_id}/settings
{
  "risk_free_rate": 0.045,
  "benchmark_symbols": ["SPY", "QQQ"],
  "cash_target_pct": 0.05
}
```

Send the bearer token when adding lots, ledger entries, trades, or reading portfolio state. The
portfolio state endpoint returns frontend-ready totals, performance summary, settings, positions,
lots, cash ledger, trade history, charts, and background job status:

```text
GET /portfolios/{portfolio_id}
```

Fresh Docker Postgres volumes initialize the schema from `app/db/schema.sql`, and Docker sets `PORTFOLIO_REPOSITORY=postgres` so portfolios, lots, positions, quote cache records, auth tokens, manual trades, cash transactions, settings, valuation snapshots, and rollup jobs persist in Postgres. Sensitive account records are encrypted in `encrypted_payload` columns, with only keyed lookup hashes or minimal placeholders stored outside the ciphertext. Local tests default to the in-memory repository. For frontend dev, CORS defaults allow `localhost:3000` and `localhost:5173`; override with `FRONTEND_ORIGINS`.

## Migrations

Alembic is configured for production schema changes:

```bash
DATABASE_URL=postgresql://portfolio:portfolio@localhost:5432/portfolio alembic upgrade head
```

The production Compose file runs `alembic upgrade head` as a one-shot `migrate` service before the
API and worker start.

## Production Domain Deployment

Use the production Compose file with a real domain and HTTPS reverse proxy:

```bash
cp .env.production.example .env.production
# edit secrets and domain values
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

`deploy/Caddyfile` terminates HTTPS for `APP_DOMAIN` and proxies to the API container. Production
settings should include your real frontend origin, `APP_HOSTS`, `PUBLIC_APP_URL`, SMTP settings,
long random `AUTH_SECRET_KEY` and `DATA_ENCRYPTION_KEY`, `AUTH_DEV_EXPOSE_TOKENS=false`, and
database backups for the Postgres volume.

For a fuller launch checklist, see [docs/PUBLIC_DEPLOYMENT.md](docs/PUBLIC_DEPLOYMENT.md).
