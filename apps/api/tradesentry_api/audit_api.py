from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request

from .audit_store import AuditEvent
from .auth import ADMIN, AUDITOR, request_principal, require_roles
from .services import Services

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=list[AuditEvent])
async def list_audit_events(request: Request) -> list[AuditEvent]:
    services = cast(Services, request.app.state.services)
    principal = request_principal(request)
    require_roles(principal, AUDITOR, ADMIN)
    return await services.audit_store.list_events(
        None if principal.role == ADMIN else principal.ibu_id
    )
