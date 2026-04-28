from datetime import UTC, datetime

import duckdb
from cstack_schemas import SignIn
from cstack_storage import (
    count_signins_by_user,
    get_signins,
    upsert_signins,
)

TENANT = "00000000-0000-0000-0000-aaaa00000001"


def _signin(sid: str, user: str, when: datetime) -> SignIn:
    return SignIn.model_validate(
        {
            "id": sid,
            "createdDateTime": when.isoformat(),
            "userId": user,
            "userPrincipalName": f"{user}@example.com",
            "ipAddress": "203.0.113.10",
            "isInteractive": True,
            "location": {"countryOrRegion": "NZ", "city": "Auckland"},
        }
    )


def test_upsert_and_get(db: duckdb.DuckDBPyConnection) -> None:
    items = [
        _signin("s1", "u1", datetime(2026, 4, 28, 9, 0, tzinfo=UTC)),
        _signin("s2", "u1", datetime(2026, 4, 28, 14, 0, tzinfo=UTC)),
        _signin("s3", "u2", datetime(2026, 4, 28, 9, 0, tzinfo=UTC)),
    ]
    assert upsert_signins(db, TENANT, items) == 3

    all_signins = get_signins(db, TENANT)
    assert len(all_signins) == 3

    user1 = get_signins(db, TENANT, user_id="u1")
    assert {s.id for s in user1} == {"s1", "s2"}


def test_upsert_is_idempotent(db: duckdb.DuckDBPyConnection) -> None:
    s = _signin("s1", "u1", datetime(2026, 4, 28, 9, 0, tzinfo=UTC))
    upsert_signins(db, TENANT, [s])
    upsert_signins(db, TENANT, [s])
    assert len(get_signins(db, TENANT)) == 1


def test_count_signins_by_user(db: duckdb.DuckDBPyConnection) -> None:
    items = [
        _signin("s1", "u1", datetime(2026, 4, 28, 9, 0, tzinfo=UTC)),
        _signin("s2", "u1", datetime(2026, 4, 28, 14, 0, tzinfo=UTC)),
        _signin("s3", "u2", datetime(2026, 4, 28, 9, 0, tzinfo=UTC)),
    ]
    upsert_signins(db, TENANT, items)
    counts = count_signins_by_user(db, TENANT)
    assert counts == {"u1": 2, "u2": 1}
