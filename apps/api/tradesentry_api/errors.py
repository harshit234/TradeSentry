from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from models.contracts import ProblemDetail

from .logging import correlation_id_var


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        problem = ProblemDetail(
            title="Internal Server Error",
            status=500,
            detail="The request could not be completed.",
            instance=request.url.path,
            correlation_id=correlation_id_var.get(),
        )
        return JSONResponse(
            status_code=500,
            content=problem.model_dump(),
            media_type="application/problem+json",
        )
