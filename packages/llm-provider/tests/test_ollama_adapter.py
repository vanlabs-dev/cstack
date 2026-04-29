import httpx
import pytest
from cstack_llm_provider import LlmError, LlmMessage, LlmRequest
from cstack_llm_provider.adapters import OllamaProvider


def _ollama_chat_response() -> dict[str, object]:
    return {
        "model": "llama3.1",
        "message": {"role": "assistant", "content": "ok"},
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 5,
        "eval_count": 12,
    }


def _build_provider(handler: httpx.MockTransport) -> OllamaProvider:
    client = httpx.AsyncClient(transport=handler, base_url="http://localhost:11434")
    return OllamaProvider(base_url="http://localhost:11434", client=client)


@pytest.mark.asyncio
async def test_complete_posts_chat_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = request.read().decode()
        return httpx.Response(200, json=_ollama_chat_response())

    provider = _build_provider(httpx.MockTransport(handler))
    try:
        result = await provider.complete(
            LlmRequest(
                model="llama3.1",
                messages=[LlmMessage(role="user", content="hi")],
                system="be terse",
            )
        )
    finally:
        await provider.aclose()

    assert "/api/chat" in str(captured["url"])
    assert "be terse" in str(captured["json"])
    assert result.content == "ok"
    assert result.input_tokens == 5
    assert result.output_tokens == 12


@pytest.mark.asyncio
async def test_complete_raises_clear_error_when_unreachable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _build_provider(httpx.MockTransport(handler))
    try:
        with pytest.raises(LlmError, match="ollama not available"):
            await provider.complete(
                LlmRequest(
                    model="llama3.1",
                    messages=[LlmMessage(role="user", content="hi")],
                )
            )
    finally:
        await provider.aclose()


@pytest.mark.asyncio
async def test_refresh_supported_models_caches_tags() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "llama3.1"}, {"name": "mistral"}]})

    provider = _build_provider(httpx.MockTransport(handler))
    try:
        models = await provider.refresh_supported_models()
    finally:
        await provider.aclose()
    assert models == ["llama3.1", "mistral"]
    assert provider.supported_models() == ["llama3.1", "mistral"]


@pytest.mark.asyncio
async def test_count_tokens_returns_char_estimate() -> None:
    provider = OllamaProvider()
    try:
        count = await provider.count_tokens("hello world hello world", "llama3.1")
    finally:
        await provider.aclose()
    assert count >= 1
