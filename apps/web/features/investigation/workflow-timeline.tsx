"use client";

import { cn } from "@/lib/utils";
import type { WorkflowStep, WorkflowStatus } from "@/types";
import { Check, AlertTriangle, X, Clock, Loader2, SkipForward } from "lucide-react";

interface WorkflowTimelineProps {
  steps: WorkflowStep[];
  activeStep?: string;
  onStepClick?: (stepId: string) => void;
}

const STATUS_ICON: Record<WorkflowStatus, React.ReactNode> = {
  pending: <Clock className="w-3.5 h-3.5" />,
  processing: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
  completed: <Check className="w-3.5 h-3.5" />,
  review: <AlertTriangle className="w-3.5 h-3.5" />,
  failed: <X className="w-3.5 h-3.5" />,
  skipped: <SkipForward className="w-3.5 h-3.5" />,
};

const STATUS_COLORS: Record<WorkflowStatus, { bg: string; ring: string; text: string; line: string }> = {
  pending: { bg: "bg-slate-100", ring: "ring-slate-200", text: "text-slate-400", line: "bg-slate-200" },
  processing: { bg: "bg-info-bg", ring: "ring-info-border", text: "text-info", line: "bg-info/30" },
  completed: { bg: "bg-risk-low-bg", ring: "ring-risk-low-border", text: "text-risk-low", line: "bg-risk-low" },
  review: { bg: "bg-risk-medium-bg", ring: "ring-risk-medium-border", text: "text-risk-medium", line: "bg-risk-medium" },
  failed: { bg: "bg-risk-high-bg", ring: "ring-risk-high-border", text: "text-risk-high", line: "bg-risk-high" },
  skipped: { bg: "bg-slate-50", ring: "ring-slate-200", text: "text-slate-400", line: "bg-slate-200" },
};

export function WorkflowTimeline({ steps, activeStep, onStepClick }: WorkflowTimelineProps) {
  return (
    <>
      {/* Desktop horizontal timeline */}
      <div className="hidden lg:block">
        <div className="flex items-start">
          {steps.map((step, i) => {
            const colors = STATUS_COLORS[step.status];
            const isActive = activeStep === step.id;
            return (
              <div key={step.id} className="flex items-start flex-1 min-w-0">
                <div className="flex flex-col items-center w-full">
                  {/* Step node */}
                  <button
                    onClick={() => onStepClick?.(step.id)}
                    className={cn(
                      "relative w-8 h-8 rounded-full flex items-center justify-center ring-2 transition-all",
                      colors.bg, colors.ring, colors.text,
                      isActive && "ring-4 scale-110",
                      onStepClick && "cursor-pointer hover:scale-105"
                    )}
                    title={`${step.title}: ${step.status}`}
                    aria-label={`Step ${step.stepNumber}: ${step.title} — ${step.status}`}
                  >
                    {STATUS_ICON[step.status]}
                    {step.status === "processing" && (
                      <span className="absolute inset-0 rounded-full ring-2 ring-info opacity-40 animate-pulse-ring" />
                    )}
                  </button>
                  {/* Label */}
                  <p className={cn(
                    "mt-1.5 text-[9px] font-semibold text-center leading-tight max-w-[80px]",
                    step.status === "pending" ? "text-slate-400" : "text-slate-600"
                  )}>
                    {step.title}
                  </p>
                </div>
                {/* Connecting line */}
                {i < steps.length - 1 && (
                  <div className="flex items-center h-8 flex-1 min-w-[8px] px-0.5">
                    <div className={cn("h-0.5 w-full rounded-full transition-colors", colors.line)} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Mobile/tablet vertical timeline */}
      <div className="lg:hidden space-y-1">
        {steps.map((step, i) => {
          const colors = STATUS_COLORS[step.status];
          const isActive = activeStep === step.id;
          return (
            <div key={step.id} className="flex gap-3">
              <div className="flex flex-col items-center">
                <button
                  onClick={() => onStepClick?.(step.id)}
                  className={cn(
                    "w-7 h-7 rounded-full flex items-center justify-center ring-2 shrink-0",
                    colors.bg, colors.ring, colors.text,
                    isActive && "ring-4"
                  )}
                  aria-label={`Step ${step.stepNumber}: ${step.title} — ${step.status}`}
                >
                  {STATUS_ICON[step.status]}
                </button>
                {i < steps.length - 1 && (
                  <div className={cn("w-0.5 flex-1 min-h-[16px]", colors.line)} />
                )}
              </div>
              <div className="pb-3">
                <p className={cn(
                  "text-[12px] font-semibold leading-tight",
                  step.status === "pending" ? "text-slate-400" : "text-slate-700"
                )}>
                  {step.stepNumber.toString().padStart(2, "0")} {step.title}
                </p>
                {step.summary && step.status !== "pending" && (
                  <p className="text-[11px] text-slate-500 mt-0.5">{step.summary}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
