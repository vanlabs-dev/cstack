from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment and ``.env``.

    Environment variables are prefixed with ``CSTACK_`` so they do not collide
    with unrelated tooling running in the same shell.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CSTACK_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Path("./data")
    log_level: str = "INFO"
    tenants_file: Path = Path("./tenants.json")
    db_path: Path = Path("./data/cstack.duckdb")
