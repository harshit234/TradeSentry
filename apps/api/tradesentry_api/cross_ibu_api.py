from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, HTTPException, Request

from cross_ibu import find_best_match, signal_from_dna
from models.cross_ibu import (
    CrossIBUCaseRequest,
    CrossIBUMatch,
    RegistryRegistration,
    RegistrySignal,
)

from .audit_store import AuditEventType, event_from_request
from .auth import ADMIN, COMPLIANCE_MANAGER, request_principal, require_roles
from .services import Services

router = APIRouter(prefix="/cross-ibu", tags=["cross-ibu"])
logger = logging.getLogger(__name__)


def _services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


async def _authorized_signal(
    request: Request, services: Services, case_id: str, requesting_ibu: str
) -> RegistrySignal:
    dna = await services.dna_store.get(case_id)
    if dna is None:
        raise HTTPException(status_code=404, detail="Transaction DNA not found")
    if dna.presenting_ibu != requesting_ibu:
        await services.audit_store.record(
            event_from_request(
                request,
                event_type=AuditEventType.AUTH_FAILURE,
                case_id=case_id,
                payload_ref=f"auth://ibu-denied/{case_id}",
            )
        )
        raise HTTPException(status_code=403, detail="IBU tenant access denied")
    return signal_from_dna(dna)


@router.post("/register", response_model=RegistryRegistration)
async def register_transaction(
    payload: CrossIBUCaseRequest,
    request: Request,
) -> RegistryRegistration:
    services = _services(request)
    principal = request_principal(request)
    require_roles(principal, ADMIN)
    signal = await _authorized_signal(request, services, payload.case_id, principal.ibu_id)
    now = datetime.now(UTC)
    registration = await services.cross_ibu_registry.register(signal, now)
    await services.audit_store.record(
        event_from_request(
            request,
            event_type=AuditEventType.CROSS_IBU_REGISTERED,
            case_id=payload.case_id,
            payload_ref=f"registry://{registration.registration_id}",
        )
    )
    return registration


@router.post("/query", response_model=CrossIBUMatch)
async def query_registry(
    payload: CrossIBUCaseRequest,
    request: Request,
) -> CrossIBUMatch:
    services = _services(request)
    principal = request_principal(request)
    require_roles(principal, COMPLIANCE_MANAGER, ADMIN)
    signal = await _authorized_signal(request, services, payload.case_id, principal.ibu_id)
    now = datetime.now(UTC)
    candidates = await services.cross_ibu_registry.find_candidates(signal)
    result = find_best_match(signal, candidates, now)
    logger.info(
        "Cross-IBU signal query completed",
        extra={"cross_ibu_match_rate": 0 if result.match_level.value == "NONE" else 1},
    )
    await services.audit_store.record(
        event_from_request(
            request,
            event_type=AuditEventType.CROSS_IBU_QUERIED,
            case_id=payload.case_id,
            payload_ref=f"match://{result.match_id}",
        )
    )
    return result


@router.get("/registry", response_model=list[RegistryRegistration])
async def list_registry(request: Request) -> list[RegistryRegistration]:
    principal = request_principal(request)
    require_roles(principal, ADMIN)
    return await _services(request).cross_ibu_registry.list_all()
