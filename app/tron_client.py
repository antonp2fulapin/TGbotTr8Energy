import logging
from typing import Any, Dict

import aiohttp

from .config import settings

logger = logging.getLogger(__name__)

USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


async def _request_json(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    headers: dict[str, str] = {}
    if settings.tron_api_key:
        headers["TRON-PRO-API-KEY"] = settings.tron_api_key
    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        return await resp.json()


async def get_tron_balances(address: str) -> Dict[str, Any]:
    """Fetch balances and resource limits for a TRON address via TronGrid."""
    logger.info("Fetching balances for %s", address)
    async with aiohttp.ClientSession(base_url=settings.tron_api_base.rstrip("/")) as session:
        account_url = f"/v1/accounts/{address}"
        resources_url = f"/v1/accounts/{address}/resources"
        account_data = await _request_json(session, account_url)
        resources_data = await _request_json(session, resources_url)

        account = (account_data.get("data") or [{}])[0]
        raw_trx = account.get("balance", 0) or 0
        trx_balance = raw_trx / 1_000_000

        trc20_list = account.get("trc20") or []
        usdt_balance = 0.0
        for token in trc20_list:
            if USDT_CONTRACT in token:
                try:
                    usdt_balance = float(token[USDT_CONTRACT]) / 1_000_000
                except (TypeError, ValueError):
                    logger.warning("Unexpected USDT balance format for %s", address)
                break

        resources = (resources_data.get("data") or [{}])[0]
        free_bandwidth = resources.get("freeNetRemaining", 0) or 0
        paid_bandwidth = resources.get("netRemaining", 0) or 0
        bandwidth = free_bandwidth + paid_bandwidth
        energy = resources.get("energyRemaining", 0) or 0

        return {
            "usdt": round(usdt_balance, 2),
            "trx": round(trx_balance, 4),
            "bandwidth": int(bandwidth),
            "energy": int(energy),
        }
