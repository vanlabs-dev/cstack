from unittest.mock import AsyncMock, MagicMock

import openai
import pytest
from cstack_llm_provider import LlmError, LlmMessage, LlmRequest
from cstack_llm_provider.adapters import OpenAIProvider


def _build_response(*, content: str = "ok", finish_reason: str = "stop") -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = finish_reason
    response = MagicMock()
    response.choices = [choice]
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 20
    response.model = "gpt-4o"
    response.model_dump.return_value = {"id": "chat_x"}
    return response


@pytest.mark.asyncio
async def test_complete_maps_request_to_chat_completion() -> None:
    provider = OpenAIProvider(api_key="stub")
    provider._client.chat.completions.create = AsyncMock(return_value=_build_response())  # type: ignore[method-assign]

    request = LlmRequest(
        model="gpt-4o",
        messages=[LlmMessage(role="user", content="hello")],
        system="be concise",
        temperature=0.3,
        max_tokens=64,
    )
    result = await provider.complete(request)

    call_kwargs = provider._client.chat.completions.create.await_args.kwargs  # type: ignore[union-attr]
    assert call_kwargs["messages"][0] == {"role": "system", "content": "be concise"}
    assert call_kwargs["messages"][1] == {"role": "user", "content": "hello"}
    assert result.input_tokens == 10
    assert result.output_tokens == 20
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_complete_wraps_api_status_error() -> None:
    provider = OpenAIProvider(api_key="stub")
    err = openai.APIStatusError(
        "boom",
        response=MagicMock(status_code=500, headers={}),
        body=None,
    )
    provider._client.chat.completions.create = AsyncMock(side_effect=err)  # type: ignore[method-assign]
    with pytest.raises(LlmError) as exc_info:
        await provider.complete(
            LlmRequest(model="gpt-4o", messages=[LlmMessage(role="user", content="x")])
        )
    assert exc_info.value.provider == "openai"
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_count_tokens_falls_back_to_cl100k() -> None:
    provider = OpenAIProvider(api_key="stub")
    count = await provider.count_tokens("hello world", "unknown-future-model")
    assert count > 0
