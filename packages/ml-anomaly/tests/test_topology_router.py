"""Topology router tests (Sprint 3.5b).

Verifies ``train_tenant`` honours ``CSTACK_ML_TRAINING_TOPOLOGY`` and
the ``--topology`` argument, that pooled topology produces an empty
per_user_models dict with the single fit assigned to cold_start_pooled,
and that scoring against either bundle shape routes correctly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pytest
from cstack_ml_anomaly import (
    DEFAULT_TOPOLOGY,
    PerUserBundle,
    promote_challenger_to_champion,
    resolve_topology,
    score_batch,
    train_pooled_topology,
    train_tenant,
)
from cstack_schemas import SignIn
from cstack_storage import run_migrations, upsert_signins


def _signin(signin_id: str, user_id: str, when: datetime) -> SignIn:
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
                "countryOrRegion": "NZ",
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


def _two_user_signins(base: datetime) -> list[SignIn]:
    return _signins_for("alice", 60, base) + _signins_for("bob", 60, base)


def test_default_topology_is_pooled() -> None:
    assert DEFAULT_TOPOLOGY == "pooled"


def test_resolve_topology_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CSTACK_ML_TRAINING_TOPOLOGY", raising=False)
    assert resolve_topology() == "pooled"


def test_resolve_topology_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CSTACK_ML_TRAINING_TOPOLOGY", "per_user")
    assert resolve_topology() == "per_user"


def test_resolve_topology_argument_overrides_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CSTACK_ML_TRAINING_TOPOLOGY", "per_user")
    assert resolve_topology("pooled") == "pooled"


def test_resolve_topology_empty_env_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CSTACK_ML_TRAINING_TOPOLOGY", "")
    assert resolve_topology() == "pooled"


def test_resolve_topology_invalid_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CSTACK_ML_TRAINING_TOPOLOGY", "lstm-autoencoder")
    with pytest.raises(ValueError, match="Invalid CSTACK_ML_TRAINING_TOPOLOGY"):
        resolve_topology()


def test_pooled_topology_returns_empty_per_user_dict() -> None:
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    bundle = train_pooled_topology(
        "t-pooled-shape",
        _two_user_signins(base),
        contamination=0.05,
        random_state=42,
        min_samples=30,
    )
    assert bundle.per_user_models == {}
    assert bundle.cold_start_pooled is not None
    assert bundle.n_users_per_user == 0
    assert bundle.n_users_cold_start == 2  # alice + bob both routed to cold-start
    assert bundle.time_pipelines == {}
    assert bundle.time_score_p90 == {}


def test_pooled_topology_serialise_roundtrip(tmp_path: Path) -> None:
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    bundle = train_pooled_topology(
        "t-roundtrip",
        _two_user_signins(base),
        contamination=0.05,
        random_state=42,
    )
    out = tmp_path / "bundle.joblib"
    bundle.serialise(out)
    restored = PerUserBundle.deserialise(out)
    assert restored.per_user_models == {}
    assert bundle.cold_start_pooled is not None
    assert restored.cold_start_pooled is not None
    # Same input must produce the same scalar across the roundtrip.
    import pandas as pd

    row = pd.DataFrame(
        [{col: 0.0 for col in bundle.feature_columns}],
        columns=list(bundle.feature_columns),
    )
    original_score = float(bundle.cold_start_pooled.decision_function(row)[0])
    restored_score = float(restored.cold_start_pooled.decision_function(row)[0])
    assert original_score == restored_score


def test_train_tenant_invalid_topology_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CSTACK_ML_TRAINING_TOPOLOGY", "definitely-not-valid")
    db_path = tmp_path / "cstack.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        run_migrations(conn)
        with pytest.raises(ValueError, match="Invalid CSTACK_ML_TRAINING_TOPOLOGY"):
            train_tenant("t-invalid", conn)
    finally:
        conn.close()


def test_train_tenant_argument_overrides_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even with CSTACK_ML_TRAINING_TOPOLOGY=per_user, an explicit
    topology='pooled' argument selects pooled training."""
    monkeypatch.setenv("CSTACK_ML_TRAINING_TOPOLOGY", "per_user")
    tracking_uri = (tmp_path / "mlruns").resolve().as_uri()
    db_path = tmp_path / "cstack.duckdb"
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    tenant_id = "t-arg-override"

    conn = duckdb.connect(str(db_path))
    try:
        run_migrations(conn)
        upsert_signins(conn, tenant_id, _two_user_signins(base))
        result = train_tenant(
            tenant_id,
            conn,
            contamination=0.05,
            min_samples=30,
            tracking_uri=tracking_uri,
            topology="pooled",
        )
    finally:
        conn.close()
    assert result.topology == "pooled"
    assert result.n_users_per_user == 0
    assert result.n_users_cold_start == 2


def test_pooled_topology_score_routes_every_user_to_cold_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pooled-topology bundle: every score_batch row reports
    model_tier='cold_start_pooled'."""
    monkeypatch.delenv("CSTACK_ML_TRAINING_TOPOLOGY", raising=False)
    monkeypatch.delenv("CSTACK_ML_OFF_HOURS_ADMIN_ENABLED", raising=False)
    tracking_uri = (tmp_path / "mlruns").resolve().as_uri()
    db_path = tmp_path / "cstack.duckdb"
    base = datetime(2026, 4, 1, 9, tzinfo=UTC)
    tenant_id = "t-pooled-score"
    signins = _two_user_signins(base)

    conn = duckdb.connect(str(db_path))
    try:
        run_migrations(conn)
        upsert_signins(conn, tenant_id, signins)
        train_tenant(
            tenant_id,
            conn,
            contamination=0.05,
            tracking_uri=tracking_uri,
            topology="pooled",
        )
        promote_challenger_to_champion(tenant_id, force=True, tracking_uri=tracking_uri)
        scores = score_batch(signins, tenant_id, conn, tracking_uri=tracking_uri)
    finally:
        conn.close()
    assert scores
    assert all(s.model_tier == "cold_start_pooled" for s in scores)
