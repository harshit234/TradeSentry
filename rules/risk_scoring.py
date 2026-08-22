# rules/risk_scoring.py
# Pure Python. No LLM. No randomness.
# SAME INPUTS → SAME SCORE → ALWAYS.

from dataclasses import dataclass
from enum import Enum

class RiskBand(str, Enum):
    LOW    = "LOW"    # 0–29
    MEDIUM = "MEDIUM" # 30–69
    HIGH   = "HIGH"   # 70+

SCORE_WEIGHTS = {
    # Cross-IBU signals
    "cross_ibu_exact_match":          80,
    "cross_ibu_near_match_above_95":  45,
    "cross_ibu_near_match_85_to_95":  30,

    # UCP 600 compliance
    "compliance_material_per_finding": 40,   # applied per finding, see cap below
    "compliance_material_cap":         60,   # maximum from compliance findings
    "compliance_review":               15,   # per finding
    "compliance_review_cap":           30,
    "compliance_waivable":             10,
    "compliance_waivable_cap":         10,

    # TBML signals
    "price_significant_anomaly":       55,
    "price_review_signal":             20,
    "vessel_anomaly":                  30,
    "vessel_data_unavailable":          5,

    # Sanctions
    "sanctions_confirmed_match":       90,
    "sanctions_possible_match":        35,

    # Document completeness
    "completeness_incomplete":         25,

    # eBL Digital signature
    "ebl_tampered_document":           70,
    "ebl_invalid_signature":           50,
    "ebl_unrecognized_ca":             40,
}

BAND_THRESHOLDS = {
    RiskBand.LOW:    (0,  29),
    RiskBand.MEDIUM: (30, 69),
    RiskBand.HIGH:   (70, 999),
}

@dataclass
class RiskScoreResult:
    score: int
    band: RiskBand
    breakdown: dict[str, int]
    weights_note: str = (
        "⚠ Prototype demo weights — not calibrated for production use. "
        "Production requires statistical validation against labeled outcomes."
    )

def calculate_risk_score(
    cross_ibu_match_level: str,
    cross_ibu_similarity: float,
    compliance_findings: list,
    price_signal: str,
    vessel_signal: str,
    sanctions_status: str,
    completeness_status: str,
    ebl_integrity_status: str = "NOT_APPLICABLE"
) -> RiskScoreResult:
    score = 0
    breakdown = {}

    # ── Cross-IBU ──────────────────────────────────────────────────
    if cross_ibu_match_level == "EXACT":
        pts = SCORE_WEIGHTS["cross_ibu_exact_match"]
        score += pts
        breakdown["Cross-IBU EXACT match"] = pts

    elif cross_ibu_match_level == "NEAR":
        if cross_ibu_similarity >= 0.95:
            pts = SCORE_WEIGHTS["cross_ibu_near_match_above_95"]
        else:
            pts = SCORE_WEIGHTS["cross_ibu_near_match_85_to_95"]
        score += pts
        breakdown[f"Cross-IBU NEAR match (similarity {cross_ibu_similarity:.0%})"] = pts

    # ── UCP 600 Compliance ─────────────────────────────────────────
    material_points   = 0
    review_points     = 0
    waivable_points   = 0

    for finding in compliance_findings:
        sev = getattr(finding, "severity", None) or finding.get("severity") if isinstance(finding, dict) else finding.severity
        sev_val = sev.value if hasattr(sev, "value") else str(sev)
        if sev_val == "MATERIAL":
            material_points += SCORE_WEIGHTS["compliance_material_per_finding"]
        elif sev_val == "REVIEW":
            review_points += SCORE_WEIGHTS["compliance_review"]
        elif sev_val == "POTENTIALLY_WAIVABLE":
            waivable_points += SCORE_WEIGHTS["compliance_waivable"]

    # Apply caps
    material_points = min(material_points, SCORE_WEIGHTS["compliance_material_cap"])
    review_points   = min(review_points,   SCORE_WEIGHTS["compliance_review_cap"])
    waivable_points = min(waivable_points, SCORE_WEIGHTS["compliance_waivable_cap"])

    if material_points:
        score += material_points
        breakdown[f"UCP MATERIAL findings (capped at {SCORE_WEIGHTS['compliance_material_cap']})"] = material_points
    if review_points:
        score += review_points
        breakdown["UCP REVIEW findings"] = review_points
    if waivable_points:
        score += waivable_points
        breakdown["UCP WAIVABLE findings"] = waivable_points

    # ── Price Benchmark ────────────────────────────────────────────
    if price_signal == "SIGNIFICANT_ANOMALY":
        pts = SCORE_WEIGHTS["price_significant_anomaly"]
        score += pts
        breakdown["Price SIGNIFICANT_ANOMALY"] = pts
    elif price_signal == "REVIEW":
        pts = SCORE_WEIGHTS["price_review_signal"]
        score += pts
        breakdown["Price REVIEW signal"] = pts

    # ── Vessel Verification ────────────────────────────────────────
    if vessel_signal == "ANOMALY":
        pts = SCORE_WEIGHTS["vessel_anomaly"]
        score += pts
        breakdown["Vessel position ANOMALY"] = pts
    elif vessel_signal == "DATA_UNAVAILABLE":
        pts = SCORE_WEIGHTS["vessel_data_unavailable"]
        score += pts
        breakdown["Vessel data unavailable"] = pts

    # ── Sanctions ─────────────────────────────────────────────────
    if sanctions_status == "CONFIRMED_SOURCE_MATCH":
        pts = SCORE_WEIGHTS["sanctions_confirmed_match"]
        score += pts
        breakdown["Sanctions CONFIRMED match"] = pts
    elif sanctions_status == "POSSIBLE_MATCH":
        pts = SCORE_WEIGHTS["sanctions_possible_match"]
        score += pts
        breakdown["Sanctions POSSIBLE_MATCH"] = pts

    # ── Completeness ───────────────────────────────────────────────
    if completeness_status == "INCOMPLETE":
        pts = SCORE_WEIGHTS["completeness_incomplete"]
        score += pts
        breakdown["Document completeness INCOMPLETE"] = pts

    # ── eBL Digital Signature ──────────────────────────────────────
    if ebl_integrity_status == "TAMPERED":
        pts = SCORE_WEIGHTS["ebl_tampered_document"]
        score += pts
        breakdown["eBL document TAMPERED (hash mismatch)"] = pts
    elif ebl_integrity_status == "INVALID":
        pts = SCORE_WEIGHTS["ebl_invalid_signature"]
        score += pts
        breakdown["eBL invalid digital signature"] = pts

    # ── Determine Band ─────────────────────────────────────────────
    band = RiskBand.HIGH if score >= 70 else \
           RiskBand.MEDIUM if score >= 30 else \
           RiskBand.LOW

    return RiskScoreResult(score=score, band=band, breakdown=breakdown)
