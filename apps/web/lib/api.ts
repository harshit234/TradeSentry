const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const TOKEN_KEY = "tradesentry_dashboard_jwt";

export type Readiness = {
  case_id: string;
  status: string;
  approved: boolean;
  reason: string;
  latest_decision: string | null;
  fcss_note: string;
};

export type DashboardCase = {
  case_id: string;
  ibu_id: string;
  status: string;
  risk_band: "LOW" | "MEDIUM" | "HIGH" | null;
  risk_score: number | null;
  applicant: string | null;
  beneficiary: string | null;
  amount: string | null;
  currency: string | null;
  created_at: string;
  settlement_readiness: Readiness;
};

export type ReportDocument = {
  document_id: string;
  filename: string;
  document_type: string;
  status: string;
  confidence: number | null;
  extraction: Record<string, unknown> | null;
  view_url: string;
  download_url: string;
};

export type OfficerDecision = {
  decision_id: string;
  case_id: string;
  decision: string;
  comment: string;
  officer_id: string;
  officer_role: string;
  created_at: string;
};

export type CaseReport = {
  case: DashboardCase;
  sections: Record<string, unknown>;
  documents: ReportDocument[];
  decisions: OfficerDecision[];
};

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail ?? `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function auth(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function getCases(token: string): Promise<DashboardCase[]> {
  return json(await fetch(`${API_URL}/cases`, { headers: auth(token), cache: "no-store" }));
}

export async function getReport(token: string, caseId: string): Promise<CaseReport> {
  return json(await fetch(`${API_URL}/cases/${caseId}/report`, { headers: auth(token), cache: "no-store" }));
}

export async function submitReview(
  token: string,
  caseId: string,
  decision: string,
  comment: string,
): Promise<OfficerDecision> {
  return json(await fetch(`${API_URL}/cases/${caseId}/review`, {
    method: "POST",
    headers: { ...auth(token), "Content-Type": "application/json" },
    body: JSON.stringify({ decision, comment }),
  }));
}
