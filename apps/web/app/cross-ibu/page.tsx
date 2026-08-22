"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCases } from "@/services/mock-api";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { TradeCase } from "@/types";
import { cn, formatCurrency } from "@/lib/utils";
import { Network, Check, AlertTriangle, ArrowRight } from "lucide-react";

export default function CrossIBUPage() {
  const [cases, setCases] = useState<TradeCase[]>([]);
  useEffect(() => { void getCases().then(setCases); }, []);

  const withSignals = cases.filter((c) => c.crossIBUSignal || c.duplicateSignal);
  const ibus = ["IBU-GIFT-01", "IBU-GIFT-02", "IBU-GIFT-03"];

  return (
    <div className="p-6 max-w-[1440px] mx-auto space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Cross-IBU Intelligence</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">
          Privacy-preserving intelligence layer across GIFT City IBUs
        </p>
      </div>

      {/* Network Overview */}
      <div className="grid grid-cols-3 gap-4">
        {ibus.map((ibu) => {
          const ibuCases = cases.filter((c) => c.presentingIBU === ibu);
          const signals = ibuCases.filter((c) => c.crossIBUSignal);
          return (
            <div key={ibu} className="bg-white rounded-lg border border-border p-4">
              <div className="flex items-center gap-2 mb-3">
                <Network className="w-4 h-4 text-primary" />
                <h3 className="text-[13px] font-semibold text-slate-900">{ibu}</h3>
              </div>
              <div className="grid grid-cols-2 gap-3 text-[12px]">
                <div><span className="text-slate-500">Cases:</span> <span className="font-semibold">{ibuCases.length}</span></div>
                <div><span className="text-slate-500">Signals:</span> <span className={cn("font-semibold", signals.length > 0 ? "text-risk-medium" : "text-risk-low")}>{signals.length}</span></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Active Signals */}
      <div className="bg-white rounded-lg border border-border">
        <div className="px-5 py-3 border-b border-border">
          <h3 className="text-[13px] font-semibold text-slate-900">Active Cross-IBU Signals</h3>
        </div>
        {withSignals.length === 0 ? (
          <div className="p-8 text-center">
            <Check className="w-6 h-6 text-risk-low mx-auto mb-2" />
            <p className="text-[13px] text-slate-500">No cross-IBU matches found.</p>
            <p className="text-[11px] text-slate-400 mt-1">
              This means no match was identified by the configured checks; it does not establish zero risk.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {withSignals.map((c) => (
              <div key={c.caseId} className="px-5 py-4 hover:bg-slate-25 transition-colors">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-risk-medium" />
                      <span className="text-[13px] font-semibold text-slate-900">{c.caseId}</span>
                      <RiskBadge band={c.riskBand} />
                    </div>
                    <p className="text-[12px] text-slate-600">{c.exporter} → {c.importer}</p>
                    <p className="text-[11px] text-slate-500 mt-1">{c.presentingIBU} • {formatCurrency(c.amount, c.currency)}</p>
                    {c.crossIBUMatches?.[0] && (
                      <div className="mt-2 p-2.5 bg-risk-medium-bg/20 border border-risk-medium-border rounded-md">
                        <p className="text-[11px] text-risk-medium font-semibold">
                          {Math.round(c.crossIBUMatches[0].networkSimilarity * 100)}% network similarity with {c.crossIBUMatches[0].relatedIBU}
                        </p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {c.crossIBUMatches[0].sharedSignals.map((s) => (
                            <span key={s} className="text-[9px] bg-risk-medium-bg text-risk-medium px-1.5 py-0.5 rounded">{s}</span>
                          ))}
                        </div>
                        <p className="text-[10px] text-slate-500 mt-1.5 italic">
                          Shared: permitted intelligence signals only. Raw documents NOT shared.
                        </p>
                      </div>
                    )}
                  </div>
                  <Link href={`/cases/${c.caseId}`} className="text-[11px] font-medium text-primary hover:underline flex items-center gap-1">
                    Open <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Relationship Visualization */}
      <div className="bg-white rounded-lg border border-border p-5">
        <h3 className="text-[13px] font-semibold text-slate-900 mb-4">Relationship Network</h3>
        <div className="flex items-center justify-center py-8">
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-primary/10 border-2 border-primary flex items-center justify-center text-[10px] font-bold text-primary">
                IBU-01
              </div>
              <p className="text-[10px] text-slate-500 mt-1">12 cases</p>
            </div>
            <div className="flex flex-col items-center gap-1">
              <div className="w-24 h-0.5 bg-risk-high relative">
                <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[9px] text-risk-high font-semibold whitespace-nowrap">Related (96%)</span>
              </div>
              <span className="text-[9px] text-slate-400">B/L · Vessel · Voyage</span>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-risk-medium/10 border-2 border-risk-medium flex items-center justify-center text-[10px] font-bold text-risk-medium">
                IBU-02
              </div>
              <p className="text-[10px] text-slate-500 mt-1">7 cases</p>
            </div>
            <div className="flex flex-col items-center gap-1">
              <div className="w-24 h-0.5 bg-slate-200" />
              <span className="text-[9px] text-slate-400">No signals</span>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-slate-100 border-2 border-slate-300 flex items-center justify-center text-[10px] font-bold text-slate-500">
                IBU-03
              </div>
              <p className="text-[10px] text-slate-500 mt-1">5 cases</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
