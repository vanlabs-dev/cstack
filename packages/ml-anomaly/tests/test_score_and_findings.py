from datetime import UTC, datetime

from cstack_audit_core import AnomalyScore, ShapFeatureContribution
from cstack_ml_anomaly import findings_from_anomalies, normalise_score


def test_normalise_score_monotonic() -> None:
    very_anomalous = normalise_score(-1.0)
    near_zero = normalise_score(0.0)
    very_normal = normalise_score(1.0)
    assert very_anomalous > near_zero > very_normal
    assert 0.0 < very_anomalous <= 1.0
    assert 0.0 <= very_normal < 0.5


def test_findings_severity_tiers() -> None:
    base = datetime(2026, 4, 28, tzinfo=UTC)
    scores = [
        AnomalyScore(
            tenant_id="t",
            signin_id="s-high",
            user_id="u1",
            model_name="m",
            model_version="1",
            raw_score=-1.0,
            normalised_score=0.96,
            is_anomaly=True,
            shap_top_features=[
                ShapFeatureContribution(
                    feature_name="is_new_asn_for_user",
                    feature_value=1.0,
                    shap_value=-0.4,
                    direction="pushes_anomalous",
                )
            ],
            scored_at=base,
        ),
        AnomalyScore(
            tenant_id="t",
            signin_id="s-mid",
            user_id="u1",
            model_name="m",
            model_version="1",
            raw_score=-0.5,
            normalised_score=0.88,
            is_anomaly=True,
            shap_top_features=[],
            scored_at=base,
        ),
        AnomalyScore(
            tenant_id="t",
            signin_id="s-low",
            user_id="u2",
            model_name="m",
            model_version="1",
            raw_score=-0.2,
            normalised_score=0.72,
            is_anomaly=True,
            shap_top_features=[],
            scored_at=base,
        ),
        AnomalyScore(
            tenant_id="t",
            signin_id="s-skip",
            user_id="u3",
            model_name="m",
            model_version="1",
            raw_score=0.5,
            normalised_score=0.30,
            is_anomaly=False,
            shap_top_features=[],
            scored_at=base,
        ),
    ]
    findings = findings_from_anomalies(scores, "t", threshold=0.7)
    assert len(findings) == 3
    sev_by_id = {f.evidence["signin_id"]: f.severity for f in findings}
    assert sev_by_id["s-high"].value == "HIGH"
    assert sev_by_id["s-mid"].value == "MEDIUM"
    assert sev_by_id["s-low"].value == "LOW"
    assert all(f.category == "anomaly" for f in findings)
