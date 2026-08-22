"use client";

import { useState, useCallback, useRef } from "react";
import type { WorkflowStep, WorkflowStatus } from "@/types";

/* Deterministic step delays in milliseconds */
const STEP_DELAYS: Record<string, number> = {
  document_upload: 1200,
  document_extraction: 1800,
  document_completeness: 800,
  ucp600_compliance: 2000,
  cross_document_consistency: 1200,
  transaction_dna: 1000,
  duplicate_financing: 2200,
  cross_ibu_intelligence: 2000,
  fraud_tbml: 2500,
  risk_assessment: 1500,
  human_review: 800,
};

interface UseWorkflowReturn {
  steps: WorkflowStep[];
  currentStepIndex: number;
  isRunning: boolean;
  isComplete: boolean;
  startWorkflow: (finalSteps: WorkflowStep[]) => void;
  resetWorkflow: (initialSteps: WorkflowStep[]) => void;
}

export function useWorkflow(initialSteps: WorkflowStep[]): UseWorkflowReturn {
  const [steps, setSteps] = useState<WorkflowStep[]>(() =>
    initialSteps.map((s) => ({ ...s, status: "pending" as WorkflowStatus }))
  );
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [isRunning, setIsRunning] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const cancelRef = useRef(false);

  const startWorkflow = useCallback(
    (finalSteps: WorkflowStep[]) => {
      if (isRunning) return;
      cancelRef.current = false;
      setIsRunning(true);
      setIsComplete(false);

      /* Reset all to pending */
      const pending = finalSteps.map((s) => ({
        ...s,
        status: "pending" as WorkflowStatus,
      }));
      setSteps(pending);
      setCurrentStepIndex(0);

      async function run() {
        for (let i = 0; i < finalSteps.length; i++) {
          if (cancelRef.current) break;

          /* Set current step to processing */
          setCurrentStepIndex(i);
          setSteps((prev) =>
            prev.map((s, idx) =>
              idx === i ? { ...s, status: "processing" as WorkflowStatus } : s
            )
          );

          /* Wait the deterministic delay */
          const delayMs = STEP_DELAYS[finalSteps[i].id] ?? 1000;
          await new Promise((resolve) => setTimeout(resolve, delayMs));

          if (cancelRef.current) break;

          /* Complete the step with its final status */
          setSteps((prev) =>
            prev.map((s, idx) =>
              idx === i ? { ...finalSteps[i] } : s
            )
          );
        }

        setIsRunning(false);
        setIsComplete(true);
      }

      void run();
    },
    [isRunning]
  );

  const resetWorkflow = useCallback((initial: WorkflowStep[]) => {
    cancelRef.current = true;
    setIsRunning(false);
    setIsComplete(false);
    setCurrentStepIndex(-1);
    setSteps(initial.map((s) => ({ ...s, status: "pending" as WorkflowStatus })));
  }, []);

  return { steps, currentStepIndex, isRunning, isComplete, startWorkflow, resetWorkflow };
}
