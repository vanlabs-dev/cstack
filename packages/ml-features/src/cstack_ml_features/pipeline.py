"""Feature pipeline. The FeatureSet model defines the contract; FEATURE_COLUMNS
is the canonical alphabetical column order the model trains on.

Changing FEATURE_COLUMNS or the FeatureSet schema invalidates trained models;
bump model versions when this file changes.
"""

from __future__ import annotations

import pandas as pd
from cstack_schemas import SignIn
from pydantic import BaseModel, ConfigDict

from cstack_ml_features import extractors
from cstack_ml_features.history import UserHistory

FEATURE_COLUMNS: tuple[str, ...] = (
    "asn_entropy_30d",
    "country_entropy_30d",
    "day_of_week",
    "distance_from_last_signin_km",
    "failure_reason_category",
    "hour_of_day_cos",
    "hour_of_day_sin",
    "hours_since_last_signin",
    "is_business_hours_local",
    "is_failure",
    "is_legacy_auth",
    "is_new_asn_for_user",
    "is_new_browser_for_user",
    "is_new_country_for_user",
    "is_new_device_for_user",
    "is_new_os_for_user",
    "is_weekend",
    "mfa_satisfied",
    "risk_level_during_signin_numeric",
    "travel_speed_kmh",
)


class FeatureSet(BaseModel):
    """Typed view of a single sign-in's feature row."""

    model_config = ConfigDict(frozen=True)

    asn_entropy_30d: float
    country_entropy_30d: float
    day_of_week: int
    distance_from_last_signin_km: float
    failure_reason_category: int
    hour_of_day_cos: float
    hour_of_day_sin: float
    hours_since_last_signin: float
    is_business_hours_local: int
    is_failure: int
    is_legacy_auth: int
    is_new_asn_for_user: int
    is_new_browser_for_user: int
    is_new_country_for_user: int
    is_new_device_for_user: int
    is_new_os_for_user: int
    is_weekend: int
    mfa_satisfied: int
    risk_level_during_signin_numeric: int
    travel_speed_kmh: float


def extract_features(signin: SignIn, history: UserHistory) -> FeatureSet:
    """Compute every feature for a single sign-in given user history."""
    return FeatureSet(
        asn_entropy_30d=extractors.asn_entropy_30d(history),
        country_entropy_30d=extractors.country_entropy_30d(history),
        day_of_week=extractors.day_of_week(signin),
        distance_from_last_signin_km=extractors.distance_from_last_signin_km(signin, history),
        failure_reason_category=extractors.failure_reason_category(signin),
        hour_of_day_cos=extractors.hour_of_day_cos(signin),
        hour_of_day_sin=extractors.hour_of_day_sin(signin),
        hours_since_last_signin=extractors.hours_since_last_signin(signin, history),
        is_business_hours_local=extractors.is_business_hours_local(signin),
        is_failure=extractors.is_failure(signin),
        is_legacy_auth=extractors.is_legacy_auth(signin),
        is_new_asn_for_user=extractors.is_new_asn_for_user(signin, history),
        is_new_browser_for_user=extractors.is_new_browser_for_user(signin, history),
        is_new_country_for_user=extractors.is_new_country_for_user(signin, history),
        is_new_device_for_user=extractors.is_new_device_for_user(signin, history),
        is_new_os_for_user=extractors.is_new_os_for_user(signin, history),
        is_weekend=extractors.is_weekend(signin),
        mfa_satisfied=extractors.mfa_satisfied(signin),
        risk_level_during_signin_numeric=extractors.risk_level_during_signin_numeric(signin),
        travel_speed_kmh=extractors.travel_speed_kmh(signin, history),
    )


def extract_features_batch(
    items: list[tuple[SignIn, UserHistory]],
) -> pd.DataFrame:
    """Vectorised batch extraction. Returns DataFrame in FEATURE_COLUMNS order."""
    rows = [extract_features(s, h).model_dump() for s, h in items]
    return pd.DataFrame(rows, columns=list(FEATURE_COLUMNS))
