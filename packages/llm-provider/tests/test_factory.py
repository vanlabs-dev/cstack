import pytest
from cstack_llm_provider import (
    LlmRequest,
    LlmResponse,
    clear_registry,
    get_provider,
    register_provider,
)
from cstack_llm_provider.adapters import (
    AnthropicProvider,
    OllamaProvider,
    OpenAIProvider,
)
from cstack_llm_provider.config import get_settings


class _RecordingProvider:
    name = "anthropic"

    def __init__(self) -> None:
        self.calls: list[LlmRequest] = []

    async def complete(self, request: LlmRequest) -> LlmResponse:
        self.calls.append(request)
        return LlmResponse(
            content="ok",
            model=request.model,
            provider=self.name,
            input_tokens=1,
            output_tokens=1,
            latency_ms=1,
            finish_reason="stop",
            raw={},
        )

    async def count_tokens(self, text: str, model: str) -> int:
        return len(text)

    def supported_models(self) -> list[str]:
        return ["fake"]


def test_get_provider_returns_anthropic_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub")
    monkeypatch.delenv("CSTACK_LLM_PROVIDER", raising=False)
    get_settings.cache_clear()
    clear_registry()
    provider = get_provider()
    assert isinstance(provider, AnthropicProvider)


def test_get_provider_resolves_explicit_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "stub")
    get_settings.cache_clear()
    clear_registry()
    provider = get_provider("openai")
    assert isinstance(provider, OpenAIProvider)


def test_get_provider_ollama() -> None:
    get_settings.cache_clear()
    clear_registry()
    provider = get_provider("ollama")
    assert isinstance(provider, OllamaProvider)


def test_get_provider_unknown_name_raises() -> None:
    clear_registry()
    with pytest.raises(ValueError, match="unknown provider"):
        get_provider("not-a-provider")


def test_register_provider_overrides_real_adapter() -> None:
    fake = _RecordingProvider()
    register_provider("anthropic", fake)
    assert get_provider("anthropic") is fake
