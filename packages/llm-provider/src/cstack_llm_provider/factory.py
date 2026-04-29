from threading import Lock

from cstack_llm_provider.adapters import (
    AnthropicProvider,
    OllamaProvider,
    OpenAIProvider,
)
from cstack_llm_provider.config import get_settings
from cstack_llm_provider.protocol import LlmProvider

_PROVIDER_CACHE: dict[str, LlmProvider] = {}
_REGISTRY_OVERRIDES: dict[str, LlmProvider] = {}
_LOCK = Lock()


def get_provider(provider_name: str | None = None) -> LlmProvider:
    """Resolve a provider adapter by name.

    Adapter instances are cached per-process because the underlying SDK
    clients hold connection pools and cookie state that should be reused.
    Tests can call ``register_provider`` to inject fakes; overrides take
    precedence over real adapters.
    """

    settings = get_settings()
    name = (provider_name or settings.cstack_llm_provider).lower()

    with _LOCK:
        if name in _REGISTRY_OVERRIDES:
            return _REGISTRY_OVERRIDES[name]
        if name in _PROVIDER_CACHE:
            return _PROVIDER_CACHE[name]

        provider = _build_provider(name, settings)
        _PROVIDER_CACHE[name] = provider
        return provider


def register_provider(name: str, provider: LlmProvider) -> None:
    """Inject a provider for the given name. Used by tests; overrides any
    cached real adapter for the rest of the process.
    """

    with _LOCK:
        _REGISTRY_OVERRIDES[name.lower()] = provider


def clear_registry() -> None:
    """Drop overrides and cached adapters. Tests call this in teardown to
    keep cross-test state from leaking.
    """

    with _LOCK:
        _REGISTRY_OVERRIDES.clear()
        _PROVIDER_CACHE.clear()


def _build_provider(name: str, settings: object) -> LlmProvider:
    from cstack_llm_provider.config import LlmProviderSettings

    assert isinstance(settings, LlmProviderSettings)
    if name == "anthropic":
        return AnthropicProvider(api_key=settings.anthropic_api_key)
    if name == "openai":
        return OpenAIProvider(api_key=settings.openai_api_key)
    if name == "ollama":
        return OllamaProvider(base_url=settings.ollama_base_url)
    raise ValueError(f"unknown provider '{name}'; expected one of: anthropic, openai, ollama")
