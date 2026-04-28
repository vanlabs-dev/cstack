"""Tests for the API key mint/list/revoke endpoints."""

from __future__ import annotations

import hashlib
import json

import pytest
from httpx import AsyncClient

from .conftest import DEV_KEY, TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_list_api_keys_returns_seeded_label(client: AsyncClient) -> None:
    response = await client.get(
        f"/tenants/{TENANT_A}/api-keys", headers={"X-API-Key": DEV_KEY}
    )
    assert response.status_code == 200
    body = response.json()
    assert any(k["label"] == "ci" for k in body)
    for entry in body:
        assert "key" not in entry
        assert "key_hash" not in entry


@pytest.mark.asyncio
async def test_create_api_key_returns_plaintext_once(
    client: AsyncClient, settings, seeded_tenants
) -> None:
    _ = seeded_tenants
    response = await client.post(
        f"/tenants/{TENANT_A}/api-keys",
        headers={"X-API-Key": DEV_KEY},
        json={"label": "dashboard"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["key_label"] == "dashboard"
    plaintext = body["key"]
    assert plaintext, "plaintext key must be returned at create time"
    digest = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    persisted = json.loads(settings.tenants_file.read_text(encoding="utf-8"))
    assert plaintext not in json.dumps(persisted), "plaintext must not be persisted"
    keys = [k for t in persisted for k in t.get("api_keys", [])]
    assert any(k["key_hash"] == digest and k["label"] == "dashboard" for k in keys)


@pytest.mark.asyncio
async def test_create_api_key_rejects_duplicate_label(client: AsyncClient) -> None:
    response = await client.post(
        f"/tenants/{TENANT_A}/api-keys",
        headers={"X-API-Key": DEV_KEY},
        json={"label": "ci"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_api_key_404_unknown_tenant(client: AsyncClient) -> None:
    response = await client.post(
        f"/tenants/{'00000000-0000-0000-0000-deaddeadbeef'}/api-keys",
        headers={"X-API-Key": DEV_KEY},
        json={"label": "x"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_api_key_removes_hash(
    client: AsyncClient, settings, seeded_tenants
) -> None:
    _ = seeded_tenants
    response = await client.delete(
        f"/tenants/{TENANT_A}/api-keys/ci",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 204

    persisted = json.loads(settings.tenants_file.read_text(encoding="utf-8"))
    target = next(t for t in persisted if t["tenant_id"] == TENANT_A)
    assert all(k["label"] != "ci" for k in target.get("api_keys", []))


@pytest.mark.asyncio
async def test_delete_api_key_404_unknown_label(client: AsyncClient) -> None:
    response = await client.delete(
        f"/tenants/{TENANT_A}/api-keys/does-not-exist",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tenant_key_can_only_manage_own_keys(client: AsyncClient) -> None:
    response = await client.post(
        f"/tenants/{TENANT_B}/api-keys",
        headers={"X-API-Key": "tenant-a-plain-key-abc"},
        json={"label": "should-fail"},
    )
    assert response.status_code == 403
