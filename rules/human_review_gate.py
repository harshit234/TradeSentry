# rules/human_review_gate.py
# Pure Python. No LLM.
# This gate is NEVER bypassed. NEVER configurable at runtime.

from rules.risk_scoring import RiskBand

def should_require_human_review(
    risk_band: RiskBand,
    compliance_findings: list,
    cross_ibu_match_level: str,
    ebl_integrity_status: str = "NOT_APPLICABLE"
) -> tuple[bool, list[str]]:
    """
    Returns (requires_human_review: bool, reasons: list[str])

    TRIGGER 1: Risk band is HIGH (score >= 70)
    TRIGGER 2: Any MATERIAL compliance finding exists
    TRIGGER 3: Cross-IBU EXACT match
    TRIGGER 4: eBL document tampered (hash mismatch)

    HARD RULE: ANY single trigger = human review required.
    """
    reasons = []

    band_val = risk_band.value if hasattr(risk_band, "value") else str(risk_band)
    if band_val == "HIGH":
        reasons.append("Risk score in HIGH band (≥70)")

    material_findings = []
    for f in compliance_findings:
        sev = getattr(f, "severity", None) or (f.get("severity") if isinstance(f, dict) else None)
        sev_val = sev.value if hasattr(sev, "value") else str(sev)
        if sev_val == "MATERIAL":
            material_findings.append(f)

    if material_findings:
        rule_ids = [getattr(f, "rule_id", None) or f.get("rule_id") for f in material_findings]
        reasons.append(
            f"{len(material_findings)} MATERIAL compliance finding(s): {', '.join(str(r) for r in rule_ids)}"
        )

    if cross_ibu_match_level == "EXACT":
        reasons.append("Cross-IBU EXACT duplicate financing match")

    if ebl_integrity_status == "TAMPERED":
        reasons.append("eBL document tampered — hash mismatch detected")

    return (len(reasons) > 0, reasons)
