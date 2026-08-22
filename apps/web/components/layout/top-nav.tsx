"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Bell, Search, ChevronDown, Building2, User, LogOut, HelpCircle } from "lucide-react";
import { useMode } from "@/hooks/use-mode";
import { cn } from "@/lib/utils";
import { searchCases, getCurrentUser, type SearchResult } from "@/services/mock-api";
import { useRouter } from "next/navigation";

export function TopNav() {
  const { mode, toggleMode, isDemo } = useMode();
  const user = getCurrentUser();
  const router = useRouter();

  /* ── Search ── */
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearch = useCallback(async (query: string) => {
    setSearchQuery(query);
    if (query.length < 2) { setSearchResults([]); return; }
    const results = await searchCases(query);
    setSearchResults(results);
  }, []);

  useEffect(() => {
    if (searchOpen && inputRef.current) inputRef.current.focus();
  }, [searchOpen]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  /* ── Alerts ── */
  const [alertOpen, setAlertOpen] = useState(false);
  const unreadAlerts = 4;

  /* ── Profile ── */
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header className="flex items-center h-[56px] px-4 bg-white border-b border-border shrink-0">
      {/* Left — Product identity */}
      <div className="flex items-center gap-3 min-w-0">
        <div>
          <h1 className="text-[14px] font-semibold text-slate-900 leading-tight">
            Trade Finance Intelligence
          </h1>
          <p className="text-[10px] text-slate-500 leading-tight">
            GIFT City IBU Intelligence Layer
          </p>
        </div>
      </div>

      {/* Center — Search */}
      <div className="flex-1 flex justify-center px-6" ref={searchRef}>
        <div className="relative w-full max-w-[480px]">
          <div
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-md border transition-colors cursor-text",
              searchOpen
                ? "border-primary bg-white shadow-sm"
                : "border-slate-200 bg-slate-50 hover:bg-white hover:border-slate-300"
            )}
            onClick={() => setSearchOpen(true)}
          >
            <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              onFocus={() => setSearchOpen(true)}
              placeholder="Search case, LC, B/L, exporter, importer..."
              className="flex-1 bg-transparent text-[13px] text-slate-700 placeholder:text-slate-400 outline-none"
            />
            <kbd className="hidden sm:inline text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded font-mono">
              ⌘K
            </kbd>
          </div>
          {/* Search results dropdown */}
          {searchOpen && searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-50 max-h-[320px] overflow-y-auto">
              {searchResults.map((r) => (
                <button
                  key={r.caseId}
                  className="flex items-center justify-between w-full px-3 py-2.5 text-left hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-0"
                  onClick={() => {
                    router.push(`/cases/${r.caseId}`);
                    setSearchOpen(false);
                    setSearchQuery("");
                    setSearchResults([]);
                  }}
                >
                  <div>
                    <p className="text-[13px] font-medium text-slate-900">{r.title}</p>
                    <p className="text-[11px] text-slate-500">{r.subtitle}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-400">{r.matchField}</span>
                    <span
                      className={cn(
                        "text-[10px] font-semibold px-1.5 py-0.5 rounded",
                        r.riskBand === "HIGH" && "bg-risk-high-bg text-risk-high",
                        r.riskBand === "MEDIUM" && "bg-risk-medium-bg text-risk-medium",
                        r.riskBand === "LOW" && "bg-risk-low-bg text-risk-low"
                      )}
                    >
                      {r.riskBand}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center gap-2">
        {/* Mode toggle */}
        <button
          onClick={toggleMode}
          className={cn(
            "flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wider transition-colors",
            isDemo
              ? "bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100"
              : "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
          )}
        >
          <span className={cn(
            "w-1.5 h-1.5 rounded-full",
            isDemo ? "bg-amber-500" : "bg-emerald-500"
          )} />
          {mode} mode
        </button>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setAlertOpen(!alertOpen)}
            className="relative p-2 rounded-md text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            aria-label="Notifications"
          >
            <Bell className="w-[18px] h-[18px]" />
            {unreadAlerts > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-risk-high text-white text-[9px] font-bold flex items-center justify-center">
                {unreadAlerts}
              </span>
            )}
          </button>
          {alertOpen && (
            <div className="absolute right-0 top-full mt-1 w-[360px] bg-white border border-slate-200 rounded-lg shadow-lg z-50">
              <div className="p-3 border-b border-slate-100">
                <h3 className="text-[13px] font-semibold text-slate-900">Notifications</h3>
              </div>
              <div className="max-h-[400px] overflow-y-auto p-2">
                <div className="px-2 py-2 rounded-md hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-risk-high" />
                    <span className="text-[11px] font-semibold text-risk-high">HIGH RISK</span>
                  </div>
                  <p className="text-[12px] text-slate-700">CASE-2026-00142 elevated to HIGH risk — duplicate financing signal</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">2 min ago</p>
                </div>
                <div className="px-2 py-2 rounded-md hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-risk-high" />
                    <span className="text-[11px] font-semibold text-risk-high">CROSS-IBU</span>
                  </div>
                  <p className="text-[12px] text-slate-700">Cross-IBU match found — 96% network similarity with IBU-GIFT-02</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">2 min ago</p>
                </div>
                <div className="px-2 py-2 rounded-md hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-risk-medium" />
                    <span className="text-[11px] font-semibold text-risk-medium">UCP DISCREPANCY</span>
                  </div>
                  <p className="text-[12px] text-slate-700">Port mismatch: Mundra vs Nhava Sheva — Art. 20(a)(ii)</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">3 min ago</p>
                </div>
                <div className="px-2 py-2 rounded-md hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-risk-high" />
                    <span className="text-[11px] font-semibold text-risk-high">TBML</span>
                  </div>
                  <p className="text-[12px] text-slate-700">CASE-2026-00201 — Polypropylene price 32% above P90 benchmark</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">1 day ago</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* IBU badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 rounded-md">
          <Building2 className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-[11px] font-medium text-slate-700">IBU-GIFT-01</span>
        </div>

        {/* User profile */}
        <div className="relative">
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            className="flex items-center gap-2 px-2 py-1 rounded-md hover:bg-slate-100 transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[11px] font-semibold">
              PS
            </div>
            <div className="hidden lg:block text-left">
              <p className="text-[12px] font-medium text-slate-700 leading-tight">{user.name}</p>
              <p className="text-[10px] text-slate-500 leading-tight">Trade Finance Officer</p>
            </div>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>
          {profileOpen && (
            <div className="absolute right-0 top-full mt-1 w-[200px] bg-white border border-slate-200 rounded-lg shadow-lg z-50">
              <div className="p-3 border-b border-slate-100">
                <p className="text-[12px] font-medium text-slate-900">{user.name}</p>
                <p className="text-[10px] text-slate-500">{user.role.replace(/_/g, " ")}</p>
              </div>
              <div className="p-1">
                <button className="flex items-center gap-2 w-full px-2.5 py-1.5 text-[12px] text-slate-600 hover:bg-slate-50 rounded-md">
                  <User className="w-3.5 h-3.5" /> Profile
                </button>
                <button className="flex items-center gap-2 w-full px-2.5 py-1.5 text-[12px] text-slate-600 hover:bg-slate-50 rounded-md">
                  <HelpCircle className="w-3.5 h-3.5" /> Help
                </button>
                <button className="flex items-center gap-2 w-full px-2.5 py-1.5 text-[12px] text-risk-high hover:bg-red-50 rounded-md">
                  <LogOut className="w-3.5 h-3.5" /> Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
