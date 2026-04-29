"""Per-user bundle tests: routing, serialisation, threshold semantics."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from cstack_ml_anomaly.per_user import (
    DEFAULT_MIN_SAMPLES_FOR_PER_USER_MODEL,
    PerUserBundle,
    min_samples_default,
)
from cstack_ml_features import FEATURE_COLUMNS
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def _toy_pipeline(seed: int = 42) -> Pipeline:
    """Fit a tiny Pipeline on random data so we can route through it in tests."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.normal(size=(50, len(FEATURE_COLUMNS))), columns=list(FEATURE_COLUMNS))
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("iforest", IsolationForest(n_estimators=20, random_state=seed, contamination=0.1)),
        ]
    )
    pipe.fit(df)
    return pipe


def _toy_row() -> pd.DataFrame:
    """One-row DataFrame with the canonical column layout."""
    return pd.DataFrame(
        {col: [0.0] for col in FEATURE_COLUMNS},
        columns=list(FEATURE_COLUMNS),
    )


def _bundle_with(per_user: dict[str, Pipeline], cold: Pipeline | None) -> PerUserBundle:
    return PerUserBundle(
        tenant_id="t",
        per_user_models=per_user,
        cold_start_pooled=cold,
        feature_columns=tuple(FEATURE_COLUMNS),
        trained_at=datetime.now(UTC),
        n_users_per_user=len(per_user),
        n_users_cold_start=1 if cold is not None else 0,
        total_signins_used=0,
        min_samples_threshold=30,
    )


def test_predict_user_routes_to_per_user_when_known() -> None:
    pipe = _toy_pipeline(1)
    bundle = _bundle_with({"alice": pipe}, _toy_pipeline(2))
    _score, tier = bundle.predict_user("alice", _toy_row())
    assert tier == "per_user"


def test_predict_user_falls_back_to_cold_start_when_unknown() -> None:
    bundle = _bundle_with({"alice": _toy_pipeline(1)}, _toy_pipeline(2))
    _score, tier = bundle.predict_user("eve", _toy_row())
    assert tier == "cold_start_pooled"


def test_predict_user_returns_rule_only_when_no_pooled_and_unknown_user() -> None:
    bundle = _bundle_with({"alice": _toy_pipeline(1)}, None)
    score, tier = bundle.predict_user("eve", _toy_row())
    assert tier == "rule_only"
    assert score == 0.0


def test_has_user_model_reflects_dict_membership() -> None:
    bundle = _bundle_with({"alice": _toy_pipeline(1)}, _toy_pipeline(2))
    assert bundle.has_user_model("alice") is True
    assert bundle.has_user_model("eve") is False


def test_serialise_and_deserialise_roundtrip(tmp_path: Path) -> None:
    pipe_a = _toy_pipeline(1)
    pipe_pool = _toy_pipeline(2)
    bundle = _bundle_with({"alice": pipe_a}, pipe_pool)
    bundle.time_score_p90["alice"] = 0.42
    out = tmp_path / "bundle.joblib"
    bundle.serialise(out)
    restored = PerUserBundle.deserialise(out)
    assert restored.tenant_id == "t"
    assert "alice" in restored.per_user_models
    assert restored.cold_start_pooled is not None
    assert restored.feature_columns == tuple(FEATURE_COLUMNS)
    assert restored.time_score_p90["alice"] == 0.42


def test_min_samples_default_uses_constant_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CSTACK_ML_MIN_PER_USER_SAMPLES", raising=False)
    assert min_samples_default() == DEFAULT_MIN_SAMPLES_FOR_PER_USER_MODEL


def test_min_samples_default_respects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CSTACK_ML_MIN_PER_USER_SAMPLES", "75")
    assert min_samples_default() == 75


def test_min_samples_default_falls_back_on_invalid_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CSTACK_ML_MIN_PER_USER_SAMPLES", "not-a-number")
    assert min_samples_default() == DEFAULT_MIN_SAMPLES_FOR_PER_USER_MODEL
