from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Header, HTTPException, Request, UploadFile

from models.contracts import (
    CaseCreate,
    CaseResponse,
    CompletenessStatus,
    DocumentCompleteness,
    DocumentResponse,
    DocumentStatus,
    DocumentType,
    LetterOfCreditFields,
    UploadResponse,
)

from .documents import (
    CaseRecord,
    DocumentRecord,
    DocumentValidationError,
    deterministic_document_id,
    sanitize_filename,
    validate_upload,
)
from .services import Services

router = APIRouter(prefix="/cases", tags=["documents"])


def _services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


async def _case_or_404(request: Request, case_id: str) -> CaseRecord:
    case = await _services(request).repository.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


async def _response(
    services: Services, document: DocumentRecord, include_detail: bool = False
) -> DocumentResponse:
    view_url = await services.storage.presigned_url(document.s3_key) if include_detail else None
    return DocumentResponse(
        document_id=document.id,
        case_id=document.case_id,
        filename=document.filename,
        document_type=document.document_type,
        status=document.status,
        overall_confidence=document.overall_confidence,
        extraction_flags=document.extraction.extraction_flags if document.extraction else [],
        view_url=view_url,
        extraction=document.extraction if include_detail else None,
        error_code=document.error_code,
        advisory=document.advisory,
    )


@router.post("", response_model=CaseResponse, status_code=201)
async def create_case(payload: CaseCreate, request: Request) -> CaseResponse:
    case_id = payload.case_id or f"CASE-{uuid4().hex[:12].upper()}"
    case = await _services(request).repository.create_case(
        CaseRecord(id=case_id, ibu_id=payload.ibu_id)
    )
    return CaseResponse(case_id=case.id, ibu_id=case.ibu_id, status=case.status)


@router.post("/{case_id}/documents", response_model=UploadResponse, status_code=202)
async def upload_document(
    case_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    uploaded_by: Annotated[str, Header(alias="X-Uploaded-By")] = "demo-officer",
) -> UploadResponse:
    await _case_or_404(request, case_id)
    services = _services(request)
    data = await file.read(services.settings.max_upload_bytes + 1)
    try:
        mime_type = validate_upload(data, services.settings.max_upload_bytes)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    digest = hashlib.sha256(data).hexdigest()
    existing = await services.repository.get_by_hash(case_id, digest)
    if existing is not None:
        return UploadResponse(document_id=existing.id, status="UPLOADED")
    document_id = deterministic_document_id(case_id, data)
    filename = sanitize_filename(file.filename, mime_type)
    key = f"cases/{case_id}/documents/{document_id}/{filename}"
    await services.storage.upload(
        data,
        key,
        {
            "case_id": case_id,
            "uploaded_by": uploaded_by[:128],
            "upload_timestamp": datetime.now(UTC).isoformat(),
        },
    )
    document = DocumentRecord(
        id=document_id,
        case_id=case_id,
        filename=filename,
        content_hash=digest,
        mime_type=mime_type,
        s3_key=key,
    )
    await services.repository.save_document(document)
    background_tasks.add_task(services.processor.process, document, data)
    return UploadResponse(document_id=document_id, status="UPLOADED")


@router.get("/{case_id}/documents", response_model=list[DocumentResponse])
async def list_documents(case_id: str, request: Request) -> list[DocumentResponse]:
    await _case_or_404(request, case_id)
    services = _services(request)
    return [
        await _response(services, item)
        for item in await services.repository.list_documents(case_id)
    ]


@router.get("/{case_id}/documents/{document_id}", response_model=DocumentResponse)
async def get_document(case_id: str, document_id: str, request: Request) -> DocumentResponse:
    await _case_or_404(request, case_id)
    services = _services(request)
    document = await services.repository.get_document(case_id, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return await _response(services, document, include_detail=True)


@router.get("/{case_id}/completeness", response_model=DocumentCompleteness)
async def completeness(case_id: str, request: Request) -> DocumentCompleteness:
    await _case_or_404(request, case_id)
    documents = await _services(request).repository.list_documents(case_id)
    completed = {
        document.document_type
        for document in documents
        if document.status in {DocumentStatus.EXTRACTED, DocumentStatus.PARTIAL}
    }
    lc = next(
        (
            document
            for document in documents
            if document.document_type is DocumentType.LETTER_OF_CREDIT
            and document.extraction is not None
        ),
        None,
    )
    if lc is None:
        return DocumentCompleteness(
            required_types=[],
            present_types=sorted(completed, key=str),
            missing_types=[],
            status=CompletenessStatus.PENDING_LC,
            can_run_investigation=False,
        )
    required = list(DocumentType)
    required.remove(DocumentType.UNKNOWN)
    extraction = lc.extraction
    if (
        extraction is not None
        and isinstance(extraction.fields, LetterOfCreditFields)
        and extraction.fields.required_documents
    ):
        required = [
            item.document_type for item in extraction.fields.required_documents if item.required
        ]
    missing = [item for item in required if item not in completed]
    return DocumentCompleteness(
        required_types=required,
        present_types=sorted(completed, key=str),
        missing_types=missing,
        status=CompletenessStatus.INCOMPLETE if missing else CompletenessStatus.COMPLETE,
        can_run_investigation=not missing,
    )
