"""Content-addressed cache for finding narratives.

The cache key is a SHA-256 of ``(rule_id, canonicalised_evidence,
prompt_version, model)``. Two findings with identical rule + evidence reuse
the same narrative regardless of tenant, which is the highest-leverage
cost optimisation in the LLM pipeline.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import duckdb


@dataclass(frozen=True)
class CachedNarrative:
    """A row from the narrative_cache table.

    ``cache_key`` is the SHA-256 of ``(rule_id, canonicalised_evidence,
    prompt_version, model)``; identical findings across tenants share one
    entry. ``last_used_at`` and ``use_count`` drive LRU eviction.
    """

    cache_key: str
    rule_id: str
    evidence_hash: str
    prompt_version: str
    provider: str
    model: str
    narrative_markdown: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    generated_at: datetime
    last_used_at: datetime
    use_count: int = 1


@dataclass(frozen=True)
class CacheStats:
    """Aggregate counts from the narrative cache for the cache-stats CLI."""

    total_entries: int
    distinct_rules: int
    total_cached_output_tokens: int
    total_use_count: int
    oldest_entry: datetime | None
    newest_entry: datetime | None


def _canonical_evidence(evidence: dict[str, Any]) -> str:
    """Deterministic JSON for evidence dicts. ``sort_keys`` plus
    ``separators`` removes whitespace variability so equivalent dicts hash to
    the same value. Non-default JSON types are coerced to strings to keep the
    hash stable across pydantic versions that may change repr.
    """

    return json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str)


def hash_evidence(evidence: dict[str, Any]) -> str:
    """SHA-256 hex digest of an evidence dict via canonical JSON ordering."""
    return hashlib.sha256(_canonical_evidence(evidence).encode("utf-8")).hexdigest()


def compute_cache_key(
    rule_id: str,
    evidence: dict[str, Any],
    prompt_version: str,
    model: str,
) -> str:
    """SHA-256 of the four identity components that determine a narrative.

    Tenant id is intentionally omitted: the same rule firing on identical
    evidence in two tenants should produce identical narratives, and reusing
    the same cache entry is the whole point of content-addressing.
    """

    payload = f"{rule_id}|{hash_evidence(evidence)}|{prompt_version}|{model}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_cached_narrative(
    conn: duckdb.DuckDBPyConnection,
    cache_key: str,
) -> CachedNarrative | None:
    """Lookup a narrative by cache key. Bumps last_used_at and use_count on hit
    so eviction can rank by recency rather than just creation time.
    """

    row = conn.execute(
        """
        SELECT
            cache_key, rule_id, evidence_hash, prompt_version, provider, model,
            narrative_markdown, input_tokens, output_tokens, latency_ms,
            generated_at, last_used_at, use_count
        FROM narrative_cache
        WHERE cache_key = ?
        """,
        [cache_key],
    ).fetchone()
    if row is None:
        return None

    now = datetime.now(UTC)
    new_use_count = int(row[12]) + 1
    conn.execute(
        """
        UPDATE narrative_cache
        SET last_used_at = ?, use_count = ?
        WHERE cache_key = ?
        """,
        [now, new_use_count, cache_key],
    )
    return CachedNarrative(
        cache_key=row[0],
        rule_id=row[1],
        evidence_hash=row[2],
        prompt_version=row[3],
        provider=row[4],
        model=row[5],
        narrative_markdown=row[6],
        input_tokens=int(row[7]),
        output_tokens=int(row[8]),
        latency_ms=int(row[9]),
        generated_at=_ensure_utc(row[10]),
        last_used_at=now,
        use_count=new_use_count,
    )


def store_narrative(
    conn: duckdb.DuckDBPyConnection,
    cached: CachedNarrative,
) -> None:
    """Upsert a narrative into the cache. INSERT OR REPLACE so force-regenerate
    overwrites existing entries cleanly.
    """

    conn.execute(
        """
        INSERT OR REPLACE INTO narrative_cache (
            cache_key, rule_id, evidence_hash, prompt_version, provider, model,
            narrative_markdown, input_tokens, output_tokens, latency_ms,
            generated_at, last_used_at, use_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            cached.cache_key,
            cached.rule_id,
            cached.evidence_hash,
            cached.prompt_version,
            cached.provider,
            cached.model,
            cached.narrative_markdown,
            cached.input_tokens,
            cached.output_tokens,
            cached.latency_ms,
            cached.generated_at,
            cached.last_used_at,
            cached.use_count,
        ],
    )


def evict_old(conn: duckdb.DuckDBPyConnection, days: int = 90) -> int:
    """LRU-by-last-used eviction. Returns the number of rows removed.

    A simple cutoff over last_used_at is sufficient for V1: cache entries are
    cheap, and with content-addressing the hit rate is high enough that
    semantic dedup (V2) is not worth the engineering cost yet.
    """

    cutoff = datetime.now(UTC) - _days_to_delta(days)
    deleted = conn.execute(
        """
        DELETE FROM narrative_cache
        WHERE last_used_at < ?
        RETURNING cache_key
        """,
        [cutoff],
    ).fetchall()
    return len(deleted)


def cache_stats(conn: duckdb.DuckDBPyConnection) -> CacheStats:
    """Aggregate counters for the narrative cache (no per-entry breakdown)."""
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_entries,
            COUNT(DISTINCT rule_id) AS distinct_rules,
            COALESCE(SUM(output_tokens), 0) AS total_cached_output_tokens,
            COALESCE(SUM(use_count), 0) AS total_use_count,
            MIN(generated_at) AS oldest_entry,
            MAX(generated_at) AS newest_entry
        FROM narrative_cache
        """
    ).fetchone()
    if row is None:
        return CacheStats(0, 0, 0, 0, None, None)
    return CacheStats(
        total_entries=int(row[0]),
        distinct_rules=int(row[1]),
        total_cached_output_tokens=int(row[2]),
        total_use_count=int(row[3]),
        oldest_entry=_ensure_utc(row[4]) if row[4] is not None else None,
        newest_entry=_ensure_utc(row[5]) if row[5] is not None else None,
    )


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _days_to_delta(days: int) -> Any:
    from datetime import timedelta

    return timedelta(days=days)
