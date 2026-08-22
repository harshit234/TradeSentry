# rules/completeness.py
# Pure Python. No LLM. No external calls.

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class CompletenessStatus(str, Enum):
    COMPLETE   = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    PENDING_LC = "PENDING_LC"   # LC not yet extracted — cannot check

class DocumentStatus(str, Enum):
    PRESENT  = "PRESENT"
    MISSING  = "MISSING"
    NOT_REQ  = "NOT_REQUIRED"

@dataclass
class RequiredDocumentSpec:
    document_type: str
    originals_required: int = 0
    copies_required: int = 0

@dataclass
class DocumentCompletenessResult:
    status: CompletenessStatus
    required: list[str]
    present: list[str]
    missing: list[str]
    not_required: list[str]
    detail: dict[str, DocumentStatus]

def check_completeness(
    lc_required_documents: list[RequiredDocumentSpec],
    extracted_document_types: list[str]
) -> DocumentCompletenessResult:
    """
    HARD RULE 1: If LC not yet extracted → PENDING_LC
                 No field-level compliance checks run.

    HARD RULE 2: If any required document is missing → INCOMPLETE
                 No field-level compliance checks run.

    HARD RULE 3: Only documents listed in LC required_documents
                 are checked. Additional documents submitted
                 are NOT penalized — they are simply ignored.

    HARD RULE 4: This function runs BEFORE every other check.
                 If result is not COMPLETE → return immediately.
                 Never skip this gate.
    """
    if not lc_required_documents:
        return DocumentCompletenessResult(
            status=CompletenessStatus.PENDING_LC,
            required=[], present=[], missing=[], not_required=[], detail={}
        )

    required = [spec.document_type for spec in lc_required_documents]
    present  = [dt for dt in required if dt in extracted_document_types]
    missing  = [dt for dt in required if dt not in extracted_document_types]

    detail = {}
    for dt in required:
        detail[dt] = DocumentStatus.PRESENT if dt in extracted_document_types \
                     else DocumentStatus.MISSING

    status = CompletenessStatus.COMPLETE if not missing \
             else CompletenessStatus.INCOMPLETE

    return DocumentCompletenessResult(
        status=status,
        required=required,
        present=present,
        missing=missing,
        not_required=[],
        detail=detail
    )
