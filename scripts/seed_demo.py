from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any

from sqlalchemy import text
from tradesentry_api.config import Settings
from tradesentry_api.db import Database
from tradesentry_api.documents import (
    CaseRecord,
    DocumentRecord,
    detect_mime,
    deterministic_document_id,
)
from tradesentry_api.investigation_orchestrator import InvestigationOrchestrator
from tradesentry_api.processor import SCHEMA_BY_TYPE
from tradesentry_api.services import Services

from agents.planner import DeterministicTriagePlanner
from models.contracts import DocumentStatus, DocumentType, ExtractionResult, FieldConfidence
from scripts.seed_registry import seed_cross_ibu_registry

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "A": ("DEMO-CASE-A", "IBU-A", "case_a_clean"),
    "B": ("DEMO-CASE-B", "IBU-A", "case_b_duplicate"),
    "C": ("DEMO-CASE-C", "IBU-B", "case_c_tbml"),
    "D": ("DEMO-CASE-D", "IBU-A", "case_d_legit"),
}


def load_fixture(case_id: str) -> dict[str, Any]:
    path = ROOT / "fixtures" / "pre_extracted" / f"{case_id}.json"
    fixture = dict(json.loads(path.read_text(encoding="utf-8")))
    if case_id == "DEMO-CASE-A":
        by_type = {item["document_type"]: item for item in fixture["documents"]}
        bill = by_type["bill_of_lading"]
        bill["fields"]["bl_number"]["value"] = "BL-CLEAN-2024-042"
        bill["fields"]["vessel_name"]["value"] = "CLEAN HORIZON"
        bill["fields"]["voyage_number"]["value"] = "V042"
        bill["fields"]["shipper"]["value"] = "Clean Exporters Ltd"
        bill["fields"]["on_board_date"]["value"] = "2024-07-15"
        bill["fields"]["loading_port"]["value"] = "Nhava Sheva, India"
        bill["fields"]["discharge_port"]["value"] = "Dubai, UAE"
        by_type["commercial_invoice"]["fields"]["seller"]["value"] = (
            "Clean Exporters Ltd"
        )
        by_type["letter_of_credit"]["fields"]["beneficiary"]["value"] = (
            "Clean Exporters Ltd"
        )
    if case_id == "DEMO-CASE-C":
        lc = next(
            item for item in fixture["documents"] if item["document_type"] == "letter_of_credit"
        )
        lc["fields"]["credit_amount"]["value"] = 405000.00
    return fixture


def extraction_from_fixture(document_id: str, fixture: dict[str, Any]) -> ExtractionResult:
    document_type = DocumentType(fixture["document_type"])
    raw_fields: dict[str, dict[str, Any]] = fixture["fields"]
    values = {name: evidence["value"] for name, evidence in raw_fields.items()}
    confidence = {
        name: FieldConfidence(
            confidence=float(evidence["confidence"]), pages=[int(evidence["page"])]
        )
        for name, evidence in raw_fields.items()
    }
    page_refs = {name: evidence.pages for name, evidence in confidence.items()}
    schema = SCHEMA_BY_TYPE[document_type]
    return ExtractionResult(
        document_id=document_id,
        document_type=document_type,
        fields=schema.model_validate(values),
        confidence=confidence,
        overall_confidence=float(fixture["overall_confidence"]),
        page_refs=page_refs,
        extraction_flags=list(fixture.get("extraction_flags", [])),
        processing_status="EXTRACTED",
        processed_at=datetime.now(UTC),
    )


async def seed_case(services: Services, label: str) -> None:
    case_id, ibu_id, folder = CASES[label]
    existing = await services.repository.list_documents(case_id)
    for document in existing:
        await services.storage.delete(document.s3_key)
    if isinstance(services.db, Database):
        async with services.db.engine.begin() as connection:
            for statement in (
                "DELETE FROM officer_decisions WHERE case_id=:case_id",
                "DELETE FROM investigation_states WHERE case_id=:case_id",
                "DELETE FROM transaction_dna WHERE case_id=:case_id",
                "DELETE FROM compliance_results WHERE case_id=:case_id",
            ):
                await connection.execute(
                    text(statement),
                    {"case_id": case_id},
                )
            await connection.execute(
                text(
                    "UPDATE cases SET ibu_id=:ibu_id, status='PENDING', updated_at=now() "
                    "WHERE id=:case_id"
                ),
                {"case_id": case_id, "ibu_id": ibu_id},
            )
        if await services.repository.get_case(case_id) is None:
            await services.repository.create_case(CaseRecord(id=case_id, ibu_id=ibu_id))
    else:
        await services.repository.delete_case(case_id)
        await services.repository.create_case(CaseRecord(id=case_id, ibu_id=ibu_id))
    fixture = load_fixture(case_id)
    fixture_by_name = {item["filename"]: item for item in fixture["documents"]}
    source = ROOT / "fixtures" / "sample_documents" / folder
    for path in sorted(source.glob("*.pdf")):
        data = path.read_bytes()
        document_id = deterministic_document_id(case_id, data)
        key = f"cases/{case_id}/documents/{document_id}/{path.name}"
        await services.storage.upload(
            data,
            key,
            {
                "case_id": case_id,
                "uploaded_by": "seed-demo",
                "upload_timestamp": datetime.now(UTC).isoformat(),
            },
        )
        extraction = extraction_from_fixture(document_id, fixture_by_name[path.name])
        await services.repository.save_document(
            DocumentRecord(
                id=document_id,
                case_id=case_id,
                filename=path.name,
                content_hash=hashlib.sha256(data).hexdigest(),
                mime_type=detect_mime(data),
                s3_key=key,
                status=DocumentStatus.EXTRACTED,
                document_type=extraction.document_type,
                overall_confidence=extraction.overall_confidence,
                extraction=extraction,
            )
        )


async def main(case: str | None) -> None:
    started = monotonic()
    services = Services.build(Settings.from_env())
    try:
        await seed_cross_ibu_registry(services)
        labels = [case] if case else list(CASES)
        for label in labels:
            await seed_case(services, label)
        for label in labels:
            case_id, ibu_id, _folder = CASES[label]
            result = await InvestigationOrchestrator(
                services, DeterministicTriagePlanner()
            ).run(case_id, ibu_id)
            await services.repository.update_case_status(
                case_id, result.state.recommended_action or "PENDING REVIEW"
            )
        count = 0
        for label in labels:
            count += len(await services.repository.list_documents(CASES[label][0]))
        print(
            f"Seeded and evaluated {len(labels)} demo cases and {count} documents "
            f"in {monotonic() - started:.2f}s"
        )
    finally:
        await services.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Idempotently reset Sprint 10 demo scenarios")
    parser.add_argument("--case", choices=CASES)
    arguments = parser.parse_args()
    asyncio.run(main(arguments.case))
