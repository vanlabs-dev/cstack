from __future__ import annotations

from cstack_llm_eval import (
    NARRATIVE_QUALITY_RUBRIC,
    CriterionScore,
    aggregate_score,
)


def test_rubric_has_five_named_criteria() -> None:
    names = [c.name for c in NARRATIVE_QUALITY_RUBRIC.criteria]
    assert names == [
        "accuracy",
        "actionability",
        "concision",
        "format_compliance",
        "tone",
    ]


def test_aggregate_score_with_perfect_marks_is_100() -> None:
    perfect = {
        c.name: CriterionScore(name=c.name, score=c.max_score, justification="ok")
        for c in NARRATIVE_QUALITY_RUBRIC.criteria
    }
    assert aggregate_score(NARRATIVE_QUALITY_RUBRIC, perfect) == 100.0


def test_aggregate_score_with_floor_marks_is_0() -> None:
    floor = {
        c.name: CriterionScore(name=c.name, score=c.min_score, justification="bad")
        for c in NARRATIVE_QUALITY_RUBRIC.criteria
    }
    assert aggregate_score(NARRATIVE_QUALITY_RUBRIC, floor) == 0.0


def test_aggregate_score_partial_returns_weighted_mean() -> None:
    # All-3s on a 1-5 scale with min=1, max=5 gives normalised 0.5; total = 50.
    halfway = {
        c.name: CriterionScore(name=c.name, score=3.0, justification="ok")
        for c in NARRATIVE_QUALITY_RUBRIC.criteria
    }
    assert aggregate_score(NARRATIVE_QUALITY_RUBRIC, halfway) == 50.0
