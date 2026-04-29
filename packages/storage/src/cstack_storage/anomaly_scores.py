import json
from datetime import datetime
from typing import Any

import duckdb
from cstack_audit_core import AnomalyScore, ShapFeatureContribution


def write_scores(conn: duckdb.DuckDBPyConnection, scores: list[AnomalyScore]) -> int:
    """Insert anomaly scores. Composite PK on (tenant, signin, model, version)
    means rerunning the same model on the same signin replaces the row."""
    if not scores:
        return 0
    rows: list[tuple[object, ...]] = []
    for s in scores:
        rows.append(
            (
                s.tenant_id,
                s.signin_id,
                s.user_id,
                s.model_name,
                s.model_version,
                s.raw_score,
                s.normalised_score,
                s.is_anomaly,
                json.dumps([f.model_dump() for f in s.shap_top_features]),
                s.scored_at,
                s.model_tier,
            )
        )
    conn.executemany(
        """
        INSERT OR REPLACE INTO anomaly_scores (
            tenant_id, signin_id, user_id, model_name, model_version,
            raw_score, normalised_score, is_anomaly, shap_top_features, scored_at,
            model_tier
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def get_scores(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    user_id: str | None = None,
    model_name: str | None = None,
    min_score: float | None = None,
    since: datetime | None = None,
) -> list[AnomalyScore]:
    """Filtered read of anomaly_scores. Each filter is an AND clause."""
    sql_parts = [
        """
        SELECT tenant_id, signin_id, user_id, model_name, model_version,
               raw_score, normalised_score, is_anomaly, shap_top_features, scored_at,
               model_tier
        FROM anomaly_scores WHERE tenant_id = ?
        """
    ]
    params: list[Any] = [tenant_id]
    if user_id is not None:
        sql_parts.append(" AND user_id = ?")
        params.append(user_id)
    if model_name is not None:
        sql_parts.append(" AND model_name = ?")
        params.append(model_name)
    if min_score is not None:
        sql_parts.append(" AND normalised_score >= ?")
        params.append(min_score)
    if since is not None:
        sql_parts.append(" AND scored_at >= ?")
        params.append(since)
    sql_parts.append(" ORDER BY scored_at DESC")
    rows = conn.execute("".join(sql_parts), params).fetchall()
    return [_row_to_score(row) for row in rows]


def latest_anomalies(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    n: int = 50,
    model_name: str | None = None,
) -> list[AnomalyScore]:
    """Top N most recent rows where ``is_anomaly`` is true. Default 50."""
    sql_parts = [
        """
        SELECT tenant_id, signin_id, user_id, model_name, model_version,
               raw_score, normalised_score, is_anomaly, shap_top_features, scored_at,
               model_tier
        FROM anomaly_scores WHERE tenant_id = ? AND is_anomaly = TRUE
        """
    ]
    params: list[Any] = [tenant_id]
    if model_name is not None:
        sql_parts.append(" AND model_name = ?")
        params.append(model_name)
    sql_parts.append(" ORDER BY normalised_score DESC, scored_at DESC LIMIT ?")
    params.append(n)
    rows = conn.execute("".join(sql_parts), params).fetchall()
    return [_row_to_score(row) for row in rows]


def _row_to_score(row: tuple[Any, ...]) -> AnomalyScore:
    return AnomalyScore(
        tenant_id=row[0],
        signin_id=row[1],
        user_id=row[2],
        model_name=row[3],
        model_version=row[4],
        raw_score=row[5],
        normalised_score=row[6],
        is_anomaly=row[7],
        shap_top_features=[ShapFeatureContribution.model_validate(f) for f in json.loads(row[8])],
        scored_at=row[9],
        model_tier=row[10] if len(row) > 10 else "unknown",
    )
