"""Shadow-scoring framework for promotion gating.

Run the current production model and a candidate side by side on the same
feature batch; surface agreement, alert-volume delta, and a sample of
disagreements. The decision policy is encoded in ``should_promote`` so the
CLI just calls it.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict


class ShadowComparison(BaseModel):
    """Outcome of running two models on the same data."""

    model_config = ConfigDict(frozen=True)

    champion_anomalies: int
    challenger_anomalies: int
    rows_compared: int
    agreement_pct: float
    alert_volume_delta_pct: float
    disagreement_examples: list[dict[str, Any]]


def shadow_score(
    champion_model: Any,
    challenger_model: Any,
    feature_df: pd.DataFrame,
    sample_disagreements: int = 5,
) -> ShadowComparison:
    """Run both models on the same feature batch and compare predictions.

    Both models must expose ``predict`` returning -1 for anomaly and 1 for
    normal (the sklearn IsolationForest convention).
    """
    if feature_df.empty:
        return ShadowComparison(
            champion_anomalies=0,
            challenger_anomalies=0,
            rows_compared=0,
            agreement_pct=1.0,
            alert_volume_delta_pct=0.0,
            disagreement_examples=[],
        )
    champion_pred = np.asarray(champion_model.predict(feature_df))
    challenger_pred = np.asarray(challenger_model.predict(feature_df))

    champion_anom_count = int((champion_pred == -1).sum())
    challenger_anom_count = int((challenger_pred == -1).sum())

    agree_mask = champion_pred == challenger_pred
    agreement_pct = float(agree_mask.mean()) if agree_mask.size else 1.0

    if champion_anom_count == 0:
        alert_delta_pct = float("inf") if challenger_anom_count > 0 else 0.0
    else:
        alert_delta_pct = (
            (challenger_anom_count - champion_anom_count) / champion_anom_count * 100.0
        )

    # Pull a few example disagreements where champion=normal but challenger=anomaly,
    # which is the direction operators care about most (alert-volume increase).
    disagreement_indices = np.where(~agree_mask)[0]
    rng_choice = (
        disagreement_indices[:sample_disagreements].tolist() if disagreement_indices.size else []
    )
    examples: list[dict[str, Any]] = []
    for idx in rng_choice:
        row = feature_df.iloc[int(idx)].to_dict()
        examples.append(
            {
                "row_index": int(idx),
                "champion": int(champion_pred[int(idx)]),
                "challenger": int(challenger_pred[int(idx)]),
                "features": {k: float(v) for k, v in row.items()},
            }
        )

    return ShadowComparison(
        champion_anomalies=champion_anom_count,
        challenger_anomalies=challenger_anom_count,
        rows_compared=int(feature_df.shape[0]),
        agreement_pct=agreement_pct,
        alert_volume_delta_pct=float(alert_delta_pct)
        if alert_delta_pct != float("inf")
        else 1000.0,
        disagreement_examples=examples,
    )


def should_promote(
    comparison: ShadowComparison, max_alert_delta_pct: float = 20.0
) -> tuple[bool, str]:
    """Gate promotion on alert-volume delta and minimum sample size."""
    if comparison.rows_compared < 100:
        return (
            False,
            f"too few comparison rows ({comparison.rows_compared} < 100); "
            "skip promotion until more sign-ins land",
        )
    if abs(comparison.alert_volume_delta_pct) > max_alert_delta_pct:
        return (
            False,
            "alert volume delta "
            f"{comparison.alert_volume_delta_pct:+.1f}% exceeds the "
            f"{max_alert_delta_pct:.1f}% gate; investigate before promoting",
        )
    return (
        True,
        f"agreement {comparison.agreement_pct:.1%}, "
        f"alert delta {comparison.alert_volume_delta_pct:+.1f}%; promotion safe",
    )
