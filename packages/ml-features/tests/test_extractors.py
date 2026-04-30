from datetime import UTC, datetime

from cstack_ml_features import (
    UserHistory,
    build_history_from_signins,
    empty_history,
    extract_features,
    extract_features_batch,
    lookup_asn,
)
from cstack_ml_features.extractors import (
    asn_entropy_30d,
    country_entropy_30d,
    distance_from_last_signin_km,
    hour_of_day_sin,
    hours_since_last_signin,
    is_business_hours_local,
    is_legacy_auth,
    is_new_asn_for_user,
    is_new_country_for_user,
    is_weekend,
    risk_level_during_signin_numeric,
)
from cstack_schemas import SignIn


def _signin(
    sid: str = "s1",
    when: datetime | None = None,
    country: str = "NZ",
    city: str = "Auckland",
    lat: float = -36.85,
    lon: float = 174.76,
    ip: str = "203.0.113.10",
    is_interactive: bool = True,
    auth_req: str = "multiFactorAuthentication",
    risk: str = "none",
    error_code: int | None = 0,
    failure_reason: str | None = "Other",
) -> SignIn:
    payload = {
        "id": sid,
        "createdDateTime": (when or datetime(2026, 4, 28, 10, 30, tzinfo=UTC)).isoformat(),
        "userId": "u1",
        "userPrincipalName": "u1@example.com",
        "ipAddress": ip,
        "isInteractive": is_interactive,
        "authenticationRequirement": auth_req,
        "riskLevelDuringSignIn": risk,
        "deviceDetail": {
            "deviceId": "dev-1",
            "operatingSystem": "Windows 11",
            "browser": "Edge 124",
        },
        "location": {
            "city": city,
            "countryOrRegion": country,
            "geoCoordinates": {"latitude": lat, "longitude": lon},
        },
        "status": {"errorCode": error_code, "failureReason": failure_reason},
    }
    return SignIn.model_validate(payload)


def test_lookup_asn_known_prefix() -> None:
    """Sprint 1's prefix table is the fixture-fallback path; without a
    real GeoLite2 database the synthesizer's TEST-NET ranges still
    resolve deterministically."""
    result = lookup_asn("203.0.113.10")
    assert result.number == 4648
    assert result.organization is None  # fallback path doesn't supply org


def test_lookup_asn_handles_none() -> None:
    result = lookup_asn(None)
    assert result.number is None
    assert result.organization is None


def test_lookup_asn_returns_int_for_unknown_prefix() -> None:
    """An IP outside the synthesizer's prefix table falls through to the
    SHA-256 hash, returning a stable integer."""
    a = lookup_asn("198.51.100.42")
    b = lookup_asn("198.51.100.42")
    assert a.number == b.number
    assert isinstance(a.number, int)


def test_hour_of_day_sin_at_noon() -> None:
    s = _signin(when=datetime(2026, 4, 28, 12, 0, tzinfo=UTC))
    assert abs(hour_of_day_sin(s)) < 1e-9


def test_is_weekend_saturday() -> None:
    s = _signin(when=datetime(2026, 5, 2, 10, 0, tzinfo=UTC))  # Saturday
    assert is_weekend(s) == 1


def test_is_business_hours_local() -> None:
    in_hours = _signin(when=datetime(2026, 4, 28, 9, 0, tzinfo=UTC))
    out_hours = _signin(when=datetime(2026, 4, 28, 23, 0, tzinfo=UTC))
    assert is_business_hours_local(in_hours) == 1
    assert is_business_hours_local(out_hours) == 0


def test_hours_since_last_signin_clamped_when_history_empty() -> None:
    s = _signin()
    assert hours_since_last_signin(s, empty_history()) == 720.0


def test_country_entropy_zero_for_uniform_history() -> None:
    h = UserHistory(
        countries_30d=("NZ", "NZ", "NZ"),
        asns_30d=(),
        devices_seen=frozenset(),
        browsers_seen=frozenset(),
        os_seen=frozenset(),
        last_signin_at=None,
        last_latitude=None,
        last_longitude=None,
    )
    assert country_entropy_30d(h) == 0.0


def test_asn_entropy_increases_with_diversity() -> None:
    h_uniform = UserHistory(
        countries_30d=(),
        asns_30d=(1, 1, 1),
        devices_seen=frozenset(),
        browsers_seen=frozenset(),
        os_seen=frozenset(),
        last_signin_at=None,
        last_latitude=None,
        last_longitude=None,
    )
    h_diverse = UserHistory(
        countries_30d=(),
        asns_30d=(1, 2, 3),
        devices_seen=frozenset(),
        browsers_seen=frozenset(),
        os_seen=frozenset(),
        last_signin_at=None,
        last_latitude=None,
        last_longitude=None,
    )
    assert asn_entropy_30d(h_uniform) == 0.0
    assert asn_entropy_30d(h_diverse) > 1.0


def test_is_new_country_and_asn_flags() -> None:
    h = UserHistory(
        countries_30d=("NZ",),
        asns_30d=(4648,),
        devices_seen=frozenset(),
        browsers_seen=frozenset(),
        os_seen=frozenset(),
        last_signin_at=None,
        last_latitude=None,
        last_longitude=None,
    )
    same = _signin(country="NZ", ip="203.0.113.10")
    new_country = _signin(country="US", ip="203.0.113.10")
    new_asn = _signin(country="NZ", ip="54.240.1.1")
    assert is_new_country_for_user(same, h) == 0
    assert is_new_country_for_user(new_country, h) == 1
    assert is_new_asn_for_user(new_asn, h) == 1


def test_distance_zero_when_history_missing() -> None:
    s = _signin()
    assert distance_from_last_signin_km(s, empty_history()) == 0.0


def test_distance_haversine_auckland_to_sydney() -> None:
    h = UserHistory(
        countries_30d=(),
        asns_30d=(),
        devices_seen=frozenset(),
        browsers_seen=frozenset(),
        os_seen=frozenset(),
        last_signin_at=None,
        last_latitude=-36.85,
        last_longitude=174.76,
    )
    s = _signin(lat=-33.87, lon=151.21)
    dist = distance_from_last_signin_km(s, h)
    # Auckland-Sydney is roughly 2150 km.
    assert 2000 < dist < 2300


def test_risk_numeric_mapping() -> None:
    assert risk_level_during_signin_numeric(_signin(risk="none")) == 0
    assert risk_level_during_signin_numeric(_signin(risk="medium")) == 2
    assert risk_level_during_signin_numeric(_signin(risk="high")) == 3


def test_legacy_auth_detection() -> None:
    legacy = _signin(is_interactive=False, auth_req="singleFactorAuthentication")
    not_legacy = _signin()
    assert is_legacy_auth(legacy) == 1
    assert is_legacy_auth(not_legacy) == 0


def test_extract_features_batch_returns_canonical_columns() -> None:
    s = _signin()
    df = extract_features_batch([(s, empty_history())])
    from cstack_ml_features import FEATURE_COLUMNS

    assert tuple(df.columns) == FEATURE_COLUMNS


def test_history_rolling_state_and_determinism() -> None:
    base = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)
    signins = []
    from datetime import timedelta as td

    for i in range(10):
        s = _signin(
            sid=f"s{i}",
            when=base + td(days=i),
            country="NZ" if i % 5 != 0 else "AU",
            ip="203.0.113.10" if i % 3 != 0 else "54.240.1.1",
        )
        signins.append(s)
    h1 = build_history_from_signins(signins, base + td(days=15))
    h2 = build_history_from_signins(signins, base + td(days=15))
    assert h1 == h2
    assert "NZ" in h1.countries_30d
    assert 4648 in h1.asns_30d


def test_extract_features_pipeline_sane() -> None:
    s = _signin()
    fs = extract_features(s, empty_history())
    assert 0.0 <= fs.hour_of_day_sin**2 + fs.hour_of_day_cos**2 - 1.0 < 1e-9
    assert fs.mfa_satisfied == 1
    assert fs.is_failure == 0
