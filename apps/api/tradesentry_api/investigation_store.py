from __future__ import annotations

from typing import Protocol

from sqlalchemy import text

from models.investigation import InvestigationResponse

from .db import Database


class InvestigationStore(Protocol):
    async def save(self, response: InvestigationResponse) -> None: ...
    async def get(self, case_id: str) -> InvestigationResponse | None: ...


class InMemoryInvestigationStore:
    def __init__(self) -> None:
        self.results: dict[str, InvestigationResponse] = {}

    async def save(self, response: InvestigationResponse) -> None:
        self.results[response.state.case_id] = response.model_copy(deep=True)

    async def get(self, case_id: str) -> InvestigationResponse | None:
        result = self.results.get(case_id)
        return result.model_copy(deep=True) if result else None


class PostgresInvestigationStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def save(self, response: InvestigationResponse) -> None:
        state = response.state
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO investigation_states
                    (case_id, state_json, workflow_status, updated_at)
                    VALUES (:case_id, CAST(:state AS JSONB), :workflow_status, now())
                    ON CONFLICT (case_id) DO UPDATE SET
                      state_json=EXCLUDED.state_json,
                      workflow_status=EXCLUDED.workflow_status,
                      updated_at=now()"""
                ),
                {
                    "case_id": state.case_id,
                    "state": state.model_dump_json(),
                    "workflow_status": response.workflow_status,
                },
            )
            if state.recommended_action is not None:
                await connection.execute(
                    text("UPDATE cases SET status=:status, updated_at=now() WHERE id=:case_id"),
                    {"status": state.recommended_action, "case_id": state.case_id},
                )

    async def get(self, case_id: str) -> InvestigationResponse | None:
        async with self.database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT state_json, workflow_status FROM investigation_states "
                            "WHERE case_id=:case_id"
                        ),
                        {"case_id": case_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return InvestigationResponse.model_validate(
            {"state": row["state_json"], "workflow_status": row["workflow_status"]}
        )

