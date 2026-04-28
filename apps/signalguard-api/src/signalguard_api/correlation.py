"""Correlation-id middleware.

Reads ``X-Correlation-Id`` from the request, falls back to a UUID4, and
stores it in a contextvar so log filters and error handlers can attach the
id without threading the request object through every layer.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_HEADER = "X-Correlation-Id"
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that ensures every request has a correlation id.

    The id is reflected in the response header so callers can correlate a
    failed request against the structured logs server-side.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(CORRELATION_HEADER)
        cid = incoming if incoming else str(uuid.uuid4())
        token = _correlation_id.set(cid)
        try:
            response = await call_next(request)
        finally:
            _correlation_id.reset(token)
        response.headers[CORRELATION_HEADER] = cid
        return response
