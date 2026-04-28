"""Audit run and dry-run endpoints."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime

import duckdb
from cstack_audit_core import Finding, write_findings
from cstack_audit_coverage import compute_coverage, findings_from_coverage
from cstack_audit_exclusions import analyse_exclusions
from cstack_audit_rules import load_context_from_db, run_all_rules
from fastapi import APIRouter, Depends

from signalguard_api.auth import require_tenant_access
from signalguard_api.dependencies import get_db_connection
from signalguard_api.schemas.actions import (
    AuditDryRunResponse,
    AuditRunRequest,
    AuditRunResponse,
)

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants/{tenant_id}/audit", tags=["audit"])


def _category_findings(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    categories: list[str],
) -> dict[str, list[Finding]]:
    """Compute findings for each requested category. Pure read on the DB."""
    ctx = load_context_from_db(conn, tenant_id, as_of=datetime.now(UTC))
    out: dict[str, list[Finding]] = {}
    if "coverage" in categories:
        matrix = compute_coverage(
            ctx.tenant_id,
            ctx.policies,
            ctx.users,
            ctx.groups,
            ctx.roles,
            ctx.role_assignments,
            as_of=ctx.as_of,
        )
        out["coverage"] = findings_from_coverage(matrix, ctx.tenant_id)
    if "rules" in categories:
        out["rules"] = run_all_rules(ctx)
    if "exclusions" in categories:
        out["exclusions"] = analyse_exclusions(ctx)
    return out


@router.post(
    "/run",
    response_model=AuditRunResponse,
    summary="Execute audit categories and persist findings",
    description=(
        "Runs the requested audit modules synchronously, writes findings via "
        "the deduplicated insert helper, and returns a per-category count plus "
        "the run id for log correlation."
    ),
)
async def run_audit(
    body: AuditRunRequest,
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> AuditRunResponse:
    if not body.categories:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail="categories must contain at least one value",
        )
    run_id = str(uuid.uuid4())
    started = time.perf_counter()

    def _execute() -> tuple[int, dict[str, int]]:
        bundle = _category_findings(conn, tenant_id, list(body.categories))
        per_category: dict[str, int] = {}
        total_written = 0
        for category, findings in bundle.items():
            written = write_findings(conn, findings)
            per_category[category] = len(findings)
            total_written += written
        return total_written, per_category

    findings_written, by_category = await asyncio.to_thread(_execute)
    duration = time.perf_counter() - started
    LOG.info(
        "audit run completed",
        extra={
            "tenant_id": tenant_id,
            "run_id": run_id,
            "findings_written": findings_written,
            "duration_seconds": round(duration, 3),
        },
    )
    return AuditRunResponse(
        findings_written=findings_written,
        by_category=by_category,
        duration_seconds=duration,
        run_id=run_id,
    )


@router.post(
    "/dry-run",
    response_model=AuditDryRunResponse,
    summary="Compute findings without persisting them",
    description=(
        "Useful for previewing what an audit run would produce against the "
        "current data without writing rows to the findings table."
    ),
)
async def dry_run(
    body: AuditRunRequest,
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> AuditDryRunResponse:
    run_id = str(uuid.uuid4())

    def _execute() -> tuple[list[Finding], dict[str, int]]:
        bundle = _category_findings(conn, tenant_id, list(body.categories))
        per_category = {cat: len(findings) for cat, findings in bundle.items()}
        all_findings: list[Finding] = []
        for findings in bundle.values():
            all_findings.extend(findings)
        return all_findings, per_category

    findings, by_category = await asyncio.to_thread(_execute)
    LOG.info(
        "audit dry-run completed",
        extra={
            "tenant_id": tenant_id,
            "run_id": run_id,
            "findings_count": len(findings),
        },
    )
    return AuditDryRunResponse(findings=findings, by_category=by_category, run_id=run_id)
