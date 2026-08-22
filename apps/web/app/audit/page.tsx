"use client";

import { useEffect, useState } from "react";
import { getAuditTrail } from "@/services/mock-api";
import type { AuditEntry } from "@/types";
import { formatDate, formatTime, cn } from "@/lib/utils";
import { ClipboardList, Search, Filter } from "lucide-react";

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [search, setSearch] = useState("");
  const [caseFilter, setCaseFilter] = useState("ALL");

  useEffect(() => { void getAuditTrail().then(setEntries); }, []);

  const cases = Array.from(new Set(entries.map((e) => e.caseId)));
  const filtered = entries.filter((e) => {
    const q = search.toLowerCase();
    const matchesSearch = !q || e.action.toLowerCase().includes(q) || e.user.toLowerCase().includes(q) || e.caseId.toLowerCase().includes(q);
    const matchesCase = caseFilter === "ALL" || e.caseId === caseFilter;
    return matchesSearch && matchesCase;
  });

  return (
    <div className="p-6 max-w-[1440px] mx-auto space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Audit Trail</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">
          Complete chronological record of system and officer actions
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 flex-1 max-w-[360px] px-3 py-1.5 bg-white border border-slate-200 rounded-md">
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search actions, users, cases..." className="flex-1 bg-transparent text-[12px] text-slate-700 placeholder:text-slate-400 outline-none" />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select value={caseFilter} onChange={(e) => setCaseFilter(e.target.value)} className="text-[11px] border border-slate-200 rounded-md px-2 py-1.5 bg-white text-slate-700" aria-label="Case filter">
            <option value="ALL">All Cases</option>
            {cases.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <span className="text-[11px] text-slate-500">{filtered.length} entries</span>
      </div>

      {/* Audit table */}
      <div className="bg-white rounded-lg border border-border overflow-hidden">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-border bg-slate-25">
              {["Timestamp", "User", "Role", "IBU", "Case", "Action", "Component", "Result", "Evidence"].map((h) => (
                <th key={h} className="text-left px-3 py-2.5 font-semibold text-slate-500 uppercase text-[10px] tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((e) => (
              <tr key={e.id} className="border-b border-slate-100 hover:bg-slate-25 transition-colors">
                <td className="px-3 py-2.5 font-mono text-[10px] text-slate-500 whitespace-nowrap">{formatTime(e.timestamp)}</td>
                <td className="px-3 py-2.5 text-slate-700">{e.user}</td>
                <td className="px-3 py-2.5 text-[10px] text-slate-500">{e.userRole}</td>
                <td className="px-3 py-2.5 text-[11px] text-slate-600">{e.ibu}</td>
                <td className="px-3 py-2.5 font-semibold text-slate-900 whitespace-nowrap">{e.caseId}</td>
                <td className="px-3 py-2.5 text-slate-700 max-w-[200px] truncate">{e.action}</td>
                <td className="px-3 py-2.5 text-[11px] text-slate-500">{e.component}</td>
                <td className="px-3 py-2.5">
                  <span className={cn(
                    "text-[10px] font-semibold px-1.5 py-0.5 rounded",
                    e.result === "MATCH" && "bg-risk-medium-bg text-risk-medium",
                    e.result === "APPROVE" && "bg-risk-low-bg text-risk-low",
                    !["MATCH", "APPROVE"].includes(e.result) && "bg-slate-100 text-slate-600"
                  )}>
                    {e.result}
                  </span>
                </td>
                <td className="px-3 py-2.5 font-mono text-[10px] text-slate-400">{e.evidenceRef ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
