import random
from datetime import UTC, datetime

from cstack_fixtures.synth import (
    SyntheticUserProfile,
    inject_impossible_travel,
    synthesize_baseline_signins,
)
from cstack_fixtures.synth.scenarios import generate_scenario, scenarios_for_tenant


def _profile(uid: str = "u1") -> SyntheticUserProfile:
    return SyntheticUserProfile(
        user_id=uid,
        upn=f"{uid}@example.com",
        home_country="NZ",
        home_city="Auckland",
        home_asn_index=0,
        work_hours_start_local=8,
        work_hours_end_local=18,
        timezone_offset_hours=12,
        device_os="Windows 11",
        device_browser="Edge 124",
        mfa_method="mobileAppNotification",
        signin_frequency_per_day=4.0,
        weekend_factor=0.3,
        mobile_use_pct=0.1,
    )


def test_baseline_synth_is_reproducible() -> None:
    start = datetime(2026, 4, 1, tzinfo=UTC)
    out1 = synthesize_baseline_signins(_profile(), 5, start, random.Random(42))
    out2 = synthesize_baseline_signins(_profile(), 5, start, random.Random(42))
    assert [e["id"] for e in out1] == [e["id"] for e in out2]


def test_signins_parse_through_schema() -> None:
    from cstack_schemas import SignIn

    start = datetime(2026, 4, 1, tzinfo=UTC)
    events = synthesize_baseline_signins(_profile(), 3, start, random.Random(7))
    parsed = [SignIn.model_validate(e) for e in events]
    assert all(p.user_id == "u1" for p in parsed)


def test_injection_returns_two_events() -> None:
    when = datetime(2026, 4, 10, 14, 0, tzinfo=UTC)
    events = inject_impossible_travel(_profile(), random.Random(1), when)
    assert len(events) == 2
    # ~30 minutes apart by spec.
    t0 = datetime.fromisoformat(events[0]["createdDateTime"].replace("Z", "+00:00"))
    t1 = datetime.fromisoformat(events[1]["createdDateTime"].replace("Z", "+00:00"))
    delta = (t1 - t0).total_seconds()
    assert 1700 < delta < 1900


def test_scenario_baseline_has_no_ground_truth() -> None:
    profiles = [_profile(f"u{i}") for i in range(3)]
    scenario = scenarios_for_tenant()[0]
    result = generate_scenario(profiles, scenario, base_seed=42)
    assert result.ground_truth == []


def test_scenario_replay_attacks_produces_ground_truth() -> None:
    profiles = [_profile(f"u{i}") for i in range(8)]
    replay = scenarios_for_tenant()[1]
    result = generate_scenario(profiles, replay, base_seed=42)
    labels = {gt["anomaly_type"] for gt in result.ground_truth}
    assert {
        "impossible_travel",
        "mfa_bypass",
        "off_hours_admin_action",
        "credential_stuffing_burst",
        "new_asn",
    }.issubset(labels)


def test_load_signins_populates_db_and_returns_counts() -> None:
    from pathlib import Path

    import duckdb
    from cstack_fixtures import load_fixture, load_signins
    from cstack_storage import (
        connection_scope,
        count_signins_by_user,
        run_migrations,
    )

    db_path = Path.cwd() / ".pytest-cache-tmp.duckdb"
    if db_path.exists():
        db_path.unlink()
    try:
        with connection_scope(db_path) as conn:
            run_migrations(conn)
            load_fixture("tenant-a", conn)
            result = load_signins("tenant-a", "baseline", conn)
            assert result.rows_written > 0
            assert result.scenario == "baseline"
            counts = count_signins_by_user(conn, result.tenant_id)
            assert sum(counts.values()) == result.rows_written
    finally:
        if db_path.exists():
            db_path.unlink()
        # Conftest temp paths are normally fine; this test uses its own to
        # avoid the per-fixture db conftest because load_signins needs the
        # full tenant load first.
        _ = duckdb
