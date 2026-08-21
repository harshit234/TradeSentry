"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { DashboardCase, getCases, TOKEN_KEY } from "../lib/api";

type RiskFilter = "ALL" | "HIGH" | "MEDIUM" | "LOW";

export default function Home() {
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [cases, setCases] = useState<DashboardCase[]>([]);
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState<RiskFilter>("ALL");
  const [status, setStatus] = useState("ALL");
  const [createdFrom, setCreatedFrom] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async (activeToken: string) => {
    setLoading(true);
    setError("");
    try { setCases(await getCases(activeToken)); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Unable to load cases"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    const saved = window.localStorage.getItem(TOKEN_KEY) ?? "";
    setToken(saved);
    setTokenInput(saved);
    if (saved) void refresh(saved);
  }, [refresh]);

  const rows = useMemo(() => cases.filter((item) => {
    const matchesQuery = `${item.case_id} ${item.ibu_id}`.toLowerCase().includes(query.toLowerCase());
    const matchesRisk = risk === "ALL" || item.risk_band === risk;
    const matchesStatus = status === "ALL" || item.status.toUpperCase().includes(status);
    const matchesDate = !createdFrom || new Date(item.created_at) >= new Date(createdFrom);
    return matchesQuery && matchesRisk && matchesStatus && matchesDate;
  }).sort((left, right) => {
    const rank = { HIGH: 3, MEDIUM: 2, LOW: 1 };
    return (rank[right.risk_band ?? "LOW"] - rank[left.risk_band ?? "LOW"]) || right.created_at.localeCompare(left.created_at);
  }), [cases, createdFrom, query, risk, status]);

  function saveSession(event: FormEvent) {
    event.preventDefault();
    const next = tokenInput.trim().replace(/^Bearer\s+/i, "");
    window.localStorage.setItem(TOKEN_KEY, next);
    setToken(next);
    void refresh(next);
  }

  function clearSession() {
    window.localStorage.removeItem(TOKEN_KEY);
    setToken(""); setTokenInput(""); setCases([]); setError("");
  }

  const highCount = cases.filter((item) => item.risk_band === "HIGH").length;

  return <main className="reviewShell">
    <aside className="sidebar">
      <div className="brand"><span>TS</span><div><strong>TradeSentry</strong><small>Officer review</small></div></div>
      <nav aria-label="Primary navigation"><a className="active" href="#queue">Case queue <b>{cases.length}</b></a><a href="#decisions">My decisions</a><a href="#audit">Audit trail</a></nav>
      <div className="prototypeNote"><strong>Investigation support only</strong><p>Risk signals are not proof. Every consequential action requires human approval.</p></div>
    </aside>
    <section className="reviewMain">
      <header className="reviewHeader"><div><p className="eyebrow">GIFT City IBU · Secure workspace</p><h1>Human review queue</h1></div>{token ? <button className="sessionButton" onClick={clearSession}>End secure session</button> : <span className="secureState">JWT required</span>}</header>
      <section className="queueHero" id="queue"><div><p className="kicker">Evidence-led decisions</p><h2>Cases requiring your judgment.</h2><p>Review the complete investigation record before approving, holding, escalating, or requesting more evidence.</p></div><div className="queueMetric"><strong>{cases.length}</strong><span>cases in your IBU</span><small>{highCount} high-risk {highCount === 1 ? "case" : "cases"}</small></div></section>
      {!token && <form className="authPanel" onSubmit={saveSession}><div><p className="eyebrow">Authenticated access</p><h3>Start a secure officer session</h3><p>Paste the short-lived JWT issued by your identity provider. It is kept in this browser only.</p></div><label><span>Bearer token</span><input type="password" required value={tokenInput} onChange={(event) => setTokenInput(event.target.value)} autoComplete="off" placeholder="eyJhbGciOi…" /></label><button>Load my IBU cases</button></form>}
      {token && <section className="queuePanel">
        <div className="queueTools"><div><h3>Active cases</h3><span>Sorted by risk and age · tenant scoped by JWT</span></div><div className="filters"><input aria-label="Search cases" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Case ID or IBU" /><select aria-label="Risk filter" value={risk} onChange={(event) => setRisk(event.target.value as RiskFilter)}><option>ALL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select><select aria-label="Status filter" value={status} onChange={(event) => setStatus(event.target.value)}><option>ALL</option><option>HOLD</option><option>READY</option><option>PENDING</option><option>ESCALATED</option></select><input aria-label="Created from" type="date" value={createdFrom} onChange={(event) => setCreatedFrom(event.target.value)} /><button onClick={() => void refresh(token)}>{loading ? "Loading…" : "Refresh"}</button></div></div>
        {error && <p className="inlineError" role="alert">{error}</p>}
        <div className="caseTable" role="table" aria-label="Cases awaiting human review">
          <div className="caseRow caseHead" role="row"><span>Case</span><span>IBU</span><span>Applicant</span><span>Beneficiary</span><span>Amount</span><span>Risk</span><span>Status</span><span>Created</span><span /></div>
          {!loading && rows.length === 0 && <div className="emptyRow">No cases match this secure queue.</div>}
          {rows.map((item) => <div className="caseRow" role="row" key={item.case_id}><strong>{item.case_id}</strong><span>{item.ibu_id}</span><span>{item.applicant ?? "—"}</span><span>{item.beneficiary ?? "—"}</span><span>{item.amount ? `${item.currency ?? ""} ${item.amount}` : "—"}</span><span><i className={`riskDot ${(item.risk_band ?? "LOW").toLowerCase()}`} />{item.risk_band ?? "UNSCORED"}</span><span className="caseStatus">{item.status}</span><span>{new Date(item.created_at).toLocaleDateString()}</span><Link href={`/cases/${encodeURIComponent(item.case_id)}`}>Review <span>→</span></Link></div>)}
        </div>
      </section>}
      <footer>Prototype · Synthetic evidence only · No settlement execution</footer>
    </section>
  </main>;
}
