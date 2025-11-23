import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import aiosqlite

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class Invoice:
    id: int
    user_id: int
    wallet_address: str
    energy_amount: int
    base_price_trx: float
    final_price_trx: float
    unique_payment_address: str
    created_at: datetime
    expires_at: datetime
    status: str


async def init_db() -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                wallet_address TEXT NOT NULL,
                energy_amount INTEGER NOT NULL,
                base_price_trx REAL NOT NULL,
                final_price_trx REAL NOT NULL,
                unique_payment_address TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """
        )
        await db.commit()
    logger.info("Database initialized at %s", settings.database_path)


async def upsert_user(user_id: int, first_name: str, username: Optional[str]) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, first_name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name=excluded.first_name,
                username=excluded.username
            """,
            (user_id, first_name, username),
        )
        await db.commit()


async def create_invoice(
    user_id: int,
    wallet_address: str,
    energy_amount: int,
    base_price_trx: float,
    final_price_trx: float,
    unique_payment_address: str,
    validity_minutes: int = 20,
) -> Invoice:
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(minutes=validity_minutes)
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute(
            """
            INSERT INTO invoices (
                user_id, wallet_address, energy_amount, base_price_trx,
                final_price_trx, unique_payment_address, created_at, expires_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                user_id,
                wallet_address,
                energy_amount,
                base_price_trx,
                final_price_trx,
                unique_payment_address,
                created_at.isoformat(),
                expires_at.isoformat(),
            ),
        )
        await db.commit()
        invoice_id = cursor.lastrowid
    return Invoice(
        id=invoice_id,
        user_id=user_id,
        wallet_address=wallet_address,
        energy_amount=energy_amount,
        base_price_trx=base_price_trx,
        final_price_trx=final_price_trx,
        unique_payment_address=unique_payment_address,
        created_at=created_at,
        expires_at=expires_at,
        status="pending",
    )


async def get_pending_invoices() -> List[Invoice]:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, wallet_address, energy_amount, base_price_trx,
                   final_price_trx, unique_payment_address, created_at, expires_at, status
            FROM invoices
            WHERE status = 'pending'
            """
        )
        rows = await cursor.fetchall()
    invoices: List[Invoice] = []
    for row in rows:
        invoices.append(
            Invoice(
                id=row[0],
                user_id=row[1],
                wallet_address=row[2],
                energy_amount=row[3],
                base_price_trx=row[4],
                final_price_trx=row[5],
                unique_payment_address=row[6],
                created_at=datetime.fromisoformat(row[7]),
                expires_at=datetime.fromisoformat(row[8]),
                status=row[9],
            )
        )
    return invoices


async def mark_invoice_paid(invoice_id: int) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE invoices SET status='paid' WHERE id=?",
            (invoice_id,),
        )
        await db.commit()


async def mark_invoice_expired(invoice_id: int) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE invoices SET status='expired' WHERE id=?",
            (invoice_id,),
        )
        await db.commit()
