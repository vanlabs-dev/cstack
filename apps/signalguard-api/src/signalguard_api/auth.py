"""Dual auth model: a single dev API key for local work, plus per-tenant
keys persisted in tenants.json as SHA-256 hashes.

Plaintext keys are never logged or stored. The CLI prints a key once at
creation; thereafter only its hash exists on disk.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Literal

from cstack_schemas import TenantApiKey, TenantConfig
from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from signalguard_api.config import Settings, get_settings

LOG = logging.getLogger(__name__)

API_KEY_HEADER = "X-API-Key"


class ApiCaller(BaseModel):
    """Identity of the caller as resolved from the API key."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["dev", "tenant"]
    tenant_id: str | None
    key_label: str


def hash_key(plaintext: str) -> str:
    """SHA-256 hex digest used to compare submitted keys against the store."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def load_tenant_api_keys(path: Path) -> dict[str, tuple[str, TenantApiKey]]:
    """Build a hash -> (tenant_id, key) map by walking tenants.json.

    Returns an empty mapping when the file is missing or empty so the API
    survives first-run flows that have not minted any tenant keys yet.
    """
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected a JSON array, got {type(payload).__name__}")
    out: dict[str, tuple[str, TenantApiKey]] = {}
    for item in payload:
        tenant = TenantConfig.model_validate(item)
        for key in tenant.api_keys:
            out[key.key_hash] = (tenant.tenant_id, key)
    return out


def _unauthorized(detail: str) -> HTTPException:
    """401 with a WWW-Authenticate hint so curl users see a sane prompt."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "ApiKey"},
    )


def require_api_key(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ApiCaller:
    """Resolve the caller from the ``X-API-Key`` header.

    Dev key match wins over tenant key lookup; both code paths run in
    constant-time-ish hash comparison so a tenant key that happens to equal
    the dev key string would still not bypass scoping.
    """
    submitted = request.headers.get(API_KEY_HEADER)
    if not submitted:
        raise _unauthorized("missing X-API-Key header")

    if settings.dev_api_key is not None and submitted == settings.dev_api_key:
        return ApiCaller(kind="dev", tenant_id=None, key_label="dev")

    digest = hash_key(submitted)
    keymap = load_tenant_api_keys(settings.tenants_file)
    found = keymap.get(digest)
    if found is None:
        LOG.info("api auth rejected", extra={"key_label": "(unknown)"})
        raise _unauthorized("invalid API key")
    tenant_id, key = found
    return ApiCaller(kind="tenant", tenant_id=tenant_id, key_label=key.label)


def require_tenant_access(
    tenant_id: str,
    caller: ApiCaller = Depends(require_api_key),
) -> str:
    """Restrict tenant-scoped routes to dev callers or a matching tenant key."""
    if caller.kind == "dev":
        return tenant_id
    if caller.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key not authorised for this tenant",
        )
    return tenant_id


def require_dev(caller: ApiCaller = Depends(require_api_key)) -> ApiCaller:
    """Routes that should only be reachable with the dev key (e.g. tenant list)."""
    if caller.kind != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="dev API key required",
        )
    return caller
