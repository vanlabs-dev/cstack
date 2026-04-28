"""Baseline sign-in event synthesizer.

The output is a list of dicts shaped like Graph signIn responses. Tests
parse them through the SignIn pydantic model so any drift between the
synthesizer and the schema is caught at fixture-load time.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

# Common ASNs we expect to see in a normal NZ-centric tenant. Each entry is
# (asn, name, hint_country); ``home_asn`` for a profile usually matches one
# of the ISP entries while occasional mobile/cloud entries appear when a
# user roams.
COMMON_ASNS: tuple[tuple[int, str, str], ...] = (
    (4648, "Spark NZ ISP", "NZ"),
    (9500, "Vodafone NZ ISP", "NZ"),
    (45177, "2degrees NZ Mobile", "NZ"),
    (8075, "Microsoft Azure", "GLOBAL"),
    (16509, "AWS", "GLOBAL"),
    (15169, "Google Cloud", "GLOBAL"),
)

# A small geographic catalogue keeps the synthesizer dependency-free. Each
# entry is (city, country_or_region, latitude, longitude, asn_index).
# Cities are biased NZ-first to match typical SMB tenant geography.
CITIES: tuple[tuple[str, str, float, float, int], ...] = (
    ("Auckland", "NZ", -36.85, 174.76, 0),
    ("Wellington", "NZ", -41.29, 174.78, 0),
    ("Christchurch", "NZ", -43.53, 172.64, 1),
    ("Hamilton", "NZ", -37.78, 175.28, 0),
    ("Tauranga", "NZ", -37.69, 176.17, 1),
    ("Dunedin", "NZ", -45.88, 170.50, 0),
    ("Sydney", "AU", -33.87, 151.21, 4),
    ("Melbourne", "AU", -37.81, 144.96, 4),
    ("Brisbane", "AU", -27.47, 153.03, 4),
    ("Perth", "AU", -31.95, 115.86, 4),
    ("Singapore", "SG", 1.35, 103.82, 5),
    ("San Francisco", "US", 37.77, -122.42, 5),
    ("New York", "US", 40.71, -74.00, 4),
    ("Seattle", "US", 47.61, -122.33, 3),
    ("Dallas", "US", 32.78, -96.80, 4),
    ("London", "GB", 51.51, -0.13, 5),
)

DEVICE_OPERATING_SYSTEMS: tuple[str, ...] = (
    "Windows 11",
    "Windows 10",
    "macOS 14",
    "iOS 17",
    "Android 14",
)

DEVICE_BROWSERS: tuple[str, ...] = (
    "Edge 124",
    "Chrome 124",
    "Safari 17",
    "Firefox 125",
)

APPS: tuple[tuple[str, str], ...] = (
    ("00000003-0000-0ff1-ce00-000000000000", "SharePoint Online"),
    ("00000002-0000-0ff1-ce00-000000000000", "Exchange Online"),
    ("cc15fd57-2c6c-4117-a88c-83b1d56b4bbe", "Microsoft Teams"),
    ("c44b4083-3bb0-49c1-b47d-974e53cbdf3c", "Azure Portal"),
    ("14d82eec-204b-4c2f-b7e8-296a70dab67e", "Microsoft Graph PowerShell"),
)


@dataclass(frozen=True)
class SyntheticUserProfile:
    user_id: str
    upn: str
    home_country: str
    home_city: str
    home_asn_index: int
    work_hours_start_local: int
    work_hours_end_local: int
    timezone_offset_hours: int
    device_os: str
    device_browser: str
    mfa_method: str
    signin_frequency_per_day: float
    weekend_factor: float
    mobile_use_pct: float


def _ip_for_asn(rng: random.Random, asn_index: int) -> str:
    # Deterministic-ish IP per ASN: ASNs map to /16 ranges so the synthesised
    # IPs cluster the way real ISPs do.
    base_octets = {
        0: (203, 0),  # NZ ISP A (Spark)
        1: (122, 56),  # NZ ISP B (Vodafone)
        2: (110, 175),  # NZ Mobile
        3: (52, 96),  # Azure
        4: (54, 240),  # AWS
        5: (35, 240),  # Google
    }
    a, b = base_octets.get(asn_index, (203, 0))
    c = rng.randint(0, 255)
    d = rng.randint(1, 254)
    return f"{a}.{b}.{c}.{d}"


def _device_payload(profile: SyntheticUserProfile, rng: random.Random) -> dict[str, Any]:
    is_secondary = rng.random() < 0.05
    return {
        "deviceId": f"dev-{profile.user_id}-{'alt' if is_secondary else 'main'}",
        "displayName": f"{profile.user_id}-laptop"
        if not is_secondary
        else f"{profile.user_id}-mobile",
        "operatingSystem": "iOS 17"
        if is_secondary and "iOS" not in profile.device_os
        else profile.device_os,
        "browser": profile.device_browser,
        "isCompliant": True,
        "isManaged": True,
        "trustType": "AzureAdJoined",
    }


def _location_for(city_index: int) -> dict[str, Any]:
    city, country, lat, lon, _asn = CITIES[city_index]
    return {
        "city": city,
        "state": city,
        "countryOrRegion": country,
        "geoCoordinates": {"latitude": lat, "longitude": lon},
    }


def _city_index_for_profile(profile: SyntheticUserProfile) -> int:
    for i, (city, country, *_rest) in enumerate(CITIES):
        if city == profile.home_city and country == profile.home_country:
            return i
    return 0


def _select_app(rng: random.Random) -> tuple[str, str]:
    return rng.choice(APPS)


def _to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _local_to_utc(local: datetime, offset_hours: int) -> datetime:
    return (local - timedelta(hours=offset_hours)).replace(tzinfo=UTC)


def _draw_signin_count_for_day(
    rng: random.Random, profile: SyntheticUserProfile, is_weekend: bool
) -> int:
    mean = profile.signin_frequency_per_day
    if is_weekend:
        mean *= profile.weekend_factor
    # Poisson via inverse-CDF approximation; using random.random() tied to rng
    # for reproducibility.
    # numpy is available but keeping this stdlib makes the synth module
    # testable with no heavy deps.
    L = math.exp(-mean)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def synthesize_baseline_signins(
    profile: SyntheticUserProfile,
    days: int,
    start: datetime,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Generate one user's baseline sign-in stream over ``days`` days."""
    home_city_index = _city_index_for_profile(profile)
    events: list[dict[str, Any]] = []
    cur_day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    for day_offset in range(days):
        local_day = cur_day + timedelta(days=day_offset)
        weekday = local_day.weekday()
        is_weekend = weekday >= 5
        n = _draw_signin_count_for_day(rng, profile, is_weekend)
        for _ in range(n):
            # Most sign-ins land in business hours; ~3% off-hours.
            if rng.random() < 0.03:
                local_hour = rng.choice((1, 2, 3, 22, 23))
            else:
                local_hour = rng.randint(
                    profile.work_hours_start_local, profile.work_hours_end_local
                )
            local_minute = rng.randint(0, 59)
            local_second = rng.randint(0, 59)
            local_dt = local_day.replace(hour=local_hour, minute=local_minute, second=local_second)
            utc_dt = _local_to_utc(local_dt, profile.timezone_offset_hours)

            # Location: 99% home; 1% other.
            city_index = rng.randint(0, len(CITIES) - 1) if rng.random() < 0.01 else home_city_index
            asn_index = profile.home_asn_index
            if rng.random() < profile.mobile_use_pct:
                asn_index = 2  # NZ Mobile
            ip = _ip_for_asn(rng, asn_index)
            app_id, app_name = _select_app(rng)

            is_failure = rng.random() < 0.02
            error_code = 50053 if is_failure else 0
            failure_reason = "InvalidUserNameOrPassword" if is_failure else "Other"

            mfa_satisfied = profile.mfa_method != "none"

            event_id = str(uuid.UUID(int=rng.getrandbits(128)))
            events.append(
                {
                    "id": event_id,
                    "createdDateTime": _to_iso(utc_dt),
                    "userId": profile.user_id,
                    "userPrincipalName": profile.upn,
                    "appId": app_id,
                    "appDisplayName": app_name,
                    "clientAppUsed": "Browser",
                    "ipAddress": ip,
                    "isInteractive": True,
                    "authenticationRequirement": (
                        "multiFactorAuthentication"
                        if mfa_satisfied
                        else "singleFactorAuthentication"
                    ),
                    "authenticationMethodsUsed": (
                        ["password", profile.mfa_method] if mfa_satisfied else ["password"]
                    ),
                    "deviceDetail": _device_payload(profile, rng),
                    "location": _location_for(city_index),
                    "status": {"errorCode": error_code, "failureReason": failure_reason},
                    "riskLevelDuringSignIn": "none",
                    "riskState": "none",
                    "conditionalAccessStatus": "success" if not is_failure else "failure",
                    # Retain ASN index in extras so the anomaly injectors and
                    # the feature pipeline can reason about it without an IP
                    # lookup table during fixture work.
                    "_synthAsnIndex": asn_index,
                }
            )
    events.sort(key=lambda e: e["createdDateTime"])
    return events
