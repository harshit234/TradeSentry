"use client";

import { cn } from "@/lib/utils";
import type { WorkflowStatus } from "@/types";
import { Check, AlertTriangle, X, Clock, Loader2, SkipForward } from "lucide-react";

interface StatusBadgeProps {
  status: WorkflowStatus | string;
  label?: string;
  size?: "sm" | "md";
  className?: string;
}

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  pending: {
    icon: <Clock className="w-3 h-3" />,
    color: "bg-slate-100 text-slate-500 border-slate-200",
    label: "Pending",
  },
  processing: {
    icon: <Loader2 className="w-3 h-3 animate-spin" />,
    color: "bg-info-bg text-info border-info-border",
    label: "Processing",
  },
  completed: {
    icon: <Check className="w-3 h-3" />,
    color: "bg-risk-low-bg text-risk-low border-risk-low-border",
    label: "Completed",
  },
  review: {
    icon: <AlertTriangle className="w-3 h-3" />,
    color: "bg-risk-medium-bg text-risk-medium border-risk-medium-border",
    label: "Review",
  },
  failed: {
    icon: <X className="w-3 h-3" />,
    color: "bg-risk-high-bg text-risk-high border-risk-high-border",
    label: "Failed",
  },
  skipped: {
    icon: <SkipForward className="w-3 h-3" />,
    color: "bg-slate-100 text-slate-400 border-slate-200",
    label: "Skipped",
  },
};

export function StatusBadge({ status, label, size = "sm", className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 font-medium rounded-md border",
        config.color,
        size === "sm" ? "text-[10px] px-1.5 py-0.5" : "text-[11px] px-2 py-0.5",
        className
      )}
    >
      {config.icon}
      {label ?? config.label}
    </span>
  );
}
