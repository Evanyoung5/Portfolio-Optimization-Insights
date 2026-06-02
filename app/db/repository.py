from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from app.auth.security import normalize_email
from app.db.encryption import decrypt_json, encrypt_json, private_lookup_hash, ticker_lookup_hash
from app.db.models import (
    AuthTokenRecord,
    BackgroundJob,
    CashTransaction,
    MarketQuote,
    OptionChainHistorySnapshot,
    Portfolio,
    PortfolioSettings,
    PortfolioValuationSnapshot,
    Position,
    PositionLot,
    TradeTransaction,
    User,
)


class InMemoryPortfolioRepository:
    """Repository boundary used by tests and local runs without durable storage."""

    def __init__(self) -> None:
        self._portfolios: dict[str, Portfolio] = {}
        self._users: dict[str, User] = {}
        self._user_ids_by_email: dict[str, str] = {}
        self._auth_tokens: dict[str, AuthTokenRecord] = {}
        self._auth_token_ids_by_hash: dict[str, str] = {}
        self._market_quotes: dict[str, MarketQuote] = {}
        self._option_chain_snapshots: dict[str, OptionChainHistorySnapshot] = {}
        self._cash_transactions: dict[str, list[CashTransaction]] = {}
        self._trade_transactions: dict[str, list[TradeTransaction]] = {}
        self._portfolio_settings: dict[str, PortfolioSettings] = {}
        self._valuation_snapshots: dict[str, list[PortfolioValuationSnapshot]] = {}
        self._lock = RLock()

    def create_user(self, *, email: str, password_hash: str) -> User:
        email = normalize_email(email)
        with self._lock:
            if email in self._user_ids_by_email:
                raise ValueError("A user with that email already exists.")
            now = datetime.now(timezone.utc)
            user = User(
                id=str(uuid4()),
                email=email,
                password_hash=password_hash,
                created_at=now,
                updated_at=now,
            )
            self._users[user.id] = user
            self._user_ids_by_email[email] = user.id
            return user

    def get_user(self, user_id: str) -> User | None:
        with self._lock:
            return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        email = normalize_email(email)
        with self._lock:
            user_id = self._user_ids_by_email.get(email)
            return self._users.get(user_id) if user_id else None

    def mark_user_email_verified(self, user_id: str) -> User:
        with self._lock:
            user = self._users[user_id]
            user.email_verified_at = datetime.now(timezone.utc)
            user.updated_at = user.email_verified_at
            return user

    def update_user_password(self, user_id: str, password_hash: str) -> User:
        with self._lock:
            user = self._users[user_id]
            user.password_hash = password_hash
            user.updated_at = datetime.now(timezone.utc)
            return user

    def create_auth_token(
        self,
        *,
        user_id: str,
        token_hash: str,
        token_type: str,
        expires_at: datetime,
    ) -> AuthTokenRecord:
        with self._lock:
            now = datetime.now(timezone.utc)
            record = AuthTokenRecord(
                id=str(uuid4()),
                user_id=user_id,
                token_hash=token_hash,
                token_type=token_type,
                expires_at=expires_at,
                created_at=now,
                updated_at=now,
            )
            self._auth_tokens[record.id] = record
            self._auth_token_ids_by_hash[token_hash] = record.id
            return record

    def get_auth_token(self, *, token_hash: str, token_type: str) -> AuthTokenRecord | None:
        with self._lock:
            token_id = self._auth_token_ids_by_hash.get(token_hash)
            record = self._auth_tokens.get(token_id) if token_id else None
            if record is None or record.token_type != token_type:
                return None
            return record

    def consume_auth_token(self, token_id: str) -> AuthTokenRecord:
        with self._lock:
            record = self._auth_tokens[token_id]
            record.consumed_at = datetime.now(timezone.utc)
            record.updated_at = record.consumed_at
            return record

    def revoke_auth_token(self, token_id: str) -> AuthTokenRecord:
        with self._lock:
            record = self._auth_tokens[token_id]
            record.revoked_at = datetime.now(timezone.utc)
            record.updated_at = record.revoked_at
            return record

    def revoke_user_tokens(self, *, user_id: str, token_type: str | None = None) -> int:
        revoked = 0
        with self._lock:
            now = datetime.now(timezone.utc)
            for record in self._auth_tokens.values():
                if record.user_id != user_id or record.revoked_at is not None:
                    continue
                if token_type is not None and record.token_type != token_type:
                    continue
                record.revoked_at = now
                record.updated_at = now
                revoked += 1
        return revoked

    def create(
        self,
        *,
        name: str,
        base_currency: str,
        cash: float,
        positions: list[Position],
        lots: list[PositionLot] | None = None,
        user_id: str | None = None,
    ) -> Portfolio:
        now = datetime.now(timezone.utc)
        portfolio = Portfolio(
            id=str(uuid4()),
            name=name,
            user_id=user_id,
            base_currency=base_currency,
            cash=cash,
            positions=positions,
            lots=lots or [],
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._portfolios[portfolio.id] = portfolio
        return portfolio

    def get(self, portfolio_id: str) -> Portfolio | None:
        with self._lock:
            return self._portfolios.get(portfolio_id)

    def list_portfolios(self, *, user_id: str) -> list[Portfolio]:
        with self._lock:
            return [portfolio for portfolio in self._portfolios.values() if portfolio.user_id == user_id]

    def replace_positions(self, portfolio_id: str, positions: list[Position]) -> Portfolio:
        with self._lock:
            portfolio = self._portfolios[portfolio_id]
            portfolio.positions = positions
            portfolio.updated_at = datetime.now(timezone.utc)
            return portfolio

    def update_positions(self, portfolio_id: str, positions: list[Position]) -> Portfolio:
        return self.replace_positions(portfolio_id, positions)

    def add_lots(self, portfolio_id: str, lots: list[PositionLot]) -> Portfolio:
        with self._lock:
            portfolio = self._portfolios[portfolio_id]
            portfolio.lots.extend(lots)
            portfolio.updated_at = datetime.now(timezone.utc)
            return portfolio

    def replace_lots(self, portfolio_id: str, lots: list[PositionLot]) -> Portfolio:
        with self._lock:
            portfolio = self._portfolios[portfolio_id]
            portfolio.lots = lots
            portfolio.updated_at = datetime.now(timezone.utc)
            return portfolio

    def list_lots(self, portfolio_id: str) -> list[PositionLot]:
        with self._lock:
            return list(self._portfolios[portfolio_id].lots)

    def update_cash(self, portfolio_id: str, cash: float) -> Portfolio:
        with self._lock:
            portfolio = self._portfolios[portfolio_id]
            portfolio.cash = float(cash)
            portfolio.updated_at = datetime.now(timezone.utc)
            return portfolio

    def add_cash_transaction(self, transaction: CashTransaction) -> CashTransaction:
        with self._lock:
            self._cash_transactions.setdefault(transaction.portfolio_id, []).append(transaction)
            self._portfolios[transaction.portfolio_id].updated_at = datetime.now(timezone.utc)
            return transaction

    def list_cash_transactions(self, portfolio_id: str) -> list[CashTransaction]:
        with self._lock:
            return sorted(
                list(self._cash_transactions.get(portfolio_id, [])),
                key=lambda item: (item.occurred_at, item.id),
            )

    def add_trade_transaction(self, transaction: TradeTransaction) -> TradeTransaction:
        with self._lock:
            self._trade_transactions.setdefault(transaction.portfolio_id, []).append(transaction)
            self._portfolios[transaction.portfolio_id].updated_at = datetime.now(timezone.utc)
            return transaction

    def list_trade_transactions(self, portfolio_id: str) -> list[TradeTransaction]:
        with self._lock:
            return sorted(
                list(self._trade_transactions.get(portfolio_id, [])),
                key=lambda item: (item.occurred_at, item.id),
            )

    def get_portfolio_settings(self, portfolio_id: str) -> PortfolioSettings:
        with self._lock:
            if portfolio_id not in self._portfolios:
                raise KeyError(f"Portfolio {portfolio_id!r} was not found.")
            return self._portfolio_settings.get(portfolio_id) or PortfolioSettings(portfolio_id=portfolio_id)

    def upsert_portfolio_settings(self, settings: PortfolioSettings) -> PortfolioSettings:
        with self._lock:
            settings.updated_at = datetime.now(timezone.utc)
            self._portfolio_settings[settings.portfolio_id] = settings
            self._portfolios[settings.portfolio_id].updated_at = settings.updated_at
            return settings

    def add_valuation_snapshot(self, snapshot: PortfolioValuationSnapshot) -> PortfolioValuationSnapshot:
        with self._lock:
            self._valuation_snapshots.setdefault(snapshot.portfolio_id, []).append(snapshot)
            return snapshot

    def list_valuation_snapshots(self, portfolio_id: str) -> list[PortfolioValuationSnapshot]:
        with self._lock:
            return sorted(
                list(self._valuation_snapshots.get(portfolio_id, [])),
                key=lambda item: (item.as_of, item.id),
            )

    def upsert_market_quotes(self, quotes: list[MarketQuote]) -> list[MarketQuote]:
        with self._lock:
            now = datetime.now(timezone.utc)
            stored: list[MarketQuote] = []
            for quote in quotes:
                quote.ticker = quote.ticker.strip().upper()
                quote.updated_at = now
                self._market_quotes[quote.ticker] = quote
                stored.append(quote)
            return stored

    def get_market_quotes(
        self,
        tickers: list[str],
        *,
        max_age_seconds: int | None = None,
    ) -> list[MarketQuote]:
        now = datetime.now(timezone.utc)
        quotes: list[MarketQuote] = []
        with self._lock:
            for ticker in _normalize_tickers(tickers):
                quote = self._market_quotes.get(ticker)
                if quote is None:
                    continue
                fetched_at = _aware_datetime(quote.fetched_at)
                if max_age_seconds is not None and fetched_at < now - timedelta(seconds=max_age_seconds):
                    continue
                quotes.append(quote)
        return quotes

    def add_option_chain_snapshot(self, snapshot: OptionChainHistorySnapshot) -> OptionChainHistorySnapshot:
        with self._lock:
            existing = next(
                (
                    item
                    for item in self._option_chain_snapshots.values()
                    if item.snapshot_hash == snapshot.snapshot_hash
                ),
                None,
            )
            if existing is not None:
                return existing
            self._option_chain_snapshots[snapshot.id] = snapshot
            return snapshot

    def list_option_chain_snapshots(
        self,
        ticker: str,
        *,
        expiry: date | None = None,
        since: datetime | None = None,
    ) -> list[OptionChainHistorySnapshot]:
        normalized = str(ticker).strip().upper()
        with self._lock:
            snapshots = [
                item
                for item in self._option_chain_snapshots.values()
                if item.ticker == normalized
                and (expiry is None or item.expiry == expiry)
                and (since is None or _aware_datetime(item.fetched_at) >= _aware_datetime(since))
            ]
        return sorted(snapshots, key=lambda item: (item.fetched_at, item.expiry, item.id))

    def purge_option_chain_snapshots(self, *, before: datetime) -> int:
        with self._lock:
            expired_ids = [
                snapshot_id
                for snapshot_id, item in self._option_chain_snapshots.items()
                if _aware_datetime(item.fetched_at) < _aware_datetime(before)
            ]
            for snapshot_id in expired_ids:
                del self._option_chain_snapshots[snapshot_id]
        return len(expired_ids)

    def enqueue_background_job(
        self,
        portfolio_id: str,
        job_type: str,
        *,
        message: str | None = None,
    ) -> BackgroundJob:
        with self._lock:
            now = datetime.now(timezone.utc)
            job = BackgroundJob(
                id=str(uuid4()),
                portfolio_id=portfolio_id,
                job_type=job_type,
                status="pending",
                message=message,
                created_at=now,
                updated_at=now,
            )
            self._portfolios[portfolio_id].background_jobs.append(job)
            return job

    def complete_background_job(
        self,
        portfolio_id: str,
        job_id: str,
        *,
        status: str = "completed",
        message: str | None = None,
    ) -> BackgroundJob:
        with self._lock:
            portfolio = self._portfolios[portfolio_id]
            for job in portfolio.background_jobs:
                if job.id == job_id:
                    job.status = status
                    job.message = message
                    job.updated_at = datetime.now(timezone.utc)
                    return job
            raise KeyError(f"Background job {job_id!r} was not found.")

    def clear(self) -> None:
        with self._lock:
            self._portfolios.clear()
            self._users.clear()
            self._user_ids_by_email.clear()
            self._auth_tokens.clear()
            self._auth_token_ids_by_hash.clear()
            self._market_quotes.clear()
            self._option_chain_snapshots.clear()
            self._cash_transactions.clear()
            self._trade_transactions.clear()
            self._portfolio_settings.clear()
            self._valuation_snapshots.clear()


class PostgresPortfolioRepository:
    """Postgres repository with application-layer encryption for private data."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for PostgresPortfolioRepository.")
        self._ensure_schema()

    def create_user(self, *, email: str, password_hash: str) -> User:
        email = normalize_email(email)
        email_hash = private_lookup_hash(email)
        now = datetime.now(timezone.utc)
        user = User(id=str(uuid4()), email=email, password_hash=password_hash, created_at=now, updated_at=now)
        with self._connect() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        INSERT INTO users
                            (id, email_hash, email_ciphertext, email, password_hash, email_verified_at, created_at, updated_at)
                        VALUES (%s, %s, %s, NULL, %s, NULL, %s, %s)
                        """,
                        (
                            user.id,
                            email_hash,
                            encrypt_json({"email": email}),
                            password_hash,
                            now,
                            now,
                        ),
                    )
                except Exception as exc:
                    if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                        raise ValueError("A user with that email already exists.") from exc
                    raise
            conn.commit()
        return user

    def get_user(self, user_id: str) -> User | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email_ciphertext, email, password_hash, email_verified_at, created_at, updated_at
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                return _user_from_row(row) if row else None

    def get_user_by_email(self, email: str) -> User | None:
        email = normalize_email(email)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email_ciphertext, email, password_hash, email_verified_at, created_at, updated_at
                    FROM users
                    WHERE email_hash = %s
                    """,
                    (private_lookup_hash(email),),
                )
                row = cur.fetchone()
                return _user_from_row(row) if row else None

    def mark_user_email_verified(self, user_id: str) -> User:
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET email_verified_at = %s, updated_at = %s WHERE id = %s",
                    (now, now, user_id),
                )
            conn.commit()
        user = self.get_user(user_id)
        if user is None:
            raise KeyError(f"User {user_id!r} was not found.")
        return user

    def update_user_password(self, user_id: str, password_hash: str) -> User:
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET password_hash = %s, updated_at = %s WHERE id = %s",
                    (password_hash, now, user_id),
                )
            conn.commit()
        user = self.get_user(user_id)
        if user is None:
            raise KeyError(f"User {user_id!r} was not found.")
        return user

    def create_auth_token(
        self,
        *,
        user_id: str,
        token_hash: str,
        token_type: str,
        expires_at: datetime,
    ) -> AuthTokenRecord:
        now = datetime.now(timezone.utc)
        record = AuthTokenRecord(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            token_type=token_type,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_tokens
                        (id, user_id, token_hash, token_type, expires_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.id,
                        record.user_id,
                        record.token_hash,
                        record.token_type,
                        record.expires_at,
                        record.created_at,
                        record.updated_at,
                    ),
                )
            conn.commit()
        return record

    def get_auth_token(self, *, token_hash: str, token_type: str) -> AuthTokenRecord | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, token_hash, token_type, expires_at, consumed_at, revoked_at, created_at, updated_at
                    FROM auth_tokens
                    WHERE token_hash = %s AND token_type = %s
                    """,
                    (token_hash, token_type),
                )
                row = cur.fetchone()
                return _auth_token_from_row(row) if row else None

    def consume_auth_token(self, token_id: str) -> AuthTokenRecord:
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_tokens
                    SET consumed_at = %s, updated_at = %s
                    WHERE id = %s
                    RETURNING id, user_id, token_hash, token_type, expires_at, consumed_at, revoked_at, created_at, updated_at
                    """,
                    (now, now, token_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise KeyError(f"Auth token {token_id!r} was not found.")
            conn.commit()
        return _auth_token_from_row(row)

    def revoke_auth_token(self, token_id: str) -> AuthTokenRecord:
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_tokens
                    SET revoked_at = %s, updated_at = %s
                    WHERE id = %s
                    RETURNING id, user_id, token_hash, token_type, expires_at, consumed_at, revoked_at, created_at, updated_at
                    """,
                    (now, now, token_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise KeyError(f"Auth token {token_id!r} was not found.")
            conn.commit()
        return _auth_token_from_row(row)

    def revoke_user_tokens(self, *, user_id: str, token_type: str | None = None) -> int:
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                if token_type is None:
                    cur.execute(
                        """
                        UPDATE auth_tokens
                        SET revoked_at = %s, updated_at = %s
                        WHERE user_id = %s AND revoked_at IS NULL
                        """,
                        (now, now, user_id),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE auth_tokens
                        SET revoked_at = %s, updated_at = %s
                        WHERE user_id = %s AND token_type = %s AND revoked_at IS NULL
                        """,
                        (now, now, user_id, token_type),
                    )
                count = cur.rowcount or 0
            conn.commit()
        return count

    def create(
        self,
        *,
        name: str,
        base_currency: str,
        cash: float,
        positions: list[Position],
        lots: list[PositionLot] | None = None,
        user_id: str | None = None,
    ) -> Portfolio:
        portfolio_id = str(uuid4())
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolios
                        (id, user_id, name, base_currency, cash, encrypted_payload, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        portfolio_id,
                        user_id,
                        "[encrypted]",
                        base_currency,
                        0,
                        encrypt_json({"name": name, "cash": cash}),
                        now,
                        now,
                    ),
                )
                self._insert_positions(cur, portfolio_id, positions)
                self._insert_lots(cur, portfolio_id, lots or [])
            conn.commit()
        portfolio = self.get(portfolio_id)
        if portfolio is None:
            raise RuntimeError("Created portfolio could not be loaded from Postgres.")
        return portfolio

    def get(self, portfolio_id: str) -> Portfolio | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, name, base_currency, cash, encrypted_payload, created_at, updated_at
                    FROM portfolios
                    WHERE id = %s
                    """,
                    (portfolio_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._portfolio_from_row(cur, row)

    def list_portfolios(self, *, user_id: str) -> list[Portfolio]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, name, base_currency, cash, encrypted_payload, created_at, updated_at
                    FROM portfolios
                    WHERE user_id = %s
                    ORDER BY created_at DESC, id
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
                return [self._portfolio_from_row(cur, row) for row in rows]

    def replace_positions(self, portfolio_id: str, positions: list[Position]) -> Portfolio:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM portfolio_positions WHERE portfolio_id = %s", (portfolio_id,))
                self._insert_positions(cur, portfolio_id, positions)
                self._touch_portfolio(cur, portfolio_id)
            conn.commit()
        portfolio = self.get(portfolio_id)
        if portfolio is None:
            raise KeyError(f"Portfolio {portfolio_id!r} was not found.")
        return portfolio

    def update_positions(self, portfolio_id: str, positions: list[Position]) -> Portfolio:
        return self.replace_positions(portfolio_id, positions)

    def add_lots(self, portfolio_id: str, lots: list[PositionLot]) -> Portfolio:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._insert_lots(cur, portfolio_id, lots)
                self._touch_portfolio(cur, portfolio_id)
            conn.commit()
        portfolio = self.get(portfolio_id)
        if portfolio is None:
            raise KeyError(f"Portfolio {portfolio_id!r} was not found.")
        return portfolio

    def replace_lots(self, portfolio_id: str, lots: list[PositionLot]) -> Portfolio:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM position_lots WHERE portfolio_id = %s", (portfolio_id,))
                self._insert_lots(cur, portfolio_id, lots)
                self._touch_portfolio(cur, portfolio_id)
            conn.commit()
        portfolio = self.get(portfolio_id)
        if portfolio is None:
            raise KeyError(f"Portfolio {portfolio_id!r} was not found.")
        return portfolio

    def list_lots(self, portfolio_id: str) -> list[PositionLot]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                return self._load_lots(cur, portfolio_id)

    def update_cash(self, portfolio_id: str, cash: float) -> Portfolio:
        portfolio = self.get(portfolio_id)
        if portfolio is None:
            raise KeyError(f"Portfolio {portfolio_id!r} was not found.")
        now = datetime.now(timezone.utc)
        payload = encrypt_json({"name": portfolio.name, "cash": float(cash)})
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE portfolios
                    SET cash = 0, encrypted_payload = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (payload, now, portfolio_id),
                )
            conn.commit()
        updated = self.get(portfolio_id)
        if updated is None:
            raise KeyError(f"Portfolio {portfolio_id!r} was not found.")
        return updated

    def add_cash_transaction(self, transaction: CashTransaction) -> CashTransaction:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_cash_transactions
                        (id, portfolio_id, transaction_type, amount, currency, occurred_at, source,
                         notes, encrypted_payload, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s, %s)
                    """,
                    (
                        transaction.id,
                        transaction.portfolio_id,
                        "[encrypted]",
                        0,
                        transaction.currency,
                        transaction.occurred_at,
                        transaction.source,
                        encrypt_json(_cash_transaction_payload(transaction)),
                        transaction.created_at,
                    ),
                )
                self._touch_portfolio(cur, transaction.portfolio_id)
            conn.commit()
        return transaction

    def list_cash_transactions(self, portfolio_id: str) -> list[CashTransaction]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, portfolio_id, transaction_type, amount, currency, occurred_at, source,
                           notes, encrypted_payload, created_at
                    FROM portfolio_cash_transactions
                    WHERE portfolio_id = %s
                    ORDER BY occurred_at, id
                    """,
                    (portfolio_id,),
                )
                return [_cash_transaction_from_row(row) for row in cur.fetchall()]

    def add_trade_transaction(self, transaction: TradeTransaction) -> TradeTransaction:
        symbol_hash = ticker_lookup_hash(transaction.symbol)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_trade_transactions
                        (id, portfolio_id, symbol, symbol_hash, side, quantity, price, fees, asset_class,
                         occurred_at, realized_gain_loss, lot_ids, source, notes, encrypted_payload, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s)
                    """,
                    (
                        transaction.id,
                        transaction.portfolio_id,
                        symbol_hash,
                        symbol_hash,
                        "[encrypted]",
                        0,
                        0,
                        0,
                        "encrypted",
                        transaction.occurred_at,
                        0 if transaction.realized_gain_loss is not None else None,
                        "[]",
                        transaction.source,
                        encrypt_json(_trade_transaction_payload(transaction)),
                        transaction.created_at,
                    ),
                )
                self._touch_portfolio(cur, transaction.portfolio_id)
            conn.commit()
        return transaction

    def list_trade_transactions(self, portfolio_id: str) -> list[TradeTransaction]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, portfolio_id, symbol, symbol_hash, side, quantity, price, fees, asset_class,
                           occurred_at, realized_gain_loss, lot_ids, source, notes, encrypted_payload, created_at
                    FROM portfolio_trade_transactions
                    WHERE portfolio_id = %s
                    ORDER BY occurred_at, id
                    """,
                    (portfolio_id,),
                )
                return [_trade_transaction_from_row(row) for row in cur.fetchall()]

    def get_portfolio_settings(self, portfolio_id: str) -> PortfolioSettings:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT portfolio_id, risk_free_rate, benchmark_symbols, cash_target_pct,
                           encrypted_payload, updated_at
                    FROM portfolio_settings
                    WHERE portfolio_id = %s
                    """,
                    (portfolio_id,),
                )
                row = cur.fetchone()
        if row is None:
            if self.get(portfolio_id) is None:
                raise KeyError(f"Portfolio {portfolio_id!r} was not found.")
            return PortfolioSettings(portfolio_id=portfolio_id)
        return _settings_from_row(row)

    def upsert_portfolio_settings(self, settings: PortfolioSettings) -> PortfolioSettings:
        settings.updated_at = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_settings
                        (portfolio_id, risk_free_rate, benchmark_symbols, cash_target_pct,
                         encrypted_payload, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (portfolio_id) DO UPDATE SET
                        risk_free_rate = EXCLUDED.risk_free_rate,
                        benchmark_symbols = EXCLUDED.benchmark_symbols,
                        cash_target_pct = EXCLUDED.cash_target_pct,
                        encrypted_payload = EXCLUDED.encrypted_payload,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (
                        settings.portfolio_id,
                        settings.risk_free_rate,
                        ",".join(settings.benchmark_symbols),
                        settings.cash_target_pct,
                        encrypt_json(_settings_payload(settings)),
                        settings.updated_at,
                    ),
                )
                self._touch_portfolio(cur, settings.portfolio_id)
            conn.commit()
        return settings

    def add_valuation_snapshot(self, snapshot: PortfolioValuationSnapshot) -> PortfolioValuationSnapshot:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_valuation_snapshots
                        (id, portfolio_id, as_of, market_value, cash, total_equity, net_contributions,
                         metadata, encrypted_payload, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        snapshot.id,
                        snapshot.portfolio_id,
                        snapshot.as_of,
                        0,
                        0,
                        0,
                        0,
                        "{}",
                        encrypt_json(_valuation_snapshot_payload(snapshot)),
                        snapshot.created_at,
                    ),
                )
            conn.commit()
        return snapshot

    def list_valuation_snapshots(self, portfolio_id: str) -> list[PortfolioValuationSnapshot]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, portfolio_id, as_of, market_value, cash, total_equity, net_contributions,
                           metadata, encrypted_payload, created_at
                    FROM portfolio_valuation_snapshots
                    WHERE portfolio_id = %s
                    ORDER BY as_of, id
                    """,
                    (portfolio_id,),
                )
                return [_valuation_snapshot_from_row(row) for row in cur.fetchall()]

    def upsert_market_quotes(self, quotes: list[MarketQuote]) -> list[MarketQuote]:
        if not quotes:
            return []
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                for quote in quotes:
                    quote.ticker = quote.ticker.strip().upper()
                    quote.updated_at = now
                    cur.execute(
                        """
                        INSERT INTO market_quotes
                            (ticker, provider, price, previous_close, daily_return_pct, currency,
                             sector, industry, fetched_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ticker) DO UPDATE SET
                            provider = EXCLUDED.provider,
                            price = EXCLUDED.price,
                            previous_close = EXCLUDED.previous_close,
                            daily_return_pct = EXCLUDED.daily_return_pct,
                            currency = EXCLUDED.currency,
                            sector = EXCLUDED.sector,
                            industry = EXCLUDED.industry,
                            fetched_at = EXCLUDED.fetched_at,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            quote.ticker,
                            quote.provider,
                            quote.price,
                            quote.previous_close,
                            quote.daily_return_pct,
                            quote.currency,
                            quote.sector,
                            quote.industry,
                            quote.fetched_at,
                            quote.updated_at,
                        ),
                    )
            conn.commit()
        return quotes

    def get_market_quotes(
        self,
        tickers: list[str],
        *,
        max_age_seconds: int | None = None,
    ) -> list[MarketQuote]:
        normalized = _normalize_tickers(tickers)
        if not normalized:
            return []
        threshold = None
        if max_age_seconds is not None:
            threshold = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
        with self._connect() as conn:
            with conn.cursor() as cur:
                if threshold is None:
                    cur.execute(
                        """
                        SELECT ticker, provider, price, previous_close, daily_return_pct, currency,
                               sector, industry, fetched_at, updated_at
                        FROM market_quotes
                        WHERE ticker = ANY(%s)
                        """,
                        (normalized,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT ticker, provider, price, previous_close, daily_return_pct, currency,
                               sector, industry, fetched_at, updated_at
                        FROM market_quotes
                        WHERE ticker = ANY(%s) AND fetched_at >= %s
                        """,
                        (normalized, threshold),
                    )
                rows = cur.fetchall()
        by_ticker = {_market_quote_from_row(row).ticker: _market_quote_from_row(row) for row in rows}
        return [by_ticker[ticker] for ticker in normalized if ticker in by_ticker]

    def add_option_chain_snapshot(self, snapshot: OptionChainHistorySnapshot) -> OptionChainHistorySnapshot:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO option_chain_snapshots
                        (id, ticker, provider, expiry, fetched_at, snapshot_hash, payload, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (snapshot_hash) DO NOTHING
                    RETURNING id, ticker, provider, expiry, fetched_at, snapshot_hash, payload, created_at
                    """,
                    (
                        snapshot.id,
                        snapshot.ticker,
                        snapshot.provider,
                        snapshot.expiry,
                        snapshot.fetched_at,
                        snapshot.snapshot_hash,
                        json.dumps(snapshot.payload, separators=(",", ":"), sort_keys=True),
                        snapshot.created_at,
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    cur.execute(
                        """
                        SELECT id, ticker, provider, expiry, fetched_at, snapshot_hash, payload, created_at
                        FROM option_chain_snapshots
                        WHERE snapshot_hash = %s
                        """,
                        (snapshot.snapshot_hash,),
                    )
                    row = cur.fetchone()
            conn.commit()
        return _option_chain_history_snapshot_from_row(row)

    def list_option_chain_snapshots(
        self,
        ticker: str,
        *,
        expiry: date | None = None,
        since: datetime | None = None,
    ) -> list[OptionChainHistorySnapshot]:
        normalized = str(ticker).strip().upper()
        clauses = ["ticker = %s"]
        params: list[Any] = [normalized]
        if expiry is not None:
            clauses.append("expiry = %s")
            params.append(expiry)
        if since is not None:
            clauses.append("fetched_at >= %s")
            params.append(since)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT id, ticker, provider, expiry, fetched_at, snapshot_hash, payload, created_at
                    FROM option_chain_snapshots
                    WHERE {" AND ".join(clauses)}
                    ORDER BY fetched_at, expiry, id
                    """,
                    tuple(params),
                )
                return [_option_chain_history_snapshot_from_row(row) for row in cur.fetchall()]

    def purge_option_chain_snapshots(self, *, before: datetime) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM option_chain_snapshots WHERE fetched_at < %s", (before,))
                count = cur.rowcount or 0
            conn.commit()
        return count

    def enqueue_background_job(
        self,
        portfolio_id: str,
        job_type: str,
        *,
        message: str | None = None,
    ) -> BackgroundJob:
        job = BackgroundJob(
            id=str(uuid4()),
            portfolio_id=portfolio_id,
            job_type=job_type,
            status="pending",
            message=message,
        )
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO background_jobs
                        (id, portfolio_id, job_type, status, message, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        job.id,
                        portfolio_id,
                        job.job_type,
                        job.status,
                        job.message,
                        job.created_at,
                        job.updated_at,
                    ),
                )
            conn.commit()
        return job

    def complete_background_job(
        self,
        portfolio_id: str,
        job_id: str,
        *,
        status: str = "completed",
        message: str | None = None,
    ) -> BackgroundJob:
        updated_at = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE background_jobs
                    SET status = %s, message = %s, updated_at = %s
                    WHERE portfolio_id = %s AND id = %s
                    RETURNING id, portfolio_id, job_type, status, message, created_at, updated_at
                    """,
                    (status, message, updated_at, portfolio_id, job_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise KeyError(f"Background job {job_id!r} was not found.")
            conn.commit()
        return _job_from_row(row)

    def clear(self) -> None:
        allowed = os.getenv("ALLOW_POSTGRES_REPOSITORY_CLEAR", "false").strip().lower()
        if allowed not in {"1", "true", "yes", "on"}:
            raise RuntimeError(
                "Refusing to clear the Postgres repository. Set ALLOW_POSTGRES_REPOSITORY_CLEAR=true only for an intentional test/database reset."
            )
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM benchmark_prices")
                cur.execute("DELETE FROM option_chain_snapshots")
                cur.execute("DELETE FROM market_quotes")
                cur.execute("DELETE FROM portfolios")
                cur.execute("DELETE FROM users")
            conn.commit()

    def _portfolio_from_row(self, cur: Any, row: Any) -> Portfolio:
        payload = decrypt_json(row[5]) if row[5] else {}
        portfolio_id = str(row[0])
        return Portfolio(
            id=portfolio_id,
            user_id=str(row[1]) if row[1] is not None else None,
            name=str(payload.get("name") or row[2]),
            base_currency=row[3],
            cash=_float(payload.get("cash", row[4])),
            positions=self._load_positions(cur, portfolio_id),
            lots=self._load_lots(cur, portfolio_id),
            background_jobs=self._load_jobs(cur, portfolio_id),
            created_at=row[6],
            updated_at=row[7],
        )

    def _connect(self):
        import psycopg

        last_error: Exception | None = None
        for _ in range(30):
            try:
                return psycopg.connect(self.database_url)
            except psycopg.OperationalError as exc:
                last_error = exc
                time.sleep(0.5)
        if last_error is not None:
            raise last_error
        return psycopg.connect(self.database_url)

    def _ensure_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(schema_path.read_text())
            conn.commit()

    def _insert_positions(self, cur: Any, portfolio_id: str, positions: list[Position]) -> None:
        for position in positions:
            symbol_hash = ticker_lookup_hash(position.symbol)
            cur.execute(
                """
                INSERT INTO portfolio_positions
                    (portfolio_id, symbol, symbol_hash, asset_class, quantity, price, market_value,
                     cost_basis, average_cost, unrealized_gain_loss, lots_count, encrypted_payload, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    portfolio_id,
                    symbol_hash,
                    symbol_hash,
                    "encrypted",
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    encrypt_json(_position_payload(position)),
                    datetime.now(timezone.utc),
                ),
            )

    def _insert_lots(self, cur: Any, portfolio_id: str, lots: list[PositionLot]) -> None:
        for lot in lots:
            symbol_hash = ticker_lookup_hash(lot.symbol)
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                INSERT INTO position_lots
                    (id, portfolio_id, symbol, symbol_hash, asset_class, quantity, remaining_quantity,
                     purchase_price, current_price, fees, purchased_at, source, notes,
                     encrypted_payload, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s)
                """,
                (
                    lot.id,
                    portfolio_id,
                    symbol_hash,
                    symbol_hash,
                    "encrypted",
                    1,
                    1,
                    1,
                    1,
                    0,
                    now,
                    lot.source,
                    encrypt_json(_lot_payload(lot)),
                    now,
                    now,
                ),
            )

    def _load_positions(self, cur: Any, portfolio_id: str) -> list[Position]:
        cur.execute(
            """
            SELECT symbol, quantity, price, asset_class, cost_basis, average_cost,
                   unrealized_gain_loss, lots_count, encrypted_payload
            FROM portfolio_positions
            WHERE portfolio_id = %s
            ORDER BY symbol
            """,
            (portfolio_id,),
        )
        positions: list[Position] = []
        for row in cur.fetchall():
            if row[8]:
                payload = decrypt_json(row[8])
                positions.append(_position_from_payload(payload))
                continue
            positions.append(
                Position(
                    symbol=row[0],
                    quantity=_float(row[1]),
                    price=_float(row[2]),
                    asset_class=row[3],
                    cost_basis=_float(row[4]),
                    average_cost=_float(row[5]),
                    unrealized_gain_loss=_float(row[6]),
                    lots_count=int(row[7]),
                )
            )
        return positions

    def _load_lots(self, cur: Any, portfolio_id: str) -> list[PositionLot]:
        cur.execute(
            """
            SELECT id, symbol, quantity, purchase_price, current_price, asset_class, fees,
                   remaining_quantity, purchased_at, source, notes, encrypted_payload
            FROM position_lots
            WHERE portfolio_id = %s
            ORDER BY symbol, purchased_at, id
            """,
            (portfolio_id,),
        )
        lots: list[PositionLot] = []
        for row in cur.fetchall():
            if row[11]:
                payload = decrypt_json(row[11])
                lots.append(_lot_from_payload(str(row[0]), row[8], row[9], payload))
                continue
            lots.append(
                PositionLot(
                    id=str(row[0]),
                    symbol=row[1],
                    quantity=_float(row[2]),
                    purchase_price=_float(row[3]),
                    current_price=_float(row[4]),
                    asset_class=row[5],
                    fees=_float(row[6]),
                    remaining_quantity=_float(row[7]),
                    purchased_at=row[8],
                    source=row[9],
                    notes=row[10],
                )
            )
        return lots

    def _load_jobs(self, cur: Any, portfolio_id: str) -> list[BackgroundJob]:
        cur.execute(
            """
            SELECT id, portfolio_id, job_type, status, message, created_at, updated_at
            FROM background_jobs
            WHERE portfolio_id = %s
            ORDER BY created_at, id
            """,
            (portfolio_id,),
        )
        return [_job_from_row(row) for row in cur.fetchall()]

    def _touch_portfolio(self, cur: Any, portfolio_id: str) -> None:
        cur.execute(
            "UPDATE portfolios SET updated_at = %s WHERE id = %s",
            (datetime.now(timezone.utc), portfolio_id),
        )


def create_portfolio_repository() -> InMemoryPortfolioRepository | PostgresPortfolioRepository:
    repository_kind = os.getenv("PORTFOLIO_REPOSITORY", "memory").strip().lower()
    if repository_kind == "postgres":
        return PostgresPortfolioRepository()
    return InMemoryPortfolioRepository()


def _position_payload(position: Position) -> dict[str, Any]:
    return {
        "symbol": position.symbol,
        "quantity": position.quantity,
        "price": position.price,
        "asset_class": position.asset_class,
        "cost_basis": position.cost_basis,
        "average_cost": position.average_cost,
        "unrealized_gain_loss": position.unrealized_gain_loss,
        "lots_count": position.lots_count,
    }


def _position_from_payload(payload: dict[str, Any]) -> Position:
    return Position(
        symbol=str(payload["symbol"]),
        quantity=_float(payload["quantity"]),
        price=_float(payload["price"]),
        asset_class=str(payload.get("asset_class") or "equity"),
        cost_basis=_float(payload.get("cost_basis")),
        average_cost=_float(payload.get("average_cost")),
        unrealized_gain_loss=_float(payload.get("unrealized_gain_loss")),
        lots_count=int(payload.get("lots_count") or 0),
    )


def _lot_payload(lot: PositionLot) -> dict[str, Any]:
    return {
        "symbol": lot.symbol,
        "quantity": lot.quantity,
        "purchase_price": lot.purchase_price,
        "current_price": lot.current_price,
        "asset_class": lot.asset_class,
        "fees": lot.fees,
        "remaining_quantity": lot.remaining_quantity,
        "purchased_at": lot.purchased_at.isoformat(),
        "source": lot.source,
        "notes": lot.notes,
    }


def _lot_from_payload(lot_id: str, purchased_at: datetime, source: str, payload: dict[str, Any]) -> PositionLot:
    parsed_purchased_at = payload.get("purchased_at") or purchased_at
    if isinstance(parsed_purchased_at, str):
        parsed_purchased_at = datetime.fromisoformat(parsed_purchased_at.replace("Z", "+00:00"))
    return PositionLot(
        id=lot_id,
        symbol=str(payload["symbol"]),
        quantity=_float(payload["quantity"]),
        purchase_price=_float(payload["purchase_price"]),
        current_price=_float(payload["current_price"]),
        asset_class=str(payload.get("asset_class") or "equity"),
        fees=_float(payload.get("fees")),
        remaining_quantity=_float(payload.get("remaining_quantity")),
        purchased_at=parsed_purchased_at,
        source=str(payload.get("source") or source),
        notes=payload.get("notes"),
    )



def _cash_transaction_payload(transaction: CashTransaction) -> dict[str, Any]:
    return {
        "transaction_type": transaction.transaction_type,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "occurred_at": transaction.occurred_at.isoformat(),
        "source": transaction.source,
        "notes": transaction.notes,
    }


def _cash_transaction_from_row(row: Any) -> CashTransaction:
    if row[8]:
        payload = decrypt_json(row[8])
        return _cash_transaction_from_payload(str(row[0]), str(row[1]), row[5], row[9], payload)
    return CashTransaction(
        id=str(row[0]),
        portfolio_id=str(row[1]),
        transaction_type=str(row[2]),
        amount=_float(row[3]),
        currency=str(row[4]),
        occurred_at=row[5],
        source=str(row[6]),
        notes=row[7],
        created_at=row[9],
    )


def _cash_transaction_from_payload(
    transaction_id: str,
    portfolio_id: str,
    occurred_at: datetime,
    created_at: datetime,
    payload: dict[str, Any],
) -> CashTransaction:
    parsed_occurred_at = _parse_datetime(payload.get("occurred_at") or occurred_at)
    return CashTransaction(
        id=transaction_id,
        portfolio_id=portfolio_id,
        transaction_type=str(payload["transaction_type"]),
        amount=_float(payload["amount"]),
        currency=str(payload.get("currency") or "USD"),
        occurred_at=parsed_occurred_at,
        source=str(payload.get("source") or "manual"),
        notes=payload.get("notes"),
        created_at=created_at,
    )


def _trade_transaction_payload(transaction: TradeTransaction) -> dict[str, Any]:
    return {
        "symbol": transaction.symbol,
        "side": transaction.side,
        "quantity": transaction.quantity,
        "price": transaction.price,
        "fees": transaction.fees,
        "asset_class": transaction.asset_class,
        "occurred_at": transaction.occurred_at.isoformat(),
        "realized_gain_loss": transaction.realized_gain_loss,
        "lot_ids": transaction.lot_ids,
        "source": transaction.source,
        "notes": transaction.notes,
    }


def _trade_transaction_from_row(row: Any) -> TradeTransaction:
    if row[14]:
        payload = decrypt_json(row[14])
        return _trade_transaction_from_payload(str(row[0]), str(row[1]), row[9], row[15], payload)
    return TradeTransaction(
        id=str(row[0]),
        portfolio_id=str(row[1]),
        symbol=str(row[2]),
        side=str(row[4]),
        quantity=_float(row[5]),
        price=_float(row[6]),
        fees=_float(row[7]),
        asset_class=str(row[8]),
        occurred_at=row[9],
        realized_gain_loss=_float(row[10]) if row[10] is not None else None,
        lot_ids=[],
        source=str(row[12]),
        notes=row[13],
        created_at=row[15],
    )


def _trade_transaction_from_payload(
    transaction_id: str,
    portfolio_id: str,
    occurred_at: datetime,
    created_at: datetime,
    payload: dict[str, Any],
) -> TradeTransaction:
    parsed_occurred_at = _parse_datetime(payload.get("occurred_at") or occurred_at)
    lot_ids = payload.get("lot_ids") or []
    return TradeTransaction(
        id=transaction_id,
        portfolio_id=portfolio_id,
        symbol=str(payload["symbol"]),
        side=str(payload["side"]),
        quantity=_float(payload["quantity"]),
        price=_float(payload["price"]),
        fees=_float(payload.get("fees")),
        asset_class=str(payload.get("asset_class") or "equity"),
        occurred_at=parsed_occurred_at,
        realized_gain_loss=(
            _float(payload.get("realized_gain_loss"))
            if payload.get("realized_gain_loss") is not None
            else None
        ),
        lot_ids=[str(lot_id) for lot_id in lot_ids],
        source=str(payload.get("source") or "manual"),
        notes=payload.get("notes"),
        created_at=created_at,
    )


def _settings_payload(settings: PortfolioSettings) -> dict[str, Any]:
    return {
        "risk_free_rate": settings.risk_free_rate,
        "benchmark_symbols": settings.benchmark_symbols,
        "cash_target_pct": settings.cash_target_pct,
        "updated_at": settings.updated_at.isoformat(),
    }


def _settings_from_row(row: Any) -> PortfolioSettings:
    if row[4]:
        payload = decrypt_json(row[4])
        return PortfolioSettings(
            portfolio_id=str(row[0]),
            risk_free_rate=_float(payload.get("risk_free_rate", row[1])),
            benchmark_symbols=[str(symbol).strip().upper() for symbol in payload.get("benchmark_symbols", [])],
            cash_target_pct=(
                _float(payload.get("cash_target_pct"))
                if payload.get("cash_target_pct") is not None
                else None
            ),
            updated_at=_parse_datetime(payload.get("updated_at") or row[5]),
        )
    benchmarks = [symbol for symbol in str(row[2] or "").split(",") if symbol]
    return PortfolioSettings(
        portfolio_id=str(row[0]),
        risk_free_rate=_float(row[1]),
        benchmark_symbols=benchmarks,
        cash_target_pct=_float(row[3]) if row[3] is not None else None,
        updated_at=row[5],
    )


def _valuation_snapshot_payload(snapshot: PortfolioValuationSnapshot) -> dict[str, Any]:
    return {
        "as_of": snapshot.as_of.isoformat(),
        "market_value": snapshot.market_value,
        "cash": snapshot.cash,
        "total_equity": snapshot.total_equity,
        "net_contributions": snapshot.net_contributions,
        "metadata": snapshot.metadata,
    }


def _valuation_snapshot_from_row(row: Any) -> PortfolioValuationSnapshot:
    if row[8]:
        payload = decrypt_json(row[8])
        return PortfolioValuationSnapshot(
            id=str(row[0]),
            portfolio_id=str(row[1]),
            as_of=_parse_datetime(payload.get("as_of") or row[2]),
            market_value=_float(payload.get("market_value")),
            cash=_float(payload.get("cash")),
            total_equity=_float(payload.get("total_equity")),
            net_contributions=_float(payload.get("net_contributions")),
            metadata=dict(payload.get("metadata") or {}),
            created_at=row[9],
        )
    return PortfolioValuationSnapshot(
        id=str(row[0]),
        portfolio_id=str(row[1]),
        as_of=row[2],
        market_value=_float(row[3]),
        cash=_float(row[4]),
        total_equity=_float(row[5]),
        net_contributions=_float(row[6]),
        metadata={},
        created_at=row[9],
    )


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _float(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _normalize_tickers(tickers: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        clean = str(ticker).strip().upper()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized


def _user_from_row(row: Any) -> User:
    payload = decrypt_json(row[1]) if row[1] else {}
    email = str(payload.get("email") or row[2] or "")
    return User(
        id=str(row[0]),
        email=email,
        password_hash=row[3],
        email_verified_at=row[4],
        created_at=row[5],
        updated_at=row[6],
    )


def _auth_token_from_row(row: Any) -> AuthTokenRecord:
    return AuthTokenRecord(
        id=str(row[0]),
        user_id=str(row[1]),
        token_hash=row[2],
        token_type=row[3],
        expires_at=row[4],
        consumed_at=row[5],
        revoked_at=row[6],
        created_at=row[7],
        updated_at=row[8],
    )


def _market_quote_from_row(row: Any) -> MarketQuote:
    return MarketQuote(
        ticker=str(row[0]),
        provider=str(row[1]),
        price=_float(row[2]),
        previous_close=_float(row[3]) if row[3] is not None else None,
        daily_return_pct=_float(row[4]) if row[4] is not None else None,
        currency=row[5],
        sector=row[6],
        industry=row[7],
        fetched_at=row[8],
        updated_at=row[9],
    )


def _option_chain_history_snapshot_from_row(row: Any) -> OptionChainHistorySnapshot:
    payload = row[6]
    if isinstance(payload, str):
        payload = json.loads(payload)
    return OptionChainHistorySnapshot(
        id=str(row[0]),
        ticker=str(row[1]),
        provider=str(row[2]),
        expiry=row[3],
        fetched_at=row[4],
        snapshot_hash=str(row[5]),
        payload=dict(payload or {}),
        created_at=row[7],
    )


def _job_from_row(row: Any) -> BackgroundJob:
    return BackgroundJob(
        id=str(row[0]),
        portfolio_id=str(row[1]),
        job_type=row[2],
        status=row[3],
        message=row[4],
        created_at=row[5],
        updated_at=row[6],
    )
