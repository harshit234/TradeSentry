/* ─── Workflow ─── */
export type WorkflowStatus =
  | "pending"
  | "processing"
  | "completed"
  | "review"
  | "failed"
  | "skipped";

export interface WorkflowStep {
  id: string;
  stepNumber: number;
  title: string;
  status: WorkflowStatus;
  startedAt?: string;
  completedAt?: string;
  summary?: string;
  findings?: string[];
  evidenceIds?: string[];
  details?: Record<string, unknown>;
}

/* ─── Risk ─── */
export type RiskBand = "LOW" | "MEDIUM" | "HIGH";

export interface RiskBreakdownItem {
  category: string;
  band: RiskBand;
  score: number;
  reason?: string;
}

export interface RiskAssessment {
  overallScore: number;
  overallBand: RiskBand;
  breakdown: RiskBreakdownItem[];
  reasons: string[];
  weightsNote: string;
}

/* ─── Documents ─── */
export type DocumentType =
  | "letter_of_credit"
  | "commercial_invoice"
  | "bill_of_lading"
  | "packing_list"
  | "certificate_of_origin"
  | "insurance_certificate"
  | "inspection_certificate";

export type DocumentStatus =
  | "UPLOADED"
  | "CLASSIFIED"
  | "EXTRACTING"
  | "EXTRACTED"
  | "PARTIAL"
  | "FAILED"
  | "MISSING";

export const DOCUMENT_LABELS: Record<DocumentType, string> = {
  letter_of_credit: "Letter of Credit",
  commercial_invoice: "Commercial Invoice",
  bill_of_lading: "Bill of Lading",
  packing_list: "Packing List",
  certificate_of_origin: "Certificate of Origin",
  insurance_certificate: "Insurance Certificate",
  inspection_certificate: "Inspection Certificate",
};

export interface TradeDocument {
  documentId: string;
  caseId: string;
  filename: string;
  documentType: DocumentType;
  status: DocumentStatus;
  confidence: number | null;
  sizeBytes: number;
  uploadedAt: string;
  extractedFields?: Record<string, unknown>;
}

/* ─── Extraction ─── */
export interface ExtractionSummary {
  exporter: string;
  importer: string;
  lcAmount: string;
  currency: string;
  commodity: string;
  quantity: string;
  unit: string;
  blNumber: string;
  vessel: string;
  voyageNumber: string;
  route: string;
  loadingPort: string;
  dischargePort: string;
  shipmentDate: string;
  hsCode: string;
  incoterms?: string;
  documentsProcessed: number;
  totalDocuments: number;
  averageConfidence: number;
}

/* ─── Compliance ─── */
export type ComplianceSeverity = "PASS" | "REVIEW" | "ADVISORY" | "FAIL";

export interface ComplianceFinding {
  findingId: string;
  ruleId: string;
  ucpArticle: string;
  requirement: string;
  expected?: string;
  actual: string;
  result: ComplianceSeverity;
  evidence: string;
  page?: number;
  severity?: ComplianceSeverity;
}

export interface ComplianceResult {
  totalChecks: number;
  pass: number;
  review: number;
  advisory: number;
  fail: number;
  findings: ComplianceFinding[];
}

/* ─── Discrepancy ─── */
export interface DiscrepancyItem {
  id: string;
  ucpArticle: string;
  ruleId: string;
  description: string;
  expected: string;
  actual: string;
  evidence: string;
  severity: "MATERIAL" | "REVIEW" | "ADVISORY";
  page?: number;
}

/* ─── Transaction DNA ─── */
export interface TransactionDNAField {
  label: string;
  value: string;
  source: string;
  confidence: number;
  documentRef?: string;
}

export interface TransactionDNAData {
  fields: TransactionDNAField[];
  relationships: {
    exporter: string;
    importer: string;
    lc: string;
    invoice: string;
    bl: string;
    vessel: string;
    voyage: string;
  };
}

/* ─── Cross-IBU ─── */
export type CrossIBUMatchLevel = "NONE" | "LOW" | "MEDIUM" | "HIGH" | "EXACT";

export interface CrossIBUMatch {
  matchId: string;
  relatedIBU: string;
  networkSimilarity: number;
  matchLevel: CrossIBUMatchLevel;
  sharedSignals: string[];
  relatedCaseRef?: string;
  assessment: string;
  note: string;
  timestamp: string;
}

/* ─── Duplicate Financing ─── */
export interface DuplicateFinancingResult {
  found: boolean;
  blNumber?: string;
  similarity?: number;
  matchedFields?: string[];
  assessment: string;
  sourceIBU?: string;
  relatedRef?: string;
}

/* ─── Fraud / TBML ─── */
export type FraudToolStatus = "pending" | "running" | "completed" | "skipped" | "error";

export interface FraudToolResult {
  toolName: string;
  displayName: string;
  status: FraudToolStatus;
  result?: string;
  evidence?: string;
  signal?: string;
  confidence?: number;
  timestamp?: string;
}

export interface FraudInvestigation {
  agentDecision: string;
  tools: FraudToolResult[];
}

/* ─── Evidence ─── */
export interface EvidenceRecord {
  evidenceId: string;
  source: string;
  findingType: string;
  severity: "INFO" | "ADVISORY" | "REVIEW" | "MATERIAL" | "HIGH";
  summary: string;
  detail: string;
  matchedFields?: string[];
  confidence?: number;
  sourceIBU?: string;
  timestamp: string;
  structuredDetail?: Record<string, unknown>;
}

/* ─── Human Review ─── */
export type ReviewDecision = "APPROVE" | "HOLD" | "ESCALATE" | "REQUEST_MORE_EVIDENCE";

export interface HumanReview {
  required: boolean;
  aiRecommendation: string;
  reason: string;
  decision?: ReviewDecision;
  officerId?: string;
  decisionTimestamp?: string;
  comment?: string;
}

/* ─── Settlement ─── */
export interface SettlementReadiness {
  status: "HOLD" | "READY" | "PENDING";
  reason: string;
  humanDecision?: string;
  officerId?: string;
  timestamp?: string;
  fcssNote: string;
}

/* ─── Agent ─── */
export interface AgentStatus {
  state: "idle" | "investigating" | "completed";
  currentAction?: string;
  currentTool?: string;
  evidenceFound: number;
  nextStep?: string;
  toolsUsed: string[];
  recommendation?: string;
}

export interface AgentTimelineEntry {
  timestamp: string;
  agent: string;
  action: string;
  result?: string;
  evidenceId?: string;
}

/* ─── Audit ─── */
export interface AuditEntry {
  id: string;
  timestamp: string;
  user: string;
  userRole: string;
  ibu: string;
  caseId: string;
  action: string;
  component: string;
  result: string;
  evidenceRef?: string;
}

/* ─── Alert ─── */
export type AlertCategory =
  | "HIGH_RISK"
  | "CROSS_IBU_MATCH"
  | "UCP_DISCREPANCY"
  | "TBML"
  | "MISSING_DOCUMENT"
  | "SYSTEM_ERROR";

export interface Alert {
  id: string;
  category: AlertCategory;
  title: string;
  description: string;
  caseId?: string;
  ibu?: string;
  timestamp: string;
  read: boolean;
  severity: RiskBand;
}

/* ─── Trade Case ─── */
export type CaseStatus =
  | "SUBMITTED"
  | "PROCESSING"
  | "COMPLIANCE"
  | "INVESTIGATION"
  | "REVIEW"
  | "READY"
  | "HOLD"
  | "ESCALATED";

export interface TradeCase {
  caseId: string;
  lcReference: string;
  transactionRef?: string;
  exporter: string;
  importer: string;
  amount: number;
  currency: string;
  presentingIBU: string;
  riskBand: RiskBand | null;
  riskScore: number | null;
  status: CaseStatus;
  documents: TradeDocument[];
  documentCount: number;
  complianceStatus?: "PASS" | "REVIEW" | "FAIL";
  crossIBUSignal?: boolean;
  duplicateSignal?: boolean;
  createdAt: string;
  updatedAt: string;

  /* Investigation data */
  workflow?: WorkflowStep[];
  extraction?: ExtractionSummary;
  compliance?: ComplianceResult;
  discrepancies?: DiscrepancyItem[];
  transactionDNA?: TransactionDNAData;
  duplicateFinancing?: DuplicateFinancingResult;
  crossIBUMatches?: CrossIBUMatch[];
  fraudInvestigation?: FraudInvestigation;
  risk?: RiskAssessment;
  humanReview?: HumanReview;
  settlementReadiness?: SettlementReadiness;
  evidence?: EvidenceRecord[];
  agentStatus?: AgentStatus;
  agentTimeline?: AgentTimelineEntry[];
}

/* ─── Workflow Events (for backend integration) ─── */
export interface WorkflowEvent {
  caseId: string;
  eventId: string;
  step: string;
  status: WorkflowStatus;
  timestamp: string;
  summary?: string;
  evidenceIds?: string[];
}

/* ─── Pipeline counts ─── */
export interface PipelineCounts {
  submitted: number;
  processing: number;
  compliance: number;
  investigation: number;
  review: number;
  ready: number;
}

/* ─── User / Role ─── */
export type UserRole =
  | "TRADE_OFFICER"
  | "COMPLIANCE_OFFICER"
  | "AML_OFFICER"
  | "TRADE_MANAGER"
  | "RISK_OFFICER"
  | "ADMIN";

export interface CurrentUser {
  id: string;
  name: string;
  role: UserRole;
  ibu: string;
}
