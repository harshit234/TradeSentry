"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCases } from "@/services/mock-api";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { TradeCase, RiskBand } from "@/types";
import { cn, formatCurrency } from "@/lib/utils";
import {
  AlertTriangle, ShieldAlert, Network, Anchor, Building, Copy, ArrowRight, Filter,
} from "lucide-react";

export default function RiskPage() {
  const [cases, setCases] = useState<TradeCase[]>([]);
  const [filter, setFilter] = useState<RiskBand | "ALL">("ALL");
  useEffect(() => { void getCases().then(setCases); }, []);

  const high = cases.filter((c) => c.riskBand === "HIGH");
  const medium = cases.filter((c) => c.riskBand === "MEDIUM");
  const signals = [
    { icon: AlertTriangle, label: "UCP Discrepancies", cases: cases.filter((c) => (c.discrepancies?.length ?? 0) > 0) },
    { icon: Copy, label: "Duplicate Financing", cases: cases.filter((c) => c.duplicateSignal) },
    { icon: Network, label: "Cross-IBU Signals", cases: cases.filter((c) => c.crossIBUSignal) },
    { icon: ShieldAlert, label: "TBML Signals", cases: cases.filter((c) => c.fraudInvestigation?.tools.some((t) => t.signal === "SIGNIFICANT_ANOMALY" || t.signal === "ANOMALY")) },
    { icon: Anchor, label: "Vessel Anomalies", cases: cases.filter((c) => c.fraudInvestigation?.tools.some((t) => t.toolName === "vessel_verification" && t.signal === "ANOMALY")) },
  ];

  return (
    <div className="p-6 max-w-[1440px] mx-auto space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Risk & Alerts</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">Monitor risk signals across all active cases</p>
      </div>

      {/* Risk summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className={cn("bg-white rounded-lg border p-4", high.length > 0 ? "border-risk-high-border" : "border-border")}>
          <div className="flex items-center gap-2 mb-2">
            <ShieldAlert className="w-4 h-4 text-risk-high" />
            <span className="text-[11px] font-semibold text-slate-500 uppercase">High Risk</span>
          </div>
          <span className="text-2xl font-bold text-risk-high">{high.length}</span>
          <p className="text-[10px] text-slate-400 mt-1">Cases requiring immediate review</p>
        </div>
        <div className="bg-white rounded-lg border border-border p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-risk-medium" />
            <span className="text-[11px] font-semibold text-slate-500 uppercase">Medium Risk</span>
          </div>
          <span className="text-2xl font-bold text-risk-medium">{medium.length}</span>
          <p className="text-[10px] text-slate-400 mt-1">Cases with review-level findings</p>
        </div>
        <div className="bg-white rounded-lg border border-border p-4">
          <div className="flex items-center gap-2 mb-2">
            <Building className="w-4 h-4 text-slate-400" />
            <span className="text-[11px] font-semibold text-slate-500 uppercase">Total Active</span>
          </div>
          <span className="text-2xl font-bold text-slate-900">{cases.length}</span>
          <p className="text-[10px] text-slate-400 mt-1">Across all IBUs</p>
        </div>
      </div>

      {/* Signal breakdown */}
      <div className="bg-white rounded-lg border border-border">
        <div className="px-5 py-3 border-b border-border flex items-center justify-between">
          <h3 className="text-[13px] font-semibold text-slate-900">Signal Breakdown</h3>
          <div className="flex items-center gap-2">
            <Filter className="w-3 h-3 text-slate-400" />
            <select value={filter} onChange={(e) => setFilter(e.target.value as RiskBand | "ALL")} className="text-[11px] border border-slate-200 rounded px-2 py-1 bg-white" aria-label="Risk filter">
              <option value="ALL">All</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>
        </div>
        <div className="divide-y divide-border">
          {signals.map(({ icon: Icon, label, cases: signalCases }) => (
            <div key={label} className="px-5 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4 text-slate-500" />
                <span className="text-[12px] font-medium text-slate-700">{label}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className={cn(
                  "text-[13px] font-bold",
                  signalCases.length > 0 ? "text-risk-medium" : "text-slate-400"
                )}>
                  {signalCases.length}
                </span>
                {signalCases.length > 0 && (
                  <div className="flex gap-1.5">
                    {signalCases.slice(0, 3).map((c) => (
                      <Link key={c.caseId} href={`/cases/${c.caseId}`} className="text-[10px] font-medium text-primary hover:underline">
                        {c.caseId}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Risk cases list */}
      <div className="bg-white rounded-lg border border-border">
        <div className="px-5 py-3 border-b border-border">
          <h3 className="text-[13px] font-semibold text-slate-900">Cases by Risk</h3>
        </div>
        <div className="divide-y divide-border">
          {cases
            .filter((c) => filter === "ALL" || c.riskBand === filter)
            .sort((a, b) => (b.riskScore ?? 0) - (a.riskScore ?? 0))
            .map((c) => (
              <div key={c.caseId} className="px-5 py-3 flex items-center justify-between hover:bg-slate-25 transition-colors">
                <div className="flex items-center gap-4">
                  <RiskBadge band={c.riskBand} score={c.riskScore} />
                  <div>
                    <span className="text-[12px] font-semibold text-slate-900">{c.caseId}</span>
                    <p className="text-[11px] text-slate-500">{c.exporter} • {c.presentingIBU}</p>
                  </div>
                </div>
                <Link href={`/cases/${c.caseId}`} className="text-[11px] font-medium text-primary hover:underline flex items-center gap-1">
                  Review <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
