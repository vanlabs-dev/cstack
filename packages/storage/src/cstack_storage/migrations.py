from dataclasses import dataclass
from datetime import UTC, datetime

import duckdb


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        name="init_tenants",
        sql="""
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            client_id TEXT NOT NULL,
            cert_thumbprint TEXT NOT NULL,
            cert_subject TEXT NOT NULL,
            added_at TIMESTAMP NOT NULL,
            is_fixture BOOLEAN NOT NULL DEFAULT FALSE
        );
        """,
    ),
    Migration(
        version=2,
        name="raw_ingestions",
        sql="""
        CREATE TABLE IF NOT EXISTS raw_ingestions (
            tenant_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            ingested_at TIMESTAMP NOT NULL,
            raw_payload JSON NOT NULL,
            source_path TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_raw_ingestions_tenant_resource
            ON raw_ingestions (tenant_id, resource_type, ingested_at);
        """,
    ),
    Migration(
        version=3,
        name="ca_policies",
        sql="""
        CREATE TABLE IF NOT EXISTS ca_policies (
            tenant_id TEXT NOT NULL,
            id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            state TEXT,
            created_at TIMESTAMP,
            modified_at TIMESTAMP,
            conditions JSON,
            grant_controls JSON,
            session_controls JSON,
            ingested_at TIMESTAMP NOT NULL,
            PRIMARY KEY (tenant_id, id)
        );
        """,
    ),
    Migration(
        version=4,
        name="named_locations",
        sql="""
        CREATE TABLE IF NOT EXISTS named_locations (
            tenant_id TEXT NOT NULL,
            id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            location_type TEXT NOT NULL,
            ip_ranges JSON,
            countries JSON,
            is_trusted BOOLEAN,
            ingested_at TIMESTAMP NOT NULL,
            PRIMARY KEY (tenant_id, id)
        );
        """,
    ),
    Migration(
        version=5,
        name="directory_objects",
        sql="""
        CREATE TABLE IF NOT EXISTS users (
            tenant_id TEXT NOT NULL,
            id TEXT NOT NULL,
            display_name TEXT,
            user_principal_name TEXT,
            account_enabled BOOLEAN,
            user_type TEXT,
            sign_in_activity JSON,
            raw JSON,
            ingested_at TIMESTAMP NOT NULL,
            PRIMARY KEY (tenant_id, id)
        );
        CREATE TABLE IF NOT EXISTS groups (
            tenant_id TEXT NOT NULL,
            id TEXT NOT NULL,
            display_name TEXT,
            mail_enabled BOOLEAN,
            security_enabled BOOLEAN,
            members JSON,
            raw JSON,
            ingested_at TIMESTAMP NOT NULL,
            PRIMARY KEY (tenant_id, id)
        );
        CREATE TABLE IF NOT EXISTS directory_roles (
            tenant_id TEXT NOT NULL,
            id TEXT NOT NULL,
            display_name TEXT,
            description TEXT,
            role_template_id TEXT,
            members JSON,
            raw JSON,
            ingested_at TIMESTAMP NOT NULL,
            PRIMARY KEY (tenant_id, id)
        );
        CREATE TABLE IF NOT EXISTS role_assignments (
            tenant_id TEXT NOT NULL,
            id TEXT NOT NULL,
            principal_id TEXT,
            role_definition_id TEXT,
            directory_scope_id TEXT,
            raw JSON,
            ingested_at TIMESTAMP NOT NULL,
            PRIMARY KEY (tenant_id, id)
        );
        """,
    ),
    Migration(
        version=6,
        name="findings",
        sql="""
        CREATE TABLE IF NOT EXISTS findings (
            id VARCHAR PRIMARY KEY,
            tenant_id VARCHAR NOT NULL,
            rule_id VARCHAR NOT NULL,
            category VARCHAR NOT NULL,
            severity VARCHAR NOT NULL,
            title VARCHAR NOT NULL,
            summary VARCHAR NOT NULL,
            affected_objects JSON NOT NULL,
            evidence JSON NOT NULL,
            remediation_hint VARCHAR NOT NULL,
            "references" JSON NOT NULL,
            detected_at TIMESTAMP NOT NULL,
            first_seen_at TIMESTAMP NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_findings_tenant_category
            ON findings(tenant_id, category);
        CREATE INDEX IF NOT EXISTS idx_findings_tenant_severity
            ON findings(tenant_id, severity);
        CREATE INDEX IF NOT EXISTS idx_findings_tenant_rule
            ON findings(tenant_id, rule_id);
        """,
    ),
    Migration(
        version=7,
        name="signins",
        sql="""
        CREATE TABLE IF NOT EXISTS signins (
            tenant_id VARCHAR NOT NULL,
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            user_principal_name VARCHAR NOT NULL,
            created_date_time TIMESTAMP NOT NULL,
            app_id VARCHAR,
            app_display_name VARCHAR,
            client_app_used VARCHAR,
            ip_address VARCHAR,
            country_or_region VARCHAR,
            city VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            device_id VARCHAR,
            device_os VARCHAR,
            device_browser VARCHAR,
            device_is_managed BOOLEAN,
            device_is_compliant BOOLEAN,
            device_trust_type VARCHAR,
            error_code INTEGER,
            failure_reason VARCHAR,
            conditional_access_status VARCHAR,
            authentication_requirement VARCHAR,
            authentication_methods_used JSON,
            risk_level_aggregated VARCHAR,
            risk_level_during_signin VARCHAR,
            risk_state VARCHAR,
            is_interactive BOOLEAN,
            raw_payload JSON NOT NULL,
            ingested_at TIMESTAMP NOT NULL,
            PRIMARY KEY (tenant_id, id)
        );
        CREATE INDEX IF NOT EXISTS idx_signins_tenant_user
            ON signins(tenant_id, user_id);
        CREATE INDEX IF NOT EXISTS idx_signins_tenant_time
            ON signins(tenant_id, created_date_time);
        """,
    ),
    Migration(
        version=8,
        name="anomaly_scores",
        sql="""
        CREATE TABLE IF NOT EXISTS anomaly_scores (
            tenant_id VARCHAR NOT NULL,
            signin_id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            model_name VARCHAR NOT NULL,
            model_version VARCHAR NOT NULL,
            raw_score DOUBLE NOT NULL,
            normalised_score DOUBLE NOT NULL,
            is_anomaly BOOLEAN NOT NULL,
            shap_top_features JSON,
            scored_at TIMESTAMP NOT NULL,
            PRIMARY KEY (tenant_id, signin_id, model_name, model_version)
        );
        CREATE INDEX IF NOT EXISTS idx_anomaly_tenant_user
            ON anomaly_scores(tenant_id, user_id);
        CREATE INDEX IF NOT EXISTS idx_anomaly_tenant_time
            ON anomaly_scores(tenant_id, scored_at);
        CREATE INDEX IF NOT EXISTS idx_anomaly_isanom
            ON anomaly_scores(tenant_id, is_anomaly);
        """,
    ),
    Migration(
        version=9,
        name="narrative_cache",
        sql="""
        CREATE TABLE IF NOT EXISTS narrative_cache (
            cache_key VARCHAR PRIMARY KEY,
            rule_id VARCHAR NOT NULL,
            evidence_hash VARCHAR NOT NULL,
            prompt_version VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            model VARCHAR NOT NULL,
            narrative_markdown VARCHAR NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            latency_ms INTEGER NOT NULL,
            generated_at TIMESTAMP NOT NULL,
            last_used_at TIMESTAMP NOT NULL,
            use_count INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_narrative_rule
            ON narrative_cache(rule_id);
        CREATE INDEX IF NOT EXISTS idx_narrative_last_used
            ON narrative_cache(last_used_at);
        """,
    ),
    Migration(
        version=10,
        name="eval_runs",
        sql="""
        CREATE TABLE IF NOT EXISTS eval_runs (
            eval_id VARCHAR PRIMARY KEY,
            prompt_version VARCHAR NOT NULL,
            model VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            examples_evaluated INTEGER NOT NULL DEFAULT 0,
            mean_score DOUBLE,
            per_criterion_scores JSON,
            run_metadata JSON
        );
        CREATE INDEX IF NOT EXISTS idx_eval_runs_prompt
            ON eval_runs(prompt_version);
        CREATE TABLE IF NOT EXISTS eval_scores (
            eval_id VARCHAR NOT NULL,
            finding_id VARCHAR NOT NULL,
            criterion_name VARCHAR NOT NULL,
            score DOUBLE NOT NULL,
            justification VARCHAR NOT NULL,
            PRIMARY KEY (eval_id, finding_id, criterion_name)
        );
        CREATE INDEX IF NOT EXISTS idx_eval_scores_eval
            ON eval_scores(eval_id);
        """,
    ),
    Migration(
        version=11,
        name="anomaly_scores_model_tier",
        sql="""
        ALTER TABLE anomaly_scores ADD COLUMN model_tier VARCHAR DEFAULT 'unknown';
        UPDATE anomaly_scores SET model_tier = 'unknown' WHERE model_tier IS NULL;
        """,
    ),
)


def run_migrations(conn: duckdb.DuckDBPyConnection) -> list[int]:
    """Apply any not-yet-applied migrations, in version order.

    Returns the list of versions applied during this call so callers can log
    or display upgrade progress. Idempotent: re-running with no pending
    migrations is a no-op.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL
        );
        """
    )
    applied_rows = conn.execute("SELECT version FROM _migrations").fetchall()
    applied = {row[0] for row in applied_rows}
    just_applied: list[int] = []
    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        conn.execute(migration.sql)
        conn.execute(
            "INSERT INTO _migrations (version, name, applied_at) VALUES (?, ?, ?)",
            [migration.version, migration.name, datetime.now(UTC)],
        )
        just_applied.append(migration.version)
    return just_applied
