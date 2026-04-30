"""Per-tenant Isolation Forest trainer with two-topology routing.

Sprint 3 trained a single pooled model per tenant; Sprint 3.5 added a
per-user topology with a cold-start pooled fallback. Sprint 3.5b
discovered the per-user topology regressed precision on synthetic
fixtures (the synthesizer's deterministic profiles lack real per-user
behavioural variance) and gated it behind ``CSTACK_ML_TRAINING_TOPOLOGY``,
defaulting to ``pooled``. The infrastructure stays in place for Sprint 7
real-data activation.

Both topologies emit a ``PerUserBundle`` artefact with the same shape
so scoring code is topology-agnostic. In ``pooled`` mode
``per_user_models`` is empty and ``cold_start_pooled`` carries the
single tenant-wide IF; every signin routes through cold-start at score
time. In ``per_user`` mode users with ``>= min_samples`` sign-ins get
dedicated pipelines and a smaller per-user time-only model used by the
off-hours-admin rule; users below the threshold contribute to a
narrower cold-start pool.

The bundle is logged to MLflow as a single ``model.joblib`` artefact
under ``signalguard-anomaly-{tenant_id}`` and aliased ``@challenger``.
The MLflow run carries a ``topology`` tag so eval history records
which topology produced each version.
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import mlflow
import numpy as np
from cstack_ml_features import (
    FEATURE_COLUMNS,
    build_history_from_signins,
    extract_features_batch,
)
from cstack_ml_mlops import (
    CHALLENGER_ALIAS,
    CHAMPION_ALIAS,
    configure_tracking,
    get_alias_version,
    register_model,
    set_alias,
    standard_tags,
)
from cstack_schemas import SignIn
from cstack_storage import get_signins
from pydantic import BaseModel, ConfigDict
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from cstack_ml_anomaly.per_user import PerUserBundle, min_samples_default

LOG = logging.getLogger(__name__)

DEFAULT_RANDOM_STATE = 42
MIN_SIGNINS_FOR_TRAINING = 100

DEFAULT_TOPOLOGY = "pooled"
VALID_TOPOLOGIES = frozenset({"pooled", "per_user"})

TIME_FEATURE_COLUMNS: tuple[str, ...] = (
    "day_of_week",
    "hour_of_day_cos",
    "hour_of_day_sin",
    "is_business_hours_local",
)


def resolve_topology(override: str | None = None) -> str:
    """Resolve the active training topology.

    Priority: explicit ``override`` argument, then ``CSTACK_ML_TRAINING_TOPOLOGY``
    env var, then ``pooled``. Validates the value is in
    ``VALID_TOPOLOGIES`` and raises ``ValueError`` otherwise so a typo
    fails fast instead of silently selecting a topology no one expected.
    """
    raw = override if override is not None else os.environ.get("CSTACK_ML_TRAINING_TOPOLOGY")
    if not raw:
        return DEFAULT_TOPOLOGY
    value = raw.lower().strip()
    if value not in VALID_TOPOLOGIES:
        raise ValueError(
            f"Invalid CSTACK_ML_TRAINING_TOPOLOGY: {raw!r}; "
            f"expected one of {sorted(VALID_TOPOLOGIES)}"
        )
    return value


def tenant_model_name(tenant_id: str) -> str:
    """Stable MLflow registered-model name for a tenant's anomaly bundle.

    The Sprint 3 ``-pooled-`` segment is gone: one name per tenant covers
    both per-user and pooled topologies so the registry stays clean
    across architectural moves.
    """
    return f"signalguard-anomaly-{tenant_id}"


# Backwards-compatibility alias for any caller that still imports the
# old name. New code should prefer ``tenant_model_name``.
pooled_model_name = tenant_model_name


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
    n_users_per_user: int
    n_users_cold_start: int
    min_samples_threshold: int
    training_duration_seconds: float
    skipped_existing: bool = False
    topology: str = DEFAULT_TOPOLOGY


def _features_for_user_signins(
    signins: list[SignIn],
) -> Any:
    """Build a feature DataFrame for a single user's sign-ins.

    Each row's history is computed strictly from sign-ins before the
    row's timestamp so features never leak the row's own value.
    """
    sorted_signins = sorted(signins, key=lambda s: s.created_date_time)
    items: list[Any] = []
    for signin in sorted_signins:
        history = build_history_from_signins(sorted_signins, as_of=signin.created_date_time)
        items.append((signin, history))
    return extract_features_batch(items)


def _fit_pipeline(
    feature_df: Any,
    columns: tuple[str, ...],
    contamination: float,
    random_state: int,
) -> Pipeline:
    """Fit a StandardScaler + IsolationForest pipeline on the requested cols.

    Scaling matters: ``distance_from_last_signin_km`` (0..20000) would
    otherwise dominate the tree splits and crowd out 0/1 categorical
    signals. ``random_state=42`` is the convention everywhere; tests
    rely on it for reproducibility.
    """
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "iforest",
                IsolationForest(
                    n_estimators=200,
                    contamination=contamination,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    pipeline.fit(feature_df[list(columns)])
    return pipeline


def train_pooled_topology(
    tenant_id: str,
    signins: list[SignIn],
    contamination: float = 0.05,
    random_state: int = DEFAULT_RANDOM_STATE,
    min_samples: int | None = None,
) -> PerUserBundle:
    """Sprint 3 pooled topology: one IF on all tenant signins.

    Returns a ``PerUserBundle`` with ``per_user_models = {}`` and the
    single fitted pipeline assigned to ``cold_start_pooled``. Every
    signin routes through cold-start at score time, which is the
    Sprint 3 behaviour exactly. ``min_samples`` is accepted for
    signature parity with ``train_per_user_topology`` but does not
    influence the fit; it is recorded on the bundle for telemetry.
    """
    if len(signins) < MIN_SIGNINS_FOR_TRAINING:
        raise ValueError(
            f"need at least {MIN_SIGNINS_FOR_TRAINING} sign-ins to train; got {len(signins)}"
        )
    threshold = min_samples if min_samples is not None else min_samples_default()

    user_signins: dict[str, list[SignIn]] = defaultdict(list)
    for signin in signins:
        user_signins[signin.user_id].append(signin)

    items: list[Any] = []
    for _user_id, rows in user_signins.items():
        sorted_signins = sorted(rows, key=lambda s: s.created_date_time)
        for signin in sorted_signins:
            history = build_history_from_signins(sorted_signins, as_of=signin.created_date_time)
            items.append((signin, history))
    feature_df = extract_features_batch(items)
    pooled_pipeline = _fit_pipeline(feature_df, FEATURE_COLUMNS, contamination, random_state)

    bundle = PerUserBundle(
        tenant_id=tenant_id,
        per_user_models={},
        cold_start_pooled=pooled_pipeline,
        feature_columns=tuple(FEATURE_COLUMNS),
        trained_at=datetime.now(UTC),
        n_users_per_user=0,
        n_users_cold_start=len(user_signins),
        total_signins_used=feature_df.shape[0],
        min_samples_threshold=threshold,
        time_pipelines={},
        time_score_p90={},
    )
    LOG.info(
        "trained pooled bundle",
        extra={
            "tenant_id": tenant_id,
            "n_users": len(user_signins),
            "total_signins": bundle.total_signins_used,
            "contamination": contamination,
        },
    )
    return bundle


def train_per_user_topology(
    tenant_id: str,
    signins: list[SignIn],
    contamination: float = 0.05,
    random_state: int = DEFAULT_RANDOM_STATE,
    min_samples: int | None = None,
) -> PerUserBundle:
    """Sprint 3.5 per-user topology: one IF per user above threshold.

    Users with ``>= min_samples`` get a dedicated 20-feature pipeline and
    a 4-feature time-only pipeline (used by the off-hours-admin rule).
    Users below the threshold contribute their sign-ins to a single shared
    pooled pipeline that handles cold-start routing at score time.
    """
    if len(signins) < MIN_SIGNINS_FOR_TRAINING:
        raise ValueError(
            f"need at least {MIN_SIGNINS_FOR_TRAINING} sign-ins to train; got {len(signins)}"
        )
    threshold = min_samples if min_samples is not None else min_samples_default()

    user_signins: dict[str, list[SignIn]] = defaultdict(list)
    for signin in signins:
        user_signins[signin.user_id].append(signin)

    per_user_models: dict[str, Pipeline] = {}
    time_pipelines: dict[str, Pipeline] = {}
    time_score_p90: dict[str, float] = {}
    cold_start_signins: list[SignIn] = []
    total_rows = 0

    for user_id, rows in user_signins.items():
        if len(rows) >= threshold:
            df = _features_for_user_signins(rows)
            total_rows += df.shape[0]
            full_pipe = _fit_pipeline(df, FEATURE_COLUMNS, contamination, random_state)
            per_user_models[user_id] = full_pipe
            time_pipe = _fit_pipeline(df, TIME_FEATURE_COLUMNS, contamination, random_state)
            time_pipelines[user_id] = time_pipe
            # Negate decision_function so higher = more anomalous; the rule
            # then fires when a row's anomaly score is at or above the
            # user's training-set p90.
            time_scores = -time_pipe.decision_function(df[list(TIME_FEATURE_COLUMNS)])
            time_score_p90[user_id] = float(np.percentile(time_scores, 90))
        else:
            cold_start_signins.extend(rows)

    cold_start_pooled: Pipeline | None = None
    n_users_cold_start = sum(1 for rows in user_signins.values() if len(rows) < threshold)
    if cold_start_signins:
        df = _features_for_user_signins(cold_start_signins)
        total_rows += df.shape[0]
        cold_start_pooled = _fit_pipeline(df, FEATURE_COLUMNS, contamination, random_state)

    bundle = PerUserBundle(
        tenant_id=tenant_id,
        per_user_models=per_user_models,
        cold_start_pooled=cold_start_pooled,
        feature_columns=tuple(FEATURE_COLUMNS),
        trained_at=datetime.now(UTC),
        n_users_per_user=len(per_user_models),
        n_users_cold_start=n_users_cold_start,
        total_signins_used=total_rows,
        min_samples_threshold=threshold,
        time_pipelines=time_pipelines,
        time_score_p90=time_score_p90,
    )
    LOG.info(
        "trained per-user bundle",
        extra={
            "tenant_id": tenant_id,
            "n_users_per_user": bundle.n_users_per_user,
            "n_users_cold_start": bundle.n_users_cold_start,
            "total_signins": bundle.total_signins_used,
            "contamination": contamination,
            "min_samples": threshold,
        },
    )
    return bundle


def train_tenant(
    tenant_id: str,
    conn: duckdb.DuckDBPyConnection,
    lookback_days: int = 60,
    contamination: float = 0.05,
    random_state: int = DEFAULT_RANDOM_STATE,
    min_samples: int | None = None,
    skip_if_registered: bool = False,
    tracking_uri: str | None = None,
    topology: str | None = None,
) -> TrainingResult:
    """Pull the lookback window, train the bundle, register it.

    ``topology`` selects between ``train_pooled_topology`` (Sprint 3
    default) and ``train_per_user_topology`` (Sprint 3.5 opt-in).
    Resolution order: explicit argument, ``CSTACK_ML_TRAINING_TOPOLOGY``
    env var, then ``pooled``.

    ``skip_if_registered`` short-circuits when an ``@champion`` already
    points at a version of the tenant model. The Compose bootstrap uses
    this to avoid accumulating dead registry versions on warm restarts.
    """
    configure_tracking(uri=tracking_uri)
    active_topology = resolve_topology(topology)

    model_name = tenant_model_name(tenant_id)
    if skip_if_registered:
        existing = get_alias_version(model_name, CHAMPION_ALIAS)
        if existing is not None:
            LOG.info(
                "skipping training; champion already registered",
                extra={
                    "tenant_id": tenant_id,
                    "model_name": model_name,
                    "version": str(existing.version),
                    "topology": active_topology,
                },
            )
            return TrainingResult(
                tenant_id=tenant_id,
                model_name=model_name,
                model_version=str(existing.version),
                contamination=contamination,
                random_state=random_state,
                n_signins_used=0,
                n_users=0,
                n_users_per_user=0,
                n_users_cold_start=0,
                min_samples_threshold=min_samples
                if min_samples is not None
                else min_samples_default(),
                training_duration_seconds=0.0,
                skipped_existing=True,
                topology=active_topology,
            )

    since = datetime.now(UTC) - timedelta(days=lookback_days)
    signins = get_signins(conn, tenant_id, since=since)

    started = time.perf_counter()
    if active_topology == "per_user":
        bundle = train_per_user_topology(
            tenant_id,
            signins,
            contamination=contamination,
            random_state=random_state,
            min_samples=min_samples,
        )
    else:
        bundle = train_pooled_topology(
            tenant_id,
            signins,
            contamination=contamination,
            random_state=random_state,
            min_samples=min_samples,
        )
    duration = time.perf_counter() - started

    with mlflow.start_run(
        run_name=f"train-{tenant_id}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
        tags=standard_tags(
            {
                "cstack.tenant": tenant_id,
                "cstack.role": "train",
                "topology": active_topology,
            }
        ),
    ) as run:
        mlflow.log_params(
            {
                "tenant_id": tenant_id,
                "contamination": contamination,
                "random_state": random_state,
                "lookback_days": lookback_days,
                "n_estimators": 200,
                "min_samples": bundle.min_samples_threshold,
                "topology": active_topology,
            }
        )
        mlflow.log_metrics(
            {
                "n_signins_used": float(len(signins)),
                "n_users": float(len(bundle.per_user_models) + bundle.n_users_cold_start),
                "n_users_per_user": float(bundle.n_users_per_user),
                "n_users_cold_start": float(bundle.n_users_cold_start),
                "training_duration_seconds": duration,
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            artefact_path = Path(tmpdir) / "model.joblib"
            bundle.serialise(artefact_path)
            mlflow.log_artifact(str(artefact_path), artifact_path="model")
        version = register_model(run.info.run_id, "model", model_name)
        set_alias(model_name, version.version, CHALLENGER_ALIAS)

    n_users_total = bundle.n_users_per_user + bundle.n_users_cold_start
    return TrainingResult(
        tenant_id=tenant_id,
        model_name=model_name,
        model_version=str(version.version),
        contamination=contamination,
        random_state=random_state,
        n_signins_used=bundle.total_signins_used,
        n_users=n_users_total,
        n_users_per_user=bundle.n_users_per_user,
        n_users_cold_start=bundle.n_users_cold_start,
        min_samples_threshold=bundle.min_samples_threshold,
        training_duration_seconds=duration,
        skipped_existing=False,
        topology=active_topology,
    )
