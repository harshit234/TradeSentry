"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FolderOpen,
  FileText,
  Search as SearchIcon,
  Network,
  Dna,
  AlertTriangle,
  BarChart3,
  ClipboardList,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: "Overview",
    items: [
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
    ],
  },
  {
    title: "Operations",
    items: [
      { label: "Trade Cases", href: "/cases", icon: FolderOpen },
      { label: "Documents", href: "/documents", icon: FileText },
      { label: "Investigations", href: "/investigations", icon: SearchIcon },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { label: "Cross-IBU Intelligence", href: "/cross-ibu", icon: Network },
      { label: "Transaction DNA", href: "/transaction-dna", icon: Dna },
      { label: "Risk & Alerts", href: "/risk", icon: AlertTriangle },
    ],
  },
  {
    title: "Governance",
    items: [
      { label: "Reports", href: "/reports", icon: BarChart3 },
      { label: "Audit Trail", href: "/audit", icon: ClipboardList },
    ],
  },
  {
    title: "Administration",
    items: [
      { label: "Settings", href: "/settings", icon: Settings },
    ],
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <aside
      className={cn(
        "flex flex-col bg-slate-900 text-slate-400 transition-all duration-200 ease-in-out border-r border-slate-800",
        collapsed ? "w-[60px]" : "w-[240px]"
      )}
    >
      {/* Brand */}
      <div className={cn(
        "flex items-center gap-2.5 px-4 h-[56px] border-b border-slate-800 shrink-0",
        collapsed && "justify-center px-0"
      )}>
        <div className="flex items-center justify-center w-8 h-8 rounded-md bg-primary text-white text-xs font-bold shrink-0">
          <Shield className="w-4 h-4" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="text-[13px] font-semibold text-slate-100 leading-tight truncate">
              Trade Finance
            </p>
            <p className="text-[10px] text-slate-500 leading-tight truncate">
              Intelligence Layer
            </p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2" aria-label="Primary navigation">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="mb-4">
            {!collapsed && (
              <p className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                {group.title}
              </p>
            )}
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={collapsed ? item.label : undefined}
                  className={cn(
                    "flex items-center gap-2.5 px-2.5 py-[7px] rounded-md text-[13px] font-medium transition-colors mb-0.5",
                    active
                      ? "bg-sidebar-active text-sidebar-text-active"
                      : "text-sidebar-text hover:bg-sidebar-hover hover:text-slate-200",
                    collapsed && "justify-center px-0"
                  )}
                >
                  <Icon className={cn("w-[18px] h-[18px] shrink-0", active && "text-blue-400")} />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Prototype notice */}
      {!collapsed && (
        <div className="mx-3 mb-3 p-2.5 rounded-md bg-slate-800/60 border border-slate-700/50">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Investigation support only
          </p>
          <p className="text-[10px] text-slate-500 leading-snug">
            Risk signals are not proof. Every consequential action requires human approval.
          </p>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="flex items-center justify-center h-10 border-t border-slate-800 text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <ChevronLeft className="w-4 h-4" />
        )}
      </button>
    </aside>
  );
}
