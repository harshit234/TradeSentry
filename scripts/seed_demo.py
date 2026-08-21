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
from tradesentry_api.processor import SCHEMA_BY_TYPE
from tradesentry_api.services import Services

from models.contracts import DocumentStatus, DocumentType, ExtractionResult, FieldConfidence

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "A": ("DEMO-CASE-A", "IBU-A", "case_a_clean"),
    "B": ("DEMO-CASE-B", "IBU-B", "case_b_duplicate"),
    "C": ("DEMO-CASE-C", "IBU-A", "case_c_tbml"),
    "D": ("DEMO-CASE-D", "IBU-C", "case_d_legit"),
}


async def register_cross_ibu_records(services: Services) -> None:
    if not isinstance(services.db, Database):
        return
    records = [
        "BL100001",
        "BL100002",
        "BL100003",
        "BL789456",
        "BL100005",
        "BL100006",
        "BL100007",
        "BL100008",
    ]
    async with services.db.engine.begin() as connection:
        for fingerprint in records:
            await connection.execute(
                text(
                    "INSERT INTO document_registry (document_fingerprint, ibu_id, document_type) "
                    "VALUES (:fingerprint, 'IBU-C', 'bill_of_lading') "
                    "ON CONFLICT (document_fingerprint) DO UPDATE SET ibu_id='IBU-C'"
                ),
                {"fingerprint": fingerprint},
            )


def load_fixture(case_id: str) -> dict[str, Any]:
    path = ROOT / "fixtures" / "pre_extracted" / f"{case_id}.json"
    return dict(json.loads(path.read_text(encoding="utf-8")))


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
        await register_cross_ibu_records(services)
        labels = [case] if case else list(CASES)
        for label in labels:
            await seed_case(services, label)
        count = 0
        for label in labels:
            count += len(await services.repository.list_documents(CASES[label][0]))
        print(
            f"Seeded {len(labels)} demo cases and {count} documents in {monotonic() - started:.2f}s"
        )
    finally:
        await services.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Idempotently seed Sprint 1 demo documents")
    parser.add_argument("--case", choices=CASES)
    arguments = parser.parse_args()
    asyncio.run(main(arguments.case))
