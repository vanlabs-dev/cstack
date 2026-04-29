import time
from typing import Any

import openai
import tiktoken

from cstack_llm_provider.types import (
    LlmError,
    LlmFinishReason,
    LlmRequest,
    LlmResponse,
)

_SUPPORTED_MODELS = [
    "gpt-5-mini",
    "gpt-4o",
    "gpt-4o-mini",
]


class OpenAIProvider:
    """Maps ``LlmRequest`` onto the OpenAI Chat Completions API.

    OpenAI's model expects the system prompt as a leading message with
    ``role=system`` rather than a top-level field, which is the inverse of
    Anthropic's convention. The adapter normalises by promoting
    ``LlmRequest.system`` into a leading system message.
    """

    name = "openai"

    def __init__(self, api_key: str | None = None) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(self, request: LlmRequest) -> LlmResponse:
        messages: list[dict[str, str]] = []
        if request.system is not None:
            messages.append({"role": "system", "content": request.system})
        messages.extend({"role": m.role, "content": m.content} for m in request.messages)

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        started = time.perf_counter()
        try:
            response = await self._client.chat.completions.create(**kwargs)
        except openai.APIStatusError as exc:
            raise LlmError(
                f"openai api error: {exc.message}",
                provider=self.name,
                model=request.model,
                status_code=exc.status_code,
            ) from exc
        except openai.APIConnectionError as exc:
            raise LlmError(
                f"openai connection error: {exc}",
                provider=self.name,
                model=request.model,
            ) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        if not response.choices:
            raise LlmError(
                "openai response had no choices",
                provider=self.name,
                model=request.model,
            )
        choice = response.choices[0]
        content = choice.message.content or ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        return LlmResponse(
            content=content,
            model=response.model,
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            finish_reason=_map_finish_reason(choice.finish_reason),
            raw=response.model_dump(),
        )

    async def count_tokens(self, text: str, model: str) -> int:
        # tiktoken's encoding_for_model raises on unknown models; for newer OpenAI
        # models without a registered tokenizer, cl100k_base remains the closest
        # public approximation.
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

    def supported_models(self) -> list[str]:
        return list(_SUPPORTED_MODELS)


def _map_finish_reason(reason: str | None) -> LlmFinishReason:
    if reason == "stop":
        return "stop"
    if reason == "length":
        return "length"
    if reason == "content_filter":
        return "content_filter"
    return "stop" if reason is None else "error"
