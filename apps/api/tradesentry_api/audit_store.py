from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import uuid4

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text

from .auth import Principal
from .db import Database
from .logging import case_id_var, correlation_id_var, event_type_var, ibu_id_var

logger = logging.getLogger(__name__)


def _log_event(event: AuditEvent) -> None:
    case_token = case_id_var.set(event.case_id or "system")
    ibu_token = ibu_id_var.set(event.ibu_id)
    event_token = event_type_var.set(event.event_type.value)
    try:
        logger.info("Audit event recorded")
    finally:
        event_type_var.reset(event_token)
        ibu_id_var.reset(ibu_token)
        case_id_var.reset(case_token)


class AuditEventType(StrEnum):
    CASE_CREATED = "CASE_CREATED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_CLASSIFIED = "DOCUMENT_CLASSIFIED"
    DOCUMENT_EXTRACTED = "DOCUMENT_EXTRACTED"
    LC_PARSED = "LC_PARSED"
    COMPLETENESS_CHECKED = "COMPLETENESS_CHECKED"
    UCP_RULE_EXECUTED = "UCP_RULE_EXECUTED"
    TRANSACTION_DNA_BUILT = "TRANSACTION_DNA_BUILT"
    CROSS_IBU_QUERIED = "CROSS_IBU_QUERIED"
    CROSS_IBU_REGISTERED = "CROSS_IBU_REGISTERED"
    TOOL_CALLED = "TOOL_CALLED"
    AGENT_DECISION = "AGENT_DECISION"
    RISK_SCORED = "RISK_SCORED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    OFFICER_DECISION = "OFFICER_DECISION"
    SETTLEMENT_STATUS_CHANGED = "SETTLEMENT_STATUS_CHANGED"
    PRESIGNED_URL_GENERATED = "PRESIGNED_URL_GENERATED"
    AUTH_FAILURE = "AUTH_FAILURE"


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str = Field(default_factory=lambda: correlation_id_var.get())
    case_id: str | None
    ibu_id: str = "system"
    actor_id: str
    actor_role: str = "SYSTEM"
    event_type: AuditEventType
    payload_ref: str
    ip_address: str = "system"
    user_agent: str = "system"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("payload_ref")
    @classmethod
    def reference_must_not_be_sensitive(cls, value: str) -> str:
        lowered = value.lower()
        forbidden = ("http://", "https://", "x-amz-signature", "bearer ", "api_key", "secret=")
        if any(marker in lowered for marker in forbidden):
            raise ValueError("Audit payload_ref must be an opaque reference, never sensitive data")
        return value


def event_from_request(
    request: Request,
    *,
    event_type: AuditEventType,
    payload_ref: str,
    case_id: str | None = None,
    principal: Principal | None = None,
) -> AuditEvent:
    current = principal or getattr(request.state, "principal", None)
    if isinstance(current, Principal):
        actor_id, actor_role, ibu_id = current.officer_id, current.role, current.ibu_id
    else:
        actor_id, actor_role, ibu_id = "system", "SYSTEM", "system"
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:24]
    user_agent = request.headers.get("User-Agent", "unknown")[:160]
    return AuditEvent(
        case_id=case_id,
        ibu_id=ibu_id,
        actor_id=actor_id,
        actor_role=actor_role,
        event_type=event_type,
        payload_ref=payload_ref,
        ip_address=f"sha256:{ip_hash}",
        user_agent=user_agent,
    )


class AuditStore(Protocol):
    async def record(self, event: AuditEvent) -> None: ...
    async def count(self, event_type: str | None = None) -> int: ...
    async def list_events(self, ibu_id: str | None = None) -> list[AuditEvent]: ...


class InMemoryAuditStore:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        self.events.append(event.model_copy(deep=True))
        _log_event(event)

    async def count(self, event_type: str | None = None) -> int:
        return sum(
            1 for event in self.events if event_type is None or event.event_type.value == event_type
        )

    async def list_events(self, ibu_id: str | None = None) -> list[AuditEvent]:
        return [
            event.model_copy(deep=True)
            for event in self.events
            if ibu_id is None or event.ibu_id == ibu_id
        ]


class PostgresAuditStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def record(self, event: AuditEvent) -> None:
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO audit_events
                    (event_id, correlation_id, case_id, ibu_id, actor_id, actor_role,
                     event_type, payload_ref, ip_address, user_agent, created_at)
                    VALUES (:event_id, :correlation_id, :case_id, :ibu_id, :actor_id,
                            :actor_role, :event_type, :payload_ref, :ip_address,
                            :user_agent, :created_at)"""
                ),
                {
                    **event.model_dump(exclude={"event_type"}),
                    "event_type": event.event_type.value,
                },
            )
        _log_event(event)

    async def count(self, event_type: str | None = None) -> int:
        statement = "SELECT count(*) FROM audit_events"
        parameters: dict[str, str] = {}
        if event_type is not None:
            statement += " WHERE event_type=:event_type"
            parameters["event_type"] = event_type
        async with self.database.engine.connect() as connection:
            value = await connection.scalar(text(statement), parameters)
        return int(value or 0)

    async def list_events(self, ibu_id: str | None = None) -> list[AuditEvent]:
        statement = "SELECT * FROM audit_events"
        parameters: dict[str, str] = {}
        if ibu_id is not None:
            statement += " WHERE ibu_id=:ibu_id"
            parameters["ibu_id"] = ibu_id
        statement += " ORDER BY created_at DESC"
        async with self.database.engine.connect() as connection:
            rows = (await connection.execute(text(statement), parameters)).mappings().all()
        return [AuditEvent.model_validate(dict(row)) for row in rows]
