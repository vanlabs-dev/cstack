"""Health and readiness endpoints.

``/healthz`` is the always-200 liveness probe so a stuck DB does not page the
service. ``/readyz`` opens a DuckDB connection to confirm the storage layer
is reachable; container orchestrators should gate traffic on this one.
"""

from __future__ import annotations

import logging

from cstack_storage import run_migrations
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

LOG = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe", description="Always 200 if the process is up.")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/readyz",
    summary="Readiness probe",
    description="Opens a DuckDB connection and runs a trivial query.",
)
async def readyz(request: Request) -> JSONResponse:
    factory = request.app.state.connection_factory
    try:
        conn = factory()
        try:
            run_migrations(conn)
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
    except Exception:
        LOG.exception("readyz: db check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "db": "error"},
        )
    return JSONResponse(status_code=200, content={"status": "ready", "db": "ok"})
