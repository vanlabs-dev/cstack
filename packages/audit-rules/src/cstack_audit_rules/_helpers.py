"""Shared evaluation helpers reused across rules. Internal to the package."""

from cstack_schemas import ConditionalAccessPolicy

REPORT_ONLY_STATE = "enabledForReportingButNotEnforced"

# Microsoft Entra role template ids that count as "admin" for rule scoping.
PRIVILEGED_ROLE_TEMPLATE_IDS: frozenset[str] = frozenset(
    {
        "62e90394-69f5-4237-9190-012177145e10",  # Global Administrator
        "e8611ab8-c189-46e8-94e1-60213ab1f814",  # Privileged Role Administrator
        "7be44c8a-adaf-4e2a-84d6-ab2649e08a13",  # Privileged Authentication Administrator
        "194ae4cb-b126-40b2-bd5b-6091b380977d",  # Security Administrator
        "b1be1c3e-b65d-4f19-8427-f6fa0d97feb9",  # Conditional Access Administrator
        "9b895d92-2cd3-44c7-9d02-a6ac2d5ea5c3",  # Application Administrator
        "158c047a-c907-4556-b7ef-446551a6b5f7",  # Cloud Application Administrator
        "fe930be7-5e62-47db-91af-98c3a49a38b1",  # User Administrator
        "729827e3-9c14-49f7-bb1b-9608f156bbb8",  # Helpdesk Administrator
        "8ac3fc64-6eca-42ea-9e69-59f4c7b60eb2",  # Hybrid Identity Administrator
        "c4e39bd9-1100-46d3-8c65-fb160da0071f",  # Authentication Administrator
        "29232cdf-9323-42fd-ade2-1d097af3e4de",  # Exchange Administrator
        "f28a1f50-f6e7-4571-818b-6a12f2af6b6c",  # SharePoint Administrator
        "17315797-102d-40b4-93e0-432062caca18",  # Compliance Administrator
    }
)

SENSITIVE_APP_IDS: frozenset[str] = frozenset(
    {
        "c44b4083-3bb0-49c1-b47d-974e53cbdf3c",  # Azure Portal
        "14d82eec-204b-4c2f-b7e8-296a70dab67e",  # Microsoft Graph PowerShell
        "00000003-0000-0ff1-ce00-000000000000",  # SharePoint / OneDrive
    }
)


def is_enabled(policy: ConditionalAccessPolicy) -> bool:
    return policy.state == "enabled"


def is_report_only(policy: ConditionalAccessPolicy) -> bool:
    return policy.state == REPORT_ONLY_STATE


def has_built_in_control(policy: ConditionalAccessPolicy, control: str) -> bool:
    if policy.grant_controls is None or policy.grant_controls.built_in_controls is None:
        return False
    return control in policy.grant_controls.built_in_controls


def targets_all_users(policy: ConditionalAccessPolicy) -> bool:
    cond = policy.conditions.users if policy.conditions is not None else None
    if cond is None:
        return False
    return cond.include_users == ["All"]


def targets_role_template_ids(
    policy: ConditionalAccessPolicy, template_ids: frozenset[str]
) -> bool:
    cond = policy.conditions.users if policy.conditions is not None else None
    if cond is None or cond.include_roles is None:
        return False
    return any(rid in template_ids for rid in cond.include_roles)


def targets_app_id(policy: ConditionalAccessPolicy, app_ids: frozenset[str]) -> bool:
    apps = policy.conditions.applications if policy.conditions is not None else None
    if apps is None or apps.include_applications is None:
        return False
    return any(aid in app_ids for aid in apps.include_applications)


def includes_legacy_client_app_types(policy: ConditionalAccessPolicy) -> bool:
    cond = policy.conditions
    if cond is None or cond.client_app_types is None:
        return False
    return bool(set(cond.client_app_types) & {"other", "exchangeActiveSync"})
