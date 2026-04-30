from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from cstack_schemas import SignIn

from cstack_ml_features.asn import lookup_asn


@dataclass(frozen=True)
class UserHistory:
    """Rolling view of a user's sign-in history used for feature extraction.

    All fields are computed from sign-ins strictly before ``as_of`` so the
    feature pipeline never leaks the current event into its own history.

    ``asns_30d`` carries integer AS numbers as of Sprint 6.7; the prior
    string form ("AS4648") is gone now that the lookup module uses
    MaxMind GeoLite2 (which yields ints) with a fixture fallback that
    also yields ints.
    """

    countries_30d: tuple[str, ...]
    asns_30d: tuple[int, ...]
    devices_seen: frozenset[str]
    browsers_seen: frozenset[str]
    os_seen: frozenset[str]
    last_signin_at: datetime | None
    last_latitude: float | None
    last_longitude: float | None


_EMPTY = UserHistory(
    countries_30d=(),
    asns_30d=(),
    devices_seen=frozenset(),
    browsers_seen=frozenset(),
    os_seen=frozenset(),
    last_signin_at=None,
    last_latitude=None,
    last_longitude=None,
)


def empty_history() -> UserHistory:
    """Return the shared empty UserHistory used for cold-start users."""
    return _EMPTY


def build_history_from_signins(
    signins: list[SignIn], as_of: datetime, window_days: int = 30
) -> UserHistory:
    """Compute the rolling history view from a chronological sign-in list."""
    cutoff = as_of - timedelta(days=window_days)
    countries: list[str] = []
    asns: list[int] = []
    devices: set[str] = set()
    browsers: set[str] = set()
    os_set: set[str] = set()
    last_at: datetime | None = None
    last_lat: float | None = None
    last_lon: float | None = None
    for s in sorted(signins, key=lambda x: x.created_date_time):
        if s.created_date_time >= as_of:
            break
        if s.created_date_time >= cutoff:
            loc = s.location
            if loc is not None and loc.country_or_region:
                countries.append(loc.country_or_region)
            asn = lookup_asn(s.ip_address)
            if asn.number is not None:
                asns.append(asn.number)
        device = s.device_detail
        if device is not None:
            if device.device_id:
                devices.add(device.device_id)
            if device.browser:
                browsers.add(device.browser)
            if device.operating_system:
                os_set.add(device.operating_system)
        last_at = s.created_date_time
        loc2 = s.location
        if loc2 is not None and loc2.geo_coordinates is not None:
            if loc2.geo_coordinates.latitude is not None:
                last_lat = loc2.geo_coordinates.latitude
            if loc2.geo_coordinates.longitude is not None:
                last_lon = loc2.geo_coordinates.longitude
    return UserHistory(
        countries_30d=tuple(countries),
        asns_30d=tuple(asns),
        devices_seen=frozenset(devices),
        browsers_seen=frozenset(browsers),
        os_seen=frozenset(os_set),
        last_signin_at=last_at,
        last_latitude=last_lat,
        last_longitude=last_lon,
    )
