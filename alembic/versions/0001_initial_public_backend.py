"""Initial public backend schema.

Revision ID: 0001_initial_public_backend
Revises:
Create Date: 2026-05-24
"""
from __future__ import annotations

from alembic import op

revision = "0001_initial_public_backend"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            email_hash TEXT UNIQUE,
            email_ciphertext TEXT,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            email_verified_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS portfolios (
            id UUID PRIMARY KEY,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            name TEXT NOT NULL DEFAULT '[encrypted]',
            base_currency CHAR(3) NOT NULL DEFAULT 'USD',
            cash NUMERIC(20, 6) NOT NULL DEFAULT 0,
            encrypted_payload TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS position_lots (
            id UUID PRIMARY KEY,
            portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            symbol TEXT NOT NULL,
            symbol_hash TEXT,
            asset_class TEXT NOT NULL DEFAULT 'encrypted',
            quantity NUMERIC(20, 8) NOT NULL CHECK (quantity > 0),
            remaining_quantity NUMERIC(20, 8) NOT NULL CHECK (remaining_quantity >= 0),
            purchase_price NUMERIC(20, 8) NOT NULL CHECK (purchase_price > 0),
            current_price NUMERIC(20, 8) NOT NULL CHECK (current_price > 0),
            fees NUMERIC(20, 8) NOT NULL DEFAULT 0 CHECK (fees >= 0),
            purchased_at TIMESTAMPTZ NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            notes TEXT,
            encrypted_payload TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_position_lots_portfolio_symbol ON position_lots(portfolio_id, symbol)",
        "CREATE INDEX IF NOT EXISTS idx_position_lots_portfolio_symbol_hash ON position_lots(portfolio_id, symbol_hash)",
        """
        CREATE TABLE IF NOT EXISTS portfolio_positions (
            portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            symbol TEXT NOT NULL,
            symbol_hash TEXT,
            asset_class TEXT NOT NULL DEFAULT 'encrypted',
            quantity NUMERIC(20, 8) NOT NULL CHECK (quantity >= 0),
            price NUMERIC(20, 8) NOT NULL CHECK (price >= 0),
            market_value NUMERIC(20, 8) NOT NULL DEFAULT 0,
            cost_basis NUMERIC(20, 8) NOT NULL DEFAULT 0,
            average_cost NUMERIC(20, 8) NOT NULL DEFAULT 0,
            unrealized_gain_loss NUMERIC(20, 8) NOT NULL DEFAULT 0,
            lots_count INTEGER NOT NULL DEFAULT 0,
            encrypted_payload TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (portfolio_id, symbol)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS background_jobs (
            id UUID PRIMARY KEY,
            portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS auth_tokens (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            token_type TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            consumed_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_type ON auth_tokens(user_id, token_type)",
        """
        CREATE TABLE IF NOT EXISTS market_quotes (
            ticker TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            price NUMERIC(20, 8) NOT NULL CHECK (price > 0),
            previous_close NUMERIC(20, 8),
            daily_return_pct NUMERIC(20, 8),
            currency TEXT,
            sector TEXT,
            industry TEXT,
            fetched_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_market_quotes_fetched_at ON market_quotes(fetched_at)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_hash TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_ciphertext TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ",
        "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL",
        "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS encrypted_payload TEXT",
        "ALTER TABLE position_lots ADD COLUMN IF NOT EXISTS symbol_hash TEXT",
        "ALTER TABLE position_lots ADD COLUMN IF NOT EXISTS encrypted_payload TEXT",
        "ALTER TABLE portfolio_positions ADD COLUMN IF NOT EXISTS symbol_hash TEXT",
        "ALTER TABLE portfolio_positions ADD COLUMN IF NOT EXISTS encrypted_payload TEXT",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_hash ON users(email_hash)",
        "CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON portfolios(user_id)",
    ]
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    for table in [
        "market_quotes",
        "auth_tokens",
        "background_jobs",
        "portfolio_positions",
        "position_lots",
        "portfolios",
        "users",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
