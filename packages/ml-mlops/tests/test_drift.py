import numpy as np
import pandas as pd
from cstack_ml_mlops import (
    compute_feature_drift,
    flag_drifting_features,
    population_stability_index,
)


def test_psi_identical_distributions_near_zero() -> None:
    rng = np.random.default_rng(42)
    samples = rng.normal(0, 1, 1000)
    psi = population_stability_index(samples, samples)
    assert psi < 1e-3


def test_psi_shifted_distribution_above_significant_threshold() -> None:
    rng = np.random.default_rng(42)
    reference = rng.normal(0, 1, 1000)
    current = rng.normal(3, 1, 1000)
    psi = population_stability_index(reference, current)
    assert psi > 0.2


def test_compute_feature_drift_picks_drifting_columns() -> None:
    rng = np.random.default_rng(7)
    ref = pd.DataFrame(
        {
            "stable": rng.normal(0, 1, 500),
            "drifting": rng.normal(0, 1, 500),
        }
    )
    cur = pd.DataFrame(
        {
            "stable": rng.normal(0, 1, 500),
            "drifting": rng.normal(4, 1, 500),
        }
    )
    drift = compute_feature_drift(ref, cur, ["stable", "drifting"])
    flagged = flag_drifting_features(drift)
    assert "drifting" in flagged
    assert "stable" not in flagged


def test_psi_returns_zero_on_empty_input() -> None:
    assert population_stability_index(np.array([]), np.array([1.0, 2.0])) == 0.0
