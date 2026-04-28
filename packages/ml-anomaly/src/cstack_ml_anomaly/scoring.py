"""Per-signin scoring with SHAP attribution.

Loads the @champion (or @challenger fallback) pooled model, runs scoring
on a feature batch, and computes top-3 SHAP contributions per signin via
``shap.Explainer`` over the model's ``score_samples`` function.

We use ``shap.Explainer`` instead of ``shap.TreeExplainer`` deliberately:
TreeExplainer has known footguns with IsolationForest because IF's leaf
weighting differs from random forests; the Explainer-over-prediction-fn
path is the community-standard route.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import shap
from cstack_audit_core import AnomalyScore, ShapDirection, ShapFeatureContribution
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
    load_by_alias,
)
from cstack_schemas import SignIn
from cstack_storage import get_signins

from cstack_ml_anomaly.score import normalise_score
from cstack_ml_anomaly.training import pooled_model_name

LOG = logging.getLogger(__name__)

ANOMALY_THRESHOLD = 0.7
SHAP_BACKGROUND_SAMPLE = 100


def _resolve_model(tenant_id: str) -> tuple[Any, str, str]:
    """Return (model, alias_used, version). Champion wins; challenger fallback."""
    name = pooled_model_name(tenant_id)
    for alias in (CHAMPION_ALIAS, CHALLENGER_ALIAS):
        version = get_alias_version(name, alias)
        if version is not None:
            model = load_by_alias(name, alias)
            return model, alias, str(version.version)
    raise LookupError(f"no @{CHAMPION_ALIAS} or @{CHALLENGER_ALIAS} version of {name} registered")


def _build_score_features(signins: list[SignIn]) -> pd.DataFrame:
    """Compute features for each signin using prefix history of the same batch.

    For scoring during a single CLI invocation we treat the batch as
    chronologically ordered; rolling state advances as we scan. This matches
    the training-time semantics so models see consistent feature shapes.
    """
    by_user: dict[str, list[SignIn]] = {}
    for s in signins:
        by_user.setdefault(s.user_id, []).append(s)
    items: list[Any] = []
    for _uid, group in by_user.items():
        sorted_group = sorted(group, key=lambda s: s.created_date_time)
        for signin in sorted_group:
            history = build_history_from_signins(sorted_group, as_of=signin.created_date_time)
            items.append((signin, history))
    df = extract_features_batch(items)
    return df


def _shap_top_features(
    model: Any,
    feature_df: pd.DataFrame,
    background_df: pd.DataFrame,
    top_k: int = 3,
) -> list[list[ShapFeatureContribution]]:
    """Compute SHAP top-K contributions for each row via shap.Explainer."""
    if feature_df.empty:
        return []
    bg = background_df.sample(
        n=min(len(background_df), SHAP_BACKGROUND_SAMPLE),
        random_state=42,
    )
    explainer = shap.Explainer(model.score_samples, bg)
    shap_values = explainer(feature_df).values
    out: list[list[ShapFeatureContribution]] = []
    columns = list(feature_df.columns)
    for i in range(feature_df.shape[0]):
        row = shap_values[i]
        order = np.argsort(np.abs(row))[::-1][:top_k]
        contributions: list[ShapFeatureContribution] = []
        for idx in order:
            shap_val = float(row[int(idx)])
            # decision_function is "higher = more normal", so a negative SHAP
            # value pushes the prediction toward anomaly.
            direction: ShapDirection = "pushes_anomalous" if shap_val < 0 else "pushes_normal"
            contributions.append(
                ShapFeatureContribution(
                    feature_name=columns[int(idx)],
                    feature_value=float(feature_df.iloc[i, int(idx)]),
                    shap_value=shap_val,
                    direction=direction,
                )
            )
        out.append(contributions)
    return out


def score_batch(
    signins: list[SignIn],
    tenant_id: str,
    conn: duckdb.DuckDBPyConnection,
    background_signins: list[SignIn] | None = None,
    tracking_uri: str | None = None,
) -> list[AnomalyScore]:
    """Score a batch of sign-ins. Loads @champion (or @challenger) model.

    ``background_signins`` is the reference distribution SHAP samples from;
    defaults to the full sign-in history for the tenant in the DB.
    """
    if not signins:
        return []
    configure_tracking(uri=tracking_uri)
    model, _alias, version = _resolve_model(tenant_id)
    background = (
        background_signins if background_signins is not None else (get_signins(conn, tenant_id))
    )
    bg_df = (
        _build_score_features(background)
        if background
        else pd.DataFrame(columns=list(FEATURE_COLUMNS))
    )
    score_df = _build_score_features(signins)
    feature_only = score_df[list(FEATURE_COLUMNS)]
    raw_scores = model.decision_function(feature_only)
    predictions = model.predict(feature_only)

    # Reorder the input list to match the order produced by _build_score_features,
    # which groups by user_id and then sorts by created_date_time.
    sorted_signins: list[SignIn] = []
    for _uid, group in sorted(
        (
            (uid, sorted(grp, key=lambda s: s.created_date_time))
            for uid, grp in (
                {s.user_id: [s2 for s2 in signins if s2.user_id == s.user_id] for s in signins}
            ).items()
        ),
        key=lambda kv: kv[0],
    ):
        sorted_signins.extend(group)

    # SHAP is expensive (~5 calls/sec for IsolationForest via PermutationExplainer);
    # scoring 3000+ rows with full SHAP takes ~10 minutes. Restrict SHAP to rows the
    # model already flags as anomalous so we still surface explanations on the rows
    # that drive findings without paying for normal rows.
    is_anom_mask: list[bool] = []
    normalised_scores: list[float] = []
    for i in range(len(sorted_signins)):
        raw = float(raw_scores[i])
        normalised = normalise_score(raw)
        normalised_scores.append(normalised)
        is_anom_mask.append(bool(predictions[i] == -1) or normalised >= ANOMALY_THRESHOLD)

    anom_indices = [i for i, flagged in enumerate(is_anom_mask) if flagged]
    if anom_indices:
        anom_df = feature_only.iloc[anom_indices].reset_index(drop=True)
        shap_for_anom = _shap_top_features(model, anom_df, bg_df)
    else:
        shap_for_anom = []
    shap_lookup = dict(zip(anom_indices, shap_for_anom, strict=False))

    scored_at = datetime.now(UTC)
    results: list[AnomalyScore] = []
    for i, signin in enumerate(sorted_signins):
        results.append(
            AnomalyScore(
                tenant_id=tenant_id,
                signin_id=signin.id,
                user_id=signin.user_id,
                model_name=pooled_model_name(tenant_id),
                model_version=version,
                raw_score=float(raw_scores[i]),
                normalised_score=normalised_scores[i],
                is_anomaly=is_anom_mask[i],
                shap_top_features=shap_lookup.get(i, []),
                scored_at=scored_at,
            )
        )
    return results
