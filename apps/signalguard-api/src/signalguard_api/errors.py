"""RFC 7807-style problem-detail error model and exception handlers.

The shape:

    {
        "type": "https://signalguard.dev/errors/not-found",
        "title": "Not Found",
        "status": 404,
        "detail": "tenant 'foo' not registered",
        "correlation_id": "abc-123",
        "instance": "/tenants/foo"
    }

Routers raise either FastAPI's ``HTTPException`` or one of the typed
exceptions below; the global handler in :mod:`signalguard_api.main` shapes
both into the problem-detail response.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from signalguard_api.correlation import get_correlation_id


class ProblemDetail(BaseModel):
    """RFC 7807-aligned error envelope. Always serialised as JSON."""

    model_config = ConfigDict(populate_by_name=True)

    type: str
    title: str
    status: int
    detail: str
    correlation_id: str
    instance: str | None = None


_DEFAULT_TITLES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Unprocessable Entity",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


def _problem(
    status_code: int,
    detail: str,
    instance: str | None,
    type_slug: str,
) -> JSONResponse:
    payload = ProblemDetail(
        type=f"https://signalguard.dev/errors/{type_slug}",
        title=_DEFAULT_TITLES.get(status_code, "Error"),
        status=status_code,
        detail=detail,
        correlation_id=get_correlation_id(),
        instance=instance,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
        media_type="application/problem+json",
    )


class APIProblem(Exception):
    """Domain-shaped error. Sub-class to avoid sprinkling status codes."""

    status_code: int = 500
    type_slug: str = "internal"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(APIProblem):
    status_code = 404
    type_slug = "not-found"


class AuthError(APIProblem):
    status_code = 401
    type_slug = "unauthorized"


class ForbiddenError(APIProblem):
    status_code = 403
    type_slug = "forbidden"


class ValidationProblem(APIProblem):
    status_code = 422
    type_slug = "validation"


class ConflictError(APIProblem):
    status_code = 409
    type_slug = "conflict"


class ServiceUnavailableError(APIProblem):
    status_code = 503
    type_slug = "service-unavailable"


def _slug_for_status(status_code: int) -> str:
    return _DEFAULT_TITLES.get(status_code, "error").lower().replace(" ", "-")


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Shape any HTTPException-derived error into RFC 7807 JSON."""
    if not isinstance(exc, StarletteHTTPException):
        return await unhandled_exception_handler(request, exc)
    detail_value: Any = exc.detail
    detail = detail_value if isinstance(detail_value, str) else str(detail_value or "")
    return _problem(
        status_code=exc.status_code,
        detail=detail,
        instance=str(request.url.path),
        type_slug=_slug_for_status(exc.status_code),
    )


async def starlette_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return await http_exception_handler(request, exc)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await unhandled_exception_handler(request, exc)
    return _problem(
        status_code=422,
        detail=str(exc.errors()),
        instance=str(request.url.path),
        type_slug="validation",
    )


async def api_problem_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, APIProblem):
        return await unhandled_exception_handler(request, exc)
    return _problem(
        status_code=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path),
        type_slug=exc.type_slug,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort: never leak a stack trace into the response body."""
    _ = exc
    return _problem(
        status_code=500,
        detail="internal server error; check logs with the correlation id",
        instance=str(request.url.path),
        type_slug="internal",
    )
