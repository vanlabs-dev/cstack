"""Score normalisation and re-exports.

The AnomalyScore + ShapFeatureContribution pydantic models live in
cstack_audit_core so the storage layer can persist them without depending
on the ML stack. This module owns the score normalisation function and
re-exports the types so ml-anomaly callers have a single import surface.
"""

from __future__ import annotations

import math

from cstack_audit_core import AnomalyScore, ShapDirection, ShapFeatureContribution

__all__ = [
    "AnomalyScore",
    "ShapDirection",
    "ShapFeatureContribution",
    "normalise_score",
]


def normalise_score(raw_score: float) -> float:
    """Map sklearn IsolationForest decision_function output to [0, 1].

    decision_function returns positive values for normal points and negative
    for anomalies; the more negative, the more anomalous. We squash through a
    logistic so the output is bounded and "higher means more anomalous"
    matches the convention every consumer expects.
    """
    return 1.0 / (1.0 + math.exp(raw_score * 6.0))
