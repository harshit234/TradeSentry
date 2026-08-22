"use client";

import { cn } from "@/lib/utils";
import type { PipelineCounts } from "@/types";
import { ArrowRight } from "lucide-react";

interface CasePipelineProps {
  counts: PipelineCounts | null;
}

const STAGES = [
  { key: "submitted" as const, label: "Submitted", color: "bg-slate-400" },
  { key: "processing" as const, label: "Processing", color: "bg-info" },
  { key: "compliance" as const, label: "Compliance", color: "bg-blue-500" },
  { key: "investigation" as const, label: "Investigation", color: "bg-risk-medium" },
  { key: "review" as const, label: "Review", color: "bg-amber-500" },
  { key: "ready" as const, label: "Ready", color: "bg-risk-low" },
];

export function CasePipeline({ counts }: CasePipelineProps) {
  return (
    <div className="bg-white rounded-lg border border-border p-5">
      <h3 className="text-[13px] font-semibold text-slate-900 mb-4">Case Pipeline</h3>
      <div className="flex items-center gap-1">
        {STAGES.map((stage, i) => {
          const count = counts ? counts[stage.key] : null;
          return (
            <div key={stage.key} className="flex items-center gap-1 flex-1">
              <div className="flex-1 text-center">
                <div className={cn(
                  "mx-auto w-full rounded-lg px-3 py-3 transition-colors",
                  count != null && count > 0 ? "bg-slate-50" : "bg-slate-25"
                )}>
                  {count != null ? (
                    <span className="text-lg font-bold text-slate-900">{count}</span>
                  ) : (
                    <div className="h-6 w-8 mx-auto bg-slate-100 rounded animate-pulse" />
                  )}
                  <p className="text-[10px] font-medium text-slate-500 mt-0.5">{stage.label}</p>
                  <div className={cn("h-1 rounded-full mt-2 mx-auto", stage.color, "opacity-60")} style={{ width: "80%" }} />
                </div>
              </div>
              {i < STAGES.length - 1 && (
                <ArrowRight className="w-3.5 h-3.5 text-slate-300 shrink-0" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
