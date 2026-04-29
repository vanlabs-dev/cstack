import os
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_env_file_overriding_empty() -> None:
    """Populate os.environ from the nearest .env, but only for keys that are
    missing or empty. Some shell environments leak through empty
    ANTHROPIC_API_KEY values; pydantic-settings reads the empty env var
    rather than the .env, which silently breaks credential loading. This
    helper loads .env with override semantics that win against empty env
    values without clobbering anything genuinely set upstream.
    """

    candidates = (
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[5] / ".env",
    )
    for path in candidates:
        if path.exists():
            for key, value in dotenv_values(path).items():
                if value is None:
                    continue
                if not os.environ.get(key):
                    os.environ[key] = value
            return


_load_env_file_overriding_empty()


class LlmProviderSettings(BaseSettings):
    """Provider configuration, sourced from environment + .env.

    Provider-native env var names (``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``,
    ``OLLAMA_BASE_URL``) are kept unprefixed so the adapters interop with
    standard tooling. cstack-specific knobs use the ``CSTACK_LLM_`` prefix
    to avoid collision.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    cstack_llm_provider: str = Field(default="anthropic", alias="CSTACK_LLM_PROVIDER")
    cstack_llm_budget_usd: float = Field(default=1.0, alias="CSTACK_LLM_BUDGET_USD")
    cstack_llm_narrative_enabled: bool = Field(default=True, alias="CSTACK_LLM_NARRATIVE_ENABLED")
    cstack_llm_default_model: str = Field(
        default="claude-opus-4-7", alias="CSTACK_LLM_DEFAULT_MODEL"
    )
    cstack_llm_judge_model: str = Field(default="claude-sonnet-4-6", alias="CSTACK_LLM_JUDGE_MODEL")


@lru_cache
def get_settings() -> LlmProviderSettings:
    return LlmProviderSettings()
