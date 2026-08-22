# rules/ui_state.py
# Pure Python deterministic UI state calculation

from typing import Optional
from pydantic import BaseModel
from rules.completeness import DocumentCompletenessResult, CompletenessStatus
from rules.ucp600 import ComplianceFinding
from rules.risk_scoring import RiskScoreResult, RiskBand

class UIState(BaseModel):
    risk_badge_color:     str
    risk_badge_label:     str
    risk_badge_icon:      str

    settlement_status:    str
    settlement_color:     str
    settlement_message:   str
    settlement_sub_note:  str

    run_button_enabled:   bool
    run_button_reason:    str

    decision_panel_active: bool

    ucp_section_badge:    str
    cross_ibu_badge:      str
    tbml_badge:           str

    prototype_disclaimer: str   = (
        "⚠ Prototype demo weights — not calibrated for production"
    )
    signal_disclaimer:    str   = (
        "Results are investigation signals — not legal verdicts"
    )

def compute_ui_state(
    risk_result: RiskScoreResult,
    completeness: DocumentCompletenessResult,
    compliance_findings: list,
    cross_ibu_match_level: str,
    price_signal: str,
    requires_human_review: bool,
    officer_decision: Optional[str]
) -> UIState:
    risk_map = {
        RiskBand.LOW:    ("green", "LOW",    "🟢"),
        RiskBand.MEDIUM: ("amber", "MEDIUM", "🟡"),
        RiskBand.HIGH:   ("red",   "HIGH",   "🔴"),
    }
    color, label, icon = risk_map[risk_result.band]

    if officer_decision == "APPROVE":
        settlement_status  = "READY"
        settlement_color   = "green"
        settlement_message = "READY FOR BANK SETTLEMENT WORKFLOW"
        settlement_sub_note = (
            "Bank will proceed with applicable settlement process "
            "including FCSS where relevant."
        )
    elif requires_human_review:
        settlement_status  = "HOLD"
        settlement_color   = "red"
        settlement_message = "HOLD — REVIEW REQUIRED"
        settlement_sub_note = (
            "Bank settlement workflow cannot proceed until "
            "authorized officer decision is recorded."
        )
    elif completeness.status == CompletenessStatus.INCOMPLETE:
        settlement_status  = "HOLD"
        settlement_color   = "red"
        settlement_message = "HOLD — DOCUMENTS INCOMPLETE"
        settlement_sub_note = "Upload all required documents before proceeding."
    else:
        settlement_status  = "READY"
        settlement_color   = "green"
        settlement_message = "READY FOR BANK SETTLEMENT WORKFLOW"
        settlement_sub_note = (
            "Bank will proceed with applicable settlement process "
            "including FCSS where relevant."
        )

    if completeness.status == CompletenessStatus.PENDING_LC:
        run_enabled = False
        run_reason  = "Extract Letter of Credit first"
    elif completeness.status == CompletenessStatus.INCOMPLETE:
        run_enabled = False
        run_reason  = f"Missing: {', '.join(completeness.missing)}"
    else:
        run_enabled = True
        run_reason  = ""

    ucp_badge = (
        "INCOMPLETE"   if completeness.status != CompletenessStatus.COMPLETE else
        "DISCREPANCY"  if compliance_findings else
        "COMPLIANT"
    )

    cross_ibu_badge = {
        "EXACT":    "🔴 EXACT MATCH",
        "NEAR":     "🟡 POSSIBLE MATCH",
        "CONTEXTUAL":"🟡 CONTEXTUAL",
        "NONE":     "🟢 NO MATCH",
    }.get(cross_ibu_match_level, "⏳ NOT CHECKED")

    tbml_badge = {
        "SIGNIFICANT_ANOMALY": "🔴 SIGNIFICANT ANOMALY",
        "REVIEW":              "🟡 REVIEW SIGNAL",
        "NORMAL":              "🟢 NORMAL",
        "DATA_UNAVAILABLE":    "⚪ DATA UNAVAILABLE",
    }.get(price_signal, "⏳ NOT CHECKED")

    return UIState(
        risk_badge_color=color,
        risk_badge_label=label,
        risk_badge_icon=icon,
        settlement_status=settlement_status,
        settlement_color=settlement_color,
        settlement_message=settlement_message,
        settlement_sub_note=settlement_sub_note,
        run_button_enabled=run_enabled,
        run_button_reason=run_reason,
        decision_panel_active=requires_human_review,
        ucp_section_badge=ucp_badge,
        cross_ibu_badge=cross_ibu_badge,
        tbml_badge=tbml_badge,
    )
