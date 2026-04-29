"""Deterministic post-IF score booster.

Each rule encodes an unambiguous attack pattern that the IsolationForest
should not be asked to learn from baseline data alone. Boosts are
computed independently per rule and combined via ``max`` so the highest-
confidence rule wins. The booster takes a final ``max`` against the IF's
normalised score in the caller so a strong IF signal is never downgraded.

The off-hours-admin rule is per-user-anchored: it fires only when the
user holds a tier-0 privileged role *and* their per-user time-only
model rates the sign-in's hour signature in the user's training-
distribution top decile (cold-start admins fall back to a hard
22:00-06:00 night band). This catches the Sprint 3 calibration miss
where pooled-tenant hour distributions did not isolate a single
admin's late-night activity.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from cstack_ml_anomaly.per_user import PerUserBundle

# Travel speed at which a row is treated as physically impossible regardless
# of any model output. Commercial flights cap around 900 km/h; we leave
# overhead so legitimate-but-fast travel does not trip the rule.
TRAVEL_SPEED_FLOOR_KMH = 1500.0

RULE_TRAVEL_SPEED_FLOOR = 0.95
RULE_NEW_COUNTRY_AND_ASN_FLOOR = 0.85
RULE_FAILURE_AND_NEW_ASN_FLOOR = 0.85
RULE_MFA_BYPASS_LEGACY_FLOOR = 0.80
RULE_OFF_HOURS_ADMIN_FLOOR = 0.85

# Cold-start admin fallback band (UTC). Used when a privileged user has no
# per-user time model (cold-start path); aligns with the spec's "22:00 to
# 06:00 user-local" — we use UTC because the existing time features do.
NIGHT_HOURS_UTC: frozenset[int] = frozenset({22, 23, 0, 1, 2, 3, 4, 5})

# Time-only feature columns the off-hours rule scores against.
TIME_FEATURE_COLUMNS: tuple[str, ...] = (
    "day_of_week",
    "hour_of_day_cos",
    "hour_of_day_sin",
    "is_business_hours_local",
)


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


def _utc_hour_from_row(row: Any) -> int | None:
    """Recover UTC hour from cyclical encoding when present.

    The features carry hour-of-day as ``hour_of_day_sin / cos`` for the
    IF, not as a raw integer. The cold-start fallback needs to compare
    against a discrete night band, so we recover the integer hour by
    inverting the sin/cos pair.
    """
    sin = getattr(row, "hour_of_day_sin", None)
    cos = getattr(row, "hour_of_day_cos", None)
    if sin is None or cos is None:
        return None
    angle = math.atan2(float(sin), float(cos))
    if angle < 0:
        angle += 2 * math.pi
    return round(angle * 24 / (2 * math.pi)) % 24


def _off_hours_admin_boost(
    user_id: str,
    row: Any,
    feature_row_df: pd.DataFrame,
    bundle: PerUserBundle | None,
    privileged_user_ids: frozenset[str],
) -> float:
    """Off-hours-admin rule. Returns 0.0 if the rule does not fire.

    Fires when the user is in ``privileged_user_ids`` AND either:
    - The user has a per-user time model and the row's negated time-only
      score is at or above the user's training-distribution p90, or
    - The user has no per-user model (cold-start) and the UTC hour falls
      in the 22:00-06:00 night band.
    """
    if user_id not in privileged_user_ids:
        return 0.0
    if bundle is not None and user_id in bundle.time_pipelines:
        time_pipe = bundle.time_pipelines[user_id]
        p90 = bundle.time_score_p90.get(user_id)
        if p90 is None:
            return 0.0
        time_features = feature_row_df[list(TIME_FEATURE_COLUMNS)]
        # decision_function: higher = more normal. Negate so higher = more
        # anomalous, matching the percentile semantics used at training time.
        anomaly_score = -float(time_pipe.decision_function(time_features)[0])
        if anomaly_score >= p90:
            return RULE_OFF_HOURS_ADMIN_FLOOR
        return 0.0
    # Cold-start admin: hard time boundary fallback.
    hour = _utc_hour_from_row(row)
    if hour is not None and hour in NIGHT_HOURS_UTC:
        return RULE_OFF_HOURS_ADMIN_FLOOR
    return 0.0


def rule_score_boosts(
    feature_df: pd.DataFrame,
    user_ids: list[str] | None = None,
    bundle: PerUserBundle | None = None,
    privileged_user_ids: frozenset[str] = frozenset(),
) -> list[float]:
    """Compute per-row score floors across the rule set.

    ``user_ids``, ``bundle`` and ``privileged_user_ids`` together drive
    the off-hours-admin rule. When ``user_ids`` is None or
    ``privileged_user_ids`` is empty the rule is skipped and only the
    Sprint 3 hybrid rules apply; this is the layer-attribution mode used
    by the Phase 4 sweep.
    """
    boosts: list[float] = []
    rows = list(feature_df.itertuples(index=False))
    if user_ids is not None and len(user_ids) != len(rows):
        raise ValueError(
            f"feature_df rows ({len(rows)}) must match user_ids length ({len(user_ids)})"
        )
    for i, row in enumerate(rows):
        score = _hybrid_rule_boost(row)
        if user_ids is not None and privileged_user_ids:
            admin_boost = _off_hours_admin_boost(
                user_ids[i],
                row,
                feature_df.iloc[[i]],
                bundle,
                privileged_user_ids,
            )
            if admin_boost > score:
                score = admin_boost
        boosts.append(score)
    return boosts
