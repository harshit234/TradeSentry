"use client";

import { ChangeEvent, DragEvent, useCallback, useEffect, useState } from "react";
import { Completeness, DocumentItem, createCase, getCompleteness, getDocument, getDocuments, uploadDocument } from "../lib/api";

const CASES = ["DEMO-CASE-A", "DEMO-CASE-B", "DEMO-CASE-C", "DEMO-CASE-D"];
const TYPE_LABELS: Record<string, string> = { letter_of_credit:"Letter of Credit", commercial_invoice:"Commercial Invoice", bill_of_lading:"Bill of Lading", packing_list:"Packing List", certificate_of_origin:"Certificate of Origin", insurance_certificate:"Insurance Certificate", inspection_certificate:"Inspection Certificate", unknown:"Unclassified" };
const VALID_TYPES = ["application/pdf", "image/tiff", "image/jpeg"];
const MAX_BYTES = 50 * 1024 * 1024;

export default function Home() {
  const [caseId, setCaseId] = useState(CASES[0]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [completeness, setCompleteness] = useState<Completeness | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [selected, setSelected] = useState<DocumentItem | null>(null);

  const refresh = useCallback(async () => {
    try {
      await createCase(caseId, "IBU-A");
      const [nextDocuments, nextCompleteness] = await Promise.all([getDocuments(caseId), getCompleteness(caseId)]);
      setDocuments(nextDocuments); setCompleteness(nextCompleteness);
    } catch { setError("The document service is unavailable. Start the local stack and retry."); }
  }, [caseId]);

  useEffect(() => { void refresh(); const timer = window.setInterval(() => void refresh(), 2500); return () => window.clearInterval(timer); }, [refresh]);

  async function acceptFiles(files: FileList | File[]) {
    setError(""); const items = Array.from(files);
    const invalid = items.find((file) => !VALID_TYPES.includes(file.type) || file.size > MAX_BYTES);
    if (invalid) { setError(invalid.size > MAX_BYTES ? `${invalid.name} exceeds 50 MB.` : `${invalid.name} is not a PDF, TIFF, or JPEG.`); return; }
    setUploading(true);
    try { for (const file of items) await uploadDocument(caseId, file); await refresh(); }
    catch (uploadError) { setError(uploadError instanceof Error ? uploadError.message : "Upload failed."); }
    finally { setUploading(false); }
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) { event.preventDefault(); void acceptFiles(event.dataTransfer.files); }
  function onChoose(event: ChangeEvent<HTMLInputElement>) { if (event.target.files) void acceptFiles(event.target.files); event.target.value = ""; }
  async function viewDocument(document: DocumentItem) { setSelected(await getDocument(caseId, document.document_id)); }

  return <main>
    <header className="topbar"><div><p className="eyebrow">GIFT City IBU intelligence</p><h1>TradeSentry</h1></div><div className="casePicker"><label htmlFor="case">Active case</label><select id="case" value={caseId} onChange={(event) => setCaseId(event.target.value)}>{CASES.map((item) => <option key={item}>{item}</option>)}</select></div></header>
    <section className="intro"><div><p className="kicker">Document intelligence</p><h2>Evidence begins with the document.</h2></div><p>Upload synthetic trade documents for classification, extraction, confidence scoring, and page-linked review.</p></section>
    <div className="workspace">
      <section className="panel documentsPanel">
        <div className="sectionHeading"><div><p className="eyebrow">Case file</p><h2>Documents</h2></div><span>{documents.length} uploaded</span></div>
        <label className={`dropzone ${uploading ? "busy" : ""}`} onDragOver={(event) => event.preventDefault()} onDrop={onDrop}><input type="file" multiple accept=".pdf,.tif,.tiff,.jpg,.jpeg" onChange={onChoose} disabled={uploading}/><span className="uploadIcon">↑</span><strong>{uploading ? "Uploading securely…" : "Drag & drop trade documents here"}</strong><small>or click to browse · PDF, TIFF, JPEG · max 50 MB</small></label>
        {error && <p className="inlineError" role="alert">{error}</p>}
        <div className="documentTable" role="table" aria-label="Case documents">
          <div className="documentHeader" role="row"><span>File</span><span>Type</span><span>Status</span><span>Confidence</span></div>
          {documents.length === 0 && <div className="emptyRow">No documents yet. Upload files or run <code>make seed-demo</code>.</div>}
          {documents.map((document) => { const confidence = Math.round((document.overall_confidence ?? 0) * 100); return <div className="documentRow" role="row" key={document.document_id}><div><strong>{document.filename}</strong>{document.advisory && <small>{document.advisory}</small>}</div><span className="typeBadge">{TYPE_LABELS[document.document_type]}</span><span className={`status status-${document.status.toLowerCase()}`}><i/>{document.status}</span><div className="confidenceCell">{document.overall_confidence == null ? <span className="muted">—</span> : <><div className="bar"><i style={{width:`${confidence}%`}}/></div><b>{confidence}%</b></>}<button className="textButton" onClick={() => void viewDocument(document)}>View</button></div></div>; })}
        </div>
      </section>
      <aside className="panel completenessPanel"><p className="eyebrow">Readiness</p><h2>Completeness</h2><p className="panelCopy">Every document required by the LC must be extracted before investigation can begin.</p><div className="tracker">{(completeness?.required_types ?? []).map((type) => { const present = completeness?.present_types.includes(type); return <div key={type} className={present ? "present" : "missing"}><span>{present ? "✓" : "×"}</span>{TYPE_LABELS[type]}</div>; })}{completeness?.status === "PENDING_LC" && <div className="pending"><span>…</span>Upload Letter of Credit first</div>}</div><div className={`readiness ${completeness?.status.toLowerCase() ?? "pending_lc"}`}><span>{completeness?.status ?? "PENDING_LC"}</span><strong>{completeness?.missing_types.length ?? 0} missing</strong></div><button className="runButton" disabled={!completeness?.can_run_investigation} title="Investigation execution is introduced in the next sprint">Run Investigation</button><small className="humanNote">Human review remains required for every consequential action.</small></aside>
    </div>
    {selected && <div className="modalBackdrop" onClick={() => setSelected(null)}><article className="modal" onClick={(event) => event.stopPropagation()}><button className="close" onClick={() => setSelected(null)}>×</button><p className="eyebrow">Extracted evidence</p><h2>{selected.filename}</h2><div className="fieldGrid">{Object.entries((selected.extraction?.fields ?? {}) as Record<string, unknown>).map(([name,value]) => <div key={name}><span>{name.replaceAll("_"," ")}</span><strong>{typeof value === "object" ? JSON.stringify(value) : String(value ?? "—")}</strong><small>Page {selected.extraction?.page_refs[name]?.join(", ") ?? "—"}</small></div>)}</div>{selected.view_url && <a className="viewOriginal" href={selected.view_url} target="_blank" rel="noreferrer">Open original PDF ↗</a>}</article></div>}
    <footer>Prototype only · Synthetic data · No settlement execution</footer>
  </main>;
}
