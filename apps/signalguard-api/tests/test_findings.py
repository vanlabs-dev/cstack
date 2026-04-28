"""Tests for the tenant + findings endpoints.

Tests use the bundled tenant-b CA fixture, run the audit pipeline directly
against the tmp_path DB to populate the findings table, then exercise the
HTTP surface.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from cstack_audit_core import write_findings
from cstack_audit_coverage import compute_coverage, findings_from_coverage
from cstack_audit_exclusions import analyse_exclusions
from cstack_audit_rules import load_context_from_db, run_all_rules
from cstack_fixtures import load_fixture
from cstack_storage import connection_scope, run_migrations
from httpx import AsyncClient
from signalguard_api.config import Settings

from .conftest import DEV_KEY, TENANT_A, TENANT_B


def _populate_audit(settings: Settings) -> int:
    """Run the audit pipeline in-process so the API has rows to read."""
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        load_fixture("tenant-b", conn)
        ctx = load_context_from_db(conn, TENANT_B, as_of=datetime.now(UTC))
        coverage_findings = findings_from_coverage(
            compute_coverage(
                ctx.tenant_id,
                ctx.policies,
                ctx.users,
                ctx.groups,
                ctx.roles,
                ctx.role_assignments,
                as_of=ctx.as_of,
            ),
            ctx.tenant_id,
        )
        rule_findings = run_all_rules(ctx)
        exclusion_findings = analyse_exclusions(ctx)
        write_findings(conn, coverage_findings)
        write_findings(conn, rule_findings)
        write_findings(conn, exclusion_findings)
        row = conn.execute(
            "SELECT COUNT(*) FROM findings WHERE tenant_id = ?", [TENANT_B]
        ).fetchone()
        return int(row[0]) if row else 0


@pytest.fixture
def populated(settings: Settings) -> dict[str, Any]:
    total = _populate_audit(settings)
    return {"total": total}


@pytest.mark.asyncio
async def test_list_tenants_dev_only(client: AsyncClient) -> None:
    no_auth = await client.get("/tenants")
    assert no_auth.status_code == 401

    dev = await client.get("/tenants", headers={"X-API-Key": DEV_KEY})
    assert dev.status_code == 200
    payload = dev.json()
    assert isinstance(payload, list)
    ids = {t["tenant_id"] for t in payload}
    assert TENANT_A in ids
    assert TENANT_B in ids


@pytest.mark.asyncio
async def test_get_tenant_detail_404_for_unknown(client: AsyncClient) -> None:
    response = await client.get(
        f"/tenants/{'00000000-0000-0000-0000-deaddeadbeef'}",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_tenant_detail_returns_summary(client: AsyncClient) -> None:
    response = await client.get(f"/tenants/{TENANT_B}", headers={"X-API-Key": DEV_KEY})
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == TENANT_B
    assert body["display_name"] == "tenant-b"
    assert body["is_fixture"] is True


@pytest.mark.asyncio
async def test_findings_list_returns_results(
    client: AsyncClient, populated: dict[str, int]
) -> None:
    response = await client.get(f"/tenants/{TENANT_B}/findings", headers={"X-API-Key": DEV_KEY})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == populated["total"]
    assert body["total"] > 0
    assert body["limit"] == 100
    assert body["offset"] == 0
    assert len(body["items"]) == min(populated["total"], 100)


@pytest.mark.asyncio
async def test_findings_list_filter_severity(
    client: AsyncClient, populated: dict[str, int]
) -> None:
    response = await client.get(
        f"/tenants/{TENANT_B}/findings?min_severity=HIGH",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 200
    body = response.json()
    for item in body["items"]:
        assert item["severity"] in {"HIGH", "CRITICAL"}


@pytest.mark.asyncio
async def test_findings_pagination(client: AsyncClient, populated: dict[str, int]) -> None:
    if populated["total"] < 2:
        pytest.skip("not enough findings to paginate")
    page1 = await client.get(
        f"/tenants/{TENANT_B}/findings?limit=1&offset=0",
        headers={"X-API-Key": DEV_KEY},
    )
    page2 = await client.get(
        f"/tenants/{TENANT_B}/findings?limit=1&offset=1",
        headers={"X-API-Key": DEV_KEY},
    )
    assert page1.status_code == 200
    assert page2.status_code == 200
    assert page1.json()["items"][0]["id"] != page2.json()["items"][0]["id"]
    assert page1.json()["has_more"] is True
    last = await client.get(
        f"/tenants/{TENANT_B}/findings?limit=1&offset={populated['total'] - 1}",
        headers={"X-API-Key": DEV_KEY},
    )
    assert last.status_code == 200
    assert last.json()["has_more"] is False


@pytest.mark.asyncio
async def test_findings_summary_shape(client: AsyncClient, populated: dict[str, int]) -> None:
    response = await client.get(
        f"/tenants/{TENANT_B}/findings/summary", headers={"X-API-Key": DEV_KEY}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == populated["total"]
    assert sum(body["by_category"].values()) == populated["total"]
    assert sum(body["by_severity"].values()) == populated["total"]
    assert sum(body["by_rule_id"].values()) == populated["total"]


@pytest.mark.asyncio
async def test_finding_404_for_unknown_id(client: AsyncClient, populated: dict[str, int]) -> None:
    response = await client.get(
        f"/tenants/{TENANT_B}/findings/does-not-exist",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_findings_unknown_tenant_returns_empty_for_dev(
    client: AsyncClient,
) -> None:
    """A registered tenant with no findings yet returns an empty page, not 404.

    The findings endpoint does not validate the tenant exists; callers can
    use /tenants/{id} to confirm registration.
    """
    response = await client.get(f"/tenants/{TENANT_A}/findings", headers={"X-API-Key": DEV_KEY})
    assert response.status_code == 200
    assert response.json()["total"] == 0
