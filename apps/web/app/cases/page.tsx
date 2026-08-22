"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCases } from "@/services/mock-api";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { TradeCase, RiskBand, CaseStatus } from "@/types";
import { formatCurrency, formatDate, cn } from "@/lib/utils";
import { Plus, Search, Filter, ArrowRight, ArrowUpDown, Network, Copy } from "lucide-react";

export default function CasesPage() {
  const [cases, setCases] = useState<TradeCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskBand | "ALL">("ALL");
  const [statusFilter, setStatusFilter] = useState<CaseStatus | "ALL">("ALL");
  const [ibuFilter, setIBUFilter] = useState("ALL");

  useEffect(() => {
    void getCases().then((data) => { setCases(data); setLoading(false); });
  }, []);

  const filtered = cases.filter((c) => {
    const q = search.toLowerCase();
    const matchesSearch = !q ||
      c.caseId.toLowerCase().includes(q) ||
      c.lcReference.toLowerCase().includes(q) ||
      c.exporter.toLowerCase().includes(q) ||
      c.importer.toLowerCase().includes(q) ||
      c.extraction?.blNumber?.toLowerCase().includes(q) ||
      c.extraction?.vessel?.toLowerCase().includes(q) ||
      c.presentingIBU.toLowerCase().includes(q);
    const matchesRisk = riskFilter === "ALL" || c.riskBand === riskFilter;
    const matchesStatus = statusFilter === "ALL" || c.status === statusFilter;
    const matchesIBU = ibuFilter === "ALL" || c.presentingIBU === ibuFilter;
    return matchesSearch && matchesRisk && matchesStatus && matchesIBU;
  });

  return (
    <div className="p-6 max-w-[1440px] mx-auto space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Trade Cases</h1>
          <p className="text-[13px] text-slate-500 mt-0.5">
            Review and manage trade finance presentations
          </p>
        </div>
        <Link
          href="/cases/new"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-white text-[12px] font-semibold rounded-md hover:bg-primary-hover transition-colors"
        >
          <Plus className="w-4 h-4" /> New Case
        </Link>
      </div>

      {/* Filters & Search */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-1 min-w-[280px] max-w-[400px] px-3 py-1.5 bg-white border border-slate-200 rounded-md">
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search case ID, LC, B/L, exporter, importer, vessel..."
            className="flex-1 bg-transparent text-[12px] text-slate-700 placeholder:text-slate-400 outline-none"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value as RiskBand | "ALL")} className="text-[11px] border border-slate-200 rounded-md px-2 py-1.5 bg-white text-slate-700" aria-label="Risk filter">
            <option value="ALL">All Risk</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as CaseStatus | "ALL")} className="text-[11px] border border-slate-200 rounded-md px-2 py-1.5 bg-white text-slate-700" aria-label="Status filter">
            <option value="ALL">All Status</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="PROCESSING">Processing</option>
            <option value="COMPLIANCE">Compliance</option>
            <option value="INVESTIGATION">Investigation</option>
            <option value="REVIEW">Review</option>
            <option value="READY">Ready</option>
            <option value="HOLD">Hold</option>
            <option value="ESCALATED">Escalated</option>
          </select>
          <select value={ibuFilter} onChange={(e) => setIBUFilter(e.target.value)} className="text-[11px] border border-slate-200 rounded-md px-2 py-1.5 bg-white text-slate-700" aria-label="IBU filter">
            <option value="ALL">All IBUs</option>
            <option value="IBU-GIFT-01">IBU-GIFT-01</option>
            <option value="IBU-GIFT-02">IBU-GIFT-02</option>
            <option value="IBU-GIFT-03">IBU-GIFT-03</option>
          </select>
        </div>
        <span className="text-[11px] text-slate-500">
          {filtered.length} case{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Cases Table */}
      <div className="bg-white rounded-lg border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border bg-slate-25">
                {["Case ID", "LC Reference", "Exporter", "Importer", "Amount", "IBU", "Docs", "Compliance", "Cross-IBU", "Risk", "Status", "Updated"].map((h) => (
                  <th key={h} className="text-left px-3 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider whitespace-nowrap">
                    <span className="inline-flex items-center gap-1">{h} <ArrowUpDown className="w-2.5 h-2.5 text-slate-300" /></span>
                  </th>
                ))}
                <th className="w-10"></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    {Array.from({ length: 13 }).map((_, j) => (
                      <td key={j} className="px-3 py-3"><div className="h-4 bg-slate-100 rounded animate-pulse w-16" /></td>
                    ))}
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={13} className="text-center py-16 text-slate-400">
                    <p className="text-[14px] font-bold text-slate-700 mb-1">No Trade Cases in Repository</p>
                    <p className="text-[12px] text-slate-500 mb-4 max-w-md mx-auto">
                      All pre-seeded mock cases have been removed. Upload your genuine trade presentations to start real-time documentary compliance and investigation.
                    </p>
                    <div className="flex items-center justify-center gap-3">
                      <Link
                        href="/documents"
                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-white text-[12px] font-semibold rounded-md hover:bg-primary-hover transition-colors shadow-2xs"
                      >
                        Ingest Fresh Documents →
                      </Link>
                      <Link
                        href="/cases/new"
                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-100 text-slate-700 text-[12px] font-semibold rounded-md hover:bg-slate-200 transition-colors"
                      >
                        + Create Presentation
                      </Link>
                    </div>
                  </td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr key={c.caseId} className="border-b border-slate-100 hover:bg-slate-25 transition-colors">
                    <td className="px-3 py-2.5 font-semibold text-slate-900 whitespace-nowrap">{c.caseId}</td>
                    <td className="px-3 py-2.5 font-mono text-[11px] text-slate-600 whitespace-nowrap">{c.lcReference}</td>
                    <td className="px-3 py-2.5 text-slate-700 max-w-[140px] truncate">{c.exporter}</td>
                    <td className="px-3 py-2.5 text-slate-700 max-w-[140px] truncate">{c.importer}</td>
                    <td className="px-3 py-2.5 text-slate-700 whitespace-nowrap">{formatCurrency(c.amount, c.currency)}</td>
                    <td className="px-3 py-2.5 text-[11px] text-slate-600 whitespace-nowrap">{c.presentingIBU}</td>
                    <td className="px-3 py-2.5 text-slate-600">{c.documentCount}</td>
                    <td className="px-3 py-2.5">
                      <span className={cn(
                        "text-[10px] font-semibold px-1.5 py-0.5 rounded",
                        c.complianceStatus === "PASS" && "bg-risk-low-bg text-risk-low",
                        c.complianceStatus === "REVIEW" && "bg-risk-medium-bg text-risk-medium",
                        c.complianceStatus === "FAIL" && "bg-risk-high-bg text-risk-high",
                      )}>
                        {c.complianceStatus ?? "—"}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      {c.crossIBUSignal ? (
                        <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-risk-medium bg-risk-medium-bg px-1.5 py-0.5 rounded">
                          <Network className="w-2.5 h-2.5" /> Signal
                        </span>
                      ) : c.duplicateSignal ? (
                        <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-risk-high bg-risk-high-bg px-1.5 py-0.5 rounded">
                          <Copy className="w-2.5 h-2.5" /> Duplicate
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5"><RiskBadge band={c.riskBand} /></td>
                    <td className="px-3 py-2.5">
                      <span className="text-[11px] font-medium text-slate-600">{c.status}</span>
                    </td>
                    <td className="px-3 py-2.5 text-[11px] text-slate-500 whitespace-nowrap">{formatDate(c.updatedAt)}</td>
                    <td className="px-3 py-2.5">
                      <Link href={`/cases/${c.caseId}`} className="inline-flex items-center gap-0.5 text-primary hover:underline text-[11px] font-medium">
                        Open <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
