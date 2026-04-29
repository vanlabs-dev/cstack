from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest
from cstack_audit_core import AffectedObject, Finding, Severity
from cstack_llm_eval import (
    REFERENCE_PROMPT_VERSION,
    GoldenExample,
    LlmJudge,
    compare_prompts,
    load_golden_set,
    make_default_generator,
    run_pairwise_eval,
    run_pointwise_eval,
)
from cstack_llm_provider import LlmRequest, LlmResponse

VALID_NARRATIVE = """## Why this fired
A finding fired because evidence shows missing CA policy.

## What it means
Without protection attackers can land valid credentials.

## Remediation
1. Step one.
2. Step two.

## Caveats
Service accounts may need exclusions.
"""


class _DualProvider:
    """Returns narrative content when temperature > 0; returns judge JSON when temperature == 0."""

    name = "dual"

    def __init__(self, judge_score: int = 4) -> None:
        self._judge_score = judge_score

    async def complete(self, request: LlmRequest) -> LlmResponse:
        if request.temperature == 0.0:
            content = json.dumps(
                {
                    "scores": {
                        name: {"score": self._judge_score, "justification": "ok"}
                        for name in [
                            "accuracy",
                            "actionability",
                            "concision",
                            "format_compliance",
                            "tone",
                        ]
                    }
                }
            )
        else:
            content = VALID_NARRATIVE
        return LlmResponse(
            content=content,
            model=request.model,
            provider=self.name,
            input_tokens=10,
            output_tokens=20,
            latency_ms=1,
            finish_reason="stop",
            raw={},
        )

    async def count_tokens(self, text: str, model: str) -> int:
        return len(text)

    def supported_models(self) -> list[str]:
        return ["m"]


def _example(finding_id: str = "f-1") -> GoldenExample:
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    finding = Finding(
        id=finding_id,
        tenant_id="tenant-b",
        rule_id="rule.x",
        category="rule",
        severity=Severity.HIGH,
        title="t",
        summary="s",
        affected_objects=[AffectedObject(type="tenant", id="tenant-b", display_name="t-b")],
        evidence={"a": 1},
        remediation_hint="hint",
        references=[],
        detected_at=now,
        first_seen_at=now,
    )
    return GoldenExample(
        finding=finding,
        reference_narrative=VALID_NARRATIVE,
        scenario_notes="",
    )


@pytest.mark.asyncio
async def test_run_pointwise_eval_persists_results(db: duckdb.DuckDBPyConnection) -> None:
    provider = _DualProvider(judge_score=5)
    generator = make_default_generator(provider=provider, conn=db, budget_dollars=10.0)
    judge = LlmJudge(provider=provider, model="judge-stub")
    examples = [_example("f-1"), _example("f-2"), _example("f-3")]
    run = await run_pointwise_eval(
        prompt_version="v1",
        model="m",
        golden_set=examples,
        generator=generator,
        judge=judge,
        conn=db,
    )
    assert run.examples_evaluated == 3
    assert run.mean_score == 100.0
    rows = db.execute("SELECT count(*) FROM eval_runs WHERE eval_id = ?", [run.eval_id]).fetchone()
    assert rows is not None and int(rows[0]) == 1
    score_rows = db.execute(
        "SELECT count(*) FROM eval_scores WHERE eval_id = ?", [run.eval_id]
    ).fetchone()
    assert score_rows is not None and int(score_rows[0]) == 3 * 5


@pytest.mark.asyncio
async def test_run_pairwise_eval_returns_winrate(db: duckdb.DuckDBPyConnection) -> None:
    """Pairwise eval against the reference. The scripted provider returns the
    same narrative for both candidate (v1) and reference, so the judge will
    return whatever winner we script. Use a provider that returns 'tie' so
    result is statistically defensible.
    """

    class _PairwiseTieProvider:
        name = "pair-tie"

        async def complete(self, request: LlmRequest) -> LlmResponse:
            if request.temperature == 0.0:
                content = json.dumps({"winner": "tie", "reason": "indistinguishable"})
            else:
                content = VALID_NARRATIVE
            return LlmResponse(
                content=content,
                model=request.model,
                provider=self.name,
                input_tokens=1,
                output_tokens=1,
                latency_ms=1,
                finish_reason="stop",
                raw={},
            )

        async def count_tokens(self, text: str, model: str) -> int:
            return len(text)

        def supported_models(self) -> list[str]:
            return ["m"]

    provider = _PairwiseTieProvider()
    generator = make_default_generator(provider=provider, conn=db, budget_dollars=10.0)
    judge = LlmJudge(provider=provider, model="judge-stub")
    run = await run_pairwise_eval(
        prompt_version="v1",
        model="m",
        golden_set=[_example("f-1"), _example("f-2")],
        generator=generator,
        judge=judge,
    )
    assert run.pairwise_vs_reference_winrate == 0.5  # all ties


@pytest.mark.asyncio
async def test_compare_prompts_pairwise(db: duckdb.DuckDBPyConnection) -> None:
    """Compare reference vs reference: should always tie."""
    provider = _DualProvider(judge_score=4)
    generator = make_default_generator(provider=provider, conn=db, budget_dollars=10.0)

    class _AlwaysTie:
        name = "always-tie"

        async def complete(self, request: LlmRequest) -> LlmResponse:
            if request.temperature == 0.0:
                content = json.dumps({"winner": "tie", "reason": "same"})
            else:
                content = VALID_NARRATIVE
            return LlmResponse(
                content=content,
                model=request.model,
                provider=self.name,
                input_tokens=1,
                output_tokens=1,
                latency_ms=1,
                finish_reason="stop",
                raw={},
            )

        async def count_tokens(self, text: str, model: str) -> int:
            return len(text)

        def supported_models(self) -> list[str]:
            return ["m"]

    judge = LlmJudge(provider=_AlwaysTie(), model="judge-stub")
    result = await compare_prompts(
        version_a=REFERENCE_PROMPT_VERSION,
        version_b=REFERENCE_PROMPT_VERSION,
        model="m",
        golden_set=[_example("f-1"), _example("f-2")],
        generator=generator,
        judge=judge,
    )
    assert result.ties == 2
    assert result.winrate_b == 0.5


def test_load_golden_set_reads_json(tmp_path: Path) -> None:
    payload = [
        {
            "finding": _example().finding.model_dump(mode="json"),
            "reference_narrative": VALID_NARRATIVE,
            "scenario_notes": "test",
        }
    ]
    target = tmp_path / "golden.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    examples = load_golden_set(target)
    assert len(examples) == 1
    assert examples[0].scenario_notes == "test"
