from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .contracts import (
    BillOfLadingFields,
    CommercialInvoiceFields,
    DocumentStatus,
    DocumentType,
    InsuranceCertificateFields,
    PackingListFields,
    RequiredDocumentSpec,
)


class LCRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lc_number: str | None = None
    issuing_bank: str | None = None
    applicant: str | None = None
    beneficiary: str | None = None
    credit_amount: Decimal | None = None
    currency: str | None = None
    about_flag: bool = False
    expiry_date: date | None = None
    latest_shipment_date: date | None = None
    credit_specific_presentation_days: int | None = None
    partial_shipments_allowed: bool = True
    required_documents: list[RequiredDocumentSpec] = []
    special_conditions: list[str] = []
    goods_description: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    loading_port: str | None = None
    discharge_port: str | None = None


class RuleDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    ucp_article: str
    description: str
    version: str
    enabled: bool
    parameters: dict[str, str] = {}


class Severity(StrEnum):
    MATERIAL = "MATERIAL"
    REVIEW = "REVIEW"
    POTENTIALLY_WAIVABLE = "POTENTIALLY_WAIVABLE"
    ADVISORY = "ADVISORY"


class ComplianceFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: str
    rule_id: str
    ucp_article: str
    document_id: str
    field_name: str
    page_ref: int | None
    expected: str
    actual: str
    severity: Severity
    evidence: dict[str, Any]
    rule_version: str


class ComplianceStatus(StrEnum):
    COMPLIANT = "COMPLIANT"
    DISCREPANCY = "DISCREPANCY"
    INCOMPLETE = "INCOMPLETE"


class ComplianceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    completeness_status: Literal["COMPLETE", "INCOMPLETE"]
    missing_documents: list[str]
    findings: list[ComplianceFinding]
    overall_status: ComplianceStatus
    evaluated_at: datetime
    rule_versions_used: dict[str, str]


class PresentedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    document_type: DocumentType
    status: DocumentStatus
    originals_presented: int = 1
    copies_presented: int = 0
    page_refs: dict[str, list[int]] = {}


class ComplianceCaseFacts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    lc: LCRequirements
    presented_documents: list[PresentedDocument]
    invoice: CommercialInvoiceFields | None = None
    invoice_document_id: str = "commercial_invoice"
    bill_of_lading: BillOfLadingFields | None = None
    bill_of_lading_document_id: str = "bill_of_lading"
    packing_list: PackingListFields | None = None
    packing_list_document_id: str = "packing_list"
    insurance: InsuranceCertificateFields | None = None
    insurance_document_id: str = "insurance_certificate"
    drawing_amount: Decimal | None = None
    presentation_date: date | None = None
    is_original_transport_document: bool = True
    is_bulk_or_generic: bool = False
    evaluated_at: datetime


class ComplianceRunResponse(BaseModel):
    result: ComplianceResult


class ComplianceRunRequest(BaseModel):
    presentation_date: date | None = None
    drawing_amount: Decimal | None = None
    is_original_transport_document: bool = True
    is_bulk_or_generic: bool = False
