import time
from typing import Any

import httpx

from cstack_llm_provider.types import (
    LlmError,
    LlmFinishReason,
    LlmRequest,
    LlmResponse,
)

_TAGS_TTL_SECONDS = 300.0


class OllamaProvider:
    """Talks to a local Ollama server over HTTP.

    Ollama doesn't ship a Python SDK. The REST surface is small enough that
    httpx is the right tool. ``count_tokens`` falls back to a character
    approximation because Ollama doesn't expose a tokenizer endpoint; callers
    that need exact counts should use the Anthropic or OpenAI adapters.
    """

    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url=self._base_url, timeout=120.0)
        self._tags_cache: tuple[float, list[str]] | None = None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def complete(self, request: LlmRequest) -> LlmResponse:
        messages: list[dict[str, str]] = []
        if request.system is not None:
            messages.append({"role": "system", "content": request.system})
        messages.extend({"role": m.role, "content": m.content} for m in request.messages)

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        started = time.perf_counter()
        try:
            response = await self._client.post("/api/chat", json=payload)
        except httpx.ConnectError as exc:
            raise LlmError(
                f"ollama not available at {self._base_url}: {exc}",
                provider=self.name,
                model=request.model,
            ) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code != 200:
            raise LlmError(
                f"ollama api error: {response.text}",
                provider=self.name,
                model=request.model,
                status_code=response.status_code,
            )

        data = response.json()
        message = data.get("message", {})
        content = message.get("content", "")
        if not content:
            raise LlmError(
                "ollama response missing message content",
                provider=self.name,
                model=request.model,
            )

        # Ollama returns prompt_eval_count and eval_count when the model has
        # been loaded long enough to report; default to zero otherwise so
        # downstream cost tracking degrades gracefully.
        input_tokens = int(data.get("prompt_eval_count", 0))
        output_tokens = int(data.get("eval_count", 0))

        finish_reason: LlmFinishReason = "stop" if data.get("done") else "error"
        if data.get("done_reason") == "length":
            finish_reason = "length"

        return LlmResponse(
            content=content,
            model=data.get("model", request.model),
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            raw=data,
        )

    async def count_tokens(self, text: str, model: str) -> int:
        # Ollama models tokenise differently per family; without server-side
        # support, char-count / 4 is the standard public-domain approximation.
        return max(1, len(text) // 4)

    def supported_models(self) -> list[str]:
        if self._tags_cache and (time.monotonic() - self._tags_cache[0]) < _TAGS_TTL_SECONDS:
            return list(self._tags_cache[1])
        # Synchronous-callable contract; tags are cached and only refreshed by
        # the async refresh helper. On a cold start, return an empty list and
        # let callers decide whether to await refresh.
        return []

    async def refresh_supported_models(self) -> list[str]:
        try:
            response = await self._client.get("/api/tags")
        except httpx.ConnectError as exc:
            raise LlmError(
                f"ollama not available at {self._base_url}: {exc}",
                provider=self.name,
            ) from exc
        if response.status_code != 200:
            raise LlmError(
                f"ollama tags error: {response.text}",
                provider=self.name,
                status_code=response.status_code,
            )
        models = [m.get("name", "") for m in response.json().get("models", [])]
        models = [m for m in models if m]
        self._tags_cache = (time.monotonic(), models)
        return list(models)
