"""Narrative read and regenerate endpoints.

GET returns the cached narrative if it exists and synchronously generates
on miss. POST /regenerate force-regenerates and is dev-key-only because it
costs real money.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import duckdb
from cstack_audit_core import AffectedObject, Finding, Severity
from cstack_llm_narrative import NarrativeGenerator
from cstack_llm_provider import get_provider
from cstack_llm_provider import get_settings as get_llm_settings
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from signalguard_api.auth import ApiCaller, require_api_key, require_tenant_access
from signalguard_api.dependencies import get_db_connection

LOG = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tenants/{tenant_id}/findings/{finding_id}/narrative",
    tags=["narratives"],
)


class NarrativeResponse(BaseModel):
    markdown: str
    model: str
    provider: str
    generated_at: datetime
    cached: bool
    input_tokens: int
    output_tokens: int


class RegenerateRequest(BaseModel):
    prompt_version: str = Field(default="v1")
    model: str | None = None


def _row_to_finding(row: tuple[Any, ...]) -> Finding:
    return Finding(
        id=row[0],
        tenant_id=row[1],
        rule_id=row[2],
        category=row[3],
        severity=Severity(row[4]),
        title=row[5],
        summary=row[6],
        affected_objects=[AffectedObject.model_validate(o) for o in json.loads(row[7])],
        evidence=json.loads(row[8]),
        remediation_hint=row[9],
        references=json.loads(row[10]),
        detected_at=row[11],
        first_seen_at=row[12],
    )


def _load_finding(conn: duckdb.DuckDBPyConnection, tenant_id: str, finding_id: str) -> Finding:
    row = conn.execute(
        """
        SELECT id, tenant_id, rule_id, category, severity, title, summary,
               affected_objects, evidence, remediation_hint, "references",
               detected_at, first_seen_at
        FROM findings WHERE tenant_id = ? AND id = ?
        """,
        [tenant_id, finding_id],
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"finding '{finding_id}' not found for tenant '{tenant_id}'",
        )
    return _row_to_finding(row)


@router.get(
    "",
    response_model=NarrativeResponse,
    summary="Read or generate a finding narrative",
)
async def get_narrative(
    tenant_id: str = Depends(require_tenant_access),
    finding_id: str = "",
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> NarrativeResponse:
    finding = await asyncio.to_thread(_load_finding, conn, tenant_id, finding_id)

    settings = get_llm_settings()
    provider = get_provider(settings.cstack_llm_provider)
    generator = NarrativeGenerator(
        provider=provider,
        connection=conn,
        default_model=settings.cstack_llm_default_model,
    )
    narrative = await generator.generate(finding)
    return NarrativeResponse(
        markdown=narrative.markdown,
        model=narrative.model,
        provider=narrative.provider,
        generated_at=narrative.generated_at,
        cached=narrative.cached,
        input_tokens=narrative.input_tokens,
        output_tokens=narrative.output_tokens,
    )


@router.post(
    "/regenerate",
    response_model=NarrativeResponse,
    summary="Force-regenerate a narrative (dev key only)",
    description=(
        "Bypasses the cache and replaces any existing entry on success. "
        "Restricted to dev callers because it spends real money on every "
        "invocation."
    ),
)
async def regenerate_narrative(
    body: RegenerateRequest,
    tenant_id: str = Depends(require_tenant_access),
    finding_id: str = "",
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
    caller: ApiCaller = Depends(require_api_key),
) -> NarrativeResponse:
    if caller.kind != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="dev API key required for regenerate",
        )

    finding = await asyncio.to_thread(_load_finding, conn, tenant_id, finding_id)
    settings = get_llm_settings()
    provider = get_provider(settings.cstack_llm_provider)
    generator = NarrativeGenerator(
        provider=provider,
        connection=conn,
        default_model=settings.cstack_llm_default_model,
    )
    narrative = await generator.generate(
        finding,
        prompt_version=body.prompt_version,
        model=body.model,
        force=True,
    )
    LOG.info(
        "narrative regenerated",
        extra={
            "tenant_id": tenant_id,
            "finding_id": finding_id,
            "prompt_version": body.prompt_version,
            "model": narrative.model,
            "input_tokens": narrative.input_tokens,
            "output_tokens": narrative.output_tokens,
            "caller": caller.key_label,
        },
    )
    return NarrativeResponse(
        markdown=narrative.markdown,
        model=narrative.model,
        provider=narrative.provider,
        generated_at=narrative.generated_at,
        cached=False,
        input_tokens=narrative.input_tokens,
        output_tokens=narrative.output_tokens,
    )
