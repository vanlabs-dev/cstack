from typing import Any
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest
from cstack_llm_provider import LlmError, LlmMessage, LlmRequest
from cstack_llm_provider.adapters import AnthropicProvider


def _build_response(
    *,
    text: str = "narrative content",
    stop_reason: str = "end_turn",
    input_tokens: int = 42,
    output_tokens: int = 17,
    model: str = "claude-opus-4-7",
) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.stop_reason = stop_reason
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    response.model = model
    response.model_dump.return_value = {"id": "msg_x"}
    return response


@pytest.mark.asyncio
async def test_complete_maps_request_to_messages_create() -> None:
    provider = AnthropicProvider(api_key="stub")
    response = _build_response()
    provider._client.messages.create = AsyncMock(return_value=response)  # type: ignore[method-assign]

    request = LlmRequest(
        model="claude-sonnet-4-6",
        messages=[LlmMessage(role="user", content="hello")],
        system="be concise",
        temperature=0.1,
        max_tokens=200,
    )
    response.model = "claude-sonnet-4-6"
    result = await provider.complete(request)

    call_kwargs: dict[str, Any] = dict(
        provider._client.messages.create.await_args.kwargs  # type: ignore[union-attr]
    )
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["system"] == "be concise"
    assert call_kwargs["messages"] == [{"role": "user", "content": "hello"}]
    assert call_kwargs["temperature"] == 0.1
    assert call_kwargs["max_tokens"] == 200

    assert result.content == "narrative content"
    assert result.input_tokens == 42
    assert result.output_tokens == 17
    assert result.finish_reason == "stop"
    assert result.provider == "anthropic"


@pytest.mark.asyncio
async def test_complete_promotes_system_role_message() -> None:
    provider = AnthropicProvider(api_key="stub")
    provider._client.messages.create = AsyncMock(return_value=_build_response())  # type: ignore[method-assign]

    request = LlmRequest(
        model="claude-opus-4-7",
        messages=[
            LlmMessage(role="system", content="from message"),
            LlmMessage(role="user", content="hello"),
        ],
    )
    await provider.complete(request)
    call_kwargs: dict[str, Any] = dict(
        provider._client.messages.create.await_args.kwargs  # type: ignore[union-attr]
    )
    assert call_kwargs["system"] == "from message"
    assert call_kwargs["messages"] == [{"role": "user", "content": "hello"}]


@pytest.mark.asyncio
async def test_complete_wraps_api_status_error() -> None:
    provider = AnthropicProvider(api_key="stub")
    err = anthropic.APIStatusError(
        "rate limited",
        response=MagicMock(status_code=429, headers={}),
        body=None,
    )
    provider._client.messages.create = AsyncMock(side_effect=err)  # type: ignore[method-assign]

    request = LlmRequest(
        model="claude-opus-4-7",
        messages=[LlmMessage(role="user", content="hi")],
    )
    with pytest.raises(LlmError) as exc_info:
        await provider.complete(request)
    assert exc_info.value.provider == "anthropic"
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_complete_raises_when_response_has_no_text() -> None:
    provider = AnthropicProvider(api_key="stub")
    response = _build_response()
    response.content = []
    provider._client.messages.create = AsyncMock(return_value=response)  # type: ignore[method-assign]
    request = LlmRequest(model="claude-opus-4-7", messages=[LlmMessage(role="user", content="hi")])
    with pytest.raises(LlmError, match="no text blocks"):
        await provider.complete(request)


def test_supported_models() -> None:
    provider = AnthropicProvider(api_key="stub")
    models = provider.supported_models()
    assert "claude-opus-4-7" in models
    assert "claude-sonnet-4-6" in models


@pytest.mark.asyncio
async def test_complete_drops_temperature_for_opus_4_7() -> None:
    provider = AnthropicProvider(api_key="stub")
    response = _build_response(model="claude-opus-4-7")
    provider._client.messages.create = AsyncMock(return_value=response)  # type: ignore[method-assign]

    request = LlmRequest(
        model="claude-opus-4-7",
        messages=[LlmMessage(role="user", content="hi")],
        temperature=0.2,
    )
    await provider.complete(request)
    call_kwargs: dict[str, Any] = dict(
        provider._client.messages.create.await_args.kwargs  # type: ignore[union-attr]
    )
    # Opus 4.7 rejects temperature; the adapter silently drops it.
    assert "temperature" not in call_kwargs
