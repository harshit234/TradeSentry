from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded"]
    db: Literal["ok", "unavailable"]
    redis: Literal["ok", "unavailable"]
    s3: Literal["ok", "unavailable"]
    textract: Literal["ok", "unavailable"]
    dynamodb: Literal["ok", "unavailable"]
    version: str
    aws_region: str
    deployment: str
    infrastructure_note: str


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str
    correlation_id: str


class DocumentType(StrEnum):
    LETTER_OF_CREDIT = "letter_of_credit"
    COMMERCIAL_INVOICE = "commercial_invoice"
    BILL_OF_LADING = "bill_of_lading"
    PACKING_LIST = "packing_list"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    INSURANCE_CERTIFICATE = "insurance_certificate"
    INSPECTION_CERTIFICATE = "inspection_certificate"
    UNKNOWN = "unknown"


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    CLASSIFIED = "CLASSIFIED"
    QUEUED = "QUEUED"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    MISSING = "MISSING"


class RequiredDocumentSpec(BaseModel):
    document_type: DocumentType
    description: str | None = None
    required: bool = True
    originals_required: int = 0
    copies_required: int = 0
    additional_conditions: list[str] = []


class DocumentFieldsBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LetterOfCreditFields(DocumentFieldsBase):
    lc_number: str | None = None
    issuing_bank: str | None = None
    applicant: str | None = None
    beneficiary: str | None = None
    credit_amount: Decimal | None = None
    currency: str | None = None
    about_flag: bool | None = None
    expiry_date: Date | None = None
    latest_shipment_date: Date | None = None
    credit_specific_presentation_days: int | None = None
    loading_port: str | None = None
    discharge_port: str | None = None
    incoterms: str | None = None
    goods_description: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    partial_shipments_allowed: bool | None = None
    required_documents: list[RequiredDocumentSpec] = []
    special_conditions: list[str] = []


class CommercialInvoiceFields(DocumentFieldsBase):
    invoice_number: str | None = None
    invoice_date: Date | None = None
    seller: str | None = None
    buyer: str | None = None
    currency: str | None = None
    invoice_amount: Decimal | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    goods_description: str | None = None
    hs_code: str | None = None
    incoterms: str | None = None
    country_of_origin: str | None = None
    loading_port: str | None = None
    discharge_port: str | None = None
    vessel_name: str | None = None


class BillOfLadingFields(DocumentFieldsBase):
    bl_number: str | None = None
    bl_date: Date | None = None
    vessel_name: str | None = None
    imo_number: str | None = None
    voyage_number: str | None = None
    carrier: str | None = None
    shipper: str | None = None
    consignee: str | None = None
    notify_party: str | None = None
    loading_port: str | None = None
    discharge_port: str | None = None
    on_board_notation: bool | None = None
    on_board_date: Date | None = None
    goods_description: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    hs_code: str | None = None
    freight_terms: str | None = None
    carrier_or_master_signature: bool | None = None
    partial_shipment_indicated: bool | None = None


class PackingLineItem(BaseModel):
    description: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    gross_weight: Decimal | None = None
    net_weight: Decimal | None = None
    packages: int | None = None


class PackingListFields(DocumentFieldsBase):
    seller: str | None = None
    buyer: str | None = None
    line_items: list[PackingLineItem] = []
    total_quantity: Decimal | None = None
    total_gross_weight: Decimal | None = None
    total_packages: int | None = None


class InsuranceCertificateFields(DocumentFieldsBase):
    policy_number: str | None = None
    certificate_number: str | None = None
    date: Date | None = None
    insured_party: str | None = None
    insurer: str | None = None
    insured_amount: Decimal | None = None
    currency: str | None = None
    coverage_type: str | None = None
    risks_covered: str | None = None
    vessel_name: str | None = None
    voyage: str | None = None
    loading_port: str | None = None
    discharge_port: str | None = None
    goods_description: str | None = None
    effective_date: Date | None = None


class CertificateOfOriginFields(DocumentFieldsBase):
    certificate_number: str | None = None
    date: Date | None = None
    exporter: str | None = None
    producer: str | None = None
    consignee: str | None = None
    country_of_origin: str | None = None
    destination_country: str | None = None
    goods_description: str | None = None
    hs_code: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None


class InspectionCertificateFields(DocumentFieldsBase):
    certificate_number: str | None = None
    date: Date | None = None
    inspection_agency: str | None = None
    inspection_date: Date | None = None
    applicant: str | None = None
    goods_description: str | None = None
    quantity: Decimal | None = None
    result: str | None = None
    findings: list[str] = []


ExtractedFields = (
    LetterOfCreditFields
    | CommercialInvoiceFields
    | BillOfLadingFields
    | PackingListFields
    | InsuranceCertificateFields
    | CertificateOfOriginFields
    | InspectionCertificateFields
)


class FieldConfidence(BaseModel):
    confidence: float
    pages: list[int] = []


class ExtractionResult(BaseModel):
    document_id: str
    document_type: DocumentType
    fields: ExtractedFields | dict[str, Any]
    confidence: dict[str, FieldConfidence]
    overall_confidence: float
    page_refs: dict[str, list[int]]
    extraction_flags: list[str] = []
    processing_status: Literal["EXTRACTED", "PARTIAL", "FAILED"]
    processed_at: datetime


class CaseCreate(BaseModel):
    case_id: str | None = None
    ibu_id: str


class CaseResponse(BaseModel):
    case_id: str
    ibu_id: str
    status: str


class DocumentResponse(BaseModel):
    document_id: str
    case_id: str
    filename: str
    document_type: DocumentType
    status: DocumentStatus
    overall_confidence: float | None = None
    extraction_flags: list[str] = []
    view_url: str | None = None
    extraction: ExtractionResult | None = None
    error_code: str | None = None
    advisory: str | None = None


class UploadResponse(BaseModel):
    document_id: str
    status: Literal["UPLOADED"]


class CompletenessStatus(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    PENDING_LC = "PENDING_LC"


class DocumentCompleteness(BaseModel):
    required_types: list[DocumentType]
    present_types: list[DocumentType]
    missing_types: list[DocumentType]
    status: CompletenessStatus
    can_run_investigation: bool
