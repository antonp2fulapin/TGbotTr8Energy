import logging
import os
from dataclasses import dataclass
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def str_to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    bot_token: str
    commission_percent: float
    database_path: str
    payment_check_interval: timedelta
    simulate_payments: bool
    payment_receiver_address: str
    tron_api_base: str
    tron_api_key: str
    tronsave_api_base: str
    tronsave_api_key: str
    tronsave_duration_sec: int
    tronsave_unit_price: str
    tronsave_allow_partial_fill: bool
    tronsave_min_delegate_amount: int


settings = Settings(
    bot_token=os.getenv("BOT_TOKEN", ""),
    commission_percent=float(os.getenv("COMMISSION_PERCENT", "10")),
    database_path=os.getenv("DATABASE_PATH", "bot_data.sqlite3"),
    payment_check_interval=timedelta(
        seconds=int(os.getenv("PAYMENT_CHECK_INTERVAL_SEC", "30"))
    ),
    simulate_payments=str_to_bool(os.getenv("SIMULATE_PAYMENTS"), default=True),
    payment_receiver_address=os.getenv("PAYMENT_RECEIVER_ADDRESS", ""),
    tron_api_base=os.getenv("TRON_API_BASE", "https://api.trongrid.io"),
    tron_api_key=os.getenv("TRON_API_KEY", ""),
    tronsave_api_base=os.getenv("TRONSAVE_API_BASE", "https://api.tronsave.io"),
    tronsave_api_key=os.getenv("TRONSAVE_API_KEY", ""),
    tronsave_duration_sec=int(os.getenv("TRONSAVE_DURATION_SEC", "259200")),
    tronsave_unit_price=os.getenv("TRONSAVE_UNIT_PRICE", "MEDIUM"),
    tronsave_allow_partial_fill=str_to_bool(os.getenv("TRONSAVE_ALLOW_PARTIAL_FILL"), True),
    tronsave_min_delegate_amount=int(os.getenv("TRONSAVE_MIN_DELEGATE_AMOUNT", "32000")),
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s",
)
