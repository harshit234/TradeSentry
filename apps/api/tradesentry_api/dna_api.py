from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, HTTPException, Request

from dna import build_transaction_dna
from models.contracts import ExtractionResult
from models.dna import TransactionDNA

from .services import Services

router = APIRouter(prefix="/cases", tags=["transaction-dna"])


def _services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


@router.post("/{case_id}/transaction-dna", response_model=TransactionDNA)
async def create_transaction_dna(case_id: str, request: Request) -> TransactionDNA:
    services = _services(request)
    case = await services.repository.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    documents = await services.repository.list_documents(case_id)
    extractions: list[ExtractionResult] = [
        document.extraction for document in documents if document.extraction is not None
    ]
    if not extractions:
        raise HTTPException(status_code=422, detail="Extracted document fields are required")
    result = build_transaction_dna(case_id, case.ibu_id, extractions, datetime.now(UTC))
    await services.dna_store.save(result)
    return result


@router.get("/{case_id}/transaction-dna", response_model=TransactionDNA)
async def get_transaction_dna(case_id: str, request: Request) -> TransactionDNA:
    result = await _services(request).dna_store.get(case_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Transaction DNA not found")
    return result
