from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from sqlalchemy import text

from .db import Database


@dataclass(frozen=True, slots=True)
class AuditEvent:
    case_id: str | None
    actor_id: str
    event_type: str
    payload_ref: str
    created_at: datetime


class AuditStore(Protocol):
    async def record(self, event: AuditEvent) -> None: ...
    async def count(self, event_type: str | None = None) -> int: ...


class InMemoryAuditStore:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        self.events.append(event)

    async def count(self, event_type: str | None = None) -> int:
        return sum(
            1 for event in self.events if event_type is None or event.event_type == event_type
        )


class PostgresAuditStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def record(self, event: AuditEvent) -> None:
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO audit_events
                    (id, case_id, actor_id, event_type, payload_ref, created_at)
                    VALUES (:id, :case_id, :actor_id, :event_type, :payload_ref, :created_at)"""
                ),
                {
                    "id": f"audit-{uuid4().hex}",
                    "case_id": event.case_id,
                    "actor_id": event.actor_id,
                    "event_type": event.event_type,
                    "payload_ref": event.payload_ref,
                    "created_at": event.created_at,
                },
            )

    async def count(self, event_type: str | None = None) -> int:
        statement = "SELECT count(*) FROM audit_events"
        parameters: dict[str, str] = {}
        if event_type is not None:
            statement += " WHERE event_type=:event_type"
            parameters["event_type"] = event_type
        async with self.database.engine.connect() as connection:
            value = await connection.scalar(text(statement), parameters)
        return int(value or 0)
