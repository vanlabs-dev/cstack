"""Rule-booster tests, including the off-hours-admin per-user anchor."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from cstack_ml_anomaly.per_user import PerUserBundle
from cstack_ml_anomaly.rules import (
    NIGHT_HOURS_UTC,
    RULE_OFF_HOURS_ADMIN_FLOOR,
    TIME_FEATURE_COLUMNS,
    rule_score_boosts,
)
from cstack_ml_features import FEATURE_COLUMNS
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def _row(hour: int, **overrides: float) -> dict[str, float]:
    """One synthetic feature row at UTC ``hour`` plus optional overrides."""
    base: dict[str, float] = {col: 0.0 for col in FEATURE_COLUMNS}
    base["hour_of_day_sin"] = math.sin(2 * math.pi * hour / 24)
    base["hour_of_day_cos"] = math.cos(2 * math.pi * hour / 24)
    base["is_business_hours_local"] = 1.0 if 8 <= hour <= 18 else 0.0
    base["mfa_satisfied"] = 1.0
    base.update(overrides)
    return base


def _df(*rows: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=list(FEATURE_COLUMNS))


def _toy_time_pipeline(seed: int = 1) -> tuple[Pipeline, list[float]]:
    """Tiny time-only IF fit on daytime hours so a 3am row scores anomalous.

    Returns the pipeline and a list of training-set negated scores so the
    caller can compute a deterministic p90 to bake into the bundle.
    """
    daytime_rows = []
    for dow in range(5):  # Mon-Fri
        for hour in (9, 10, 11, 13, 14, 15, 16):
            for _ in range(4):
                r = {col: 0.0 for col in TIME_FEATURE_COLUMNS}
                r["hour_of_day_sin"] = math.sin(2 * math.pi * hour / 24)
                r["hour_of_day_cos"] = math.cos(2 * math.pi * hour / 24)
                r["is_business_hours_local"] = 1.0
                r["day_of_week"] = float(dow)
                daytime_rows.append(r)
    df = pd.DataFrame(daytime_rows, columns=list(TIME_FEATURE_COLUMNS))
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "iforest",
                IsolationForest(n_estimators=50, random_state=seed, contamination=0.05),
            ),
        ]
    )
    pipe.fit(df)
    train_scores = (-pipe.decision_function(df)).tolist()
    return pipe, train_scores


def _bundle_with_admin_time_model(user_id: str) -> PerUserBundle:
    """A bundle whose only per-user content is a time-only model for ``user_id``."""
    pipe, train_scores = _toy_time_pipeline()
    p90 = float(np.percentile(train_scores, 90))
    return PerUserBundle(
        tenant_id="t",
        per_user_models={},
        cold_start_pooled=None,
        feature_columns=tuple(FEATURE_COLUMNS),
        trained_at=datetime.now(UTC),
        n_users_per_user=1,
        n_users_cold_start=0,
        total_signins_used=0,
        min_samples_threshold=30,
        time_pipelines={user_id: pipe},
        time_score_p90={user_id: p90},
    )


def test_off_hours_admin_fires_for_privileged_user_outside_pattern() -> None:
    """Privileged user + 3am sign-in + per-user time model that rates the
    hour anomalous -> rule fires at the 0.85 floor."""
    bundle = _bundle_with_admin_time_model("admin-1")
    df = _df(_row(hour=3))
    boosts = rule_score_boosts(
        df,
        user_ids=["admin-1"],
        bundle=bundle,
        privileged_user_ids=frozenset({"admin-1"}),
    )
    assert boosts == [RULE_OFF_HOURS_ADMIN_FLOOR]


def test_off_hours_admin_does_not_fire_for_non_admin() -> None:
    """Non-admin user at 3am: no fire even if time pattern looks unusual."""
    bundle = _bundle_with_admin_time_model("admin-1")
    df = _df(_row(hour=3))
    boosts = rule_score_boosts(
        df,
        user_ids=["regular-user"],
        bundle=bundle,
        privileged_user_ids=frozenset({"admin-1"}),
    )
    assert boosts == [0.0]


def test_off_hours_admin_does_not_fire_within_user_pattern() -> None:
    """Admin user at 13:00 mid-week (well inside training pattern): no fire."""
    bundle = _bundle_with_admin_time_model("admin-1")
    row = _row(hour=13)
    row["day_of_week"] = 2.0
    df = _df(row)
    boosts = rule_score_boosts(
        df,
        user_ids=["admin-1"],
        bundle=bundle,
        privileged_user_ids=frozenset({"admin-1"}),
    )
    assert boosts == [0.0]


def test_off_hours_admin_cold_start_uses_night_band() -> None:
    """Admin user with no per-user model + 3am UTC -> rule fires via fallback."""
    bundle = PerUserBundle(
        tenant_id="t",
        per_user_models={},
        cold_start_pooled=None,
        feature_columns=tuple(FEATURE_COLUMNS),
        trained_at=datetime.now(UTC),
        n_users_per_user=0,
        n_users_cold_start=1,
        total_signins_used=0,
        min_samples_threshold=30,
    )
    df = _df(_row(hour=3))
    boosts = rule_score_boosts(
        df,
        user_ids=["admin-cold"],
        bundle=bundle,
        privileged_user_ids=frozenset({"admin-cold"}),
    )
    assert boosts == [RULE_OFF_HOURS_ADMIN_FLOOR]


def test_off_hours_admin_cold_start_does_not_fire_during_day() -> None:
    """Cold-start admin at 14:00 UTC: not in night band, no fire."""
    bundle = PerUserBundle(
        tenant_id="t",
        per_user_models={},
        cold_start_pooled=None,
        feature_columns=tuple(FEATURE_COLUMNS),
        trained_at=datetime.now(UTC),
        n_users_per_user=0,
        n_users_cold_start=1,
        total_signins_used=0,
        min_samples_threshold=30,
    )
    df = _df(_row(hour=14))
    boosts = rule_score_boosts(
        df,
        user_ids=["admin-cold"],
        bundle=bundle,
        privileged_user_ids=frozenset({"admin-cold"}),
    )
    assert boosts == [0.0]


def test_off_hours_admin_skipped_when_privileged_set_empty() -> None:
    """Layer-attribution mode: empty privileged set disables the rule."""
    bundle = _bundle_with_admin_time_model("admin-1")
    df = _df(_row(hour=3))
    boosts = rule_score_boosts(
        df,
        user_ids=["admin-1"],
        bundle=bundle,
        privileged_user_ids=frozenset(),
    )
    assert boosts == [0.0]


def test_hybrid_rule_impossible_travel_still_fires_alongside_admin() -> None:
    """When both impossible-travel and off-hours-admin would fire, the
    higher floor (0.95) wins over the admin floor (0.85)."""
    bundle = _bundle_with_admin_time_model("admin-1")
    df = _df(_row(hour=3, travel_speed_kmh=2000.0))
    boosts = rule_score_boosts(
        df,
        user_ids=["admin-1"],
        bundle=bundle,
        privileged_user_ids=frozenset({"admin-1"}),
    )
    assert boosts == [0.95]


def test_night_hours_band_covers_22_to_05_inclusive() -> None:
    """Sanity-check the night band documented on the rule."""
    assert frozenset({22, 23, 0, 1, 2, 3, 4, 5}) == NIGHT_HOURS_UTC


def test_user_ids_required_when_privileged_set_supplied() -> None:
    """A privileged set without user_ids cannot match anyone; we still
    expect zeros and no exception (defensive call from layer-attribution)."""
    bundle = _bundle_with_admin_time_model("admin-1")
    df = _df(_row(hour=3))
    boosts = rule_score_boosts(
        df,
        user_ids=None,
        bundle=bundle,
        privileged_user_ids=frozenset({"admin-1"}),
    )
    assert boosts == [0.0]
