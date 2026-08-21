from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import PurePath

from models.contracts import DocumentStatus, DocumentType, ExtractionResult

MAX_FILENAME_LENGTH = 180


class DocumentValidationError(ValueError):
    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def detect_mime(data: bytes) -> str:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    raise DocumentValidationError("Only PDF, TIFF, and JPEG documents are supported", 415)


def validate_upload(data: bytes, maximum_bytes: int) -> str:
    if len(data) > maximum_bytes:
        raise DocumentValidationError("Document exceeds the configured 50 MB limit", 413)
    if not data:
        raise DocumentValidationError("Document is empty", 415)
    return detect_mime(data)


def sanitize_filename(filename: str | None, mime_type: str) -> str:
    fallback = {
        "application/pdf": "document.pdf",
        "image/tiff": "document.tiff",
        "image/jpeg": "document.jpg",
    }[mime_type]
    leaf = PurePath((filename or fallback).replace("\\", "/")).name
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", leaf).strip("._")
    return (safe or fallback)[:MAX_FILENAME_LENGTH]


FILENAME_HINTS: tuple[tuple[DocumentType, tuple[str, ...]], ...] = (
    (DocumentType.LETTER_OF_CREDIT, ("letter_of_credit", "letter-credit", "lc_", "lc.")),
    (DocumentType.COMMERCIAL_INVOICE, ("commercial_invoice", "invoice")),
    (DocumentType.BILL_OF_LADING, ("bill_of_lading", "bill-lading", "b_l", "bl_")),
    (DocumentType.PACKING_LIST, ("packing_list", "packing")),
    (DocumentType.CERTIFICATE_OF_ORIGIN, ("certificate_of_origin", "origin")),
    (DocumentType.INSURANCE_CERTIFICATE, ("insurance_certificate", "insurance")),
    (DocumentType.INSPECTION_CERTIFICATE, ("inspection_certificate", "inspection")),
)

KEYWORD_HINTS: tuple[tuple[DocumentType, tuple[str, ...]], ...] = (
    (DocumentType.LETTER_OF_CREDIT, ("documentary credit", "letter of credit", "credit number")),
    (DocumentType.COMMERCIAL_INVOICE, ("commercial invoice", "invoice number", "unit price")),
    (DocumentType.BILL_OF_LADING, ("bill of lading", "vessel", "shipper")),
    (DocumentType.PACKING_LIST, ("packing list", "gross weight", "net weight")),
    (DocumentType.CERTIFICATE_OF_ORIGIN, ("certificate of origin", "country of origin")),
    (DocumentType.INSURANCE_CERTIFICATE, ("insurance certificate", "insured amount")),
    (DocumentType.INSPECTION_CERTIFICATE, ("inspection certificate", "inspection agency")),
)


def classify_document(filename: str, first_page_text: str = "") -> DocumentType:
    normalized_name = filename.lower().replace(" ", "_")
    for document_type, hints in FILENAME_HINTS:
        if any(hint in normalized_name for hint in hints):
            return document_type
    normalized_text = first_page_text.lower()
    for document_type, hints in KEYWORD_HINTS:
        if any(hint in normalized_text for hint in hints):
            return document_type
    return DocumentType.UNKNOWN


def deterministic_document_id(case_id: str, data: bytes) -> str:
    digest = hashlib.sha256(case_id.encode() + b"\0" + data).hexdigest()
    return f"doc-{digest[:24]}"


@dataclass(slots=True)
class CaseRecord:
    id: str
    ibu_id: str
    status: str = "CREATED"


@dataclass(slots=True)
class DocumentRecord:
    id: str
    case_id: str
    filename: str
    content_hash: str
    mime_type: str
    s3_key: str
    status: DocumentStatus = DocumentStatus.UPLOADED
    document_type: DocumentType = DocumentType.UNKNOWN
    overall_confidence: float | None = None
    extraction: ExtractionResult | None = None
    textract_job_id: str | None = None
    error_code: str | None = None
    advisory: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
