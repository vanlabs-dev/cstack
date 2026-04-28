from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for signalguard-api.

    Environment variables are prefixed with ``SIGNALGUARD_API_`` so they do
    not collide with the cstack CLI's ``CSTACK_`` prefix when both run in the
    same shell.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SIGNALGUARD_API_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_path: Path = Path("./data/cstack.duckdb")
    tenants_file: Path = Path("./tenants.json")
    mlflow_tracking_uri: str | None = None
    dev_api_key: str | None = None
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    log_level: str = "INFO"
    request_timeout_seconds: int = 30


@lru_cache
def get_settings() -> Settings:
    """FastAPI dependency. Cached so repeated injections hit the same object."""
    return Settings()
