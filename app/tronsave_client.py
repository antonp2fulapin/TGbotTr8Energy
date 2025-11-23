import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class EnergyPackage:
    id: int
    energy_amount: int
    base_price_trx: float


def get_energy_packages() -> List[EnergyPackage]:
    """
    Retrieve energy packages from tronsave.io.

    TODO: Replace mocked list with actual API request to tronsave.io endpoints.
    """
    logger.info("Retrieving energy packages from tronsave.io (mocked)")
    sample_data = [
        (1, 65_000, 2.21),
        (2, 131_000, 4.45),
        (3, 262_000, 8.91),
        (4, 393_000, 13.36),
        (5, 524_000, 17.82),
        (6, 655_000, 22.27),
    ]
    return [EnergyPackage(id=item[0], energy_amount=item[1], base_price_trx=item[2]) for item in sample_data]


async def delegate_energy(wallet_address: str, energy_amount: int) -> None:
    """
    Delegate purchased energy to the target wallet.

    TODO: Implement real delegation through tronsave.io API once available.
    """
    logger.info(
        "Delegating %s energy to wallet %s via tronsave.io (mocked)",
        energy_amount,
        wallet_address,
    )
