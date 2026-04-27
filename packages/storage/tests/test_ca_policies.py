import duckdb
from cstack_schemas import ConditionalAccessPolicy
from cstack_storage import get_policies, upsert_ca_policies

TENANT = "00000000-0000-0000-0000-0000000000aa"


def _make_policy(policy_id: str, name: str, state: str = "enabled") -> ConditionalAccessPolicy:
    return ConditionalAccessPolicy.model_validate(
        {
            "id": policy_id,
            "displayName": name,
            "state": state,
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }
    )


def test_upsert_then_read_back(db: duckdb.DuckDBPyConnection) -> None:
    written = upsert_ca_policies(
        db, TENANT, [_make_policy("p1", "MFA"), _make_policy("p2", "Block")]
    )
    assert written == 2

    fetched = get_policies(db, TENANT)
    assert {p.id for p in fetched} == {"p1", "p2"}
    by_id = {p.id: p for p in fetched}
    assert by_id["p1"].grant_controls is not None
    assert by_id["p1"].grant_controls.built_in_controls == ["mfa"]


def test_upsert_is_idempotent(db: duckdb.DuckDBPyConnection) -> None:
    upsert_ca_policies(db, TENANT, [_make_policy("p1", "v1")])
    upsert_ca_policies(db, TENANT, [_make_policy("p1", "v2")])
    fetched = get_policies(db, TENANT)
    assert len(fetched) == 1
    assert fetched[0].display_name == "v2"


def test_upsert_empty_list_returns_zero(db: duckdb.DuckDBPyConnection) -> None:
    assert upsert_ca_policies(db, TENANT, []) == 0


def test_get_policies_returns_empty_for_unknown_tenant(db: duckdb.DuckDBPyConnection) -> None:
    assert get_policies(db, "no-such-tenant") == []
