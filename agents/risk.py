from __future__ import annotations

from models.compliance import Severity
from models.cross_ibu import MatchLevel
from models.fraud_tbml import PriceSignal, SanctionsMatchStatus, VesselVerificationStatus
from models.investigation import InvestigationState, RiskBand


def deterministic_risk_score(state: InvestigationState) -> tuple[int, RiskBand]:
    score = 0
    for match in state.cross_ibu_matches:
        if match.match_level is MatchLevel.EXACT:
            score += 80
        elif match.match_level is MatchLevel.NEAR and match.similarity_score >= 0.85:
            score += 45
    if state.compliance_result is not None:
        material_count = sum(
            finding.severity is Severity.MATERIAL
            for finding in state.compliance_result.findings
        )
        score += min(material_count * 40, 60)
        score += sum(
            10
            for finding in state.compliance_result.findings
            if finding.severity is Severity.POTENTIALLY_WAIVABLE
        )
    if state.price_benchmark is not None:
        if state.price_benchmark.signal is PriceSignal.SIGNIFICANT_ANOMALY:
            score += 55
        elif state.price_benchmark.signal is PriceSignal.REVIEW:
            score += 20
    if (
        state.vessel_verification is not None
        and state.vessel_verification.verification_result is VesselVerificationStatus.ANOMALY
    ):
        score += 30
    if state.sanctions_result is not None:
        for entity in state.sanctions_result.screened_entities:
            if entity.match_status is SanctionsMatchStatus.POSSIBLE_MATCH:
                score += 35
            elif entity.match_status is SanctionsMatchStatus.CONFIRMED_SOURCE_MATCH:
                score += 90
    if state.completeness is not None and state.completeness.status.value == "INCOMPLETE":
        score += 25
    band = RiskBand.LOW if score <= 29 else RiskBand.MEDIUM if score <= 69 else RiskBand.HIGH
    return score, band

