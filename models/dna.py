from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ConflictSeverity(StrEnum):
    MATERIAL = "MATERIAL"
    ADVISORY = "ADVISORY"


class ConflictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field_name: str
    document_a_id: str
    document_a_value: str
    document_b_id: str
    document_b_value: str
    severity: ConflictSeverity


class TransactionDNA(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction_id: str
    case_id: str
    presenting_ibu: str

    raw_exporter: str | None = None
    raw_importer: str | None = None
    raw_bl_number: str | None = None
    raw_vessel_name: str | None = None
    raw_voyage_number: str | None = None
    raw_loading_port: str | None = None
    raw_discharge_port: str | None = None
    raw_shipment_date: str | None = None
    raw_commodity: str | None = None
    raw_hs_code: str | None = None
    raw_quantity: Decimal | None = None
    raw_quantity_unit: str | None = None
    raw_invoice_value: Decimal | None = None
    raw_currency: str | None = None
    raw_lc_number: str | None = None
    raw_invoice_number: str | None = None

    exporter_normalized: str | None = None
    importer_normalized: str | None = None
    bl_number_normalized: str | None = None
    vessel_normalized: str | None = None
    imo_number: str | None = None
    voyage_normalized: str | None = None
    loading_port_unlocode: str | None = None
    discharge_port_unlocode: str | None = None
    shipment_date_iso: str | None = None
    commodity_normalized: str | None = None
    hs_code_canonical: str | None = None
    quantity_canonical: Decimal | None = None
    unit_canonical: str | None = None
    invoice_value_usd: Decimal | None = None
    unit_value_usd_per_unit: Decimal | None = None

    dna_fingerprint: str
    source_documents: dict[str, str]
    normalization_methods: dict[str, str]
    confidence_flags: list[str]
    conflicts: list[ConflictRecord]
    created_at: datetime
