from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any

from models.compliance import ComplianceFinding, LCRequirements, Severity
from models.contracts import (
    BillOfLadingFields,
    CommercialInvoiceFields,
    InsuranceCertificateFields,
)

from .definitions import decimal_parameter, rule

ART14C = "UCP600-ART14C-PRESENTATION-PERIOD"
ART14D = "UCP600-ART14D-DATA-CONSISTENCY"
ART18 = "UCP600-ART18-COMMERCIAL-INVOICE"
ART20 = "UCP600-ART20-BILL-OF-LADING"
ART28 = "UCP600-ART28-INSURANCE"
ART30A = "UCP600-ART30A-AMOUNT-TOLERANCE"
ART30B = "UCP600-ART30B-QUANTITY-TOLERANCE"
ART30C = "UCP600-ART30C-DRAWING-LIMIT"
ART31 = "UCP600-ART31-PARTIAL-SHIPMENTS"


def _finding(
    rule_id: str,
    document_id: str,
    field_name: str,
    expected: object,
    actual: object,
    severity: Severity,
    page_ref: int | None = None,
    evidence: dict[str, Any] | None = None,
) -> ComplianceFinding:
    definition = rule(rule_id)
    stable = json.dumps(
        {
            "rule_id": rule_id,
            "document_id": document_id,
            "field_name": field_name,
            "expected": str(expected),
            "actual": str(actual),
            "page_ref": page_ref,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    finding_id = f"finding-{hashlib.sha256(stable.encode()).hexdigest()[:24]}"
    return ComplianceFinding(
        finding_id=finding_id,
        rule_id=definition.rule_id,
        ucp_article=definition.ucp_article,
        document_id=document_id,
        field_name=field_name,
        page_ref=page_ref,
        expected=str(expected),
        actual=str(actual),
        severity=severity,
        evidence=evidence
        or {
            "provenance": "typed_extraction",
            "document_id": document_id,
            "field_name": field_name,
            "page_ref": page_ref,
        },
        rule_version=definition.version,
    )


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def check_string_consistency(
    expected: str | None,
    actual: str | None,
    *,
    document_id: str,
    field_name: str,
    rule_id: str = ART14D,
    page_ref: int | None = None,
) -> list[ComplianceFinding]:
    if expected is None or actual is None:
        return []
    left, right = _normalize(expected), _normalize(actual)
    if left == right:
        return []
    threshold = Decimal(decimal_parameter(ART14D, "fuzzy_advisory_threshold"))
    ratio = Decimal(str(SequenceMatcher(None, left, right).ratio()))
    severity = Severity.ADVISORY if ratio >= threshold else Severity.MATERIAL
    return [
        _finding(
            rule_id,
            document_id,
            field_name,
            expected,
            actual,
            severity,
            page_ref,
            {
                "provenance": "cross_document_comparison",
                "expected_value": expected,
                "actual_value": actual,
                "similarity": str(ratio),
                "page_ref": page_ref,
            },
        )
    ]


def check_numeric_consistency(
    expected: Decimal | None,
    actual: Decimal | None,
    *,
    document_id: str,
    field_name: str,
    page_ref: int | None = None,
) -> list[ComplianceFinding]:
    if expected is None or actual is None or expected == actual:
        return []
    return [
        _finding(ART14D, document_id, field_name, expected, actual, Severity.MATERIAL, page_ref)
    ]


def check_credit_amount_tolerance(
    credit_amount: Decimal,
    invoice_amount: Decimal,
    drawing_amount: Decimal,
    about_flag: bool,
    *,
    document_id: str = "commercial_invoice",
    page_ref: int | None = None,
) -> list[ComplianceFinding]:
    tolerance = Decimal(decimal_parameter(ART30A, "about_tolerance")) if about_flag else Decimal(0)
    lower = credit_amount * (Decimal(1) - tolerance)
    upper = credit_amount * (Decimal(1) + tolerance)
    findings: list[ComplianceFinding] = []
    if not lower <= invoice_amount <= upper:
        findings.append(
            _finding(
                ART30A,
                document_id,
                "invoice_amount",
                f"{lower}..{upper}",
                invoice_amount,
                Severity.MATERIAL,
                page_ref,
            )
        )
    if drawing_amount > upper:
        findings.append(
            _finding(
                ART30C,
                document_id,
                "drawing_amount",
                f"<= {upper}",
                drawing_amount,
                Severity.MATERIAL,
                page_ref,
            )
        )
    return findings


def check_quantity_tolerance(
    lc_quantity: Decimal,
    presented_quantity: Decimal,
    is_bulk_or_generic: bool,
    total_drawing_within_credit: bool,
    *,
    document_id: str = "commercial_invoice",
    page_ref: int | None = None,
) -> list[ComplianceFinding]:
    tolerance = (
        Decimal(decimal_parameter(ART30B, "bulk_tolerance"))
        if is_bulk_or_generic and total_drawing_within_credit
        else Decimal(0)
    )
    lower = lc_quantity * (Decimal(1) - tolerance)
    upper = lc_quantity * (Decimal(1) + tolerance)
    if lower <= presented_quantity <= upper:
        return []
    return [
        _finding(
            ART30B,
            document_id,
            "quantity",
            f"{lower}..{upper}",
            presented_quantity,
            Severity.MATERIAL,
            page_ref,
        )
    ]


def check_presentation_period(
    is_original_transport_document: bool,
    shipment_date: date,
    presentation_date: date,
    expiry_date: date,
    credit_specific_presentation_days: int | None,
    *,
    document_id: str = "bill_of_lading",
    page_ref: int | None = None,
) -> list[ComplianceFinding]:
    findings: list[ComplianceFinding] = []
    if is_original_transport_document:
        configured_default = int(decimal_parameter(ART14C, "default_transport_presentation_days"))
        allowed_days = credit_specific_presentation_days or configured_default
        elapsed = (presentation_date - shipment_date).days
        if elapsed > allowed_days:
            findings.append(
                _finding(
                    ART14C,
                    document_id,
                    "presentation_date",
                    f"within {allowed_days} days of shipment",
                    f"{elapsed} days",
                    Severity.MATERIAL,
                    page_ref,
                )
            )
    if presentation_date > expiry_date:
        findings.append(
            _finding(
                ART14C,
                document_id,
                "expiry_date",
                f"presentation on or before {expiry_date.isoformat()}",
                presentation_date.isoformat(),
                Severity.MATERIAL,
                page_ref,
            )
        )
    return findings


def check_commercial_invoice(
    lc: LCRequirements,
    invoice: CommercialInvoiceFields,
    *,
    drawing_amount: Decimal | None = None,
    document_id: str = "commercial_invoice",
) -> list[ComplianceFinding]:
    findings = check_string_consistency(
        lc.beneficiary,
        invoice.seller,
        document_id=document_id,
        field_name="seller",
        rule_id=ART18,
    )
    if lc.currency and invoice.currency and _normalize(lc.currency) != _normalize(invoice.currency):
        findings.append(
            _finding(
                ART18, document_id, "currency", lc.currency, invoice.currency, Severity.MATERIAL
            )
        )
    findings.extend(
        check_string_consistency(
            lc.goods_description,
            invoice.goods_description,
            document_id=document_id,
            field_name="goods_description",
            rule_id=ART18,
        )
    )
    if lc.credit_amount is not None and invoice.invoice_amount is not None:
        findings.extend(
            check_credit_amount_tolerance(
                lc.credit_amount,
                invoice.invoice_amount,
                drawing_amount if drawing_amount is not None else invoice.invoice_amount,
                lc.about_flag,
                document_id=document_id,
            )
        )
    return findings


def check_bill_of_lading(
    lc: LCRequirements,
    bl: BillOfLadingFields,
    *,
    document_id: str = "bill_of_lading",
) -> list[ComplianceFinding]:
    findings: list[ComplianceFinding] = []
    if bl.on_board_notation is False:
        findings.append(
            _finding(ART20, document_id, "on_board_notation", True, False, Severity.MATERIAL)
        )
    findings.extend(
        check_string_consistency(
            lc.loading_port,
            bl.loading_port,
            document_id=document_id,
            field_name="loading_port",
            rule_id=ART20,
        )
    )
    findings.extend(
        check_string_consistency(
            lc.discharge_port,
            bl.discharge_port,
            document_id=document_id,
            field_name="discharge_port",
            rule_id=ART20,
        )
    )
    shipment_date = bl.on_board_date or bl.bl_date
    if lc.latest_shipment_date and shipment_date and shipment_date > lc.latest_shipment_date:
        findings.append(
            _finding(
                ART20,
                document_id,
                "on_board_date",
                f"<= {lc.latest_shipment_date}",
                shipment_date,
                Severity.MATERIAL,
            )
        )
    if bl.carrier_or_master_signature is False:
        findings.append(
            _finding(
                ART20, document_id, "carrier_or_master_signature", True, False, Severity.MATERIAL
            )
        )
    return findings


def check_insurance(
    lc: LCRequirements,
    invoice: CommercialInvoiceFields,
    insurance: InsuranceCertificateFields,
    *,
    bill_of_lading: BillOfLadingFields | None = None,
    document_id: str = "insurance_certificate",
) -> list[ComplianceFinding]:
    findings: list[ComplianceFinding] = []
    ratio = Decimal(decimal_parameter(ART28, "minimum_coverage_ratio"))
    if invoice.invoice_amount is not None and insurance.insured_amount is not None:
        minimum = invoice.invoice_amount * ratio
        if insurance.insured_amount < minimum:
            findings.append(
                _finding(
                    ART28,
                    document_id,
                    "insured_amount",
                    f">= {minimum}",
                    insurance.insured_amount,
                    Severity.MATERIAL,
                )
            )
    if (
        lc.currency
        and insurance.currency
        and _normalize(lc.currency) != _normalize(insurance.currency)
    ):
        findings.append(
            _finding(
                ART28, document_id, "currency", lc.currency, insurance.currency, Severity.MATERIAL
            )
        )
    if bill_of_lading:
        shipment_date = bill_of_lading.on_board_date or bill_of_lading.bl_date
        if insurance.effective_date and shipment_date and insurance.effective_date > shipment_date:
            findings.append(
                _finding(
                    ART28,
                    document_id,
                    "effective_date",
                    f"<= {shipment_date}",
                    insurance.effective_date,
                    Severity.MATERIAL,
                )
            )
        for field_name in ("goods_description", "vessel_name", "loading_port", "discharge_port"):
            findings.extend(
                check_string_consistency(
                    getattr(bill_of_lading, field_name),
                    getattr(insurance, field_name),
                    document_id=document_id,
                    field_name=field_name,
                    rule_id=ART28,
                )
            )
    return findings


def check_partial_shipments(
    lc: LCRequirements,
    bl: BillOfLadingFields,
    *,
    document_id: str = "bill_of_lading",
) -> list[ComplianceFinding]:
    if not lc.partial_shipments_allowed and bl.partial_shipment_indicated is True:
        return [
            _finding(
                ART31, document_id, "partial_shipment_indicated", False, True, Severity.MATERIAL
            )
        ]
    return []
