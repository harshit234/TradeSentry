from __future__ import annotations

from decimal import Decimal

from models.compliance import (
    ComplianceCaseFacts,
    ComplianceFinding,
    ComplianceResult,
    ComplianceStatus,
    LCRequirements,
    PresentedDocument,
)
from models.contracts import DocumentStatus, DocumentType

from .checks import (
    check_bill_of_lading,
    check_commercial_invoice,
    check_insurance,
    check_numeric_consistency,
    check_partial_shipments,
    check_presentation_period,
    check_quantity_tolerance,
    check_string_consistency,
)
from .definitions import decimal_parameter, rule_definitions


def check_document_completeness(
    lc: LCRequirements, presented_documents: list[PresentedDocument]
) -> list[str]:
    missing: list[str] = []
    extracted = [
        document for document in presented_documents if document.status is DocumentStatus.EXTRACTED
    ]
    for required in sorted(lc.required_documents, key=lambda item: item.document_type.value):
        if not required.required:
            continue
        matching = [
            document for document in extracted if document.document_type is required.document_type
        ]
        if not matching:
            missing.append(required.document_type.value)
            continue
        originals = sum(document.originals_presented for document in matching)
        copies = sum(document.copies_presented for document in matching)
        if originals < required.originals_required:
            missing.append(
                f"{required.document_type.value}:originals({originals}/{required.originals_required})"
            )
        if copies < required.copies_required:
            missing.append(
                f"{required.document_type.value}:copies({copies}/{required.copies_required})"
            )
    return sorted(missing)


def _page(facts: ComplianceCaseFacts, document_type: DocumentType, field_name: str) -> int | None:
    document = next(
        (
            item
            for item in facts.presented_documents
            if item.document_type is document_type and item.status is DocumentStatus.EXTRACTED
        ),
        None,
    )
    pages = document.page_refs.get(field_name, []) if document else []
    return pages[0] if pages else None


def _packing_description(facts: ComplianceCaseFacts) -> str | None:
    if facts.packing_list is None:
        return None
    descriptions = [item.description for item in facts.packing_list.line_items if item.description]
    return "; ".join(descriptions) or None


def _cross_document_checks(facts: ComplianceCaseFacts) -> list[ComplianceFinding]:
    findings: list[ComplianceFinding] = []
    invoice, bl, packing = facts.invoice, facts.bill_of_lading, facts.packing_list
    if invoice:
        findings.extend(
            check_string_consistency(
                facts.lc.applicant,
                invoice.buyer,
                document_id=facts.invoice_document_id,
                field_name="buyer",
                page_ref=_page(facts, DocumentType.COMMERCIAL_INVOICE, "buyer"),
            )
        )
    if bl:
        findings.extend(
            check_string_consistency(
                facts.lc.beneficiary,
                bl.shipper,
                document_id=facts.bill_of_lading_document_id,
                field_name="shipper",
                page_ref=_page(facts, DocumentType.BILL_OF_LADING, "shipper"),
            )
        )
        findings.extend(
            check_string_consistency(
                facts.lc.applicant,
                bl.consignee,
                document_id=facts.bill_of_lading_document_id,
                field_name="consignee",
                page_ref=_page(facts, DocumentType.BILL_OF_LADING, "consignee"),
            )
        )
    if invoice and bl:
        findings.extend(
            check_string_consistency(
                invoice.goods_description,
                bl.goods_description,
                document_id=facts.bill_of_lading_document_id,
                field_name="goods_description",
                page_ref=_page(facts, DocumentType.BILL_OF_LADING, "goods_description"),
            )
        )
        findings.extend(
            check_numeric_consistency(
                invoice.quantity,
                bl.quantity,
                document_id=facts.bill_of_lading_document_id,
                field_name="quantity",
                page_ref=_page(facts, DocumentType.BILL_OF_LADING, "quantity"),
            )
        )
        findings.extend(
            check_string_consistency(
                invoice.vessel_name,
                bl.vessel_name,
                document_id=facts.bill_of_lading_document_id,
                field_name="vessel_name",
                page_ref=_page(facts, DocumentType.BILL_OF_LADING, "vessel_name"),
            )
        )
    if invoice and packing:
        findings.extend(
            check_string_consistency(
                invoice.goods_description,
                _packing_description(facts),
                document_id=facts.packing_list_document_id,
                field_name="goods_description",
                page_ref=_page(facts, DocumentType.PACKING_LIST, "line_items"),
            )
        )
        findings.extend(
            check_numeric_consistency(
                invoice.quantity,
                packing.total_quantity,
                document_id=facts.packing_list_document_id,
                field_name="total_quantity",
                page_ref=_page(facts, DocumentType.PACKING_LIST, "total_quantity"),
            )
        )
    return findings


def evaluate_compliance(facts: ComplianceCaseFacts) -> ComplianceResult:
    missing = check_document_completeness(facts.lc, facts.presented_documents)
    if missing:
        return ComplianceResult(
            case_id=facts.case_id,
            completeness_status="INCOMPLETE",
            missing_documents=missing,
            findings=[],
            overall_status=ComplianceStatus.INCOMPLETE,
            evaluated_at=facts.evaluated_at,
            rule_versions_used={},
        )

    findings: list[ComplianceFinding] = []
    if facts.invoice:
        findings.extend(
            check_commercial_invoice(
                facts.lc,
                facts.invoice,
                drawing_amount=facts.drawing_amount,
                document_id=facts.invoice_document_id,
            )
        )
        if facts.lc.quantity is not None and facts.invoice.quantity is not None:
            credit = facts.lc.credit_amount
            drawing = facts.drawing_amount or facts.invoice.invoice_amount
            about = (
                Decimal(decimal_parameter("UCP600-ART30A-AMOUNT-TOLERANCE", "about_tolerance"))
                if facts.lc.about_flag
                else Decimal(0)
            )
            upper = credit * (Decimal(1) + about) if credit is not None else None
            within = drawing is None or upper is None or drawing <= upper
            findings.extend(
                check_quantity_tolerance(
                    facts.lc.quantity,
                    facts.invoice.quantity,
                    facts.is_bulk_or_generic,
                    within,
                    document_id=facts.invoice_document_id,
                    page_ref=_page(facts, DocumentType.COMMERCIAL_INVOICE, "quantity"),
                )
            )
    if facts.bill_of_lading:
        findings.extend(
            check_bill_of_lading(
                facts.lc, facts.bill_of_lading, document_id=facts.bill_of_lading_document_id
            )
        )
        findings.extend(
            check_partial_shipments(
                facts.lc, facts.bill_of_lading, document_id=facts.bill_of_lading_document_id
            )
        )
        shipment_date = facts.bill_of_lading.on_board_date or facts.bill_of_lading.bl_date
        if shipment_date and facts.presentation_date and facts.lc.expiry_date:
            findings.extend(
                check_presentation_period(
                    facts.is_original_transport_document,
                    shipment_date,
                    facts.presentation_date,
                    facts.lc.expiry_date,
                    facts.lc.credit_specific_presentation_days,
                    document_id=facts.bill_of_lading_document_id,
                    page_ref=_page(facts, DocumentType.BILL_OF_LADING, "on_board_date"),
                )
            )
    if facts.invoice and facts.insurance:
        findings.extend(
            check_insurance(
                facts.lc,
                facts.invoice,
                facts.insurance,
                bill_of_lading=facts.bill_of_lading,
                document_id=facts.insurance_document_id,
            )
        )
    findings.extend(_cross_document_checks(facts))
    findings = sorted(
        findings,
        key=lambda item: (
            item.rule_id,
            item.document_id,
            item.field_name,
            item.actual,
            item.finding_id,
        ),
    )
    versions = {
        definition.rule_id: definition.version
        for definition in sorted(rule_definitions().values(), key=lambda item: item.rule_id)
    }
    return ComplianceResult(
        case_id=facts.case_id,
        completeness_status="COMPLETE",
        missing_documents=[],
        findings=findings,
        overall_status=(ComplianceStatus.DISCREPANCY if findings else ComplianceStatus.COMPLIANT),
        evaluated_at=facts.evaluated_at,
        rule_versions_used=versions,
    )
