from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_coverage.app_segments import AppSegment
from cstack_audit_coverage.matrix import CoverageCell, CoverageMatrix, ProtectionLevel
from cstack_audit_coverage.segments import UserSegment

_REFERENCES: list[str] = [
    "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/concept-conditional-access-policy-common",
    "https://www.cisa.gov/scuba",
    "https://www.cisecurity.org/benchmark/microsoft_365",
]

_SENSITIVE_APP_SEGMENTS = frozenset(
    {AppSegment.M365_CORE, AppSegment.ADMIN_PORTALS, AppSegment.HIGH_RISK_APPS}
)


def findings_from_coverage(matrix: CoverageMatrix, tenant_id: str) -> list[Finding]:
    """Translate weak coverage cells into Finding records."""
    findings: list[Finding] = []
    for cell in matrix.cells:
        finding = _cell_to_finding(cell, tenant_id, matrix.computed_at)
        if finding is not None:
            findings.append(finding)
    return findings


def _cell_to_finding(cell: CoverageCell, tenant_id: str, now: object) -> Finding | None:
    severity = _severity_for_cell(cell)
    if severity is None:
        return None
    rule_id = f"coverage.{cell.user_segment.value}-on-{cell.app_segment.value}"
    affected: list[AffectedObject] = []
    if cell.applicable_policy_ids:
        affected.extend(
            AffectedObject(type="policy", id=pid, display_name=pid)
            for pid in cell.applicable_policy_ids
        )
    else:
        affected.append(AffectedObject(type="tenant", id=tenant_id, display_name=tenant_id))
    affected_ids = [a.id for a in affected]
    title = (
        f"{cell.user_segment.value} unprotected on {cell.app_segment.value}"
        if cell.protection_level == ProtectionLevel.NONE
        else f"{cell.user_segment.value} only in report-only on {cell.app_segment.value}"
    )
    summary = _summary_for_cell(cell)
    evidence: dict[str, object] = {
        "user_segment": cell.user_segment.value,
        "app_segment": cell.app_segment.value,
        "protection_level": cell.protection_level.name,
        "applicable_policy_ids": list(cell.applicable_policy_ids),
        "segment_member_count": cell.member_count,
    }
    return Finding(
        id=Finding.compute_id(tenant_id, rule_id, affected_ids),
        tenant_id=tenant_id,
        rule_id=rule_id,
        category="coverage",
        severity=severity,
        title=title,
        summary=summary,
        affected_objects=affected,
        evidence=evidence,
        remediation_hint=_remediation_for_cell(cell),
        references=_REFERENCES,
        detected_at=now,  # type: ignore[arg-type]
        first_seen_at=now,  # type: ignore[arg-type]
    )


def _severity_for_cell(cell: CoverageCell) -> Severity | None:
    """Decide severity for a cell, or None when the cell needs no finding."""
    level = cell.protection_level
    if level >= ProtectionLevel.MFA:
        return None
    if level == ProtectionLevel.COMPLIANT_DEVICE:
        # Device-only without MFA is a partial gap; rules layer surfaces this.
        return None

    if cell.member_count == 0 and cell.user_segment is not UserSegment.ALL_USERS:
        # No members means the segment is empty in this tenant; do not flag.
        return None

    is_report_only = level == ProtectionLevel.REPORT_ONLY
    segment = cell.user_segment
    app = cell.app_segment

    if segment is UserSegment.PRIVILEGED_ROLES:
        return Severity.HIGH if is_report_only else Severity.CRITICAL

    if segment is UserSegment.ADMINS_ANY:
        if app in {AppSegment.M365_CORE, AppSegment.ADMIN_PORTALS}:
            return Severity.HIGH if is_report_only else Severity.CRITICAL
        return Severity.MEDIUM if is_report_only else Severity.HIGH

    if segment is UserSegment.ALL_USERS:
        if app in {AppSegment.M365_CORE, AppSegment.LEGACY_AUTH}:
            return Severity.MEDIUM if is_report_only else Severity.HIGH
        return Severity.LOW if is_report_only else Severity.MEDIUM

    if segment is UserSegment.GUESTS and app in _SENSITIVE_APP_SEGMENTS:
        return Severity.MEDIUM if is_report_only else Severity.HIGH

    if segment is UserSegment.SERVICE_ACCOUNTS:
        # Service accounts are often intentionally excluded from interactive
        # MFA. Surface as MEDIUM at most so the audit is not noisy.
        return Severity.LOW if is_report_only else Severity.MEDIUM

    return Severity.LOW if is_report_only else Severity.MEDIUM


def _summary_for_cell(cell: CoverageCell) -> str:
    if cell.protection_level == ProtectionLevel.NONE:
        return (
            f"No enabled CA policy enforces a grant control for "
            f"{cell.user_segment.value} accessing {cell.app_segment.value}."
        )
    return (
        f"Only report-only CA policies cover {cell.user_segment.value} on "
        f"{cell.app_segment.value}; nothing is enforced today."
    )


def _remediation_for_cell(cell: CoverageCell) -> str:
    if cell.user_segment is UserSegment.PRIVILEGED_ROLES:
        return (
            "Add an enabled CA policy that requires MFA plus compliant device for "
            "privileged role members; verify break-glass exclusions are documented."
        )
    if cell.user_segment is UserSegment.ADMINS_ANY:
        return (
            "Add an enabled CA policy targeting Microsoft Entra admin role members "
            "with MFA as a minimum grant control."
        )
    if cell.app_segment is AppSegment.LEGACY_AUTH:
        return (
            "Add an enabled CA policy that blocks clientAppTypes 'other' and "
            "'exchangeActiveSync' for the affected user segment."
        )
    return (
        "Promote any report-only policy covering this segment to enabled, or add "
        "a new enabled policy with MFA as a minimum control."
    )
