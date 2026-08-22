"use client";

import { cn } from "@/lib/utils";
import type { RiskBand } from "@/types";
import { AlertTriangle, ShieldCheck, ShieldAlert } from "lucide-react";

interface RiskBadgeProps {
  band: RiskBand | string | null;
  score?: number | null;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
  className?: string;
}

export function RiskBadge({ band, score, size = "sm", showIcon = true, className }: RiskBadgeProps) {
  const b = band?.toUpperCase() ?? "UNSCORED";

  const colors: Record<string, string> = {
    HIGH: "bg-risk-high-bg text-risk-high border-risk-high-border",
    MEDIUM: "bg-risk-medium-bg text-risk-medium border-risk-medium-border",
    LOW: "bg-risk-low-bg text-risk-low border-risk-low-border",
    UNSCORED: "bg-pending-bg text-pending border-pending-border",
  };

  const icons: Record<string, React.ReactNode> = {
    HIGH: <ShieldAlert className={cn(size === "sm" ? "w-3 h-3" : "w-4 h-4")} />,
    MEDIUM: <AlertTriangle className={cn(size === "sm" ? "w-3 h-3" : "w-4 h-4")} />,
    LOW: <ShieldCheck className={cn(size === "sm" ? "w-3 h-3" : "w-4 h-4")} />,
    UNSCORED: null,
  };

  const sizeClasses: Record<string, string> = {
    sm: "text-[10px] px-2 py-0.5 gap-1",
    md: "text-[11px] px-2.5 py-1 gap-1.5",
    lg: "text-[12px] px-3 py-1.5 gap-2",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center font-semibold uppercase tracking-wider rounded-md border",
        colors[b] ?? colors.UNSCORED,
        sizeClasses[size],
        className
      )}
    >
      {showIcon && icons[b]}
      {b}
      {score != null && <span className="font-normal opacity-75">{score}/100</span>}
    </span>
  );
}
