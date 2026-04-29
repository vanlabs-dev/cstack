"""Champion/challenger promotion gating.

V1 evaluates the candidate by running shadow scoring across the recent
sign-in window and checking the alert-volume delta gate. Promotion is a
single set_alias call that moves @champion to the challenger version; the
old champion stays as a numbered version for rollback.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from cstack_ml_features import FEATURE_COLUMNS
from cstack_ml_mlops import (
    CHALLENGER_ALIAS,
    CHAMPION_ALIAS,
    ShadowComparison,
    configure_tracking,
    download_artifact_by_alias,
    get_alias_version,
    set_alias,
    shadow_score,
    should_promote,
)
from cstack_storage import get_signins
from pydantic import BaseModel, ConfigDict

from cstack_ml_anomaly.per_user import PerUserBundle
from cstack_ml_anomaly.scoring import _build_score_features
from cstack_ml_anomaly.training import tenant_model_name


class PromotionDecision(BaseModel):
    """Result of running the promotion gate.

    ``comparison`` is the shadow scoring comparison used to make the
    decision; it's None when the gate refused early (no champion, too few
    rows, no challenger).
    """

    model_config = ConfigDict(frozen=True)

    promote: bool
    reason: str
    comparison: ShadowComparison | None
    challenger_version: str | None


def _load_bundle_from_alias(model_name: str, alias: str) -> PerUserBundle:
    artefact_dir = download_artifact_by_alias(model_name, alias)
    return PerUserBundle.deserialise(Path(artefact_dir) / "model.joblib")


class _BundlePredictAdapter:
    """Wrap a PerUserBundle so it exposes the sklearn ``.predict`` shape.

    Required because ``cstack_ml_mlops.shadow.shadow_score`` was written
    for sklearn-flavour models with a single ``.predict`` over the whole
    batch; the bundle routes per row through different pipelines.
    """

    def __init__(self, bundle: PerUserBundle, user_ids: list[str]) -> None:
        self._bundle = bundle
        self._user_ids = user_ids

    def predict(self, feature_df: pd.DataFrame) -> np.ndarray:
        feature_cols = list(self._bundle.feature_columns)
        out = np.ones(len(feature_df), dtype=int)
        for i, user_id in enumerate(self._user_ids):
            model: Any = self._bundle.per_user_models.get(user_id) or self._bundle.cold_start_pooled
            if model is None:
                continue
            row = feature_df.iloc[[i]][feature_cols]
            out[i] = int(model.predict(row)[0])
        return out


def evaluate_for_promotion(
    tenant_id: str,
    conn: duckdb.DuckDBPyConnection,
    recent_window_days: int = 7,
    tracking_uri: str | None = None,
) -> PromotionDecision:
    """Run shadow scoring of @challenger vs @champion on the recent window."""
    configure_tracking(uri=tracking_uri)
    model_name = tenant_model_name(tenant_id)
    challenger = get_alias_version(model_name, CHALLENGER_ALIAS)
    champion = get_alias_version(model_name, CHAMPION_ALIAS)
    if challenger is None:
        return PromotionDecision(
            promote=False,
            reason="no @challenger version registered",
            comparison=None,
            challenger_version=None,
        )
    if champion is None:
        return PromotionDecision(
            promote=True,
            reason="no @champion yet; promote first challenger as the initial champion",
            comparison=None,
            challenger_version=str(challenger.version),
        )

    challenger_bundle = _load_bundle_from_alias(model_name, CHALLENGER_ALIAS)
    champion_bundle = _load_bundle_from_alias(model_name, CHAMPION_ALIAS)

    since = datetime.now(UTC) - timedelta(days=recent_window_days)
    signins = get_signins(conn, tenant_id, since=since)
    if not signins:
        return PromotionDecision(
            promote=False,
            reason="no recent sign-ins to compare on",
            comparison=None,
            challenger_version=str(challenger.version),
        )
    feature_df, user_ids = _build_score_features(signins)
    feature_df = feature_df[list(FEATURE_COLUMNS)] if not feature_df.empty else pd.DataFrame()
    comparison = shadow_score(
        _BundlePredictAdapter(champion_bundle, user_ids),
        _BundlePredictAdapter(challenger_bundle, user_ids),
        feature_df,
    )
    promote, reason = should_promote(comparison)
    return PromotionDecision(
        promote=promote,
        reason=reason,
        comparison=comparison,
        challenger_version=str(challenger.version),
    )


def promote_challenger_to_champion(
    tenant_id: str, force: bool = False, tracking_uri: str | None = None
) -> PromotionDecision:
    """Move @champion to the challenger version. ``force`` bypasses gating."""
    configure_tracking(uri=tracking_uri)
    model_name = tenant_model_name(tenant_id)
    challenger = get_alias_version(model_name, CHALLENGER_ALIAS)
    if challenger is None:
        return PromotionDecision(
            promote=False,
            reason="no @challenger version to promote",
            comparison=None,
            challenger_version=None,
        )
    set_alias(model_name, challenger.version, CHAMPION_ALIAS)
    return PromotionDecision(
        promote=True,
        reason=f"promoted v{challenger.version} to @{CHAMPION_ALIAS}"
        + (" (forced)" if force else ""),
        comparison=None,
        challenger_version=str(challenger.version),
    )
