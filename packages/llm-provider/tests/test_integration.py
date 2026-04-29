"""Live integration tests. Skipped unless CSTACK_LLM_INTEGRATION_TESTS=1.

These guard against silent SDK breaking changes by hitting the real provider
with a tiny prompt. They are NOT run on every test invocation; they cost
real money and require valid credentials.
"""

import os

import pytest
from cstack_llm_provider import LlmMessage, LlmRequest, get_provider

INTEGRATION = os.environ.get("CSTACK_LLM_INTEGRATION_TESTS") == "1"
pytestmark = pytest.mark.skipif(not INTEGRATION, reason="integration tests opt-in")


@pytest.mark.asyncio
async def test_anthropic_round_trip() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    provider = get_provider("anthropic")
    response = await provider.complete(
        LlmRequest(
            model="claude-haiku-4-5",
            messages=[LlmMessage(role="user", content="reply with the single word PONG")],
            max_tokens=8,
            temperature=0.0,
        )
    )
    assert "PONG" in response.content.upper()
    assert response.input_tokens > 0
