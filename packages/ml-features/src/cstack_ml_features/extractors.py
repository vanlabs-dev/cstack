"""Per-feature extractors. Each is a pure function over (SignIn, UserHistory).

Functions return primitive numeric types so they slot directly into a numpy
matrix for IsolationForest. Tests cover each function with hand-crafted
minimal inputs.
"""

from __future__ import annotations

import math
from collections import Counter

from cstack_schemas import SignIn

from cstack_ml_features.asn_stub import lookup_asn
from cstack_ml_features.history import UserHistory

_LEGACY_CLIENT_APPS = frozenset({"Other", "ExchangeActiveSync", "AutoDiscover"})

_RISK_NUMERIC: dict[str, int] = {"none": 0, "low": 1, "medium": 2, "high": 3}

_FAIL_REASON_NUMERIC: dict[str, int] = {
    "InvalidUserNameOrPassword": 1,
    "MfaRequired": 2,
    "BlockedByConditionalAccess": 3,
    "ConditionalAccess": 3,
}

_DEFAULT_BUSINESS_START = 8
_DEFAULT_BUSINESS_END = 18


def hour_of_day_sin(signin: SignIn) -> float:
    h = signin.created_date_time.hour
    return math.sin(2 * math.pi * h / 24)


def hour_of_day_cos(signin: SignIn) -> float:
    h = signin.created_date_time.hour
    return math.cos(2 * math.pi * h / 24)


def day_of_week(signin: SignIn) -> int:
    return signin.created_date_time.weekday()


def is_weekend(signin: SignIn) -> int:
    return 1 if signin.created_date_time.weekday() >= 5 else 0


def is_business_hours_local(
    signin: SignIn,
    start: int = _DEFAULT_BUSINESS_START,
    end: int = _DEFAULT_BUSINESS_END,
) -> int:
    h = signin.created_date_time.hour
    return 1 if start <= h <= end else 0


def hours_since_last_signin(signin: SignIn, history: UserHistory) -> float:
    if history.last_signin_at is None:
        return 720.0
    delta = signin.created_date_time - history.last_signin_at
    seconds = max(delta.total_seconds(), 0.0)
    return min(720.0, seconds / 3600.0)


def country_entropy_30d(history: UserHistory) -> float:
    if not history.countries_30d:
        return 0.0
    counts = Counter(history.countries_30d)
    total = sum(counts.values())
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)


def asn_entropy_30d(history: UserHistory) -> float:
    if not history.asns_30d:
        return 0.0
    counts = Counter(history.asns_30d)
    total = sum(counts.values())
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)


def is_new_country_for_user(signin: SignIn, history: UserHistory) -> int:
    loc = signin.location
    if loc is None or not loc.country_or_region:
        return 0
    return 0 if loc.country_or_region in history.countries_30d else 1


def is_new_asn_for_user(signin: SignIn, history: UserHistory) -> int:
    asn = lookup_asn(signin.ip_address)
    if asn is None:
        return 0
    return 0 if asn in history.asns_30d else 1


def distance_from_last_signin_km(signin: SignIn, history: UserHistory) -> float:
    loc = signin.location
    coords = loc.geo_coordinates if loc is not None else None
    if (
        coords is None
        or coords.latitude is None
        or coords.longitude is None
        or history.last_latitude is None
        or history.last_longitude is None
    ):
        return 0.0
    lat1 = math.radians(history.last_latitude)
    lat2 = math.radians(coords.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(coords.longitude - history.last_longitude)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def travel_speed_kmh(signin: SignIn, history: UserHistory) -> float:
    """Effective km/h between this and the previous sign-in.

    Interaction feature designed to separate legitimate travel (under
    1000 km/h, typical of commercial flights) from impossible travel
    (thousands of km/h, only achievable by session-token theft or VPN
    bouncing). Returns 0 when either coordinate or the prior timestamp
    is missing so absence of data does not look anomalous.
    """
    if history.last_signin_at is None:
        return 0.0
    distance = distance_from_last_signin_km(signin, history)
    if distance <= 0.0:
        return 0.0
    delta = signin.created_date_time - history.last_signin_at
    hours = max(delta.total_seconds() / 3600.0, 1.0 / 60.0)  # floor at 1 minute
    return min(distance / hours, 100_000.0)


def is_new_device_for_user(signin: SignIn, history: UserHistory) -> int:
    device = signin.device_detail
    if device is None or not device.device_id:
        return 0
    return 0 if device.device_id in history.devices_seen else 1


def is_new_browser_for_user(signin: SignIn, history: UserHistory) -> int:
    device = signin.device_detail
    if device is None or not device.browser:
        return 0
    return 0 if device.browser in history.browsers_seen else 1


def is_new_os_for_user(signin: SignIn, history: UserHistory) -> int:
    device = signin.device_detail
    if device is None or not device.operating_system:
        return 0
    return 0 if device.operating_system in history.os_seen else 1


def mfa_satisfied(signin: SignIn) -> int:
    return 1 if signin.authentication_requirement == "multiFactorAuthentication" else 0


def is_legacy_auth(signin: SignIn) -> int:
    if signin.client_app_used in _LEGACY_CLIENT_APPS:
        return 1
    if (
        signin.is_interactive is False
        and signin.authentication_requirement == "singleFactorAuthentication"
    ):
        return 1
    return 0


def risk_level_during_signin_numeric(signin: SignIn) -> int:
    return _RISK_NUMERIC.get(signin.risk_level_during_sign_in or "none", 0)


def is_failure(signin: SignIn) -> int:
    status = signin.status
    if status is None or status.error_code is None:
        return 0
    return 1 if status.error_code != 0 else 0


def failure_reason_category(signin: SignIn) -> int:
    status = signin.status
    if status is None or not status.failure_reason:
        return 0
    return _FAIL_REASON_NUMERIC.get(status.failure_reason, 4)
