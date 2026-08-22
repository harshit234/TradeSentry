"use client";

import { Dna } from "lucide-react";

export default function TransactionDNAPage() {
  return (
    <div className="p-6 max-w-[1440px] mx-auto space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Transaction DNA</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">
          Canonical structured trade fingerprints across all cases
        </p>
      </div>
      <div className="bg-white rounded-lg border border-border p-12 text-center">
        <Dna className="w-8 h-8 text-slate-300 mx-auto mb-2" />
        <p className="text-[14px] text-slate-500 mb-1">Transaction DNA browser</p>
        <p className="text-[12px] text-slate-400">
          View Transaction DNA on individual case investigation pages.
        </p>
      </div>
    </div>
  );
}
