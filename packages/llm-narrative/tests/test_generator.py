from __future__ import annotations

import asyncio

import duckdb
import pytest
from cstack_audit_core import Finding
from cstack_llm_narrative import (
    BudgetExceededError,
    NarrativeBudget,
    NarrativeGenerator,
    NarrativeValidationError,
)
from cstack_llm_provider import LlmRequest, LlmResponse

VALID_NARRATIVE = """## Why this fired
The tenant has no enabled conditional access policy that blocks legacy
authentication clients. Evidence shows zero matching policies.

## What it means
Legacy authentication bypasses MFA and is the most common path attackers
use to land valid credentials in modern phishing campaigns.

## Remediation
1. Open the Entra portal and create a CA policy targeting all users.
2. Set client app types to legacy auth (other, exchangeActiveSync).
3. Set grant controls to block.
4. Enable the policy after a 24-hour report-only soak.

## Caveats
A small population of headless service accounts may still need legacy
auth; exclude them via a named group rather than disabling the policy.
"""


class _RecordingProvider:
    name = "anthropic"

    def __init__(
        self,
        responses: list[str],
        input_tokens: int = 100,
        output_tokens: int = 200,
    ) -> None:
        self._responses = list(responses)
        self.calls: list[LlmRequest] = []
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens

    async def complete(self, request: LlmRequest) -> LlmResponse:
        self.calls.append(request)
        if not self._responses:
            raise RuntimeError("no scripted responses left")
        content = self._responses.pop(0)
        return LlmResponse(
            content=content,
            model=request.model,
            provider=self.name,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            latency_ms=10,
            finish_reason="stop",
            raw={},
        )

    async def count_tokens(self, text: str, model: str) -> int:
        return len(text)

    def supported_models(self) -> list[str]:
        return ["claude-opus-4-7"]


@pytest.mark.asyncio
async def test_generate_writes_narrative_and_caches(
    db: duckdb.DuckDBPyConnection, finding: Finding
) -> None:
    provider = _RecordingProvider([VALID_NARRATIVE])
    gen = NarrativeGenerator(provider, db)
    narrative = await gen.generate(finding)
    assert narrative.cached is False
    assert "## Why this fired" in narrative.markdown
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_second_call_hits_cache(db: duckdb.DuckDBPyConnection, finding: Finding) -> None:
    provider = _RecordingProvider([VALID_NARRATIVE])
    gen = NarrativeGenerator(provider, db)
    await gen.generate(finding)
    second = await gen.generate(finding)
    assert second.cached is True
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_force_bypasses_cache(db: duckdb.DuckDBPyConnection, finding: Finding) -> None:
    provider = _RecordingProvider([VALID_NARRATIVE, VALID_NARRATIVE])
    gen = NarrativeGenerator(provider, db)
    await gen.generate(finding)
    forced = await gen.generate(finding, force=True)
    assert forced.cached is False
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_validation_failure_triggers_retry(
    db: duckdb.DuckDBPyConnection, finding: Finding
) -> None:
    provider = _RecordingProvider(["short reply with no headings", VALID_NARRATIVE])
    gen = NarrativeGenerator(provider, db)
    narrative = await gen.generate(finding)
    assert narrative.cached is False
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_validation_failure_twice_raises(
    db: duckdb.DuckDBPyConnection, finding: Finding
) -> None:
    provider = _RecordingProvider(["bad 1", "bad 2"])
    gen = NarrativeGenerator(provider, db)
    with pytest.raises(NarrativeValidationError):
        await gen.generate(finding)


@pytest.mark.asyncio
async def test_em_dash_fails_validation(db: duckdb.DuckDBPyConnection, finding: Finding) -> None:
    em_dash = chr(0x2014)
    bad = VALID_NARRATIVE.replace(
        "headless service accounts",
        em_dash + " headless service accounts",
    )
    assert em_dash in bad
    provider = _RecordingProvider([bad, "still bad"])
    gen = NarrativeGenerator(provider, db)
    with pytest.raises(NarrativeValidationError):
        await gen.generate(finding)


@pytest.mark.asyncio
async def test_budget_exhaustion_raises(db: duckdb.DuckDBPyConnection, finding: Finding) -> None:
    provider = _RecordingProvider([VALID_NARRATIVE])
    budget = NarrativeBudget(max_dollars=0.0)
    gen = NarrativeGenerator(provider, db, budget=budget)
    with pytest.raises(BudgetExceededError):
        await gen.generate(finding)
    assert budget.skipped_count == 1


@pytest.mark.asyncio
async def test_generate_batch_aggregates_outcomes(
    db: duckdb.DuckDBPyConnection, finding: Finding
) -> None:
    provider = _RecordingProvider([VALID_NARRATIVE, VALID_NARRATIVE])
    gen = NarrativeGenerator(provider, db)

    # Same finding twice: one generate, one cache hit.
    result = await gen.generate_batch([finding, finding])
    assert result.cache_hits + result.generated == 2
    assert result.cache_hits >= 1
    assert result.errored == 0


@pytest.mark.asyncio
async def test_generate_batch_records_skipped_under_budget(
    db: duckdb.DuckDBPyConnection, finding: Finding
) -> None:
    provider = _RecordingProvider([VALID_NARRATIVE, VALID_NARRATIVE])
    budget = NarrativeBudget(max_dollars=0.0)
    gen = NarrativeGenerator(provider, db, budget=budget)
    result = await gen.generate_batch([finding])
    assert result.skipped_budget == 1
    assert result.generated == 0


def test_estimate_cost_unknown_model_returns_zero() -> None:
    from cstack_llm_narrative import estimate_cost_usd

    assert estimate_cost_usd("not-a-real-model", 1000, 1000) == 0.0


def test_budget_remaining_clamps_at_zero() -> None:
    budget = NarrativeBudget(max_dollars=1.0)
    budget.record(1.5)
    assert budget.remaining == 0.0


def test_concurrent_generate_batch_does_not_exceed_semaphore(
    db: duckdb.DuckDBPyConnection, finding: Finding
) -> None:
    # Sanity: with concurrency=2, scripted provider returns deterministic
    # results; we just verify the call shape doesn't deadlock on the same
    # cache key being hit twice.
    provider = _RecordingProvider([VALID_NARRATIVE])
    gen = NarrativeGenerator(provider, db, max_concurrency=2)
    result = asyncio.run(gen.generate_batch([finding, finding]))
    assert result.errored == 0
