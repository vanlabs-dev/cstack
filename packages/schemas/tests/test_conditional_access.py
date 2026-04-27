from cstack_schemas import (
    ConditionalAccessPolicy,
    Conditions,
    GrantControls,
    Users,
)


def test_minimum_policy_from_graph_payload() -> None:
    payload: dict[str, object] = {
        "id": "ca-policy-1",
        "displayName": "Require MFA for all users",
        "state": "enabled",
        "createdDateTime": "2025-01-15T10:00:00Z",
        "modifiedDateTime": "2025-02-01T10:00:00Z",
        "conditions": {
            "users": {
                "includeUsers": ["All"],
                "excludeUsers": ["00000000-0000-0000-0000-000000000099"],
            },
            "applications": {"includeApplications": ["All"]},
        },
        "grantControls": {
            "operator": "OR",
            "builtInControls": ["mfa"],
        },
    }
    policy = ConditionalAccessPolicy.model_validate(payload)
    assert policy.id == "ca-policy-1"
    assert policy.display_name == "Require MFA for all users"
    assert policy.state == "enabled"
    assert isinstance(policy.conditions, Conditions)
    assert isinstance(policy.conditions.users, Users)
    assert policy.conditions.users.include_users == ["All"]
    assert isinstance(policy.grant_controls, GrantControls)
    assert policy.grant_controls.built_in_controls == ["mfa"]


def test_unknown_extra_fields_preserved() -> None:
    payload: dict[str, object] = {
        "id": "p1",
        "displayName": "future-shape",
        "futureFieldFromGraph": {"any": "value"},
    }
    policy = ConditionalAccessPolicy.model_validate(payload)
    # extra="allow" should retain unknown fields without parsing failure
    dumped = policy.model_dump(by_alias=True)
    assert dumped["futureFieldFromGraph"] == {"any": "value"}


def test_disabled_state_accepted() -> None:
    policy = ConditionalAccessPolicy.model_validate(
        {"id": "p", "displayName": "name", "state": "disabled"}
    )
    assert policy.state == "disabled"


def test_report_only_state_accepted() -> None:
    policy = ConditionalAccessPolicy.model_validate(
        {"id": "p", "displayName": "name", "state": "enabledForReportingButNotEnforced"}
    )
    assert policy.state == "enabledForReportingButNotEnforced"
