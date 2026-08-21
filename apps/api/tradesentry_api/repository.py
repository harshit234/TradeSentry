from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy import text

from models.contracts import (
    BillOfLadingFields,
    CertificateOfOriginFields,
    CommercialInvoiceFields,
    DocumentStatus,
    DocumentType,
    ExtractionResult,
    InspectionCertificateFields,
    InsuranceCertificateFields,
    LetterOfCreditFields,
    PackingListFields,
)

from .db import Database
from .documents import CaseRecord, DocumentRecord

FIELD_SCHEMA_BY_TYPE: dict[DocumentType, type[BaseModel]] = {
    DocumentType.LETTER_OF_CREDIT: LetterOfCreditFields,
    DocumentType.COMMERCIAL_INVOICE: CommercialInvoiceFields,
    DocumentType.BILL_OF_LADING: BillOfLadingFields,
    DocumentType.PACKING_LIST: PackingListFields,
    DocumentType.CERTIFICATE_OF_ORIGIN: CertificateOfOriginFields,
    DocumentType.INSURANCE_CERTIFICATE: InsuranceCertificateFields,
    DocumentType.INSPECTION_CERTIFICATE: InspectionCertificateFields,
}


class DocumentRepository(Protocol):
    async def create_case(self, case: CaseRecord) -> CaseRecord: ...
    async def get_case(self, case_id: str) -> CaseRecord | None: ...
    async def list_cases(self) -> list[CaseRecord]: ...
    async def update_case_status(self, case_id: str, status: str) -> None: ...
    async def delete_case(self, case_id: str) -> None: ...
    async def save_document(self, document: DocumentRecord) -> DocumentRecord: ...
    async def get_document(self, case_id: str, document_id: str) -> DocumentRecord | None: ...
    async def get_by_hash(self, case_id: str, content_hash: str) -> DocumentRecord | None: ...
    async def list_documents(self, case_id: str) -> list[DocumentRecord]: ...


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.cases: dict[str, CaseRecord] = {}
        self.documents: dict[str, DocumentRecord] = {}

    async def create_case(self, case: CaseRecord) -> CaseRecord:
        existing = self.cases.get(case.id)
        if existing is not None:
            return existing
        self.cases[case.id] = case
        return case

    async def get_case(self, case_id: str) -> CaseRecord | None:
        return self.cases.get(case_id)

    async def list_cases(self) -> list[CaseRecord]:
        return sorted(self.cases.values(), key=lambda case: case.created_at, reverse=True)

    async def update_case_status(self, case_id: str, status: str) -> None:
        case = self.cases.get(case_id)
        if case is not None:
            case.status = status

    async def delete_case(self, case_id: str) -> None:
        self.cases.pop(case_id, None)
        self.documents = {
            key: value for key, value in self.documents.items() if value.case_id != case_id
        }

    async def save_document(self, document: DocumentRecord) -> DocumentRecord:
        self.documents[document.id] = document
        return document

    async def get_document(self, case_id: str, document_id: str) -> DocumentRecord | None:
        document = self.documents.get(document_id)
        return document if document is not None and document.case_id == case_id else None

    async def get_by_hash(self, case_id: str, content_hash: str) -> DocumentRecord | None:
        return next(
            (
                document
                for document in self.documents.values()
                if document.case_id == case_id and document.content_hash == content_hash
            ),
            None,
        )

    async def list_documents(self, case_id: str) -> list[DocumentRecord]:
        return sorted(
            (document for document in self.documents.values() if document.case_id == case_id),
            key=lambda document: document.created_at,
        )


class PostgresDocumentRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def create_case(self, case: CaseRecord) -> CaseRecord:
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO cases (id, ibu_id, status) VALUES (:id, :ibu, :status) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": case.id, "ibu": case.ibu_id, "status": case.status},
            )
        return await self.get_case(case.id) or case

    async def get_case(self, case_id: str) -> CaseRecord | None:
        async with self.database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT id, ibu_id, status, created_at FROM cases WHERE id=:id"),
                        {"id": case_id},
                    )
                )
                .mappings()
                .first()
            )
        return (
            CaseRecord(
                id=row["id"], ibu_id=row["ibu_id"], status=row["status"],
                created_at=row["created_at"],
            )
            if row else None
        )

    async def list_cases(self) -> list[CaseRecord]:
        async with self.database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text("SELECT id, ibu_id, status, created_at FROM cases ORDER BY created_at DESC")
                    )
                )
                .mappings()
                .all()
            )
        return [
            CaseRecord(
                id=row["id"], ibu_id=row["ibu_id"], status=row["status"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def update_case_status(self, case_id: str, status: str) -> None:
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text("UPDATE cases SET status=:status, updated_at=now() WHERE id=:case_id"),
                {"status": status, "case_id": case_id},
            )

    async def delete_case(self, case_id: str) -> None:
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM documents WHERE case_id=:id"), {"id": case_id}
            )
            await connection.execute(text("DELETE FROM cases WHERE id=:id"), {"id": case_id})

    async def save_document(self, document: DocumentRecord) -> DocumentRecord:
        extraction_json = document.extraction.model_dump_json() if document.extraction else None
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO documents
                    (id, case_id, filename, content_hash, mime_type, document_type, s3_key,
                     status, overall_confidence, extraction_json, textract_job_id, error_code, advisory)
                    VALUES (:id, :case_id, :filename, :content_hash, :mime_type, :document_type,
                            :s3_key, :status, :confidence, CAST(:extraction AS JSONB), :job_id,
                            :error_code, :advisory)
                    ON CONFLICT (id) DO UPDATE SET document_type=EXCLUDED.document_type,
                      status=EXCLUDED.status, overall_confidence=EXCLUDED.overall_confidence,
                      extraction_json=EXCLUDED.extraction_json,
                      textract_job_id=EXCLUDED.textract_job_id,
                      error_code=EXCLUDED.error_code, advisory=EXCLUDED.advisory"""
                ),
                {
                    "id": document.id,
                    "case_id": document.case_id,
                    "filename": document.filename,
                    "content_hash": document.content_hash,
                    "mime_type": document.mime_type,
                    "document_type": document.document_type.value,
                    "s3_key": document.s3_key,
                    "status": document.status.value,
                    "confidence": document.overall_confidence,
                    "extraction": extraction_json or "null",
                    "job_id": document.textract_job_id,
                    "error_code": document.error_code,
                    "advisory": document.advisory,
                },
            )
        return document

    def _from_row(self, row: object) -> DocumentRecord:
        values = row  # SQLAlchemy RowMapping is intentionally accessed dynamically.
        raw_extraction = values["extraction_json"]  # type: ignore[index]
        if isinstance(raw_extraction, str):
            raw_extraction = json.loads(raw_extraction)
        document_type = DocumentType(values["document_type"])  # type: ignore[index]
        if raw_extraction:
            schema = FIELD_SCHEMA_BY_TYPE.get(document_type)
            if schema is not None:
                raw_extraction["fields"] = schema.model_validate(raw_extraction["fields"])
        extraction = ExtractionResult.model_validate(raw_extraction) if raw_extraction else None
        return DocumentRecord(
            id=values["id"],  # type: ignore[index]
            case_id=values["case_id"],  # type: ignore[index]
            filename=values["filename"],  # type: ignore[index]
            content_hash=values["content_hash"],  # type: ignore[index]
            mime_type=values["mime_type"],  # type: ignore[index]
            s3_key=values["s3_key"],  # type: ignore[index]
            status=DocumentStatus(values["status"]),  # type: ignore[index]
            document_type=document_type,
            overall_confidence=values["overall_confidence"],  # type: ignore[index]
            extraction=extraction,
            textract_job_id=values["textract_job_id"],  # type: ignore[index]
            error_code=values["error_code"],  # type: ignore[index]
            advisory=values["advisory"],  # type: ignore[index]
            created_at=values["created_at"],  # type: ignore[index]
        )

    async def get_document(self, case_id: str, document_id: str) -> DocumentRecord | None:
        async with self.database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM documents WHERE case_id=:case_id AND id=:id"),
                        {"case_id": case_id, "id": document_id},
                    )
                )
                .mappings()
                .first()
            )
        return self._from_row(row) if row else None

    async def get_by_hash(self, case_id: str, content_hash: str) -> DocumentRecord | None:
        async with self.database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM documents WHERE case_id=:case_id AND content_hash=:hash"
                        ),
                        {"case_id": case_id, "hash": content_hash},
                    )
                )
                .mappings()
                .first()
            )
        return self._from_row(row) if row else None

    async def list_documents(self, case_id: str) -> list[DocumentRecord]:
        async with self.database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text("SELECT * FROM documents WHERE case_id=:case_id ORDER BY created_at"),
                        {"case_id": case_id},
                    )
                )
                .mappings()
                .all()
            )
        return [self._from_row(row) for row in rows]
