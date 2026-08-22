import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number | string, currency = "USD"): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateString;
  }
}

export function formatTime(dateString: string): string {
  try {
    return new Date(dateString).toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return dateString;
  }
}

export function formatDateTime(dateString: string): string {
  return `${formatDate(dateString)} ${formatTime(dateString)}`;
}

export function riskColor(band: string): string {
  switch (band?.toUpperCase()) {
    case "HIGH": return "text-risk-high";
    case "MEDIUM": return "text-risk-medium";
    case "LOW": return "text-risk-low";
    default: return "text-slate-400";
  }
}

export function riskBgColor(band: string): string {
  switch (band?.toUpperCase()) {
    case "HIGH": return "bg-risk-high-bg border-risk-high-border";
    case "MEDIUM": return "bg-risk-medium-bg border-risk-medium-border";
    case "LOW": return "bg-risk-low-bg border-risk-low-border";
    default: return "bg-pending-bg border-pending-border";
  }
}
