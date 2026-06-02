from __future__ import annotations

from typing import Protocol

from app.db.models import MarketQuote


class MarketDataConnector(Protocol):
    provider: str

    def fetch_quotes(self, tickers: list[str]) -> list[MarketQuote]:
        """Fetch quote snapshots for normalized ticker symbols."""
