from datetime import UTC, datetime

import duckdb
from cstack_audit_core import AnomalyScore, ShapFeatureContribution
from cstack_storage import get_scores, latest_anomalies, write_scores

TENANT = "00000000-0000-0000-0000-bbbb00000001"


def _score(
    signin_id: str,
    user: str,
    score: float,
    is_anom: bool,
    when: datetime,
) -> AnomalyScore:
    return AnomalyScore(
        tenant_id=TENANT,
        signin_id=signin_id,
        user_id=user,
        model_name="signalguard-anomaly-pooled-test",
        model_version="1",
        raw_score=-0.1 if is_anom else 0.05,
        normalised_score=score,
        is_anomaly=is_anom,
        shap_top_features=[
            ShapFeatureContribution(
                feature_name="hours_since_last_signin",
                feature_value=72.0,
                shap_value=0.4,
                direction="pushes_anomalous",
            )
        ],
        scored_at=when,
    )


def test_write_then_read(db: duckdb.DuckDBPyConnection) -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
    scores = [
        _score("s1", "u1", 0.85, True, now),
        _score("s2", "u1", 0.20, False, now),
        _score("s3", "u2", 0.95, True, now),
    ]
    assert write_scores(db, scores) == 3

    fetched = get_scores(db, TENANT)
    assert len(fetched) == 3

    high = get_scores(db, TENANT, min_score=0.8)
    assert len(high) == 2


def test_latest_anomalies_filters_to_anomalies_only(db: duckdb.DuckDBPyConnection) -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
    write_scores(
        db,
        [
            _score("s1", "u1", 0.85, True, now),
            _score("s2", "u1", 0.20, False, now),
            _score("s3", "u2", 0.95, True, now),
        ],
    )
    anomalies = latest_anomalies(db, TENANT)
    assert len(anomalies) == 2
    # Sorted by normalised_score DESC.
    assert anomalies[0].normalised_score == 0.95


def test_rerun_replaces_row(db: duckdb.DuckDBPyConnection) -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
    write_scores(db, [_score("s1", "u1", 0.50, False, now)])
    write_scores(db, [_score("s1", "u1", 0.92, True, now)])
    rows = get_scores(db, TENANT)
    assert len(rows) == 1
    assert rows[0].is_anomaly is True
