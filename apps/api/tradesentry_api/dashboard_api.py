from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated, Any, cast
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query, Request

from models.review import (
    CaseReport,
    DashboardCase,
    OfficerDecision,
    ReportDocument,
    ReviewDecision,
    ReviewRequest,
    SettlementReadiness,
)

from .audit_store import AuditEventType, event_from_request
from .auth import Principal, request_principal, require_officer, require_viewer
from .documents import CaseRecord
from .services import Services

router = APIRouter(prefix="/cases", tags=["human-review"])


def _services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


def _principal(request: Request) -> Principal:
    principal = request_principal(request)
    require_viewer(principal)
    return principal


async def _case_for_principal(
    services: Services, case_id: str, principal: Principal
) -> CaseRecord:
    case = await services.repository.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.ibu_id != principal.ibu_id:
        raise HTTPException(status_code=403, detail="IBU tenant access denied")
    return case


async def _readiness(services: Services, case_id: str) -> SettlementReadiness:
    decisions = await services.review_store.list_for_case(case_id)
    latest = decisions[-1] if decisions else None
    if latest is not None and latest.decision is ReviewDecision.APPROVE:
        return SettlementReadiness(
            case_id=case_id,
            status="READY FOR BANK SETTLEMENT WORKFLOW",
            approved=True,
            reason="An authenticated officer approved this case after reviewing the evidence.",
            latest_decision=latest.decision,
        )
    reason = "Bank settlement workflow cannot proceed until an officer approval is recorded."
    if latest is not None:
        reason = {
            ReviewDecision.HOLD: "The latest officer decision placed this case on hold.",
            ReviewDecision.ESCALATE: "The case is escalated to senior compliance review.",
            ReviewDecision.REQUEST_MORE_EVIDENCE: "Additional evidence is required before approval.",
            ReviewDecision.APPROVE: reason,
        }[latest.decision]
    return SettlementReadiness(
        case_id=case_id,
        status="HOLD",
        approved=False,
        reason=reason,
        latest_decision=None if latest is None else latest.decision,
    )


async def _dashboard_case(services: Services, case: CaseRecord) -> DashboardCase:
    investigation = await services.investigation_store.get(case.id)
    state = None if investigation is None else investigation.state
    dna = None if state is None else state.transaction_dna
    readiness = await _readiness(services, case.id)
    display_status = (
        "HOLD — AWAITING OFFICER"
        if readiness.latest_decision is None
        else readiness.status if readiness.approved else case.status
    )
    return DashboardCase(
        case_id=case.id,
        ibu_id=case.ibu_id,
        status=display_status,
        risk_band=None if state is None else state.risk_band,
        risk_score=None if state is None else state.risk_score,
        applicant=None if dna is None else dna.importer_normalized or dna.raw_importer,
        beneficiary=None if dna is None else dna.exporter_normalized or dna.raw_exporter,
        amount=None if dna is None or dna.raw_invoice_value is None else str(dna.raw_invoice_value),
        currency=None if dna is None else dna.raw_currency,
        created_at=case.created_at,
        settlement_readiness=readiness,
    )


async def _report(request: Request, services: Services, case: CaseRecord) -> CaseReport:
    investigation = await services.investigation_store.get(case.id)
    decisions = await services.review_store.list_for_case(case.id)
    documents = await services.repository.list_documents(case.id)
    report_documents: list[ReportDocument] = []
    for document in documents:
        view_url = await services.storage.presigned_url(document.s3_key, 900)
        download_url = await services.storage.presigned_url(document.s3_key, 900)
        await services.audit_store.record(
            event_from_request(
                request,
                event_type=AuditEventType.PRESIGNED_URL_GENERATED,
                case_id=case.id,
                payload_ref=f"s3://key/{document.s3_key}",
            )
        )
        report_documents.append(ReportDocument(
            document_id=document.id,
            filename=document.filename,
            document_type=document.document_type.value,
            status=document.status.value,
            confidence=document.overall_confidence,
            extraction=(
                None if document.extraction is None
                else document.extraction.model_dump(mode="json")
            ),
            view_url=view_url,
            download_url=download_url,
        ))
    state = None if investigation is None else investigation.state
    fraud_checks: dict[str, Any] = {}
    if state is not None:
        fraud_checks = {
            "price_benchmark": None if state.price_benchmark is None else state.price_benchmark.model_dump(mode="json"),
            "vessel_verification": None if state.vessel_verification is None else state.vessel_verification.model_dump(mode="json"),
            "entity_verifications": [item.model_dump(mode="json") for item in state.entity_verifications],
            "sanctions": None if state.sanctions_result is None else state.sanctions_result.model_dump(mode="json"),
        }
    sections: dict[str, Any] = {
        "case_summary": {
            "case_id": case.id, "ibu_id": case.ibu_id, "created_at": case.created_at,
            "status": case.status,
        },
        "documents": [item.model_dump(mode="json") for item in report_documents],
        "compliance_findings": (
            None if state is None or state.compliance_result is None
            else state.compliance_result.model_dump(mode="json")
        ),
        "transaction_dna": (
            None if state is None or state.transaction_dna is None
            else state.transaction_dna.model_dump(mode="json")
        ),
        "cross_ibu_matches": (
            [] if state is None else [item.model_dump(mode="json") for item in state.cross_ibu_matches]
        ),
        "fraud_tbml_checks": fraud_checks,
        "risk_assessment": {
            "score": None if state is None else state.risk_score,
            "band": None if state is None or state.risk_band is None else state.risk_band.value,
            "weights_note": None if state is None else state.risk_weights_note,
            "recommended_action": None if state is None else state.recommended_action,
            "evidence": [] if state is None else [item.model_dump(mode="json") for item in state.evidence],
        },
        "investigation_timeline": (
            [] if state is None else [item.model_dump(mode="json") for item in state.timeline]
        ),
        "officer_decision": [item.model_dump(mode="json") for item in decisions],
    }
    return CaseReport(
        case=await _dashboard_case(services, case),
        sections=sections,
        documents=report_documents,
        decisions=decisions,
    )


@router.get("", response_model=list[DashboardCase])
async def list_cases(
    request: Request,
    ibu_id: str | None = Query(default=None),
    risk_band: str | None = Query(default=None),
    status: str | None = Query(default=None),
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
) -> list[DashboardCase]:
    services = _services(request)
    principal = _principal(request)
    if ibu_id is not None and ibu_id != principal.ibu_id:
        raise HTTPException(status_code=403, detail="IBU tenant access denied")
    result: list[DashboardCase] = []
    for case in await services.repository.list_cases():
        if case.ibu_id != principal.ibu_id:
            continue
        item = await _dashboard_case(services, case)
        if risk_band is not None and (item.risk_band is None or item.risk_band.value != risk_band.upper()):
            continue
        if status is not None and status.upper() not in item.status.upper():
            continue
        if created_from is not None and item.created_at < created_from:
            continue
        if created_to is not None and item.created_at > created_to:
            continue
        result.append(item)
    return result


@router.get("/{case_id}", response_model=CaseReport)
async def get_case(
    case_id: str,
    request: Request,
) -> CaseReport:
    services = _services(request)
    principal = _principal(request)
    case = await _case_for_principal(services, case_id, principal)
    return await _report(request, services, case)


@router.get("/{case_id}/report", response_model=CaseReport)
async def get_report(
    case_id: str,
    request: Request,
) -> CaseReport:
    return await get_case(case_id, request)


@router.get("/{case_id}/settlement-readiness", response_model=SettlementReadiness)
async def get_settlement_readiness(
    case_id: str,
    request: Request,
) -> SettlementReadiness:
    services = _services(request)
    principal = _principal(request)
    await _case_for_principal(services, case_id, principal)
    return await _readiness(services, case_id)


@router.post("/{case_id}/review", response_model=OfficerDecision, status_code=201)
async def submit_review(
    case_id: str,
    payload: ReviewRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16)],
) -> OfficerDecision:
    services = _services(request)
    principal = _principal(request)
    require_officer(principal)
    await _case_for_principal(services, case_id, principal)
    key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
    existing = await services.review_store.get_by_idempotency(case_id, key_hash)
    if existing is not None:
        if existing.decision == payload.decision and existing.comment == payload.comment:
            return existing
        raise HTTPException(status_code=409, detail="Idempotency key was already used")
    decision = OfficerDecision(
        decision_id=f"decision-{uuid4().hex}",
        case_id=case_id,
        decision=payload.decision,
        comment=payload.comment,
        officer_id=principal.subject,
        officer_role=principal.role,
        idempotency_key_hash=key_hash,
        created_at=datetime.now(UTC),
    )
    await services.review_store.save(decision)
    status = {
        ReviewDecision.APPROVE: "READY FOR BANK SETTLEMENT WORKFLOW",
        ReviewDecision.HOLD: "HOLD — OFFICER DECISION",
        ReviewDecision.ESCALATE: "ESCALATED — SENIOR COMPLIANCE",
        ReviewDecision.REQUEST_MORE_EVIDENCE: "PENDING — MORE EVIDENCE",
    }[decision.decision]
    await services.repository.update_case_status(case_id, status)
    comment_hash = hashlib.sha256(payload.comment.encode()).hexdigest()
    await services.audit_store.record(
        event_from_request(
            request,
            event_type=AuditEventType.OFFICER_DECISION,
            case_id=case_id,
            payload_ref=(
                f"decision://{decision.decision_id}/{decision.decision.value}/"
                f"comment-sha256-{comment_hash}"
            ),
        )
    )
    await services.audit_store.record(
        event_from_request(
            request,
            event_type=AuditEventType.SETTLEMENT_STATUS_CHANGED,
            case_id=case_id,
            payload_ref=f"case-status://{case_id}/{decision.decision.value}",
        )
    )
    return decision
