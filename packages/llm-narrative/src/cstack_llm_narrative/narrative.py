"""Narrative model, budget tracking, and pricing constants.

The pricing dict mirrors the public Anthropic and OpenAI rate cards as of
April 2026. Numbers are per-token in USD. Drift between this constant and
the real bill is acceptable: budget tracking is a guard rail, not an
audited accounting figure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict


class _ModelPrice(TypedDict):
    input: float
    output: float


# Token pricing in USD per token. Anthropic publishes per-million; divide by 1e6.
MODEL_PRICING: dict[str, _ModelPrice] = {
    "claude-opus-4-7": {"input": 15.0e-6, "output": 75.0e-6},
    "claude-sonnet-4-6": {"input": 3.0e-6, "output": 15.0e-6},
    "claude-haiku-4-5": {"input": 0.8e-6, "output": 4.0e-6},
    "gpt-5-mini": {"input": 1.5e-6, "output": 6.0e-6},
    "gpt-4o": {"input": 2.5e-6, "output": 10.0e-6},
    "gpt-4o-mini": {"input": 0.15e-6, "output": 0.60e-6},
}

# Models we don't have rates for (e.g. Ollama local) cost zero for budget purposes.
_FREE_PRICE: _ModelPrice = {"input": 0.0, "output": 0.0}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Per-call USD estimate via MODEL_PRICING. Unknown models cost zero.

    Used by NarrativeBudget to gate calls before a request leaves the
    process. Drift against the real Anthropic bill is acceptable; this is a
    guard rail, not an audited figure.
    """

    rate = MODEL_PRICING.get(model, _FREE_PRICE)
    return rate["input"] * input_tokens + rate["output"] * output_tokens


@dataclass
class Narrative:
    """A generated or cache-hit narrative ready to render.

    ``cached=True`` means this row came from narrative_cache without a
    fresh provider call; the input/output token counts then reflect the
    original generation, not a re-render.
    """

    cache_key: str
    rule_id: str
    prompt_version: str
    provider: str
    model: str
    markdown: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    generated_at: datetime
    cached: bool = False


class BudgetExceededError(RuntimeError):
    """Raised when a generation would push spend over the configured cap.

    Callers should treat this as a non-fatal signal: skip the remaining
    findings, emit a structured log, and let the UI render "narrative
    pending" for the affected rows.
    """


@dataclass
class NarrativeBudget:
    """Tracks USD spend across a generate-batch call. Cumulative; resets
    only when a new ``NarrativeBudget`` is constructed.
    """

    max_dollars: float = 1.0
    dollars_spent: float = 0.0
    skipped_count: int = 0
    estimated_pending: list[float] = field(default_factory=list)

    def would_exceed(self, estimated_cost: float) -> bool:
        return (self.dollars_spent + estimated_cost) > self.max_dollars

    def record(self, actual_cost: float) -> None:
        self.dollars_spent += actual_cost

    def record_skip(self) -> None:
        self.skipped_count += 1

    @property
    def remaining(self) -> float:
        return max(0.0, self.max_dollars - self.dollars_spent)
