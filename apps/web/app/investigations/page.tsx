"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCases } from "@/services/mock-api";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { TradeCase } from "@/types";
import { formatCurrency } from "@/lib/utils";
import { Search as SearchIcon, Activity, ArrowRight } from "lucide-react";

export default function InvestigationsPage() {
  const [cases, setCases] = useState<TradeCase[]>([]);
  useEffect(() => { void getCases().then(setCases); }, []);

  const active = cases.filter((c) => ["INVESTIGATION", "COMPLIANCE", "PROCESSING", "REVIEW"].includes(c.status));

  return (
    <div className="p-6 max-w-[1440px] mx-auto space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Investigations</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">Active and recent trade finance investigations</p>
      </div>

      {active.length === 0 ? (
        <div className="bg-white rounded-lg border border-border p-12 text-center">
          <Activity className="w-8 h-8 text-slate-300 mx-auto mb-2" />
          <p className="text-[14px] text-slate-500">No active investigations.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {active.map((c) => (
            <div key={c.caseId} className="bg-white rounded-lg border border-border p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[13px] font-semibold text-slate-900">{c.caseId}</span>
                    <RiskBadge band={c.riskBand} />
                    <span className="text-[10px] font-medium text-info bg-info-bg px-1.5 py-0.5 rounded">{c.status}</span>
                  </div>
                  <p className="text-[12px] text-slate-600">{c.exporter} → {c.importer}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">{c.presentingIBU} • {formatCurrency(c.amount, c.currency)}</p>
                  {c.agentStatus && (
                    <p className="text-[11px] text-slate-500 mt-1">
                      Agent: {c.agentStatus.state} • {c.agentStatus.evidenceFound} evidence found • {c.agentStatus.toolsUsed.length} tools used
                    </p>
                  )}
                </div>
                <Link href={`/cases/${c.caseId}`} className="text-[11px] font-medium text-primary hover:underline flex items-center gap-1">
                  Open investigation <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
