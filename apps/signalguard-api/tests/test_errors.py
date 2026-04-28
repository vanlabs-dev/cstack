"""Verify RFC 7807-style error responses."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from .conftest import DEV_KEY, TENANT_A


@pytest.mark.asyncio
async def test_404_returns_problem_detail(client: AsyncClient) -> None:
    response = await client.get(
        f"/tenants/{TENANT_A}/findings/does-not-exist",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 404
    assert body["title"] == "Not Found"
    assert body["type"].startswith("https://signalguard.dev/errors/")
    assert "correlation_id" in body
    assert body["instance"] == f"/tenants/{TENANT_A}/findings/does-not-exist"


@pytest.mark.asyncio
async def test_401_returns_problem_detail(client: AsyncClient) -> None:
    response = await client.get("/whoami")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 401
    assert body["title"] == "Unauthorized"


@pytest.mark.asyncio
async def test_correlation_id_round_trip(client: AsyncClient) -> None:
    custom = "test-correlation-id-12345"
    response = await client.get(
        "/whoami",
        headers={"X-API-Key": DEV_KEY, "X-Correlation-Id": custom},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-Id") == custom


@pytest.mark.asyncio
async def test_correlation_id_in_problem_body(client: AsyncClient) -> None:
    custom = "another-correlation-id-67890"
    response = await client.get("/whoami", headers={"X-Correlation-Id": custom})
    assert response.status_code == 401
    body = response.json()
    assert body["correlation_id"] == custom
