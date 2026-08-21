from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from tradesentry_api.config import Settings
from tradesentry_api.documents import CaseRecord, DocumentRecord
from tradesentry_api.main import create_app
from tradesentry_api.services import Services

from models.contracts import DocumentStatus, DocumentType
from models.investigation import InvestigationResponse, InvestigationState, RiskBand

SECRET = "sprint-7-test-secret-at-least-32-bytes"


@pytest.fixture
def dashboard() -> Iterator[tuple[TestClient, Services]]:
    settings = Settings(jwt_secret=SECRET)
    services = Services.build(settings)
    with TestClient(create_app(settings, services)) as client:
        yield client, services


def token(role: str = "OFFICER", ibu_id: str = "IBU-A") -> str:
    encoded = jwt.encode(
        {
            "sub": "officer-001",
            "role": role,
            "ibu_id": ibu_id,
            "iss": "tradesentry",
            "aud": "tradesentry-dashboard",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        SECRET,
        algorithm="HS256",
    )
    return f"Bearer {encoded}"


def add_case(services: Services, case_id: str, ibu_id: str = "IBU-A") -> None:
    asyncio.run(services.repository.create_case(CaseRecord(id=case_id, ibu_id=ibu_id)))


def add_investigation(services: Services, case_id: str, band: RiskBand) -> None:
    response = InvestigationResponse(
        state=InvestigationState(
            case_id=case_id,
            ibu_id="IBU-A",
            risk_band=band,
            risk_score=88 if band is RiskBand.HIGH else 12,
            investigation_complete=True,
            requires_human_review=True,
        ),
        workflow_status="INTERRUPTED" if band is RiskBand.HIGH else "COMPLETED",
    )
    asyncio.run(services.investigation_store.save(response))


def auth_header(role: str = "OFFICER", ibu_id: str = "IBU-A") -> dict[str, str]:
    return {"Authorization": token(role, ibu_id)}


def test_unauthenticated_dashboard_request_returns_401(
    dashboard: tuple[TestClient, Services],
) -> None:
    client, _services = dashboard
    assert client.get("/cases").status_code == 401


def test_cross_ibu_case_request_returns_403(dashboard: tuple[TestClient, Services]) -> None:
    client, services = dashboard
    add_case(services, "CASE-CROSS", "IBU-B")
    assert client.get("/cases/CASE-CROSS", headers=auth_header()).status_code == 403


def test_empty_review_comment_returns_422(dashboard: tuple[TestClient, Services]) -> None:
    client, services = dashboard
    add_case(services, "CASE-EMPTY")
    response = client.post(
        "/cases/CASE-EMPTY/review",
        headers=auth_header(),
        json={"decision": "APPROVE", "comment": "   "},
    )
    assert response.status_code == 422


def test_officer_approval_makes_case_settlement_ready(
    dashboard: tuple[TestClient, Services],
) -> None:
    client, services = dashboard
    add_case(services, "CASE-APPROVE")
    reviewed = client.post(
        "/cases/CASE-APPROVE/review",
        headers=auth_header(),
        json={"decision": "APPROVE", "comment": "Evidence reviewed and acceptable."},
    )
    readiness = client.get(
        "/cases/CASE-APPROVE/settlement-readiness", headers=auth_header()
    )
    assert reviewed.status_code == 201
    assert readiness.json()["status"] == "READY FOR BANK SETTLEMENT WORKFLOW"
    assert readiness.json()["approved"] is True


def test_officer_hold_records_status_and_reason(
    dashboard: tuple[TestClient, Services],
) -> None:
    client, services = dashboard
    add_case(services, "CASE-HOLD")
    response = client.post(
        "/cases/CASE-HOLD/review",
        headers=auth_header(),
        json={"decision": "HOLD", "comment": "Invoice evidence needs clarification."},
    )
    readiness = client.get("/cases/CASE-HOLD/settlement-readiness", headers=auth_header())
    assert response.status_code == 201
    assert (asyncio.run(services.repository.get_case("CASE-HOLD"))).status == "HOLD — OFFICER DECISION"  # type: ignore[union-attr]
    assert "hold" in readiness.json()["reason"].lower()


def test_agent_identity_cannot_submit_review(dashboard: tuple[TestClient, Services]) -> None:
    client, services = dashboard
    add_case(services, "CASE-AGENT")
    response = client.post(
        "/cases/CASE-AGENT/review",
        headers=auth_header("AGENT"),
        json={"decision": "APPROVE", "comment": "Agent must not make this decision."},
    )
    assert response.status_code == 403


def test_high_risk_report_renders_all_nine_evidence_sections(
    dashboard: tuple[TestClient, Services],
) -> None:
    client, services = dashboard
    add_case(services, "CASE-HIGH")
    add_investigation(services, "CASE-HIGH", RiskBand.HIGH)
    report = client.get("/cases/CASE-HIGH/report", headers=auth_header()).json()
    assert report["case"]["risk_band"] == "HIGH"
    assert len(report["sections"]) == 9


def test_low_risk_report_renders_all_nine_evidence_sections(
    dashboard: tuple[TestClient, Services],
) -> None:
    client, services = dashboard
    add_case(services, "CASE-LOW")
    add_investigation(services, "CASE-LOW", RiskBand.LOW)
    report = client.get("/cases/CASE-LOW/report", headers=auth_header()).json()
    assert report["case"]["risk_band"] == "LOW"
    assert len(report["sections"]) == 9


def test_report_pdf_link_targets_correct_object_for_nine_hundred_seconds(
    dashboard: tuple[TestClient, Services],
) -> None:
    client, services = dashboard
    add_case(services, "CASE-PDF")
    key = "cases/CASE-PDF/documents/doc-pdf/evidence.pdf"
    asyncio.run(services.storage.upload(b"%PDF-1.4", key, {}))
    asyncio.run(
        services.repository.save_document(
            DocumentRecord(
                id="doc-pdf", case_id="CASE-PDF", filename="evidence.pdf",
                content_hash="abc", mime_type="application/pdf", s3_key=key,
                status=DocumentStatus.EXTRACTED, document_type=DocumentType.COMMERCIAL_INVOICE,
            )
        )
    )
    document = client.get("/cases/CASE-PDF/report", headers=auth_header()).json()["documents"][0]
    assert key in document["view_url"]
    assert document["view_url"].endswith("expires=900")


def test_each_officer_decision_creates_an_audit_event(
    dashboard: tuple[TestClient, Services],
) -> None:
    client, services = dashboard
    add_case(services, "CASE-AUDIT")
    before = asyncio.run(services.audit_store.count("OFFICER_REVIEW_DECISION"))
    for decision in ("HOLD", "REQUEST_MORE_EVIDENCE"):
        response = client.post(
            "/cases/CASE-AUDIT/review",
            headers=auth_header(),
            json={"decision": decision, "comment": "Recorded evidence-based officer rationale."},
        )
        assert response.status_code == 201
    after = asyncio.run(services.audit_store.count("OFFICER_REVIEW_DECISION"))
    assert after - before == 2
