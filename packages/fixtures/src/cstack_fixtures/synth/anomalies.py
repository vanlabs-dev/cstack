"""Scripted anomaly injection helpers. Each function returns the events it
inserts plus a label string the scenario writer captures into the
ground-truth file."""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from cstack_fixtures.synth.signins import (
    APPS,
    CITIES,
    SyntheticUserProfile,
    _device_payload,
    _ip_for_asn,
    _location_for,
    _to_iso,
)


def _injected(event: dict[str, Any], label: str) -> dict[str, Any]:
    event["_anomaly_label"] = label
    return event


def inject_impossible_travel(
    profile: SyntheticUserProfile, rng: random.Random, when: datetime
) -> list[dict[str, Any]]:
    """Two sign-ins about 30 minutes apart from geographically distant cities."""
    home_index = next(
        (
            i
            for i, c in enumerate(CITIES)
            if c[0] == profile.home_city and c[1] == profile.home_country
        ),
        0,
    )
    far_index = (home_index + 7) % len(CITIES)
    when = when.replace(tzinfo=UTC)
    out: list[dict[str, Any]] = []
    for offset_minutes, city_index, asn_index in (
        (0, home_index, profile.home_asn_index),
        (30, far_index, 4),
    ):
        ts = when + timedelta(minutes=offset_minutes)
        app_id, app_name = APPS[0]
        out.append(
            _injected(
                {
                    "id": str(uuid.UUID(int=rng.getrandbits(128))),
                    "createdDateTime": _to_iso(ts),
                    "userId": profile.user_id,
                    "userPrincipalName": profile.upn,
                    "appId": app_id,
                    "appDisplayName": app_name,
                    "clientAppUsed": "Browser",
                    "ipAddress": _ip_for_asn(rng, asn_index),
                    "isInteractive": True,
                    "authenticationRequirement": "multiFactorAuthentication",
                    "authenticationMethodsUsed": ["password", profile.mfa_method],
                    "deviceDetail": _device_payload(profile, rng),
                    "location": _location_for(city_index),
                    "status": {"errorCode": 0, "failureReason": "Other"},
                    "riskLevelDuringSignIn": "high",
                    "riskState": "atRisk",
                    "conditionalAccessStatus": "success",
                    "_synthAsnIndex": asn_index,
                },
                "impossible_travel",
            )
        )
    return out


def inject_new_asn(
    profile: SyntheticUserProfile, rng: random.Random, when: datetime
) -> dict[str, Any]:
    """Single sign-in from a never-seen ASN."""
    when = when.replace(tzinfo=UTC)
    novel_asn = 4  # AWS; unlikely for a typical office user
    app_id, app_name = APPS[0]
    return _injected(
        {
            "id": str(uuid.UUID(int=rng.getrandbits(128))),
            "createdDateTime": _to_iso(when),
            "userId": profile.user_id,
            "userPrincipalName": profile.upn,
            "appId": app_id,
            "appDisplayName": app_name,
            "clientAppUsed": "Browser",
            "ipAddress": _ip_for_asn(rng, novel_asn),
            "isInteractive": True,
            "authenticationRequirement": "multiFactorAuthentication",
            "authenticationMethodsUsed": ["password", profile.mfa_method],
            "deviceDetail": _device_payload(profile, rng),
            "location": _location_for(11),  # San Francisco
            "status": {"errorCode": 0, "failureReason": "Other"},
            "riskLevelDuringSignIn": "medium",
            "riskState": "atRisk",
            "conditionalAccessStatus": "success",
            "_synthAsnIndex": novel_asn,
        },
        "new_asn",
    )


def inject_off_hours_admin_action(
    profile: SyntheticUserProfile, rng: random.Random, when: datetime
) -> dict[str, Any]:
    """Interactive sign-in to the Azure Portal at 3am local time."""
    home_index = next(
        (
            i
            for i, c in enumerate(CITIES)
            if c[0] == profile.home_city and c[1] == profile.home_country
        ),
        0,
    )
    local = when.replace(hour=3, minute=12, second=0, microsecond=0)
    utc_dt = (local - timedelta(hours=profile.timezone_offset_hours)).replace(tzinfo=UTC)
    return _injected(
        {
            "id": str(uuid.UUID(int=rng.getrandbits(128))),
            "createdDateTime": _to_iso(utc_dt),
            "userId": profile.user_id,
            "userPrincipalName": profile.upn,
            "appId": "c44b4083-3bb0-49c1-b47d-974e53cbdf3c",
            "appDisplayName": "Azure Portal",
            "clientAppUsed": "Browser",
            "ipAddress": _ip_for_asn(rng, profile.home_asn_index),
            "isInteractive": True,
            "authenticationRequirement": "multiFactorAuthentication",
            "authenticationMethodsUsed": ["password", profile.mfa_method],
            "deviceDetail": _device_payload(profile, rng),
            "location": _location_for(home_index),
            "status": {"errorCode": 0, "failureReason": "Other"},
            "riskLevelDuringSignIn": "low",
            "riskState": "none",
            "conditionalAccessStatus": "success",
            "_synthAsnIndex": profile.home_asn_index,
        },
        "off_hours_admin_action",
    )


def inject_mfa_bypass(
    profile: SyntheticUserProfile, rng: random.Random, when: datetime
) -> dict[str, Any]:
    """A sign-in that satisfies only single-factor for a normally-MFA user."""
    home_index = next(
        (
            i
            for i, c in enumerate(CITIES)
            if c[0] == profile.home_city and c[1] == profile.home_country
        ),
        0,
    )
    when = when.replace(tzinfo=UTC)
    app_id, app_name = APPS[1]  # Exchange Online
    return _injected(
        {
            "id": str(uuid.UUID(int=rng.getrandbits(128))),
            "createdDateTime": _to_iso(when),
            "userId": profile.user_id,
            "userPrincipalName": profile.upn,
            "appId": app_id,
            "appDisplayName": app_name,
            "clientAppUsed": "Other",
            "ipAddress": _ip_for_asn(rng, profile.home_asn_index),
            "isInteractive": False,
            "authenticationRequirement": "singleFactorAuthentication",
            "authenticationMethodsUsed": ["password"],
            "deviceDetail": _device_payload(profile, rng),
            "location": _location_for(home_index),
            "status": {"errorCode": 0, "failureReason": "Other"},
            "riskLevelDuringSignIn": "medium",
            "riskState": "atRisk",
            "conditionalAccessStatus": "success",
            "_synthAsnIndex": profile.home_asn_index,
        },
        "mfa_bypass",
    )


def inject_credential_stuffing_burst(
    profile: SyntheticUserProfile, rng: random.Random, when: datetime, count: int = 22
) -> list[dict[str, Any]]:
    """count failed sign-ins in 5 minutes from rotating IPs."""
    when = when.replace(tzinfo=UTC)
    out: list[dict[str, Any]] = []
    for i in range(count):
        ts = when + timedelta(seconds=int(300 * i / max(count - 1, 1)))
        asn_index = rng.choice((3, 4, 5))
        out.append(
            _injected(
                {
                    "id": str(uuid.UUID(int=rng.getrandbits(128))),
                    "createdDateTime": _to_iso(ts),
                    "userId": profile.user_id,
                    "userPrincipalName": profile.upn,
                    "appId": APPS[0][0],
                    "appDisplayName": APPS[0][1],
                    "clientAppUsed": "Browser",
                    "ipAddress": _ip_for_asn(rng, asn_index),
                    "isInteractive": True,
                    "authenticationRequirement": "singleFactorAuthentication",
                    "authenticationMethodsUsed": ["password"],
                    "deviceDetail": _device_payload(profile, rng),
                    "location": _location_for(rng.randint(10, len(CITIES) - 1)),
                    "status": {
                        "errorCode": 50053,
                        "failureReason": "InvalidUserNameOrPassword",
                    },
                    "riskLevelDuringSignIn": "high",
                    "riskState": "atRisk",
                    "conditionalAccessStatus": "failure",
                    "_synthAsnIndex": asn_index,
                },
                "credential_stuffing_burst",
            )
        )
    return out
