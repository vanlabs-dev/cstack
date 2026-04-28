"""Tenant inventory endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
from cstack_schemas import TenantApiKey, TenantConfig
from cstack_storage import get_tenant_db, list_tenants_db
from fastapi import APIRouter, Depends, HTTPException, status

from signalguard_api.auth import require_dev, require_tenant_access
from signalguard_api.config import Settings, get_settings
from signalguard_api.dependencies import get_db_connection
from signalguard_api.schemas.api_keys import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeySummary,
)
from signalguard_api.schemas.tenant import TenantDetail, TenantSummary

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _load_tenants_file(path: Path) -> list[TenantConfig]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    payload = json.loads(raw)
    if not isinstance(payload, list):
        return []
    return [TenantConfig.model_validate(item) for item in payload]


def _save_tenants_file(path: Path, tenants: list[TenantConfig]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [t.model_dump(mode="json") for t in tenants]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _last_extract_at(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> datetime | None:
    row = conn.execute(
        "SELECT MAX(ingested_at) FROM raw_ingestions WHERE tenant_id = ?",
        [tenant_id],
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _last_audit_at(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> datetime | None:
    row = conn.execute(
        """
        SELECT MAX(detected_at) FROM findings
        WHERE tenant_id = ? AND category != 'anomaly'
        """,
        [tenant_id],
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _last_anomaly_at(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> datetime | None:
    row = conn.execute(
        "SELECT MAX(scored_at) FROM anomaly_scores WHERE tenant_id = ?",
        [tenant_id],
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _api_key_count(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> int:
    """Tenants.json holds the keys; API never reads from the DB for this. Returns
    0 here as a sentinel because the DB-listed tenants do not carry keys."""
    _ = (conn, tenant_id)
    return 0


def _build_summary(conn: duckdb.DuckDBPyConnection, tenant: Any) -> TenantSummary:
    return TenantSummary(
        tenant_id=tenant.tenant_id,
        display_name=tenant.display_name,
        is_fixture=tenant.is_fixture,
        added_at=tenant.added_at,
        last_extract_at=_last_extract_at(conn, tenant.tenant_id),
        last_audit_at=_last_audit_at(conn, tenant.tenant_id),
        last_anomaly_score_at=_last_anomaly_at(conn, tenant.tenant_id),
        api_key_count=_api_key_count(conn, tenant.tenant_id),
    )


@router.get(
    "",
    response_model=list[TenantSummary],
    summary="List registered tenants",
    description="Dev-only endpoint that returns every tenant the storage layer knows about.",
    dependencies=[Depends(require_dev)],
)
async def list_tenants(
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> list[TenantSummary]:
    def _query() -> list[TenantSummary]:
        return [_build_summary(conn, t) for t in list_tenants_db(conn)]

    return await asyncio.to_thread(_query)


@router.get(
    "/{tenant_id}",
    response_model=TenantDetail,
    summary="Get tenant detail",
    description="Per-tenant detail. Tenant-scoped keys can only read their own row.",
)
async def get_tenant_detail(
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> TenantDetail:
    def _query() -> TenantDetail:
        tenant = get_tenant_db(conn, tenant_id)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"tenant '{tenant_id}' not registered",
            )
        summary = _build_summary(conn, tenant)
        return TenantDetail(**summary.model_dump())

    return await asyncio.to_thread(_query)


@router.get(
    "/{tenant_id}/api-keys",
    response_model=list[ApiKeySummary],
    summary="List API keys for a tenant",
    description=(
        "Returns label and creation timestamp for each minted key. The hash and "
        "plaintext are never exposed; the only place plaintext is visible is the "
        "POST response at creation time."
    ),
)
async def list_api_keys(
    tenant_id: str = Depends(require_tenant_access),
    settings: Settings = Depends(get_settings),
) -> list[ApiKeySummary]:
    def _read() -> list[ApiKeySummary]:
        tenants = _load_tenants_file(settings.tenants_file)
        match = next((t for t in tenants if t.tenant_id == tenant_id), None)
        if match is None:
            return []
        return [ApiKeySummary(label=k.label, created_at=k.created_at) for k in match.api_keys]

    return await asyncio.to_thread(_read)


@router.post(
    "/{tenant_id}/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mint a new API key for a tenant",
    description=(
        "Generates a 32-byte url-safe secret, persists only its SHA-256 hash, and "
        "returns the plaintext exactly once. Save the response."
    ),
)
async def create_api_key(
    body: ApiKeyCreateRequest,
    tenant_id: str = Depends(require_tenant_access),
    settings: Settings = Depends(get_settings),
) -> ApiKeyCreateResponse:
    def _mint() -> ApiKeyCreateResponse:
        tenants = _load_tenants_file(settings.tenants_file)
        match = next((t for t in tenants if t.tenant_id == tenant_id), None)
        if match is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"tenant '{tenant_id}' not in tenants.json",
            )
        if any(k.label == body.label for k in match.api_keys):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"label '{body.label}' is already in use",
            )
        plaintext = secrets.token_urlsafe(32)
        digest = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
        now = datetime.now(UTC)
        new_key = TenantApiKey(key_hash=digest, label=body.label, created_at=now)
        updated = TenantConfig.model_validate(
            {**match.model_dump(mode="json"), "api_keys": [*match.api_keys, new_key]}
        )
        survivors = [t if t.tenant_id != tenant_id else updated for t in tenants]
        _save_tenants_file(settings.tenants_file, survivors)
        return ApiKeyCreateResponse(key=plaintext, key_label=body.label, created_at=now)

    return await asyncio.to_thread(_mint)


@router.delete(
    "/{tenant_id}/api-keys/{key_label}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key by label",
    description=(
        "Removes the hash row from tenants.json. Existing in-flight requests using "
        "the key will fail on the next call."
    ),
)
async def delete_api_key(
    key_label: str,
    tenant_id: str = Depends(require_tenant_access),
    settings: Settings = Depends(get_settings),
) -> None:
    def _delete() -> None:
        tenants = _load_tenants_file(settings.tenants_file)
        match = next((t for t in tenants if t.tenant_id == tenant_id), None)
        if match is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"tenant '{tenant_id}' not in tenants.json",
            )
        survivors_keys = [k for k in match.api_keys if k.label != key_label]
        if len(survivors_keys) == len(match.api_keys):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"no API key labelled '{key_label}' for tenant '{tenant_id}'",
            )
        updated = TenantConfig.model_validate(
            {**match.model_dump(mode="json"), "api_keys": survivors_keys}
        )
        survivors = [t if t.tenant_id != tenant_id else updated for t in tenants]
        _save_tenants_file(settings.tenants_file, survivors)

    await asyncio.to_thread(_delete)
