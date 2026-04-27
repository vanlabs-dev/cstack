from cstack_audit_coverage.app_segments import (
    ADMIN_PORTAL_APP_IDS,
    HIGH_RISK_APP_IDS,
    LEGACY_AUTH_CLIENT_APP_TYPES,
    M365_CORE_APP_IDS,
    AppSegment,
)
from cstack_audit_coverage.findings import findings_from_coverage
from cstack_audit_coverage.matrix import (
    CoverageCell,
    CoverageMatrix,
    ProtectionLevel,
    compute_coverage,
)
from cstack_audit_coverage.segments import (
    PRIVILEGED_ROLE_TEMPLATE_IDS,
    TIER_0_ROLE_TEMPLATE_IDS,
    UserSegment,
    is_service_account,
    resolve_segment_members,
)

__all__ = [
    "ADMIN_PORTAL_APP_IDS",
    "HIGH_RISK_APP_IDS",
    "LEGACY_AUTH_CLIENT_APP_TYPES",
    "M365_CORE_APP_IDS",
    "PRIVILEGED_ROLE_TEMPLATE_IDS",
    "TIER_0_ROLE_TEMPLATE_IDS",
    "AppSegment",
    "CoverageCell",
    "CoverageMatrix",
    "ProtectionLevel",
    "UserSegment",
    "compute_coverage",
    "findings_from_coverage",
    "is_service_account",
    "resolve_segment_members",
]
