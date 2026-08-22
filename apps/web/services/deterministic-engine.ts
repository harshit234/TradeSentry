/**
 * DETERMINISTIC CORE ENGINE — TypeScript Web Mirror
 * Pure deterministic execution mirroring rules/*.py exactly.
 * Same inputs -> same outputs -> always.
 */

export interface RequiredDocumentSpec {
  documentType: string;
  originalsRequired?: number;
  copiesRequired?: number;
}

export interface DocumentCompletenessResult {
  status: "COMPLETE" | "INCOMPLETE" | "PENDING_LC";
  required: string[];
  present: string[];
  missing: string[];
  detail: Record<string, "PRESENT" | "MISSING">;
}

export function checkCompleteness(
  lcRequiredDocuments: RequiredDocumentSpec[],
  extractedDocumentTypes: string[]
): DocumentCompletenessResult {
  if (!lcRequiredDocuments || lcRequiredDocuments.length === 0) {
    return {
      status: "PENDING_LC",
      required: [],
      present: [],
      missing: [],
      detail: {},
    };
  }

  const required = lcRequiredDocuments.map((s) => s.documentType);
  const present = required.filter((dt) => extractedDocumentTypes.includes(dt));
  const missing = required.filter((dt) => !extractedDocumentTypes.includes(dt));

  const detail: Record<string, "PRESENT" | "MISSING"> = {};
  for (const dt of required) {
    detail[dt] = extractedDocumentTypes.includes(dt) ? "PRESENT" : "MISSING";
  }

  return {
    status: missing.length === 0 ? "COMPLETE" : "INCOMPLETE",
    required,
    present,
    missing,
    detail,
  };
}

// ── EXACT SCORE WEIGHTS (Matching rules/risk_scoring.py) ───────────────
export const SCORE_WEIGHTS = {
  cross_ibu_exact_match: 80,
  cross_ibu_near_match_above_95: 45,
  cross_ibu_near_match_85_to_95: 30,

  compliance_material_per_finding: 40,
  compliance_material_cap: 60,
  compliance_review: 15,
  compliance_review_cap: 30,
  compliance_waivable: 10,
  compliance_waivable_cap: 10,

  price_significant_anomaly: 55,
  price_review_signal: 20,
  vessel_anomaly: 30,
  vessel_data_unavailable: 5,

  sanctions_confirmed_match: 90,
  sanctions_possible_match: 35,

  completeness_incomplete: 25,

  ebl_tampered_document: 70,
  ebl_invalid_signature: 50,
  ebl_unrecognized_ca: 40,
} as const;

export interface RiskScoreResult {
  score: number;
  band: "LOW" | "MEDIUM" | "HIGH";
  breakdown: Record<string, number>;
  weightsNote: string;
}

export function calculateRiskScore(params: {
  crossIBUMatchLevel: "EXACT" | "NEAR" | "NONE";
  crossIBUSimilarity: number;
  complianceFindings: Array<{ severity: "MATERIAL" | "REVIEW" | "POTENTIALLY_WAIVABLE" | "ADVISORY" }>;
  priceSignal: "NORMAL" | "REVIEW" | "SIGNIFICANT_ANOMALY" | "DATA_UNAVAILABLE";
  vesselSignal: "CONSISTENT" | "ANOMALY" | "DATA_UNAVAILABLE";
  sanctionsStatus: "NO_MATCH" | "POSSIBLE_MATCH" | "CONFIRMED_SOURCE_MATCH";
  completenessStatus: "COMPLETE" | "INCOMPLETE" | "PENDING_LC";
  eblIntegrityStatus?: "VALID" | "INVALID" | "TAMPERED" | "NOT_APPLICABLE";
}): RiskScoreResult {
  let score = 0;
  const breakdown: Record<string, number> = {};

  // 1. Cross-IBU
  if (params.crossIBUMatchLevel === "EXACT") {
    score += SCORE_WEIGHTS.cross_ibu_exact_match;
    breakdown["Cross-IBU EXACT match"] = SCORE_WEIGHTS.cross_ibu_exact_match;
  } else if (params.crossIBUMatchLevel === "NEAR") {
    const pts = params.crossIBUSimilarity >= 0.95
      ? SCORE_WEIGHTS.cross_ibu_near_match_above_95
      : SCORE_WEIGHTS.cross_ibu_near_match_85_to_95;
    score += pts;
    breakdown[`Cross-IBU NEAR match (${Math.round(params.crossIBUSimilarity * 100)}%)`] = pts;
  }

  // 2. UCP 600 Compliance
  let materialPoints = 0;
  let reviewPoints = 0;
  let waivablePoints = 0;

  for (const f of params.complianceFindings) {
    if (f.severity === "MATERIAL") materialPoints += SCORE_WEIGHTS.compliance_material_per_finding;
    else if (f.severity === "REVIEW") reviewPoints += SCORE_WEIGHTS.compliance_review;
    else if (f.severity === "POTENTIALLY_WAIVABLE") waivablePoints += SCORE_WEIGHTS.compliance_waivable;
  }

  materialPoints = Math.min(materialPoints, SCORE_WEIGHTS.compliance_material_cap);
  reviewPoints = Math.min(reviewPoints, SCORE_WEIGHTS.compliance_review_cap);
  waivablePoints = Math.min(waivablePoints, SCORE_WEIGHTS.compliance_waivable_cap);

  if (materialPoints) {
    score += materialPoints;
    breakdown[`UCP MATERIAL findings (capped at ${SCORE_WEIGHTS.compliance_material_cap})`] = materialPoints;
  }
  if (reviewPoints) {
    score += reviewPoints;
    breakdown["UCP REVIEW findings"] = reviewPoints;
  }
  if (waivablePoints) {
    score += waivablePoints;
    breakdown["UCP WAIVABLE findings"] = waivablePoints;
  }

  // 3. Price Benchmark
  if (params.priceSignal === "SIGNIFICANT_ANOMALY") {
    score += SCORE_WEIGHTS.price_significant_anomaly;
    breakdown["Price SIGNIFICANT_ANOMALY"] = SCORE_WEIGHTS.price_significant_anomaly;
  } else if (params.priceSignal === "REVIEW") {
    score += SCORE_WEIGHTS.price_review_signal;
    breakdown["Price REVIEW signal"] = SCORE_WEIGHTS.price_review_signal;
  }

  // 4. Vessel Verification
  if (params.vesselSignal === "ANOMALY") {
    score += SCORE_WEIGHTS.vessel_anomaly;
    breakdown["Vessel position ANOMALY"] = SCORE_WEIGHTS.vessel_anomaly;
  } else if (params.vesselSignal === "DATA_UNAVAILABLE") {
    score += SCORE_WEIGHTS.vessel_data_unavailable;
    breakdown["Vessel data unavailable"] = SCORE_WEIGHTS.vessel_data_unavailable;
  }

  // 5. Sanctions
  if (params.sanctionsStatus === "CONFIRMED_SOURCE_MATCH") {
    score += SCORE_WEIGHTS.sanctions_confirmed_match;
    breakdown["Sanctions CONFIRMED match"] = SCORE_WEIGHTS.sanctions_confirmed_match;
  } else if (params.sanctionsStatus === "POSSIBLE_MATCH") {
    score += SCORE_WEIGHTS.sanctions_possible_match;
    breakdown["Sanctions POSSIBLE_MATCH"] = SCORE_WEIGHTS.sanctions_possible_match;
  }

  // 6. Completeness
  if (params.completenessStatus === "INCOMPLETE") {
    score += SCORE_WEIGHTS.completeness_incomplete;
    breakdown["Document completeness INCOMPLETE"] = SCORE_WEIGHTS.completeness_incomplete;
  }

  // 7. eBL
  if (params.eblIntegrityStatus === "TAMPERED") {
    score += SCORE_WEIGHTS.ebl_tampered_document;
    breakdown["eBL document TAMPERED (hash mismatch)"] = SCORE_WEIGHTS.ebl_tampered_document;
  } else if (params.eblIntegrityStatus === "INVALID") {
    score += SCORE_WEIGHTS.ebl_invalid_signature;
    breakdown["eBL invalid digital signature"] = SCORE_WEIGHTS.ebl_invalid_signature;
  }

  const band: "LOW" | "MEDIUM" | "HIGH" = score >= 70 ? "HIGH" : score >= 30 ? "MEDIUM" : "LOW";

  return {
    score,
    band,
    breakdown,
    weightsNote: "⚠ Prototype demo weights — not calibrated for production use. Production requires statistical validation against labeled outcomes.",
  };
}

export function shouldRequireHumanReview(params: {
  riskBand: "LOW" | "MEDIUM" | "HIGH";
  complianceFindings: Array<{ severity: string; rule_id?: string; ruleId?: string }>;
  crossIBUMatchLevel: "EXACT" | "NEAR" | "NONE";
  eblIntegrityStatus?: string;
}): { requiresHumanReview: boolean; reasons: string[] } {
  const reasons: string[] = [];

  if (params.riskBand === "HIGH") {
    reasons.push("Risk score in HIGH band (≥70)");
  }

  const material = params.complianceFindings.filter((f) => f.severity === "MATERIAL");
  if (material.length > 0) {
    const ids = material.map((m) => m.rule_id || m.ruleId || "MATERIAL_FINDING").join(", ");
    reasons.push(`${material.length} MATERIAL compliance finding(s): ${ids}`);
  }

  if (params.crossIBUMatchLevel === "EXACT") {
    reasons.push("Cross-IBU EXACT duplicate financing match");
  }

  if (params.eblIntegrityStatus === "TAMPERED") {
    reasons.push("eBL document tampered — hash mismatch detected");
  }

  return {
    requiresHumanReview: reasons.length > 0,
    reasons,
  };
}
