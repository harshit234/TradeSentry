from __future__ import annotations

from typing import Protocol

from sqlalchemy import text

from models.compliance import ComplianceResult

from .db import Database


class ComplianceStore(Protocol):
    async def save(self, result: ComplianceResult) -> None: ...
    async def get(self, case_id: str) -> ComplianceResult | None: ...


class InMemoryComplianceStore:
    def __init__(self) -> None:
        self.results: dict[str, ComplianceResult] = {}

    async def save(self, result: ComplianceResult) -> None:
        self.results[result.case_id] = result

    async def get(self, case_id: str) -> ComplianceResult | None:
        return self.results.get(case_id)


class PostgresComplianceStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def save(self, result: ComplianceResult) -> None:
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO compliance_results (case_id, result_json, evaluated_at)
                    VALUES (:case_id, CAST(:result AS JSONB), :evaluated_at)
                    ON CONFLICT (case_id) DO UPDATE SET
                      result_json=EXCLUDED.result_json,
                      evaluated_at=EXCLUDED.evaluated_at"""
                ),
                {
                    "case_id": result.case_id,
                    "result": result.model_dump_json(),
                    "evaluated_at": result.evaluated_at,
                },
            )

    async def get(self, case_id: str) -> ComplianceResult | None:
        async with self.database.engine.connect() as connection:
            value = await connection.scalar(
                text("SELECT result_json FROM compliance_results WHERE case_id=:case_id"),
                {"case_id": case_id},
            )
        return ComplianceResult.model_validate(value) if value else None
