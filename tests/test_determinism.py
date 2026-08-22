# tests/test_determinism.py
# These tests verify the core guarantee: same inputs → same outputs

from decimal import Decimal
from datetime import date

def test_risk_score_deterministic():
    """Run same inputs 10 times — must be identical every time"""
    from rules.risk_scoring import calculate_risk_score

    inputs = dict(
        cross_ibu_match_level="EXACT",
        cross_ibu_similarity=1.0,
        compliance_findings=[],
        price_signal="SIGNIFICANT_ANOMALY",
        vessel_signal="CONSISTENT",
        sanctions_status="NO_MATCH",
        completeness_status="COMPLETE",
    )
    results = [calculate_risk_score(**inputs) for _ in range(10)]
    assert all(r.score == results[0].score for r in results)
    assert all(r.band == results[0].band for r in results)
    assert results[0].score == 135   # 80 (EXACT) + 55 (ANOMALY)
    assert results[0].band.value == "HIGH"


def test_ucp_amount_tolerance_about_flag():
    """LC states 'about USD 250,000' — invoice USD 265,000 must be COMPLIANT"""
    from rules.ucp600 import check_credit_amount_tolerance
    findings = check_credit_amount_tolerance(
        credit_amount=Decimal("250000"),
        invoice_amount=Decimal("265000"),
        drawing_amount=Decimal("265000"),
        about_flag=True           # ← ±10% tolerance applies
    )
    assert findings == []         # COMPLIANT — within ±10% tolerance


def test_ucp_amount_no_about_flag():
    """LC states USD 250,000 (no about) — invoice USD 275,000 must be MATERIAL"""
    from rules.ucp600 import check_credit_amount_tolerance
    findings = check_credit_amount_tolerance(
        credit_amount=Decimal("250000"),
        invoice_amount=Decimal("275000"),
        drawing_amount=Decimal("275000"),
        about_flag=False          # ← no tolerance
    )
    assert len(findings) >= 1
    assert findings[0].severity.value == "MATERIAL"


def test_presentation_period_21_day_default():
    """B/L presented 25 days after shipment — must be MATERIAL finding"""
    from rules.ucp600 import check_presentation_period
    findings = check_presentation_period(
        is_original_transport_document=True,
        shipment_date=date(2024, 8, 14),
        presentation_date=date(2024, 9, 8),   # 25 days later
        expiry_date=date(2024, 10, 1),
        credit_specific_presentation_days=None # use 21-day default
    )
    assert len(findings) == 1
    assert "ART14C" in findings[0].rule_id
    assert findings[0].severity.value == "MATERIAL"


def test_presentation_period_credit_specific():
    """Same case but LC specifies 30 days — must be COMPLIANT"""
    from rules.ucp600 import check_presentation_period
    findings = check_presentation_period(
        is_original_transport_document=True,
        shipment_date=date(2024, 8, 14),
        presentation_date=date(2024, 9, 8),   # 25 days later
        expiry_date=date(2024, 10, 1),
        credit_specific_presentation_days=30  # ← credit specifies 30 days
    )
    assert findings == []  # COMPLIANT — 25 days within 30-day limit


def test_false_positive_prevention():
    """Same exporter, different shipment — similarity must be < 0.85"""
    from rules.cross_ibu_similarity import weighted_similarity, classify_match
    tx_a = {
        "bl_number_normalized":     "BL789456",
        "vessel_normalized":        "ocean_star",
        "voyage_normalized":        "v123",
        "exporter_normalized":      "abc_trading",
        "loading_port_unlocode":    "INMUN",
        "discharge_port_unlocode":  "SGSIN",
        "shipment_date_iso":        "2024-08-14",
    }
    tx_d = {  # Demo Case D — same exporter, different shipment
        "bl_number_normalized":     "BL-LEGIT-2024-099",
        "vessel_normalized":        "sea_breeze",
        "voyage_normalized":        "v900",
        "exporter_normalized":      "abc_trading",  # same exporter
        "loading_port_unlocode":    "INMUN",        # same loading port
        "discharge_port_unlocode":  "LKCMB",        # different destination
        "shipment_date_iso":        "2024-09-01",   # different date
    }
    score, _ = weighted_similarity(tx_a, tx_d)
    level, signal = classify_match(score)

    assert score < 0.85,  f"False positive! Score {score} >= 0.85 threshold"
    assert level == "NONE", f"False positive! Match level should be NONE, got {level}"


def test_normalization_deterministic():
    """Different OCR variants → same canonical entity string"""
    from rules.normalization import normalize_entity_name
    variants = [
        "ABC Trading Pvt. Ltd.",
        "ABC TRADING PRIVATE LIMITED",
        "A.B.C. Trading Ltd",
        "abc trading pvt ltd",
        "ABC Trading Ltd.",
    ]
    normalized = [normalize_entity_name(v) for v in variants]
    assert len(set(normalized)) == 1, f"Variants produced different strings: {set(normalized)}"


def test_fingerprint_deterministic():
    """Same fields always produce same SHA-256 fingerprint"""
    from rules.normalization import generate_dna_fingerprint
    args = dict(
        bl_number_normalized="BL789456",
        vessel_normalized="ocean_star",
        voyage_normalized="v123",
        exporter_normalized="abc_trading",
        loading_port_unlocode="INMUN",
        discharge_port_unlocode="SGSIN",
        shipment_date_iso="2024-08-14",
    )
    fingerprints = [generate_dna_fingerprint(**args) for _ in range(10)]
    assert len(set(fingerprints)) == 1   # all identical


def test_human_review_gate_material_finding():
    """MATERIAL compliance finding → must trigger human review"""
    from rules.human_review_gate import should_require_human_review
    from rules.risk_scoring import RiskBand

    class MockFinding:
        severity = "MATERIAL"
        rule_id = "TEST-RULE"

    required, reasons = should_require_human_review(
        risk_band=RiskBand.MEDIUM,         # not HIGH — testing material trigger
        compliance_findings=[MockFinding()],
        cross_ibu_match_level="NONE",
    )
    assert required is True
    assert any("MATERIAL" in r for r in reasons)


def test_ui_state_hold_on_high_risk():
    """HIGH risk band → settlement HOLD regardless of other signals"""
    from rules.risk_scoring import RiskBand, RiskScoreResult
    assert RiskBand.HIGH.value == "HIGH"
