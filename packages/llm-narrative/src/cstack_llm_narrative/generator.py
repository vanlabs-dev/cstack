"""Finding-to-narrative generator with cache, budget, and validation.

The generator is the single entry point Sprint 6 callers (CLI, API,
eval harness) use to turn a Finding into a markdown narrative. Steps,
in order:

1. Compute content-addressed cache key.
2. Look up the cache; on hit, bump last_used and return.
3. Check the budget; on would-exceed, raise BudgetExceededError.
4. Render the prompt; call the provider.
5. Validate the response shape; retry once with a fix instruction on failure.
6. Store in the cache; emit a structured token-usage log line; return.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import duckdb
from cstack_audit_core import Finding
from cstack_llm_provider import (
    LlmError,
    LlmMessage,
    LlmProvider,
    LlmRequest,
)
from cstack_storage import (
    CachedNarrative,
    compute_cache_key,
    get_cached_narrative,
    hash_evidence,
    store_narrative,
)

from cstack_llm_narrative.narrative import (
    BudgetExceededError,
    Narrative,
    NarrativeBudget,
    estimate_cost_usd,
)
from cstack_llm_narrative.prompt_loader import (
    PromptTemplate,
    load_prompt,
    render_prompt,
)

logger = logging.getLogger("cstack_llm_narrative")

REQUIRED_HEADINGS = (
    "## Why this fired",
    "## What it means",
    "## Remediation",
    "## Caveats",
)
DEFAULT_PROMPT_ID = "finding_narrative"
DEFAULT_PROMPT_VERSION = "v1"


class NarrativeValidationError(RuntimeError):
    """Raised when the LLM output does not contain the four required sections.

    The generator catches the first occurrence and retries once with an
    explicit fix instruction; a second failure surfaces this exception so
    the caller can decide how to handle a misbehaving model.
    """


@dataclass
class BatchResult:
    """Counts and spend reported back from ``generate_batch``."""

    cache_hits: int = 0
    generated: int = 0
    skipped_budget: int = 0
    errored: int = 0
    dollars_spent: float = 0.0


class NarrativeGenerator:
    """Finding-to-narrative pipeline with cache, budget, and validation.

    Constructor takes a provider, a DuckDB connection, an optional budget,
    and the default model name. ``generate`` is the single-finding entry
    point; ``generate_batch`` runs many findings concurrently with a
    semaphore to bound provider request rate.
    """

    def __init__(
        self,
        provider: LlmProvider,
        connection: duckdb.DuckDBPyConnection,
        budget: NarrativeBudget | None = None,
        default_model: str = "claude-opus-4-7",
        max_concurrency: int = 4,
    ) -> None:
        self._provider = provider
        self._conn = connection
        self._budget = budget or NarrativeBudget(max_dollars=float("inf"))
        self._default_model = default_model
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def generate(
        self,
        finding: Finding,
        *,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
        model: str | None = None,
        force: bool = False,
    ) -> Narrative:
        chosen_model = model or self._default_model
        cache_key = compute_cache_key(
            finding.rule_id,
            finding.evidence,
            prompt_version,
            chosen_model,
        )

        if not force:
            cached = get_cached_narrative(self._conn, cache_key)
            if cached is not None:
                _log_event(
                    "narrative.cache.hit",
                    finding_id=finding.id,
                    rule_id=finding.rule_id,
                    cache_key=cache_key,
                )
                return Narrative(
                    cache_key=cached.cache_key,
                    rule_id=cached.rule_id,
                    prompt_version=cached.prompt_version,
                    provider=cached.provider,
                    model=cached.model,
                    markdown=cached.narrative_markdown,
                    input_tokens=cached.input_tokens,
                    output_tokens=cached.output_tokens,
                    latency_ms=cached.latency_ms,
                    generated_at=cached.generated_at,
                    cached=True,
                )

        template = load_prompt(DEFAULT_PROMPT_ID, prompt_version)
        prompt_text = _render_for_finding(template, finding)

        # Estimated cost uses the prompt size + a generous output ceiling because
        # the actual output token count isn't known until after the call. The
        # ceiling is intentionally cautious to avoid the user sliding past the
        # budget cap by a few percent.
        estimated_input = max(1, len(prompt_text) // 4)
        estimated_output = 500
        estimated_cost = estimate_cost_usd(chosen_model, estimated_input, estimated_output)
        if self._budget.would_exceed(estimated_cost):
            self._budget.record_skip()
            raise BudgetExceededError(
                f"would exceed budget: spent={self._budget.dollars_spent:.4f} "
                f"cap={self._budget.max_dollars:.4f} estimated={estimated_cost:.4f}"
            )

        markdown = await self._call_with_validation(
            prompt_text=prompt_text,
            model=chosen_model,
            finding_id=finding.id,
            rule_id=finding.rule_id,
        )

        # The actual cost lands on the response object. Re-fetch latency/tokens
        # by issuing a fresh call would double-bill; instead, we return the
        # latest call's metadata stashed on the generator state.
        last = self._last_response
        actual_cost = estimate_cost_usd(chosen_model, last.input_tokens, last.output_tokens)
        self._budget.record(actual_cost)

        now = datetime.now(UTC)
        cached_narrative = CachedNarrative(
            cache_key=cache_key,
            rule_id=finding.rule_id,
            evidence_hash=hash_evidence(finding.evidence),
            prompt_version=prompt_version,
            provider=last.provider,
            model=last.model,
            narrative_markdown=markdown,
            input_tokens=last.input_tokens,
            output_tokens=last.output_tokens,
            latency_ms=last.latency_ms,
            generated_at=now,
            last_used_at=now,
        )
        store_narrative(self._conn, cached_narrative)

        _log_event(
            "narrative.generate.ok",
            finding_id=finding.id,
            rule_id=finding.rule_id,
            cache_key=cache_key,
            provider=last.provider,
            model=last.model,
            input_tokens=last.input_tokens,
            output_tokens=last.output_tokens,
            latency_ms=last.latency_ms,
            cost_usd=actual_cost,
        )
        return Narrative(
            cache_key=cache_key,
            rule_id=finding.rule_id,
            prompt_version=prompt_version,
            provider=last.provider,
            model=last.model,
            markdown=markdown,
            input_tokens=last.input_tokens,
            output_tokens=last.output_tokens,
            latency_ms=last.latency_ms,
            generated_at=now,
            cached=False,
        )

    async def generate_batch(
        self,
        findings: list[Finding],
        *,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
        model: str | None = None,
    ) -> BatchResult:
        result = BatchResult()

        async def _one(finding: Finding) -> None:
            async with self._semaphore:
                try:
                    narrative = await self.generate(
                        finding,
                        prompt_version=prompt_version,
                        model=model,
                    )
                    if narrative.cached:
                        result.cache_hits += 1
                    else:
                        result.generated += 1
                except BudgetExceededError:
                    result.skipped_budget += 1
                except (LlmError, NarrativeValidationError) as exc:
                    result.errored += 1
                    _log_event(
                        "narrative.generate.error",
                        finding_id=finding.id,
                        rule_id=finding.rule_id,
                        error=str(exc),
                    )

        await asyncio.gather(*(_one(f) for f in findings))
        result.dollars_spent = self._budget.dollars_spent
        return result

    async def _call_with_validation(
        self,
        *,
        prompt_text: str,
        model: str,
        finding_id: str,
        rule_id: str,
    ) -> str:
        request = LlmRequest(
            model=model,
            messages=[LlmMessage(role="user", content=prompt_text)],
            temperature=0.2,
            max_tokens=900,
        )
        response = await self._provider.complete(request)
        self._last_response = response
        try:
            _validate_structure(response.content)
            return response.content
        except NarrativeValidationError as first_error:
            _log_event(
                "narrative.validate.retry",
                finding_id=finding_id,
                rule_id=rule_id,
                error=str(first_error),
            )

        retry_request = LlmRequest(
            model=model,
            messages=[
                LlmMessage(role="user", content=prompt_text),
                LlmMessage(role="assistant", content=response.content),
                LlmMessage(
                    role="user",
                    content=(
                        "Your previous reply did not include all four required "
                        "sections (## Why this fired, ## What it means, ## "
                        "Remediation, ## Caveats). Reply again with all four "
                        "sections present, sentence case headings, no em dashes, "
                        "under 250 words. Output only the markdown sections."
                    ),
                ),
            ],
            temperature=0.2,
            max_tokens=900,
        )
        retry_response = await self._provider.complete(retry_request)
        self._last_response = retry_response
        _validate_structure(retry_response.content)
        return retry_response.content


def _render_for_finding(template: PromptTemplate, finding: Finding) -> str:
    affected = "; ".join(f"{obj.type}:{obj.display_name}" for obj in finding.affected_objects)
    references = "\n".join(f"- {ref}" for ref in finding.references) or "- none"
    params: dict[str, object] = {
        "rule_id": finding.rule_id,
        "severity": finding.severity.value,
        "title": finding.title,
        "summary": finding.summary,
        "affected_objects": affected or "(none)",
        "evidence_json": json.dumps(finding.evidence, indent=2, default=str),
        "references": references,
    }
    return render_prompt(template, params)


# U+2014 EM DASH and U+2013 EN DASH. Stored as chr() calls so the source
# file itself does not contain characters the project's hard rules prohibit.
_EM_DASH = chr(0x2014)
_EN_DASH = chr(0x2013)


def _validate_structure(content: str) -> None:
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in content]
    if missing:
        raise NarrativeValidationError(f"narrative missing required sections: {missing}")
    if _EM_DASH in content or _EN_DASH in content:
        raise NarrativeValidationError("narrative contains em dash or en dash")
    if _word_count(content) > 320:
        raise NarrativeValidationError(
            f"narrative exceeds 320-word ceiling (was {_word_count(content)})"
        )


_WORD_RE = re.compile(r"[\w'-]+")


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _log_event(event: str, **fields: Any) -> None:
    logger.info(event, extra={"event": event, **fields})
