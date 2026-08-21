from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from models.contracts import HealthResponse

from .api import router as document_router
from .config import Settings
from .errors import install_exception_handlers
from .logging import configure_logging, correlation_id_var
from .services import Checkable, Services


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    app_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.services = services or Services.build(app_settings)
        yield
        await app.state.services.close()

    configure_logging(app_settings.log_level)
    app = FastAPI(title=app_settings.app_name, version=app_settings.version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Correlation-ID", "X-Uploaded-By"],
    )

    @app.middleware("http")
    async def correlation_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        token = correlation_id_var.set(correlation_id)
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            correlation_id_var.reset(token)

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
    return app


app = create_app()
