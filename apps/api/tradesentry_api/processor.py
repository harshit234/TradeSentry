from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any, Literal

from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from pydantic import ValidationError
from pypdf import PdfReader

from models.contracts import (
    BillOfLadingFields,
    CertificateOfOriginFields,
    CommercialInvoiceFields,
    DocumentStatus,
    DocumentType,
    ExtractionResult,
    FieldConfidence,
    InspectionCertificateFields,
    InsuranceCertificateFields,
    LetterOfCreditFields,
    PackingListFields,
)

from .audit_store import AuditEvent, AuditEventType, AuditStore
from .documents import DocumentRecord, classify_document
from .ocr import LLMFallback, OCRProvider, RawOCRResult
from .repository import DocumentRepository

logger = logging.getLogger(__name__)

QUESTION_FIELDS: dict[str, str] = {
    "what is the lc number?": "lc_number",
    "what is the credit amount?": "credit_amount",
    "what is the expiry date?": "expiry_date",
    "who is the beneficiary?": "beneficiary",
    "who is the applicant?": "applicant",
    "what is the latest shipment date?": "latest_shipment_date",
    "what is the presentation period?": "credit_specific_presentation_days",
    "what is the port of loading?": "loading_port",
    "what is the port of discharge?": "discharge_port",
    "what is the bill of lading number?": "bl_number",
    "what is the vessel name?": "vessel_name",
    "what is the imo number?": "imo_number",
    "what is the voyage number?": "voyage_number",
    "what is the on-board date?": "on_board_date",
    "who is the shipper?": "shipper",
    "who is the consignee?": "consignee",
    "what is the invoice number?": "invoice_number",
    "what is the invoice amount?": "invoice_amount",
    "what is the currency?": "currency",
    "what is the quantity?": "quantity",
    "what is the unit price?": "unit_price",
    "what is the hs code?": "hs_code",
    "what is the country of origin?": "country_of_origin",
    "what is the certificate number?": "certificate_number",
    "who is the exporter?": "exporter",
    "what is the policy number?": "policy_number",
    "what is the insured amount?": "insured_amount",
    "who is the insured party?": "insured_party",
    "who is the insurer?": "insurer",
}

SCHEMA_BY_TYPE: dict[DocumentType, type[Any]] = {
    DocumentType.LETTER_OF_CREDIT: LetterOfCreditFields,
    DocumentType.COMMERCIAL_INVOICE: CommercialInvoiceFields,
    DocumentType.BILL_OF_LADING: BillOfLadingFields,
    DocumentType.PACKING_LIST: PackingListFields,
    DocumentType.CERTIFICATE_OF_ORIGIN: CertificateOfOriginFields,
    DocumentType.INSURANCE_CERTIFICATE: InsuranceCertificateFields,
    DocumentType.INSPECTION_CERTIFICATE: InspectionCertificateFields,
}


def page_count(data: bytes, mime_type: str) -> int:
    if mime_type == "application/pdf":
        return len(PdfReader(BytesIO(data)).pages)
    return 1


def _coerce_value(field_name: str, value: str) -> object:
    if field_name in {
        "credit_amount",
        "invoice_amount",
        "insured_amount",
        "quantity",
        "unit_price",
    }:
        normalized = "".join(
            character for character in value if character.isdigit() or character in ".-"
        )
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return value
    if field_name == "credit_specific_presentation_days":
        digits = "".join(character for character in value if character.isdigit())
        return int(digits) if digits else value
    return value


def build_extraction(
    document: DocumentRecord, raw: RawOCRResult, fallback_fields: dict[str, Any]
) -> ExtractionResult:
    values: dict[str, Any] = dict(fallback_fields)
    confidence: dict[str, FieldConfidence] = {}
    page_refs: dict[str, list[int]] = {}
    for question, answer in raw.query_results.items():
        field_name = QUESTION_FIELDS.get(question.lower())
        if not field_name:
            continue
        values[field_name] = _coerce_value(field_name, answer.answer)
        confidence[field_name] = FieldConfidence(confidence=answer.confidence, pages=[answer.page])
        page_refs[field_name] = [answer.page]
    low_fields = [name for name, value in confidence.items() if value.confidence < 0.70]
    status: Literal["EXTRACTED", "PARTIAL", "FAILED"] = (
        "PARTIAL" if raw.overall_confidence < 0.70 or raw.low_confidence_pages else "EXTRACTED"
    )
    schema = SCHEMA_BY_TYPE.get(document.document_type)
    typed_fields: Any = values
    if schema is not None:
        try:
            typed_fields = schema.model_validate(values)
        except ValidationError:
            status = "PARTIAL"
    return ExtractionResult(
        document_id=document.id,
        document_type=document.document_type,
        fields=typed_fields,
        confidence=confidence,
        overall_confidence=raw.overall_confidence,
        page_refs=page_refs,
        extraction_flags=sorted(set(low_fields)),
        processing_status=status,
        processed_at=datetime.now(UTC),
    )


class DocumentProcessor:
    def __init__(
        self,
        repository: DocumentRepository,
        ocr: OCRProvider,
        fallback: LLMFallback,
        bucket: str,
        audit_store: AuditStore | None = None,
    ) -> None:
        self.repository = repository
        self.ocr = ocr
        self.fallback = fallback
        self.bucket = bucket
        self.audit_store = audit_store

    async def _audit(
        self, document: DocumentRecord, event_type: AuditEventType, suffix: str
    ) -> None:
        if self.audit_store is None:
            return
        case = await self.repository.get_case(document.case_id)
        await self.audit_store.record(
            AuditEvent(
                case_id=document.case_id,
                ibu_id="system" if case is None else case.ibu_id,
                actor_id="document-processor",
                actor_role="AGENT",
                event_type=event_type,
                payload_ref=f"document://{document.id}/{suffix}",
            )
        )

    async def process(self, document: DocumentRecord, data: bytes) -> None:
        try:
            document.document_type = classify_document(document.filename)
            document.status = DocumentStatus.CLASSIFIED
            if document.document_type is DocumentType.UNKNOWN:
                document.advisory = "Document type could not be identified; generic extraction used"
            await self.repository.save_document(document)
            await self._audit(document, AuditEventType.DOCUMENT_CLASSIFIED, "classified")
            document.status = DocumentStatus.EXTRACTING
            await self.repository.save_document(document)
            raw = await self.ocr.analyze_document(
                self.bucket,
                document.s3_key,
                document.document_type,
                page_count(data, document.mime_type),
            )
            if document.document_type is DocumentType.UNKNOWN:
                document.document_type = classify_document(document.filename, raw.full_text)
            document.textract_job_id = raw.job_id
            fallback_fields: dict[str, Any] = {}
            if raw.low_confidence_pages or raw.overall_confidence < 0.70:
                fallback_fields = await self.fallback.reextract(raw, document.document_type)
            extraction = build_extraction(document, raw, fallback_fields)
            document.extraction = extraction
            document.overall_confidence = extraction.overall_confidence
            document.status = DocumentStatus(extraction.processing_status)
            await self.repository.save_document(document)
            await self._audit(document, AuditEventType.DOCUMENT_EXTRACTED, "extracted")
            logger.info(
                "Document extraction completed",
                extra={"extraction_confidence": extraction.overall_confidence},
            )
            if document.document_type is DocumentType.LETTER_OF_CREDIT:
                await self._audit(document, AuditEventType.LC_PARSED, "lc-parsed")
        except TimeoutError:
            document.status = DocumentStatus.FAILED
            document.error_code = "DATA_UNAVAILABLE"
            await self.repository.save_document(document)
        except (ClientError, RuntimeError, ValueError):
            document.status = DocumentStatus.FAILED
            document.error_code = "EXTRACTION_FAILED"
            await self.repository.save_document(document)
        except Exception:  # noqa: BLE001 - malformed documents fail safely in the background
            document.status = DocumentStatus.FAILED
            document.error_code = "EXTRACTION_FAILED"
            await self.repository.save_document(document)
