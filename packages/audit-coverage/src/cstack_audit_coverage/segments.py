import re
from datetime import datetime
from enum import StrEnum

from cstack_schemas import DirectoryRole, Group, RoleAssignment, User

# 14 highest-privilege Microsoft Entra role template IDs. The list is used by
# the ADMINS_ANY user segment. Sourced from Microsoft's published built-in
# role catalogue.
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

# Subset for the PRIVILEGED_ROLES segment: the four most sensitive tier-0
# roles. These are the ones whose compromise hands the attacker the keys.
TIER_0_ROLE_TEMPLATE_IDS: frozenset[str] = frozenset(
    {
        "62e90394-69f5-4237-9190-012177145e10",  # Global Administrator
        "e8611ab8-c189-46e8-94e1-60213ab1f814",  # Privileged Role Administrator
        "7be44c8a-adaf-4e2a-84d6-ab2649e08a13",  # Privileged Authentication Administrator
        "194ae4cb-b126-40b2-bd5b-6091b380977d",  # Security Administrator
    }
)


class UserSegment(StrEnum):
    """Coarse user buckets the coverage matrix evaluates against.

    Resolution from raw directory data lives in this module's helpers; the
    matrix consumes the resolved sets only.
    """

    ALL_USERS = "all_users"
    ADMINS_ANY = "admins_any"
    GUESTS = "guests"
    SERVICE_ACCOUNTS = "service_accounts"
    PRIVILEGED_ROLES = "privileged_roles"


_SERVICE_ACCOUNT_PATTERNS = (
    re.compile(r"^svc[_\-\.]", re.IGNORECASE),
    re.compile(r"-sa$", re.IGNORECASE),
    re.compile(r"_serviceaccount_", re.IGNORECASE),
    re.compile(r"^noreply", re.IGNORECASE),
    re.compile(r"automation", re.IGNORECASE),
)


def is_service_account(user: User, as_of: datetime, stale_days: int = 365) -> bool:
    """Heuristic: looks like a non-interactive service account.

    A user is treated as a service account if its identifiers match any of the
    name patterns or it has no recorded sign-in for ``stale_days`` or more.
    """
    haystack = " ".join(filter(None, [user.display_name, user.user_principal_name]))
    if any(p.search(haystack) for p in _SERVICE_ACCOUNT_PATTERNS):
        return True
    activity = user.sign_in_activity
    if activity is None or activity.last_sign_in_date_time is None:
        return True
    return (as_of - activity.last_sign_in_date_time).days >= stale_days


def resolve_segment_members(
    segment: UserSegment,
    users: list[User],
    groups: list[Group],
    roles: list[DirectoryRole],
    role_assignments: list[RoleAssignment],
    as_of: datetime,
) -> set[str]:
    """Return the user IDs that belong to the given segment."""
    if segment is UserSegment.ALL_USERS:
        return {u.id for u in users}
    if segment is UserSegment.GUESTS:
        return {u.id for u in users if (u.user_type or "").lower() == "guest"}
    if segment is UserSegment.SERVICE_ACCOUNTS:
        return {u.id for u in users if is_service_account(u, as_of)}
    if segment is UserSegment.ADMINS_ANY:
        return _members_of_role_templates(roles, role_assignments, PRIVILEGED_ROLE_TEMPLATE_IDS)
    if segment is UserSegment.PRIVILEGED_ROLES:
        return _members_of_role_templates(roles, role_assignments, TIER_0_ROLE_TEMPLATE_IDS)
    raise ValueError(f"unknown user segment: {segment!r}")


def _members_of_role_templates(
    roles: list[DirectoryRole],
    role_assignments: list[RoleAssignment],
    template_ids: frozenset[str],
) -> set[str]:
    """Pull principal ids from both DirectoryRole.members and RoleAssignment.

    Live tenants populate one or the other depending on whether unified RBAC
    is in use; fixtures may use either, so the segment resolver supports both.
    """
    members: set[str] = set()
    for role in roles:
        if role.role_template_id in template_ids:
            members.update(role.members)
    for assignment in role_assignments:
        if assignment.role_definition_id in template_ids and assignment.principal_id is not None:
            members.add(assignment.principal_id)
    return members
