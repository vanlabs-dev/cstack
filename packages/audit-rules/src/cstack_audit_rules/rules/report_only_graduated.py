from datetime import timedelta

from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules._helpers import ensure_utc, is_report_only
from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.report-only-graduated",
    title="Report-only policy never graduated",
    severity=Severity.LOW,
    description=(
        "Report-only policies left in place for more than 180 days are likely "
        "abandoned and should either be enabled or removed."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/concept-conditional-access-report-only",
    ],
    remediation_hint=(
        "Review each report-only policy and either enable, delete, or refresh "
        "the modifiedDateTime if it is still being assessed."
    ),
)

_STALE_DAYS = 180


def _evaluate(context: AuditContext) -> list[Finding]:
    findings: list[Finding] = []
    threshold = context.as_of - timedelta(days=_STALE_DAYS)
    for policy in context.policies:
        if not is_report_only(policy):
            continue
        modified = policy.modified_date_time
        if modified is None or ensure_utc(modified) < threshold:
            findings.append(
                make_finding(
                    METADATA,
                    tenant_id=context.tenant_id,
                    affected_objects=[
                        AffectedObject(
                            type="policy", id=policy.id, display_name=policy.display_name
                        )
                    ],
                    summary=(
                        f"Report-only policy '{policy.display_name}' has not been "
                        f"updated in {_STALE_DAYS}+ days."
                    ),
                    evidence={
                        "policy_id": policy.id,
                        "modified_date_time": modified.isoformat() if modified else None,
                        "stale_days_threshold": _STALE_DAYS,
                    },
                    as_of=context.as_of,
                )
            )
    return findings


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
