from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Per-test environment variables that point cstack at scratch paths."""
    db_path = tmp_path / "cstack.duckdb"
    tenants_file = tmp_path / "tenants.json"
    data_dir = tmp_path / "data"
    env = {
        "CSTACK_DB_PATH": str(db_path),
        "CSTACK_TENANTS_FILE": str(tenants_file),
        "CSTACK_DATA_DIR": str(data_dir),
        "CSTACK_LOG_LEVEL": "WARNING",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    yield env
