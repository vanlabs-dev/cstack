from __future__ import annotations

import json

import pytest
from cstack_audit_core import Finding
from cstack_llm_eval import (
    NARRATIVE_QUALITY_RUBRIC,
    JudgeError,
    LlmJudge,
)
from cstack_llm_provider import LlmRequest, LlmResponse


class _ScriptedProvider:
    name = "scripted"

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)

    async def complete(self, request: LlmRequest) -> LlmResponse:
        if not self._replies:
            raise RuntimeError("no scripted reply")
        content = self._replies.pop(0)
        return LlmResponse(
            content=content,
            model=request.model,
            provider=self.name,
            input_tokens=10,
            output_tokens=10,
            latency_ms=1,
            finish_reason="stop",
            raw={},
        )

    async def count_tokens(self, text: str, model: str) -> int:
        return len(text)

    def supported_models(self) -> list[str]:
        return ["scripted-judge"]


def _pointwise_response(score_value: int) -> str:
    body = {
        "scores": {
            c.name: {"score": score_value, "justification": "ok"}
            for c in NARRATIVE_QUALITY_RUBRIC.criteria
        }
    }
    return json.dumps(body)


@pytest.mark.asyncio
async def test_score_pointwise_aggregates_perfect_marks(finding: Finding) -> None:
    provider = _ScriptedProvider([_pointwise_response(5)])
    judge = LlmJudge(provider=provider, model="scripted-judge")
    score = await judge.score_pointwise(
        narrative="## Why this fired\nbody\n## What it means\nx\n## Remediation\n1.\n## Caveats\nx",
        finding=finding,
        rubric=NARRATIVE_QUALITY_RUBRIC,
    )
    assert score.total == 100.0
    assert set(score.criteria_scores.keys()) == {
        "accuracy",
        "actionability",
        "concision",
        "format_compliance",
        "tone",
    }


@pytest.mark.asyncio
async def test_score_pointwise_retries_on_malformed_json(finding: Finding) -> None:
    provider = _ScriptedProvider(["not even json", _pointwise_response(4)])
    judge = LlmJudge(provider=provider, model="scripted-judge")
    score = await judge.score_pointwise(
        narrative="x", finding=finding, rubric=NARRATIVE_QUALITY_RUBRIC
    )
    assert score.total > 0


@pytest.mark.asyncio
async def test_score_pointwise_raises_after_two_bad_responses(finding: Finding) -> None:
    provider = _ScriptedProvider(["nope", "nope again"])
    judge = LlmJudge(provider=provider, model="scripted-judge")
    with pytest.raises(JudgeError):
        await judge.score_pointwise(narrative="x", finding=finding, rubric=NARRATIVE_QUALITY_RUBRIC)


def _pairwise_response(winner: str) -> str:
    return json.dumps({"winner": winner, "reason": "test"})


@pytest.mark.asyncio
async def test_score_pairwise_consistent_winner(finding: Finding) -> None:
    # First pass picks a; swapped pass should also pick the same narrative
    # (which is now in slot b after the swap), so judge says "b" in second.
    provider = _ScriptedProvider([_pairwise_response("a"), _pairwise_response("b")])
    judge = LlmJudge(provider=provider, model="scripted-judge")
    result = await judge.score_pairwise(narrative_a="A text", narrative_b="B text", finding=finding)
    assert result.winner == "a"
    assert result.position_swap_consistent is True


@pytest.mark.asyncio
async def test_score_pairwise_inconsistent_returns_tie(finding: Finding) -> None:
    # First pass picks a; swapped pass also picks a — meaning the judge
    # preferred whichever narrative was in position A, regardless of content.
    # That's position bias; the result should be reported as tie.
    provider = _ScriptedProvider([_pairwise_response("a"), _pairwise_response("a")])
    judge = LlmJudge(provider=provider, model="scripted-judge")
    result = await judge.score_pairwise(narrative_a="A text", narrative_b="B text", finding=finding)
    assert result.winner == "tie"
    assert result.position_swap_consistent is False
