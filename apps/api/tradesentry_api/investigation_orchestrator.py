from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Literal, TypeVar

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agents.guardrails import safe_inputs_hash, validate_compliance_rule_ids
from agents.planner import APPROVED_AGENT_TOOLS, TriagePlanner, validate_tool_plan
from agents.risk import deterministic_risk_score
from cross_ibu import find_best_match, signal_from_dna
from dna import build_transaction_dna
from models.compliance import ComplianceRunRequest, Severity
from models.contracts import (
    CompletenessStatus,
    DocumentCompleteness,
    DocumentStatus,
    DocumentType,
    LetterOfCreditFields,
)
from models.cross_ibu import MatchLevel
from models.fraud_tbml import (
    PriceSignal,
    SanctionsMatchStatus,
    VesselVerificationStatus,
)
from models.investigation import (
    HOLD_ACTION,
    READY_ACTION,
    DocumentSummary,
    EvidenceRecord,
    EvidenceSeverity,
    InvestigationResponse,
    InvestigationState,
    TimelineRecord,
    ToolCallRecord,
    ToolSelectionPlan,
    TriageContext,
)
from rules.engine import evaluate_compliance

from .audit_store import AuditEvent, AuditEventType
from .compliance_api import build_compliance_facts
from .services import Services
from .telemetry import traced

T = TypeVar("T")
logger = logging.getLogger(__name__)


class InvestigationOrchestrator:
    def __init__(
        self,
        services: Services,
        planner: TriagePlanner,
        tool_timeout_seconds: float = 30.0,
        default_tool_budget: int = 12,
    ) -> None:
        self.services = services
        self.planner = planner
        self.tool_timeout_seconds = tool_timeout_seconds
        self.default_tool_budget = default_tool_budget
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        graph = StateGraph(InvestigationState)
        graph.add_node("load_case", self._traced_node("load_case", self.load_case))
        graph.add_node("check_completeness", self._traced_node("check_completeness", self.check_completeness))
        graph.add_node("run_ucp_rules", self._traced_node("run_ucp_rules", self.run_ucp_rules))
        graph.add_node("build_transaction_dna", self._traced_node("build_transaction_dna", self.build_transaction_dna))
        graph.add_node("cross_ibu_check", self._traced_node("cross_ibu_check", self.cross_ibu_check))
        graph.add_node("fraud_triage", self._traced_node("fraud_triage", self.fraud_triage))
        graph.add_node("conditional_tool_calls", self._traced_node("conditional_tool_calls", self.conditional_tool_calls))
        graph.add_node("aggregate_evidence", self._traced_node("aggregate_evidence", self.aggregate_evidence))
        graph.add_node("risk_assessment", self._traced_node("risk_assessment", self.risk_assessment))
        graph.add_node("human_review_gate", self._traced_node("human_review_gate", self.human_review_gate))
        graph.add_node("settlement_readiness", self._traced_node("settlement_readiness", self.settlement_readiness))
        graph.add_edge(START, "load_case")
        graph.add_conditional_edges(
            "load_case", self._after_load, {"continue": "check_completeness", "stop": END}
        )
        graph.add_conditional_edges(
            "check_completeness",
            self._after_completeness,
            {"continue": "run_ucp_rules", "review": "human_review_gate"},
        )
        graph.add_edge("run_ucp_rules", "build_transaction_dna")
        graph.add_edge("build_transaction_dna", "cross_ibu_check")
        graph.add_edge("cross_ibu_check", "fraud_triage")
        graph.add_edge("fraud_triage", "conditional_tool_calls")
        graph.add_edge("conditional_tool_calls", "aggregate_evidence")
        graph.add_edge("aggregate_evidence", "risk_assessment")
        graph.add_edge("risk_assessment", "human_review_gate")
        graph.add_edge("human_review_gate", "settlement_readiness")
        graph.add_edge("settlement_readiness", END)
        return graph.compile(checkpointer=self.checkpointer)

    @staticmethod
    def _traced_node(name: str, operation: Callable[..., Any]) -> Callable[..., Any]:
        async def invoke(state: InvestigationState) -> Any:
            with traced(f"langgraph.{name}", case_id=state.case_id, ibu_id=state.ibu_id):
                result = operation(state)
                return await result if inspect.isawaitable(result) else result

        return invoke

    async def run(
        self, case_id: str, ibu_id: str, tool_budget: int | None = None
    ) -> InvestigationResponse:
        investigation_started = monotonic()
        initial = InvestigationState(
            case_id=case_id,
            ibu_id=ibu_id,
            tool_budget_remaining=(
                self.default_tool_budget if tool_budget is None else tool_budget
            ),
        )
        config = {"configurable": {"thread_id": f"{ibu_id}:{case_id}:{datetime.now(UTC).timestamp()}"}}
        with traced("case.investigation", case_id=case_id, ibu_id=ibu_id):
            raw = await self.graph.ainvoke(initial, config)
        values = dict(raw)
        interrupted = bool(values.pop("__interrupt__", ()))
        state = InvestigationState.model_validate(values)
        if interrupted:
            state = state.model_copy(
                update={
                    "timeline": _timeline(
                        state,
                        "human_review_gate",
                        "INTERRUPTED",
                        state.stop_reason or "Mandatory human review required",
                    )
                }
            )
        workflow_status: Literal["COMPLETED", "INTERRUPTED"] = (
            "INTERRUPTED" if interrupted else "COMPLETED"
        )
        response = InvestigationResponse(state=state, workflow_status=workflow_status)
        await self.services.investigation_store.save(response)
        await self.services.audit_store.record(
            AuditEvent(
                case_id=case_id,
                ibu_id=ibu_id,
                actor_id="investigation-orchestrator",
                actor_role="AGENT",
                event_type=AuditEventType.AGENT_DECISION,
                payload_ref=f"agent://{case_id}/{state.stop_reason or 'complete'}",
            )
        )
        if state.risk_band is not None:
            await self.services.audit_store.record(
                AuditEvent(
                    case_id=case_id,
                    ibu_id=ibu_id,
                    actor_id="investigation-orchestrator",
                    actor_role="AGENT",
                    event_type=AuditEventType.RISK_SCORED,
                    payload_ref=f"risk://{case_id}/{state.risk_band.value}/{state.risk_score}",
                )
            )
        if state.requires_human_review:
            await self.services.audit_store.record(
                AuditEvent(
                    case_id=case_id,
                    ibu_id=ibu_id,
                    actor_id="investigation-orchestrator",
                    actor_role="AGENT",
                    event_type=AuditEventType.HUMAN_REVIEW_REQUIRED,
                    payload_ref=f"review-gate://{case_id}/{state.stop_reason or 'required'}",
                )
            )
        logger.info(
            "Case investigation completed",
            extra={
                "case_processing_latency_ms": round(
                    (monotonic() - investigation_started) * 1000, 3
                ),
                "risk_band": None if state.risk_band is None else state.risk_band.value,
            },
        )
        return response

    @staticmethod
    def _after_load(state: InvestigationState) -> str:
        return "stop" if state.stop_reason == "NO_DOCUMENTS" else "continue"

    @staticmethod
    def _after_completeness(state: InvestigationState) -> str:
        if state.completeness is None or state.completeness.status is not CompletenessStatus.COMPLETE:
            return "review"
        return "continue"

    async def load_case(self, state: InvestigationState) -> dict[str, Any]:
        documents = await self.services.repository.list_documents(state.case_id)
        summaries = [
            DocumentSummary(
                document_id=item.id,
                document_type=item.document_type,
                status=item.status,
                overall_confidence=item.overall_confidence,
            )
            for item in documents
        ]
        extractions = {
            item.id: item.extraction for item in documents if item.extraction is not None
        }
        errors = list(state.errors)
        stop_reason = state.stop_reason
        complete = state.investigation_complete
        if not documents:
            errors.append("No documents available for investigation")
            stop_reason = "NO_DOCUMENTS"
            complete = True
        return {
            "documents": summaries,
            "extraction_results": extractions,
            "errors": errors,
            "stop_reason": stop_reason,
            "investigation_complete": complete,
            "timeline": _timeline(state, "load_case", "COMPLETED", f"Loaded {len(documents)} documents"),
        }

    async def check_completeness(self, state: InvestigationState) -> dict[str, Any]:
        completeness = _completeness(state)
        incomplete = completeness.status is not CompletenessStatus.COMPLETE
        return {
            "completeness": completeness,
            "requires_human_review": incomplete,
            "recommended_action": HOLD_ACTION if incomplete else state.recommended_action,
            "stop_reason": "INCOMPLETE_DOCUMENT_SET" if incomplete else state.stop_reason,
            "timeline": _timeline(
                state,
                "check_completeness",
                completeness.status.value,
                "Deterministic document completeness check",
            ),
        }

    async def run_ucp_rules(self, state: InvestigationState) -> dict[str, Any]:
        async def operation() -> Any:
            facts = await build_compliance_facts(
                self.services, state.case_id, ComplianceRunRequest()
            )
            result = validate_compliance_rule_ids(evaluate_compliance(facts))
            await self.services.compliance_store.save(result)
            return facts.lc, result

        result, record, remaining, errors = await self._record_tool_call(
            state, "ucp_rules", {"case_id": state.case_id}, operation
        )
        if result is None:
            return _failure_update(state, record, remaining, errors, "run_ucp_rules")
        lc, compliance = result
        return {
            "lc_requirements": lc,
            "compliance_result": compliance,
            "tool_calls_made": [*state.tool_calls_made, record],
            "tool_budget_remaining": remaining,
            "errors": errors,
            "timeline": _timeline(state, "run_ucp_rules", "COMPLETED", "Deterministic UCP engine only"),
        }

    async def build_transaction_dna(self, state: InvestigationState) -> dict[str, Any]:
        async def operation() -> Any:
            dna = build_transaction_dna(
                state.case_id,
                state.ibu_id,
                list(state.extraction_results.values()),
                datetime.now(UTC),
            )
            await self.services.dna_store.save(dna)
            return dna

        result, record, remaining, errors = await self._record_tool_call(
            state, "transaction_dna", {"case_id": state.case_id}, operation
        )
        if result is None:
            return _failure_update(state, record, remaining, errors, "build_transaction_dna")
        return {
            "transaction_dna": result,
            "tool_calls_made": [*state.tool_calls_made, record],
            "tool_budget_remaining": remaining,
            "errors": errors,
            "timeline": _timeline(state, "build_transaction_dna", "COMPLETED", "Deterministic normalization"),
        }

    async def cross_ibu_check(self, state: InvestigationState) -> dict[str, Any]:
        dna = state.transaction_dna
        if dna is None or dna.bl_number_normalized is None:
            return {"timeline": _timeline(state, "cross_ibu_check", "SKIPPED", "No normalized B/L number")}

        async def operation() -> Any:
            signal = signal_from_dna(dna)
            candidates = await self.services.cross_ibu_registry.find_candidates(signal)
            return find_best_match(signal, candidates, datetime.now(UTC))

        result, record, remaining, errors = await self._record_tool_call(
            state,
            "cross_ibu_check",
            {"case_id": state.case_id, "dna_fingerprint": dna.dna_fingerprint},
            operation,
        )
        if result is None:
            return _failure_update(state, record, remaining, errors, "cross_ibu_check")
        return {
            "cross_ibu_matches": [result],
            "tool_calls_made": [*state.tool_calls_made, record],
            "tool_budget_remaining": remaining,
            "errors": errors,
            "timeline": _timeline(
                state,
                "cross_ibu_check",
                result.match_level.value,
                f"DynamoDB GSI query · {record.duration_ms:.3f}ms · {result.explanation}",
            ),
        }

    async def fraud_triage(self, state: InvestigationState) -> dict[str, Any]:
        dna = state.transaction_dna
        context = TriageContext(
            cross_ibu_levels=[item.match_level.value for item in state.cross_ibu_matches],
            unit_value_usd_per_unit=(
                float(dna.unit_value_usd_per_unit)
                if dna is not None and dna.unit_value_usd_per_unit is not None
                else None
            ),
            conflict_fields=[] if dna is None else [item.field_name for item in dna.conflicts],
            both_trade_entities_missing=bool(
                dna is not None
                and dna.exporter_normalized is None
                and dna.importer_normalized is None
            ),
            sanctions_already_run=state.sanctions_result is not None,
        )
        errors = list(state.errors)
        try:
            plan = validate_tool_plan(await self.planner.plan(context))
        except Exception as exc:  # noqa: BLE001 - invalid LLM output safely selects sanctions only
            errors.append(f"Triage planner output rejected ({type(exc).__name__})")
            plan = ToolSelectionPlan(
                run_price_benchmark=False,
                run_vessel_verification=False,
                run_entity_verification=False,
                run_sanctions=state.sanctions_result is None,
                reasoning="Planner output was rejected; only mandatory sanctions screening retained.",
            )
        return {
            "tool_selection_plan": plan,
            "errors": errors,
            "timeline": _timeline(state, "fraud_triage", "VALIDATED", plan.reasoning),
        }

    async def conditional_tool_calls(self, state: InvestigationState) -> dict[str, Any]:
        plan = state.tool_selection_plan
        dna = state.transaction_dna
        if plan is None or dna is None:
            return {"timeline": _timeline(state, "conditional_tool_calls", "SKIPPED", "No valid plan or DNA")}
        selected: list[tuple[str, Callable[[], Awaitable[Any]]]] = []
        runner = self.services.fraud_tbml_runner
        if plan.run_price_benchmark:
            selected.append(("price_benchmark", lambda: runner.run_price_benchmark(dna)))
        if plan.run_vessel_verification:
            selected.append(("vessel_verification", lambda: runner.run_vessel_verification(dna)))
        if plan.run_entity_verification:
            selected.append(("entity_verification", lambda: runner.run_entity_verification(dna)))
        if plan.run_sanctions:
            selected.append(("sanctions_screening", lambda: runner.run_sanctions_screening(dna)))

        updates: dict[str, Any] = {}
        records = list(state.tool_calls_made)
        errors = list(state.errors)
        remaining = state.tool_budget_remaining
        exhausted = False
        for tool_name, operation in selected:
            if tool_name not in APPROVED_AGENT_TOOLS:
                errors.append(f"Blocked non-allow-listed tool: {tool_name}")
                continue
            if remaining <= 0:
                exhausted = True
                break
            current = state.model_copy(
                update={
                    "tool_calls_made": records,
                    "tool_budget_remaining": remaining,
                    "errors": errors,
                }
            )
            result, record, remaining, errors = await self._record_tool_call(
                current,
                tool_name,
                {"case_id": state.case_id, "dna_fingerprint": dna.dna_fingerprint},
                operation,
            )
            records.append(record)
            if result is not None:
                key = {
                    "price_benchmark": "price_benchmark",
                    "vessel_verification": "vessel_verification",
                    "entity_verification": "entity_verifications",
                    "sanctions_screening": "sanctions_result",
                }[tool_name]
                updates[key] = result
        if exhausted:
            errors.append("Tool budget exhausted; remaining selections were not called")
            updates.update(
                {
                    "requires_human_review": True,
                    "recommended_action": HOLD_ACTION,
                    "stop_reason": "TOOL_BUDGET_EXHAUSTED",
                }
            )
        updates.update(
            {
                "tool_calls_made": records,
                "tool_budget_remaining": remaining,
                "errors": errors,
                "timeline": _timeline(
                    state,
                    "conditional_tool_calls",
                    "BUDGET_EXHAUSTED" if exhausted else "COMPLETED",
                    f"Executed {len(records) - len(state.tool_calls_made)} selected tools",
                ),
            }
        )
        return updates

    async def aggregate_evidence(self, state: InvestigationState) -> dict[str, Any]:
        evidence = _evidence(state)
        return {
            "evidence": evidence,
            "timeline": _timeline(state, "aggregate_evidence", "COMPLETED", f"Created {len(evidence)} evidence records"),
        }

    async def risk_assessment(self, state: InvestigationState) -> dict[str, Any]:
        score, band = deterministic_risk_score(state)
        material = bool(
            state.compliance_result
            and any(item.severity is Severity.MATERIAL for item in state.compliance_result.findings)
        )
        exact = any(item.match_level is MatchLevel.EXACT for item in state.cross_ibu_matches)
        near = any(item.match_level is MatchLevel.NEAR for item in state.cross_ibu_matches)
        dna_attention = bool(
            state.transaction_dna
            and (state.transaction_dna.confidence_flags or state.transaction_dna.conflicts)
        )
        external_signal = bool(
            (state.price_benchmark and state.price_benchmark.signal is not PriceSignal.NORMAL)
            or (
                state.vessel_verification
                and state.vessel_verification.verification_result
                is VesselVerificationStatus.ANOMALY
            )
            or (
                state.sanctions_result
                and any(
                    item.match_status is not SanctionsMatchStatus.NO_MATCH
                    for item in state.sanctions_result.screened_entities
                )
            )
        )
        requires_review = (
            state.requires_human_review
            or band.value == "HIGH"
            or material
            or exact
            or near
            or dna_attention
            or external_signal
        )
        return {
            "risk_score": score,
            "risk_band": band,
            "requires_human_review": requires_review,
            "recommended_action": HOLD_ACTION if requires_review else state.recommended_action,
            "stop_reason": (
                state.stop_reason or "HUMAN_REVIEW_REQUIRED" if requires_review else state.stop_reason
            ),
            "timeline": _timeline(
                state,
                "risk_assessment",
                band.value,
                "Applied prototype demo weights — not calibrated for production",
            ),
        }

    def human_review_gate(self, state: InvestigationState) -> dict[str, Any]:
        if state.requires_human_review:
            interrupt(
                {
                    "case_id": state.case_id,
                    "reason": state.stop_reason or "HUMAN_REVIEW_REQUIRED",
                    "risk_band": state.risk_band.value if state.risk_band else None,
                    "action": HOLD_ACTION,
                }
            )
        return {
            "timeline": _timeline(state, "human_review_gate", "PASSED", "No mandatory review trigger")
        }

    async def settlement_readiness(self, state: InvestigationState) -> dict[str, Any]:
        return {
            "recommended_action": READY_ACTION,
            "investigation_complete": True,
            "stop_reason": "INVESTIGATION_COMPLETE",
            "timeline": _timeline(
                state,
                "settlement_readiness",
                "READY",
                "Readiness advisory only; no settlement action exists or was executed",
            ),
        }

    async def _record_tool_call(
        self,
        state: InvestigationState,
        tool_name: str,
        inputs: dict[str, Any],
        operation: Callable[[], Awaitable[T]],
    ) -> tuple[T | None, ToolCallRecord, int, list[str]]:
        started = monotonic()
        called_at = datetime.now(UTC)
        errors = list(state.errors)
        status = "COMPLETED"
        result: T | None = None
        if state.tool_budget_remaining <= 0:
            status = "BUDGET_EXHAUSTED"
            errors.append(f"Tool budget exhausted before {tool_name}")
        else:
            try:
                with traced(f"tool.{tool_name}", case_id=state.case_id, ibu_id=state.ibu_id):
                    result = await asyncio.wait_for(operation(), timeout=self.tool_timeout_seconds)
            except Exception as exc:  # noqa: BLE001 - graph records failure and continues safely
                status = "DATA_UNAVAILABLE"
                errors.append(f"{tool_name} unavailable ({type(exc).__name__})")
        duration_ms = round((monotonic() - started) * 1000, 3)
        logger.info(
            "Investigation tool call completed",
            extra={"tool_call_latency_ms": duration_ms, "tool_name": tool_name},
        )
        record = ToolCallRecord(
            tool_name=tool_name,
            inputs_hash=safe_inputs_hash(inputs),
            duration_ms=duration_ms,
            status=status,
            called_at=called_at,
        )
        await self.services.audit_store.record(
            AuditEvent(
                case_id=state.case_id,
                ibu_id=state.ibu_id,
                actor_id="investigation-orchestrator",
                actor_role="AGENT",
                event_type=AuditEventType.TOOL_CALLED,
                payload_ref=f"tool={tool_name};inputs={record.inputs_hash[:12]};status={status}",
                created_at=called_at,
            )
        )
        remaining = max(0, state.tool_budget_remaining - 1)
        return result, record, remaining, errors


def _timeline(
    state: InvestigationState, node_name: str, status: str, detail: str
) -> list[TimelineRecord]:
    return [
        *state.timeline,
        TimelineRecord(
            node_name=node_name,
            status=status,
            occurred_at=datetime.now(UTC),
            detail=detail,
        ),
    ]


def _completeness(state: InvestigationState) -> DocumentCompleteness:
    completed = {
        item.document_type
        for item in state.documents
        if item.status in {DocumentStatus.EXTRACTED, DocumentStatus.PARTIAL}
    }
    lc_extraction = next(
        (
            extraction
            for extraction in state.extraction_results.values()
            if extraction.document_type is DocumentType.LETTER_OF_CREDIT
        ),
        None,
    )
    if lc_extraction is None or not isinstance(lc_extraction.fields, LetterOfCreditFields):
        return DocumentCompleteness(
            required_types=[],
            present_types=sorted(completed, key=str),
            missing_types=[],
            status=CompletenessStatus.PENDING_LC,
            can_run_investigation=False,
        )
    required: list[DocumentType] = list(DocumentType)
    required.remove(DocumentType.UNKNOWN)
    if lc_extraction.fields.required_documents:
        required = [
            item.document_type for item in lc_extraction.fields.required_documents if item.required
        ]
    missing = [item for item in required if item not in completed]
    return DocumentCompleteness(
        required_types=required,
        present_types=sorted(completed, key=str),
        missing_types=missing,
        status=CompletenessStatus.INCOMPLETE if missing else CompletenessStatus.COMPLETE,
        can_run_investigation=not missing,
    )


def _failure_update(
    state: InvestigationState,
    record: ToolCallRecord,
    remaining: int,
    errors: list[str],
    node_name: str,
) -> dict[str, Any]:
    return {
        "tool_calls_made": [*state.tool_calls_made, record],
        "tool_budget_remaining": remaining,
        "errors": errors,
        "requires_human_review": True,
        "recommended_action": HOLD_ACTION,
        "stop_reason": f"{node_name.upper()}_UNAVAILABLE",
        "timeline": _timeline(state, node_name, "DATA_UNAVAILABLE", "Service call unavailable"),
    }


def _evidence(state: InvestigationState) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    if state.transaction_dna is not None:
        for field_name in state.transaction_dna.confidence_flags:
            records.append(
                EvidenceRecord(
                    source="transaction_dna",
                    finding_type="LOW_CONFIDENCE_FIELD",
                    severity=EvidenceSeverity.ADVISORY,
                    summary=f"Low-confidence extraction requires attention: {field_name}",
                    structured_detail={"field_name": field_name, "human_attention": True},
                    evidence_ref=(
                        f"dna://{state.transaction_dna.transaction_id}/confidence/{field_name}"
                    ),
                )
            )
        for conflict in state.transaction_dna.conflicts:
            records.append(
                EvidenceRecord(
                    source="transaction_dna",
                    finding_type="DOCUMENT_CONFLICT",
                    severity=EvidenceSeverity.REVIEW,
                    summary=f"Conflicting structured document evidence: {conflict.field_name}",
                    structured_detail={
                        "field_name": conflict.field_name,
                        "document_a_id": conflict.document_a_id,
                        "document_b_id": conflict.document_b_id,
                        "conflict_severity": conflict.severity.value,
                    },
                    evidence_ref=(
                        f"dna://{state.transaction_dna.transaction_id}/conflict/"
                        f"{conflict.field_name}"
                    ),
                )
            )
    if state.tool_selection_plan is not None:
        records.append(
            EvidenceRecord(
                source="fraud_triage",
                finding_type="TOOL_SELECTION",
                severity=EvidenceSeverity.INFO,
                summary=state.tool_selection_plan.reasoning,
                structured_detail=state.tool_selection_plan.model_dump(),
                evidence_ref=f"investigation://{state.case_id}/triage",
            )
        )
    if state.compliance_result is not None:
        for finding in state.compliance_result.findings:
            records.append(
                EvidenceRecord(
                    source=finding.rule_id,
                    finding_type="UCP_COMPLIANCE",
                    severity=(
                        EvidenceSeverity.MATERIAL
                        if finding.severity is Severity.MATERIAL
                        else EvidenceSeverity.REVIEW
                    ),
                    summary=f"{finding.ucp_article}: {finding.field_name} discrepancy",
                    structured_detail={
                        "rule_id": finding.rule_id,
                        "ucp_article": finding.ucp_article,
                        "expected": finding.expected,
                        "actual": finding.actual,
                        "evidence": finding.evidence,
                    },
                    evidence_ref=f"db://compliance/{finding.finding_id}",
                )
            )
    for match in state.cross_ibu_matches:
        records.append(
            EvidenceRecord(
                source="cross_ibu_check",
                finding_type="CROSS_IBU_MATCH",
                severity=(
                    EvidenceSeverity.HIGH
                    if match.match_level is MatchLevel.EXACT
                    else EvidenceSeverity.REVIEW
                    if match.match_level is not MatchLevel.NONE
                    else EvidenceSeverity.INFO
                ),
                summary=match.explanation,
                structured_detail={
                    "match_level": match.match_level.value,
                    "similarity_score": match.similarity_score,
                    "matched_fields": match.matched_fields,
                    "thresholds_note": match.thresholds_note,
                },
                evidence_ref=match.evidence_ref or f"match://{match.match_id}",
            )
        )
    if state.price_benchmark is not None:
        price = state.price_benchmark
        records.append(
            EvidenceRecord(
                source="price_benchmark",
                finding_type="PRICE_SIGNAL",
                severity=(
                    EvidenceSeverity.HIGH
                    if price.signal is PriceSignal.SIGNIFICANT_ANOMALY
                    else EvidenceSeverity.REVIEW
                    if price.signal is PriceSignal.REVIEW
                    else EvidenceSeverity.INFO
                ),
                summary=f"Price benchmark signal: {price.signal.value}",
                structured_detail={
                    "signal": price.signal.value,
                    "deviation_from_p50_pct": price.deviation_from_p50_pct,
                    "data_source": price.data_source,
                    "caveats": price.caveats,
                },
                evidence_ref=f"tool://price_benchmark/{state.case_id}",
            )
        )
    if state.vessel_verification is not None:
        vessel = state.vessel_verification
        records.append(
            EvidenceRecord(
                source="vessel_verification",
                finding_type="VESSEL_SIGNAL",
                severity=(
                    EvidenceSeverity.REVIEW
                    if vessel.verification_result is VesselVerificationStatus.ANOMALY
                    else EvidenceSeverity.INFO
                ),
                summary=f"Vessel verification: {vessel.verification_result.value}",
                structured_detail={
                    "verification_result": vessel.verification_result.value,
                    "data_source": vessel.data_source,
                    "caveats": vessel.caveats,
                },
                evidence_ref=f"tool://vessel_verification/{state.case_id}",
            )
        )
    for entity in state.entity_verifications:
        records.append(
            EvidenceRecord(
                source="entity_verification",
                finding_type="ENTITY_SIGNAL",
                severity=(
                    EvidenceSeverity.INFO
                    if entity.verification_status.value == "VERIFIED"
                    else EvidenceSeverity.REVIEW
                ),
                summary=f"Entity verification: {entity.verification_status.value}",
                structured_detail={
                    "normalized_name": entity.normalized_name,
                    "verification_status": entity.verification_status.value,
                    "data_source": entity.data_source,
                    "caveats": entity.caveats,
                },
                evidence_ref=f"tool://entity_verification/{state.case_id}",
            )
        )
    if state.sanctions_result is not None:
        for screened in state.sanctions_result.screened_entities:
            records.append(
                EvidenceRecord(
                    source="sanctions_screening",
                    finding_type="SANCTIONS_SIGNAL",
                    severity=(
                        EvidenceSeverity.HIGH
                        if screened.match_status is SanctionsMatchStatus.CONFIRMED_SOURCE_MATCH
                        else EvidenceSeverity.REVIEW
                        if screened.match_status is SanctionsMatchStatus.POSSIBLE_MATCH
                        else EvidenceSeverity.INFO
                    ),
                    summary=f"Sanctions screening: {screened.match_status.value}",
                    structured_detail={
                        "match_status": screened.match_status.value,
                        "match_score": screened.match_score,
                        "data_source": screened.data_source,
                        "human_determination_required": True,
                    },
                    evidence_ref=f"tool://sanctions_screening/{state.case_id}",
                )
            )
    return records
