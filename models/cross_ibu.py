from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

PROTOTYPE_THRESHOLDS_NOTE = "Prototype demo values — not regulatory standards"


class MatchLevel(StrEnum):
    EXACT = "EXACT"
    NEAR = "NEAR"
    CONTEXTUAL = "CONTEXTUAL"
    NONE = "NONE"


class CrossIBUCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str


class RegistrySignal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ibu_id: str
    case_id: str
    transaction_id: str
    dna_fingerprint: str
    bl_number_normalized: str | None = None
    vessel_normalized: str | None = None
    voyage_normalized: str | None = None
    exporter_normalized: str | None = None
    loading_port_unlocode: str | None = None
    discharge_port_unlocode: str | None = None
    shipment_date_iso: str | None = None
    commodity_normalized: str | None = None
    quantity_canonical: Decimal | None = None
    unit_canonical: str | None = None


class RegistryRegistration(RegistrySignal):
    registration_id: str
    registered_at: datetime
    ttl: int


class CrossIBUMatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    match_id: str
    querying_ibu_id: str
    querying_case_id: str
    matched_registration_id: str | None = None
    matched_ibu_id: str | None = None
    match_level: MatchLevel
    similarity_score: float = Field(ge=0.0, le=1.0)
    matched_fields: list[str]
    explanation: str
    is_false_positive_candidate: bool
    evidence_ref: str | None = None
    thresholds_note: str = PROTOTYPE_THRESHOLDS_NOTE
    queried_at: datetime
