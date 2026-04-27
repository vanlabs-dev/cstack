from datetime import datetime
from enum import IntEnum

from cstack_schemas import (
    ConditionalAccessPolicy,
    DirectoryRole,
    Group,
    RoleAssignment,
    User,
)
from pydantic import BaseModel, ConfigDict

from cstack_audit_coverage.app_segments import (
    LEGACY_AUTH_CLIENT_APP_TYPES,
    AppSegment,
    app_segment_ids,
)
from cstack_audit_coverage.segments import (
    UserSegment,
    resolve_segment_members,
)


class ProtectionLevel(IntEnum):
    """Strongest control any applicable policy applies. Higher is stronger."""

    NONE = 0
    REPORT_ONLY = 1
    COMPLIANT_DEVICE = 2
    MFA = 3
    MFA_AND_DEVICE = 4


class CoverageCell(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_segment: UserSegment
    app_segment: AppSegment
    applicable_policy_ids: list[str]
    protection_level: ProtectionLevel
    member_count: int


class CoverageMatrix(BaseModel):
    tenant_id: str
    cells: list[CoverageCell]
    computed_at: datetime


def compute_coverage(
    tenant_id: str,
    policies: list[ConditionalAccessPolicy],
    users: list[User],
    groups: list[Group],
    roles: list[DirectoryRole],
    role_assignments: list[RoleAssignment],
    as_of: datetime,
) -> CoverageMatrix:
    """Build the coverage matrix for a tenant. Pure function; no IO."""
    cells: list[CoverageCell] = []
    for user_segment in UserSegment:
        member_ids = resolve_segment_members(
            user_segment, users, groups, roles, role_assignments, as_of=as_of
        )
        for app_segment in AppSegment:
            applicable: list[str] = []
            best_level = ProtectionLevel.NONE
            for policy in policies:
                if policy.state == "disabled":
                    continue
                if not _users_in_scope(policy, member_ids, groups, roles):
                    continue
                if not _app_segment_in_scope(policy, app_segment):
                    continue
                applicable.append(policy.id)
                level = _policy_protection_level(policy)
                if level > best_level:
                    best_level = level
            cells.append(
                CoverageCell(
                    user_segment=user_segment,
                    app_segment=app_segment,
                    applicable_policy_ids=applicable,
                    protection_level=best_level,
                    member_count=len(member_ids),
                )
            )
    return CoverageMatrix(tenant_id=tenant_id, cells=cells, computed_at=as_of)


def _users_in_scope(
    policy: ConditionalAccessPolicy,
    candidate_ids: set[str],
    groups: list[Group],
    roles: list[DirectoryRole],
) -> bool:
    """True if at least one user in ``candidate_ids`` is covered by the policy.

    A user is covered when an include condition matches and no exclude
    condition does. Empty candidate sets (segment has no members) trivially
    fail because there is nobody to protect.
    """
    if not candidate_ids:
        return False
    cond = policy.conditions.users if policy.conditions is not None else None
    if cond is None:
        # Policy with no user condition is treated as "applies to everyone".
        return True

    if cond.include_users == ["All"]:
        included = set(candidate_ids)
    else:
        included = set()
        if cond.include_users:
            included.update(uid for uid in cond.include_users if uid in candidate_ids)
        if cond.include_groups:
            target_groups = set(cond.include_groups)
            for group in groups:
                if group.id in target_groups:
                    included.update(set(group.members) & candidate_ids)
        if cond.include_roles:
            target_roles = set(cond.include_roles)
            for role in roles:
                if role.role_template_id in target_roles or role.id in target_roles:
                    included.update(set(role.members) & candidate_ids)
        # Guest external user inclusion is treated permissively here; the
        # exclusion analyser handles guest-specific edge cases.
        if cond.include_guests_or_external_users:
            # Without resolving the actual guest type, assume any guests in
            # the candidate set are reachable.
            included.update(candidate_ids)

    excluded: set[str] = set()
    if cond.exclude_users:
        excluded.update(cond.exclude_users)
    if cond.exclude_groups:
        target_groups = set(cond.exclude_groups)
        for group in groups:
            if group.id in target_groups:
                excluded.update(group.members)
    if cond.exclude_roles:
        target_roles = set(cond.exclude_roles)
        for role in roles:
            if role.role_template_id in target_roles or role.id in target_roles:
                excluded.update(role.members)

    return bool(included - excluded)


def _app_segment_in_scope(policy: ConditionalAccessPolicy, segment: AppSegment) -> bool:
    """True if the policy targets the given app segment."""
    cond = policy.conditions
    if segment is AppSegment.LEGACY_AUTH:
        if cond is None or cond.client_app_types is None:
            return False
        return bool(set(cond.client_app_types) & LEGACY_AUTH_CLIENT_APP_TYPES)

    apps = cond.applications if cond is not None else None
    if apps is None:
        return False
    include = set(apps.include_applications or [])
    exclude = set(apps.exclude_applications or [])
    if segment is AppSegment.ALL_APPS:
        return "All" in include and not exclude
    target = set(app_segment_ids(segment))
    if not target:
        return False
    if "All" in include:
        return bool(target - exclude)
    return bool((include & target) - exclude)


def _policy_protection_level(policy: ConditionalAccessPolicy) -> ProtectionLevel:
    """Translate a policy's grant control + state into a coverage level."""
    if policy.state == "enabledForReportingButNotEnforced":
        return ProtectionLevel.REPORT_ONLY
    if policy.state != "enabled":
        return ProtectionLevel.NONE
    grant = policy.grant_controls
    if grant is None or grant.built_in_controls is None:
        return ProtectionLevel.NONE
    controls = set(grant.built_in_controls)
    has_mfa = "mfa" in controls
    has_device = "compliantDevice" in controls or "domainJoinedDevice" in controls
    has_block = "block" in controls
    # Block protects access; treat as MFA-equivalent for coverage scoring.
    if has_block and has_device:
        return ProtectionLevel.MFA_AND_DEVICE
    if has_block:
        return ProtectionLevel.MFA
    if has_mfa and has_device:
        return ProtectionLevel.MFA_AND_DEVICE
    if has_mfa:
        return ProtectionLevel.MFA
    if has_device:
        return ProtectionLevel.COMPLIANT_DEVICE
    return ProtectionLevel.NONE
