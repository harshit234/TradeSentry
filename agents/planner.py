from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any

import boto3  # type: ignore[import-untyped]

from models.investigation import ToolSelectionPlan, TriageContext

APPROVED_AGENT_TOOLS = frozenset(
    {
        "price_benchmark",
        "vessel_verification",
        "entity_verification",
        "sanctions_screening",
    }
)


class TriagePlanner(ABC):
    @abstractmethod
    async def plan(self, context: TriageContext) -> object: ...


class DeterministicTriagePlanner(TriagePlanner):
    """Offline planner used by the MVP and tests; mirrors the constrained LLM schema."""

    def __init__(self, unit_value_threshold: float = 700.0) -> None:
        self.unit_value_threshold = unit_value_threshold

    async def plan(self, context: TriageContext) -> object:
        cross_ibu_signal = any(level != "NONE" for level in context.cross_ibu_levels)
        high_unit_value = bool(
            context.unit_value_usd_per_unit is not None
            and context.unit_value_usd_per_unit > self.unit_value_threshold
        )
        vessel_conflict = "vessel_name" in context.conflict_fields
        selected: list[str] = []
        if cross_ibu_signal or high_unit_value:
            selected.append("price benchmark")
        if cross_ibu_signal or vessel_conflict:
            selected.append("vessel verification")
        if cross_ibu_signal or context.both_trade_entities_missing:
            selected.append("entity verification")
        if not context.sanctions_already_run:
            selected.append("sanctions screening")
        reasoning = (
            "Selected read-only investigation tools from structured signals: "
            + (", ".join(selected) if selected else "none")
            + ". Findings remain subject to human review."
        )
        return ToolSelectionPlan(
            run_price_benchmark=cross_ibu_signal or high_unit_value,
            run_vessel_verification=cross_ibu_signal or vessel_conflict,
            run_entity_verification=cross_ibu_signal or context.both_trade_entities_missing,
            run_sanctions=not context.sanctions_already_run,
            reasoning=reasoning,
        )


class BedrockTriagePlanner(TriagePlanner):
    """Constrained production planner; AWS credentials come from the task role/profile."""

    def __init__(self, region: str, model_id: str) -> None:
        self.client: Any = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    async def plan(self, context: TriageContext) -> object:
        schema = ToolSelectionPlan.model_json_schema()
        prompt = (
            "Select only the four boolean investigation options in the supplied JSON schema. "
            "Do not evaluate UCP rules, propose other tools, make settlement decisions, or invent "
            "facts. Return JSON only. Structured investigation signals:\n"
            f"{context.model_dump_json()}\nSchema:\n{json.dumps(schema)}"
        )
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 800,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        response = await asyncio.to_thread(
            self.client.invoke_model,
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        payload = json.loads(response["body"].read())
        return json.loads(payload["content"][0]["text"])


def validate_tool_plan(value: object) -> ToolSelectionPlan:
    """Reject extra fields or arbitrary tool names before any tool can execute."""

    return ToolSelectionPlan.model_validate(value)
