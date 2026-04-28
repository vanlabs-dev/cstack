"""Champion/challenger promotion gating.

V1 evaluates the candidate by running shadow scoring across the recent
sign-in window and checking the alert-volume delta gate. Promotion is a
single set_alias call that moves @champion to the challenger version; the
old champion stays as a numbered version for rollback.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import duckdb
import pandas as pd
from cstack_ml_features import FEATURE_COLUMNS
from cstack_ml_mlops import (
    CHALLENGER_ALIAS,
    CHAMPION_ALIAS,
    ShadowComparison,
    configure_tracking,
    get_alias_version,
    load_by_alias,
    set_alias,
    shadow_score,
    should_promote,
)
from cstack_storage import get_signins
from pydantic import BaseModel, ConfigDict

from cstack_ml_anomaly.scoring import _build_score_features
from cstack_ml_anomaly.training import pooled_model_name


class PromotionDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    promote: bool
    reason: str
    comparison: ShadowComparison | None
    challenger_version: str | None


def evaluate_for_promotion(
    tenant_id: str,
    conn: duckdb.DuckDBPyConnection,
    recent_window_days: int = 7,
    tracking_uri: str | None = None,
) -> PromotionDecision:
    """Run shadow scoring of @challenger vs @champion on the recent window."""
    configure_tracking(uri=tracking_uri)
    model_name = pooled_model_name(tenant_id)
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

    challenger_model = load_by_alias(model_name, CHALLENGER_ALIAS)
    champion_model = load_by_alias(model_name, CHAMPION_ALIAS)

    since = datetime.now(UTC) - timedelta(days=recent_window_days)
    signins = get_signins(conn, tenant_id, since=since)
    if not signins:
        return PromotionDecision(
            promote=False,
            reason="no recent sign-ins to compare on",
            comparison=None,
            challenger_version=str(challenger.version),
        )
    feature_df: Any = _build_score_features(signins)
    feature_df = feature_df[list(FEATURE_COLUMNS)] if not feature_df.empty else pd.DataFrame()
    comparison = shadow_score(champion_model, challenger_model, feature_df)
    promote, reason = should_promote(comparison)
    return PromotionDecision(
        promote=promote,
        reason=reason,
        comparison=comparison,
        challenger_version=str(challenger.version),
    )


def promote_challenger_to_champion(tenant_id: str, force: bool = False) -> PromotionDecision:
    """Move @champion to the challenger version. ``force`` bypasses gating."""
    model_name = pooled_model_name(tenant_id)
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
