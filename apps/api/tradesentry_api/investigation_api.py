from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException, Request

from agents.planner import BedrockTriagePlanner, DeterministicTriagePlanner, TriagePlanner
from models.investigation import InvestigationResponse, InvestigationRunRequest

from .auth import ADMIN, request_principal, require_roles
from .investigation_orchestrator import InvestigationOrchestrator
from .services import Services

router = APIRouter(prefix="/cases", tags=["investigation"])


def _services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


async def _authorize(services: Services, case_id: str, ibu_id: str) -> None:
    case = await services.repository.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.ibu_id != ibu_id:
        raise HTTPException(status_code=403, detail="IBU tenant access denied")


@router.post("/{case_id}/run", response_model=InvestigationResponse)
async def run_investigation(
    case_id: str,
    request: Request,
    payload: InvestigationRunRequest | None = None,
) -> InvestigationResponse:
    services = _services(request)
    principal = request_principal(request)
    require_roles(principal, ADMIN)
    await _authorize(services, case_id, principal.ibu_id)
    planner: TriagePlanner = (
        BedrockTriagePlanner(services.settings.aws_region, services.settings.bedrock_model_id)
        if services.settings.bedrock_model_id
        else DeterministicTriagePlanner(services.settings.price_triage_threshold_usd)
    )
    orchestrator = InvestigationOrchestrator(
        services,
        planner,
        tool_timeout_seconds=services.settings.investigation_tool_timeout_seconds,
        default_tool_budget=services.settings.investigation_tool_budget,
    )
    return await orchestrator.run(
        case_id,
        principal.ibu_id,
        tool_budget=None if payload is None else payload.tool_budget,
    )


@router.get("/{case_id}/investigation", response_model=InvestigationResponse)
async def get_investigation(
    case_id: str,
    request: Request,
) -> InvestigationResponse:
    services = _services(request)
    principal = request_principal(request)
    await _authorize(services, case_id, principal.ibu_id)
    result = await services.investigation_store.get(case_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return result
