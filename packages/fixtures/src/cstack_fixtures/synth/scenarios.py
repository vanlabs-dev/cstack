"""Scenario plan: how baselines and injections combine for each fixture tenant."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from cstack_fixtures.synth.anomalies import (
    inject_credential_stuffing_burst,
    inject_impossible_travel,
    inject_mfa_bypass,
    inject_new_asn,
    inject_off_hours_admin_action,
)
from cstack_fixtures.synth.signins import (
    SyntheticUserProfile,
    synthesize_baseline_signins,
)

ScenarioName = Literal["baseline", "replay-attacks", "noisy"]

BASELINE_DAYS = 30
SCENARIO_START = datetime(2026, 3, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Scenario:
    name: ScenarioName
    description: str
    days: int
    inject_attacks: bool
    noisy_users_count: int
    seed_offset: int


_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="baseline",
        description="60 days of normal behaviour, no injected anomalies.",
        days=BASELINE_DAYS,
        inject_attacks=False,
        noisy_users_count=0,
        seed_offset=0,
    ),
    Scenario(
        name="replay-attacks",
        description=(
            "Baseline plus scripted impossible-travel, MFA bypass, off-hours admin, "
            "and credential-stuffing burst on known days."
        ),
        days=BASELINE_DAYS,
        inject_attacks=True,
        noisy_users_count=0,
        seed_offset=1,
    ),
    Scenario(
        name="noisy",
        description=(
            "Operationally noisy normals (frequent travel, shared workstation, "
            "shifted hours) plus the same scripted attacks."
        ),
        days=BASELINE_DAYS,
        inject_attacks=True,
        noisy_users_count=3,
        seed_offset=2,
    ),
)


def scenarios_for_tenant() -> tuple[Scenario, ...]:
    return _SCENARIOS


@dataclass(frozen=True)
class GeneratedScenario:
    scenario: Scenario
    signins: list[dict[str, Any]] = field(default_factory=list)
    ground_truth: list[dict[str, Any]] = field(default_factory=list)


_InjectionFn = Callable[[SyntheticUserProfile, random.Random, datetime], Any]


def _attack_injection_plan() -> tuple[tuple[int, str, _InjectionFn], ...]:
    """Day offsets and injection functions, in plan order."""
    return (
        (15, "impossible_travel", inject_impossible_travel),
        (18, "mfa_bypass", inject_mfa_bypass),
        (21, "off_hours_admin_action", inject_off_hours_admin_action),
        (25, "credential_stuffing_burst", inject_credential_stuffing_burst),
        (28, "new_asn", inject_new_asn),
    )


def _apply_noise(
    profiles: list[SyntheticUserProfile], noisy_count: int
) -> list[SyntheticUserProfile]:
    if noisy_count <= 0:
        return profiles
    out = list(profiles)
    # First noisy_count profiles: shift hours, raise mobile use, raise weekend
    # factor. These look anomaly-shaped to a naive model.
    for i in range(min(noisy_count, len(out))):
        p = out[i]
        out[i] = SyntheticUserProfile(
            user_id=p.user_id,
            upn=p.upn,
            home_country=p.home_country,
            home_city=p.home_city,
            home_asn_index=p.home_asn_index,
            work_hours_start_local=max(p.work_hours_start_local - 4, 0),
            work_hours_end_local=min(p.work_hours_end_local + 4, 23),
            timezone_offset_hours=p.timezone_offset_hours,
            device_os=p.device_os,
            device_browser=p.device_browser,
            mfa_method=p.mfa_method,
            signin_frequency_per_day=p.signin_frequency_per_day * 1.4,
            weekend_factor=max(p.weekend_factor, 0.6),
            mobile_use_pct=min(p.mobile_use_pct + 0.2, 1.0),
        )
    return out


def generate_scenario(
    profiles: list[SyntheticUserProfile],
    scenario: Scenario,
    base_seed: int,
) -> GeneratedScenario:
    rng = random.Random(base_seed + scenario.seed_offset)
    profiles = _apply_noise(profiles, scenario.noisy_users_count)
    all_events: list[dict[str, Any]] = []
    for profile in profiles:
        events = synthesize_baseline_signins(profile, scenario.days, SCENARIO_START, rng)
        all_events.extend(events)

    ground_truth: list[dict[str, Any]] = []
    if scenario.inject_attacks and profiles:
        # Pick deterministic victim users for the scripted attacks.
        victims = [
            profiles[len(profiles) * (i + 1) // (len(_attack_injection_plan()) + 1)]
            for i in range(len(_attack_injection_plan()))
        ]
        for victim, (day_offset, label, fn) in zip(victims, _attack_injection_plan(), strict=False):
            when_local = SCENARIO_START + timedelta(days=day_offset, hours=14)
            result = fn(victim, rng, when_local)
            events = result if isinstance(result, list) else [result]
            for ev in events:
                ev_id = ev["id"]
                ground_truth.append(
                    {
                        "signin_id": ev_id,
                        "user_id": victim.user_id,
                        "anomaly_type": label,
                        "injected_at": ev["createdDateTime"],
                    }
                )
                all_events.append(ev)

    all_events.sort(key=lambda e: e["createdDateTime"])
    # Strip private debug fields before the JSON corpus is written.
    cleaned: list[dict[str, Any]] = []
    for ev in all_events:
        cleaned.append({k: v for k, v in ev.items() if not k.startswith("_")})
    return GeneratedScenario(scenario=scenario, signins=cleaned, ground_truth=ground_truth)
