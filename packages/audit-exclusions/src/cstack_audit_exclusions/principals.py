from dataclasses import dataclass
from typing import Literal

from cstack_schemas import (
    ConditionalAccessPolicy,
    DirectoryRole,
    Group,
    RoleAssignment,
    User,
)

ExclusionVia = Literal["direct", "group", "role"]


@dataclass(frozen=True)
class ResolvedPrincipal:
    """A user resolved from a policy's exclusion list, with provenance.

    Attributes:
        user: the underlying User object.
        excluded_from_policy_id: which CA policy excluded this user.
        excluded_via: how the exclusion happened (direct id, via group, via role).
        via_object_id: the group or role id that caused the exclusion (None for direct).
        current_role_assignments: roleTemplateIds the user currently holds, used by
            the analyser to flag privileged-user exclusions.
    """

    user: User
    excluded_from_policy_id: str
    excluded_via: ExclusionVia
    via_object_id: str | None
    current_role_assignments: list[str]


def resolve_excluded_principals(
    policy: ConditionalAccessPolicy,
    users: list[User],
    groups: list[Group],
    roles: list[DirectoryRole],
    role_assignments: list[RoleAssignment],
) -> list[ResolvedPrincipal]:
    """Flatten a policy's exclude lists into a list of resolved users."""
    cond = policy.conditions.users if policy.conditions is not None else None
    if cond is None:
        return []

    user_index = {u.id: u for u in users}
    resolved: list[ResolvedPrincipal] = []
    seen: set[tuple[str, ExclusionVia, str | None]] = set()

    def _push(user_id: str, via: ExclusionVia, via_obj: str | None) -> None:
        user = user_index.get(user_id)
        if user is None:
            return
        key = (user_id, via, via_obj)
        if key in seen:
            return
        seen.add(key)
        resolved.append(
            ResolvedPrincipal(
                user=user,
                excluded_from_policy_id=policy.id,
                excluded_via=via,
                via_object_id=via_obj,
                current_role_assignments=_role_templates_for_user(user_id, roles, role_assignments),
            )
        )

    for uid in cond.exclude_users or []:
        _push(uid, "direct", None)

    if cond.exclude_groups:
        target_groups = set(cond.exclude_groups)
        for group in groups:
            if group.id in target_groups:
                for uid in group.members:
                    _push(uid, "group", group.id)

    if cond.exclude_roles:
        target_roles = set(cond.exclude_roles)
        for role in roles:
            if role.role_template_id in target_roles or role.id in target_roles:
                for uid in role.members:
                    _push(uid, "role", role.id)

    return resolved


def _role_templates_for_user(
    user_id: str,
    roles: list[DirectoryRole],
    role_assignments: list[RoleAssignment],
) -> list[str]:
    holds: set[str] = set()
    for role in roles:
        if user_id in role.members and role.role_template_id is not None:
            holds.add(role.role_template_id)
    for assignment in role_assignments:
        if assignment.principal_id == user_id and assignment.role_definition_id is not None:
            holds.add(assignment.role_definition_id)
    return sorted(holds)
