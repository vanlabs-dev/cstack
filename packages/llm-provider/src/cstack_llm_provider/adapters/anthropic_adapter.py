import time
from typing import Any

import anthropic

from cstack_llm_provider.types import (
    LlmError,
    LlmFinishReason,
    LlmRequest,
    LlmResponse,
)

_SUPPORTED_MODELS = [
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
]

# Claude 4.7+ no longer accepts the temperature parameter on the messages
# endpoint; sending it returns a 400 invalid_request_error. The adapter
# silently drops temperature for these models and surfaces a debug log.
_MODELS_WITHOUT_TEMPERATURE = frozenset({"claude-opus-4-7"})


class AnthropicProvider:
    """Maps the provider-agnostic ``LlmRequest`` onto Anthropic's Messages API.

    Anthropic treats the system prompt as a top-level field. The adapter
    forwards ``LlmRequest.system`` directly and only sends conversation turns
    in ``messages``; any ``role="system"`` message inside ``messages`` is
    promoted into the system field rather than being silently rejected.
    """

    name = "anthropic"

    def __init__(self, api_key: str | None = None) -> None:
        # The anthropic SDK reads ANTHROPIC_API_KEY itself when api_key is None;
        # we accept an explicit override so tests can inject deterministic keys.
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(self, request: LlmRequest) -> LlmResponse:
        system_prompt = request.system
        conversation: list[dict[str, str]] = []
        for msg in request.messages:
            if msg.role == "system":
                system_prompt = msg.content if system_prompt is None else system_prompt
                continue
            conversation.append({"role": msg.role, "content": msg.content})

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": conversation,
            "max_tokens": request.max_tokens,
        }
        if request.model not in _MODELS_WITHOUT_TEMPERATURE:
            kwargs["temperature"] = request.temperature
        if system_prompt is not None:
            kwargs["system"] = system_prompt

        started = time.perf_counter()
        try:
            response = await self._client.messages.create(**kwargs)
        except anthropic.APIStatusError as exc:
            raise LlmError(
                f"anthropic api error: {exc.message}",
                provider=self.name,
                model=request.model,
                status_code=exc.status_code,
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise LlmError(
                f"anthropic connection error: {exc}",
                provider=self.name,
                model=request.model,
            ) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        text_parts = [block.text for block in response.content if block.type == "text"]
        if not text_parts:
            raise LlmError(
                "anthropic response contained no text blocks",
                provider=self.name,
                model=request.model,
            )

        return LlmResponse(
            content="".join(text_parts),
            model=response.model,
            provider=self.name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms,
            finish_reason=_map_stop_reason(response.stop_reason),
            raw=response.model_dump(),
        )

    async def count_tokens(self, text: str, model: str) -> int:
        result = await self._client.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": text}],
        )
        return int(result.input_tokens)

    def supported_models(self) -> list[str]:
        return list(_SUPPORTED_MODELS)


def _map_stop_reason(reason: str | None) -> LlmFinishReason:
    if reason in ("end_turn", "stop_sequence"):
        return "stop"
    if reason == "max_tokens":
        return "length"
    if reason == "refusal":
        return "content_filter"
    return "stop" if reason is None else "error"
