import logging
from dataclasses import dataclass
from typing import List

import aiohttp

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class EnergyPackage:
    id: int
    energy_amount: int
    base_price_trx: float


async def get_energy_packages() -> List[EnergyPackage]:
    """Retrieve energy packages from tronsave.io."""
    api_base = settings.tronsave_api_base.rstrip("/")
    url = f"{api_base}/api/energy-packages"
    headers: dict[str, str] = {}
    if settings.tronsave_api_key:
        headers["Authorization"] = f"Bearer {settings.tronsave_api_key}"

    packages: list[EnergyPackage] = []
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to fetch energy packages from tronsave.io; falling back to defaults")
            fallback = [
                (1, 65_000, 2.21),
                (2, 131_000, 4.45),
                (3, 262_000, 8.91),
                (4, 393_000, 13.36),
                (5, 524_000, 17.82),
                (6, 655_000, 22.27),
            ]
            return [EnergyPackage(id=item[0], energy_amount=item[1], base_price_trx=item[2]) for item in fallback]

    for entry in data if isinstance(data, list) else data.get("data", []):
        try:
            pkg_id = int(entry.get("id") or entry.get("packageId"))
            energy_amount = int(entry.get("energy") or entry.get("energy_amount"))
            price = float(entry.get("price_trx") or entry.get("price") or entry.get("base_price_trx"))
        except (TypeError, ValueError):
            logger.warning("Skipping malformed package entry: %s", entry)
            continue
        packages.append(EnergyPackage(id=pkg_id, energy_amount=energy_amount, base_price_trx=price))

    if not packages:
        logger.warning("No packages returned from tronsave.io; using fallback defaults")
        fallback = [
            (1, 65_000, 2.21),
            (2, 131_000, 4.45),
            (3, 262_000, 8.91),
            (4, 393_000, 13.36),
            (5, 524_000, 17.82),
            (6, 655_000, 22.27),
        ]
        return [EnergyPackage(id=item[0], energy_amount=item[1], base_price_trx=item[2]) for item in fallback]
    return packages


async def delegate_energy(wallet_address: str, energy_amount: int) -> None:
    """Delegate purchased energy to the target wallet via tronsave.io."""
    api_base = settings.tronsave_api_base.rstrip("/")
    url = f"{api_base}/api/delegate-energy"
    payload = {"wallet": wallet_address, "energy": energy_amount}
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.tronsave_api_key:
        headers["Authorization"] = f"Bearer {settings.tronsave_api_key}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                resp.raise_for_status()
                await resp.json()
                logger.info("Delegated %s energy to %s", energy_amount, wallet_address)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to delegate energy via tronsave.io for wallet %s", wallet_address)
