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


settings = Settings(
    bot_token=os.getenv("BOT_TOKEN", ""),
    commission_percent=float(os.getenv("COMMISSION_PERCENT", "10")),
    database_path=os.getenv("DATABASE_PATH", "bot_data.sqlite3"),
    payment_check_interval=timedelta(
        seconds=int(os.getenv("PAYMENT_CHECK_INTERVAL_SEC", "30"))
    ),
    simulate_payments=str_to_bool(os.getenv("SIMULATE_PAYMENTS"), default=True),
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s",
)
