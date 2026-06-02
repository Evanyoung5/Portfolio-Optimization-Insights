"""Persist public option-chain snapshots captured during suite use.

Revision ID: 0003_option_chain_snapshots
Revises: 0002_manual_accounting
Create Date: 2026-06-01
"""
from __future__ import annotations

from alembic import op

revision = "0003_option_chain_snapshots"
down_revision = "0002_manual_accounting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS option_chain_snapshots (
            id UUID PRIMARY KEY,
            ticker TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'yfinance',
            expiry DATE NOT NULL,
            fetched_at TIMESTAMPTZ NOT NULL,
            snapshot_hash TEXT NOT NULL UNIQUE,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_option_chain_snapshots_ticker_expiry_fetched_at "
        "ON option_chain_snapshots(ticker, expiry, fetched_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_option_chain_snapshots_fetched_at "
        "ON option_chain_snapshots(fetched_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS option_chain_snapshots CASCADE")
