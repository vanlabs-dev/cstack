from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.breakglass-configured",
    title="Break-glass account exclusions not configured",
    severity=Severity.HIGH,
    description=(
        "At least one CA policy should explicitly exclude a break-glass user "
        "or group so a tenant lockout caused by a CA misconfiguration is "
        "recoverable. The convention is to exclude a dedicated break-glass "
        "group from any policy that could deny admin access."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/roles/security-emergency-access",
    ],
    remediation_hint=(
        "Create a break-glass group containing two emergency accounts and "
        "exclude it from any CA policy that could otherwise lock you out."
    ),
)

_BREAKGLASS_KEYWORDS = ("break-glass", "breakglass", "emergency-access", "emergency access")


def _evaluate(context: AuditContext) -> list[Finding]:
    breakglass_group_ids = {
        g.id
        for g in context.groups
        if g.display_name and any(kw in g.display_name.lower() for kw in _BREAKGLASS_KEYWORDS)
    }
    has_breakglass_exclusion = False
    for policy in context.policies:
        cond = policy.conditions.users if policy.conditions is not None else None
        if cond is None:
            continue
        excluded_groups = set(cond.exclude_groups or [])
        excluded_users = set(cond.exclude_users or [])
        if excluded_groups & breakglass_group_ids:
            has_breakglass_exclusion = True
            break
        # Heuristic: any policy excluding at least one user is candidate
        # break-glass; require a matching group convention to count it.
        if excluded_users and breakglass_group_ids:
            has_breakglass_exclusion = True
            break

    if has_breakglass_exclusion:
        return []
    return [
        make_finding(
            METADATA,
            tenant_id=context.tenant_id,
            affected_objects=[
                AffectedObject(type="tenant", id=context.tenant_id, display_name="tenant")
            ],
            summary="No CA policy excludes a recognisable break-glass group.",
            evidence={"breakglass_groups_found": len(breakglass_group_ids)},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
