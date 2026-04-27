"""Regenerate users.json files for each fixture tenant.

The user list is the only fixture asset large enough to justify a generator
(50-100 entries per tenant). All other Graph payloads are hand-curated so the
shapes remain intentional for the Sprint 2 audit work.

Usage:

    uv run python packages/fixtures/scripts/generate.py
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "src" / "cstack_fixtures" / "data"

_FIRST_NAMES = (
    "Pat",
    "Sam",
    "Alex",
    "Jordan",
    "Taylor",
    "Morgan",
    "Riley",
    "Casey",
    "Avery",
    "Quinn",
    "Blake",
    "Dakota",
    "Drew",
    "Jamie",
    "Kendall",
    "Reese",
    "Sage",
    "Skyler",
    "Cameron",
    "Parker",
    "Devon",
    "Emerson",
    "Finley",
    "Hayden",
    "Lane",
    "Logan",
    "Noor",
    "Phoenix",
    "Robin",
    "Tatum",
)
_LAST_NAMES = (
    "Smith",
    "Jones",
    "Williams",
    "Brown",
    "Davis",
    "Miller",
    "Wilson",
    "Moore",
    "Taylor",
    "Anderson",
    "Thomas",
    "Jackson",
    "White",
    "Harris",
    "Martin",
    "Thompson",
    "Garcia",
    "Martinez",
    "Robinson",
    "Clark",
    "Lewis",
    "Lee",
    "Walker",
    "Hall",
    "Allen",
    "Young",
    "Hernandez",
    "King",
    "Wright",
)


@dataclass(frozen=True)
class _Profile:
    count: int
    domain: str
    last_signin_distribution: tuple[int, ...]
    enabled_ratio: float
    guest_ratio: float


def _utc_iso(when: datetime) -> str:
    return when.isoformat().replace("+00:00", "Z")


def generate_user(
    tenant: str,
    index: int,
    rng: random.Random,
    now: datetime,
    profile: _Profile,
) -> dict[str, Any]:
    first = rng.choice(_FIRST_NAMES)
    last = rng.choice(_LAST_NAMES)
    is_guest = rng.random() < profile.guest_ratio
    enabled = rng.random() < profile.enabled_ratio
    days_since_signin = rng.choice(profile.last_signin_distribution)
    last_signin = _utc_iso(now - timedelta(days=days_since_signin))
    upn_local = f"user{index:04d}"
    upn = f"{upn_local}#EXT#@{profile.domain}" if is_guest else f"{upn_local}@{profile.domain}"
    return {
        "id": f"user-{tenant}-{index:04d}",
        "displayName": f"{first} {last}",
        "userPrincipalName": upn,
        "accountEnabled": enabled,
        "userType": "Guest" if is_guest else "Member",
        "signInActivity": {"lastSignInDateTime": last_signin},
    }


def generate_tenant_users(tenant: str, profile: _Profile) -> list[dict[str, Any]]:
    # Per-tenant seed makes the output deterministic across re-runs.
    rng = random.Random(f"cstack-fixtures-{tenant}".encode())
    now = datetime(2026, 4, 1, tzinfo=UTC)
    return [generate_user(tenant, i, rng, now, profile) for i in range(1, profile.count + 1)]


# Distribution arrays are sampled uniformly, so the proportion of "stale" users
# is set by how many entries are 90+ days.
_PROFILES: dict[str, _Profile] = {
    "tenant-a": _Profile(
        count=60,
        domain="tenant-a.example",
        last_signin_distribution=(1, 1, 3, 7, 14, 30, 45, 60),
        enabled_ratio=0.95,
        guest_ratio=0.10,
    ),
    "tenant-b": _Profile(
        count=80,
        domain="tenant-b.example",
        # ~30% of users are 90+ days inactive, matching the messy scenario.
        last_signin_distribution=(1, 7, 30, 60, 95, 120, 180, 365),
        enabled_ratio=0.85,
        guest_ratio=0.05,
    ),
    "tenant-c": _Profile(
        count=75,
        domain="tenant-c.example",
        last_signin_distribution=(1, 7, 30, 90, 180),
        enabled_ratio=0.90,
        guest_ratio=0.20,
    ),
}


def main() -> None:
    for tenant, profile in _PROFILES.items():
        users = generate_tenant_users(tenant, profile)
        out = DATA_DIR / tenant / "users.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(users, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {len(users)} users -> {out.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
