"""Top-level eval runner: pointwise scoring, pairwise comparison, and storage."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import duckdb
from cstack_audit_core import Finding
from cstack_llm_narrative import (
    DEFAULT_PROMPT_VERSION,
    NarrativeBudget,
    NarrativeGenerator,
)
from cstack_llm_provider import LlmProvider
from pydantic import BaseModel, ConfigDict, Field

from cstack_llm_eval.golden_set import GoldenExample
from cstack_llm_eval.judge import LlmJudge, PairwiseResult
from cstack_llm_eval.rubric import (
    NARRATIVE_QUALITY_RUBRIC,
    Rubric,
)

logger = logging.getLogger("cstack_llm_eval")

REFERENCE_PROMPT_VERSION = "reference"


class EvalRun(BaseModel):
    """Persisted record of one full eval pass over the golden set.

    Pointwise runs report aggregate quality across the rubric; pairwise runs
    report a single ``mean_score`` derived from winrate and a synthetic
    per-criterion-means dict carrying the winrate and inconsistency rate.
    """

    model_config = ConfigDict(frozen=True)

    eval_id: str
    prompt_version: str
    model: str
    provider: str
    started_at: datetime
    completed_at: datetime
    examples_evaluated: int
    mean_score: float
    per_criterion_means: dict[str, float]
    pairwise_vs_reference_winrate: float | None = None


class ComparisonResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_a: str
    version_b: str
    examples: int
    a_wins: int
    b_wins: int
    ties: int
    winrate_b: float = Field(description="Winrate of B against A; ties count as 0.5.")
    inconsistent_swaps: int


async def run_pointwise_eval(
    *,
    prompt_version: str,
    model: str,
    golden_set: list[GoldenExample],
    generator: NarrativeGenerator,
    judge: LlmJudge,
    conn: duckdb.DuckDBPyConnection | None = None,
    rubric: Rubric = NARRATIVE_QUALITY_RUBRIC,
) -> EvalRun:
    """Generate a candidate narrative for each golden example and score it
    against the rubric using the judge. Persists per-criterion scores to
    eval_scores when a connection is provided.
    """

    eval_id = str(uuid.uuid4())
    started = datetime.now(UTC)
    per_criterion: dict[str, list[float]] = {c.name: [] for c in rubric.criteria}
    totals: list[float] = []

    for example in golden_set:
        narrative_text = await _generate_or_reference(
            example=example,
            prompt_version=prompt_version,
            model=model,
            generator=generator,
        )
        score = await judge.score_pointwise(
            narrative=narrative_text, finding=example.finding, rubric=rubric
        )
        totals.append(score.total)
        for name, criterion_score in score.criteria_scores.items():
            per_criterion[name].append(criterion_score.score)
            if conn is not None:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO eval_scores
                    (eval_id, finding_id, criterion_name, score, justification)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        eval_id,
                        example.finding.id,
                        name,
                        criterion_score.score,
                        criterion_score.justification,
                    ],
                )

    mean_score = sum(totals) / len(totals) if totals else 0.0
    means: dict[str, float] = {
        name: (sum(values) / len(values)) if values else 0.0
        for name, values in per_criterion.items()
    }

    completed = datetime.now(UTC)
    if conn is not None:
        conn.execute(
            """
            INSERT OR REPLACE INTO eval_runs
            (eval_id, prompt_version, model, provider, started_at, completed_at,
             examples_evaluated, mean_score, per_criterion_scores, run_metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                eval_id,
                prompt_version,
                model,
                "anthropic",
                started,
                completed,
                len(golden_set),
                mean_score,
                json.dumps(means),
                json.dumps({"rubric_id": rubric.id}),
            ],
        )

    return EvalRun(
        eval_id=eval_id,
        prompt_version=prompt_version,
        model=model,
        provider="anthropic",
        started_at=started,
        completed_at=completed,
        examples_evaluated=len(golden_set),
        mean_score=mean_score,
        per_criterion_means=means,
    )


async def run_pairwise_eval(
    *,
    prompt_version: str,
    model: str,
    golden_set: list[GoldenExample],
    generator: NarrativeGenerator,
    judge: LlmJudge,
) -> EvalRun:
    """Compare candidate vs reference narrative pairwise across the golden
    set. Useful when pointwise scores cluster tightly and a tie-breaker is
    needed to choose between prompt versions.
    """

    eval_id = str(uuid.uuid4())
    started = datetime.now(UTC)
    a_wins = 0
    b_wins = 0
    ties = 0
    inconsistent = 0
    for example in golden_set:
        candidate = await _generate_or_reference(
            example=example,
            prompt_version=prompt_version,
            model=model,
            generator=generator,
        )
        reference = example.reference_narrative
        result = await judge.score_pairwise(
            narrative_a=candidate, narrative_b=reference, finding=example.finding
        )
        _ = result
        if not result.position_swap_consistent:
            inconsistent += 1
        if result.winner == "a":
            a_wins += 1
        elif result.winner == "b":
            b_wins += 1
        else:
            ties += 1
    completed = datetime.now(UTC)
    n = max(1, len(golden_set))
    winrate = (a_wins + 0.5 * ties) / n
    return EvalRun(
        eval_id=eval_id,
        prompt_version=prompt_version,
        model=model,
        provider="anthropic",
        started_at=started,
        completed_at=completed,
        examples_evaluated=len(golden_set),
        mean_score=winrate * 100.0,
        per_criterion_means={
            "candidate_winrate_vs_reference": winrate,
            "inconsistent_swap_rate": inconsistent / n,
        },
        pairwise_vs_reference_winrate=winrate,
    )


async def compare_prompts(
    *,
    version_a: str,
    version_b: str,
    model: str,
    golden_set: list[GoldenExample],
    generator: NarrativeGenerator,
    judge: LlmJudge,
) -> ComparisonResult:
    """Pairwise A/B between two prompt versions over the golden set."""

    a_wins = 0
    b_wins = 0
    ties = 0
    inconsistent = 0
    for example in golden_set:
        narrative_a = await _generate_or_reference(
            example=example,
            prompt_version=version_a,
            model=model,
            generator=generator,
        )
        narrative_b = await _generate_or_reference(
            example=example,
            prompt_version=version_b,
            model=model,
            generator=generator,
        )
        result: PairwiseResult = await judge.score_pairwise(
            narrative_a=narrative_a, narrative_b=narrative_b, finding=example.finding
        )
        if not result.position_swap_consistent:
            inconsistent += 1
        if result.winner == "a":
            a_wins += 1
        elif result.winner == "b":
            b_wins += 1
        else:
            ties += 1

    n = max(1, len(golden_set))
    winrate_b = (b_wins + 0.5 * ties) / n
    return ComparisonResult(
        version_a=version_a,
        version_b=version_b,
        examples=len(golden_set),
        a_wins=a_wins,
        b_wins=b_wins,
        ties=ties,
        winrate_b=winrate_b,
        inconsistent_swaps=inconsistent,
    )


async def _generate_or_reference(
    *,
    example: GoldenExample,
    prompt_version: str,
    model: str,
    generator: NarrativeGenerator,
) -> str:
    """Resolve the narrative for a candidate. ``prompt_version="reference"``
    is a sentinel meaning "use the hand-written golden-set entry"; this lets
    pairwise eval compare a generated v1 against the human reference without
    a parallel code path.
    """

    if prompt_version == REFERENCE_PROMPT_VERSION:
        return example.reference_narrative
    narrative = await generator.generate(
        example.finding,
        prompt_version=prompt_version,
        model=model,
    )
    return narrative.markdown


def latest_runs_per_prompt_version(
    conn: duckdb.DuckDBPyConnection,
) -> list[dict[str, Any]]:
    """Pull the most recent eval row per prompt_version. Used by the
    ``narrative eval-history`` CLI to show progress over time.
    """

    rows = conn.execute(
        """
        SELECT prompt_version, model, mean_score, completed_at, per_criterion_scores
        FROM eval_runs
        ORDER BY completed_at DESC
        """
    ).fetchall()
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        if row[0] in seen:
            continue
        seen.add(row[0])
        out.append(
            {
                "prompt_version": row[0],
                "model": row[1],
                "mean_score": float(row[2]) if row[2] is not None else 0.0,
                "completed_at": row[3],
                "per_criterion_scores": json.loads(row[4]) if row[4] else {},
            }
        )
    return out


def make_default_generator(
    provider: LlmProvider,
    conn: duckdb.DuckDBPyConnection,
    *,
    budget_dollars: float = 5.0,
    default_model: str = "claude-opus-4-7",
) -> NarrativeGenerator:
    """Convenience builder for the eval CLI so each invocation can pick a
    fresh budget without leaking state between runs.
    """

    return NarrativeGenerator(
        provider=provider,
        connection=conn,
        budget=NarrativeBudget(max_dollars=budget_dollars),
        default_model=default_model,
    )


# Keep imports referenced from default arguments alive for runtime use.
_RUNTIME_REFS: tuple[type[Finding], str] = (Finding, DEFAULT_PROMPT_VERSION)
