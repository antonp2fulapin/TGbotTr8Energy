import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
import base58
from aiogram import Bot

from . import db
from .config import settings
from .tronsave_client import delegate_energy

logger = logging.getLogger(__name__)


def _address_hex(address: str) -> Optional[str]:
    try:
        decoded = base58.b58decode_check(address)
    except Exception:  # noqa: BLE001
        logger.warning("Unable to decode TRON address %s", address)
        return None
    return decoded.hex()


async def _fetch_transactions(session: aiohttp.ClientSession, address: str, since: datetime) -> list[dict]:
    params = {
        "only_to": "true",
        "limit": 50,
        "min_timestamp": int(since.timestamp() * 1000),
    }
    headers: dict[str, str] = {}
    if settings.tron_api_key:
        headers["TRON-PRO-API-KEY"] = settings.tron_api_key

    async with session.get(
        f"{settings.tron_api_base.rstrip('/')}/v1/accounts/{address}/transactions",
        params=params,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=20),
    ) as resp:
        resp.raise_for_status()
        payload = await resp.json()
        return payload.get("data", [])


async def check_payment(invoice: db.Invoice, session: aiohttp.ClientSession) -> bool:
    """Check TronGrid for incoming payments that satisfy the invoice amount."""
    if settings.simulate_payments:
        now = datetime.now(timezone.utc)
        return now - invoice.created_at >= timedelta(minutes=1)

    if not settings.payment_receiver_address:
        logger.warning("PAYMENT_RECEIVER_ADDRESS is not configured; cannot check payments")
        return False

    receiver_hex = _address_hex(settings.payment_receiver_address)
    if receiver_hex is None:
        return False

    try:
        transactions = await _fetch_transactions(session, settings.payment_receiver_address, invoice.created_at)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch transactions for payment check")
        return False

    for tx in transactions:
        contracts = tx.get("raw_data", {}).get("contract", [])
        for contract in contracts:
            if contract.get("type") != "TransferContract":
                continue
            value = contract.get("parameter", {}).get("value", {})
            to_addr_hex = value.get("to_address")
            if isinstance(to_addr_hex, str) and to_addr_hex.startswith("0x"):
                to_addr_hex = to_addr_hex[2:]
            if not to_addr_hex:
                continue
            if to_addr_hex.lower() != receiver_hex.lower():
                continue
            amount_sun = value.get("amount", 0) or 0
            amount_trx = amount_sun / 1_000_000
            if amount_trx + 1e-8 >= invoice.final_price_trx:
                return True
    return False


async def handle_pending_invoices(bot: Bot, session: aiohttp.ClientSession) -> None:
    pending = await db.get_pending_invoices()
    now = datetime.now(timezone.utc)
    for invoice in pending:
        if invoice.expires_at <= now:
            logger.info("Invoice %s expired", invoice.id)
            await db.mark_invoice_expired(invoice.id)
            try:
                await bot.send_message(
                    invoice.user_id,
                    "❌ This invoice has expired.\nPlease create a new one.",
                )
            except Exception:  # noqa: BLE001
                logger.exception("Failed to notify user %s about expiration", invoice.user_id)
            continue

        paid = await check_payment(invoice, session)
        if paid:
            logger.info("Invoice %s marked as paid", invoice.id)
            await db.mark_invoice_paid(invoice.id)
            await delegate_energy(invoice.wallet_address, invoice.energy_amount)
            try:
                await bot.send_message(
                    invoice.user_id,
                    (
                        "✅ Payment received!\n\n"
                        f"⚡ {invoice.energy_amount} energy has been delegated to:\n"
                        f"{invoice.wallet_address}"
                    ),
                )
            except Exception:  # noqa: BLE001
                logger.exception("Failed to notify user %s about payment", invoice.user_id)


async def payment_watcher(bot: Bot) -> None:
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await handle_pending_invoices(bot, session)
            except Exception:  # noqa: BLE001
                logger.exception("Error while checking pending invoices")
            await asyncio.sleep(settings.payment_check_interval.total_seconds())
