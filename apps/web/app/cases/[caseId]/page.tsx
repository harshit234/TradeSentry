"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, ReactNode, useCallback, useEffect, useState } from "react";
import { CaseReport, getReport, submitReview, TOKEN_KEY } from "../../../lib/api";
import { AwsBadge } from "../../aws-badge";

const DECISIONS = ["APPROVE", "HOLD", "ESCALATE", "REQUEST_MORE_EVIDENCE"] as const;

function Section({ id, number, title, note, children }: { id: string; number: string; title: string; note: string; children: ReactNode }) {
  return <section className="evidenceSection" id={id} data-review-section={id}><div className="evidenceHeading"><span>{number}</span><div><h2>{title}</h2><p>{note}</p></div></div>{children}</section>;
}

function StructuredEvidence({ value, empty = "No evidence returned." }: { value: unknown; empty?: string }) {
  if (value === null || value === undefined || (Array.isArray(value) && value.length === 0)) return <p className="emptyEvidence">{empty}</p>;
  return <pre className="structuredEvidence">{JSON.stringify(value, null, 2)}</pre>;
}

function records(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null) : [];
}

export default function CaseReviewPage() {
  const params = useParams<{ caseId: string }>();
  const router = useRouter();
  const caseId = decodeURIComponent(params.caseId);
  const [token, setToken] = useState("");
  const [report, setReport] = useState<CaseReport | null>(null);
  const [error, setError] = useState("");
  const [decision, setDecision] = useState<(typeof DECISIONS)[number]>("HOLD");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async (activeToken: string) => {
    setError("");
    try { setReport(await getReport(activeToken, caseId)); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Unable to load report"); }
  }, [caseId]);

  useEffect(() => {
    const saved = window.localStorage.getItem(TOKEN_KEY) ?? "";
    if (!saved) { router.replace("/"); return; }
    setToken(saved); void load(saved);
  }, [load, router]);

  async function review(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true); setError("");
    try { await submitReview(token, caseId, decision, comment); setComment(""); await load(token); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Decision could not be recorded"); }
    finally { setSubmitting(false); }
  }

  const sections = report?.sections ?? {};
  const compliance = sections.compliance_findings as Record<string, unknown> | null;
  const findings = records(compliance?.findings);
  const risk = sections.risk_assessment as Record<string, unknown> | undefined;
  const timeline = records(sections.investigation_timeline);

  return <main className="caseReview">
    <header className="caseTopbar"><Link href="/">← Case queue</Link><div><p className="eyebrow">Human review record</p><h1>{caseId}</h1></div><div className="headerActions"><AwsBadge /><span className="secureState">JWT · IBU isolated</span></div></header>
    {!report && !error && <div className="reportLoading"><i /><strong>Loading protected evidence…</strong></div>}
    {error && <p className="reportError" role="alert">{error}</p>}
    {report && <>
      <section className={`readinessBanner ${report.case.settlement_readiness.approved ? "ready" : "hold"}`}><div><span>{report.case.settlement_readiness.approved ? "Officer approved" : "Settlement gate"}</span><h2>{report.case.settlement_readiness.status}</h2><p>{report.case.settlement_readiness.reason}</p></div><small>{report.case.settlement_readiness.fcss_note}</small></section>
      <div className="reportLayout"><nav className="reportNav" aria-label="Evidence sections"><strong>Case evidence</strong>{["Case summary", "Documents", "Compliance findings", "Transaction DNA", "Cross-IBU matches", "Fraud & TBML checks", "Risk assessment", "Investigation timeline", "Officer decision"].map((label, index) => <a key={label} href={`#section-${index + 1}`}><span>{String(index + 1).padStart(2, "0")}</span>{label}</a>)}</nav>
      <article className="evidenceReport">
        <Section id="section-1" number="01" title="Case summary" note="Authenticated case identity and current workflow state."><div className="summaryGrid"><div><span>Case ID</span><strong>{report.case.case_id}</strong></div><div><span>IBU tenant</span><strong>{report.case.ibu_id}</strong></div><div><span>Risk band</span><strong className={`riskText ${(report.case.risk_band ?? "LOW").toLowerCase()}`}>{report.case.risk_band ?? "UNSCORED"}</strong></div><div><span>Risk score</span><strong>{report.case.risk_score ?? "—"}</strong></div><div><span>Case status</span><strong>{report.case.status}</strong></div><div><span>Created</span><strong>{new Date(report.case.created_at).toLocaleString()}</strong></div></div></Section>
        <Section id="section-2" number="02" title="Documents" note="Extracted document evidence with short-lived access links."><div className="reportDocuments">{report.documents.map((document) => <div key={document.document_id}><div><strong>{document.filename}</strong><span>{document.document_type.replaceAll("_", " ")} · {document.status}</span></div><b>{document.confidence === null ? "—" : `${Math.round(document.confidence * 100)}%`}</b><a href={document.view_url} target="_blank" rel="noreferrer">View PDF ↗</a><a href={document.download_url}>Download</a></div>)}</div></Section>
        <Section id="section-3" number="03" title="Compliance findings" note="Deterministic findings only; every finding retains its rule and evidence provenance.">{findings.length === 0 ? <p className="emptyEvidence">No compliance findings returned.</p> : <div className="findingList">{findings.map((finding, index) => <article key={String(finding.finding_id ?? index)}><header><strong>{String(finding.rule_id ?? "Rule")}</strong><span>{String(finding.ucp_article ?? "Article unavailable")}</span></header><dl><div><dt>Expected</dt><dd>{String(finding.expected ?? "—")}</dd></div><div><dt>Actual</dt><dd>{String(finding.actual ?? "—")}</dd></div><div><dt>Evidence</dt><dd>{JSON.stringify(finding.evidence ?? {})}</dd></div></dl></article>)}</div>}</Section>
        <Section id="section-4" number="04" title="Transaction DNA" note="Canonical structured trade fingerprint; no raw document content."><StructuredEvidence value={sections.transaction_dna} /></Section>
        <Section id="section-5" number="05" title="Cross-IBU matches" note="Privacy-preserving correlation signals across registered IBU records."><StructuredEvidence value={sections.cross_ibu_matches} empty="No cross-IBU match signals." /></Section>
        <Section id="section-6" number="06" title="Fraud & TBML checks" note="Read-only screening results from allow-listed investigation tools."><StructuredEvidence value={sections.fraud_tbml_checks} /></Section>
        <Section id="section-7" number="07" title="Risk assessment" note="Prototype investigation signal—not a finding of fraud or non-compliance."><div className="riskSummary"><strong>{String(risk?.score ?? "—")}</strong><div><span>{String(risk?.band ?? "UNSCORED")}</span><p>{String(risk?.weights_note ?? "Prototype thresholds are not calibrated for production.")}</p></div></div><StructuredEvidence value={risk?.evidence} empty="No risk evidence records." /></Section>
        <Section id="section-8" number="08" title="Investigation timeline" note="Ordered agent steps and tool outcomes for reproducible review.">{timeline.length === 0 ? <p className="emptyEvidence">No investigation timeline.</p> : <ol className="timeline">{timeline.map((item, index) => <li key={`${String(item.node_name)}-${index}`}><i /><div><strong>{String(item.node_name ?? "Step")}</strong><span>{String(item.status ?? "")}</span><p>{String(item.detail ?? "")}</p><small>{item.occurred_at ? new Date(String(item.occurred_at)).toLocaleString() : ""}</small></div></li>)}</ol>}</Section>
        <Section id="section-9" number="09" title="Officer decision" note="Only an authenticated OFFICER can create an immutable consequential decision."><form className="decisionForm" onSubmit={review}><div className="decisionOptions">{DECISIONS.map((item) => <button type="button" className={decision === item ? "selected" : ""} onClick={() => setDecision(item)} key={item}>{item.replaceAll("_", " ")}</button>)}</div><label><span>Evidence-based rationale · minimum 10 characters</span><textarea required minLength={10} maxLength={4000} value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Record what you reviewed and why this decision is appropriate." /></label><button className="recordDecision" disabled={submitting}>{submitting ? "Recording…" : `Record ${decision.replaceAll("_", " ")}`}</button></form><div className="decisionHistory"><h3>Decision history</h3>{report.decisions.length === 0 ? <p className="emptyEvidence">No officer decision has been recorded.</p> : report.decisions.slice().reverse().map((item) => <article key={item.decision_id}><div><strong>{item.decision.replaceAll("_", " ")}</strong><span>{new Date(item.created_at).toLocaleString()}</span></div><p>{item.comment}</p><small>Officer ID: {item.officer_id}</small></article>)}</div></Section>
      </article></div>
      <footer className="caseFooter">TradeSentry supports investigation and review. It does not execute settlement or control FCSS.</footer>
    </>}
  </main>;
}
