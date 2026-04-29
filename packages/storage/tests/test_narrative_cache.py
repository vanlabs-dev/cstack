from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pytest
from cstack_storage import (
    CachedNarrative,
    cache_stats,
    compute_cache_key,
    evict_old,
    get_cached_narrative,
    hash_evidence,
    run_migrations,
    store_narrative,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    conn = duckdb.connect(str(tmp_path / "narrative.duckdb"))
    run_migrations(conn)
    try:
        yield conn
    finally:
        conn.close()


def test_compute_cache_key_is_deterministic_for_same_inputs() -> None:
    a = compute_cache_key("rule.x", {"k": 1, "b": [1, 2]}, "v1", "claude-opus-4-7")
    b = compute_cache_key("rule.x", {"b": [1, 2], "k": 1}, "v1", "claude-opus-4-7")
    assert a == b


def test_compute_cache_key_changes_when_any_input_changes() -> None:
    base = compute_cache_key("rule.x", {"k": 1}, "v1", "claude-opus-4-7")
    assert base != compute_cache_key("rule.y", {"k": 1}, "v1", "claude-opus-4-7")
    assert base != compute_cache_key("rule.x", {"k": 2}, "v1", "claude-opus-4-7")
    assert base != compute_cache_key("rule.x", {"k": 1}, "v2", "claude-opus-4-7")
    assert base != compute_cache_key("rule.x", {"k": 1}, "v1", "claude-sonnet-4-6")


def test_hash_evidence_canonicalises_key_order() -> None:
    h1 = hash_evidence({"a": 1, "b": 2})
    h2 = hash_evidence({"b": 2, "a": 1})
    assert h1 == h2


def test_storage_roundtrip_returns_identical_content(db: duckdb.DuckDBPyConnection) -> None:
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    cached = CachedNarrative(
        cache_key="key-1",
        rule_id="rule.block-legacy-auth",
        evidence_hash="evh",
        prompt_version="v1",
        provider="anthropic",
        model="claude-opus-4-7",
        narrative_markdown="## Why this fired\nbody",
        input_tokens=100,
        output_tokens=200,
        latency_ms=1500,
        generated_at=now,
        last_used_at=now,
        use_count=1,
    )
    store_narrative(db, cached)
    got = get_cached_narrative(db, "key-1")
    assert got is not None
    assert got.rule_id == "rule.block-legacy-auth"
    assert got.narrative_markdown == "## Why this fired\nbody"
    assert got.input_tokens == 100
    assert got.output_tokens == 200


def test_get_bumps_last_used_and_use_count(db: duckdb.DuckDBPyConnection) -> None:
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    cached = CachedNarrative(
        cache_key="key-2",
        rule_id="rule.x",
        evidence_hash="e",
        prompt_version="v1",
        provider="anthropic",
        model="m",
        narrative_markdown="x",
        input_tokens=1,
        output_tokens=1,
        latency_ms=1,
        generated_at=now,
        last_used_at=now,
        use_count=1,
    )
    store_narrative(db, cached)
    first = get_cached_narrative(db, "key-2")
    second = get_cached_narrative(db, "key-2")
    assert first is not None and second is not None
    # First lookup bumped 1 -> 2, second lookup bumped 2 -> 3.
    assert first.use_count == 2
    assert second.use_count == 3
    assert second.last_used_at >= first.last_used_at


def test_get_returns_none_for_missing_key(db: duckdb.DuckDBPyConnection) -> None:
    assert get_cached_narrative(db, "no-such-key") is None


def test_evict_old_removes_entries_older_than_cutoff(db: duckdb.DuckDBPyConnection) -> None:
    fresh = datetime.now(UTC)
    stale = fresh - timedelta(days=200)

    store_narrative(
        db,
        CachedNarrative(
            cache_key="fresh",
            rule_id="r",
            evidence_hash="e",
            prompt_version="v1",
            provider="p",
            model="m",
            narrative_markdown="x",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1,
            generated_at=fresh,
            last_used_at=fresh,
        ),
    )
    store_narrative(
        db,
        CachedNarrative(
            cache_key="stale",
            rule_id="r",
            evidence_hash="e",
            prompt_version="v1",
            provider="p",
            model="m",
            narrative_markdown="x",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1,
            generated_at=stale,
            last_used_at=stale,
        ),
    )

    deleted = evict_old(db, days=90)
    assert deleted == 1
    assert get_cached_narrative(db, "stale") is None
    assert get_cached_narrative(db, "fresh") is not None


def test_cache_stats_reports_aggregates(db: duckdb.DuckDBPyConnection) -> None:
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    for i in range(3):
        store_narrative(
            db,
            CachedNarrative(
                cache_key=f"k-{i}",
                rule_id="rule.a" if i < 2 else "rule.b",
                evidence_hash="e",
                prompt_version="v1",
                provider="anthropic",
                model="m",
                narrative_markdown="x",
                input_tokens=10,
                output_tokens=20,
                latency_ms=100,
                generated_at=now,
                last_used_at=now,
            ),
        )
    stats = cache_stats(db)
    assert stats.total_entries == 3
    assert stats.distinct_rules == 2
    assert stats.total_cached_output_tokens == 60
    assert stats.total_use_count == 3
    assert stats.oldest_entry is not None
