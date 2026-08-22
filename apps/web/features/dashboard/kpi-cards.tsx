"use client";

import { TrendingUp, TrendingDown, Clock, AlertTriangle, Copy, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import type { KPIData } from "@/services/mock-api";

interface KPICardsProps {
  data: KPIData | null;
}

const CARDS = [
  { key: "activeCases" as const, label: "Active Cases", icon: Activity, trend: "+3", trendUp: true, time: "Today" },
  { key: "awaitingReview" as const, label: "Awaiting Review", icon: Clock, trend: "+2", trendUp: true, time: "Last 4h" },
  { key: "highRisk" as const, label: "High Risk", icon: AlertTriangle, trend: "+1", trendUp: true, time: "This week", highlight: true },
  { key: "duplicateSignals" as const, label: "Duplicate Signals", icon: Copy, trend: "0", trendUp: false, time: "This week" },
  { key: "avgReviewMinutes" as const, label: "Avg Review Time", icon: Clock, trend: "-2 min", trendUp: false, time: "7-day avg", suffix: " min" },
];

export function KPICards({ data }: KPICardsProps) {
  return (
    <div className="grid grid-cols-5 gap-4">
      {CARDS.map((card) => {
        const value = data ? data[card.key] : null;
        return (
          <div
            key={card.key}
            className={cn(
              "bg-white rounded-lg border p-4 transition-shadow hover:shadow-sm",
              card.highlight && value != null && value > 0
                ? "border-risk-high-border"
                : "border-border"
            )}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                {card.label}
              </span>
              <card.icon
                className={cn(
                  "w-4 h-4",
                  card.highlight && value != null && value > 0
                    ? "text-risk-high"
                    : "text-slate-400"
                )}
              />
            </div>
            <div className="flex items-end justify-between">
              <div>
                {value != null ? (
                  <span
                    className={cn(
                      "text-2xl font-bold",
                      card.highlight && value > 0 ? "text-risk-high" : "text-slate-900"
                    )}
                  >
                    {value}{card.suffix ?? ""}
                  </span>
                ) : (
                  <div className="h-8 w-16 bg-slate-100 rounded animate-pulse" />
                )}
              </div>
              <div className="flex items-center gap-1">
                {card.trendUp ? (
                  <TrendingUp className="w-3 h-3 text-risk-medium" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-risk-low" />
                )}
                <span className="text-[10px] text-slate-500">{card.trend}</span>
              </div>
            </div>
            <p className="text-[10px] text-slate-400 mt-1">{card.time}</p>
          </div>
        );
      })}
    </div>
  );
}
