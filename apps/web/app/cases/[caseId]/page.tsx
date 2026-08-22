"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getCase, buildWorkflowSteps } from "@/services/mock-api";
import { useWorkflow } from "@/hooks/use-workflow";
import { RiskBadge } from "@/components/shared/risk-badge";
import { WorkflowTimeline } from "@/features/investigation/workflow-timeline";
import {
  DocumentUploadSection,
  CaseSummarySection,
  DocumentsSection,
  ComplianceSection,
  TransactionDNASection,
  DuplicateFinancingSection,
  CrossIBUSection,
  FraudTBMLSection,
  RiskSection,
  HumanReviewSection,
  AgentTimelineSection,
} from "@/features/investigation/step-sections";
import type { TradeCase, WorkflowStep } from "@/types";
import { cn, formatCurrency } from "@/lib/utils";
import {
  ArrowLeft,
  Play,
  RotateCcw,
  Building2,
  UserPlus,
  AlertTriangle,
  FileSearch,
  Activity,
} from "lucide-react";

export default function CaseInvestigationPage() {
  const params = useParams<{ caseId: string }>();
  const caseId = decodeURIComponent(params.caseId);
  const [tradeCase, setTradeCase] = useState<TradeCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  const emptySteps: WorkflowStep[] = [];
  const { steps, currentStepIndex, isRunning, isComplete, startWorkflow, resetWorkflow } = useWorkflow(emptySteps);

  useEffect(() => {
    void getCase(caseId).then((data) => {
      setTradeCase(data);
      setLoading(false);
    });
  }, [caseId]);

  const finalSteps = tradeCase ? buildWorkflowSteps(tradeCase) : [];

  const handleStart = useCallback(() => {
    if (tradeCase) {
      startWorkflow(finalSteps);
    }
  }, [tradeCase, finalSteps, startWorkflow]);

  const handleReset = useCallback(() => {
    resetWorkflow(finalSteps.map((s) => ({ ...s, status: "pending" as const })));
  }, [finalSteps, resetWorkflow]);

  const sectionIdByStep: Record<string, string> = {
    document_upload: "sec-document_upload",
    document_extraction: "sec-document_extraction",
    document_completeness: "sec-document_extraction",
    ucp600_compliance: "sec-compliance",
    cross_document_consistency: "sec-compliance",
    transaction_dna: "sec-dna",
    duplicate_financing: "sec-duplicate",
    cross_ibu_intelligence: "sec-crossibu",
    fraud_tbml: "sec-fraud",
    risk_assessment: "sec-risk",
    human_review: "sec-review",
  };

  if (loading) {
    return (
      <div className="p-6 max-w-[1440px] mx-auto animate-fade-in">
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-white border border-border rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!tradeCase) {
    return (
      <div className="p-6 max-w-[1440px] mx-auto">
        <div className="bg-white rounded-lg border border-border p-12 text-center">
          <p className="text-[14px] text-slate-500">Case not found: {caseId}</p>
          <Link href="/cases" className="text-[12px] text-primary hover:underline mt-2 inline-block">
            ← Back to cases
          </Link>
        </div>
      </div>
    );
  }

  const showSections = isComplete || (!isRunning && steps.length === 0);

  return (
    <div className="p-6 max-w-[1440px] mx-auto space-y-5 animate-fade-in">
      {/* Back link */}
      <Link href="/cases" className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-primary">
        <ArrowLeft className="w-3 h-3" /> Back to cases
      </Link>

      {/* ═══ CASE HEADER ═══ */}
      <div className="bg-white rounded-lg border border-border p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-lg font-bold text-slate-900">{tradeCase.caseId}</h1>
              <RiskBadge band={tradeCase.riskBand} score={tradeCase.riskScore} size="md" />
              {tradeCase.humanReview?.required && !tradeCase.humanReview?.decision && (
                <span className="text-[10px] font-semibold text-risk-medium bg-risk-medium-bg px-2 py-0.5 rounded border border-risk-medium-border flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> REVIEW REQUIRED
                </span>
              )}
            </div>
            <p className="text-[13px] text-slate-600">
              {tradeCase.exporter} → {tradeCase.importer}
            </p>
            <div className="flex items-center gap-4 mt-2 text-[11px] text-slate-500">
              <span className="flex items-center gap-1">
                <Building2 className="w-3 h-3" /> {tradeCase.presentingIBU}
              </span>
              <span>LC: <span className="font-mono text-slate-700">{tradeCase.lcReference}</span></span>
              <span>{formatCurrency(tradeCase.amount, tradeCase.currency)}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1.5 text-[11px] font-medium text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors flex items-center gap-1">
              <UserPlus className="w-3 h-3" /> Assign
            </button>
            <button className="px-3 py-1.5 text-[11px] font-medium text-risk-medium border border-risk-medium-border rounded-md hover:bg-risk-medium-bg transition-colors flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" /> Escalate
            </button>
            <button className="px-3 py-1.5 text-[11px] font-medium text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors flex items-center gap-1">
              <FileSearch className="w-3 h-3" /> Request Evidence
            </button>
          </div>
        </div>
      </div>

      {/* ═══ LIVE INVESTIGATION WORKFLOW ═══ */}
      <div className="bg-white rounded-lg border border-border p-5">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-[14px] font-bold text-slate-900 flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary" />
              Live Investigation Workflow
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              AI-assisted trade-finance investigation {isRunning ? "in progress" : isComplete ? "completed" : ""}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {!isRunning && !isComplete && (
              <button
                onClick={handleStart}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-white text-[12px] font-semibold rounded-md hover:bg-primary-hover transition-colors"
              >
                <Play className="w-3.5 h-3.5" /> Start Investigation
              </button>
            )}
            {isComplete && (
              <button
                onClick={handleReset}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors"
              >
                <RotateCcw className="w-3 h-3" /> Reset
              </button>
            )}
            {isRunning && (
              <span className="flex items-center gap-1.5 text-[11px] text-info font-medium">
                <span className="w-2 h-2 rounded-full bg-info animate-pulse" />
                Step {currentStepIndex + 1} of {steps.length}
              </span>
            )}
          </div>
        </div>

        <WorkflowTimeline
          steps={steps.length > 0 ? steps : finalSteps}
          activeStep={isRunning && steps[currentStepIndex] ? steps[currentStepIndex].id : undefined}
          onStepClick={(id) => {
            const el = document.getElementById(sectionIdByStep[id] ?? `sec-${id}`);
            if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
          }}
        />
      </div>

      {/* ═══ AGENT STATUS ═══ */}
      {(isRunning || isComplete) && tradeCase.agentStatus && (
        <div className="bg-white rounded-lg border border-border p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className={cn(
              "w-2 h-2 rounded-full",
              isRunning ? "bg-info animate-pulse" : "bg-risk-low"
            )} />
            <h3 className="text-[12px] font-semibold text-slate-700">Agent Status</h3>
          </div>
          {isRunning && currentStepIndex >= 0 && steps[currentStepIndex] && (
            <div className="grid grid-cols-4 gap-3 text-[11px]">
              <div><span className="text-slate-400">Current action:</span><p className="font-medium text-slate-700">{steps[currentStepIndex].title}</p></div>
              <div><span className="text-slate-400">Step:</span><p className="font-medium text-slate-700">{currentStepIndex + 1} / {steps.length}</p></div>
              <div><span className="text-slate-400">Evidence found:</span><p className="font-medium text-slate-700">{tradeCase.agentStatus.evidenceFound}</p></div>
              <div><span className="text-slate-400">Tools used:</span><p className="font-medium text-slate-700">{tradeCase.agentStatus.toolsUsed.length}</p></div>
            </div>
          )}
          {isComplete && (
            <div className="grid grid-cols-4 gap-3 text-[11px]">
              <div><span className="text-slate-400">Status:</span><p className="font-medium text-risk-low">✓ Investigation complete</p></div>
              <div><span className="text-slate-400">Evidence:</span><p className="font-medium text-slate-700">{tradeCase.agentStatus.evidenceFound} findings</p></div>
              <div><span className="text-slate-400">Tools:</span><p className="font-medium text-slate-700">{tradeCase.agentStatus.toolsUsed.join(", ")}</p></div>
              <div><span className="text-slate-400">Recommendation:</span><p className="font-medium text-slate-700">{tradeCase.agentStatus.recommendation}</p></div>
            </div>
          )}
        </div>
      )}

      {/* ═══ INVESTIGATION SECTIONS ═══ */}
      {(showSections || isComplete) && (
        <div className="space-y-4">
          {/* Step 01: Document Upload */}
          <DocumentUploadSection data={tradeCase} />

          {/* Case Summary */}
          <div className="bg-white rounded-lg border border-border p-5">
            <h2 className="text-[13px] font-semibold text-slate-900 mb-3">Case Summary</h2>
            <CaseSummarySection data={tradeCase} />
          </div>

          <DocumentsSection data={tradeCase} />
          <ComplianceSection data={tradeCase} />
          <TransactionDNASection data={tradeCase} />
          <DuplicateFinancingSection data={tradeCase} />
          <CrossIBUSection data={tradeCase} />
          <FraudTBMLSection data={tradeCase} />
          <RiskSection data={tradeCase} />
          <HumanReviewSection data={tradeCase} />
          <AgentTimelineSection data={tradeCase} />
        </div>
      )}

      {/* Footer */}
      <footer className="text-center py-4">
        <p className="text-[10px] text-slate-400">
          Prototype · Synthetic evidence only · No settlement execution · FCSS is downstream settlement infrastructure
        </p>
      </footer>
    </div>
  );
}
