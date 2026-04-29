from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

LlmRole = Literal["system", "user", "assistant"]
LlmFinishReason = Literal["stop", "length", "content_filter", "error"]


class LlmMessage(BaseModel):
    """A single message in a conversation. Anthropic treats system as a top-level
    field, not a message; use ``LlmRequest.system`` for it. ``role="system"``
    appearing here is supported for OpenAI-style chats and is mapped by adapters.
    """

    model_config = ConfigDict(frozen=True)

    role: LlmRole
    content: str


class LlmRequest(BaseModel):
    """A provider-agnostic completion request."""

    model_config = ConfigDict(frozen=True)

    model: str
    messages: list[LlmMessage]
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)
    system: str | None = None


class LlmResponse(BaseModel):
    """A provider-agnostic completion response."""

    model_config = ConfigDict(frozen=True)

    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    finish_reason: LlmFinishReason
    raw: dict[str, Any]


class LlmError(Exception):
    """Wraps provider-side failures with provider/model context. Adapters raise
    this for rate limits, auth errors, server errors, and malformed responses so
    callers handle one exception type regardless of which SDK threw originally.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.status_code = status_code
        suffix = f" [{provider}"
        if model:
            suffix += f"/{model}"
        if status_code is not None:
            suffix += f" status={status_code}"
        suffix += "]"
        super().__init__(message + suffix)
