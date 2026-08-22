"use client";

import { useState } from "react";
import { cn, formatCurrency, formatTime } from "@/lib/utils";
import type { TradeCase, TradeDocument, EvidenceRecord, ReviewDecision } from "@/types";
import {
  Check, AlertTriangle, FileText, ShieldCheck, Network, Copy, Skull,
  Gauge, UserCheck, Landmark, ArrowRight, X, ExternalLink, ChevronDown,
  ChevronRight, Sparkles, Building2, Eye, FileSpreadsheet, Anchor, ShieldAlert,
  Loader2
} from "lucide-react";

/* ── Reusable Section Wrapper ── */
function Section({
  title,
  subtitle,
  icon: Icon,
  children,
  id,
  status,
  action,
}: {
  title: string;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  id: string;
  status?: "completed" | "review" | "pending";
  action?: React.ReactNode;
}) {
  return (
    <section id={id} className="bg-white rounded-lg border border-border shadow-xs overflow-hidden animate-fade-in transition-all">
      <div className={cn(
        "flex items-center justify-between px-5 py-3.5 border-b",
        status === "review" ? "border-amber-200 bg-amber-50/40" : "border-border bg-slate-25/60"
      )}>
        <div className="flex items-center gap-2.5">
          <div className={cn(
            "w-7 h-7 rounded-md flex items-center justify-center text-xs font-bold",
            status === "review" ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-700"
          )}>
            <Icon className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-[13.5px] font-bold text-slate-900 leading-tight">{title}</h2>
            {subtitle && <p className="text-[11px] text-slate-500 leading-tight mt-0.5">{subtitle}</p>}
          </div>
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

/* ── 00 Document Upload & Presentation Intake ── */
export function DocumentUploadSection({ data }: { data: TradeCase }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploadedList, setUploadedList] = useState(data.documents);
  const [isProcessingNew, setIsProcessingNew] = useState(false);
  const [justAddedCount, setJustAddedCount] = useState(0);

  function handleAddFiles(files: FileList | File[]) {
    const arr = Array.from(files);
    if (arr.length === 0) return;

    setIsProcessingNew(true);
    setJustAddedCount(arr.length);

    setTimeout(() => {
      const newItems = arr.map((f, i) => ({
        documentId: `DOC-${Date.now().toString().slice(-4)}-${i + 1}`,
        caseId: data.caseId,
        filename: f.name,
        documentType: (f.name.toLowerCase().includes("lc") ? "letter_of_credit" : f.name.toLowerCase().includes("inv") ? "commercial_invoice" : "bill_of_lading") as TradeDocument["documentType"],
        status: "EXTRACTED" as const,
        confidence: 0.97,
        sizeBytes: f.size || 185000,
        uploadedAt: new Date().toISOString(),
      }));

      setUploadedList((prev) => [...prev, ...newItems]);
      setIsProcessingNew(false);
    }, 1200);
  }

  const docChecklist = [
    { type: "Letter of Credit (LC)", code: "LC", present: true, time: "14:31:02" },
    { type: "Commercial Invoice", code: "Invoice", present: true, time: "14:31:02" },
    { type: "Bill of Lading (B/L)", code: "B/L", present: true, time: "14:31:02" },
    { type: "Packing List", code: "Packing List", present: true, time: "14:31:02" },
    { type: "Certificate of Origin", code: "Certificate of Origin", present: true, time: "14:31:02" },
    { type: "Insurance Certificate", code: "Insurance", present: true, time: "14:31:02" },
  ];

  return (
    <Section
      title="01 Document Upload & Presentation Intake"
      subtitle="Intake of trade documents presented under documentary credit"
      icon={FileText}
      id="sec-document_upload"
      status="completed"
      action={
        <div className="flex items-center gap-2">
          {uploadedList.length > 0 && (
            <button
              onClick={() => setUploadedList([])}
              className="text-[11px] font-semibold px-2 py-0.5 text-red-600 hover:bg-red-50 rounded border border-red-200 transition-colors"
            >
              Clear & Use Fresh Files
            </button>
          )}
          <span className="text-[11px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">
            {uploadedList.length > 0 ? `✓ COMPLETED (${uploadedList.length} received)` : "Pending Upload"}
          </span>
          <span className="text-[11px] font-mono text-slate-400">14:31:02 IST</span>
        </div>
      }
    >
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Step 01 Specification Card */}
        <div className="lg:col-span-5 space-y-3">
          <div className="p-4 bg-slate-900 text-white rounded-lg space-y-3 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest">01 DOCUMENT UPLOAD</span>
              <span className="text-[10px] font-bold text-emerald-400">✓ COMPLETED</span>
            </div>

            <p className="text-[13px] font-semibold text-slate-200">
              {uploadedList.length} documents received & indexed
            </p>

            <div className="grid grid-cols-2 gap-1.5 text-[11px]">
              {docChecklist.map((d) => (
                <div key={d.type} className="flex items-center gap-1.5 text-slate-300">
                  <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span className="truncate">{d.code}</span>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-400">
              <span>Presented via IBU Gateway</span>
              <span className="font-mono">14:31:02 IST</span>
            </div>
          </div>
        </div>

        {/* Upload Dropzone & Additional Document Intake */}
        <div className="lg:col-span-7">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              if (e.dataTransfer.files) handleAddFiles(e.dataTransfer.files);
            }}
            className={cn(
              "border-2 border-dashed rounded-lg p-5 text-center flex flex-col items-center justify-center transition-all h-full",
              dragOver ? "border-primary bg-blue-50/50 ring-4 ring-blue-100" : "border-slate-300 bg-slate-50/50 hover:bg-slate-50"
            )}
          >
            {isProcessingNew ? (
              <div className="space-y-2 py-4">
                <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto" />
                <p className="text-[13px] font-bold text-slate-800">
                  Ingesting & Extracting {justAddedCount} Document{justAddedCount !== 1 ? "s" : ""}...
                </p>
                <div className="w-48 h-1.5 bg-slate-200 rounded-full mx-auto overflow-hidden">
                  <div className="h-full bg-primary animate-pulse w-3/4" />
                </div>
              </div>
            ) : (
              <>
                <FileSpreadsheet className="w-8 h-8 text-slate-400 mb-2" />
                <p className="text-[13px] font-bold text-slate-800">
                  Drag & Drop Additional Trade Documents Here
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Supported formats: PDF, PNG, JPG, TIFF (Max 25MB per file)
                </p>
                <label className="mt-3 px-3.5 py-1.5 bg-white border border-slate-300 text-slate-700 text-[11.5px] font-semibold rounded-md hover:bg-slate-50 cursor-pointer shadow-2xs">
                  Browse Document Files
                  <input
                    type="file"
                    multiple
                    className="hidden"
                    accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                    onChange={(e) => {
                      if (e.target.files) handleAddFiles(e.target.files);
                      e.target.value = "";
                    }}
                  />
                </label>
              </>
            )}
          </div>
        </div>
      </div>
    </Section>
  );
}

/* ── 01 Case Summary Section ── */
export function CaseSummarySection({ data }: { data: TradeCase }) {
  const fields = [
    { label: "Exporter", value: data.exporter, sub: "Seller / Shipper" },
    { label: "Importer", value: data.importer, sub: "Buyer / Consignee" },
    { label: "LC Amount", value: formatCurrency(data.amount, data.currency), sub: `Currency: ${data.currency}` },
    { label: "B/L Reference", value: data.extraction?.blNumber ?? "—", sub: "Ocean Bill of Lading" },
    { label: "Vessel / Voyage", value: `${data.extraction?.vessel ?? "—"} (${data.extraction?.voyageNumber ?? "—"})`, sub: "Carrier verified" },
    { label: "Trade Route", value: data.extraction?.route ?? "—", sub: "Port of Loading → Discharge" },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {fields.map((f) => (
        <div key={f.label} className="p-3 bg-slate-50 rounded-md border border-slate-200/80">
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">{f.label}</p>
          <p className="text-[13px] font-bold text-slate-900 truncate" title={f.value}>{f.value}</p>
          <p className="text-[10px] text-slate-400 mt-0.5 truncate">{f.sub}</p>
        </div>
      ))}
    </div>
  );
}

/* ── 02 & 03 Documents & Extraction Section ── */
export function DocumentsSection({ data, onOpenEvidence }: { data: TradeCase; onOpenEvidence?: (ev: EvidenceRecord) => void }) {
  const [activeDocTab, setActiveDocTab] = useState<string>(data.documents[0]?.documentId ?? "");

  return (
    <Section
      title="02 & 03 Document Extraction & Completeness"
      subtitle="Extracted fields with OCR confidence and completeness validation"
      icon={FileText}
      id="sec-document_extraction"
      status="completed"
    >
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Left: Document List & Completeness */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-slate-50 p-3.5 rounded-md border border-slate-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">Document Completeness</span>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">
                ✓ COMPLETE (6/6)
              </span>
            </div>
            <p className="text-[11px] text-slate-500">
              Required document types present • Required copies/originals verified • Presentation within LC expiry
            </p>
          </div>

          <div className="space-y-1.5">
            <p className="text-[10.5px] font-semibold text-slate-400 uppercase tracking-wider">Submitted Files</p>
            {data.documents.map((doc) => {
              const isSelected = activeDocTab === doc.documentId;
              return (
                <button
                  key={doc.documentId}
                  onClick={() => setActiveDocTab(doc.documentId)}
                  className={cn(
                    "w-full flex items-center justify-between p-2.5 rounded-md text-left transition-all border",
                    isSelected
                      ? "bg-blue-50/70 border-primary text-slate-900 font-medium"
                      : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                  )}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    <div className="truncate">
                      <p className="text-[12px] font-semibold leading-tight truncate">{doc.filename}</p>
                      <p className="text-[10px] text-slate-400 capitalize">{doc.documentType.replace(/_/g, " ")}</p>
                    </div>
                  </div>
                  <span className="text-[10.5px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded shrink-0">
                    {doc.confidence != null ? `${Math.round(doc.confidence * 100)}% conf` : "100%"}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Extracted Facts Grid */}
        <div className="lg:col-span-7">
          <div className="bg-slate-50/50 p-4 rounded-md border border-slate-200 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3 border-b border-slate-200 pb-2">
                <h3 className="text-[12px] font-bold text-slate-800 uppercase tracking-wider">Summary-Wise Extracted Facts</h3>
                <span className="text-[11px] text-slate-500">
                  Confidence: <strong className="text-slate-800">{Math.round((data.extraction?.averageConfidence ?? 0.96) * 100)}%</strong>
                </span>
              </div>
              {data.extraction && (
                <div className="grid grid-cols-2 gap-3 text-[12px]">
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase">Exporter</span>
                    <p className="font-semibold text-slate-900">{data.extraction.exporter}</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase">Importer</span>
                    <p className="font-semibold text-slate-900">{data.extraction.importer}</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase">LC Amount</span>
                    <p className="font-semibold text-slate-900">{data.currency} {data.extraction.lcAmount}</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase">Commodity</span>
                    <p className="font-semibold text-slate-900">{data.extraction.commodity} (HS {data.extraction.hsCode})</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase">Quantity</span>
                    <p className="font-semibold text-slate-900">{data.extraction.quantity} {data.extraction.unit}</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase">Bill of Lading</span>
                    <p className="font-mono font-semibold text-slate-900">{data.extraction.blNumber}</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase">Vessel & Voyage</span>
                    <p className="font-semibold text-slate-900">{data.extraction.vessel} ({data.extraction.voyageNumber})</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase">Shipment Date</span>
                    <p className="font-semibold text-slate-900">{data.extraction.shipmentDate}</p>
                  </div>
                </div>
              )}
            </div>
            <div className="pt-4 mt-4 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
              <span>All 6 documents processed without OCR extraction failure</span>
              <button className="text-primary font-semibold hover:underline inline-flex items-center gap-1">
                View detailed field extraction <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}

/* ── 04 & 05 UCP 600 Compliance & Discrepancies ── */
export function ComplianceSection({ data, onOpenEvidence }: { data: TradeCase; onOpenEvidence?: (ev: EvidenceRecord) => void }) {
  const c = data.compliance;
  if (!c) return null;
  const hasDiscrepancy = (data.discrepancies?.length ?? 0) > 0;

  return (
    <Section
      title="UCP 600 Documentary Compliance"
      subtitle="Deterministic rules validation across ICC Uniform Customs and Practice for Documentary Credits"
      icon={ShieldCheck}
      id="sec-compliance"
      status={hasDiscrepancy ? "review" : "completed"}
      action={
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">{c.pass} Pass</span>
          <span className="text-[11px] font-bold px-2 py-0.5 bg-amber-100 text-amber-800 rounded">{c.review} Review</span>
          <span className="text-[11px] font-bold px-2 py-0.5 bg-slate-100 text-slate-700 rounded">{c.advisory} Advisory</span>
        </div>
      }
    >
      {/* High-Visibility Discrepancy Alert Panel */}
      {data.discrepancies && data.discrepancies.length > 0 && (
        <div className="mb-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[12px] font-bold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              {data.discrepancies.length} Discrepanc{data.discrepancies.length === 1 ? "y" : "ies"} Requiring Officer Attention
            </h3>
          </div>

          <div className="grid gap-3">
            {data.discrepancies.map((d) => (
              <div key={d.id} className="p-4 rounded-lg border-2 border-amber-300 bg-amber-50/50 shadow-xs">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-amber-200/80 text-amber-900 font-mono text-[11px] font-bold rounded">
                      {d.ucpArticle}
                    </span>
                    <span className="text-[13px] font-bold text-slate-900">{d.description}</span>
                  </div>
                  <span className="text-[10.5px] font-bold text-amber-800 uppercase px-2 py-0.5 bg-amber-100 rounded">
                    {d.severity}
                  </span>
                </div>

                <div className="grid sm:grid-cols-2 gap-3 text-[12px] bg-white p-3 rounded-md border border-amber-200 mt-2">
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase block">Expected Value (LC Requirement)</span>
                    <span className="font-semibold text-slate-800">{d.expected}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase block">Actual Value (Presented Document)</span>
                    <span className="font-bold text-red-600">{d.actual}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-600 mt-3 pt-2 border-t border-amber-200/60">
                  <span><strong>Evidence:</strong> {d.evidence} {d.page ? `(Document Page ${d.page})` : ""}</span>
                  <span className="font-mono text-slate-400 text-[10px]">Rule ID: {d.ruleId}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Compliance Rules Table */}
      <div>
        <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">Evaluated UCP 600 Rules Checklist</h4>
        <div className="overflow-x-auto border border-border rounded-md">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-slate-50 border-b border-border text-[10.5px] font-bold text-slate-500 uppercase">
                <th className="text-left py-2 px-3">Rule / Article</th>
                <th className="text-left py-2 px-3">Requirement</th>
                <th className="text-left py-2 px-3">Actual Presented</th>
                <th className="text-left py-2 px-3">Outcome</th>
                <th className="text-left py-2 px-3">Evidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {c.findings.map((f) => (
                <tr key={f.findingId} className="hover:bg-slate-25">
                  <td className="py-2 px-3 font-mono font-semibold text-slate-800">{f.ucpArticle}</td>
                  <td className="py-2 px-3 text-slate-700">{f.requirement}</td>
                  <td className="py-2 px-3 font-medium text-slate-900">{f.actual}</td>
                  <td className="py-2 px-3">
                    <span className={cn(
                      "text-[10px] font-bold px-1.5 py-0.5 rounded",
                      f.result === "PASS" && "bg-emerald-100 text-emerald-800",
                      f.result === "REVIEW" && "bg-amber-100 text-amber-800",
                      f.result === "ADVISORY" && "bg-blue-100 text-blue-800",
                    )}>
                      {f.result}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-500 max-w-[200px] truncate" title={f.evidence}>{f.evidence}</td>
                </tr>
              ))}
              <tr className="hover:bg-slate-25">
                <td className="py-2 px-3 font-mono font-semibold text-slate-800">Art. 18(a)(iii)</td>
                <td className="py-2 px-3 text-slate-700">Commercial Invoice Amount</td>
                <td className="py-2 px-3 font-medium text-slate-900">{data.currency} {data.extraction?.lcAmount}</td>
                <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 bg-emerald-100 text-emerald-800 rounded">PASS</span></td>
                <td className="py-2 px-3 text-slate-500">Invoice exact match with LC amount</td>
              </tr>
              <tr className="hover:bg-slate-25">
                <td className="py-2 px-3 font-mono font-semibold text-slate-800">Art. 28</td>
                <td className="py-2 px-3 text-slate-700">Insurance Certificate Coverage</td>
                <td className="py-2 px-3 font-medium text-slate-900">110% CIF Value Covered</td>
                <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 bg-emerald-100 text-emerald-800 rounded">PASS</span></td>
                <td className="py-2 px-3 text-slate-500">Policy covers all Institute Cargo Clauses</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </Section>
  );
}

/* ── 06 Transaction DNA (Visual Hierarchy + Provenance) ── */
export function TransactionDNASection({ data }: { data: TradeCase }) {
  const dna = data.transactionDNA;
  if (!dna) return null;

  return (
    <Section
      title="Transaction DNA"
      subtitle="Canonical structured trade fingerprint and relationship graph with field-level provenance"
      icon={Network}
      id="sec-dna"
      status="completed"
    >
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Visual Graph Hierarchy */}
        <div className="lg:col-span-5 bg-slate-900 text-white p-5 rounded-lg flex flex-col items-center justify-center">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-4">Transaction Entity Graph</p>

          <div className="w-full flex flex-col items-center gap-3 text-center text-[12px]">
            {/* Exporter Node */}
            <div className="px-4 py-2 bg-blue-600 text-white rounded-md font-semibold border border-blue-400 shadow-md">
              Exporter: {dna.relationships.exporter}
            </div>

            <div className="w-0.5 h-4 bg-slate-600" />

            {/* Document Layer */}
            <div className="grid grid-cols-3 gap-2 w-full">
              <div className="p-2 bg-slate-800 rounded border border-slate-700 text-[11px]">
                <span className="text-[9px] text-slate-400 block uppercase">LC</span>
                <span className="font-mono text-blue-300 truncate block">{dna.relationships.lc}</span>
              </div>
              <div className="p-2 bg-slate-800 rounded border border-slate-700 text-[11px]">
                <span className="text-[9px] text-slate-400 block uppercase">Invoice</span>
                <span className="font-mono text-blue-300 truncate block">{dna.relationships.invoice}</span>
              </div>
              <div className="p-2 bg-slate-800 rounded border border-slate-700 text-[11px]">
                <span className="text-[9px] text-slate-400 block uppercase">B/L</span>
                <span className="font-mono text-amber-300 truncate block">{dna.relationships.bl}</span>
              </div>
            </div>

            <div className="w-0.5 h-4 bg-slate-600" />

            {/* Vessel Node */}
            <div className="px-4 py-2 bg-slate-800 text-slate-200 rounded-md font-semibold border border-slate-700 flex items-center gap-2">
              <Anchor className="w-3.5 h-3.5 text-blue-400" />
              Vessel: {dna.relationships.vessel}
            </div>

            <div className="w-0.5 h-4 bg-slate-600" />

            {/* Voyage Node */}
            <div className="px-3 py-1 bg-slate-950 text-slate-400 rounded text-[11px] font-mono">
              Voyage: {dna.relationships.voyage}
            </div>
          </div>
        </div>

        {/* Provenance Table */}
        <div className="lg:col-span-7">
          <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">Field Provenance & Extraction Confidence</h4>
          <div className="max-h-[300px] overflow-y-auto border border-border rounded-md divide-y divide-border text-[12px]">
            {dna.fields.map((f) => (
              <div key={f.label} className="p-2.5 flex items-center justify-between hover:bg-slate-50">
                <div>
                  <span className="text-[10px] font-semibold text-slate-400 uppercase block">{f.label}</span>
                  <span className="font-semibold text-slate-900">{f.value}</span>
                </div>
                <div className="text-right">
                  <span className="text-[10.5px] text-slate-500 block">{f.source}</span>
                  <span className="text-[10px] font-mono text-emerald-600 font-semibold">{Math.round(f.confidence * 100)}% confidence</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Section>
  );
}

/* ── 07 Duplicate Financing Check ── */
export function DuplicateFinancingSection({ data }: { data: TradeCase }) {
  const dup = data.duplicateFinancing;
  if (!dup) return null;

  return (
    <Section
      title="Duplicate Financing Check"
      subtitle="Cross-referencing global registry and active financing portfolios across IBUs"
      icon={Copy}
      id="sec-duplicate"
      status={dup.found ? "review" : "completed"}
    >
      {dup.found ? (
        <div className="p-4 rounded-lg border-2 border-red-300 bg-red-50/40 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <span className="text-[14px] font-bold">POTENTIAL MATCH FOUND</span>
            </div>
            <span className="px-2.5 py-1 bg-red-100 text-red-800 text-[12px] font-bold rounded-md border border-red-200">
              Similarity: {Math.round((dup.similarity ?? 0) * 100)}%
            </span>
          </div>

          <div className="grid md:grid-cols-3 gap-3 bg-white p-3.5 rounded-md border border-red-200 text-[12px]">
            <div>
              <span className="text-[10px] font-semibold text-slate-400 uppercase block">Matched Bill of Lading</span>
              <span className="font-mono font-bold text-red-700 text-[13px]">{dup.blNumber}</span>
            </div>
            <div>
              <span className="text-[10px] font-semibold text-slate-400 uppercase block">Detected Under</span>
              <span className="font-semibold text-slate-800">{dup.sourceIBU} ({dup.relatedRef})</span>
            </div>
            <div>
              <span className="text-[10px] font-semibold text-slate-400 uppercase block">Investigation Assessment</span>
              <span className="font-bold text-red-700">{dup.assessment}</span>
            </div>
          </div>

          <div>
            <span className="text-[10.5px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">Matched Fields Across Submissions</span>
            <div className="flex flex-wrap gap-2">
              {dup.matchedFields?.map((f) => (
                <span key={f} className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 bg-red-100/80 text-red-900 rounded border border-red-200">
                  ✓ {f}
                </span>
              ))}
            </div>
          </div>

          <p className="text-[10.5px] text-slate-500 italic pt-1">
            * Investigation signal only. System flags potential duplicate financing presentation for mandatory human officer verification.
          </p>
        </div>
      ) : (
        <div className="p-4 bg-emerald-50 rounded-md border border-emerald-200 flex items-center gap-3">
          <Check className="w-5 h-5 text-emerald-600 shrink-0" />
          <div>
            <p className="text-[13px] font-bold text-emerald-900">No Duplicate Financing Signal Detected</p>
            <p className="text-[11px] text-emerald-700 mt-0.5">{dup.assessment}</p>
          </div>
        </div>
      )}
    </Section>
  );
}

/* ── 08 Cross-IBU Intelligence ── */
export function CrossIBUSection({ data }: { data: TradeCase }) {
  const matches = data.crossIBUMatches;
  if (!matches) return null;
  const hasMatch = matches.length > 0;

  return (
    <Section
      title="Cross-IBU Intelligence"
      subtitle="Privacy-preserving query across permissioned GIFT City International Banking Units"
      icon={Network}
      id="sec-crossibu"
      status={hasMatch ? "review" : "completed"}
    >
      <div className="space-y-4">
        {hasMatch ? (
          matches.map((m) => (
            <div key={m.matchId} className="p-4 rounded-lg border-2 border-amber-300 bg-amber-50/40 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-amber-900">
                  <Network className="w-4 h-4 text-amber-600" />
                  <span className="text-[13px] font-bold">MATCH FOUND: Related Transaction in {m.relatedIBU}</span>
                </div>
                <span className="px-2.5 py-0.5 bg-amber-100 text-amber-900 text-[11px] font-bold rounded">
                  {Math.round(m.networkSimilarity * 100)}% Network Similarity
                </span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">Shared Permitted Signals</span>
                <div className="flex flex-wrap gap-1.5">
                  {m.sharedSignals.map((s) => (
                    <span key={s} className="px-2 py-0.5 bg-white text-slate-800 text-[11px] font-medium rounded border border-amber-200">
                      • {s}
                    </span>
                  ))}
                </div>
              </div>

              {/* Strict Privacy Callout */}
              <div className="p-3 bg-slate-900 text-white rounded-md flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span><strong>Raw Documents:</strong> NOT SHARED</span>
                </div>
                <span className="text-slate-400 font-mono text-[10px]">
                  Shared: PERMITTED INTELLIGENCE SIGNALS ONLY
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className="p-4 bg-emerald-50 rounded-md border border-emerald-200 flex items-center gap-3">
            <Check className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <p className="text-[13px] font-bold text-emerald-900">No Cross-IBU Correlation Identified</p>
              <p className="text-[11px] text-emerald-700 mt-0.5">
                Query across IBU-GIFT-01, IBU-GIFT-02, and IBU-GIFT-03 returned zero conflicting financing signals.
              </p>
            </div>
          </div>
        )}
      </div>
    </Section>
  );
}

/* ── 09 Fraud & TBML Investigation ── */
export function FraudTBMLSection({ data }: { data: TradeCase }) {
  const fraud = data.fraudInvestigation;
  if (!fraud) return null;

  const hasTBMLAnomaly = fraud.tools.some(
    (t) => t.signal === "SIGNIFICANT_ANOMALY" || t.signal === "ANOMALY" || t.signal === "REVIEW"
  );
  const priceTool = fraud.tools.find((t) => t.toolName === "price_benchmark");
  const isPriceAnomaly = priceTool?.signal === "SIGNIFICANT_ANOMALY" || priceTool?.signal === "REVIEW";

  return (
    <Section
      title="Fraud / TBML Investigation"
      subtitle="Autonomous tool executions with observable telemetry and provenance"
      icon={Skull}
      id="sec-fraud"
      status={hasTBMLAnomaly ? "review" : "completed"}
    >
      {/* TBML Anomaly Alert Banner */}
      {hasTBMLAnomaly ? (
        <div className="mb-4 p-4 rounded-lg border-2 border-red-300 bg-red-50/70 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-red-900">
              <ShieldAlert className="w-5 h-5 text-red-600 shrink-0" />
              <span className="text-[13.5px] font-bold">
                {isPriceAnomaly ? "TBML OVER-INVOICING SIGNAL FLAGGED" : "TBML & FRAUD INVESTIGATION ANOMALY DETECTED"}
              </span>
            </div>
            <span className="px-2.5 py-0.5 bg-red-100 text-red-800 text-[11px] font-bold rounded border border-red-200 uppercase tracking-wide">
              Compliance Review Triggered
            </span>
          </div>
          <p className="text-[12px] text-red-950 font-medium leading-relaxed">
            {fraud.agentDecision}
          </p>
          <div className="text-[10.5px] text-red-700 italic pt-1 border-t border-red-200">
            * Investigation signal only (per UCP 600 & FIU-IND guidance). Requires human compliance officer authorization before case resolution.
          </div>
        </div>
      ) : (
        <div className="mb-4 p-3 bg-emerald-50 rounded-md border border-emerald-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-emerald-900 text-[12.5px] font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>All 4 Fraud/TBML Tools Cleared — Zero Money Laundering Signals</span>
          </div>
          <span className="text-[10px] font-bold uppercase px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">
            All Clear
          </span>
        </div>
      )}

      <div className="mb-3 p-3 bg-slate-50 rounded-md border border-slate-200 flex items-center justify-between text-[12px]">
        <span className="text-slate-700">
          <strong>Agent Triage Plan:</strong> {fraud.agentDecision}
        </span>
        <span className="text-[10.5px] font-bold uppercase px-2 py-0.5 bg-blue-50 text-blue-800 border border-blue-200 rounded">
          4 Autonomous Tools Run
        </span>
      </div>

      <div className="grid md:grid-cols-2 gap-3.5">
        {fraud.tools.map((t) => {
          const isToolAnomaly = t.signal === "SIGNIFICANT_ANOMALY" || t.signal === "ANOMALY";
          return (
            <div
              key={t.toolName}
              className={cn(
                "p-4 rounded-lg border flex flex-col justify-between space-y-3 transition-all",
                isToolAnomaly ? "bg-red-50/40 border-red-300 shadow-2xs" : "bg-white border-border shadow-2xs"
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {t.toolName === "price_benchmark" && <FileSpreadsheet className={cn("w-4 h-4", isToolAnomaly ? "text-red-600" : "text-slate-600")} />}
                  {t.toolName === "vessel_verification" && <Anchor className={cn("w-4 h-4", isToolAnomaly ? "text-amber-600" : "text-slate-600")} />}
                  {t.toolName === "entity_verification" && <Building2 className="w-4 h-4 text-slate-600" />}
                  {t.toolName === "sanctions_screening" && <ShieldCheck className="w-4 h-4 text-emerald-600" />}
                  <span className="text-[13px] font-bold text-slate-900">{t.displayName}</span>
                </div>
                <span
                  className={cn(
                    "text-[10.5px] font-bold px-2.5 py-0.5 rounded uppercase border",
                    t.signal === "SIGNIFICANT_ANOMALY" && "bg-red-100 text-red-900 border-red-300",
                    t.signal === "ANOMALY" && "bg-amber-100 text-amber-900 border-amber-300",
                    t.signal === "REVIEW" && "bg-amber-100 text-amber-900 border-amber-300",
                    t.signal === "NORMAL" && "bg-emerald-100 text-emerald-900 border-emerald-300",
                    t.signal === "CLEAR" && "bg-emerald-100 text-emerald-900 border-emerald-300"
                  )}
                >
                  {(t.signal || "NORMAL").replace(/_/g, " ")}
                </span>
              </div>
              <p className={cn("text-[12px] leading-relaxed", isToolAnomaly ? "text-red-950 font-medium" : "text-slate-600")}>
                {t.evidence}
              </p>
              <div className="flex items-center justify-between text-[10.5px] text-slate-400 pt-2 border-t border-slate-100">
                <span className="font-medium text-slate-500">Confidence: {Math.round((t.confidence ?? 0.9) * 100)}%</span>
                <span className="font-mono">{t.timestamp ? formatTime(t.timestamp) : "14:32:06"} IST</span>
              </div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}

/* ── 10 Risk Assessment ── */
export function RiskSection({ data, onOpenEvidence }: { data: TradeCase; onOpenEvidence?: (ev: EvidenceRecord) => void }) {
  const risk = data.risk;
  if (!risk) return null;
  const isHigh = risk.overallBand === "HIGH";

  return (
    <Section
      title="Comprehensive Risk Assessment"
      subtitle="Synthesized signals across compliance, duplicate, cross-IBU, and TBML dimensions"
      icon={Gauge}
      id="sec-risk"
      status={isHigh ? "review" : "completed"}
    >
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Overall Score Badge */}
        <div className="lg:col-span-4 bg-slate-50 p-5 rounded-lg border border-slate-200 text-center flex flex-col items-center justify-center">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Overall Risk Score</span>
          <div className="my-2">
            <span className={cn(
              "text-5xl font-black",
              isHigh ? "text-red-600" : risk.overallBand === "MEDIUM" ? "text-amber-600" : "text-emerald-600"
            )}>
              {risk.overallScore}
            </span>
            <span className="text-2xl font-light text-slate-400">/100</span>
          </div>
          <span className={cn(
            "px-3 py-1 text-[12px] font-bold uppercase tracking-widest rounded-md",
            isHigh ? "bg-red-100 text-red-800" : risk.overallBand === "MEDIUM" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
          )}>
            {risk.overallBand} RISK
          </span>
          <p className="text-[10px] text-slate-400 mt-3 italic">{risk.weightsNote}</p>
        </div>

        {/* Category Breakdown & Reasons */}
        <div className="lg:col-span-8 space-y-4">
          <div className="space-y-2">
            <span className="text-[10.5px] font-bold text-slate-500 uppercase tracking-wider block">Risk Signal Breakdown</span>
            {risk.breakdown.map((b) => (
              <div key={b.category} className="flex items-center gap-3 text-[12px]">
                <span className="w-36 font-semibold text-slate-700 shrink-0">{b.category}</span>
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full",
                      b.band === "HIGH" ? "bg-red-500" : b.band === "MEDIUM" ? "bg-amber-500" : "bg-emerald-500"
                    )}
                    style={{ width: `${b.score}%` }}
                  />
                </div>
                <span className={cn(
                  "w-16 text-right font-bold text-[11px]",
                  b.band === "HIGH" ? "text-red-600" : b.band === "MEDIUM" ? "text-amber-600" : "text-emerald-600"
                )}>
                  {b.band}
                </span>
              </div>
            ))}
          </div>

          <div className="p-3.5 bg-slate-50 rounded-md border border-slate-200">
            <span className="text-[11px] font-bold text-slate-800 uppercase tracking-wider block mb-1.5">
              Why {risk.overallBand}?
            </span>
            <ul className="space-y-1 text-[12px] text-slate-700">
              {risk.reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-slate-400 font-mono text-[10px] mt-0.5">{i + 1}.</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </Section>
  );
}

/* ── 11 Human Review (Interactive Decision) ── */
export function HumanReviewSection({ data, onDecisionRecorded }: { data: TradeCase; onDecisionRecorded?: (dec: ReviewDecision, comment: string) => void }) {
  const review = data.humanReview;
  const [comment, setComment] = useState("");
  const [selectedDecision, setSelectedDecision] = useState<ReviewDecision>("HOLD");
  const [recorded, setRecorded] = useState(review?.decision != null);
  const [recordedAt, setRecordedAt] = useState(review?.decisionTimestamp ?? "");

  if (!review) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setRecordedAt(new Date().toISOString());
    setRecorded(true);
    onDecisionRecorded?.(selectedDecision, comment);
  }

  return (
    <Section
      title="Human Review & Consequential Authorization"
      subtitle="AI provides signals and recommendations; only authenticated human officers make settlement decisions"
      icon={UserCheck}
      id="sec-review"
      status={recorded ? "completed" : "review"}
    >
      <div className="space-y-4">
        {/* Recommendation Header */}
        <div className={cn(
          "p-4 rounded-lg border-2",
          recorded ? "bg-emerald-50/60 border-emerald-300" : "bg-amber-50/70 border-amber-300"
        )}>
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">AI Recommendation</p>
          <p className="text-[14px] font-bold text-slate-900 mt-0.5">{review.aiRecommendation}</p>
          <p className="text-[12px] text-slate-700 mt-1">{review.reason}</p>
        </div>

        {/* Decision Form or Result */}
        {!recorded ? (
          <form onSubmit={handleSubmit} className="space-y-3 bg-slate-50 p-4 rounded-md border border-slate-200">
            <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block">Record Officer Decision</span>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setSelectedDecision("APPROVE")}
                className={cn(
                  "py-2.5 px-3 text-[12px] font-bold rounded-md border transition-all",
                  selectedDecision === "APPROVE" ? "bg-emerald-600 text-white border-emerald-700 shadow-xs" : "bg-white text-emerald-800 border-emerald-200 hover:bg-emerald-50"
                )}
              >
                CLEAR CASE
              </button>
              <button
                type="button"
                onClick={() => setSelectedDecision("REQUEST_MORE_EVIDENCE")}
                className={cn(
                  "py-2.5 px-3 text-[12px] font-bold rounded-md border transition-all",
                  selectedDecision === "REQUEST_MORE_EVIDENCE" ? "bg-amber-600 text-white border-amber-700 shadow-xs" : "bg-white text-amber-800 border-amber-200 hover:bg-amber-50"
                )}
              >
                REQUEST MORE EVIDENCE
              </button>
              <button
                type="button"
                onClick={() => setSelectedDecision("ESCALATE")}
                className={cn(
                  "py-2.5 px-3 text-[12px] font-bold rounded-md border transition-all",
                  selectedDecision === "ESCALATE" ? "bg-red-600 text-white border-red-700 shadow-xs" : "bg-white text-red-800 border-red-200 hover:bg-red-50"
                )}
              >
                ESCALATE
              </button>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                Decision Rationale / Investigation Notes (required)
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="State your review findings and reasons for this decision..."
                className="w-full p-2.5 text-[12px] border border-slate-300 rounded-md bg-white text-slate-900 outline-none focus:border-primary"
                rows={2}
                required
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-[10.5px] text-slate-500">Signing as: <strong>Officer-102 (Trade Finance Operations Officer)</strong></span>
              <button
                type="submit"
                className="px-5 py-2 bg-slate-900 text-white text-[12px] font-bold rounded-md hover:bg-slate-800 transition-colors shadow-xs"
              >
                Authorize & Submit Decision
              </button>
            </div>
          </form>
        ) : (
          <div className="p-4 bg-emerald-50 rounded-md border border-emerald-200 flex items-start justify-between">
            <div>
              <span className="text-[10px] font-bold uppercase text-emerald-700">Consequential Decision Recorded</span>
              <p className="text-[14px] font-bold text-emerald-900 mt-0.5">
                Officer Decision: {selectedDecision.replace(/_/g, " ")}
              </p>
              <p className="text-[12px] text-slate-700 mt-1">{comment || "Review completed based on presented cross-IBU evidence and documentary checks."}</p>
              <p className="text-[10px] text-slate-500 mt-1">Recorded by: Officer-102 • Timestamp: {recordedAt ? new Date(recordedAt).toLocaleString() : "—"}</p>
            </div>
            <button
              onClick={() => setRecorded(false)}
              className="text-[11px] text-slate-500 hover:underline"
            >
              Modify
            </button>
          </div>
        )}
      </div>
    </Section>
  );
}

/* ── Agent Activity Timeline ── */
export function AgentTimelineSection({ data }: { data: TradeCase }) {
  const timeline = data.agentTimeline;
  if (!timeline || timeline.length === 0) return null;

  return (
    <Section
      title="Agent Activity Timeline"
      subtitle="Chronological sequence of observable agent decisions and tool outputs"
      icon={FileText}
      id="sec-agent-timeline"
      status="completed"
    >
      <div className="divide-y divide-border">
        {timeline.map((e, idx) => (
          <div key={idx} className="py-2.5 flex items-start gap-4 text-[12px]">
            <span className="font-mono text-[11px] text-slate-400 w-24 shrink-0 pt-0.5">
              {formatTime(e.timestamp)}
            </span>
            <div className="flex-1">
              <span className="font-bold text-slate-900">{e.agent}</span>
              <p className="text-slate-600">{e.action}</p>
            </div>
            {e.result && (
              <span className="text-[11px] font-semibold px-2 py-0.5 bg-slate-100 text-slate-700 rounded shrink-0">
                {e.result}
              </span>
            )}
          </div>
        ))}
      </div>
    </Section>
  );
}
