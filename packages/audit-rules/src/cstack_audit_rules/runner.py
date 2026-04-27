import logging

from cstack_audit_core import Finding

from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import RULE_REGISTRY

LOG = logging.getLogger(__name__)


def run_all_rules(context: AuditContext) -> list[Finding]:
    """Execute every registered rule. A rule that throws is logged and the
    rest still run, so one buggy rule cannot blank the report."""
    findings: list[Finding] = []
    for rule_id, rule in RULE_REGISTRY.items():
        try:
            findings.extend(rule.evaluator(context))
        except Exception:
            LOG.exception("rule failed", extra={"rule_id": rule_id})
    return findings


def run_rule(rule_id: str, context: AuditContext) -> list[Finding]:
    """Execute a single rule by id. Raises KeyError if not registered."""
    rule = RULE_REGISTRY[rule_id]
    return rule.evaluator(context)
