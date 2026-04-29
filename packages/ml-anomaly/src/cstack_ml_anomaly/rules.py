"""Deterministic post-IF score booster.

Each rule encodes an unambiguous attack pattern that the IsolationForest
should not be asked to learn from baseline data alone. Boosts are
computed independently per rule and combined via ``max`` so the highest-
confidence rule wins. The booster takes a final ``max`` against the IF's
normalised score in the caller so a strong IF signal is never downgraded.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

# Travel speed at which a row is treated as physically impossible regardless
# of any model output. Commercial flights cap around 900 km/h; we leave
# overhead so legitimate-but-fast travel does not trip the rule.
TRAVEL_SPEED_FLOOR_KMH = 1500.0

RULE_TRAVEL_SPEED_FLOOR = 0.95
RULE_NEW_COUNTRY_AND_ASN_FLOOR = 0.85
RULE_FAILURE_AND_NEW_ASN_FLOOR = 0.85
RULE_MFA_BYPASS_LEGACY_FLOOR = 0.80


def _hybrid_rule_boost(row: Any) -> float:
    """Score floor from the four Sprint 3 hybrid rules."""
    score = 0.0
    if getattr(row, "travel_speed_kmh", 0.0) > TRAVEL_SPEED_FLOOR_KMH:
        score = max(score, RULE_TRAVEL_SPEED_FLOOR)
    if getattr(row, "is_new_country_for_user", 0) and getattr(row, "is_new_asn_for_user", 0):
        score = max(score, RULE_NEW_COUNTRY_AND_ASN_FLOOR)
    if getattr(row, "is_failure", 0) and getattr(row, "is_new_asn_for_user", 0):
        score = max(score, RULE_FAILURE_AND_NEW_ASN_FLOOR)
    mfa = getattr(row, "mfa_satisfied", 1)
    legacy = getattr(row, "is_legacy_auth", 0)
    if not mfa and legacy:
        score = max(score, RULE_MFA_BYPASS_LEGACY_FLOOR)
    return score


def rule_score_boosts(feature_df: pd.DataFrame) -> list[float]:
    """Compute the per-row hybrid-rule score floors."""
    return [_hybrid_rule_boost(row) for row in feature_df.itertuples(index=False)]
