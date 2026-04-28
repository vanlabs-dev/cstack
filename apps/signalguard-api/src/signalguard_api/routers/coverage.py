"""Coverage matrix endpoint. Recomputes on demand from normalised tables."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import duckdb
from cstack_audit_coverage import CoverageMatrix, compute_coverage
from cstack_audit_rules import load_context_from_db
from fastapi import APIRouter, Depends

from signalguard_api.auth import require_tenant_access
from signalguard_api.dependencies import get_db_connection

router = APIRouter(prefix="/tenants/{tenant_id}/coverage-matrix", tags=["coverage"])


@router.get(
    "",
    response_model=CoverageMatrix,
    summary="Compute the user/app coverage matrix on demand",
    description=(
        "Coverage is cheap to compute (in-memory over the normalised tables) "
        "so the API recomputes per request rather than caching. This makes "
        "the response always reflect the current policy + directory state."
    ),
)
async def get_coverage(
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> CoverageMatrix:
    def _query() -> CoverageMatrix:
        ctx = load_context_from_db(conn, tenant_id, as_of=datetime.now(UTC))
        return compute_coverage(
            ctx.tenant_id,
            ctx.policies,
            ctx.users,
            ctx.groups,
            ctx.roles,
            ctx.role_assignments,
            as_of=ctx.as_of,
        )

    return await asyncio.to_thread(_query)
