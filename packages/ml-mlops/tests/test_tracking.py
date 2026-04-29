from __future__ import annotations

from pathlib import Path

import pytest
from cstack_ml_mlops.tracking import (
    _default_tracking_uri,
    configure_tracking,
)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Each test starts with no MLFLOW_TRACKING_URI and a clean cwd."""
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.chdir(tmp_path)


def test_explicit_uri_wins_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "sqlite:///from-env.db")
    resolved = configure_tracking(tracking_uri="sqlite:///explicit.db")
    assert resolved == "sqlite:///explicit.db"


def test_legacy_uri_kwarg_still_accepted() -> None:
    resolved = configure_tracking(uri="sqlite:///legacy.db")
    assert resolved == "sqlite:///legacy.db"


def test_env_uri_used_when_no_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "sqlite:///from-env.db")
    resolved = configure_tracking()
    assert resolved == "sqlite:///from-env.db"


def test_default_falls_back_to_sqlite_under_mlruns(tmp_path: Path) -> None:
    resolved = configure_tracking()
    assert resolved.startswith("sqlite:///")
    assert "mlruns/mlflow.sqlite" in resolved
    assert (tmp_path / "mlruns").exists()


def test_default_uri_creates_mlruns_dir(tmp_path: Path) -> None:
    assert not (tmp_path / "mlruns").exists()
    _default_tracking_uri()
    assert (tmp_path / "mlruns").exists()


def test_in_memory_sqlite_supported() -> None:
    """The :memory: form is valid; useful for unit tests that need a fresh
    registry per test without spilling files to disk.
    """

    resolved = configure_tracking(tracking_uri="sqlite:///:memory:")
    assert resolved == "sqlite:///:memory:"


def test_file_uri_still_supported(tmp_path: Path) -> None:
    """Tests and CI continue to use file:// URIs; the helper does not
    second-guess explicitly-passed schemes.
    """

    file_uri = (tmp_path / "mlruns").resolve().as_uri()
    resolved = configure_tracking(tracking_uri=file_uri)
    assert resolved == file_uri


def test_env_var_with_empty_string_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty MLFLOW_TRACKING_URI in the environment should not shadow the
    fallback. Some shells leak empty env vars; the resolution order
    treats empty as absent.
    """

    monkeypatch.setenv("MLFLOW_TRACKING_URI", "")
    resolved = configure_tracking()
    assert resolved.startswith("sqlite:///")
    assert "mlflow.sqlite" in resolved
