import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot

from . import db
from .config import settings
from .tronsave_client import delegate_energy

logger = logging.getLogger(__name__)


async def check_payment(invoice: db.Invoice) -> bool:
    """
    Placeholder payment checker.

    TODO: Integrate real Tron payment detection via TronGrid or webhook listener.
    """
    if not settings.simulate_payments:
        return False

    # Simulate a successful payment 1 minute after invoice creation.
    now = datetime.now(timezone.utc)
    return now - invoice.created_at >= timedelta(minutes=1)


async def handle_pending_invoices(bot: Bot) -> None:
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

        paid = await check_payment(invoice)
        if paid:
            logger.info("Invoice %s marked as paid (simulated)", invoice.id)
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
    while True:
        try:
            await handle_pending_invoices(bot)
        except Exception:  # noqa: BLE001
            logger.exception("Error while checking pending invoices")
        await asyncio.sleep(settings.payment_check_interval.total_seconds())
