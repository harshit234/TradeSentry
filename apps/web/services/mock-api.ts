import type {
  TradeCase,
  AuditEntry,
  Alert,
  PipelineCounts,
  WorkflowStep,
  CurrentUser,
} from "@/types";
import { DEMO_AUDIT_TRAIL } from "@/mock-data/audit";
import { DEMO_ALERTS } from "@/mock-data/alerts";

/* ─── In-Memory Store synced with LocalStorage ─── */
let inMemoryCases: TradeCase[] = [];
const CASE_STORAGE_KEY = "tradesentry_genuine_cases";
const CASE_RESET_VERSION_KEY = "tradesentry_case_reset_version";
const CASE_RESET_VERSION = "2026-08-22-cleared-all-cases";

function loadStoredCases(): TradeCase[] {
  if (typeof window === "undefined") return inMemoryCases;
  try {
    if (localStorage.getItem(CASE_RESET_VERSION_KEY) !== CASE_RESET_VERSION) {
      localStorage.removeItem(CASE_STORAGE_KEY);
      localStorage.setItem(CASE_RESET_VERSION_KEY, CASE_RESET_VERSION);
      inMemoryCases = [];
    }

    const raw = localStorage.getItem(CASE_STORAGE_KEY);
    if (raw) {
      inMemoryCases = JSON.parse(raw);
    }
  } catch (e) {
    console.error("Failed to load stored cases", e);
  }
  return inMemoryCases;
}

function saveStoredCases(cases: TradeCase[]): void {
  inMemoryCases = cases;
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(CASE_STORAGE_KEY, JSON.stringify(cases));
    } catch (e) {
      console.error("Failed to save stored cases", e);
    }
  }
}

/* ─── Simulated delay for smooth UX ─── */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/* ─── Current user (mock) ─── */
export function getCurrentUser(): CurrentUser {
  return {
    id: "Officer-102",
    name: "Priya Sharma",
    role: "TRADE_OFFICER",
    ibu: "IBU-GIFT-01",
  };
}

/* ─── Cases (Pure Dynamic Genuine Cases Only) ─── */
export async function getCases(): Promise<TradeCase[]> {
  await delay(100);
  return loadStoredCases();
}

export async function getCase(caseId: string): Promise<TradeCase | null> {
  await delay(50);
  const cases = loadStoredCases();
  const found = cases.find((c) => c.caseId === caseId) ||
                cases.find((c) => c.caseId.toLowerCase() === caseId.toLowerCase());
  if (found) return found;

  // Dynamically generate genuine case structure for this caseId
  const isCaseC = caseId.toUpperCase().includes("CASE-C") || caseId.toUpperCase().includes("TBML");
  const isCaseB = caseId.toUpperCase().includes("CASE-B") || caseId.toUpperCase().includes("DUP");

  const defaultCase: TradeCase = {
    caseId,
    lcReference: `LC-GIFT-2024-${caseId.slice(-4) || "0042"}`,
    transactionRef: `TXN-${caseId.slice(-4) || "0042"}`,
    exporter: isCaseC ? "TBML Exports Ltd" : "ABC Trading Ltd",
    importer: isCaseC ? "Pacific Imports Pte Ltd" : "XYZ Imports Pte Ltd",
    amount: isCaseC ? 405000 : 225000,
    currency: "USD",
    presentingIBU: isCaseB ? "IBU-GIFT-02" : "IBU-GIFT-01",
    riskBand: isCaseC || isCaseB ? "HIGH" : "LOW",
    riskScore: isCaseC ? 78 : isCaseB ? 84 : 18,
    status: "READY",
    documents: [
      { documentId: `${caseId}-DOC-001`, caseId, filename: "lc.pdf", documentType: "letter_of_credit", status: "EXTRACTED", confidence: 0.98, sizeBytes: 185000, uploadedAt: new Date().toISOString() },
      { documentId: `${caseId}-DOC-002`, caseId, filename: "commercial_invoice.pdf", documentType: "commercial_invoice", status: "EXTRACTED", confidence: 0.97, sizeBytes: 210000, uploadedAt: new Date().toISOString() },
      { documentId: `${caseId}-DOC-003`, caseId, filename: "bill_of_lading.pdf", documentType: "bill_of_lading", status: "EXTRACTED", confidence: 0.96, sizeBytes: 195000, uploadedAt: new Date().toISOString() },
      { documentId: `${caseId}-DOC-004`, caseId, filename: "packing_list.pdf", documentType: "packing_list", status: "EXTRACTED", confidence: 0.96, sizeBytes: 175000, uploadedAt: new Date().toISOString() },
      { documentId: `${caseId}-DOC-005`, caseId, filename: "certificate_of_origin.pdf", documentType: "certificate_of_origin", status: "EXTRACTED", confidence: 0.95, sizeBytes: 160000, uploadedAt: new Date().toISOString() },
      { documentId: `${caseId}-DOC-006`, caseId, filename: "insurance_certificate.pdf", documentType: "insurance_certificate", status: "EXTRACTED", confidence: 0.95, sizeBytes: 190000, uploadedAt: new Date().toISOString() },
    ],
    documentCount: 6,
    complianceStatus: isCaseC || isCaseB ? "REVIEW" : "PASS",
    crossIBUSignal: isCaseB,
    duplicateSignal: isCaseB,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    extraction: {
      exporter: isCaseC ? "TBML Exports Ltd" : "ABC Trading Ltd",
      importer: isCaseC ? "Pacific Imports Pte Ltd" : "XYZ Imports Pte Ltd",
      lcAmount: isCaseC ? "405,000.00" : "225,000.00",
      currency: "USD",
      commodity: "Semi-milled rice",
      quantity: "500",
      unit: "MT",
      blNumber: "BL789456",
      vessel: isCaseC ? "SEA EAGLE" : "OCEAN STAR",
      voyageNumber: "V123",
      route: "Mundra, India → Singapore",
      loadingPort: "Mundra, India",
      dischargePort: "Singapore",
      shipmentDate: new Date().toISOString().split("T")[0],
      hsCode: "1006.30",
      incoterms: "CIF",
      documentsProcessed: 6,
      totalDocuments: 6,
      averageConfidence: 0.97,
    },
    compliance: {
      totalChecks: 18,
      pass: isCaseC || isCaseB ? 15 : 18,
      review: isCaseC || isCaseB ? 3 : 0,
      advisory: 0,
      fail: 0,
      findings: isCaseC
        ? [{ findingId: "FC-001", ucpArticle: "Art. 18(a)(iii)", ruleId: "UCP600-INV-OVER", requirement: "Invoice unit price within commercial corridor", actual: "USD 810.00/MT vs baseline $450.00/MT", result: "REVIEW", evidence: "+80% price anomaly detected", page: 1 }]
        : isCaseB
        ? [{ findingId: "FB-001", ucpArticle: "Art. 14(d)", ruleId: "UCP600-DUPLICATE-SIG", requirement: "Original unique bill of lading presentation", actual: "B/L BL789456 already financed in IBU-GIFT-01", result: "REVIEW", evidence: "Cross-IBU duplicate registry match", page: 1 }]
        : [
            { findingId: "F-001", ucpArticle: "Art. 18(a)(iii)", ruleId: "UCP600-INV-AMOUNT", requirement: "Invoice amount ≤ LC credit amount", actual: "USD 225,000.00 = LC USD 225,000.00", result: "PASS", evidence: "commercial_invoice.pdf & lc.pdf exact match", page: 1 },
            { findingId: "F-002", ucpArticle: "Art. 14(d)", ruleId: "UCP600-DESC-CONSISTENCY", requirement: "Goods description consistent across all documents", actual: "Semi-milled rice (HS 1006.30)", result: "PASS", evidence: "Exact description matches across LC, Invoice, B/L", page: 1 },
          ],
    },
    discrepancies: isCaseC
      ? [{ id: "DISC-C-001", ucpArticle: "Art. 18(a)(iii)", ruleId: "UCP600-PRICE-ANOMALY", description: "Significant price inflation detected (potential TBML over-invoicing)", expected: "Market benchmark unit price $400-$520/MT", actual: "Invoiced at $810/MT (+80% above P90 benchmark)", evidence: "commercial_invoice.pdf unit price $810/MT", severity: "MATERIAL", page: 1 }]
      : isCaseB
      ? [{ id: "DISC-B-001", ucpArticle: "Art. 14(d)", ruleId: "UCP600-DUPLICATE-SIG", description: "Bill of Lading already registered under active financing in IBU-GIFT-01", expected: "Original unique bill of lading presentation", actual: "BL789456 matches active presentation under DEMO-CASE-A", evidence: "Duplicate registry match (98% similarity)", severity: "MATERIAL", page: 1 }]
      : [],
    transactionDNA: {
      fields: [
        { label: "Exporter", value: isCaseC ? "TBML Exports Ltd" : "ABC Trading Ltd", source: "commercial_invoice.pdf", confidence: 0.98 },
        { label: "Importer", value: isCaseC ? "Pacific Imports Pte Ltd" : "XYZ Imports Pte Ltd", source: "lc.pdf", confidence: 0.98 },
        { label: "LC Amount", value: isCaseC ? "USD 405,000.00" : "USD 225,000.00", source: "lc.pdf", confidence: 0.99 },
      ],
      relationships: { exporter: isCaseC ? "TBML Exports Ltd" : "ABC Trading Ltd", importer: isCaseC ? "Pacific Imports Pte Ltd" : "XYZ Imports Pte Ltd", lc: `LC-GIFT-${caseId}`, invoice: "INV-001", bl: "BL789456", vessel: isCaseC ? "SEA EAGLE" : "OCEAN STAR", voyage: "V123" },
    },
    duplicateFinancing: isCaseB
      ? { found: true, blNumber: "BL789456", similarity: 0.98, matchedFields: ["B/L Number", "Vessel Name", "Voyage Number", "Shipper", "Shipment Route"], assessment: "POTENTIAL DUPLICATE FINANCING SIGNAL", sourceIBU: "IBU-GIFT-01", relatedRef: "DEMO-CASE-A" }
      : { found: false, assessment: "No duplicate financing signals detected across global registry" },
    crossIBUMatches: isCaseB
      ? [{ matchId: "XIBU-001", relatedIBU: "IBU-GIFT-01", networkSimilarity: 0.96, matchLevel: "HIGH", sharedSignals: ["B/L Number", "Vessel Name", "Voyage Number", "Shipment Date"], relatedCaseRef: "DEMO-CASE-A", assessment: "Same Bill of Lading financed under different IBU facility", note: "Shared: permitted intelligence signals only. Raw documents NOT shared.", timestamp: new Date().toISOString() }]
      : [],
    fraudInvestigation: {
      agentDecision: isCaseC
        ? "TBML over-invoicing and vessel AIS route anomaly detected"
        : "Standard investigation — all 4 fraud/TBML tools returned clean/normal results",
      tools: [
        { toolName: "price_benchmark", displayName: "Price Benchmark", status: "completed", result: isCaseC ? "SIGNIFICANT_ANOMALY" : "NORMAL", evidence: isCaseC ? "Semi-milled rice unit price $810/MT is +80% above P90 benchmark ($450/MT)" : "Semi-milled rice unit price $450/MT is within normal corridor P25-P75 range ($400-$520/MT)", signal: isCaseC ? "SIGNIFICANT_ANOMALY" : "NORMAL", confidence: 0.96, timestamp: new Date().toISOString() },
        { toolName: "vessel_verification", displayName: "Vessel Verification", status: "completed", result: isCaseC ? "ANOMALY" : "CONSISTENT", evidence: isCaseC ? "SEA EAGLE AIS position indicates departure port mismatch" : "OCEAN STAR AIS track confirmed at Mundra port", signal: isCaseC ? "ANOMALY" : "NORMAL", confidence: 0.95, timestamp: new Date().toISOString() },
        { toolName: "entity_verification", displayName: "Entity Verification", status: "completed", result: "VERIFIED", evidence: "Both parties verified in good standing", signal: "NORMAL", confidence: 0.97, timestamp: new Date().toISOString() },
        { toolName: "sanctions_screening", displayName: "Sanctions Screening", status: "completed", result: "NO_MATCH", evidence: "Clean sanctions screening", signal: "CLEAR", confidence: 0.99, timestamp: new Date().toISOString() },
      ],
    },
    risk: {
      overallScore: isCaseC ? 78 : isCaseB ? 84 : 18,
      overallBand: isCaseC || isCaseB ? "HIGH" : "LOW",
      breakdown: [
        { category: "Compliance", band: isCaseC || isCaseB ? "MEDIUM" : "LOW", score: isCaseC ? 40 : isCaseB ? 45 : 0, reason: isCaseC ? "Invoice price deviation" : isCaseB ? "Duplicate B/L presentation" : "18 of 18 UCP checks passed cleanly" },
        { category: "Duplicate Financing", band: isCaseB ? "HIGH" : "LOW", score: isCaseB ? 98 : 0, reason: isCaseB ? "Identical B/L BL789456, Vessel OCEAN STAR" : "No duplicate B/L found" },
        { category: "Cross-IBU", band: isCaseB ? "HIGH" : "LOW", score: isCaseB ? 96 : 0, reason: isCaseB ? "Match found with IBU-GIFT-01 transaction" : "Zero cross-IBU conflicts" },
        { category: "TBML & Fraud", band: isCaseC ? "HIGH" : "LOW", score: isCaseC ? 92 : 5, reason: isCaseC ? "Price anomaly +80% above P90 benchmark" : "Price within normal benchmark corridor" },
        { category: "Vessel & Carrier", band: isCaseC ? "HIGH" : "LOW", score: isCaseC ? 75 : 5, reason: isCaseC ? "Vessel route mismatch" : "AIS track verified" },
      ],
      reasons: isCaseC
        ? ["Severe TBML over-invoicing signal: $810/MT vs $450/MT benchmark", "Vessel SEA EAGLE AIS position indicates route anomaly"]
        : isCaseB
        ? ["Potential duplicate financing: Identical Bill of Lading (BL789456) across IBUs"]
        : ["100% compliance with UCP 600 articles", "Normal price corridor benchmark", "Vessel trajectory verified", "Clean sanctions screening"],
      weightsNote: "Prototype weights — deterministic evaluation",
    },
    humanReview: { required: isCaseC || isCaseB, aiRecommendation: isCaseC ? "High risk — TBML price anomaly flagged; require compliance officer review" : isCaseB ? "High risk — duplicate financing detected; require secondary officer verification" : "Low risk (18/100) — eligible for human officer approval", reason: isCaseC ? "Invoice price is 80% above market benchmarks." : isCaseB ? "Identical Bill of Lading BL789456 financed in IBU-GIFT-01." : "All checks passed cleanly." },
    evidence: [],
    agentTimeline: [
      { timestamp: new Date().toISOString(), agent: "Supervisor Agent", action: "Initiated 11-step investigation" },
    ],
    agentStatus: { state: "completed", evidenceFound: isCaseC || isCaseB ? 2 : 0, toolsUsed: ["UCP 600 Engine", "Price Benchmark", "Vessel Verification", "Sanctions Screening"], recommendation: isCaseC ? "High risk — TBML signals require compliance review" : isCaseB ? "High risk — duplicate financing signal requires human approval" : "Low risk — 100% pass across all stages" },
  };

  await createCase(defaultCase);
  return defaultCase;
}

export interface SearchResult {
  caseId: string;
  title: string;
  subtitle: string;
  matchField?: string;
  status: string;
  riskBand: string | null;
}

export async function searchCases(query: string): Promise<SearchResult[]> {
  await delay(50);
  const cases = loadStoredCases();
  if (!query.trim()) return [];
  const q = query.toLowerCase();
  return cases
    .filter((c) =>
      c.caseId.toLowerCase().includes(q) ||
      c.lcReference.toLowerCase().includes(q) ||
      c.exporter.toLowerCase().includes(q) ||
      c.importer.toLowerCase().includes(q)
    )
    .map((c) => ({
      caseId: c.caseId,
      title: `${c.caseId} — ${c.lcReference}`,
      subtitle: `${c.exporter} → ${c.importer}`,
      matchField: c.caseId.toLowerCase().includes(q) ? "Case ID" : "Party / LC",
      status: c.status,
      riskBand: c.riskBand ?? "LOW",
    }));
}

export async function createCase(tradeCase: TradeCase): Promise<TradeCase> {
  const cases = loadStoredCases();
  const existingIdx = cases.findIndex((c) => c.caseId === tradeCase.caseId);
  let updated: TradeCase[];
  if (existingIdx >= 0) {
    updated = [...cases];
    updated[existingIdx] = tradeCase;
  } else {
    updated = [tradeCase, ...cases];
  }
  saveStoredCases(updated);
  await delay(150);
  return tradeCase;
}

export async function deleteCase(caseId: string): Promise<boolean> {
  await delay(100);
  const cases = loadStoredCases();
  const updated = cases.filter((c) => c.caseId !== caseId);
  saveStoredCases(updated);
  return true;
}

export async function clearAllCases(): Promise<void> {
  saveStoredCases([]);
}

/* ─── Pipeline Counts ─── */
export async function getPipelineCounts(): Promise<PipelineCounts> {
  await delay(100);
  const cases = loadStoredCases();
  return {
    submitted: cases.filter((c) => c.status === "SUBMITTED").length,
    processing: cases.filter((c) => c.status === "PROCESSING").length,
    compliance: cases.filter((c) => c.status === "COMPLIANCE").length,
    investigation: cases.filter((c) => c.status === "INVESTIGATION").length,
    review: cases.filter((c) => c.status === "REVIEW").length,
    ready: cases.filter((c) => c.status === "READY").length,
  };
}

/* ─── KPIs ─── */
export interface KPIData {
  activeCases: number;
  awaitingReview: number;
  highRisk: number;
  duplicateSignals: number;
  avgReviewMinutes: number;
}

export async function getKPIs(): Promise<KPIData> {
  await delay(100);
  const cases = loadStoredCases();
  return {
    activeCases: cases.length,
    awaitingReview: cases.filter((c) => c.status === "REVIEW" || c.riskBand === "HIGH").length,
    highRisk: cases.filter((c) => c.riskBand === "HIGH").length,
    duplicateSignals: cases.filter((c) => c.duplicateSignal).length,
    avgReviewMinutes: cases.length > 0 ? 12 : 0,
  };
}

/* ─── Audit ─── */
export async function getAuditTrail(caseId?: string): Promise<AuditEntry[]> {
  await delay(100);
  if (caseId) {
    return DEMO_AUDIT_TRAIL.filter((e) => e.caseId === caseId);
  }
  return DEMO_AUDIT_TRAIL;
}

/* ─── Alerts ─── */
export async function getAlerts(): Promise<Alert[]> {
  await delay(100);
  const cases = loadStoredCases();
  if (cases.length === 0) return [];
  return DEMO_ALERTS;
}

/* ─── Workflow Steps (11 Steps ending at Step 11 Human Review) ─── */
export function buildWorkflowSteps(tradeCase: TradeCase): WorkflowStep[] {
  const hasDiscrepancies = (tradeCase.discrepancies?.length ?? 0) > 0;
  const hasDuplicate = tradeCase.duplicateFinancing?.found ?? false;
  const hasCrossIBU = (tradeCase.crossIBUMatches?.length ?? 0) > 0;
  const isHighRisk = tradeCase.riskBand === "HIGH";
  const isAuthorized = tradeCase.humanReview?.decision === "APPROVE";
  const hasFraudSignals = tradeCase.fraudInvestigation?.tools.some((tool) =>
    !["NORMAL", "CLEAR", "CONSISTENT", "VERIFIED", "NO_MATCH"].includes(tool.signal ?? "") &&
    !["NORMAL", "CLEAR", "CONSISTENT", "VERIFIED", "NO_MATCH"].includes(tool.result ?? "")
  ) ?? false;

  return [
    {
      id: "document_upload",
      stepNumber: 1,
      title: "Document Upload",
      status: "completed",
      startedAt: tradeCase.createdAt,
      completedAt: tradeCase.createdAt,
      summary: `${tradeCase.documentCount} documents received`,
      findings: tradeCase.documents.map((d) => `✓ ${d.documentType.replace(/_/g, " ")}`),
    },
    {
      id: "document_extraction",
      stepNumber: 2,
      title: "Document Extraction",
      status: "completed",
      summary: `${tradeCase.extraction?.documentsProcessed ?? 0} / ${tradeCase.extraction?.totalDocuments ?? 0} documents processed`,
    },
    {
      id: "document_completeness",
      stepNumber: 3,
      title: "Document Completeness",
      status: "completed",
      summary: "All mandatory presentation documents present",
    },
    {
      id: "ucp600_compliance",
      stepNumber: 4,
      title: "UCP 600 Compliance Checks",
      status: hasDiscrepancies ? "review" : "completed",
      findings: hasDiscrepancies
        ? tradeCase.discrepancies?.map((d) => `${d.ucpArticle}: ${d.description}`)
        : ["18 deterministic checks passed"],
      summary: hasDiscrepancies
        ? `${tradeCase.discrepancies?.length} discrepancies flagged`
        : "18 of 18 checks compliant",
    },
    {
      id: "cross_document_consistency",
      stepNumber: 5,
      title: "Cross-Document Consistency",
      status: hasDiscrepancies ? "review" : "completed",
      summary: hasDiscrepancies ? "Conflicts identified across documents" : "All fields match across presentation",
    },
    {
      id: "transaction_dna",
      stepNumber: 6,
      title: "Transaction DNA",
      status: "completed",
      summary: "Transaction fingerprint and entity network graph generated",
    },
    {
      id: "duplicate_financing",
      stepNumber: 7,
      title: "Duplicate Financing Check",
      status: hasDuplicate ? "review" : "completed",
      findings: hasDuplicate ? ["POTENTIAL DUPLICATE FINANCING DETECTED"] : ["Zero duplicate financing matches"],
      summary: hasDuplicate ? "Duplicate B/L detected across IBU registry" : "No duplicate financing found",
    },
    {
      id: "cross_ibu_intelligence",
      stepNumber: 8,
      title: "Cross-IBU Intelligence",
      status: hasCrossIBU ? "review" : "completed",
      summary: hasCrossIBU ? "Cross-IBU entity correlation found" : "No cross-IBU conflicts",
    },
    {
      id: "fraud_tbml",
      stepNumber: 9,
      title: "Fraud / TBML Investigation",
      status: hasFraudSignals ? "review" : "completed",
      findings: [
        "Price benchmark verified",
        "Vessel trajectory checked",
        "Entity verification completed",
        "Sanctions screened (OFAC / UN / EU / Sanctions-IN)",
      ],
      summary: hasFraudSignals ? "Anomalies detected in fraud/TBML tools" : "All fraud/TBML tools cleared",
    },
    {
      id: "risk_assessment",
      stepNumber: 10,
      title: "Risk Assessment",
      status: isHighRisk ? "review" : "completed",
      summary: `Composite risk score: ${tradeCase.riskScore}/100 (${tradeCase.riskBand})`,
    },
    {
      id: "human_review",
      stepNumber: 11,
      title: "Human Review & Authorization",
      status: isAuthorized ? "completed" : "pending",
      summary: isAuthorized ? "Consequential review authorized by officer" : "Pending trade officer approval",
    },
  ];
}
