from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from models.cross_ibu import RegistryRegistration, RegistrySignal
from models.dna import TransactionDNA


def signal_from_dna(dna: TransactionDNA) -> RegistrySignal:
    """Project DNA onto the approved cross-IBU signal allow-list."""
    return RegistrySignal(
        ibu_id=dna.presenting_ibu,
        case_id=dna.case_id,
        transaction_id=dna.transaction_id,
        dna_fingerprint=dna.dna_fingerprint,
        bl_number_normalized=dna.bl_number_normalized,
        vessel_normalized=dna.vessel_normalized,
        voyage_normalized=dna.voyage_normalized,
        exporter_normalized=dna.exporter_normalized,
        loading_port_unlocode=dna.loading_port_unlocode,
        discharge_port_unlocode=dna.discharge_port_unlocode,
        shipment_date_iso=dna.shipment_date_iso,
        commodity_normalized=dna.commodity_normalized,
        quantity_canonical=dna.quantity_canonical,
        unit_canonical=dna.unit_canonical,
    )


def registration_from_signal(
    signal: RegistrySignal, registered_at: datetime, ttl_days: int
) -> RegistryRegistration:
    digest = hashlib.sha256(f"{signal.ibu_id}:{signal.dna_fingerprint}".encode()).hexdigest()[:24]
    return RegistryRegistration(
        **signal.model_dump(),
        registration_id=f"reg-{digest}",
        registered_at=registered_at,
        ttl=int((registered_at + timedelta(days=ttl_days)).timestamp()),
    )
