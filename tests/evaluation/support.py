from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from tradesentry_api.config import Settings
from tradesentry_api.investigation_orchestrator import InvestigationOrchestrator
from tradesentry_api.services import Services

from agents.planner import DeterministicTriagePlanner
from cross_ibu import signal_from_dna
from dna import build_transaction_dna
from models.compliance import ComplianceCaseFacts, LCRequirements, PresentedDocument
from models.contracts import (
    BillOfLadingFields,
    CommercialInvoiceFields,
    DocumentStatus,
    DocumentType,
    ExtractionResult,
    FieldConfidence,
    InsuranceCertificateFields,
    PackingLineItem,
    PackingListFields,
    RequiredDocumentSpec,
)
from models.dna import TransactionDNA
from models.investigation import InvestigationResponse
from scripts.seed_demo import CASES, seed_case

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2024, 9, 8, 12, tzinfo=UTC)
ALL_TYPES = [item for item in DocumentType if item is not DocumentType.UNKNOWN]
_DEMO_CACHE: tuple[Services, dict[str, InvestigationResponse]] | None = None


def evaluation_contract(case_id: str) -> dict[str, Any]:
    payload = json.loads(
        (ROOT / "fixtures" / "regression" / "cases_a_n.json").read_text(encoding="utf-8")
    )
    return next(item for item in payload["cases"] if item["id"] == case_id)


def base_facts(case_id: str = "EVAL") -> ComplianceCaseFacts:
    lc = LCRequirements(
        lc_number="LC-1",
        applicant="Importer Ltd",
        beneficiary="Exporter Ltd",
        credit_amount=Decimal(250000),
        currency="USD",
        expiry_date=date(2024, 10, 1),
        latest_shipment_date=date(2024, 8, 20),
        partial_shipments_allowed=False,
        goods_description="Rice",
        quantity=Decimal(500),
        unit="MT",
        loading_port="Mundra",
        discharge_port="Singapore",
        required_documents=[RequiredDocumentSpec(document_type=item) for item in ALL_TYPES],
    )
    presented = [
        PresentedDocument(
            document_id=f"doc-{item.value}",
            document_type=item,
            status=DocumentStatus.EXTRACTED,
            page_refs={"vessel_name": [1], "goods_description": [1], "quantity": [1]},
        )
        for item in ALL_TYPES
    ]
    return ComplianceCaseFacts(
        case_id=case_id,
        lc=lc,
        presented_documents=presented,
        invoice=CommercialInvoiceFields(
            seller="Exporter Ltd",
            buyer="Importer Ltd",
            currency="USD",
            invoice_amount=Decimal(250000),
            quantity=Decimal(500),
            unit="MT",
            goods_description="Rice",
            vessel_name="Ocean Star",
        ),
        invoice_document_id="doc-commercial_invoice",
        bill_of_lading=BillOfLadingFields(
            bl_number="BL-EVAL",
            shipper="Exporter Ltd",
            consignee="Importer Ltd",
            vessel_name="Ocean Star",
            loading_port="Mundra",
            discharge_port="Singapore",
            on_board_notation=True,
            on_board_date=date(2024, 8, 14),
            goods_description="Rice",
            quantity=Decimal(500),
            unit="MT",
            carrier_or_master_signature=True,
            partial_shipment_indicated=False,
        ),
        bill_of_lading_document_id="doc-bill_of_lading",
        packing_list=PackingListFields(
            line_items=[PackingLineItem(description="Rice", quantity=Decimal(500), unit="MT")],
            total_quantity=Decimal(500),
        ),
        packing_list_document_id="doc-packing_list",
        insurance=InsuranceCertificateFields(
            insured_amount=Decimal(275000),
            currency="USD",
            effective_date=date(2024, 8, 13),
            goods_description="Rice",
            vessel_name="Ocean Star",
            loading_port="Mundra",
            discharge_port="Singapore",
        ),
        insurance_document_id="doc-insurance_certificate",
        drawing_amount=Decimal(250000),
        presentation_date=date(2024, 8, 20),
        is_bulk_or_generic=True,
        evaluated_at=NOW,
    )


def extraction(
    document_id: str,
    document_type: DocumentType,
    fields: object,
    *,
    flags: list[str] | None = None,
    confidence: dict[str, FieldConfidence] | None = None,
) -> ExtractionResult:
    return ExtractionResult(
        document_id=document_id,
        document_type=document_type,
        fields=fields,
        confidence=confidence or {},
        overall_confidence=0.39 if flags else 0.98,
        page_refs={name: item.pages for name, item in (confidence or {}).items()},
        extraction_flags=flags or [],
        processing_status="PARTIAL" if flags else "EXTRACTED",
        processed_at=NOW,
    )


def dna(
    case_id: str,
    ibu_id: str = "IBU-A",
    *,
    bl: str | None = "BL789456",
    vessel: str = "ocean_star",
    voyage: str = "V123",
    exporter: str = "abc_trading",
    loading: str = "INMUN",
    discharge: str = "SGSIN",
    shipped: str = "2024-08-14",
) -> TransactionDNA:
    values = (bl, vessel, voyage, loading, discharge, shipped, exporter)
    fingerprint = hashlib.sha256("".join(value or "" for value in values).encode()).hexdigest()
    return TransactionDNA(
        transaction_id=f"txn-{case_id.lower()}",
        case_id=case_id,
        presenting_ibu=ibu_id,
        bl_number_normalized=bl,
        vessel_normalized=vessel,
        voyage_normalized=voyage,
        exporter_normalized=exporter,
        loading_port_unlocode=loading,
        discharge_port_unlocode=discharge,
        shipment_date_iso=shipped,
        commodity_normalized="rice",
        quantity_canonical=Decimal(500),
        unit_canonical="MT",
        dna_fingerprint=fingerprint,
        source_documents={},
        normalization_methods={},
        confidence_flags=[],
        conflicts=[],
        created_at=NOW,
    )


async def demo_results() -> tuple[Services, dict[str, InvestigationResponse]]:
    global _DEMO_CACHE
    if _DEMO_CACHE is None:
        services = Services.build(Settings())
        for label in CASES:
            await seed_case(services, label)
        documents = await services.repository.list_documents("DEMO-CASE-A")
        case_a_dna = build_transaction_dna(
            "DEMO-CASE-A",
            "IBU-A",
            [item.extraction for item in documents if item.extraction is not None],
            datetime.now(UTC),
        )
        await services.cross_ibu_registry.register(signal_from_dna(case_a_dna), datetime.now(UTC))
        results: dict[str, InvestigationResponse] = {}
        for label, (case_id, ibu_id, _folder) in CASES.items():
            results[label] = await InvestigationOrchestrator(
                services, DeterministicTriagePlanner()
            ).run(case_id, ibu_id)
        _DEMO_CACHE = services, results
    return _DEMO_CACHE
