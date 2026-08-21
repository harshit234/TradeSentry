from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from tradesentry_api.audit_store import AuditEvent, AuditEventType
from tradesentry_api.documents import CaseRecord, DocumentRecord
from tradesentry_api.logging import JsonFormatter
from tradesentry_api.main import create_app
from tradesentry_api.malware import ScanStatus
from tradesentry_api.services import Services

from models.contracts import DocumentStatus, DocumentType
from tests.security_support import access_token, auth_headers, secure_settings

SAMPLES = Path(__file__).parents[1] / "fixtures" / "documents"


def _client(**settings_overrides: object) -> tuple[TestClient, Services]:
    settings = secure_settings(**settings_overrides)
    services = Services.build(settings)
    return TestClient(create_app(settings, services)), services


def _add_case(services: Services, case_id: str, ibu_id: str = "IBU-A") -> None:
    asyncio.run(services.repository.create_case(CaseRecord(id=case_id, ibu_id=ibu_id)))


def test_protected_route_rejects_missing_token_and_audits_failure() -> None:
    client, services = _client()
    with client:
        assert client.get("/cases").status_code == 401
    assert asyncio.run(services.audit_store.count("AUTH_FAILURE")) == 1


def test_expired_access_token_is_rejected() -> None:
    client, _ = _client()
    token = access_token(expires_delta=timedelta(minutes=-1))
    with client:
        response = client.get("/cases", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_refresh_token_cannot_access_api() -> None:
    client, _ = _client()
    token = access_token(token_type="refresh")
    with client:
        response = client.get("/cases", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_cross_tenant_case_is_denied() -> None:
    client, services = _client()
    _add_case(services, "SEC-CROSS", "IBU-B")
    with client:
        response = client.get("/cases/SEC-CROSS", headers=auth_headers("ADMIN", "IBU-A"))
    assert response.status_code == 403


def test_auditor_cannot_create_case() -> None:
    client, _ = _client()
    with client:
        response = client.post(
            "/cases",
            headers=auth_headers("AUDITOR"),
            json={"case_id": "SEC-AUDITOR", "ibu_id": "IBU-A"},
        )
    assert response.status_code == 403


def test_executable_disguised_as_pdf_is_rejected() -> None:
    client, services = _client()
    _add_case(services, "SEC-EXE")
    with client:
        response = client.post(
            "/cases/SEC-EXE/documents",
            headers=auth_headers(),
            files={"file": ("malware.pdf", b"MZ\x90\x00executable", "application/pdf")},
        )
    assert response.status_code == 415


def test_upload_over_configured_limit_is_rejected() -> None:
    client, services = _client(max_upload_bytes=10)
    _add_case(services, "SEC-LARGE")
    with client:
        response = client.post(
            "/cases/SEC-LARGE/documents",
            headers=auth_headers(),
            files={"file": ("large.pdf", b"%PDF-1.7" + b"x" * 20, "application/pdf")},
        )
    assert response.status_code == 413


def test_malformed_pdf_structure_is_rejected() -> None:
    client, services = _client()
    _add_case(services, "SEC-PDF")
    with client:
        response = client.post(
            "/cases/SEC-PDF/documents",
            headers=auth_headers(),
            files={"file": ("broken.pdf", b"%PDF-1.7\nnot-a-pdf", "application/pdf")},
        )
    assert response.status_code == 415


def test_malware_scanner_detects_eicar_signature() -> None:
    _, services = _client()
    result = asyncio.run(
        services.malware_scanner.scan(b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE")
    )
    assert result.status is ScanStatus.MALICIOUS


def test_ip_rate_limit_returns_429() -> None:
    client, _ = _client(rate_limit_ip_per_minute=2)
    with client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 429


def test_all_eighteen_audit_event_types_are_recorded() -> None:
    _, services = _client()
    for event_type in AuditEventType:
        asyncio.run(
            services.audit_store.record(
                AuditEvent(
                    case_id="SEC-AUDIT",
                    ibu_id="IBU-A",
                    actor_id="security-test",
                    event_type=event_type,
                    payload_ref=f"test://{event_type.value.lower()}",
                )
            )
        )
    events = asyncio.run(services.audit_store.list_events())
    assert len(AuditEventType) == 18
    assert {event.event_type for event in events} == set(AuditEventType)


def test_structured_log_redacts_tokens_secrets_and_signed_urls() -> None:
    record = logging.LogRecord(
        "security",
        logging.INFO,
        __file__,
        1,
        "Bearer abc.def.ghi secret=visible https://s3/x?X-Amz-Signature=visible",
        (),
        None,
    )
    output = JsonFormatter().format(record)
    payload = json.loads(output)
    assert "visible" not in payload["message"]
    assert "abc.def.ghi" not in payload["message"]
    assert payload["correlation_id"]


def test_presigned_url_audit_contains_only_opaque_object_reference() -> None:
    client, services = _client()
    _add_case(services, "SEC-URL")
    key = "cases/SEC-URL/documents/doc-1/evidence.pdf"
    asyncio.run(
        services.repository.save_document(
            DocumentRecord(
                id="doc-1",
                case_id="SEC-URL",
                filename="evidence.pdf",
                content_hash="sha256",
                mime_type="application/pdf",
                s3_key=key,
                status=DocumentStatus.EXTRACTED,
                document_type=DocumentType.COMMERCIAL_INVOICE,
            )
        )
    )
    with client:
        assert client.get("/cases/SEC-URL/report", headers=auth_headers()).status_code == 200
    events = asyncio.run(services.audit_store.list_events())
    generated = [event for event in events if event.event_type is AuditEventType.PRESIGNED_URL_GENERATED]
    assert generated[0].payload_ref == f"s3://key/{key}"
    assert "http" not in generated[0].payload_ref


def test_review_idempotency_blocks_conflict_and_stores_sql_text_as_data() -> None:
    client, services = _client()
    _add_case(services, "SEC-IDEMPOTENT")
    headers = {**auth_headers("OFFICER"), "Idempotency-Key": "security-review-key-0001"}
    payload = {"decision": "HOLD", "comment": "'; DROP TABLE cases; -- evidence reviewed"}
    with client:
        first = client.post("/cases/SEC-IDEMPOTENT/review", headers=headers, json=payload)
        replay = client.post("/cases/SEC-IDEMPOTENT/review", headers=headers, json=payload)
        conflict = client.post(
            "/cases/SEC-IDEMPOTENT/review",
            headers=headers,
            json={"decision": "APPROVE", "comment": "different payload"},
        )
    assert first.status_code == 201
    assert replay.json()["decision_id"] == first.json()["decision_id"]
    assert replay.json()["comment"] == payload["comment"]
    assert conflict.status_code == 409
