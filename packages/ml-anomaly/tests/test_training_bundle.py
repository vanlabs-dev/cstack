"""Training tests for the per-user bundle path.

These exercise the per-user vs cold-start split, training-time
determinism, and the ``--skip-if-registered`` fast path.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pytest
from cstack_ml_anomaly import (
    tenant_model_name,
    train_per_user_topology,
    train_tenant,
)
from cstack_ml_mlops import configure_tracking, set_alias
from cstack_schemas import SignIn


def _signin(
    tenant_id: str, signin_id: str, user_id: str, when: datetime, country: str = "NZ"
) -> SignIn:
    location = {
        "countryOrRegion": country,
        "city": "Auckland",
        "geoCoordinates": {"latitude": -36.85, "longitude": 174.76},
    }
    device = {
        "deviceId": f"device-{user_id}",
        "operatingSystem": "Windows",
        "browser": "Chrome",
        "isManaged": True,
        "isCompliant": True,
        "trustType": "AzureAD",
    }
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
            "location": location,
            "deviceDetail": device,
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


def _signins_for(tenant_id: str, user_id: str, count: int, base: datetime) -> list[SignIn]:
    return [
        _signin(tenant_id, f"{user_id}-{i}", user_id, base + timedelta(hours=i * 3))
        for i in range(count)
    ]


def test_per_user_split_routes_high_volume_users_to_dedicated_models() -> None:
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    signins: list[SignIn] = []
    # alice: 50 sign-ins (above threshold 30) -> dedicated model.
    signins += _signins_for("t", "alice", 50, base)
    # bob: 25 sign-ins (below threshold) -> cold-start pool.
    signins += _signins_for("t", "bob", 25, base)
    # carol: 35 sign-ins (above) -> dedicated model.
    signins += _signins_for("t", "carol", 35, base)

    bundle = train_per_user_topology(
        "t", signins, contamination=0.05, random_state=42, min_samples=30
    )
    assert set(bundle.per_user_models.keys()) == {"alice", "carol"}
    assert bundle.n_users_per_user == 2
    assert bundle.n_users_cold_start == 1
    assert bundle.cold_start_pooled is not None


def test_per_user_with_no_cold_start_users_skips_pooled() -> None:
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    signins = _signins_for("t", "alice", 50, base) + _signins_for("t", "bob", 50, base)
    bundle = train_per_user_topology(
        "t", signins, contamination=0.05, random_state=42, min_samples=30
    )
    assert bundle.cold_start_pooled is None
    assert bundle.n_users_cold_start == 0


def test_per_user_with_only_cold_start_users_returns_pooled_only() -> None:
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    signins: list[SignIn] = []
    for uid in ("a", "b", "c", "d"):
        signins += _signins_for("t", uid, 25, base)
    bundle = train_per_user_topology(
        "t", signins, contamination=0.05, random_state=42, min_samples=30
    )
    assert bundle.per_user_models == {}
    assert bundle.cold_start_pooled is not None


def test_per_user_training_is_deterministic() -> None:
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    signins = _signins_for("t", "alice", 60, base) + _signins_for("t", "bob", 60, base)
    b1 = train_per_user_topology("t", signins, contamination=0.05, random_state=42, min_samples=30)
    b2 = train_per_user_topology("t", signins, contamination=0.05, random_state=42, min_samples=30)
    assert np.allclose(
        b1.per_user_models["alice"].named_steps["scaler"].mean_,
        b2.per_user_models["alice"].named_steps["scaler"].mean_,
    )
    # Time-only model has its own scaler with different mean shape; same
    # expectation about reproducibility.
    assert np.allclose(
        b1.time_pipelines["alice"].named_steps["scaler"].mean_,
        b2.time_pipelines["alice"].named_steps["scaler"].mean_,
    )
    assert b1.time_score_p90["alice"] == b2.time_score_p90["alice"]


def test_train_per_user_topology_raises_under_minimum_signins() -> None:
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    signins = _signins_for("t", "alice", 50, base)
    with pytest.raises(ValueError, match="at least"):
        train_per_user_topology("t", signins, contamination=0.05, random_state=42)


def test_skip_if_registered_short_circuits(tmp_path: Path) -> None:
    """When a champion already exists, ``--skip-if-registered`` returns the
    existing version without retraining."""
    tracking_uri = (tmp_path / "mlruns").resolve().as_uri()
    configure_tracking(uri=tracking_uri)
    name = tenant_model_name("t-skip")

    # Seed a registered model with a champion alias by hand. We don't need
    # an actual model artefact to exercise the skip path; the alias is
    # enough.
    import mlflow
    from mlflow.tracking import MlflowClient

    client = MlflowClient()
    client.create_registered_model(name)
    with mlflow.start_run() as run:
        mv = client.create_model_version(
            name=name, source=run.info.artifact_uri, run_id=run.info.run_id
        )
    set_alias(name, mv.version, "champion")

    # Open a duckdb in tmp_path so train_tenant can pull (zero) sign-ins.
    db_path = tmp_path / "cstack.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        from cstack_storage import run_migrations

        run_migrations(conn)
        result = train_tenant(
            "t-skip",
            conn,
            contamination=0.05,
            skip_if_registered=True,
            tracking_uri=tracking_uri,
        )
    finally:
        conn.close()
    assert result.skipped_existing is True
    assert result.model_version == str(mv.version)
