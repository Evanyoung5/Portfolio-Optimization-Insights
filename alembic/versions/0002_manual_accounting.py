"""Manual accounting and performance tracking tables.

Revision ID: 0002_manual_accounting
Revises: 0001_initial_public_backend
Create Date: 2026-05-24
"""
from __future__ import annotations

from alembic import op

revision = "0002_manual_accounting"
down_revision = "0001_initial_public_backend"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS portfolio_cash_transactions (
            id UUID PRIMARY KEY,
            portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            transaction_type TEXT NOT NULL DEFAULT '[encrypted]',
            amount NUMERIC(20, 8) NOT NULL DEFAULT 0,
            currency CHAR(3) NOT NULL DEFAULT 'USD',
            occurred_at TIMESTAMPTZ NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            notes TEXT,
            encrypted_payload TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_portfolio_cash_transactions_portfolio_date ON portfolio_cash_transactions(portfolio_id, occurred_at)",
        """
        CREATE TABLE IF NOT EXISTS portfolio_trade_transactions (
            id UUID PRIMARY KEY,
            portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            symbol TEXT NOT NULL,
            symbol_hash TEXT,
            side TEXT NOT NULL DEFAULT '[encrypted]',
            quantity NUMERIC(20, 8) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
            price NUMERIC(20, 8) NOT NULL DEFAULT 0 CHECK (price >= 0),
            fees NUMERIC(20, 8) NOT NULL DEFAULT 0 CHECK (fees >= 0),
            asset_class TEXT NOT NULL DEFAULT 'encrypted',
            occurred_at TIMESTAMPTZ NOT NULL,
            realized_gain_loss NUMERIC(20, 8),
            lot_ids TEXT NOT NULL DEFAULT '[]',
            source TEXT NOT NULL DEFAULT 'manual',
            notes TEXT,
            encrypted_payload TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_portfolio_trade_transactions_portfolio_date ON portfolio_trade_transactions(portfolio_id, occurred_at)",
        "CREATE INDEX IF NOT EXISTS idx_portfolio_trade_transactions_symbol_hash ON portfolio_trade_transactions(portfolio_id, symbol_hash)",
        """
        CREATE TABLE IF NOT EXISTS portfolio_settings (
            portfolio_id UUID PRIMARY KEY REFERENCES portfolios(id) ON DELETE CASCADE,
            risk_free_rate NUMERIC(12, 8) NOT NULL DEFAULT 0.02,
            benchmark_symbols TEXT NOT NULL DEFAULT '',
            cash_target_pct NUMERIC(8, 6),
            encrypted_payload TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS portfolio_valuation_snapshots (
            id UUID PRIMARY KEY,
            portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            as_of TIMESTAMPTZ NOT NULL,
            market_value NUMERIC(20, 8) NOT NULL DEFAULT 0,
            cash NUMERIC(20, 8) NOT NULL DEFAULT 0,
            total_equity NUMERIC(20, 8) NOT NULL DEFAULT 0,
            net_contributions NUMERIC(20, 8) NOT NULL DEFAULT 0,
            metadata TEXT NOT NULL DEFAULT '{}',
            encrypted_payload TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_portfolio_valuation_snapshots_portfolio_as_of ON portfolio_valuation_snapshots(portfolio_id, as_of)",
        """
        CREATE TABLE IF NOT EXISTS benchmark_prices (
            symbol TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'manual',
            observed_at TIMESTAMPTZ NOT NULL,
            price NUMERIC(20, 8) NOT NULL CHECK (price > 0),
            currency TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (symbol, provider, observed_at)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_benchmark_prices_symbol_observed_at ON benchmark_prices(symbol, observed_at)",
    ]
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    for table in [
        "benchmark_prices",
        "portfolio_valuation_snapshots",
        "portfolio_settings",
        "portfolio_trade_transactions",
        "portfolio_cash_transactions",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
