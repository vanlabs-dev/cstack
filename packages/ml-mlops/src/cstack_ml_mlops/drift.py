"""Population Stability Index drift monitoring.

PSI gives a single number per feature comparing two distributions; we treat
> 0.2 as significant drift, 0.1-0.2 as worth watching, < 0.1 as stable.
Industry-standard thresholds; tune per-feature later if needed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DRIFT_NONE = 0.1
DRIFT_SIGNIFICANT = 0.2

DRIFT_THRESHOLDS = {
    "none": DRIFT_NONE,
    "significant": DRIFT_SIGNIFICANT,
}


def population_stability_index(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Compute PSI between reference and current distributions.

    Bins are derived from the reference quantile edges so the metric is
    stable as the current population's range drifts. Adds a small epsilon
    to avoid log(0) when a bin is empty in either side.
    """
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    if reference.size == 0 or current.size == 0:
        return 0.0
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(reference, quantiles))
    if edges.size < 2:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    ref_counts, _ = np.histogram(reference, bins=edges)
    cur_counts, _ = np.histogram(current, bins=edges)
    eps = 1e-6
    ref_pct = ref_counts / max(ref_counts.sum(), 1) + eps
    cur_pct = cur_counts / max(cur_counts.sum(), 1) + eps
    psi = float(((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)).sum())
    return psi


def compute_feature_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: list[str],
) -> dict[str, float]:
    """PSI per feature column."""
    out: dict[str, float] = {}
    for feature in features:
        if feature not in reference_df.columns or feature not in current_df.columns:
            continue
        out[feature] = population_stability_index(
            reference_df[feature].to_numpy(), current_df[feature].to_numpy()
        )
    return out


def flag_drifting_features(
    drift_scores: dict[str, float], threshold: float = DRIFT_SIGNIFICANT
) -> list[str]:
    """Return feature names whose PSI meets or exceeds the drift threshold."""
    return [name for name, psi in drift_scores.items() if psi >= threshold]
