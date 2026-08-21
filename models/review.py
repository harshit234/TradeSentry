from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .investigation import RiskBand


class ReviewDecision(StrEnum):
    APPROVE = "APPROVE"
    HOLD = "HOLD"
    ESCALATE = "ESCALATE"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    comment: str = Field(min_length=10, max_length=4000)

    @field_validator("comment")
    @classmethod
    def meaningful_comment(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("Comment must contain at least 10 non-whitespace characters")
        return cleaned


class OfficerDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str
    case_id: str
    decision: ReviewDecision
    comment: str
    officer_id: str
    officer_role: str
    idempotency_key_hash: str = Field(exclude=True)
    created_at: datetime


class SettlementReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    status: str
    approved: bool
    reason: str
    latest_decision: ReviewDecision | None = None
    fcss_note: str = (
        "FCSS is a downstream bank process where applicable; TradeSentry does not control it."
    )


class DashboardCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    ibu_id: str
    status: str
    risk_band: RiskBand | None = None
    risk_score: int | None = None
    applicant: str | None = None
    beneficiary: str | None = None
    amount: str | None = None
    currency: str | None = None
    created_at: datetime
    settlement_readiness: SettlementReadiness


class ReportDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    filename: str
    document_type: str
    status: str
    confidence: float | None
    extraction: dict[str, Any] | None
    view_url: str
    download_url: str


class CaseReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case: DashboardCase
    sections: dict[str, Any]
    documents: list[ReportDocument]
    decisions: list[OfficerDecision]
