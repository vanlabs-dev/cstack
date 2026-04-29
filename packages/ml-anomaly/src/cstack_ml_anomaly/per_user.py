"""Per-user IsolationForest bundle with cold-start pooled fallback.

A tenant's anomaly model is now a single artefact ``PerUserBundle`` carrying
one fitted ``Pipeline`` per user with enough sign-ins to support a dedicated
fit, plus one shared cold-start pooled pipeline that handles users below
the threshold. Routing happens at score time via ``predict_user``.

The bundle is the unit of MLflow registration: one registered model per
tenant, one ``model.joblib`` artefact per registered version. Per-user
pipelines are *not* registered separately; that would multiply registry
entries by N users with no operational benefit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import joblib
from sklearn.pipeline import Pipeline

DEFAULT_MIN_SAMPLES_FOR_PER_USER_MODEL = 30


def min_samples_default() -> int:
    """Resolve the per-user sample threshold from env or the constant."""
    raw = os.environ.get("CSTACK_ML_MIN_PER_USER_SAMPLES")
    if raw is None or not raw.strip():
        return DEFAULT_MIN_SAMPLES_FOR_PER_USER_MODEL
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_MIN_SAMPLES_FOR_PER_USER_MODEL


@dataclass
class PerUserBundle:
    """Tenant-scoped artefact: per-user models + cold-start pooled fallback.

    Attributes:
        tenant_id: tenant the bundle was trained against.
        per_user_models: user_id -> fitted Pipeline. One entry per user that
            had at least ``min_samples_threshold`` sign-ins in the training
            window.
        cold_start_pooled: shared Pipeline fitted on users below the
            threshold; used when a user_id is not in ``per_user_models``.
            ``None`` only when there were zero cold-start users at training
            time, in which case unknown users get the rule-only path.
        feature_columns: canonical feature order at training time. Stored
            so scoring can detect drift in FEATURE_COLUMNS that would
            silently misalign the input matrix.
        time_score_p90: per-user 90th percentile of the user's negated
            time-only IF ``score_samples`` (higher = more anomalous). Used
            by the off-hours-admin rule to anchor "this user's late-night
            sign-ins are unusual for them specifically".
        time_pipelines: per-user time-only Pipeline. Smaller (4 features)
            so the rule can score the time component independently from
            the full 20-feature model.
    """

    tenant_id: str
    per_user_models: dict[str, Pipeline]
    cold_start_pooled: Pipeline | None
    feature_columns: tuple[str, ...]
    trained_at: datetime
    n_users_per_user: int
    n_users_cold_start: int
    total_signins_used: int
    min_samples_threshold: int
    time_pipelines: dict[str, Pipeline] = field(default_factory=dict)
    time_score_p90: dict[str, float] = field(default_factory=dict)

    def predict_user(self, user_id: str, features_row: object) -> tuple[float, str]:
        """Score one row for ``user_id``. Returns ``(raw_score, model_tier)``.

        ``raw_score`` is the model's ``decision_function`` output (higher
        means more normal, sklearn convention). Callers normalise.

        Tier is ``"per_user"`` when the user has a dedicated model,
        ``"cold_start_pooled"`` when they fall back to the shared pooled
        pipeline, and never ``"rule_only"`` (that's a scoring-time concept
        that comes from the rule booster, not the bundle).
        """
        model = self.per_user_models.get(user_id)
        if model is not None:
            score = float(model.decision_function(features_row)[0])
            return score, "per_user"
        if self.cold_start_pooled is not None:
            score = float(self.cold_start_pooled.decision_function(features_row)[0])
            return score, "cold_start_pooled"
        # No per-user, no pooled. Caller falls back to the rule booster only.
        return 0.0, "rule_only"

    def has_user_model(self, user_id: str) -> bool:
        """True when ``user_id`` has a dedicated per-user model."""
        return user_id in self.per_user_models

    def serialise(self, path: str | Path) -> None:
        """Write the bundle to ``path`` via joblib."""
        joblib.dump(self, str(path))

    @classmethod
    def deserialise(cls, path: str | Path) -> PerUserBundle:
        """Load a bundle from ``path``. Raises if the file is missing."""
        loaded: PerUserBundle = joblib.load(str(path))
        return loaded
