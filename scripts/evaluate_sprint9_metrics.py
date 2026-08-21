"""Measure deterministic Sprint 9 system metrics without external API calls."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from statistics import median, quantiles
from time import perf_counter

from tradesentry_api.config import Settings
from tradesentry_api.investigation_orchestrator import InvestigationOrchestrator
from tradesentry_api.services import Services

from agents.planner import DeterministicTriagePlanner
from cross_ibu import signal_from_dna
from dna import build_transaction_dna
from scripts.seed_demo import CASES, seed_case


async def measure(iterations: int = 3) -> dict[str, object]:
    logging.disable(logging.CRITICAL)
    services = Services.build(Settings())
    try:
        for label in CASES:
            await seed_case(services, label)
        documents = await services.repository.list_documents("DEMO-CASE-A")
        case_a_dna = build_transaction_dna(
            "DEMO-CASE-A",
            "IBU-A",
            [item.extraction for item in documents if item.extraction is not None],
            datetime.now(UTC),
        )
        await services.cross_ibu_registry.register(signal_from_dna(case_a_dna), datetime.now(UTC))

        latencies: list[float] = []
        tool_calls: list[int] = []
        failures = 0
        for _iteration in range(iterations):
            for case_id, ibu_id, _folder in CASES.values():
                started = perf_counter()
                try:
                    result = await InvestigationOrchestrator(
                        services, DeterministicTriagePlanner()
                    ).run(case_id, ibu_id)
                    tool_calls.append(len(result.state.tool_calls_made))
                except Exception:  # noqa: BLE001 - metric records failures, then continues
                    failures += 1
                latencies.append((perf_counter() - started) * 1000)
        ordered = sorted(latencies)
        return {
            "sample_count": len(latencies),
            "p50_case_latency_ms": round(median(ordered), 3),
            "p95_case_latency_ms": round(quantiles(ordered, n=100, method="inclusive")[94], 3),
            "mean_tool_calls_per_case": round(sum(tool_calls) / len(tool_calls), 3),
            "failure_rate": round(failures / len(latencies), 4),
            "api_token_count": 0,
            "cost_per_case_usd": 0.0,
            "measurement_scope": "local deterministic providers; 4 cases x 3 runs",
        }
    finally:
        await services.close()
        logging.disable(logging.NOTSET)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(measure()), indent=2, sort_keys=True))
