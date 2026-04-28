"""Tests for the anomaly, coverage, and signins read endpoints.

The anomaly tests insert hand-built scores plus signins directly through
the storage layer so they do not pay the cost of training a real model
per run. Coverage and signin-stats tests use the bundled fixture corpus
since those code paths are pure-DB reads.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from cstack_audit_core import AnomalyScore, ShapFeatureContribution, write_findings
from cstack_fixtures import load_fixture, load_signins
from cstack_ml_anomaly import findings_from_anomalies
from cstack_schemas import (
    DeviceDetail,
    GeoCoordinates,
    SignIn,
    SignInLocation,
    SignInStatus,
)
from cstack_storage import (
    connection_scope,
    register_tenant,
    run_migrations,
    upsert_signins,
    write_scores,
)
from httpx import AsyncClient

from signalguard_api.config import Settings

from .conftest import DEV_KEY, TENANT_A, TENANT_B


def _make_signin(signin_id: str, user_id: str, when: datetime, country: str = "US") -> SignIn:
    return SignIn(
        id=signin_id,
        created_date_time=when,
        user_id=user_id,
        user_principal_name=f"{user_id}@example.com",
        app_id="00000003-0000-0000-c000-000000000000",
        app_display_name="Office 365 Exchange Online",
        client_app_used="Browser",
        device_detail=DeviceDetail(
            device_id="dev-1",
            operating_system="Windows 11",
            browser="Edge",
            is_managed=True,
            is_compliant=True,
            trust_type="AzureAd",
        ),
        location=SignInLocation(
            country_or_region=country,
            city="Springfield",
            geo_coordinates=GeoCoordinates(latitude=39.78, longitude=-89.65),
        ),
        ip_address="203.0.113.10",
        status=SignInStatus(error_code=0),
        is_interactive=True,
    )


def _seed_anomaly_data(settings: Settings) -> dict[str, Any]:
    """Insert two signins, two scores (one anomalous), and a linked finding."""
    when = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    signins = [
        _make_signin("signin-normal", "u1", when),
        _make_signin("signin-anom", "u1", when + timedelta(minutes=30), country="RU"),
    ]
    scores = [
        AnomalyScore(
            tenant_id=TENANT_A,
            signin_id="signin-normal",
            user_id="u1",
            model_name="signalguard-anomaly-pooled-test",
            model_version="1",
            raw_score=-0.05,
            normalised_score=0.10,
            is_anomaly=False,
            shap_top_features=[],
            scored_at=when,
        ),
        AnomalyScore(
            tenant_id=TENANT_A,
            signin_id="signin-anom",
            user_id="u1",
            model_name="signalguard-anomaly-pooled-test",
            model_version="1",
            raw_score=-0.45,
            normalised_score=0.97,
            is_anomaly=True,
            shap_top_features=[
                ShapFeatureContribution(
                    feature_name="travel_speed_kmh",
                    feature_value=8000.0,
                    shap_value=-0.42,
                    direction="pushes_anomalous",
                ),
            ],
            scored_at=when + timedelta(minutes=31),
        ),
    ]
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        # tenant-a was registered by conftest.seeded_tenants; re-register no-op
        from cstack_schemas import TenantConfig

        register_tenant(
            conn,
            TenantConfig(
                tenant_id=TENANT_A,
                display_name="tenant-a",
                client_id="00000000-1111-2222-3333-aaaabbbbcccc",
                cert_thumbprint="A" * 40,
                cert_subject="CN=cstack-fixture-tenant-a",
                added_at=when,
                is_fixture=True,
            ),
        )
        upsert_signins(conn, TENANT_A, signins)
        write_scores(conn, scores)
        anom_findings = findings_from_anomalies(scores, TENANT_A, threshold=0.7)
        write_findings(conn, anom_findings)
    return {"anom_count": sum(1 for s in scores if s.is_anomaly)}


@pytest.fixture
def anomaly_seed(settings: Settings) -> dict[str, Any]:
    return _seed_anomaly_data(settings)


@pytest.mark.asyncio
async def test_list_scores_returns_paginated(
    client: AsyncClient, anomaly_seed: dict[str, int]
) -> None:
    response = await client.get(
        f"/tenants/{TENANT_A}/anomaly-scores", headers={"X-API-Key": DEV_KEY}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["items"][0]["normalised_score"] >= body["items"][1]["normalised_score"]


@pytest.mark.asyncio
async def test_list_scores_filter_anomaly_true(
    client: AsyncClient, anomaly_seed: dict[str, int]
) -> None:
    response = await client.get(
        f"/tenants/{TENANT_A}/anomaly-scores?is_anomaly=true",
        headers={"X-API-Key": DEV_KEY},
    )
    body = response.json()
    assert body["total"] == anomaly_seed["anom_count"]
    assert all(s["is_anomaly"] for s in body["items"])


@pytest.mark.asyncio
async def test_anomaly_feed_returns_top_n(
    client: AsyncClient, anomaly_seed: dict[str, int]
) -> None:
    response = await client.get(
        f"/tenants/{TENANT_A}/anomaly-scores/feed?n=5&min_score=0.7",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 200
    feed = response.json()
    assert len(feed) == 1
    assert feed[0]["signin_id"] == "signin-anom"


@pytest.mark.asyncio
async def test_anomaly_detail_bundle(
    client: AsyncClient, anomaly_seed: dict[str, int]
) -> None:
    response = await client.get(
        f"/tenants/{TENANT_A}/anomaly-scores/signin-anom",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["score"]["signin_id"] == "signin-anom"
    assert body["signin"]["id"] == "signin-anom"
    assert body["finding"] is not None
    assert body["finding"]["category"] == "anomaly"


@pytest.mark.asyncio
async def test_anomaly_detail_404(client: AsyncClient, anomaly_seed: dict[str, int]) -> None:
    response = await client.get(
        f"/tenants/{TENANT_A}/anomaly-scores/does-not-exist",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_coverage_matrix_for_fixture(client: AsyncClient, settings: Settings) -> None:
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        load_fixture("tenant-b", conn)
    response = await client.get(
        f"/tenants/{TENANT_B}/coverage-matrix", headers={"X-API-Key": DEV_KEY}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == TENANT_B
    assert isinstance(body["cells"], list)
    # 5 user segments x 5 app segments = 25 cells.
    assert len(body["cells"]) == 25


@pytest.mark.asyncio
async def test_signins_stats_baseline(client: AsyncClient, settings: Settings) -> None:
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        load_fixture("tenant-a", conn)
        load_signins("tenant-a", "baseline", conn)
    response = await client.get(
        f"/tenants/{TENANT_A}/signins/stats", headers={"X-API-Key": DEV_KEY}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    assert body["distinct_users"] > 0
    assert body["earliest_at"] is not None
    assert body["latest_at"] is not None


@pytest.mark.asyncio
async def test_signins_stats_empty(client: AsyncClient) -> None:
    response = await client.get(
        f"/tenants/{TENANT_B}/signins/stats", headers={"X-API-Key": DEV_KEY}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["distinct_users"] == 0


@pytest.mark.asyncio
async def test_user_signins_history(client: AsyncClient, settings: Settings) -> None:
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        load_fixture("tenant-a", conn)
        load_signins("tenant-a", "baseline", conn)
        sample = conn.execute(
            "SELECT user_id FROM signins WHERE tenant_id = ? LIMIT 1",
            [TENANT_A],
        ).fetchone()
    assert sample is not None
    user_id = sample[0]
    response = await client.get(
        f"/tenants/{TENANT_A}/users/{user_id}/signins?limit=5",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert all(item["userId"] == user_id for item in body["items"])
