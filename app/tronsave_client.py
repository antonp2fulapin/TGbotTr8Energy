import logging
from dataclasses import dataclass
from typing import Any, Dict, List

import aiohttp

from .config import settings

logger = logging.getLogger(__name__)


_ENERGY_PRESETS = [65_000, 131_000, 262_000, 393_000, 524_000, 655_000]


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.tronsave_api_key:
        headers["apikey"] = settings.tronsave_api_key
    return headers


@dataclass
class EnergyPackage:
    id: int
    energy_amount: int
    base_price_trx: float
    unit_price: str | int


async def _get_account_info(session: aiohttp.ClientSession) -> Dict[str, Any] | None:
    url = f"{settings.tronsave_api_base.rstrip('/')}/v2/user-info"
    try:
        async with session.get(url, headers=_headers(), timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch tronsave.io account info")
        return None

    if data.get("error"):
        logger.warning("tronsave.io account info error: %s", data.get("message"))
        return None
    return data.get("data")


async def get_account_info() -> Dict[str, Any] | None:
    async with aiohttp.ClientSession() as session:
        return await _get_account_info(session)


async def get_order_book(
    receiver: str,
    *,
    min_delegate_amount: int | None = None,
    duration_sec: int | None = None,
    resource_type: str = "ENERGY",
) -> Dict[str, Any] | None:
    url = f"{settings.tronsave_api_base.rstrip('/')}/v2/order-book"
    params: dict[str, Any] = {"address": receiver, "resourceType": resource_type}
    if min_delegate_amount:
        params["minDelegateAmount"] = min_delegate_amount
    if duration_sec:
        params["durationSec"] = duration_sec

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params, headers=_headers(), timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                resp.raise_for_status()
                payload = await resp.json()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch tronsave.io order book")
        return None

    if payload.get("error"):
        logger.warning("tronsave.io order book error: %s", payload.get("message"))
        return None
    return payload.get("data")


async def _estimate_with_session(
    session: aiohttp.ClientSession,
    *,
    resource_amount: int,
    receiver: str,
    duration_sec: int,
    unit_price: str | int,
    allow_partial_fill: bool,
    min_delegate_amount: int,
) -> dict[str, Any]:
    url = f"{settings.tronsave_api_base.rstrip('/')}/v2/estimate-buy-resource"
    payload: dict[str, Any] = {
        "resourceType": "ENERGY",
        "receiver": receiver,
        "durationSec": duration_sec,
        "resourceAmount": resource_amount,
        "unitPrice": unit_price,
        "options": {
            "allowPartialFill": allow_partial_fill,
            "minResourceDelegateRequiredAmount": min_delegate_amount,
        },
    }

    async with session.post(
        url,
        json=payload,
        headers=_headers(),
        timeout=aiohttp.ClientTimeout(total=15),
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()

    if data.get("error"):
        raise RuntimeError(data.get("message", "Unknown tronsave.io estimate error"))
    return data.get("data", {})


async def estimate_buy_resource(
    *,
    resource_amount: int,
    receiver: str,
    duration_sec: int | None = None,
    unit_price: str | int | None = None,
    allow_partial_fill: bool | None = None,
    min_delegate_amount: int | None = None,
) -> dict[str, Any] | None:
    duration = duration_sec or settings.tronsave_duration_sec
    price = unit_price or settings.tronsave_unit_price
    allow_partial = settings.tronsave_allow_partial_fill if allow_partial_fill is None else allow_partial_fill
    min_delegate = min_delegate_amount or settings.tronsave_min_delegate_amount

    try:
        async with aiohttp.ClientSession() as session:
            return await _estimate_with_session(
                session,
                resource_amount=resource_amount,
                receiver=receiver,
                duration_sec=duration,
                unit_price=price,
                allow_partial_fill=allow_partial,
                min_delegate_amount=min_delegate,
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to estimate buy-resource: %s", exc)
        return None


async def get_energy_packages(receiver_address: str) -> List[EnergyPackage]:
    """Retrieve energy packages using tronsave.io estimates; fallback to defaults."""
    if not settings.tronsave_api_key:
        logger.warning("TRONSAVE_API_KEY is not configured; using fallback packages")
        return [
            EnergyPackage(id=i + 1, energy_amount=amt, base_price_trx=price, unit_price="MEDIUM")
            for i, (amt, price) in enumerate(
                zip(
                    _ENERGY_PRESETS,
                    [2.21, 4.45, 8.91, 13.36, 17.82, 22.27],
                )
            )
        ]

    packages: list[EnergyPackage] = []
    async with aiohttp.ClientSession() as session:
        for idx, amount in enumerate(_ENERGY_PRESETS, start=1):
            try:
                estimate = await _estimate_with_session(
                    session,
                    resource_amount=amount,
                    receiver=receiver_address,
                    duration_sec=settings.tronsave_duration_sec,
                    unit_price=settings.tronsave_unit_price,
                    allow_partial_fill=settings.tronsave_allow_partial_fill,
                    min_delegate_amount=settings.tronsave_min_delegate_amount,
                )
                estimate_trx = (estimate.get("estimateTrx") or 0) / 1_000_000
                packages.append(
                    EnergyPackage(
                        id=idx,
                        energy_amount=amount,
                        base_price_trx=estimate_trx,
                        unit_price=estimate.get("unitPrice", settings.tronsave_unit_price),
                    )
                )
            except Exception:  # noqa: BLE001
                logger.exception("Failed to estimate package for %s energy", amount)
                continue

    if not packages:
        logger.warning("No packages could be estimated; falling back to defaults")
        return [
            EnergyPackage(id=i + 1, energy_amount=amt, base_price_trx=price, unit_price="MEDIUM")
            for i, (amt, price) in enumerate(
                zip(
                    _ENERGY_PRESETS,
                    [2.21, 4.45, 8.91, 13.36, 17.82, 22.27],
                )
            )
        ]
    return packages


async def buy_resource(
    *,
    resource_amount: int,
    receiver: str,
    duration_sec: int | None = None,
    unit_price: str | int | None = None,
    allow_partial_fill: bool | None = None,
    only_create_when_fulfilled: bool = False,
    min_delegate_amount: int | None = None,
    max_price_accepted: int | None = None,
    prevent_duplicate_incomplete: bool = False,
) -> dict[str, Any] | None:
    url = f"{settings.tronsave_api_base.rstrip('/')}/v2/buy-resource"
    payload: dict[str, Any] = {
        "resourceType": "ENERGY",
        "unitPrice": unit_price or settings.tronsave_unit_price,
        "resourceAmount": resource_amount,
        "receiver": receiver,
        "durationSec": duration_sec or settings.tronsave_duration_sec,
        "options": {
            "allowPartialFill": settings.tronsave_allow_partial_fill if allow_partial_fill is None else allow_partial_fill,
            "onlyCreateWhenFulfilled": only_create_when_fulfilled,
            "preventDuplicateIncompleteOrders": prevent_duplicate_incomplete,
        },
    }

    min_delegate = min_delegate_amount or settings.tronsave_min_delegate_amount
    if min_delegate:
        payload["options"]["minResourceDelegateRequiredAmount"] = min_delegate
    if max_price_accepted is not None:
        payload["options"]["maxPriceAccepted"] = max_price_accepted

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=_headers(), timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to create buy-resource order")
        return None

    if data.get("error"):
        logger.warning("tronsave.io buy-resource error: %s", data.get("message"))
        return None
    return data.get("data")


async def get_order_details(order_id: str) -> dict[str, Any] | None:
    base = settings.tronsave_api_base.rstrip("/")
    paths = [f"{base}/v2/orders/{order_id}", f"{base}/v2/order/{order_id}"]
    for url in paths:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=_headers(), timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 404:
                        continue
                    resp.raise_for_status()
                    data = await resp.json()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to fetch tronsave.io order details from %s", url)
            continue

        if data.get("error"):
            logger.warning("tronsave.io order details error: %s", data.get("message"))
            return None
        return data.get("data")
    return None


async def delegate_energy(wallet_address: str, energy_amount: int) -> None:
    """Delegate purchased energy to the target wallet via a buy-resource order."""
    order = await buy_resource(
        resource_amount=energy_amount,
        receiver=wallet_address,
    )
    if not order:
        logger.error("Failed to create buy-resource order for %s", wallet_address)
        return
    logger.info("Created buy-resource order %s for %s energy to %s", order.get("orderId"), energy_amount, wallet_address)
