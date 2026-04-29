from typing import Any

from cstack_audit_core import AffectedObject, Finding, Severity
from cstack_audit_rules import AuditContext
from cstack_schemas import ConditionalAccessPolicy, User

from cstack_audit_exclusions.principals import (
    ResolvedPrincipal,
    resolve_excluded_principals,
)

# Re-stated locally so the exclusions package keeps a small dependency graph.
_PRIVILEGED_ROLE_TEMPLATE_IDS: frozenset[str] = frozenset(
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

_DOC_KEYWORDS = (
    "exclude",
    "exception",
    "break-glass",
    "breakglass",
    "service account",
    "svc",
    "bypass",
)

_REFERENCES_BASE = [
    "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/concept-conditional-access-users-groups",
    "https://www.cisa.gov/scuba",
]

_STALE_DAYS = 90
_CREEP_THRESHOLD = 5


def analyse_exclusions(context: AuditContext) -> list[Finding]:
    """Run every exclusion-hygiene check across every policy in the context.

    Emits findings for stale (90+ days inactive) excluded users, orphaned
    exclusions on disabled accounts, admin-MFA-bypass exclusions, exclusion
    creep (more than five excluded principals), and undocumented exclusions
    whose policy display name carries no break-glass keyword.
    """

    findings: list[Finding] = []
    for policy in context.policies:
        if not _has_exclusions(policy):
            continue
        principals = resolve_excluded_principals(
            policy,
            context.users,
            context.groups,
            context.roles,
            context.role_assignments,
        )

        for principal in principals:
            stale = _check_stale(principal, context)
            if stale is not None:
                findings.append(stale)
            orphan = _check_orphan(principal, context)
            if orphan is not None:
                findings.append(orphan)
            admin_bypass = _check_admin_mfa_bypass(principal, policy, context)
            if admin_bypass is not None:
                findings.append(admin_bypass)

        if _direct_excluded_count(policy) > _CREEP_THRESHOLD:
            findings.append(_creep_finding(policy, context))

        if not _is_documented_exclusion(policy):
            findings.append(_undocumented_finding(policy, context))

    return findings


def _has_exclusions(policy: ConditionalAccessPolicy) -> bool:
    cond = policy.conditions.users if policy.conditions is not None else None
    if cond is None:
        return False
    return bool(cond.exclude_users or cond.exclude_groups or cond.exclude_roles)


def _direct_excluded_count(policy: ConditionalAccessPolicy) -> int:
    cond = policy.conditions.users if policy.conditions is not None else None
    if cond is None or cond.exclude_users is None:
        return 0
    return len(cond.exclude_users)


def _check_stale(principal: ResolvedPrincipal, context: AuditContext) -> Finding | None:
    activity = principal.user.sign_in_activity
    if activity is None or activity.last_sign_in_date_time is None:
        last_seen: object = "never"
        days_since = None
    else:
        delta = context.as_of - activity.last_sign_in_date_time
        if delta.days < _STALE_DAYS:
            return None
        last_seen = activity.last_sign_in_date_time.isoformat()
        days_since = delta.days
    rule_id = "exclusion.stale-user"
    affected = [
        AffectedObject(type="user", id=principal.user.id, display_name=_display(principal.user)),
        AffectedObject(
            type="policy",
            id=principal.excluded_from_policy_id,
            display_name=principal.excluded_from_policy_id,
        ),
    ]
    summary = (
        f"User '{_display(principal.user)}' is excluded from policy "
        f"{principal.excluded_from_policy_id} but has not signed in for "
        f"{_STALE_DAYS}+ days."
    )
    evidence: dict[str, Any] = {
        "user_id": principal.user.id,
        "policy_id": principal.excluded_from_policy_id,
        "excluded_via": principal.excluded_via,
        "via_object_id": principal.via_object_id,
        "last_sign_in": last_seen,
        "days_since_sign_in": days_since,
        "stale_days_threshold": _STALE_DAYS,
    }
    return _make(
        rule_id=rule_id,
        title="Stale user exclusion",
        severity=Severity.MEDIUM,
        affected=affected,
        summary=summary,
        evidence=evidence,
        remediation_hint=(
            "If the user is no longer required, remove them from the exclusion "
            "list and disable the account. Otherwise document the exception in "
            "the policy description."
        ),
        context=context,
    )


def _check_orphan(principal: ResolvedPrincipal, context: AuditContext) -> Finding | None:
    if principal.user.account_enabled is None or principal.user.account_enabled:
        return None
    rule_id = "exclusion.orphan-user"
    affected = [
        AffectedObject(type="user", id=principal.user.id, display_name=_display(principal.user)),
        AffectedObject(
            type="policy",
            id=principal.excluded_from_policy_id,
            display_name=principal.excluded_from_policy_id,
        ),
    ]
    summary = (
        f"Disabled user '{_display(principal.user)}' is still excluded from "
        f"policy {principal.excluded_from_policy_id}."
    )
    evidence: dict[str, Any] = {
        "user_id": principal.user.id,
        "policy_id": principal.excluded_from_policy_id,
        "excluded_via": principal.excluded_via,
        "account_enabled": principal.user.account_enabled,
    }
    return _make(
        rule_id=rule_id,
        title="Orphan exclusion: account disabled",
        severity=Severity.HIGH,
        affected=affected,
        summary=summary,
        evidence=evidence,
        remediation_hint=("Remove the disabled user from the policy's exclusion list."),
        context=context,
    )


def _check_admin_mfa_bypass(
    principal: ResolvedPrincipal,
    excluding_policy: ConditionalAccessPolicy,
    context: AuditContext,
) -> Finding | None:
    if not _enforces_mfa(excluding_policy):
        return None
    if not (set(principal.current_role_assignments) & _PRIVILEGED_ROLE_TEMPLATE_IDS):
        return None
    if _has_alternate_mfa_coverage(principal.user.id, context.policies, excluding_policy.id):
        return None
    rule_id = "exclusion.admin-mfa-bypass"
    affected = [
        AffectedObject(type="user", id=principal.user.id, display_name=_display(principal.user)),
        AffectedObject(
            type="policy",
            id=excluding_policy.id,
            display_name=excluding_policy.display_name,
        ),
    ]
    summary = (
        f"Privileged user '{_display(principal.user)}' is excluded from MFA "
        f"policy '{excluding_policy.display_name}' with no alternate MFA "
        "coverage detected."
    )
    evidence: dict[str, Any] = {
        "user_id": principal.user.id,
        "policy_id": excluding_policy.id,
        "current_role_assignments": principal.current_role_assignments,
        "excluded_via": principal.excluded_via,
    }
    return _make(
        rule_id=rule_id,
        title="Privileged user excluded from MFA policy",
        severity=Severity.CRITICAL,
        affected=affected,
        summary=summary,
        evidence=evidence,
        remediation_hint=(
            "Either remove the user from the exclusion list, or add an "
            "explicit MFA policy that covers them outside the original."
        ),
        context=context,
    )


def _creep_finding(policy: ConditionalAccessPolicy, context: AuditContext) -> Finding:
    cond = policy.conditions.users if policy.conditions is not None else None
    excluded = list(cond.exclude_users or []) if cond is not None else []
    return _make(
        rule_id="exclusion.creep",
        title="Exclusion list growing",
        severity=Severity.LOW,
        affected=[AffectedObject(type="policy", id=policy.id, display_name=policy.display_name)],
        summary=(
            f"Policy '{policy.display_name}' excludes {len(excluded)} users; "
            f"more than {_CREEP_THRESHOLD} indicates exclusion creep."
        ),
        evidence={
            "policy_id": policy.id,
            "excluded_user_count": len(excluded),
            "threshold": _CREEP_THRESHOLD,
            "excluded_user_ids": excluded,
        },
        remediation_hint=(
            "Review each exclusion. Move legitimate ones to a documented group; remove the rest."
        ),
        context=context,
    )


def _undocumented_finding(policy: ConditionalAccessPolicy, context: AuditContext) -> Finding:
    return _make(
        rule_id="exclusion.undocumented",
        title="Undocumented exclusion",
        severity=Severity.LOW,
        affected=[AffectedObject(type="policy", id=policy.id, display_name=policy.display_name)],
        summary=(
            f"Policy '{policy.display_name}' has exclusions but no keyword in "
            "displayName signalling intent."
        ),
        evidence={
            "policy_id": policy.id,
            "display_name": policy.display_name,
            "expected_keywords": list(_DOC_KEYWORDS),
        },
        remediation_hint=(
            "Rename the policy or add a description that includes one of "
            "'exclude', 'exception', 'break-glass', 'service account', or "
            "'bypass' so reviewers can grasp intent at a glance."
        ),
        context=context,
    )


def _enforces_mfa(policy: ConditionalAccessPolicy) -> bool:
    if policy.state != "enabled":
        return False
    grant = policy.grant_controls
    if grant is None or grant.built_in_controls is None:
        return False
    return "mfa" in grant.built_in_controls


def _has_alternate_mfa_coverage(
    user_id: str,
    policies: list[ConditionalAccessPolicy],
    exclude_policy_id: str,
) -> bool:
    """True if some other enabled MFA policy covers ``user_id``.

    Conservative quick check: looks for an All-users MFA policy that does not
    directly exclude this user. Group/role exclusions are not deeply resolved
    here because the analyser only needs a defensible "user is covered
    somewhere else" signal, not a full coverage proof.
    """
    for policy in policies:
        if policy.id == exclude_policy_id:
            continue
        if not _enforces_mfa(policy):
            continue
        cond = policy.conditions.users if policy.conditions is not None else None
        if cond is None or cond.include_users != ["All"]:
            continue
        if cond.exclude_users and user_id in cond.exclude_users:
            continue
        return True
    return False


def _is_documented_exclusion(policy: ConditionalAccessPolicy) -> bool:
    haystack = (policy.display_name or "").lower()
    return any(kw in haystack for kw in _DOC_KEYWORDS)


def _display(user: User) -> str:
    return user.display_name or user.user_principal_name or user.id


def _make(
    rule_id: str,
    title: str,
    severity: Severity,
    affected: list[AffectedObject],
    summary: str,
    evidence: dict[str, Any],
    remediation_hint: str,
    context: AuditContext,
) -> Finding:
    affected_ids = [o.id for o in affected]
    return Finding(
        id=Finding.compute_id(context.tenant_id, rule_id, affected_ids),
        tenant_id=context.tenant_id,
        rule_id=rule_id,
        category="exclusion",
        severity=severity,
        title=title,
        summary=summary,
        affected_objects=affected,
        evidence=evidence,
        remediation_hint=remediation_hint,
        references=_REFERENCES_BASE,
        detected_at=context.as_of,
        first_seen_at=context.as_of,
    )
