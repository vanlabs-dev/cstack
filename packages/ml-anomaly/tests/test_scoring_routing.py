"""End-to-end scoring routing test.

Exercises the per-user / cold-start tier split via the public
``score_batch`` surface against a tmp-path MLflow registry. Verifies the
``model_tier`` field on each ``AnomalyScore`` matches which pipeline
actually scored the row.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
from cstack_ml_anomaly import (
    promote_challenger_to_champion,
    score_batch,
    train_tenant,
)
from cstack_schemas import SignIn
from cstack_storage import run_migrations, upsert_signins


def _signin(signin_id: str, user_id: str, when: datetime, country: str = "NZ") -> SignIn:
    return SignIn.model_validate(
        {
            "id": signin_id,
            "userId": user_id,
            "userPrincipalName": f"{user_id}@example.com",
            "createdDateTime": when.isoformat(),
            "appId": "00000000-0000-0000-0000-000000000001",
            "appDisplayName": "App",
            "clientAppUsed": "Browser",
            "ipAddress": "203.0.113.10",
            "location": {
                "countryOrRegion": country,
                "city": "Auckland",
                "geoCoordinates": {"latitude": -36.85, "longitude": 174.76},
            },
            "deviceDetail": {
                "deviceId": f"device-{user_id}",
                "operatingSystem": "Windows",
                "browser": "Chrome",
                "isManaged": True,
                "isCompliant": True,
                "trustType": "AzureAD",
            },
            "status": {"errorCode": 0, "failureReason": ""},
            "conditionalAccessStatus": "success",
            "authenticationRequirement": "multiFactorAuthentication",
            "authenticationDetails": [],
            "riskLevelAggregated": "none",
            "riskLevelDuringSignIn": "none",
            "riskState": "none",
            "isInteractive": True,
        }
    )


def _signins_for(user_id: str, count: int, base: datetime) -> list[SignIn]:
    return [_signin(f"{user_id}-{i}", user_id, base + timedelta(hours=i * 3)) for i in range(count)]


def test_score_batch_emits_per_user_and_cold_start_tiers(tmp_path: Path) -> None:
    """Mix of high-volume + low-volume users routes to both tiers."""
    tracking_uri = (tmp_path / "mlruns").resolve().as_uri()
    db_path = tmp_path / "cstack.duckdb"
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    tenant_id = "t-routing"

    signins: list[SignIn] = []
    # alice + bob both have 50 sign-ins (above threshold).
    signins += _signins_for("alice", 50, base)
    signins += _signins_for("bob", 50, base)
    # charlie has 25 (below) -> cold-start.
    signins += _signins_for("charlie", 25, base)

    conn = duckdb.connect(str(db_path))
    try:
        run_migrations(conn)
        upsert_signins(conn, tenant_id, signins)
        train_tenant(
            tenant_id,
            conn,
            contamination=0.05,
            min_samples=30,
            tracking_uri=tracking_uri,
        )
        promote_challenger_to_champion(tenant_id, force=True, tracking_uri=tracking_uri)
        scores = score_batch(signins, tenant_id, conn, tracking_uri=tracking_uri)
    finally:
        conn.close()

    by_user_tier = {(s.user_id, s.model_tier) for s in scores}
    assert ("alice", "per_user") in by_user_tier
    assert ("bob", "per_user") in by_user_tier
    assert ("charlie", "cold_start_pooled") in by_user_tier
    # No row should fall to rule_only here: cold-start pool exists.
    assert all(s.model_tier in {"per_user", "cold_start_pooled"} for s in scores)


def test_score_batch_falls_to_rule_only_when_no_pooled_for_unknown_user(
    tmp_path: Path,
) -> None:
    """When all training users had per-user models and a never-seen user
    appears at score time, the row falls to the rule-only path."""
    tracking_uri = (tmp_path / "mlruns").resolve().as_uri()
    db_path = tmp_path / "cstack.duckdb"
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    tenant_id = "t-rule-only"

    signins: list[SignIn] = []
    signins += _signins_for("alice", 60, base)
    signins += _signins_for("bob", 60, base)

    conn = duckdb.connect(str(db_path))
    try:
        run_migrations(conn)
        upsert_signins(conn, tenant_id, signins)
        train_tenant(
            tenant_id,
            conn,
            contamination=0.05,
            min_samples=30,
            tracking_uri=tracking_uri,
        )
        promote_challenger_to_champion(tenant_id, force=True, tracking_uri=tracking_uri)
        unknown = _signins_for("eve", 5, base + timedelta(days=1))
        upsert_signins(conn, tenant_id, unknown)
        scores = score_batch(unknown, tenant_id, conn, tracking_uri=tracking_uri)
    finally:
        conn.close()

    assert all(s.model_tier == "rule_only" for s in scores)
