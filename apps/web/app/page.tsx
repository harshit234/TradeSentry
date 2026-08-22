"use client";

import { useEffect, useState } from "react";
import { KPICards } from "@/features/dashboard/kpi-cards";
import { CasePipeline } from "@/features/dashboard/case-pipeline";
import { RiskOverview } from "@/features/dashboard/risk-overview";
import { PriorityCases } from "@/features/dashboard/priority-cases";
import { getCases, getKPIs, getPipelineCounts, type KPIData } from "@/services/mock-api";
import type { TradeCase, PipelineCounts } from "@/types";

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KPIData | null>(null);
  const [pipeline, setPipeline] = useState<PipelineCounts | null>(null);
  const [cases, setCases] = useState<TradeCase[]>([]);

  useEffect(() => {
    void getKPIs().then(setKpis);
    void getPipelineCounts().then(setPipeline);
    void getCases().then(setCases);
  }, []);

  return (
    <div className="p-6 max-w-[1440px] mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Trade Finance Intelligence</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">
          Pre-settlement documentary compliance and transaction intelligence
        </p>
      </div>

      {/* KPI Cards */}
      <KPICards data={kpis} />

      {/* Case Pipeline */}
      <CasePipeline counts={pipeline} />

      {/* Risk Overview Charts */}
      <RiskOverview />

      {/* Priority Cases Table */}
      <PriorityCases cases={cases} />

      {/* Footer */}
      <footer className="text-center py-4">
        <p className="text-[10px] text-slate-400">
          Prototype · Synthetic evidence only · No settlement execution · Risk scores are investigation signals, not legal findings
        </p>
      </footer>
    </div>
  );
}
