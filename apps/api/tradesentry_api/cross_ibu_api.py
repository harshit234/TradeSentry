from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Header, HTTPException, Request

from cross_ibu import find_best_match, signal_from_dna
from models.cross_ibu import (
    CrossIBUCaseRequest,
    CrossIBUMatch,
    RegistryRegistration,
    RegistrySignal,
)

from .audit_store import AuditEvent
from .services import Services

router = APIRouter(prefix="/cross-ibu", tags=["cross-ibu"])


def _services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


async def _authorized_signal(
    services: Services, case_id: str, requesting_ibu: str, action: str
) -> RegistrySignal:
    dna = await services.dna_store.get(case_id)
    if dna is None:
        raise HTTPException(status_code=404, detail="Transaction DNA not found")
    if dna.presenting_ibu != requesting_ibu:
        now = datetime.now(UTC)
        await services.audit_store.record(
            AuditEvent(
                case_id=case_id,
                actor_id=requesting_ibu,
                event_type=f"CROSS_IBU_{action}_DENIED",
                payload_ref=f"case://{case_id}",
                created_at=now,
            )
        )
        raise HTTPException(status_code=403, detail="IBU tenant access denied")
    return signal_from_dna(dna)


@router.post("/register", response_model=RegistryRegistration)
async def register_transaction(
    payload: CrossIBUCaseRequest,
    request: Request,
    ibu_id: Annotated[str, Header(alias="X-IBU-ID")],
) -> RegistryRegistration:
    services = _services(request)
    signal = await _authorized_signal(services, payload.case_id, ibu_id, "REGISTER")
    now = datetime.now(UTC)
    registration = await services.cross_ibu_registry.register(signal, now)
    await services.audit_store.record(
        AuditEvent(
            case_id=payload.case_id,
            actor_id=ibu_id,
            event_type="CROSS_IBU_REGISTERED",
            payload_ref=f"registry://{registration.registration_id}",
            created_at=now,
        )
    )
    return registration


@router.post("/query", response_model=CrossIBUMatch)
async def query_registry(
    payload: CrossIBUCaseRequest,
    request: Request,
    ibu_id: Annotated[str, Header(alias="X-IBU-ID")],
) -> CrossIBUMatch:
    services = _services(request)
    signal = await _authorized_signal(services, payload.case_id, ibu_id, "QUERY")
    now = datetime.now(UTC)
    candidates = await services.cross_ibu_registry.find_candidates(signal)
    result = find_best_match(signal, candidates, now)
    await services.audit_store.record(
        AuditEvent(
            case_id=payload.case_id,
            actor_id=ibu_id,
            event_type="CROSS_IBU_QUERIED",
            payload_ref=f"match://{result.match_id}",
            created_at=now,
        )
    )
    return result


@router.get("/registry", response_model=list[RegistryRegistration])
async def list_registry(
    request: Request,
    admin_debug: Annotated[bool, Header(alias="X-Admin-Debug")] = False,
) -> list[RegistryRegistration]:
    if not admin_debug:
        raise HTTPException(status_code=403, detail="Admin debug access required")
    return await _services(request).cross_ibu_registry.list_all()
