from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


BUY_ENERGY = "buy_energy"
PROVIDE_ENERGY = "provide_energy"
FAQ = "faq"
OUR_TOOLS = "our_tools"
ENTER_ADDRESS = "enter_address"
WALLET_CONNECT = "wallet_connect_stub"


MAIN_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔋 Buy Energy", callback_data=BUY_ENERGY)],
        [InlineKeyboardButton(text="⚡ Provide Energy", callback_data=PROVIDE_ENERGY)],
        [InlineKeyboardButton(text="❓ FAQ", callback_data=FAQ)],
        [InlineKeyboardButton(text="⭐ Our Tools", callback_data=OUR_TOOLS)],
    ]
)


BUY_ENERGY_START_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Connect Wallet (WalletConnect)", callback_data=WALLET_CONNECT)],
        [InlineKeyboardButton(text="✍️ Enter Address Manually", callback_data=ENTER_ADDRESS)],
    ]
)


def energy_packages_kb(packages: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """Build keyboard rows of (id, label)."""
    inline_keyboard = [
        [InlineKeyboardButton(text=label, callback_data=f"pkg:{pkg_id}")]
        for pkg_id, label in packages
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
