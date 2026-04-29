from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cstack_audit_core import AffectedObject, Finding, Severity
from pydantic import BaseModel, ConfigDict

from cstack_audit_rules.context import AuditContext

RuleEvaluator = Callable[[AuditContext], list[Finding]]


class RuleMetadata(BaseModel):
    """Static descriptor for a rule. Lives next to the evaluator function."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    severity: Severity
    description: str
    references: list[str]
    remediation_hint: str


@dataclass(frozen=True)
class Rule:
    """One CA audit rule: metadata + a pure evaluator function.

    Rules live in `packages/audit-rules/src/cstack_audit_rules/rules/`;
    each module instantiates a `Rule` and calls `register_rule` at import.
    """

    metadata: RuleMetadata
    evaluator: RuleEvaluator


# Module-level registry. Rule modules register themselves on import.
RULE_REGISTRY: dict[str, Rule] = {}


def register_rule(rule: Rule) -> None:
    """Add a rule to the module-level registry. Raises if id is duplicated."""
    if rule.metadata.id in RULE_REGISTRY:
        raise ValueError(f"rule already registered: {rule.metadata.id}")
    RULE_REGISTRY[rule.metadata.id] = rule


def make_finding(
    metadata: RuleMetadata,
    tenant_id: str,
    affected_objects: list[AffectedObject],
    summary: str,
    evidence: dict[str, Any],
    as_of: datetime,
) -> Finding:
    """Standard finding constructor used by every rule."""
    affected_ids = [o.id for o in affected_objects]
    return Finding(
        id=Finding.compute_id(tenant_id, metadata.id, affected_ids),
        tenant_id=tenant_id,
        rule_id=metadata.id,
        category="rule",
        severity=metadata.severity,
        title=metadata.title,
        summary=summary,
        affected_objects=affected_objects,
        evidence=evidence,
        remediation_hint=metadata.remediation_hint,
        references=metadata.references,
        detected_at=as_of,
        first_seen_at=as_of,
    )
