from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .compliance import ComplianceResult, LCRequirements
from .contracts import DocumentCompleteness, DocumentStatus, DocumentType, ExtractionResult
from .cross_ibu import CrossIBUMatch
from .dna import TransactionDNA
from .fraud_tbml import (
    EntityVerificationResult,
    PriceBenchmarkResult,
    SanctionsScreeningResult,
    VesselVerificationResult,
)

RISK_WEIGHTS_NOTE = "prototype demo weights — not calibrated for production"
READY_ACTION = "READY FOR BANK SETTLEMENT WORKFLOW"
HOLD_ACTION = "HOLD — REVIEW REQUIRED"


class RiskBand(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceSeverity(StrEnum):
    INFO = "INFO"
    REVIEW = "REVIEW"
    MATERIAL = "MATERIAL"
    HIGH = "HIGH"


class DocumentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    document_type: DocumentType
    status: DocumentStatus
    overall_confidence: float | None = None


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    finding_type: str
    severity: EvidenceSeverity
    summary: str
    structured_detail: dict[str, Any]
    evidence_ref: str


class ToolCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: str
    inputs_hash: str
    duration_ms: float = Field(ge=0)
    status: str
    called_at: datetime


class TimelineRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_name: str
    status: str
    occurred_at: datetime
    detail: str


class ToolSelectionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_price_benchmark: bool
    run_vessel_verification: bool
    run_entity_verification: bool
    run_sanctions: bool
    reasoning: str = Field(min_length=1, max_length=1000)


class TriageContext(BaseModel):
    """Structured-only planner input; raw document text is deliberately absent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cross_ibu_levels: list[str]
    unit_value_usd_per_unit: float | None
    conflict_fields: list[str]
    both_trade_entities_missing: bool
    sanctions_already_run: bool


class InvestigationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    ibu_id: str
    documents: list[DocumentSummary] = []
    extraction_results: dict[str, ExtractionResult] = {}
    completeness: DocumentCompleteness | None = None
    lc_requirements: LCRequirements | None = None
    compliance_result: ComplianceResult | None = None
    transaction_dna: TransactionDNA | None = None
    cross_ibu_matches: list[CrossIBUMatch] = []
    price_benchmark: PriceBenchmarkResult | None = None
    vessel_verification: VesselVerificationResult | None = None
    entity_verifications: list[EntityVerificationResult] = []
    sanctions_result: SanctionsScreeningResult | None = None
    tool_selection_plan: ToolSelectionPlan | None = None
    evidence: list[EvidenceRecord] = []
    risk_score: int | None = Field(default=None, ge=0)
    risk_band: RiskBand | None = None
    risk_weights_note: str = RISK_WEIGHTS_NOTE
    recommended_action: str | None = None
    tool_calls_made: list[ToolCallRecord] = []
    tool_budget_remaining: int = Field(default=12, ge=0)
    errors: list[str] = []
    timeline: list[TimelineRecord] = []
    investigation_complete: bool = False
    requires_human_review: bool = False
    stop_reason: str | None = None


class InvestigationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_budget: int | None = Field(default=None, ge=0, le=12)


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: InvestigationState
    workflow_status: Literal["COMPLETED", "INTERRUPTED"]

