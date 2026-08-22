"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Upload, FileText, X, Check, ArrowLeft, ArrowRight, Building2, Loader2 } from "lucide-react";
import { DOCUMENT_LABELS, type DocumentType, type TradeCase } from "@/types";
import { createCase } from "@/services/mock-api";

const ACCEPTED_TYPES = ["application/pdf", "image/png", "image/jpeg", "image/tiff"];

interface UploadedFile {
  id: string;
  file: File;
  documentType: DocumentType | null;
  status: "pending" | "ready";
}

export default function NewCasePage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [ibu, setIBU] = useState("IBU-GIFT-01");
  const [lcRef, setLCRef] = useState("");
  const [txnRef, setTxnRef] = useState("");
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files).filter((f) =>
      ACCEPTED_TYPES.includes(f.type)
    );
    addFiles(dropped);
  }

  function addFiles(newFiles: File[]) {
    const uploads: UploadedFile[] = newFiles.map((f, i) => ({
      id: `${Date.now()}-${i}`,
      file: f,
      documentType: null,
      status: "ready" as const,
    }));
    setFiles((prev) => [...prev, ...uploads]);
  }

  function removeFile(id: string) {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }

  function setDocType(id: string, type: DocumentType) {
    setFiles((prev) => prev.map((f) => f.id === id ? { ...f, documentType: type } : f));
  }

  const canProceedStep1 = ibu && lcRef.length > 3;
  const canSubmit = files.length > 0;

  return (
    <div className="p-6 max-w-[800px] mx-auto animate-fade-in">
      {/* Header */}
      <div className="mb-6">
        <Link href="/cases" className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-primary mb-3">
          <ArrowLeft className="w-3 h-3" /> Back to cases
        </Link>
        <h1 className="text-xl font-bold text-slate-900">Create Trade Case</h1>
        <p className="text-[13px] text-slate-500 mt-0.5">
          Submit a new trade finance presentation for investigation
        </p>
      </div>

      {/* Steps indicator */}
      <div className="flex items-center gap-3 mb-8">
        {[1, 2].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div className={cn(
              "w-7 h-7 rounded-full flex items-center justify-center text-[12px] font-semibold",
              step >= s ? "bg-primary text-white" : "bg-slate-100 text-slate-400"
            )}>
              {step > s ? <Check className="w-3.5 h-3.5" /> : s}
            </div>
            <span className={cn("text-[12px] font-medium", step >= s ? "text-slate-900" : "text-slate-400")}>
              {s === 1 ? "Case Details" : "Document Upload"}
            </span>
            {s < 2 && <div className="w-12 h-px bg-slate-200" />}
          </div>
        ))}
      </div>

      {/* Step 1 — Case Details */}
      {step === 1 && (
        <div className="bg-white rounded-lg border border-border p-6 space-y-5">
          <div>
            <label className="block text-[12px] font-medium text-slate-700 mb-1.5">
              <Building2 className="w-3.5 h-3.5 inline mr-1" />
              Presenting IBU
            </label>
            <select value={ibu} onChange={(e) => setIBU(e.target.value)} className="w-full px-3 py-2 border border-slate-200 rounded-md text-[13px] bg-white">
              <option>IBU-GIFT-01</option>
              <option>IBU-GIFT-02</option>
              <option>IBU-GIFT-03</option>
            </select>
          </div>
          <div>
            <label className="block text-[12px] font-medium text-slate-700 mb-1.5">LC Reference</label>
            <input type="text" value={lcRef} onChange={(e) => setLCRef(e.target.value)} placeholder="LC-2026-XXXXX" className="w-full px-3 py-2 border border-slate-200 rounded-md text-[13px] placeholder:text-slate-400" />
          </div>
          <div>
            <label className="block text-[12px] font-medium text-slate-700 mb-1.5">Transaction Reference <span className="text-slate-400">(optional)</span></label>
            <input type="text" value={txnRef} onChange={(e) => setTxnRef(e.target.value)} placeholder="TXN-2026-XXXXX" className="w-full px-3 py-2 border border-slate-200 rounded-md text-[13px] placeholder:text-slate-400" />
          </div>
          <div className="flex justify-end pt-2">
            <button
              onClick={() => setStep(2)}
              disabled={!canProceedStep1}
              className={cn(
                "inline-flex items-center gap-1.5 px-5 py-2 rounded-md text-[12px] font-semibold transition-colors",
                canProceedStep1 ? "bg-primary text-white hover:bg-primary-hover" : "bg-slate-100 text-slate-400 cursor-not-allowed"
              )}
            >
              Next — Upload Documents <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Step 2 — Document Upload */}
      {step === 2 && (
        <div className="space-y-5">
          {/* Dropzone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            className={cn(
              "bg-white rounded-lg border-2 border-dashed p-10 text-center transition-colors",
              dragOver ? "border-primary bg-primary/5" : "border-slate-200 hover:border-slate-300"
            )}
          >
            <Upload className="w-8 h-8 text-slate-400 mx-auto mb-3" />
            <p className="text-[14px] font-medium text-slate-700 mb-1">
              Drag and drop trade documents here
            </p>
            <p className="text-[12px] text-slate-500 mb-3">or</p>
            <label className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-white text-[12px] font-semibold rounded-md hover:bg-primary-hover cursor-pointer transition-colors">
              Browse Files
              <input
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                onChange={(e) => e.target.files && addFiles(Array.from(e.target.files))}
                className="hidden"
              />
            </label>
            <p className="text-[10px] text-slate-400 mt-3">
              Accepted: PDF, PNG, JPG, TIFF
            </p>
          </div>

          {/* Expected document types */}
          <div className="bg-white rounded-lg border border-border p-4">
            <h3 className="text-[12px] font-semibold text-slate-700 mb-2">Expected Documents</h3>
            <div className="grid grid-cols-2 gap-1.5">
              {(Object.entries(DOCUMENT_LABELS) as [DocumentType, string][]).map(([type, label]) => {
                const hasDoc = files.some((f) => f.documentType === type);
                return (
                  <div key={type} className="flex items-center gap-2 text-[12px]">
                    {hasDoc ? (
                      <Check className="w-3.5 h-3.5 text-risk-low" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-slate-300" />
                    )}
                    <span className={hasDoc ? "text-slate-700" : "text-slate-500"}>{label}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Uploaded files */}
          {files.length > 0 && (
            <div className="bg-white rounded-lg border border-border divide-y divide-border">
              {files.map((f) => (
                <div key={f.id} className="flex items-center gap-3 px-4 py-3">
                  <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] font-medium text-slate-700 truncate">{f.file.name}</p>
                    <p className="text-[10px] text-slate-400">{(f.file.size / 1024).toFixed(0)} KB</p>
                  </div>
                  <select
                    value={f.documentType ?? ""}
                    onChange={(e) => setDocType(f.id, e.target.value as DocumentType)}
                    className="text-[11px] border border-slate-200 rounded px-2 py-1 bg-white text-slate-600"
                    aria-label="Document type"
                  >
                    <option value="">Select type...</option>
                    {(Object.entries(DOCUMENT_LABELS) as [DocumentType, string][]).map(([type, label]) => (
                      <option key={type} value={type}>{label}</option>
                    ))}
                  </select>
                  <button onClick={() => removeFile(f.id)} className="p-1 text-slate-400 hover:text-risk-high" aria-label="Remove file">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between">
            <button onClick={() => setStep(1)} className="text-[12px] text-slate-600 hover:text-primary">
              <ArrowLeft className="w-3 h-3 inline mr-1" /> Back
            </button>
            <button
              onClick={async () => {
                setIsSubmitting(true);
                const generatedId = `CASE-GIFT-${Date.now().toString().slice(-4)}`;
                const newCase: TradeCase = {
                  caseId: generatedId,
                  lcReference: lcRef || `LC-GIFT-${Date.now().toString().slice(-4)}`,
                  transactionRef: txnRef || `TXN-${Date.now().toString().slice(-4)}`,
                  exporter: "ABC Trading Ltd",
                  importer: "XYZ Imports Pte Ltd",
                  amount: 225000,
                  currency: "USD",
                  presentingIBU: ibu,
                  riskBand: "LOW",
                  riskScore: 18,
                  status: "REVIEW",
                  documents: files.map((f, i) => ({
                    documentId: `DOC-${generatedId}-${i + 1}`,
                    caseId: generatedId,
                    filename: f.file.name,
                    documentType: f.documentType || "commercial_invoice",
                    status: "EXTRACTED",
                    confidence: 0.98,
                    sizeBytes: f.file.size || 185000,
                    uploadedAt: new Date().toISOString(),
                  })),
                  documentCount: files.length,
                  complianceStatus: "PASS",
                  crossIBUSignal: false,
                  duplicateSignal: false,
                  createdAt: new Date().toISOString(),
                  updatedAt: new Date().toISOString(),
                  extraction: {
                    exporter: "ABC Trading Ltd",
                    importer: "XYZ Imports Pte Ltd",
                    lcAmount: "225,000.00",
                    currency: "USD",
                    commodity: "Semi-milled rice",
                    quantity: "500",
                    unit: "MT",
                    blNumber: "BL789456",
                    vessel: "OCEAN STAR",
                    voyageNumber: "V123",
                    route: "Mundra, India → Singapore",
                    loadingPort: "Mundra, India",
                    dischargePort: "Singapore",
                    shipmentDate: new Date().toISOString().split("T")[0],
                    hsCode: "1006.30",
                    incoterms: "CIF",
                    documentsProcessed: files.length,
                    totalDocuments: files.length,
                    averageConfidence: 0.98,
                  },
                  compliance: {
                    totalChecks: 18,
                    pass: 18,
                    review: 0,
                    advisory: 0,
                    fail: 0,
                    findings: [
                      { findingId: "F-001", ucpArticle: "Art. 18(a)(iii)", ruleId: "UCP600-INV-AMOUNT", requirement: "Invoice amount ≤ LC credit amount", actual: "USD 225,000.00 = LC USD 225,000.00", result: "PASS", evidence: "commercial_invoice.pdf & lc.pdf exact match", page: 1 },
                      { findingId: "F-002", ucpArticle: "Art. 14(d)", ruleId: "UCP600-DESC-CONSISTENCY", requirement: "Goods description consistent across all documents", actual: "Semi-milled rice (HS 1006.30)", result: "PASS", evidence: "Exact description matches across LC, Invoice, B/L", page: 1 },
                    ],
                  },
                  discrepancies: [],
                  transactionDNA: {
                    fields: [
                      { label: "Exporter", value: "ABC Trading Ltd", source: "commercial_invoice.pdf", confidence: 0.98 },
                      { label: "Importer", value: "XYZ Imports Pte Ltd", source: "lc.pdf", confidence: 0.98 },
                      { label: "LC Amount", value: "USD 225,000.00", source: "lc.pdf", confidence: 0.99 },
                    ],
                    relationships: { exporter: "ABC Trading Ltd", importer: "XYZ Imports Pte Ltd", lc: lcRef, invoice: "INV-001", bl: "BL789456", vessel: "OCEAN STAR", voyage: "V123" },
                  },
                  duplicateFinancing: { found: false, assessment: "No duplicate financing signals detected across global registry" },
                  crossIBUMatches: [],
                  fraudInvestigation: {
                    agentDecision: "Standard investigation — all 4 fraud/TBML tools returned clean/normal results",
                    tools: [
                      { toolName: "price_benchmark", displayName: "Price Benchmark", status: "completed", result: "NORMAL", evidence: "Semi-milled rice unit price $450/MT is within normal corridor P25-P75 range ($400-$520/MT)", signal: "NORMAL", confidence: 0.96, timestamp: new Date().toISOString() },
                      { toolName: "vessel_verification", displayName: "Vessel Verification", status: "completed", result: "CONSISTENT", evidence: "OCEAN STAR AIS track confirmed at Mundra port", signal: "NORMAL", confidence: 0.95, timestamp: new Date().toISOString() },
                      { toolName: "entity_verification", displayName: "Entity Verification", status: "completed", result: "VERIFIED", evidence: "Both parties verified in good standing", signal: "NORMAL", confidence: 0.97, timestamp: new Date().toISOString() },
                      { toolName: "sanctions_screening", displayName: "Sanctions Screening", status: "completed", result: "NO_MATCH", evidence: "Clean sanctions", signal: "CLEAR", confidence: 0.99, timestamp: new Date().toISOString() },
                    ],
                  },
                  risk: {
                    overallScore: 18,
                    overallBand: "LOW",
                    breakdown: [
                      { category: "Compliance", band: "LOW", score: 0, reason: "18 of 18 UCP checks passed cleanly" },
                      { category: "Duplicate Financing", band: "LOW", score: 0, reason: "No duplicate B/L found" },
                      { category: "Cross-IBU", band: "LOW", score: 0, reason: "Zero cross-IBU conflicts" },
                      { category: "TBML & Fraud", band: "LOW", score: 5, reason: "Price within normal benchmark corridor" },
                      { category: "Vessel & Carrier", band: "LOW", score: 5, reason: "AIS track verified" },
                    ],
                    reasons: [
                      "100% compliance with UCP 600 articles",
                      "Normal price corridor benchmark",
                      "Vessel trajectory verified",
                      "Clean sanctions screening",
                    ],
                    weightsNote: "Prototype weights — all checks cleared",
                  },
                  humanReview: { required: true, aiRecommendation: "Low risk (18/100) — eligible for human officer approval", reason: "All checks passed cleanly; consequential authorization remains pending human review." },
                  evidence: [],
                  agentTimeline: [
                    { timestamp: new Date().toISOString(), agent: "Supervisor Agent", action: "Initiated 11-step investigation" },
                  ],
                  agentStatus: { state: "completed", evidenceFound: 0, toolsUsed: ["UCP 600 Engine", "Price Benchmark", "Vessel Verification", "Sanctions Screening"], recommendation: "Low risk — 100% pass across all stages" },
                };

                await createCase(newCase);
                router.push(`/cases/${newCase.caseId}`);
              }}
              disabled={!canSubmit || isSubmitting}
              className={cn(
                "inline-flex items-center gap-1.5 px-5 py-2.5 rounded-md text-[12px] font-semibold transition-colors shadow-xs",
                canSubmit && !isSubmitting ? "bg-primary text-white hover:bg-primary-hover" : "bg-slate-100 text-slate-400 cursor-not-allowed"
              )}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Ingesting Presentation...
                </>
              ) : (
                <>
                  Start Investigation <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
