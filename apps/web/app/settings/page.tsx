"use client";

import { Settings as SettingsIcon, Shield, Users, Building2, Key } from "lucide-react";

const ROLES = [
  { role: "TRADE_OFFICER", desc: "View cases, review documents, add notes, submit decisions" },
  { role: "COMPLIANCE_OFFICER", desc: "View compliance findings, review UCP checks" },
  { role: "AML_OFFICER", desc: "Investigate high-risk cases, view fraud/TBML evidence" },
  { role: "TRADE_MANAGER", desc: "Assign cases, escalate, review metrics" },
  { role: "RISK_OFFICER", desc: "View risk assessments, manage risk thresholds" },
  { role: "ADMIN", desc: "Configuration, user management, permissions" },
];

export default function SettingsPage() {
  return (
    <div className="p-6 max-w-[1440px] mx-auto space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Settings</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">System configuration and access control</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* RBAC */}
        <div className="bg-white rounded-lg border border-border p-5">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-4 h-4 text-primary" />
            <h3 className="text-[13px] font-semibold text-slate-900">Access Control (RBAC)</h3>
          </div>
          <div className="space-y-2.5">
            {ROLES.map((r) => (
              <div key={r.role} className="flex items-start gap-3 py-2 border-b border-slate-100 last:border-0">
                <Key className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-[12px] font-semibold text-slate-800">{r.role.replace(/_/g, " ")}</p>
                  <p className="text-[11px] text-slate-500">{r.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* IBU Configuration */}
        <div className="bg-white rounded-lg border border-border p-5">
          <div className="flex items-center gap-2 mb-4">
            <Building2 className="w-4 h-4 text-primary" />
            <h3 className="text-[13px] font-semibold text-slate-900">IBU Configuration</h3>
          </div>
          <div className="space-y-2.5">
            {["IBU-GIFT-01", "IBU-GIFT-02", "IBU-GIFT-03"].map((ibu) => (
              <div key={ibu} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-risk-low" />
                  <span className="text-[12px] font-medium text-slate-700">{ibu}</span>
                </div>
                <span className="text-[10px] text-risk-low font-medium bg-risk-low-bg px-2 py-0.5 rounded">Active</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Security notice */}
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
        <p className="text-[11px] text-slate-500">
          <strong className="text-slate-600">Security:</strong> All data access is tenant-isolated by IBU. Cross-IBU intelligence uses privacy-preserving signals only. Raw documents are never shared across IBU boundaries. All consequential actions require authenticated officer approval with audit trail.
        </p>
      </div>
    </div>
  );
}
