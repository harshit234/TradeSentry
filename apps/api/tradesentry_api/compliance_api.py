from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, HTTPException, Request

from models.compliance import (
    ComplianceCaseFacts,
    ComplianceResult,
    ComplianceRunRequest,
    PresentedDocument,
)
from models.contracts import (
    BillOfLadingFields,
    CommercialInvoiceFields,
    DocumentType,
    InsuranceCertificateFields,
    LetterOfCreditFields,
    PackingListFields,
)
from rules.engine import evaluate_compliance
from rules.parser import parse_lc_requirements

from .documents import DocumentRecord
from .services import Services

router = APIRouter(prefix="/cases", tags=["compliance"])


def _services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


def _document_of_type(
    documents: list[DocumentRecord], document_type: DocumentType
) -> DocumentRecord | None:
    return next((item for item in documents if item.document_type is document_type), None)


def _fields(document: DocumentRecord | None, expected: type[object]) -> object | None:
    if document is None or document.extraction is None:
        return None
    fields = document.extraction.fields
    return fields if isinstance(fields, expected) else None


async def build_compliance_facts(
    services: Services, case_id: str, payload: ComplianceRunRequest
) -> ComplianceCaseFacts:
    case = await services.repository.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    documents = await services.repository.list_documents(case_id)
    lc_document = _document_of_type(documents, DocumentType.LETTER_OF_CREDIT)
    lc_fields = _fields(lc_document, LetterOfCreditFields)
    if not isinstance(lc_fields, LetterOfCreditFields):
        raise HTTPException(
            status_code=422, detail="Extracted Letter of Credit fields are required"
        )
    invoice_document = _document_of_type(documents, DocumentType.COMMERCIAL_INVOICE)
    bl_document = _document_of_type(documents, DocumentType.BILL_OF_LADING)
    packing_document = _document_of_type(documents, DocumentType.PACKING_LIST)
    insurance_document = _document_of_type(documents, DocumentType.INSURANCE_CERTIFICATE)
    invoice = _fields(invoice_document, CommercialInvoiceFields)
    bl = _fields(bl_document, BillOfLadingFields)
    packing = _fields(packing_document, PackingListFields)
    insurance = _fields(insurance_document, InsuranceCertificateFields)
    return ComplianceCaseFacts(
        case_id=case_id,
        lc=parse_lc_requirements(lc_fields),
        presented_documents=[
            PresentedDocument(
                document_id=document.id,
                document_type=document.document_type,
                status=document.status,
                originals_presented=1,
                copies_presented=0,
                page_refs=document.extraction.page_refs if document.extraction else {},
            )
            for document in documents
        ],
        invoice=invoice if isinstance(invoice, CommercialInvoiceFields) else None,
        invoice_document_id=invoice_document.id if invoice_document else "commercial_invoice",
        bill_of_lading=bl if isinstance(bl, BillOfLadingFields) else None,
        bill_of_lading_document_id=bl_document.id if bl_document else "bill_of_lading",
        packing_list=packing if isinstance(packing, PackingListFields) else None,
        packing_list_document_id=packing_document.id if packing_document else "packing_list",
        insurance=insurance if isinstance(insurance, InsuranceCertificateFields) else None,
        insurance_document_id=(
            insurance_document.id if insurance_document else "insurance_certificate"
        ),
        drawing_amount=payload.drawing_amount,
        presentation_date=payload.presentation_date,
        is_original_transport_document=payload.is_original_transport_document,
        is_bulk_or_generic=payload.is_bulk_or_generic,
        evaluated_at=datetime.now(UTC),
    )


@router.post("/{case_id}/compliance", response_model=ComplianceResult)
async def run_compliance(
    case_id: str, request: Request, payload: ComplianceRunRequest | None = None
) -> ComplianceResult:
    services = _services(request)
    facts = await build_compliance_facts(services, case_id, payload or ComplianceRunRequest())
    result = evaluate_compliance(facts)
    await services.compliance_store.save(result)
    return result


@router.get("/{case_id}/compliance", response_model=ComplianceResult)
async def get_compliance(case_id: str, request: Request) -> ComplianceResult:
    result = await _services(request).compliance_store.get(case_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Compliance result not found")
    return result
