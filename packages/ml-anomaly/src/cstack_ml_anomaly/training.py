"""Pooled per-tenant Isolation Forest trainer with MLflow tracking.

V1 trains a single pooled model per tenant: every user's sign-ins go into
one IsolationForest. Per-user dedicated models are deferred to Sprint 3.5
once we know what calibration looks like at scale.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import duckdb
import mlflow
import mlflow.sklearn
from cstack_ml_features import (
    FEATURE_COLUMNS,
    build_history_from_signins,
    extract_features_batch,
)
from cstack_ml_mlops import (
    CHALLENGER_ALIAS,
    configure_tracking,
    register_model,
    set_alias,
    standard_tags,
)
from cstack_schemas import SignIn
from cstack_storage import get_signins
from pydantic import BaseModel, ConfigDict
from sklearn.ensemble import IsolationForest

LOG = logging.getLogger(__name__)

DEFAULT_RANDOM_STATE = 42
MIN_SIGNINS_FOR_TRAINING = 100


def pooled_model_name(tenant_id: str) -> str:
    return f"signalguard-anomaly-pooled-{tenant_id}"


class TrainingResult(BaseModel):
    """Counts and identifiers from a single train_tenant call."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    model_name: str
    model_version: str
    contamination: float
    random_state: int
    n_signins_used: int
    n_users: int
    training_duration_seconds: float


def _build_training_features(
    user_signins: dict[str, list[SignIn]],
) -> tuple[Any, int]:
    """Build a feature DataFrame across every user, with each row's history
    computed from the user's sign-ins strictly before the row's timestamp."""
    items: list[Any] = []
    for _user_id, signins in user_signins.items():
        sorted_signins = sorted(signins, key=lambda s: s.created_date_time)
        for signin in sorted_signins:
            history = build_history_from_signins(sorted_signins, as_of=signin.created_date_time)
            items.append((signin, history))
    df = extract_features_batch(items)
    return df, len(items)


def train_pooled_model(
    tenant_id: str,
    signins: list[SignIn],
    contamination: float = 0.02,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> tuple[IsolationForest, Any, int]:
    """Fit a single Isolation Forest on every user's sign-ins.

    Returns (fitted_model, feature_dataframe, n_users).
    """
    if len(signins) < MIN_SIGNINS_FOR_TRAINING:
        raise ValueError(
            f"need at least {MIN_SIGNINS_FOR_TRAINING} sign-ins to train; got {len(signins)}"
        )
    user_signins: dict[str, list[SignIn]] = defaultdict(list)
    for signin in signins:
        user_signins[signin.user_id].append(signin)
    feature_df, n_rows = _build_training_features(user_signins)
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(feature_df[list(FEATURE_COLUMNS)])
    LOG.info(
        "trained pooled model",
        extra={
            "tenant_id": tenant_id,
            "n_signins": n_rows,
            "n_users": len(user_signins),
            "contamination": contamination,
        },
    )
    return model, feature_df, len(user_signins)


def train_tenant(
    tenant_id: str,
    conn: duckdb.DuckDBPyConnection,
    lookback_days: int = 60,
    contamination: float = 0.02,
    random_state: int = DEFAULT_RANDOM_STATE,
    tracking_uri: str | None = None,
) -> TrainingResult:
    """Pull the lookback window of sign-ins, train the pooled IF, register
    with @challenger alias, and return summary stats."""
    configure_tracking(uri=tracking_uri)

    since = datetime.now(UTC) - timedelta(days=lookback_days)
    signins = get_signins(conn, tenant_id, since=since)

    started = time.perf_counter()
    model, feature_df, n_users = train_pooled_model(
        tenant_id, signins, contamination=contamination, random_state=random_state
    )
    duration = time.perf_counter() - started

    model_name = pooled_model_name(tenant_id)
    with mlflow.start_run(
        run_name=f"train-{tenant_id}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
        tags=standard_tags({"cstack.tenant": tenant_id, "cstack.role": "train"}),
    ) as run:
        mlflow.log_params(
            {
                "tenant_id": tenant_id,
                "contamination": contamination,
                "random_state": random_state,
                "lookback_days": lookback_days,
                "n_estimators": 200,
            }
        )
        mlflow.log_metrics(
            {
                "n_signins_used": float(len(signins)),
                "n_users": float(n_users),
                "training_duration_seconds": duration,
            }
        )
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=None,
        )
        # Register the artifact and assign the @challenger alias.
        version = register_model(run.info.run_id, "model", model_name)
        set_alias(model_name, version.version, CHALLENGER_ALIAS)

    # The reference DataFrame is logged as an MLflow artifact for drift
    # baselines; persisting full training data is intentional.
    return TrainingResult(
        tenant_id=tenant_id,
        model_name=model_name,
        model_version=str(version.version),
        contamination=contamination,
        random_state=random_state,
        n_signins_used=feature_df.shape[0],
        n_users=n_users,
        training_duration_seconds=duration,
    )
