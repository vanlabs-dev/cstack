"""Translate AnomalyScore rows into Finding rows for the audit findings table."""

from __future__ import annotations

from cstack_audit_core import AffectedObject, AnomalyScore, Finding, Severity

ANOMALY_REFERENCES = [
    "https://learn.microsoft.com/en-us/azure/active-directory/identity-protection/concept-identity-protection-risks",
    "https://www.cisa.gov/scuba",
]


def _severity_for_score(normalised_score: float) -> Severity:
    if normalised_score >= 0.95:
        return Severity.HIGH
    if normalised_score >= 0.85:
        return Severity.MEDIUM
    return Severity.LOW


def findings_from_anomalies(
    scores: list[AnomalyScore],
    tenant_id: str,
    threshold: float = 0.7,
) -> list[Finding]:
    """For each anomalous score above threshold, build a Finding."""
    findings: list[Finding] = []
    for score in scores:
        if score.normalised_score < threshold:
            continue
        rule_id = "anomaly.signin"
        affected = [
            AffectedObject(
                type="user",
                id=score.user_id,
                display_name=score.user_id,
            ),
        ]
        affected_ids = [score.signin_id]
        top = score.shap_top_features[:3]
        bullets = ", ".join(f"{f.feature_name}={f.feature_value:.2f} ({f.direction})" for f in top)
        findings.append(
            Finding(
                id=Finding.compute_id(tenant_id, rule_id, [score.signin_id]),
                tenant_id=tenant_id,
                rule_id=rule_id,
                category="anomaly",
                severity=_severity_for_score(score.normalised_score),
                title=f"Anomalous sign-in flagged for {score.user_id}",
                summary=(
                    f"Sign-in {score.signin_id} scored "
                    f"{score.normalised_score:.2f}; top contributors: "
                    f"{bullets or '(no SHAP attribution)'}"
                ),
                affected_objects=affected,
                evidence={
                    "signin_id": score.signin_id,
                    "raw_score": score.raw_score,
                    "normalised_score": score.normalised_score,
                    "model_name": score.model_name,
                    "model_version": score.model_version,
                    "shap_top_features": [c.model_dump() for c in top],
                    "affected_signin_ids": affected_ids,
                },
                remediation_hint=(
                    "Review the sign-in in the Entra portal; contact the user to "
                    "confirm authenticity; revoke the session token if the sign-in "
                    "is unfamiliar."
                ),
                references=ANOMALY_REFERENCES,
                detected_at=score.scored_at,
                first_seen_at=score.scored_at,
            )
        )
    return findings
