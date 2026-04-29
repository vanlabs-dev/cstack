import pytest
from cstack_llm_provider import LlmError, LlmMessage, LlmRequest
from pydantic import ValidationError


def test_request_defaults() -> None:
    request = LlmRequest(model="claude-opus-4-7", messages=[LlmMessage(role="user", content="hi")])
    assert request.temperature == 0.2
    assert request.max_tokens == 1024
    assert request.system is None


def test_request_rejects_temperature_out_of_range() -> None:
    with pytest.raises(ValidationError):
        LlmRequest(
            model="m",
            messages=[LlmMessage(role="user", content="hi")],
            temperature=3.0,
        )


def test_error_renders_provider_and_status_in_message() -> None:
    err = LlmError("boom", provider="anthropic", model="claude-opus-4-7", status_code=429)
    rendered = str(err)
    assert "anthropic" in rendered
    assert "claude-opus-4-7" in rendered
    assert "429" in rendered
