from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from tradesentry_api.audit_store import AuditEvent
from tradesentry_api.config import Settings
from tradesentry_api.services import Services

from models.cross_ibu import RegistrySignal

SEED_ROWS = (
    (
        "IBU-A",
        "BL789456",
        "ocean_star",
        "V123",
        "abc_trading",
        "INMUN",
        "SGSIN",
        "rice",
        "500",
        "2024-08-14",
    ),
    (
        "IBU-B",
        "BL-002",
        "sea_eagle",
        "V456",
        "def_trading",
        "INKLA",
        "MYPKG",
        "wheat",
        "800",
        "2024-08-20",
    ),
    (
        "IBU-C",
        "BL789456",
        "ocean_star",
        "V123",
        "abc_trading",
        "INMUN",
        "SGSIN",
        "rice",
        "500",
        "2024-08-14",
    ),
    (
        "IBU-C",
        "BL-LEGIT-099",
        "sea_breeze",
        "V900",
        "abc_trading",
        "INMUN",
        "LKCMB",
        "rice",
        "300",
        "2024-09-01",
    ),
    (
        "IBU-A",
        "BL-003",
        "evergreen",
        "V210",
        "ghi",
        "INMAA",
        "AEDXB",
        "cotton",
        "1200",
        "2024-08-10",
    ),
    (
        "IBU-B",
        "BL-004",
        "pearl_ocean",
        "V311",
        "jkl_trading",
        "INHAZ",
        "NLRTM",
        "spices",
        "200",
        "2024-08-18",
    ),
    (
        "IBU-C",
        "BL-005",
        "new_horizon",
        "V415",
        "mno_exports",
        "INMUN",
        "AEJEA",
        "steel",
        "5000",
        "2024-08-22",
    ),
    (
        "IBU-A",
        "BL-006",
        "atlantic",
        "V519",
        "pqr_goods",
        "INNSA",
        "DEHAM",
        "textiles",
        "900",
        "2024-08-25",
    ),
)


def _signal(index: int, row: tuple[str, ...]) -> RegistrySignal:
    ibu, bl, vessel, voyage, exporter, loading, discharge, commodity, quantity, shipped = row
    fingerprint = hashlib.sha256(
        f"{bl}{vessel}{voyage}{loading}{discharge}{shipped}{exporter}".encode()
    ).hexdigest()
    return RegistrySignal(
        ibu_id=ibu,
        case_id=f"REGISTRY-SEED-{index + 1:03d}",
        transaction_id=f"seed-txn-{index + 1:03d}",
        dna_fingerprint=fingerprint,
        bl_number_normalized=bl,
        vessel_normalized=vessel,
        voyage_normalized=voyage,
        exporter_normalized=exporter,
        loading_port_unlocode=loading,
        discharge_port_unlocode=discharge,
        shipment_date_iso=shipped,
        commodity_normalized=commodity,
        quantity_canonical=Decimal(quantity),
        unit_canonical="MT",
    )


async def main() -> None:
    services = Services.build(Settings.from_env())
    try:
        started = datetime.now(UTC)
        for index, row in enumerate(SEED_ROWS):
            registered_at = started + timedelta(microseconds=index)
            registration = await services.cross_ibu_registry.register(
                _signal(index, row), registered_at
            )
            await services.audit_store.record(
                AuditEvent(
                    case_id=None,
                    actor_id="registry-seed",
                    event_type="CROSS_IBU_REGISTERED",
                    payload_ref=f"registry://{registration.registration_id}",
                    created_at=registered_at,
                )
            )
        print("Seeded 8 normalized synthetic cross-IBU registry signals")
    finally:
        await services.close()


if __name__ == "__main__":
    asyncio.run(main())
