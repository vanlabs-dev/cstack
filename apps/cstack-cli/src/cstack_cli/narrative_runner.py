"""Helpers for the ``cstack narrative`` CLI subgroup.

Kept separate from ``audit_runner`` so the audit-only code path doesn't pull
the LLM stack into its import graph until it actually needs it.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import duckdb
from cstack_audit_core import Finding
from cstack_llm_narrative import (
    BatchResult,
    Narrative,
    NarrativeBudget,
    NarrativeGenerator,
)
from cstack_llm_provider import (
    LlmError,
    LlmMessage,
    LlmRequest,
    get_provider,
    get_settings,
)
from cstack_llm_provider.adapters import OllamaProvider


@dataclass(frozen=True)
class ProviderProbe:
    name: str
    reachable: bool
    detail: str


def run_narrative_pass_for_findings(
    conn: duckdb.DuckDBPyConnection,
    findings: list[Finding],
    *,
    prompt_version: str = "v1",
    budget_usd: float | None = None,
    force: bool = False,
) -> BatchResult:
    settings = get_settings()
    provider = get_provider(settings.cstack_llm_provider)
    cap = budget_usd if budget_usd is not None else settings.cstack_llm_budget_usd
    budget = NarrativeBudget(max_dollars=cap)
    generator = NarrativeGenerator(
        provider=provider,
        connection=conn,
        budget=budget,
        default_model=settings.cstack_llm_default_model,
    )
    if force:
        # Force-regenerate is one-finding-at-a-time so we don't blow past the
        # budget surprising the user; this path is for prompt iteration, not
        # bulk re-runs. Provider/validation failures are swallowed per finding
        # so a single bad row doesn't take down the whole regenerate batch.
        import contextlib

        async def _force_one(finding: Finding) -> None:
            with contextlib.suppress(LlmError, Exception):
                await generator.generate(
                    finding,
                    prompt_version=prompt_version,
                    force=True,
                )

        async def _all() -> None:
            for f in findings:
                await _force_one(f)

        asyncio.run(_all())
        return BatchResult(
            cache_hits=0,
            generated=len(findings),
            skipped_budget=budget.skipped_count,
            errored=0,
            dollars_spent=budget.dollars_spent,
        )
    return asyncio.run(generator.generate_batch(findings, prompt_version=prompt_version))


def regenerate_for_finding(
    conn: duckdb.DuckDBPyConnection,
    finding: Finding,
    *,
    prompt_version: str = "v1",
    model: str | None = None,
) -> Narrative:
    settings = get_settings()
    provider = get_provider(settings.cstack_llm_provider)
    generator = NarrativeGenerator(
        provider=provider,
        connection=conn,
        default_model=settings.cstack_llm_default_model,
    )
    return asyncio.run(
        generator.generate(
            finding,
            prompt_version=prompt_version,
            model=model,
            force=True,
        )
    )


def format_narrative_summary(result: BatchResult) -> str:
    return (
        f"narratives: {result.generated} generated, {result.cache_hits} cached, "
        f"{result.skipped_budget} skipped (budget), {result.errored} errored, "
        f"${result.dollars_spent:.4f} spent"
    )


async def probe_providers() -> list[ProviderProbe]:
    """Round-trip a tiny prompt through each provider to report reachability.

    Anthropic and OpenAI are skipped when their key isn't configured to avoid
    needless 401s; Ollama is probed via /api/tags which is cheap and free.
    """

    settings = get_settings()
    out: list[ProviderProbe] = []

    if settings.anthropic_api_key:
        out.append(await _probe_anthropic())
    else:
        out.append(ProviderProbe("anthropic", False, "ANTHROPIC_API_KEY not set"))

    if settings.openai_api_key:
        out.append(await _probe_openai())
    else:
        out.append(ProviderProbe("openai", False, "OPENAI_API_KEY not set"))

    out.append(await _probe_ollama(settings.ollama_base_url))
    return out


async def _probe_anthropic() -> ProviderProbe:
    try:
        provider = get_provider("anthropic")
        await provider.complete(
            LlmRequest(
                model="claude-haiku-4-5",
                messages=[LlmMessage(role="user", content="say PONG")],
                max_tokens=8,
                temperature=0.0,
            )
        )
        return ProviderProbe("anthropic", True, "haiku-4-5 round-trip ok")
    except LlmError as exc:
        return ProviderProbe("anthropic", False, str(exc))


async def _probe_openai() -> ProviderProbe:
    try:
        provider = get_provider("openai")
        await provider.complete(
            LlmRequest(
                model="gpt-4o-mini",
                messages=[LlmMessage(role="user", content="say PONG")],
                max_tokens=8,
                temperature=0.0,
            )
        )
        return ProviderProbe("openai", True, "gpt-4o-mini round-trip ok")
    except LlmError as exc:
        return ProviderProbe("openai", False, str(exc))


async def _probe_ollama(base_url: str) -> ProviderProbe:
    provider = OllamaProvider(base_url=base_url)
    try:
        models = await provider.refresh_supported_models()
        detail = f"reached {base_url}; models={models}" if models else f"reached {base_url}"
        return ProviderProbe("ollama", True, detail)
    except LlmError as exc:
        return ProviderProbe("ollama", False, str(exc))
    finally:
        await provider.aclose()
