from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models.contracts import HealthResponse

from .api import router as document_router
from .audit_api import router as audit_router
from .audit_store import AuditEventType, event_from_request
from .auth import authenticate, require_viewer
from .compliance_api import router as compliance_router
from .config import Settings
from .cross_ibu_api import router as cross_ibu_router
from .dashboard_api import router as dashboard_router
from .dna_api import router as dna_router
from .errors import install_exception_handlers
from .investigation_api import router as investigation_router
from .logging import case_id_var, configure_logging, correlation_id_var, ibu_id_var
from .services import Checkable, Services
from .telemetry import configure_telemetry


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    app_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.services = services or Services.build(app_settings)
        yield
        await app.state.services.close()

    configure_logging(app_settings.log_level)
    configure_telemetry(app_settings.app_name)
    app = FastAPI(title=app_settings.app_name, version=app_settings.version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "X-Correlation-ID",
            "X-Uploaded-By",
            "X-IBU-ID",
            "X-Admin-Debug",
            "Authorization",
            "Idempotency-Key",
        ],
    )

    @app.middleware("http")
    async def security_and_correlation_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        correlation_token = correlation_id_var.set(correlation_id)
        path_parts = [part for part in request.url.path.split("/") if part]
        case_token = case_id_var.set(
            path_parts[1] if len(path_parts) > 1 and path_parts[0] == "cases" else "system"
        )
        ibu_token = ibu_id_var.set("system")
        try:
            current: Services = request.app.state.services
            protected = request.url.path == "/cases" or request.url.path.startswith(
                ("/cases/", "/cross-ibu", "/audit-events")
            )
            client_ip = request.client.host if request.client else "unknown"
            if not await current.rate_limiter.allow(
                f"ip:{client_ip}", app_settings.rate_limit_ip_per_minute
            ):
                return JSONResponse(status_code=429, content={"detail": "IP rate limit exceeded"})
            if protected:
                try:
                    principal = authenticate(request.headers.get("Authorization"), app_settings)
                    require_viewer(principal)
                except HTTPException as exc:
                    await current.audit_store.record(
                        event_from_request(
                            request,
                            event_type=AuditEventType.AUTH_FAILURE,
                            payload_ref=f"auth://failure/{exc.status_code}",
                        )
                    )
                    return JSONResponse(
                        status_code=exc.status_code,
                        content={"detail": exc.detail},
                        headers=exc.headers,
                    )
                request.state.principal = principal
                ibu_id_var.set(principal.ibu_id)
                if not await current.rate_limiter.allow(
                    f"user:{principal.officer_id}", app_settings.rate_limit_user_per_minute
                ):
                    return JSONResponse(
                        status_code=429, content={"detail": "User rate limit exceeded"}
                    )
                is_upload = (
                    request.method == "POST"
                    and request.url.path.startswith("/cases/")
                    and request.url.path.endswith("/documents")
                )
                if is_upload and not await current.rate_limiter.allow(
                    f"upload:{principal.officer_id}",
                    app_settings.rate_limit_upload_per_minute,
                ):
                    return JSONResponse(
                        status_code=429, content={"detail": "Upload rate limit exceeded"}
                    )
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            ibu_id_var.reset(ibu_token)
            case_id_var.reset(case_token)
            correlation_id_var.reset(correlation_token)

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        current: Services = request.app.state.services

        async def status(checkable: Checkable) -> Literal["ok", "unavailable"]:
            try:
                return "ok" if await checkable.check() else "unavailable"
            except Exception:  # noqa: BLE001 - a health check must degrade, not crash
                return "unavailable"

        db_status = await status(current.db)
        redis_status = await status(current.redis)
        s3_status = await status(current.storage)
        textract_status = await status(current.textract)
        overall: Literal["ok", "degraded"] = (
            "ok"
            if all(value == "ok" for value in (db_status, redis_status, s3_status, textract_status))
            else "degraded"
        )
        return HealthResponse(
            status=overall,
            db=db_status,
            redis=redis_status,
            s3=s3_status,
            textract=textract_status,
            version=app_settings.version,
            aws_region=app_settings.aws_region,
            deployment=app_settings.deployment,
        )

    install_exception_handlers(app)
    app.include_router(document_router)
    app.include_router(compliance_router)
    app.include_router(dna_router)
    app.include_router(cross_ibu_router)
    app.include_router(investigation_router)
    app.include_router(dashboard_router)
    app.include_router(audit_router)
    return app


app = create_app()
