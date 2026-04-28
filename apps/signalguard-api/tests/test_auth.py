"""Auth tests against /whoami and a test-only tenant-scoped route."""

from __future__ import annotations

import logging

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from signalguard_api.auth import require_tenant_access

from .conftest import (
    DEV_KEY,
    TENANT_A,
    TENANT_A_KEY_PLAIN,
    TENANT_B,
    TENANT_B_KEY_PLAIN,
)


def _attach_tenant_route(app: FastAPI) -> None:
    """Add a tenant-scoped ping route used purely by tests."""

    async def _ping(tenant_id: str = Depends(require_tenant_access)) -> dict[str, str]:
        return {"tenant_id": tenant_id}

    app.add_api_route("/_test/tenant/{tenant_id}", _ping, methods=["GET"])


@pytest.mark.asyncio
async def test_whoami_requires_header(client: AsyncClient) -> None:
    response = await client.get("/whoami")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_whoami_rejects_unknown_key(client: AsyncClient) -> None:
    response = await client.get("/whoami", headers={"X-API-Key": "not-a-real-key"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_whoami_accepts_dev_key(client: AsyncClient) -> None:
    response = await client.get("/whoami", headers={"X-API-Key": DEV_KEY})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "dev"
    assert body["tenant_id"] is None


@pytest.mark.asyncio
async def test_whoami_accepts_tenant_key(client: AsyncClient) -> None:
    response = await client.get("/whoami", headers={"X-API-Key": TENANT_A_KEY_PLAIN})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "tenant"
    assert body["tenant_id"] == TENANT_A
    assert body["key_label"] == "ci"


@pytest.mark.asyncio
async def test_dev_key_can_reach_any_tenant(app: FastAPI) -> None:
    _attach_tenant_route(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/_test/tenant/{TENANT_A}", headers={"X-API-Key": DEV_KEY})
        assert response.status_code == 200
        response = await ac.get(f"/_test/tenant/{TENANT_B}", headers={"X-API-Key": DEV_KEY})
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_key_scoped_to_owning_tenant(app: FastAPI) -> None:
    _attach_tenant_route(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ok = await ac.get(f"/_test/tenant/{TENANT_A}", headers={"X-API-Key": TENANT_A_KEY_PLAIN})
        assert ok.status_code == 200
        denied = await ac.get(
            f"/_test/tenant/{TENANT_B}", headers={"X-API-Key": TENANT_A_KEY_PLAIN}
        )
        assert denied.status_code == 403


@pytest.mark.asyncio
async def test_tenant_b_key_only_reaches_tenant_b(app: FastAPI) -> None:
    _attach_tenant_route(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ok = await ac.get(f"/_test/tenant/{TENANT_B}", headers={"X-API-Key": TENANT_B_KEY_PLAIN})
        assert ok.status_code == 200
        denied = await ac.get(
            f"/_test/tenant/{TENANT_A}", headers={"X-API-Key": TENANT_B_KEY_PLAIN}
        )
        assert denied.status_code == 403


@pytest.mark.asyncio
async def test_logs_do_not_leak_api_key(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    sentinel = "should-never-appear-in-logs-XYZ"
    with caplog.at_level(logging.DEBUG):
        await client.get("/whoami", headers={"X-API-Key": sentinel})
    for record in caplog.records:
        assert sentinel not in record.getMessage()
        for value in record.__dict__.values():
            if isinstance(value, str):
                assert sentinel not in value
