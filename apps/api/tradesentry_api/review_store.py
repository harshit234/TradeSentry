from __future__ import annotations

from typing import Protocol

from sqlalchemy import text

from models.review import OfficerDecision

from .db import Database


class ReviewStore(Protocol):
    async def save(self, decision: OfficerDecision) -> None: ...
    async def list_for_case(self, case_id: str) -> list[OfficerDecision]: ...
    async def get_by_idempotency(
        self, case_id: str, key_hash: str
    ) -> OfficerDecision | None: ...


class InMemoryReviewStore:
    def __init__(self) -> None:
        self.decisions: list[OfficerDecision] = []

    async def save(self, decision: OfficerDecision) -> None:
        self.decisions.append(decision.model_copy(deep=True))

    async def list_for_case(self, case_id: str) -> list[OfficerDecision]:
        return [
            item.model_copy(deep=True)
            for item in self.decisions
            if item.case_id == case_id
        ]

    async def get_by_idempotency(
        self, case_id: str, key_hash: str
    ) -> OfficerDecision | None:
        return next(
            (
                item.model_copy(deep=True)
                for item in self.decisions
                if item.case_id == case_id and item.idempotency_key_hash == key_hash
            ),
            None,
        )


class PostgresReviewStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def save(self, decision: OfficerDecision) -> None:
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO officer_decisions
                    (id, case_id, decision, comment, officer_id, officer_role,
                     idempotency_key_hash, created_at)
                    VALUES (:id, :case_id, :decision, :comment, :officer_id, :officer_role,
                            :idempotency_key_hash, :created_at)"""
                ),
                {
                    "id": decision.decision_id,
                    "case_id": decision.case_id,
                    "decision": decision.decision.value,
                    "comment": decision.comment,
                    "officer_id": decision.officer_id,
                    "officer_role": decision.officer_role,
                    "idempotency_key_hash": decision.idempotency_key_hash,
                    "created_at": decision.created_at,
                },
            )

    async def list_for_case(self, case_id: str) -> list[OfficerDecision]:
        async with self.database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT id, case_id, decision, comment, officer_id, officer_role, "
                            "idempotency_key_hash, created_at FROM officer_decisions "
                            "WHERE case_id=:case_id "
                            "ORDER BY created_at"
                        ),
                        {"case_id": case_id},
                    )
                )
                .mappings()
                .all()
            )
        return [
            OfficerDecision(
                decision_id=row["id"], case_id=row["case_id"], decision=row["decision"],
                comment=row["comment"], officer_id=row["officer_id"],
                officer_role=row["officer_role"], created_at=row["created_at"],
                idempotency_key_hash=row["idempotency_key_hash"],
            )
            for row in rows
        ]

    async def get_by_idempotency(
        self, case_id: str, key_hash: str
    ) -> OfficerDecision | None:
        async with self.database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT id, case_id, decision, comment, officer_id, officer_role, "
                            "idempotency_key_hash, created_at FROM officer_decisions "
                            "WHERE case_id=:case_id AND idempotency_key_hash=:key_hash"
                        ),
                        {"case_id": case_id, "key_hash": key_hash},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return OfficerDecision(
            decision_id=row["id"], case_id=row["case_id"], decision=row["decision"],
            comment=row["comment"], officer_id=row["officer_id"],
            officer_role=row["officer_role"],
            idempotency_key_hash=row["idempotency_key_hash"], created_at=row["created_at"],
        )
