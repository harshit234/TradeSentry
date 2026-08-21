from __future__ import annotations

import asyncio
from pathlib import Path

from alembic.config import Config
from fastapi.testclient import TestClient
from tradesentry_api.config import Settings
from tradesentry_api.investigation_orchestrator import InvestigationOrchestrator
from tradesentry_api.main import create_app
from tradesentry_api.services import Services

from agents.planner import DeterministicTriagePlanner
from models.cross_ibu import MatchLevel
from models.fraud_tbml import PriceSignal
from models.investigation import HOLD_ACTION, READY_ACTION, RiskBand
from scripts.seed_demo import CASES, seed_case
from scripts.seed_registry import seed_cross_ibu_registry

ROOT = Path(__file__).resolve().parents[2]


async def _scenarios() -> dict[str, object]:
    services = Services.build(Settings())
    await seed_cross_ibu_registry(services)
    for label in CASES:
        await seed_case(services, label)
    return {
        label: await InvestigationOrchestrator(
            services, DeterministicTriagePlanner()
        ).run(case_id, ibu_id)
        for label, (case_id, ibu_id, _folder) in CASES.items()
    }


def test_health_contract_includes_all_six_components_and_aws_metadata() -> None:
    settings = Settings(
        deployment="AWS ECS · Textract · RDS · DynamoDB · ElastiCache · S3",
        infrastructure_note="Deployed on AWS using hackathon credits",
        version="abc123",
    )
    with TestClient(create_app(settings)) as client:
        payload = client.get("/health").json()
    assert payload["status"] == "ok"
    assert all(payload[name] == "ok" for name in ("db", "redis", "s3", "textract", "dynamodb"))
    assert payload["version"] == "abc123"
    assert payload["infrastructure_note"] == "Deployed on AWS using hackathon credits"


def test_four_demo_scenarios_are_deterministic_and_safe() -> None:
    results = asyncio.run(_scenarios())
    clean, duplicate, tbml, legitimate = (results[label] for label in "ABCD")
    assert clean.workflow_status == "COMPLETED"
    assert clean.state.risk_band is RiskBand.LOW
    assert clean.state.recommended_action == READY_ACTION
    assert len(clean.state.tool_calls_made) <= 4
    assert duplicate.state.cross_ibu_matches[0].match_level is MatchLevel.EXACT
    assert duplicate.state.risk_band is RiskBand.HIGH
    assert duplicate.state.recommended_action == HOLD_ACTION
    assert tbml.state.price_benchmark is not None
    assert tbml.state.price_benchmark.signal is PriceSignal.SIGNIFICANT_ANOMALY
    assert tbml.state.risk_band is RiskBand.HIGH
    assert tbml.state.recommended_action == HOLD_ACTION
    match = legitimate.state.cross_ibu_matches[0]
    assert match.match_level is MatchLevel.NONE
    assert 0.30 <= match.similarity_score <= 0.39
    assert legitimate.state.risk_band is RiskBand.LOW
    assert legitimate.state.recommended_action == READY_ACTION
    assert legitimate.state.requires_human_review is False


def test_cross_ibu_timeline_uses_measured_dynamodb_latency() -> None:
    results = asyncio.run(_scenarios())
    step = next(
        item for item in results["B"].state.timeline if item.node_name == "cross_ibu_check"
    )
    assert step.detail.startswith("DynamoDB GSI query · ")
    assert "ms ·" in step.detail


def test_demo_seed_is_idempotent_in_memory() -> None:
    async def run() -> tuple[int, list[str]]:
        services = Services.build(Settings())
        for _ in range(2):
            await seed_cross_ibu_registry(services)
            for label in CASES:
                await seed_case(services, label)
        cases = await services.repository.list_cases()
        document_counts = [
            len(await services.repository.list_documents(case_id))
            for case_id, _ibu, _folder in CASES.values()
        ]
        return len(cases), [str(item) for item in document_counts]

    case_count, document_counts = asyncio.run(run())
    assert case_count == 4
    assert document_counts == ["7", "7", "7", "7"]


def test_aws_badge_and_required_make_commands_are_present() -> None:
    badge = (ROOT / "apps" / "web" / "app" / "aws-badge.tsx").read_text()
    makefile = (ROOT / "Makefile").read_text()
    assert all(name in badge for name in ("Deployed on AWS", "ECS", "Textract", "DynamoDB", "S3"))
    for target in ("deploy-staging:", "rollback-staging:", "seed-demo:", "health-check:"):
        assert target in makefile
    terraform = (ROOT / "infra" / "aws" / "main.tf").read_text()
    assert terraform.count("skip_destroy             = true") == 2


def test_backup_video_manifest_has_one_slot_per_scenario() -> None:
    manifest = (ROOT / "docs" / "demo-videos" / "README.md").read_text()
    assert all(f"demo-{number}-" in manifest for number in range(1, 5))


def test_alembic_database_url_escapes_config_interpolation() -> None:
    database_url = "postgresql+asyncpg://user:p%3Cword@db/tradesentry"
    config = Config()
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    assert config.get_main_option("sqlalchemy.url") == database_url
    migration_env = (ROOT / "db" / "migrations" / "env.py").read_text()
    assert 'database_url.replace("%", "%%")' in migration_env
