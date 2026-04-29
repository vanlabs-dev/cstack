"""MLflow tracking helpers.

Resolution order for the tracking URI:

1. Explicit ``uri`` argument (highest priority; tests inject deterministic
   in-memory or per-test paths via this).
2. ``MLFLOW_TRACKING_URI`` environment variable (containers and CI set this).
3. SQLite at ``./mlruns/mlflow.sqlite`` (default for production paths;
   multi-process safe and works under Compose bind mounts).

The historical file:// backend remains available by passing it explicitly
or via the env var; tests still use it because per-test ``tmp_path``
filesystems are simpler than per-test SQLite databases.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import mlflow

DEFAULT_EXPERIMENT = "signalguard"
SPRINT_TAG_VALUE = "3"


def _default_tracking_uri() -> str:
    """SQLite at ``./mlruns/mlflow.sqlite``; mlruns dir created if absent."""
    mlruns = Path.cwd() / "mlruns"
    mlruns.mkdir(parents=True, exist_ok=True)
    db_path = (mlruns / "mlflow.sqlite").resolve()
    # MLflow's SQLite scheme is sqlite:/// for absolute paths; on Windows the
    # absolute path already starts with a drive letter, so we need an extra
    # slash to keep the URI shape correct (``sqlite:///C:/...``).
    return f"sqlite:///{db_path.as_posix()}"


def configure_tracking(
    uri: str | None = None,
    experiment_name: str = DEFAULT_EXPERIMENT,
    tracking_uri: str | None = None,
) -> str:
    """Set tracking URI and experiment. Returns the resolved tracking URI.

    The legacy ``uri`` keyword is still accepted for backwards compatibility
    with the rest of the codebase; ``tracking_uri`` is the new canonical
    spelling that matches the env var and Compose service config.

    Resolution order (described in the module docstring): explicit argument,
    then ``MLFLOW_TRACKING_URI``, then a SQLite fallback. Creates the
    experiment if it does not exist; idempotent.
    """

    explicit = tracking_uri if tracking_uri is not None else uri
    if explicit is not None:
        resolved = explicit
    else:
        env_uri = os.environ.get("MLFLOW_TRACKING_URI")
        resolved = env_uri or _default_tracking_uri()
    mlflow.set_tracking_uri(resolved)
    mlflow.set_experiment(experiment_name)
    return resolved


def standard_tags(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Tags every run picks up so the registry stays groupable."""
    tags: dict[str, str] = {
        "cstack.sprint": SPRINT_TAG_VALUE,
        "cstack.module": "signalguard",
    }
    if extra:
        tags.update(extra)
    return tags


def start_run(
    run_name: str,
    tags: dict[str, str] | None = None,
    nested: bool = False,
) -> Any:
    """Thin wrapper around mlflow.start_run that injects standard tags."""
    return mlflow.start_run(
        run_name=run_name,
        tags=standard_tags(tags),
        nested=nested,
    )
