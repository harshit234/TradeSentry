"use client";

import { BarChart3 } from "lucide-react";

export default function ReportsPage() {
  return (
    <div className="p-6 max-w-[1440px] mx-auto space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Reports</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">
          Compliance, risk, and operational reports
        </p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {[
          { title: "Compliance Summary", desc: "UCP 600 check results across all cases" },
          { title: "Risk Distribution", desc: "Weekly risk band distribution analysis" },
          { title: "Investigation Metrics", desc: "Average review time, tool usage, signal counts" },
        ].map((r) => (
          <div key={r.title} className="bg-white rounded-lg border border-border p-5">
            <BarChart3 className="w-5 h-5 text-slate-400 mb-2" />
            <h3 className="text-[13px] font-semibold text-slate-900 mb-1">{r.title}</h3>
            <p className="text-[11px] text-slate-500">{r.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
