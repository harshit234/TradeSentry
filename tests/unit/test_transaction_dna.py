from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from tradesentry_api.config import Settings
from tradesentry_api.main import create_app

from dna import build_transaction_dna
from dna.normalization import (
    normalize_date,
    normalize_entity_name,
    normalize_hs_code,
    normalize_port,
    normalize_quantity,
)
from models.contracts import (
    BillOfLadingFields,
    CommercialInvoiceFields,
    DocumentType,
    ExtractionResult,
    LetterOfCreditFields,
    PackingLineItem,
    PackingListFields,
)
from models.dna import ConflictSeverity

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "fixtures" / "sample_documents" / "case_a_clean"


def _extraction(
    document_id: str,
    document_type: DocumentType,
    fields: (
        LetterOfCreditFields | CommercialInvoiceFields | BillOfLadingFields | PackingListFields
    ),
    flags: list[str] | None = None,
) -> ExtractionResult:
    return ExtractionResult(
        document_id=document_id,
        document_type=document_type,
        fields=fields,
        confidence={},
        overall_confidence=0.9,
        page_refs={},
        extraction_flags=flags or [],
        processing_status="PARTIAL" if flags else "EXTRACTED",
        processed_at=NOW,
    )


def _documents() -> list[ExtractionResult]:
    return [
        _extraction(
            "doc-lc",
            DocumentType.LETTER_OF_CREDIT,
            LetterOfCreditFields(
                lc_number="LC 101", loading_port="JNPT", discharge_port="Singapore"
            ),
        ),
        _extraction(
            "doc-invoice",
            DocumentType.COMMERCIAL_INVOICE,
            CommercialInvoiceFields(
                invoice_number="INV-9",
                seller="A.B.C. Trading Ltd",
                buyer="Buyer Private Limited",
                currency="USD",
                invoice_amount=Decimal(2500),
                quantity=Decimal(1000),
                unit="KG",
                goods_description="Refined Copper Cathodes",
                hs_code="7403 11 00",
                vessel_name="MV Other",
            ),
            ["vessel_name"],
        ),
        _extraction(
            "doc-bl",
            DocumentType.BILL_OF_LADING,
            BillOfLadingFields(
                bl_number=" BL 001 ",
                vessel_name="MV Trade Star",
                imo_number="IMO 9876543",
                voyage_number=" V-22 ",
                shipper="ABC TRADING PRIVATE LTD",
                consignee="Buyer Pvt Ltd",
                loading_port="Nhava Sheva",
                discharge_port="SGSIN",
                on_board_date=date(2026, 8, 20),
                goods_description="Refined Copper Cathodes",
                hs_code="7403.11.00",
                quantity=Decimal(2),
                unit="MT",
            ),
        ),
        _extraction(
            "doc-packing",
            DocumentType.PACKING_LIST,
            PackingListFields(
                total_quantity=Decimal(1000),
                line_items=[PackingLineItem(quantity=Decimal(1000), unit="KG")],
            ),
        ),
    ]


def test_entity_name_ocr_variants_share_canonical_form() -> None:
    assert normalize_entity_name("A.B.C. Trading Ltd") == "abc_trading"
    assert normalize_entity_name("ABC TRADING PRIVATE LTD") == "abc_trading"
    assert normalize_entity_name("XYZ Trading Ltd") != "abc_trading"


def test_port_date_hs_and_quantity_normalization() -> None:
    assert normalize_port("JNPT") == normalize_port("Jawaharlal Nehru Port") == "INNSA"
    assert normalize_date("21/08/2026") == normalize_date("2026-08-21")
    assert normalize_hs_code("7403 11 00") == "7403.11.00"
    assert normalize_quantity(Decimal(1000), "KG") == (Decimal(1), "MT")


def test_builder_preserves_sources_flags_conflicts_and_fingerprint() -> None:
    first = build_transaction_dna("CASE-1", "IBU-A", _documents(), NOW)
    second = build_transaction_dna("CASE-1", "IBU-A", _documents(), NOW)

    assert first.exporter_normalized == "abc_trading"
    assert first.loading_port_unlocode == "INNSA"
    assert first.discharge_port_unlocode == "SGSIN"
    assert first.quantity_canonical == Decimal(1)
    assert first.invoice_value_usd == Decimal(2500)
    assert first.unit_value_usd_per_unit == Decimal(2500)
    assert first.source_documents["raw_exporter"] == "doc-invoice"
    assert first.source_documents["raw_loading_port"] == "doc-lc"
    assert first.confidence_flags == ["vessel_normalized"]
    assert first.dna_fingerprint == second.dna_fingerprint
    assert first.transaction_id == second.transaction_id

    conflicts = {conflict.field_name: conflict for conflict in first.conflicts}
    assert "exporter" not in conflicts
    assert "loading_port" not in conflicts
    assert "discharge_port" not in conflicts
    assert conflicts["vessel_name"].severity is ConflictSeverity.MATERIAL
    assert conflicts["quantity"].severity is ConflictSeverity.MATERIAL


def test_fallback_value_records_actual_source_and_unknown_currency_is_not_converted() -> None:
    invoice = _extraction(
        "doc-invoice",
        DocumentType.COMMERCIAL_INVOICE,
        CommercialInvoiceFields(currency="EUR", invoice_amount=Decimal(100)),
    )
    bl = _extraction(
        "doc-bl",
        DocumentType.BILL_OF_LADING,
        BillOfLadingFields(goods_description="Steel coils", hs_code="7208 10"),
    )
    result = build_transaction_dna("CASE-2", "IBU-A", [invoice, bl], NOW)

    assert result.source_documents["raw_commodity"] == "doc-bl"
    assert result.source_documents["raw_hs_code"] == "doc-bl"
    assert result.invoice_value_usd is None


def test_transaction_dna_post_then_get() -> None:
    with TestClient(create_app(Settings())) as client:
        created = client.post("/cases", json={"case_id": "DNA-CASE", "ibu_id": "IBU-A"})
        assert created.status_code == 201
        for filename in ("lc.pdf", "commercial_invoice.pdf", "bill_of_lading.pdf"):
            path = SAMPLES / filename
            uploaded = client.post(
                "/cases/DNA-CASE/documents",
                files={"file": (filename, path.read_bytes(), "application/pdf")},
            )
            assert uploaded.status_code == 202

        generated = client.post("/cases/DNA-CASE/transaction-dna")
        retrieved = client.get("/cases/DNA-CASE/transaction-dna")

    assert generated.status_code == 200
    assert retrieved.status_code == 200
    assert retrieved.json() == generated.json()
    assert len(generated.json()["dna_fingerprint"]) == 64


def test_transaction_dna_requires_case_and_extracted_documents() -> None:
    with TestClient(create_app(Settings())) as client:
        missing = client.post("/cases/DOES-NOT-EXIST/transaction-dna")
        client.post("/cases", json={"case_id": "EMPTY", "ibu_id": "IBU-A"})
        empty = client.post("/cases/EMPTY/transaction-dna")
        absent = client.get("/cases/EMPTY/transaction-dna")

    assert missing.status_code == 404
    assert empty.status_code == 422
    assert absent.status_code == 404
