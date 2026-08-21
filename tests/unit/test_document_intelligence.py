from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from tradesentry_api.config import Settings
from tradesentry_api.documents import classify_document, detect_mime
from tradesentry_api.main import create_app
from tradesentry_api.ocr import PageBlock, RawOCRResult
from tradesentry_api.processor import DocumentProcessor
from tradesentry_api.services import Services

from models.contracts import DocumentType
from tests.security_support import auth_headers, secure_settings, with_security

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "fixtures" / "sample_documents" / "case_a_clean"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("lc.pdf", DocumentType.LETTER_OF_CREDIT),
        ("commercial_invoice.pdf", DocumentType.COMMERCIAL_INVOICE),
        ("bill_of_lading.pdf", DocumentType.BILL_OF_LADING),
        ("packing_list.pdf", DocumentType.PACKING_LIST),
        ("certificate_of_origin.pdf", DocumentType.CERTIFICATE_OF_ORIGIN),
        ("insurance_certificate.pdf", DocumentType.INSURANCE_CERTIFICATE),
        ("inspection_certificate.pdf", DocumentType.INSPECTION_CERTIFICATE),
    ],
)
def test_classifies_all_supported_types(filename: str, expected: DocumentType) -> None:
    assert classify_document(filename) is expected


def test_unknown_classification_is_advisory() -> None:
    assert classify_document("other.pdf", "unrecognized form") is DocumentType.UNKNOWN


def test_magic_bytes_reject_executable() -> None:
    with pytest.raises(ValueError):
        detect_mime(b"MZ executable")


def _client(settings: Settings | None = None, services: Services | None = None) -> TestClient:
    secured = secure_settings() if settings is None else with_security(settings)
    return TestClient(create_app(secured, services), headers=auth_headers())


def _create_case(client: TestClient, case_id: str = "TEST-CASE") -> None:
    response = client.post("/cases", json={"case_id": case_id, "ibu_id": "IBU-A"})
    assert response.status_code == 201


def test_upload_is_classified_extracted_and_idempotent() -> None:
    data = (SAMPLES / "commercial_invoice.pdf").read_bytes()
    with _client() as client:
        _create_case(client)
        first = client.post(
            "/cases/TEST-CASE/documents",
            files={"file": ("commercial_invoice.pdf", data, "application/pdf")},
        )
        second = client.post(
            "/cases/TEST-CASE/documents",
            files={"file": ("renamed.pdf", data, "application/pdf")},
        )
        listing = client.get("/cases/TEST-CASE/documents").json()
    assert first.status_code == 202
    assert first.json()["document_id"] == second.json()["document_id"]
    assert len(listing) == 1
    assert listing[0]["document_type"] == "commercial_invoice"
    assert listing[0]["status"] == "EXTRACTED"


def test_wrong_type_returns_415() -> None:
    with _client() as client:
        _create_case(client)
        response = client.post(
            "/cases/TEST-CASE/documents",
            files={"file": ("bad.exe", b"MZbad", "application/octet-stream")},
        )
    assert response.status_code == 415


def test_size_limit_returns_413() -> None:
    settings = Settings(max_upload_bytes=8)
    with _client(settings) as client:
        _create_case(client)
        response = client.post(
            "/cases/TEST-CASE/documents",
            files={"file": ("large.pdf", b"%PDF-123456", "application/pdf")},
        )
    assert response.status_code == 413


def test_malformed_pdf_is_rejected_before_storage() -> None:
    with _client() as client:
        _create_case(client)
        response = client.post(
            "/cases/TEST-CASE/documents",
            files={"file": ("invoice.pdf", b"%PDF-malformed", "application/pdf")},
        )
        listing = client.get("/cases/TEST-CASE/documents").json()
    assert response.status_code == 415
    assert listing == []


class LowConfidenceOCR:
    async def analyze_document(self, *args: Any, **kwargs: Any) -> RawOCRResult:
        del args, kwargs
        return RawOCRResult(
            full_text="redacted from logs",
            page_blocks=[PageBlock(1, "redacted from logs", 0.55)],
            query_results={},
            tables=[],
            overall_confidence=0.55,
            low_confidence_pages=[1],
        )


class TrackingFallback:
    def __init__(self) -> None:
        self.called = False

    async def reextract(
        self, raw_result: RawOCRResult, document_type: DocumentType
    ) -> dict[str, Any]:
        del raw_result, document_type
        self.called = True
        return {"invoice_number": "FALLBACK-1", "invoice_amount": "10.00"}


def test_low_confidence_calls_llm_fallback_and_marks_partial() -> None:
    services = Services.build(Settings())
    fallback = TrackingFallback()
    services.processor = DocumentProcessor(
        services.repository, LowConfidenceOCR(), fallback, services.settings.s3_bucket
    )
    data = (SAMPLES / "commercial_invoice.pdf").read_bytes()
    with _client(services=services) as client:
        _create_case(client)
        client.post(
            "/cases/TEST-CASE/documents", files={"file": ("invoice.pdf", data, "application/pdf")}
        )
        listing = client.get("/cases/TEST-CASE/documents").json()
    assert fallback.called
    assert listing[0]["status"] == "PARTIAL"


class TimeoutOCR:
    async def analyze_document(self, *args: Any, **kwargs: Any) -> RawOCRResult:
        del args, kwargs
        raise TimeoutError


def test_textract_timeout_becomes_data_unavailable() -> None:
    services = Services.build(Settings())
    services.processor = DocumentProcessor(
        services.repository, TimeoutOCR(), TrackingFallback(), services.settings.s3_bucket
    )
    data = (SAMPLES / "lc.pdf").read_bytes()
    with _client(services=services) as client:
        _create_case(client)
        client.post(
            "/cases/TEST-CASE/documents", files={"file": ("lc.pdf", data, "application/pdf")}
        )
        listing = client.get("/cases/TEST-CASE/documents").json()
    assert listing[0]["status"] == "FAILED"
    assert listing[0]["error_code"] == "DATA_UNAVAILABLE"


def test_completeness_missing_then_complete() -> None:
    with _client() as client:
        _create_case(client)
        for path in sorted(SAMPLES.glob("*.pdf")):
            if path.name != "insurance_certificate.pdf":
                client.post(
                    "/cases/TEST-CASE/documents",
                    files={"file": (path.name, path.read_bytes(), "application/pdf")},
                )
        incomplete = client.get("/cases/TEST-CASE/completeness").json()
        path = SAMPLES / "insurance_certificate.pdf"
        client.post(
            "/cases/TEST-CASE/documents",
            files={"file": (path.name, path.read_bytes(), "application/pdf")},
        )
        complete = client.get("/cases/TEST-CASE/completeness").json()
    assert incomplete["status"] == "INCOMPLETE"
    assert "insurance_certificate" in incomplete["missing_types"]
    assert complete["status"] == "COMPLETE"
    assert complete["can_run_investigation"] is True


def test_detail_contains_capped_presigned_url() -> None:
    data = (SAMPLES / "lc.pdf").read_bytes()
    with _client() as client:
        _create_case(client)
        document_id = client.post(
            "/cases/TEST-CASE/documents", files={"file": ("lc.pdf", data, "application/pdf")}
        ).json()["document_id"]
        detail = client.get(f"/cases/TEST-CASE/documents/{document_id}").json()
    assert detail["view_url"].endswith("expires=900")
