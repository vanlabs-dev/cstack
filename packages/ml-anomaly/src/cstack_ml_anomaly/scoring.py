"""Per-signin scoring with SHAP attribution.

Loads the @champion (or @challenger fallback) tenant bundle and routes
each row through either its per-user pipeline or the cold-start pooled
pipeline. SHAP attributions are computed only on flagged rows because
SHAP is expensive (~5 calls/sec for IsolationForest); restricting to
flagged rows keeps a 3000-row score pass under 30 seconds.

We use ``shap.Explainer`` over ``score_samples`` rather than
``shap.TreeExplainer`` deliberately: TreeExplainer has known footguns
with IsolationForest because IF leaf weighting differs from random
forests. The Explainer-over-prediction-fn path is the community-standard
route.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import joblib
import numpy as np
import pandas as pd
import shap
from cstack_audit_core import AnomalyScore, ModelTier, ShapDirection, ShapFeatureContribution
from cstack_audit_coverage import TIER_0_ROLE_TEMPLATE_IDS
from cstack_ml_features import (
    FEATURE_COLUMNS,
    build_history_from_signins,
    extract_features_batch,
)
from cstack_ml_mlops import (
    CHALLENGER_ALIAS,
    CHAMPION_ALIAS,
    configure_tracking,
    download_artifact_by_alias,
    get_alias_version,
)
from cstack_schemas import SignIn
from cstack_storage import get_directory_roles, get_role_assignments, get_signins

from cstack_ml_anomaly.per_user import PerUserBundle
from cstack_ml_anomaly.rules import rule_score_boosts
from cstack_ml_anomaly.score import normalise_score
from cstack_ml_anomaly.training import tenant_model_name

LOG = logging.getLogger(__name__)

ANOMALY_THRESHOLD = 0.7
SHAP_BACKGROUND_SAMPLE = 100


def load_bundle(
    tenant_id: str, prefer_alias: str = CHAMPION_ALIAS
) -> tuple[PerUserBundle, str, str]:
    """Load the tenant's @champion (or @challenger fallback) bundle.

    Returns ``(bundle, alias_used, version)``. Raises ``LookupError`` if
    no version is registered.
    """
    name = tenant_model_name(tenant_id)
    if prefer_alias != CHALLENGER_ALIAS:
        aliases: tuple[str, ...] = (prefer_alias, CHALLENGER_ALIAS)
    else:
        aliases = (CHALLENGER_ALIAS,)
    seen: set[str] = set()
    for alias in aliases:
        if alias in seen:
            continue
        seen.add(alias)
        version = get_alias_version(name, alias)
        if version is None:
            continue
        artefact_dir = download_artifact_by_alias(name, alias)
        bundle_path = Path(artefact_dir) / "model.joblib"
        if not bundle_path.exists():
            raise LookupError(
                f"alias @{alias} of {name} resolved but model.joblib not found at {bundle_path}"
            )
        bundle: PerUserBundle = joblib.load(bundle_path)
        return bundle, alias, str(version.version)
    raise LookupError(f"no @{CHAMPION_ALIAS} or @{CHALLENGER_ALIAS} version of {name} registered")


def _build_score_features(signins: list[SignIn]) -> tuple[pd.DataFrame, list[str]]:
    """Compute features for each signin using prefix history of the same batch.

    Returns ``(feature_df, user_ids)`` where ``user_ids[i]`` is the user
    that owns ``feature_df.iloc[i]``. Iterates users in alphabetical order
    so callers that recover a parallel ordering of the original sign-ins
    produce the same row layout.
    """
    by_user: dict[str, list[SignIn]] = {}
    for s in signins:
        by_user.setdefault(s.user_id, []).append(s)
    items: list[Any] = []
    user_ids: list[str] = []
    for uid in sorted(by_user.keys()):
        sorted_group = sorted(by_user[uid], key=lambda s: s.created_date_time)
        for signin in sorted_group:
            history = build_history_from_signins(sorted_group, as_of=signin.created_date_time)
            items.append((signin, history))
            user_ids.append(uid)
    df = extract_features_batch(items)
    return df, user_ids


def _bundle_score_rows(
    bundle: PerUserBundle, feature_df: pd.DataFrame, user_ids: list[str]
) -> tuple[list[float], list[ModelTier], list[bool]]:
    """Score every row through its per-user or cold-start pipeline.

    Returns ``(raw_scores, model_tiers, predictions)`` where ``predictions``
    is True when the IF predicts -1 (anomaly) for that row. Rule-only
    rows (no per-user, no pooled) have raw_score=0.0 and prediction=False.
    """
    raw_scores: list[float] = []
    tiers: list[ModelTier] = []
    predictions: list[bool] = []
    feature_cols = list(bundle.feature_columns)
    for i, user_id in enumerate(user_ids):
        row = feature_df.iloc[[i]][feature_cols]
        per_user_model = bundle.per_user_models.get(user_id)
        tier: ModelTier
        if per_user_model is not None:
            model = per_user_model
            tier = "per_user"
        elif bundle.cold_start_pooled is not None:
            model = bundle.cold_start_pooled
            tier = "cold_start_pooled"
        else:
            raw_scores.append(0.0)
            tiers.append("rule_only")
            predictions.append(False)
            continue
        raw = float(model.decision_function(row)[0])
        pred = int(model.predict(row)[0])
        raw_scores.append(raw)
        tiers.append(tier)
        predictions.append(pred == -1)
    return raw_scores, tiers, predictions


def _shap_for_anomalous_rows(
    bundle: PerUserBundle,
    feature_df: pd.DataFrame,
    user_ids: list[str],
    anom_indices: list[int],
    background_df: pd.DataFrame,
) -> dict[int, list[ShapFeatureContribution]]:
    """Compute SHAP top-3 for flagged rows. Background pulls from the same
    pipeline that scored the row so attributions match the routing path."""
    if not anom_indices:
        return {}
    feature_cols = list(bundle.feature_columns)
    bg_pool = background_df[feature_cols] if not background_df.empty else feature_df[feature_cols]
    bg = bg_pool.sample(
        n=min(len(bg_pool), SHAP_BACKGROUND_SAMPLE),
        random_state=42,
    )
    shap_lookup: dict[int, list[ShapFeatureContribution]] = {}
    for idx in anom_indices:
        user_id = user_ids[idx]
        model = bundle.per_user_models.get(user_id) or bundle.cold_start_pooled
        if model is None:
            shap_lookup[idx] = []
            continue
        explainer = shap.Explainer(model.score_samples, bg)
        row = feature_df.iloc[[idx]][feature_cols]
        shap_values = explainer(row).values[0]
        order = np.argsort(np.abs(shap_values))[::-1][:3]
        contributions: list[ShapFeatureContribution] = []
        for col_idx in order:
            shap_val = float(shap_values[int(col_idx)])
            direction: ShapDirection = "pushes_anomalous" if shap_val < 0 else "pushes_normal"
            contributions.append(
                ShapFeatureContribution(
                    feature_name=feature_cols[int(col_idx)],
                    feature_value=float(row.iloc[0, int(col_idx)]),
                    shap_value=shap_val,
                    direction=direction,
                )
            )
        shap_lookup[idx] = contributions
    return shap_lookup


def _compute_privileged_user_ids(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> frozenset[str]:
    """Pull tier-0 admin user ids from the directory tables for ``tenant_id``.

    Returns the union of principals listed under any tier-0 role assignment
    or directly in a directory role's ``members`` array. Empty when the
    tenant has no tier-0 admins recorded.
    """
    roles = get_directory_roles(conn, tenant_id)
    assignments = get_role_assignments(conn, tenant_id)
    user_ids: set[str] = set()
    for role in roles:
        if role.role_template_id in TIER_0_ROLE_TEMPLATE_IDS:
            user_ids.update(role.members)
    for assignment in assignments:
        if (
            assignment.role_definition_id in TIER_0_ROLE_TEMPLATE_IDS
            and assignment.principal_id is not None
        ):
            user_ids.add(assignment.principal_id)
    return frozenset(user_ids)


def score_batch(
    signins: list[SignIn],
    tenant_id: str,
    conn: duckdb.DuckDBPyConnection,
    background_signins: list[SignIn] | None = None,
    tracking_uri: str | None = None,
    enable_rules: bool = True,
    enable_off_hours_admin: bool = True,
) -> list[AnomalyScore]:
    """Score a batch of sign-ins. Loads the bundle, routes per user, then
    layers the rule booster on top.

    ``enable_rules=False`` returns the raw model score without the booster
    floor. Used by the layer-attribution sweep in Phase 4 to measure
    each tier's contribution independently. ``enable_off_hours_admin``
    further toggles the per-user admin rule independently of the four
    Sprint 3 hybrid rules; defaults to on.
    """
    if not signins:
        return []
    configure_tracking(uri=tracking_uri)
    bundle, _alias, version = load_bundle(tenant_id)
    background = (
        background_signins if background_signins is not None else (get_signins(conn, tenant_id))
    )
    bg_df, _ = (
        _build_score_features(background)
        if background
        else (pd.DataFrame(columns=list(FEATURE_COLUMNS)), [])
    )
    feature_df, user_ids = _build_score_features(signins)
    raw_scores, tiers, predictions = _bundle_score_rows(bundle, feature_df, user_ids)
    if enable_rules:
        privileged_ids = (
            _compute_privileged_user_ids(conn, tenant_id) if enable_off_hours_admin else frozenset()
        )
        rule_boosts = rule_score_boosts(
            feature_df,
            user_ids=user_ids,
            bundle=bundle,
            privileged_user_ids=privileged_ids,
        )
    else:
        rule_boosts = [0.0] * len(feature_df)

    sorted_signins: list[SignIn] = []
    by_user: dict[str, list[SignIn]] = {}
    for s in signins:
        by_user.setdefault(s.user_id, []).append(s)
    for uid in sorted(by_user.keys()):
        sorted_signins.extend(sorted(by_user[uid], key=lambda s: s.created_date_time))

    is_anom_mask: list[bool] = []
    normalised_scores: list[float] = []
    for i in range(len(sorted_signins)):
        normalised = normalise_score(raw_scores[i]) if tiers[i] != "rule_only" else 0.0
        normalised = max(normalised, rule_boosts[i])
        normalised_scores.append(normalised)
        is_anom_mask.append(predictions[i] or normalised >= ANOMALY_THRESHOLD)

    anom_indices = [i for i, flagged in enumerate(is_anom_mask) if flagged]
    shap_lookup = _shap_for_anomalous_rows(bundle, feature_df, user_ids, anom_indices, bg_df)

    scored_at = datetime.now(UTC)
    results: list[AnomalyScore] = []
    model_name = tenant_model_name(tenant_id)
    for i, signin in enumerate(sorted_signins):
        results.append(
            AnomalyScore(
                tenant_id=tenant_id,
                signin_id=signin.id,
                user_id=signin.user_id,
                model_name=model_name,
                model_version=version,
                raw_score=raw_scores[i],
                normalised_score=normalised_scores[i],
                is_anomaly=is_anom_mask[i],
                shap_top_features=shap_lookup.get(i, []),
                scored_at=scored_at,
                model_tier=tiers[i],
            )
        )
        LOG.debug(
            "anomaly score row",
            extra={
                "tenant_id": tenant_id,
                "user_id": signin.user_id,
                "signin_id": signin.id,
                "model_tier": tiers[i],
                "normalised_score": normalised_scores[i],
            },
        )
    return results
