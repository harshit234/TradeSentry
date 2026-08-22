"use client";

import Link from "next/link";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { TradeCase } from "@/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import { ArrowRight, Clock } from "lucide-react";

interface PriorityCasesProps {
  cases: TradeCase[];
}

export function PriorityCases({ cases }: PriorityCasesProps) {
  const sorted = [...cases].sort((a, b) => {
    const rank = { HIGH: 3, MEDIUM: 2, LOW: 1 };
    return (rank[b.riskBand ?? "LOW"] - rank[a.riskBand ?? "LOW"]) ||
      new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
  });

  return (
    <div className="bg-white rounded-lg border border-border">
      <div className="flex items-center justify-between px-5 py-3 border-b border-border">
        <h3 className="text-[13px] font-semibold text-slate-900">Priority Cases</h3>
        <Link href="/cases" className="text-[11px] font-medium text-primary hover:underline">
          View all cases →
        </Link>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-border bg-slate-25">
              <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider">Case</th>
              <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider">LC</th>
              <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider">Exporter</th>
              <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider">Importer</th>
              <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider">IBU</th>
              <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider">Risk</th>
              <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider">Status</th>
              <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider">Updated</th>
              <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider"></th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={9} className="text-center py-12 text-slate-400">
                  <p className="text-[13.5px] font-bold text-slate-700 mb-1">No Active Trade Presentations</p>
                  <p className="text-[12px] text-slate-500 mb-4 max-w-md mx-auto">
                    Upload fresh trade documents or create a new presentation to begin live pre-settlement investigation.
                  </p>
                  <div className="flex items-center justify-center gap-2.5">
                    <Link
                      href="/documents"
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-primary text-white text-[11.5px] font-semibold rounded-md hover:bg-primary-hover transition-colors"
                    >
                      Ingest Fresh Documents →
                    </Link>
                    <Link
                      href="/cases/new"
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-100 text-slate-700 text-[11.5px] font-semibold rounded-md hover:bg-slate-200 transition-colors"
                    >
                      + Create Presentation
                    </Link>
                  </div>
                </td>
              </tr>
            ) : (
              sorted.map((c) => (
                <tr key={c.caseId} className="border-b border-slate-100 hover:bg-slate-25 transition-colors">
                  <td className="px-4 py-2.5">
                    <span className="font-semibold text-slate-900">{c.caseId}</span>
                  </td>
                  <td className="px-4 py-2.5 text-slate-600 font-mono text-[11px]">{c.lcReference}</td>
                  <td className="px-4 py-2.5 text-slate-700">{c.exporter}</td>
                  <td className="px-4 py-2.5 text-slate-700">{c.importer}</td>
                  <td className="px-4 py-2.5 text-slate-600 text-[11px]">{c.presentingIBU}</td>
                  <td className="px-4 py-2.5">
                    <RiskBadge band={c.riskBand} />
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="text-[11px] font-medium text-slate-600">{c.status}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-1 text-slate-500">
                      <Clock className="w-3 h-3" />
                      <span className="text-[11px]">{formatDate(c.updatedAt)}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/cases/${c.caseId}`}
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline"
                    >
                      Review <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
