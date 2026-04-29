"""Rubric definitions and aggregate scoring math."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RubricCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    weight: float = Field(ge=0.0)
    min_score: int = 1
    max_score: int = 5


class Rubric(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    description: str
    criteria: list[RubricCriterion]

    def criterion(self, name: str) -> RubricCriterion:
        for c in self.criteria:
            if c.name == name:
                return c
        raise KeyError(f"unknown criterion: {name}")


class CriterionScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    score: float
    justification: str


class RubricScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    criteria_scores: dict[str, CriterionScore]
    total: float
    judge_model: str

    def per_criterion_means(self) -> dict[str, float]:
        return {name: s.score for name, s in self.criteria_scores.items()}


def aggregate_score(rubric: Rubric, scores: dict[str, CriterionScore]) -> float:
    """Weighted-mean over criteria, normalised to a 0-100 scale.

    Each criterion's score occupies the [min, max] window declared by the
    rubric; we shift to [0, 1] then weight, sum, divide by total weight, and
    multiply by 100.
    """

    total_weight = sum(c.weight for c in rubric.criteria)
    if total_weight == 0:
        return 0.0
    weighted = 0.0
    for criterion in rubric.criteria:
        score = scores.get(criterion.name)
        if score is None:
            continue
        span = max(1, criterion.max_score - criterion.min_score)
        normalised = (score.score - criterion.min_score) / span
        weighted += normalised * criterion.weight
    return round((weighted / total_weight) * 100.0, 2)


NARRATIVE_QUALITY_RUBRIC = Rubric(
    id="narrative-quality-v1",
    description="Triage-grade narrative quality across five orthogonal axes.",
    criteria=[
        RubricCriterion(
            name="accuracy",
            description=(
                "Does the narrative correctly reflect the finding evidence and rule? "
                "Penalises hallucinations, invented evidence, or contradictions."
            ),
            weight=1.5,
        ),
        RubricCriterion(
            name="actionability",
            description=(
                "Can an engineer act on it? Penalises hedging, vague advice, "
                "and 'consider doing X' phrasing."
            ),
            weight=1.5,
        ),
        RubricCriterion(
            name="concision",
            description=(
                "Is it under 250 words and on-topic? Penalises padding, "
                "throat-clearing, and unrelated background."
            ),
            weight=1.0,
        ),
        RubricCriterion(
            name="format_compliance",
            description=(
                "Has all four required sections (Why this fired, What it means, "
                "Remediation, Caveats), sentence case headings, no em dashes."
            ),
            weight=1.0,
        ),
        RubricCriterion(
            name="tone",
            description=(
                "Triage-grade engineer voice. Penalises marketing tone, emoji, "
                "exclamation marks, hype adjectives like 'comprehensive' or "
                "'powerful'."
            ),
            weight=0.5,
        ),
    ],
)
