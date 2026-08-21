from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PriceSignal(StrEnum):
    NORMAL = "NORMAL"
    REVIEW = "REVIEW"
    SIGNIFICANT_ANOMALY = "SIGNIFICANT_ANOMALY"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class VesselVerificationStatus(StrEnum):
    CONSISTENT = "CONSISTENT"
    ANOMALY = "ANOMALY"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class EntityVerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    SUSPICIOUS = "SUSPICIOUS"


class SanctionsMatchStatus(StrEnum):
    NO_MATCH = "NO_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    CONFIRMED_SOURCE_MATCH = "CONFIRMED_SOURCE_MATCH"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class ProvenanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    data_source: str
    source_version: str
    retrieved_at: datetime
    caveats: list[str]


class PriceBenchmarkResult(ProvenanceModel):
    hs_code: str
    trade_corridor: str
    period: str
    reference_min: float | None = None
    reference_p25: float | None = None
    reference_p50: float | None = None
    reference_p75: float | None = None
    reference_p90: float | None = None
    invoice_unit_value: float
    currency: str
    deviation_from_p50_pct: float | None = None
    signal: PriceSignal
    methodology_note: str
    confidence: float = Field(ge=0.0, le=1.0)


class VesselVerificationResult(ProvenanceModel):
    vessel_name: str
    imo_number: str | None
    voyage_number: str
    stated_port: str
    stated_date: date
    verification_result: VesselVerificationStatus
    details: str
    confidence: float = Field(ge=0.0, le=1.0)


class EntityVerificationResult(ProvenanceModel):
    raw_name: str
    normalized_name: str
    country: str
    entity_type: str
    verification_status: EntityVerificationStatus
    known_relationships: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class EntityScreenResult(ProvenanceModel):
    input_name: str
    normalized_name: str
    match_status: SanctionsMatchStatus
    matched_list: str | None
    match_score: float = Field(ge=0.0, le=1.0)
    match_rationale: str
    list_date: date


class SanctionsScreeningResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    screened_entities: list[EntityScreenResult]
    human_determination_required: bool = True

