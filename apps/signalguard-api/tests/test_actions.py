"""Tests for the audit and anomaly action endpoints."""

from __future__ import annotations

import pytest
from cstack_fixtures import load_fixture
from cstack_storage import connection_scope, run_migrations
from httpx import AsyncClient

from signalguard_api.config import Settings

from .conftest import DEV_KEY, TENANT_A, TENANT_B


@pytest.fixture
def loaded_tenant_b(settings: Settings) -> int:
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        load_fixture("tenant-b", conn)
        row = conn.execute(
            "SELECT COUNT(*) FROM ca_policies WHERE tenant_id = ?", [TENANT_B]
        ).fetchone()
    assert row is not None
    return int(row[0])


@pytest.mark.asyncio
async def test_audit_dry_run_writes_zero_rows(
    client: AsyncClient, loaded_tenant_b: int, settings: Settings
) -> None:
    with connection_scope(settings.db_path) as conn:
        before_row = conn.execute(
            "SELECT COUNT(*) FROM findings WHERE tenant_id = ?", [TENANT_B]
        ).fetchone()
    assert before_row is not None
    before = int(before_row[0])

    response = await client.post(
        f"/tenants/{TENANT_B}/audit/dry-run",
        headers={"X-API-Key": DEV_KEY},
        json={"categories": ["coverage", "rules", "exclusions"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["findings"], list)
    assert "by_category" in body
    assert body["run_id"]

    with connection_scope(settings.db_path) as conn:
        after_row = conn.execute(
            "SELECT COUNT(*) FROM findings WHERE tenant_id = ?", [TENANT_B]
        ).fetchone()
    assert after_row is not None
    after = int(after_row[0])
    assert after == before, "dry-run must not persist findings"


@pytest.mark.asyncio
async def test_audit_run_writes_findings(
    client: AsyncClient, loaded_tenant_b: int, settings: Settings
) -> None:
    response = await client.post(
        f"/tenants/{TENANT_B}/audit/run",
        headers={"X-API-Key": DEV_KEY},
        json={"categories": ["coverage", "rules", "exclusions"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["findings_written"] > 0
    assert body["duration_seconds"] >= 0
    assert body["run_id"]

    with connection_scope(settings.db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM findings WHERE tenant_id = ?", [TENANT_B]
        ).fetchone()
    assert row is not None
    assert int(row[0]) > 0


@pytest.mark.asyncio
async def test_audit_run_rejects_empty_categories(
    client: AsyncClient, loaded_tenant_b: int
) -> None:
    response = await client.post(
        f"/tenants/{TENANT_B}/audit/run",
        headers={"X-API-Key": DEV_KEY},
        json={"categories": []},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_audit_run_subset_runs_only_requested_category(
    client: AsyncClient, loaded_tenant_b: int
) -> None:
    response = await client.post(
        f"/tenants/{TENANT_B}/audit/dry-run",
        headers={"X-API-Key": DEV_KEY},
        json={"categories": ["rules"]},
    )
    body = response.json()
    assert set(body["by_category"].keys()) == {"rules"}


@pytest.mark.asyncio
async def test_anomaly_score_returns_503_without_model(client: AsyncClient) -> None:
    response = await client.post(
        f"/tenants/{TENANT_A}/anomaly/score",
        headers={"X-API-Key": DEV_KEY},
        json={"generate_findings": True},
    )
    assert response.status_code == 503
    assert "champion" in response.json()["detail"].lower()
