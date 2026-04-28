"""Generate sign-in corpora for every fixture tenant and scenario.

    uv run python -m cstack_fixtures.synth.generate

Reads each tenant's existing ``users.json``, derives a synthetic profile per
user, and writes one ``signins.json`` plus ``ground_truth.json`` per
scenario under ``data/<tenant>/signins/<scenario>/``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cstack_fixtures.synth.scenarios import generate_scenario, scenarios_for_tenant
from cstack_fixtures.synth.signins import SyntheticUserProfile

DATA_DIR = Path(__file__).parent.parent / "data"

TENANTS = ("tenant-a", "tenant-b", "tenant-c")
USERS_PER_TENANT_FOR_SIGNINS = 30  # Subset of fixture users for tractable corpus size.

# Per-tenant tuning. Frequency is per business day; weekends downscale via
# weekend_factor. Mobile use rises for tenant-c where guests dominate.
_TENANT_TUNING: dict[str, dict[str, float]] = {
    "tenant-a": {"freq": 5.0, "weekend": 0.2, "mobile": 0.05},
    "tenant-b": {"freq": 4.0, "weekend": 0.3, "mobile": 0.08},
    "tenant-c": {"freq": 6.0, "weekend": 0.4, "mobile": 0.20},
}


def _profile_from_user(user: dict[str, Any], tenant: str) -> SyntheticUserProfile:
    tuning = _TENANT_TUNING[tenant]
    upn = user.get("userPrincipalName") or f"{user['id']}@example.com"
    return SyntheticUserProfile(
        user_id=user["id"],
        upn=upn,
        home_country="NZ",
        home_city="Auckland",
        home_asn_index=0,
        work_hours_start_local=8,
        work_hours_end_local=18,
        timezone_offset_hours=12,
        device_os="Windows 11",
        device_browser="Edge 124",
        mfa_method="mobileAppNotification",
        signin_frequency_per_day=float(tuning["freq"]),
        weekend_factor=float(tuning["weekend"]),
        mobile_use_pct=float(tuning["mobile"]),
    )


def _load_users(tenant: str, limit: int) -> list[dict[str, Any]]:
    path = DATA_DIR / tenant / "users.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected JSON array")
    users: list[dict[str, Any]] = [u for u in payload if isinstance(u, dict)]
    return users[:limit]


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(seed: int = 42) -> None:
    for tenant_index, tenant in enumerate(TENANTS):
        users = _load_users(tenant, USERS_PER_TENANT_FOR_SIGNINS)
        profiles = [_profile_from_user(u, tenant) for u in users]
        for scenario in scenarios_for_tenant():
            base_seed = seed + tenant_index * 10000
            generated = generate_scenario(profiles, scenario, base_seed=base_seed)
            scenario_dir = DATA_DIR / tenant / "signins" / scenario.name
            _write(scenario_dir / "signins.json", generated.signins)
            _write(scenario_dir / "ground_truth.json", generated.ground_truth)
            print(
                f"{tenant}/{scenario.name}: "
                f"{len(generated.signins)} signins, "
                f"{len(generated.ground_truth)} ground-truth anomalies"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    main(seed=args.seed)
