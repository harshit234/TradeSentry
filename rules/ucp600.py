try:
    from rapidfuzz import fuzz
except ImportError:
    import difflib
    class FuzzFallback:
        @staticmethod
        def token_sort_ratio(s1: str, s2: str) -> float:
            t1 = " ".join(sorted(str(s1).split()))
            t2 = " ".join(sorted(str(s2).split()))
            return difflib.SequenceMatcher(None, t1, t2).ratio() * 100.0
    fuzz = FuzzFallback()

from decimal import Decimal
from datetime import date
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class Severity(str, Enum):
    MATERIAL           = "MATERIAL"           # likely justifies refusal
    REVIEW             = "REVIEW"             # officer attention needed
    POTENTIALLY_WAIVABLE = "POTENTIALLY_WAIVABLE"  # minor, may be waived
    ADVISORY           = "ADVISORY"           # informational only

    # NEVER use the word "FATAL" anywhere in this codebase

@dataclass
class ComplianceFinding:
    rule_id:     str
    ucp_article: str
    field_name:  str
    expected:    str
    actual:      str
    severity:    Severity
    evidence:    dict
    rule_version: str = "UCP600-2007"

# ─────────────────────────────────────────────
# RULE 1: Art. 30(a) — Credit Amount Tolerance
# ─────────────────────────────────────────────
def check_credit_amount_tolerance(
    credit_amount: Decimal,
    invoice_amount: Decimal,
    drawing_amount: Decimal,
    about_flag: bool
) -> list[ComplianceFinding]:
    """
    Art. 30(a): When credit states "about" or "approximately",
                tolerance is ±10% on credit amount.
    Art. 30(c): Drawing amount MUST NOT exceed credit amount
                regardless of about_flag.
    Art. 18:    Invoice amount is separate from drawing amount.

    HARD RULE: Never implement invoice_amount != credit_amount as discrepancy.
               Always check against the tolerance band first.
    """
    findings = []
    tolerance = Decimal("0.10") if about_flag else Decimal("0.00")
    lower = credit_amount * (1 - tolerance)
    upper = credit_amount * (1 + tolerance)

    # Check invoice amount against tolerance band
    if not (lower <= invoice_amount <= upper):
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART30A-AMOUNT-TOLERANCE",
            ucp_article="UCP 600 Art. 30(a) / Art. 18",
            field_name="invoice_amount",
            expected=f"Between {lower} and {upper} (tolerance: {'±10%' if about_flag else '0%'})",
            actual=str(invoice_amount),
            severity=Severity.MATERIAL,
            evidence={
                "credit_amount": str(credit_amount),
                "about_flag": about_flag,
                "tolerance_pct": "10%" if about_flag else "0%",
                "lower_bound": str(lower),
                "upper_bound": str(upper),
            }
        ))

    # Drawing amount must not exceed upper allowable credit limit (Art. 30c)
    if drawing_amount > upper:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART30C-DRAWING-EXCEEDS",
            ucp_article="UCP 600 Art. 30(c)",
            field_name="drawing_amount",
            expected=f"<= {upper}",
            actual=str(drawing_amount),
            severity=Severity.MATERIAL,
            evidence={
                "credit_amount": str(credit_amount),
                "drawing_amount": str(drawing_amount),
                "upper_limit": str(upper),
                "excess": str(drawing_amount - upper),
            }
        ))

    return findings


# ─────────────────────────────────────────────
# RULE 2: Art. 30(b) — Quantity Tolerance
# ─────────────────────────────────────────────
def check_quantity_tolerance(
    lc_quantity: Decimal,
    presented_quantity: Decimal,
    is_bulk_or_generic: bool,
    total_drawing_within_credit: bool
) -> list[ComplianceFinding]:
    """
    Art. 30(b): ±5% quantity tolerance applies ONLY when:
      1. Goods are NOT stated in packaging units or individual pieces
         (i.e. bulk commodity like rice, wheat, oil — measured in MT/KG/L)
      2. Total drawing amount does not exceed credit amount

    HARD RULE: Never apply 5% tolerance to goods stated in pieces/units.
    """
    findings = []

    if not is_bulk_or_generic:
        # Tolerance does NOT apply — exact quantity required
        if presented_quantity != lc_quantity:
            findings.append(ComplianceFinding(
                rule_id="UCP600-ART30B-QUANTITY-EXACT",
                ucp_article="UCP 600 Art. 30(b)",
                field_name="quantity",
                expected=f"Exactly {lc_quantity} (packaged goods — no tolerance)",
                actual=str(presented_quantity),
                severity=Severity.MATERIAL,
                evidence={"lc_quantity": str(lc_quantity),
                          "presented": str(presented_quantity),
                          "is_bulk": False}
            ))
        return findings

    # Bulk goods — apply ±5% tolerance
    lower = lc_quantity * Decimal("0.95")
    upper = lc_quantity * Decimal("1.05")

    if not (lower <= presented_quantity <= upper):
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART30B-QUANTITY-TOLERANCE",
            ucp_article="UCP 600 Art. 30(b)",
            field_name="quantity",
            expected=f"Between {lower} and {upper} (±5% bulk tolerance)",
            actual=str(presented_quantity),
            severity=Severity.MATERIAL,
            evidence={
                "lc_quantity": str(lc_quantity),
                "presented": str(presented_quantity),
                "tolerance": "±5%",
                "lower": str(lower),
                "upper": str(upper),
            }
        ))

    if not total_drawing_within_credit:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART30B-DRAWING-EXCEEDS",
            ucp_article="UCP 600 Art. 30(b)",
            field_name="drawing_amount",
            expected="Drawing must not exceed credit amount",
            actual="Drawing exceeds credit amount",
            severity=Severity.MATERIAL,
            evidence={"note": "Art 30(b) quantity tolerance invalidated"}
        ))

    return findings


# ─────────────────────────────────────────────
# RULE 3: Art. 14(c) — Presentation Period
# ─────────────────────────────────────────────
def check_presentation_period(
    is_original_transport_document: bool,
    shipment_date: date,
    presentation_date: date,
    expiry_date: date,
    credit_specific_presentation_days: Optional[int] = None
) -> list[ComplianceFinding]:
    """
    Art. 14(c): 21-day default applies ONLY to original transport
                documents under Arts. 19–25.
                If credit specifies a different period, use that instead.
                Presentation must ALSO be within credit expiry.

    TWO INDEPENDENT CHECKS:
      1. Days since shipment <= presentation limit
      2. Presentation date <= expiry date

    HARD RULE: Both checks run independently.
               Failing expiry does NOT skip the period check.
               Both findings are recorded if both fail.
    """
    findings = []

    if not is_original_transport_document:
        # Art. 14(c) only applies to original transport documents
        # Non-transport documents have no 21-day rule
        return findings

    limit_days = credit_specific_presentation_days \
                 if credit_specific_presentation_days is not None \
                 else 21

    days_elapsed = (presentation_date - shipment_date).days

    # Check 1: Presentation period
    if days_elapsed > limit_days:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART14C-PRESENTATION-PERIOD",
            ucp_article="UCP 600 Art. 14(c)",
            field_name="presentation_date",
            expected=f"Within {limit_days} days of shipment date "
                     f"({'credit-specific' if credit_specific_presentation_days else '21-day default'})",
            actual=f"{days_elapsed} days after shipment",
            severity=Severity.MATERIAL,
            evidence={
                "shipment_date": str(shipment_date),
                "presentation_date": str(presentation_date),
                "days_elapsed": days_elapsed,
                "limit_days": limit_days,
                "credit_specific": credit_specific_presentation_days is not None,
            }
        ))

    # Check 2: Expiry date (independent check)
    if presentation_date > expiry_date:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART14C-EXPIRY",
            ucp_article="UCP 600 Art. 14(c) / Art. 6",
            field_name="presentation_date",
            expected=f"On or before expiry date {expiry_date}",
            actual=f"Presented {presentation_date} — after expiry",
            severity=Severity.MATERIAL,
            evidence={
                "presentation_date": str(presentation_date),
                "expiry_date": str(expiry_date),
                "days_overdue": (presentation_date - expiry_date).days,
            }
        ))

    return findings


# ─────────────────────────────────────────────
# RULE 4: Art. 18 — Commercial Invoice
# ─────────────────────────────────────────────
def check_commercial_invoice(
    lc_beneficiary: str,
    lc_applicant: str,
    lc_currency: str,
    lc_goods_description: str,
    invoice_seller: str,
    invoice_buyer: str,
    invoice_currency: str,
    invoice_goods_description: str,
    invoice_amount: Decimal,
    credit_amount: Decimal,
    about_flag: bool,
    fuzzy_threshold: float = 0.85   # configurable, not magic number
) -> list[ComplianceFinding]:
    """
    Art. 18(a)(i):  Invoice issued by beneficiary (seller = LC beneficiary)
    Art. 18(a)(ii): Made out in name of applicant (buyer = LC applicant)
    Art. 18(a)(iv): In same currency as credit
    Art. 18(c):     Goods description must not conflict with LC description
    Art. 30:        Amount delegated to check_credit_amount_tolerance
    """
    findings = []
    from rapidfuzz import fuzz

    # Seller must match LC beneficiary
    seller_similarity = fuzz.token_sort_ratio(
        invoice_seller.lower(), lc_beneficiary.lower()
    ) / 100
    if seller_similarity < fuzzy_threshold:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART18A-SELLER-MISMATCH",
            ucp_article="UCP 600 Art. 18(a)(i)",
            field_name="invoice_seller",
            expected=f"Invoice issued by beneficiary: {lc_beneficiary}",
            actual=f"Invoice seller: {invoice_seller} (similarity: {seller_similarity:.0%})",
            severity=Severity.MATERIAL if seller_similarity < 0.70 else Severity.REVIEW,
            evidence={"lc_beneficiary": lc_beneficiary,
                      "invoice_seller": invoice_seller,
                      "similarity": seller_similarity}
        ))

    # Buyer must match LC applicant
    buyer_similarity = fuzz.token_sort_ratio(
        invoice_buyer.lower(), lc_applicant.lower()
    ) / 100
    if buyer_similarity < fuzzy_threshold:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART18A-BUYER-MISMATCH",
            ucp_article="UCP 600 Art. 18(a)(ii)",
            field_name="invoice_buyer",
            expected=f"Made out in name of applicant: {lc_applicant}",
            actual=f"Invoice buyer: {invoice_buyer} (similarity: {buyer_similarity:.0%})",
            severity=Severity.MATERIAL if buyer_similarity < 0.70 else Severity.REVIEW,
            evidence={"lc_applicant": lc_applicant,
                      "invoice_buyer": invoice_buyer,
                      "similarity": buyer_similarity}
        ))

    # Currency must match
    if invoice_currency.upper() != lc_currency.upper():
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART18A-CURRENCY-MISMATCH",
            ucp_article="UCP 600 Art. 18(a)(iv)",
            field_name="invoice_currency",
            expected=f"Currency: {lc_currency}",
            actual=f"Currency: {invoice_currency}",
            severity=Severity.MATERIAL,
            evidence={"lc_currency": lc_currency, "invoice_currency": invoice_currency}
        ))

    # Goods description must not conflict
    desc_similarity = fuzz.token_sort_ratio(
        invoice_goods_description.lower(), lc_goods_description.lower()
    ) / 100
    if desc_similarity < 0.50:   # Very different — likely different goods
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART18C-GOODS-CONFLICT",
            ucp_article="UCP 600 Art. 18(c)",
            field_name="goods_description",
            expected=f"Consistent with LC: {lc_goods_description}",
            actual=f"Invoice states: {invoice_goods_description}",
            severity=Severity.MATERIAL,
            evidence={"lc_description": lc_goods_description,
                      "invoice_description": invoice_goods_description,
                      "similarity": desc_similarity}
        ))
    elif desc_similarity < 0.75:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART18C-GOODS-VARIATION",
            ucp_article="UCP 600 Art. 18(c)",
            field_name="goods_description",
            expected=f"Consistent with LC: {lc_goods_description}",
            actual=f"Invoice states: {invoice_goods_description}",
            severity=Severity.ADVISORY,
            evidence={"similarity": desc_similarity,
                      "note": "Minor variation — may be acceptable specificity"}
        ))

    return findings


# ─────────────────────────────────────────────
# RULE 5: Art. 20 — Bill of Lading
# ─────────────────────────────────────────────
def check_bill_of_lading(
    lc_loading_port: str,
    lc_discharge_port: str,
    lc_latest_shipment_date: date,
    bl_loading_port: str,
    bl_discharge_port: str,
    bl_on_board_notation: bool,
    bl_on_board_date: date,
    bl_carrier_signature: bool,
    bl_shipper: str,
    lc_beneficiary: str,
    fuzzy_threshold: float = 0.85
) -> list[ComplianceFinding]:
    """
    Art. 20(a)(i):   Must indicate name of carrier
    Art. 20(a)(ii):  Must indicate on-board notation
    Art. 20(a)(iii): Port of loading must match LC
    Art. 20(a)(iv):  Port of discharge must match LC
    Art. 20(a)(vi):  Must be the sole original (or indicate full set)
    Custom:          Shipment date must be within latest_shipment_date
    """
    findings = []
    from rapidfuzz import fuzz

    # On-board notation required (Art. 20(a)(ii))
    if not bl_on_board_notation:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART20A-ONBOARD-MISSING",
            ucp_article="UCP 600 Art. 20(a)(ii)",
            field_name="on_board_notation",
            expected="On-board notation present on B/L",
            actual="No on-board notation found",
            severity=Severity.MATERIAL,
            evidence={"on_board_notation": False}
        ))

    # Carrier signature required (Art. 20(a)(i))
    if not bl_carrier_signature:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART20A-CARRIER-SIG-MISSING",
            ucp_article="UCP 600 Art. 20(a)(i)",
            field_name="carrier_signature",
            expected="Carrier/master/agent signature present",
            actual="No carrier signature found",
            severity=Severity.MATERIAL,
            evidence={"carrier_signature": False}
        ))

    # Loading port must match LC
    port_load_sim = fuzz.token_sort_ratio(
        bl_loading_port.lower(), lc_loading_port.lower()
    ) / 100
    if port_load_sim < fuzzy_threshold:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART20A-LOADING-PORT-MISMATCH",
            ucp_article="UCP 600 Art. 20(a)(iii)",
            field_name="loading_port",
            expected=f"Port of loading: {lc_loading_port}",
            actual=f"B/L states: {bl_loading_port}",
            severity=Severity.MATERIAL,
            evidence={"lc_port": lc_loading_port,
                      "bl_port": bl_loading_port,
                      "similarity": port_load_sim}
        ))

    # Discharge port must match LC
    port_disc_sim = fuzz.token_sort_ratio(
        bl_discharge_port.lower(), lc_discharge_port.lower()
    ) / 100
    if port_disc_sim < fuzzy_threshold:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART20A-DISCHARGE-PORT-MISMATCH",
            ucp_article="UCP 600 Art. 20(a)(iv)",
            field_name="discharge_port",
            expected=f"Port of discharge: {lc_discharge_port}",
            actual=f"B/L states: {bl_discharge_port}",
            severity=Severity.MATERIAL,
            evidence={"lc_port": lc_discharge_port,
                      "bl_port": bl_discharge_port,
                      "similarity": port_disc_sim}
        ))

    # Shipment date within latest_shipment_date
    if bl_on_board_date > lc_latest_shipment_date:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART20A-LATE-SHIPMENT",
            ucp_article="UCP 600 Art. 20(a) / Art. 14(c)",
            field_name="on_board_date",
            expected=f"Shipped on or before {lc_latest_shipment_date}",
            actual=f"On-board date: {bl_on_board_date}",
            severity=Severity.MATERIAL,
            evidence={
                "on_board_date": str(bl_on_board_date),
                "latest_shipment_date": str(lc_latest_shipment_date),
                "days_late": (bl_on_board_date - lc_latest_shipment_date).days
            }
        ))

    return findings


# ─────────────────────────────────────────────
# RULE 6: Art. 28 — Insurance
# ─────────────────────────────────────────────
def check_insurance(
    lc_currency: str,
    invoice_amount: Decimal,
    invoice_incoterms: str,
    insured_amount: Decimal,
    insurance_currency: str,
    insurance_effective_date: date,
    bl_on_board_date: date,
    insurance_coverage_type: str,
    lc_required_coverage_type: Optional[str] = None,
    cif_percentage: Decimal = Decimal("1.10")   # 110% default, LC may specify more
) -> list[ComplianceFinding]:
    """
    Art. 28(f)(i):  Minimum coverage = 110% of CIF value
                    (or invoice amount if CIF/CIP Incoterms)
    Art. 28(f)(ii): Currency must match credit
    Art. 28(e):     Effective date must be no later than B/L on-board date
    Art. 28(c):     Coverage type must match LC requirement if specified
    """
    findings = []

    cif_value = invoice_amount
    minimum_coverage = cif_value * cif_percentage

    # Coverage amount check
    if insured_amount < minimum_coverage:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART28F-INSURANCE-AMOUNT",
            ucp_article="UCP 600 Art. 28(f)(i)",
            field_name="insured_amount",
            expected=f">= {minimum_coverage} ({cif_percentage*100:.0f}% of CIF value {cif_value})",
            actual=str(insured_amount),
            severity=Severity.MATERIAL,
            evidence={
                "invoice_amount": str(invoice_amount),
                "minimum_coverage": str(minimum_coverage),
                "actual_coverage": str(insured_amount),
                "shortfall": str(minimum_coverage - insured_amount),
                "percentage": f"{cif_percentage*100:.0f}%"
            }
        ))

    # Currency check
    if insurance_currency.upper() != lc_currency.upper():
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART28F-INSURANCE-CURRENCY",
            ucp_article="UCP 600 Art. 28(f)(ii)",
            field_name="insurance_currency",
            expected=f"Currency: {lc_currency}",
            actual=f"Currency: {insurance_currency}",
            severity=Severity.MATERIAL,
            evidence={"lc_currency": lc_currency,
                      "insurance_currency": insurance_currency}
        ))

    # Effective date must be on or before on-board date
    if insurance_effective_date > bl_on_board_date:
        findings.append(ComplianceFinding(
            rule_id="UCP600-ART28E-INSURANCE-DATE",
            ucp_article="UCP 600 Art. 28(e)",
            field_name="insurance_effective_date",
            expected=f"Effective on or before on-board date {bl_on_board_date}",
            actual=f"Insurance effective: {insurance_effective_date}",
            severity=Severity.MATERIAL,
            evidence={
                "effective_date": str(insurance_effective_date),
                "on_board_date": str(bl_on_board_date),
                "days_late": (insurance_effective_date - bl_on_board_date).days
            }
        ))

    # Coverage type check
    if lc_required_coverage_type:
        if lc_required_coverage_type.lower() not in insurance_coverage_type.lower():
            findings.append(ComplianceFinding(
                rule_id="UCP600-ART28C-COVERAGE-TYPE",
                ucp_article="UCP 600 Art. 28(c)",
                field_name="coverage_type",
                expected=f"Coverage type: {lc_required_coverage_type}",
                actual=f"Coverage type: {insurance_coverage_type}",
                severity=Severity.REVIEW,
                evidence={"required": lc_required_coverage_type,
                          "actual": insurance_coverage_type}
            ))

    return findings


# ─────────────────────────────────────────────
# RULE 7: eBL Digital Signature Check
# ─────────────────────────────────────────────
def check_ebl_digital_signature(
    is_ebl: bool,
    has_valid_pki_signature: Optional[bool],
    ca_is_recognized: Optional[bool],
    document_integrity_valid: Optional[bool],
    signature_timestamp: Optional[date],
    bl_on_board_date: Optional[date]
) -> list[ComplianceFinding]:
    """
    India Bills of Lading Act 2025 (effective July 2025):
    eBLs with PKI-based digital signatures legally equivalent to paper.
    """
    findings = []

    if not is_ebl:
        return findings

    # eBL — digital signature required
    if has_valid_pki_signature is False:
        findings.append(ComplianceFinding(
            rule_id="EBL-SIG-001-NO-VALID-SIG",
            ucp_article="India Bills of Lading Act 2025 / UNCITRAL MLETR",
            field_name="digital_signature",
            expected="Valid PKI digital signature from recognized CA",
            actual="No valid digital signature found",
            severity=Severity.MATERIAL,
            evidence={"is_ebl": True, "has_valid_pki": False}
        ))
        return findings

    if ca_is_recognized is False:
        findings.append(ComplianceFinding(
            rule_id="EBL-SIG-002-UNRECOGNIZED-CA",
            ucp_article="India Bills of Lading Act 2025 / CCA India",
            field_name="digital_signature",
            expected="Certificate issued by CCA India recognized CA",
            actual="Certificate authority not in recognized CA list",
            severity=Severity.MATERIAL,
            evidence={"ca_recognized": False}
        ))

    if document_integrity_valid is False:
        findings.append(ComplianceFinding(
            rule_id="EBL-SIG-003-TAMPERED",
            ucp_article="India Bills of Lading Act 2025 — Document Integrity",
            field_name="document_integrity",
            expected="Document hash matches signed hash (not tampered)",
            actual="Document hash MISMATCH — document modified after signing",
            severity=Severity.MATERIAL,
            evidence={"integrity_check": "FAILED",
                      "note": "Document content was modified after PKI signature was applied"}
        ))

    # Timestamp consistency check
    if signature_timestamp and bl_on_board_date:
        if signature_timestamp.date() < bl_on_board_date:
            findings.append(ComplianceFinding(
                rule_id="EBL-SIG-004-TIMESTAMP-ANOMALY",
                ucp_article="India Bills of Lading Act 2025 — Temporal Integrity",
                field_name="signature_timestamp",
                expected=f"Signature on or after on-board date {bl_on_board_date}",
                actual=f"Signed {signature_timestamp.date()} — before on-board date",
                severity=Severity.MATERIAL,
                evidence={
                    "signature_timestamp": str(signature_timestamp),
                    "on_board_date": str(bl_on_board_date),
                    "note": "Document signed before goods were loaded — impossible"
                }
            ))

    return findings


# ─────────────────────────────────────────────
# RULE 8: Art. 14(d) — Cross-Document Consistency
# ─────────────────────────────────────────────
def check_cross_document_consistency(
    fields: dict[str, dict[str, str]],
    fuzzy_threshold_material: float = 0.70,
    fuzzy_threshold_advisory: float = 0.85
) -> list[ComplianceFinding]:
    """
    Art. 14(d): Data in documents need not be identical to data
                in the credit but must not conflict.
    """
    from rapidfuzz import fuzz
    findings = []

    for field_name, doc_values in fields.items():
        docs = list(doc_values.keys())
        values = list(doc_values.values())

        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                sim = fuzz.token_sort_ratio(
                    values[i].lower(), values[j].lower()
                ) / 100

                if sim >= 1.0:
                    continue

                if sim < fuzzy_threshold_material:
                    severity = Severity.MATERIAL
                elif sim < fuzzy_threshold_advisory:
                    severity = Severity.REVIEW
                else:
                    severity = Severity.ADVISORY

                findings.append(ComplianceFinding(
                    rule_id=f"UCP600-ART14D-{field_name.upper()}-INCONSISTENCY",
                    ucp_article="UCP 600 Art. 14(d)",
                    field_name=field_name,
                    expected=f"{docs[i]}: {values[i]}",
                    actual=f"{docs[j]}: {values[j]} (similarity: {sim:.0%})",
                    severity=severity,
                    evidence={
                        "field": field_name,
                        "doc_a": docs[i], "value_a": values[i],
                        "doc_b": docs[j], "value_b": values[j],
                        "similarity": sim,
                        "note": "OCR variant" if sim >= fuzzy_threshold_advisory else "Possible conflict"
                    }
                ))

    return findings
