"""Narrative endpoint tests with a fake provider injected.

The real provider is registered globally via the factory, but tests
override it with a recording fake before each call so no LLM credentials
are needed and runs stay deterministic.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from cstack_llm_provider import (
    LlmRequest,
    LlmResponse,
    clear_registry,
    register_provider,
)
from cstack_llm_provider.config import get_settings as get_llm_settings
from httpx import AsyncClient
from signalguard_api.config import Settings

from .conftest import DEV_KEY, TENANT_B, TENANT_B_KEY_PLAIN

VALID_NARRATIVE = """## Why this fired
A finding fired because the evidence shows a missing CA policy.

## What it means
Without this protection, attackers can land valid credentials.

## Remediation
1. Create a CA policy targeting all users.
2. Set client app types appropriately.
3. Set grant controls to block.
4. Enable the policy.

## Caveats
A small population of service accounts may need exclusions.
"""


class _RecordingProvider:
    name = "anthropic"

    def __init__(self) -> None:
        self.calls: list[LlmRequest] = []

    async def complete(self, request: LlmRequest) -> LlmResponse:
        self.calls.append(request)
        return LlmResponse(
            content=VALID_NARRATIVE,
            model=request.model,
            provider=self.name,
            input_tokens=120,
            output_tokens=180,
            latency_ms=10,
            finish_reason="stop",
            raw={},
        )

    async def count_tokens(self, text: str, model: str) -> int:
        return len(text)

    def supported_models(self) -> list[str]:
        return ["claude-opus-4-7"]


@pytest.fixture(autouse=True)
def _reset_provider_registry() -> Iterator[None]:
    clear_registry()
    yield
    clear_registry()


async def _seed_finding(client: AsyncClient) -> str:
    """Run the audit so the findings table has at least one row to narrate."""
    response = await client.post(
        f"/tenants/{TENANT_B}/audit/run",
        json={
            "categories": ["coverage", "rules", "exclusions"],
            "generate_narratives": False,
        },
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 200
    listing = await client.get(
        f"/tenants/{TENANT_B}/findings",
        headers={"X-API-Key": DEV_KEY},
        params={"limit": 1},
    )
    assert listing.status_code == 200
    items: list[dict[str, Any]] = listing.json()["items"]
    assert items, "expected at least one finding"
    return cast(str, items[0]["id"])


@pytest.mark.asyncio
async def test_get_narrative_generates_and_then_caches(
    client: AsyncClient, fixture_corpus: dict[str, Any], settings: Settings
) -> None:
    _ = fixture_corpus
    fake = _RecordingProvider()
    register_provider("anthropic", fake)
    get_llm_settings.cache_clear()

    finding_id = await _seed_finding(client)

    first = await client.get(
        f"/tenants/{TENANT_B}/findings/{finding_id}/narrative",
        headers={"X-API-Key": DEV_KEY},
    )
    assert first.status_code == 200, first.text
    payload = first.json()
    assert "## Why this fired" in payload["markdown"]
    assert payload["cached"] is False
    assert len(fake.calls) == 1

    second = await client.get(
        f"/tenants/{TENANT_B}/findings/{finding_id}/narrative",
        headers={"X-API-Key": DEV_KEY},
    )
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert len(fake.calls) == 1, "second call should hit cache, not the provider"


@pytest.mark.asyncio
async def test_regenerate_requires_dev_key(
    client: AsyncClient, fixture_corpus: dict[str, Any], settings: Settings
) -> None:
    _ = fixture_corpus
    fake = _RecordingProvider()
    register_provider("anthropic", fake)
    get_llm_settings.cache_clear()

    finding_id = await _seed_finding(client)
    response = await client.post(
        f"/tenants/{TENANT_B}/findings/{finding_id}/narrative/regenerate",
        json={},
        headers={"X-API-Key": TENANT_B_KEY_PLAIN},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_regenerate_with_dev_key_bypasses_cache(
    client: AsyncClient, fixture_corpus: dict[str, Any], settings: Settings
) -> None:
    _ = fixture_corpus
    fake = _RecordingProvider()
    register_provider("anthropic", fake)
    get_llm_settings.cache_clear()

    finding_id = await _seed_finding(client)
    # Prime the cache.
    primed = await client.get(
        f"/tenants/{TENANT_B}/findings/{finding_id}/narrative",
        headers={"X-API-Key": DEV_KEY},
    )
    assert primed.status_code == 200
    assert len(fake.calls) == 1

    regen = await client.post(
        f"/tenants/{TENANT_B}/findings/{finding_id}/narrative/regenerate",
        json={"prompt_version": "v1"},
        headers={"X-API-Key": DEV_KEY},
    )
    assert regen.status_code == 200, regen.text
    assert regen.json()["cached"] is False
    assert len(fake.calls) == 2


@pytest.mark.asyncio
async def test_audit_run_generates_narratives_when_enabled(
    client: AsyncClient, fixture_corpus: dict[str, Any], settings: Settings
) -> None:
    _ = fixture_corpus
    fake = _RecordingProvider()
    register_provider("anthropic", fake)
    get_llm_settings.cache_clear()

    response = await client.post(
        f"/tenants/{TENANT_B}/audit/run",
        json={"generate_narratives": True, "narrative_budget_usd": 5.0},
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["narrative_summary"] is not None
    assert payload["narrative_summary"]["errored"] == 0


@pytest.mark.asyncio
async def test_get_narrative_404_for_unknown_finding(
    client: AsyncClient, fixture_corpus: dict[str, Any], settings: Settings
) -> None:
    _ = fixture_corpus
    fake = _RecordingProvider()
    register_provider("anthropic", fake)
    get_llm_settings.cache_clear()

    response = await client.get(
        f"/tenants/{TENANT_B}/findings/does-not-exist/narrative",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 404
