from typing import Protocol, runtime_checkable

from cstack_llm_provider.types import LlmRequest, LlmResponse


@runtime_checkable
class LlmProvider(Protocol):
    """Duck-typed contract every adapter implements. A Protocol rather than an
    ABC so test fakes can satisfy the contract without inheriting, and so
    isinstance checks at runtime stay opt-in via runtime_checkable.
    """

    name: str

    async def complete(self, request: LlmRequest) -> LlmResponse:
        """Run a completion. Adapters map the request to the provider's native
        call shape and normalise the response. On provider failure they raise
        ``LlmError``.
        """
        ...

    async def count_tokens(self, text: str, model: str) -> int:
        """Best-effort token count. Adapters use the official tokenizer where
        available; Ollama falls back to a character-based approximation.
        """
        ...

    def supported_models(self) -> list[str]:
        """Models the adapter will accept. Used by the factory and CLI to
        report capabilities; not enforced inside ``complete`` so callers can
        pass through new models without an adapter release.
        """
        ...
