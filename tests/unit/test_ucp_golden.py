from __future__ import annotations

import subprocess
import sys
from datetime import UTC, date, datetime
from decimal import Decimal

from models.compliance import (
    ComplianceCaseFacts,
    ComplianceStatus,
    LCRequirements,
    PresentedDocument,
    Severity,
)
from models.contracts import (
    BillOfLadingFields,
    CommercialInvoiceFields,
    DocumentStatus,
    DocumentType,
    InsuranceCertificateFields,
    LetterOfCreditFields,
    PackingLineItem,
    PackingListFields,
    RequiredDocumentSpec,
)
from rules.checks import ART14C, ART14D, ART30B, check_presentation_period
from rules.engine import check_document_completeness, evaluate_compliance
from rules.parser import parse_lc_requirements

NOW = datetime(2024, 9, 8, 12, tzinfo=UTC)
ALL_TYPES = [item for item in DocumentType if item is not DocumentType.UNKNOWN]


def base_facts() -> ComplianceCaseFacts:
    lc = LCRequirements(
        lc_number="LC-1",
        applicant="Importer Ltd",
        beneficiary="Exporter Ltd",
        credit_amount=Decimal(250000),
        currency="USD",
        expiry_date=date(2024, 10, 1),
        latest_shipment_date=date(2024, 8, 20),
        partial_shipments_allowed=False,
        goods_description="Rice",
        quantity=Decimal(500),
        unit="MT",
        loading_port="Mundra",
        discharge_port="Singapore",
        required_documents=[RequiredDocumentSpec(document_type=item) for item in ALL_TYPES],
    )
    presented = [
        PresentedDocument(
            document_id=f"doc-{item.value}",
            document_type=item,
            status=DocumentStatus.EXTRACTED,
            page_refs={"vessel_name": [1], "goods_description": [1], "quantity": [1]},
        )
        for item in ALL_TYPES
    ]
    return ComplianceCaseFacts(
        case_id="TC-01",
        lc=lc,
        presented_documents=presented,
        invoice=CommercialInvoiceFields(
            seller="Exporter Ltd",
            buyer="Importer Ltd",
            currency="USD",
            invoice_amount=Decimal(250000),
            quantity=Decimal(500),
            unit="MT",
            goods_description="Rice",
            vessel_name="Ocean Star",
        ),
        invoice_document_id="doc-commercial_invoice",
        bill_of_lading=BillOfLadingFields(
            shipper="Exporter Ltd",
            consignee="Importer Ltd",
            vessel_name="Ocean Star",
            loading_port="Mundra",
            discharge_port="Singapore",
            on_board_notation=True,
            on_board_date=date(2024, 8, 14),
            goods_description="Rice",
            quantity=Decimal(500),
            unit="MT",
            carrier_or_master_signature=True,
            partial_shipment_indicated=False,
        ),
        bill_of_lading_document_id="doc-bill_of_lading",
        packing_list=PackingListFields(
            line_items=[PackingLineItem(description="Rice", quantity=Decimal(500), unit="MT")],
            total_quantity=Decimal(500),
        ),
        packing_list_document_id="doc-packing_list",
        insurance=InsuranceCertificateFields(
            insured_amount=Decimal(275000),
            currency="USD",
            effective_date=date(2024, 8, 13),
            goods_description="Rice",
            vessel_name="Ocean Star",
            loading_port="Mundra",
            discharge_port="Singapore",
        ),
        insurance_document_id="doc-insurance_certificate",
        drawing_amount=Decimal(250000),
        presentation_date=date(2024, 8, 20),
        is_bulk_or_generic=True,
        evaluated_at=NOW,
    )


def test_tc01_all_consistent_is_compliant() -> None:
    result = evaluate_compliance(base_facts())
    assert result.overall_status is ComplianceStatus.COMPLIANT
    assert result.findings == []


def test_tc02_about_amount_within_ten_percent_is_compliant() -> None:
    facts = base_facts()
    facts = facts.model_copy(
        update={
            "case_id": "TC-02",
            "lc": facts.lc.model_copy(update={"about_flag": True}),
            "invoice": facts.invoice.model_copy(update={"invoice_amount": Decimal(265000)})
            if facts.invoice
            else None,
            "insurance": facts.insurance.model_copy(update={"insured_amount": Decimal(291500)})
            if facts.insurance
            else None,
            "drawing_amount": Decimal(265000),
        }
    )
    assert evaluate_compliance(facts).overall_status is ComplianceStatus.COMPLIANT


def test_tc03_exact_credit_exceeded_is_material() -> None:
    facts = base_facts()
    facts = facts.model_copy(
        update={
            "case_id": "TC-03",
            "invoice": facts.invoice.model_copy(update={"invoice_amount": Decimal(275000)})
            if facts.invoice
            else None,
            "insurance": facts.insurance.model_copy(update={"insured_amount": Decimal(302500)})
            if facts.insurance
            else None,
            "drawing_amount": Decimal(275000),
        }
    )
    result = evaluate_compliance(facts)
    assert result.overall_status is ComplianceStatus.DISCREPANCY
    assert any(
        item.severity is Severity.MATERIAL
        and item.ucp_article in {"Art. 30(a) / Art. 18", "Art. 30(c)"}
        for item in result.findings
    )


def quantity_case(case_id: str, quantity: str) -> ComplianceCaseFacts:
    facts = base_facts()
    return facts.model_copy(
        update={
            "case_id": case_id,
            "invoice": facts.invoice.model_copy(update={"quantity": Decimal(quantity)})
            if facts.invoice
            else None,
            "bill_of_lading": facts.bill_of_lading.model_copy(
                update={"quantity": Decimal(quantity)}
            )
            if facts.bill_of_lading
            else None,
            "packing_list": facts.packing_list.model_copy(
                update={
                    "total_quantity": Decimal(quantity),
                    "line_items": [
                        PackingLineItem(description="Rice", quantity=Decimal(quantity), unit="MT")
                    ],
                }
            )
            if facts.packing_list
            else None,
        }
    )


def test_tc04_bulk_quantity_within_five_percent_is_compliant() -> None:
    assert (
        evaluate_compliance(quantity_case("TC-04", "520")).overall_status
        is ComplianceStatus.COMPLIANT
    )


def test_tc05_bulk_quantity_over_five_percent_is_material() -> None:
    result = evaluate_compliance(quantity_case("TC-05", "530"))
    assert any(
        item.rule_id == ART30B and item.severity is Severity.MATERIAL for item in result.findings
    )


def test_tc06_default_presentation_period_exceeded() -> None:
    facts = base_facts().model_copy(
        update={"case_id": "TC-06", "presentation_date": date(2024, 9, 8)}
    )
    result = evaluate_compliance(facts)
    assert any(item.rule_id == ART14C and "25 days" in item.actual for item in result.findings)


def test_tc07_credit_specific_thirty_days_is_compliant() -> None:
    facts = base_facts()
    facts = facts.model_copy(
        update={
            "case_id": "TC-07",
            "lc": facts.lc.model_copy(update={"credit_specific_presentation_days": 30}),
            "presentation_date": date(2024, 9, 8),
        }
    )
    assert evaluate_compliance(facts).overall_status is ComplianceStatus.COMPLIANT


def test_tc08_missing_insurance_stops_field_checks() -> None:
    facts = base_facts()
    presented = [
        item
        for item in facts.presented_documents
        if item.document_type is not DocumentType.INSURANCE_CERTIFICATE
    ]
    facts = facts.model_copy(
        update={
            "case_id": "TC-08",
            "presented_documents": presented,
            "invoice": facts.invoice.model_copy(update={"invoice_amount": Decimal(999999)})
            if facts.invoice
            else None,
        }
    )
    result = evaluate_compliance(facts)
    assert result.overall_status is ComplianceStatus.INCOMPLETE
    assert result.missing_documents == ["insurance_certificate"]
    assert result.findings == []


def test_tc09_vessel_ocr_variation_is_advisory() -> None:
    facts = base_facts()
    facts = facts.model_copy(
        update={
            "case_id": "TC-09",
            "bill_of_lading": facts.bill_of_lading.model_copy(update={"vessel_name": "Ocean Staar"})
            if facts.bill_of_lading
            else None,
            "insurance": facts.insurance.model_copy(update={"vessel_name": "Ocean Staar"})
            if facts.insurance
            else None,
        }
    )
    result = evaluate_compliance(facts)
    vessel = [item for item in result.findings if item.field_name == "vessel_name"]
    assert len(vessel) == 1
    assert vessel[0].rule_id == ART14D
    assert vessel[0].severity is Severity.ADVISORY


def test_tc10_goods_conflict_is_material() -> None:
    facts = base_facts()
    facts = facts.model_copy(
        update={
            "case_id": "TC-10",
            "bill_of_lading": facts.bill_of_lading.model_copy(update={"goods_description": "Wheat"})
            if facts.bill_of_lading
            else None,
            "insurance": facts.insurance.model_copy(update={"goods_description": "Wheat"})
            if facts.insurance
            else None,
        }
    )
    result = evaluate_compliance(facts)
    goods = [
        item
        for item in result.findings
        if item.rule_id == ART14D and item.field_name == "goods_description"
    ]
    assert len(goods) == 1
    assert goods[0].severity is Severity.MATERIAL


def test_result_is_identical_across_ten_runs() -> None:
    rendered = [evaluate_compliance(base_facts()).model_dump_json() for _ in range(10)]
    assert len(set(rendered)) == 1


def test_presentation_period_and_expiry_are_independent() -> None:
    findings = check_presentation_period(
        True, date(2024, 8, 1), date(2024, 9, 1), date(2024, 8, 31), None
    )
    assert len(findings) == 2
    assert {item.field_name for item in findings} == {"presentation_date", "expiry_date"}


def test_rule_package_import_has_no_fastapi_dependency() -> None:
    command = "import sys, rules; assert 'fastapi' not in sys.modules"
    subprocess.run([sys.executable, "-c", command], check=True)


def test_severities_are_only_the_four_approved_values() -> None:
    approved = {
        Severity.MATERIAL,
        Severity.REVIEW,
        Severity.POTENTIALLY_WAIVABLE,
        Severity.ADVISORY,
    }
    assert all(
        item.severity in approved
        for item in evaluate_compliance(quantity_case("TC-05", "530")).findings
    )


def test_completeness_checks_original_and_copy_counts() -> None:
    requirements = LCRequirements(
        required_documents=[
            RequiredDocumentSpec(
                document_type=DocumentType.COMMERCIAL_INVOICE,
                originals_required=2,
                copies_required=1,
            )
        ]
    )
    presented = [
        PresentedDocument(
            document_id="invoice-1",
            document_type=DocumentType.COMMERCIAL_INVOICE,
            status=DocumentStatus.EXTRACTED,
            originals_presented=1,
            copies_presented=0,
        )
    ]
    assert check_document_completeness(requirements, presented) == [
        "commercial_invoice:copies(0/1)",
        "commercial_invoice:originals(1/2)",
    ]


def test_lc_parser_only_maps_typed_extracted_facts() -> None:
    parsed = parse_lc_requirements(
        LetterOfCreditFields(
            lc_number="LC-99",
            credit_amount=Decimal(100),
            about_flag=True,
            partial_shipments_allowed=False,
        )
    )
    assert parsed.lc_number == "LC-99"
    assert parsed.credit_amount == Decimal(100)
    assert parsed.about_flag is True
    assert parsed.partial_shipments_allowed is False
