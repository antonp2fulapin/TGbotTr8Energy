import asyncio
import logging
import random
import re
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import db
from app.config import settings
from app.keyboards import (
    BUY_ENERGY,
    BUY_ENERGY_START_KB,
    ENTER_ADDRESS,
    FAQ,
    MAIN_MENU_KB,
    OUR_TOOLS,
    PROVIDE_ENERGY,
    WALLET_CONNECT,
    energy_packages_kb,
)
from app.payment import payment_watcher
from app.states import BuyEnergyStates, ProvideEnergyStates
from app.tron_client import get_tron_balances
from app.tronsave_client import EnergyPackage, get_energy_packages

logger = logging.getLogger(__name__)
router = Router()


TRON_ADDRESS_REGEX = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{25,33}$")


def format_wallet_info(address: str, balances: dict[str, Any]) -> str:
    return (
        f"📊 Wallet Status for {address}\n\n"
        f"💰 USDT: {balances['usdt']}\n"
        f"🔺 TRX: {balances['trx']}\n"
        f"📡 Bandwidth: {balances['bandwidth']:,}\n"
        f"⚡ Energy: {balances['energy']:,}"
    )


def format_package_label(pkg: EnergyPackage) -> str:
    final_price = pkg.base_price_trx * (1 + settings.commission_percent / 100)
    return f"{pkg.energy_amount:,} ⚡ — {final_price:.2f} TRX"


async def send_main_menu(message: Message) -> None:
    await message.answer(
        "Welcome to the TRON Energy bot! Choose an option below:",
        reply_markup=MAIN_MENU_KB,
    )


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await db.upsert_user(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name or "",
        username=message.from_user.username,
    )
    await send_main_menu(message)


@router.callback_query(F.data == BUY_ENERGY)
async def handle_buy_energy(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(
        "Choose how you want to provide your TRON wallet address:",
        reply_markup=BUY_ENERGY_START_KB,
    )
    await callback.answer()


@router.callback_query(F.data == WALLET_CONNECT)
async def handle_wallet_connect_stub(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BuyEnergyStates.waiting_for_address)
    await callback.message.answer(
        (
            "🔗 WalletConnect integration is not implemented yet.\n"
            "Please paste your TRON wallet address manually (e.g. starting with T...)."
        )
    )
    await callback.answer()


@router.callback_query(F.data == ENTER_ADDRESS)
async def handle_manual_address(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BuyEnergyStates.waiting_for_address)
    await callback.message.answer(
        "Please enter the TRON wallet address (e.g. T...) for which you want to buy energy."
    )
    await callback.answer()


@router.message(BuyEnergyStates.waiting_for_address)
async def receive_wallet_address(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    if not TRON_ADDRESS_REGEX.match(address):
        await message.answer(
            "⚠️ That doesn't look like a valid TRON address. Please try again (must start with T)."
        )
        return

    await state.update_data(wallet_address=address)
    balances = await get_tron_balances(address)
    await message.answer(format_wallet_info(address, balances))

    packages = get_energy_packages()
    labeled_packages = [(pkg.id, format_package_label(pkg)) for pkg in packages]
    await message.answer(
        "🔋 Available Energy Packages",
        reply_markup=energy_packages_kb(labeled_packages),
    )


@router.callback_query(F.data.startswith("pkg:"))
async def handle_package_selection(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    wallet_address = data.get("wallet_address")
    if not wallet_address:
        await callback.message.answer("Please provide a wallet address first.")
        await callback.answer()
        return

    package_id = int(callback.data.split(":", maxsplit=1)[1])
    packages = {pkg.id: pkg for pkg in get_energy_packages()}
    pkg = packages.get(package_id)
    if not pkg:
        await callback.message.answer("Selected package not found. Please try again.")
        await callback.answer()
        return

    commission_multiplier = 1 + settings.commission_percent / 100
    final_price = pkg.base_price_trx * commission_multiplier
    unique_payment_address = (
        f"TRX-{random.randint(100000, 999999)}"  # TODO: replace with real payment address generation
    )

    invoice = await db.create_invoice(
        user_id=callback.from_user.id,
        wallet_address=wallet_address,
        energy_amount=pkg.energy_amount,
        base_price_trx=pkg.base_price_trx,
        final_price_trx=final_price,
        unique_payment_address=unique_payment_address,
    )

    expires_local = invoice.expires_at.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    await callback.message.answer(
        (
            f"🧾 INVOICE #{invoice.id}\n\n"
            f"⚡ Energy: {invoice.energy_amount:,}\n"
            f"💵 Amount: {invoice.final_price_trx:.2f} TRX\n"
            f"⏳ Valid until: {expires_local}\n"
            "🏦 Pay to (TRX address):\n"
            f"{invoice.unique_payment_address}\n\n"
            "We will automatically check for payment."
        )
    )
    await callback.answer()


@router.callback_query(F.data == FAQ)
async def handle_faq(callback: CallbackQuery) -> None:
    faq_text = (
        "❓ FAQ\n\n"
        "• What is energy on Tron?\n"
        "  Energy pays for smart contract execution so you avoid large TRX fees.\n\n"
        "• What is bandwidth?\n"
        "  Bandwidth covers simple transactions like transfers. Most dApps need energy.\n\n"
        "• Why rent energy instead of paying TRX gas?\n"
        "  Renting is often cheaper than burning TRX per transaction.\n\n"
        "• How does this bot work?\n"
        "  We delegate energy to your wallet — no need to move your funds.\n\n"
        "• When do I need to pay?\n"
        "  Pay the invoice before it expires so we can delegate energy automatically."
    )
    await callback.message.answer(faq_text)
    await callback.answer()


@router.callback_query(F.data == OUR_TOOLS)
async def handle_tools(callback: CallbackQuery) -> None:
    tools_text = (
        "⭐ Our Tools\n"
        "https://tr8.energy\n"
        "https://usdtbulksender.com\n"
        "https://trxfree.us"
    )
    await callback.message.answer(tools_text)
    await callback.answer()


@router.callback_query(F.data == PROVIDE_ENERGY)
async def handle_provide_energy(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProvideEnergyStates.waiting_for_address)
    await callback.message.answer(
        "Enter your TRON wallet address so we can check if you can provide energy."
    )
    await callback.answer()


@router.message(ProvideEnergyStates.waiting_for_address)
async def receive_provider_address(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    if not TRON_ADDRESS_REGEX.match(address):
        await message.answer("Please send a valid TRON address starting with T.")
        return

    balances = await get_tron_balances(address)
    has_large_energy = balances.get("energy", 0) >= 100_000
    has_trx_to_stake = balances.get("trx", 0) >= 100

    if has_large_energy or has_trx_to_stake:
        response = (
            "✅ Your wallet looks ready to provide energy!\n"
            "Visit https://tr8.energy to provide energy and earn up to 23.7% APY."
        )
    else:
        response = (
            "You need more staked energy or TRX to start providing.\n"
            "Read https://trxfree.us/blog to learn how to stake and earn from energy provisioning."
        )

    await message.answer(response)
    await state.clear()


async def on_startup(bot: Bot) -> None:
    await db.init_db()
    asyncio.create_task(payment_watcher(bot))


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN must be set in the environment")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)

    logger.info("Starting bot polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
