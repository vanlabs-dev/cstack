"""MLflow tracking helpers. File-backed only; no tracking server.

Defaults to ``file://./mlruns`` so a fresh checkout becomes a working
tracking environment without configuration. Override via
``configure_tracking(uri=...)`` to point at a remote tracking server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mlflow

DEFAULT_EXPERIMENT = "signalguard"
SPRINT_TAG_VALUE = "3"


def configure_tracking(
    uri: str | None = None,
    experiment_name: str = DEFAULT_EXPERIMENT,
) -> str:
    """Set tracking URI and experiment. Returns the resolved tracking URI.

    Creates the experiment if it does not exist. Idempotent so repeat calls
    from CLI invocations are safe.
    """
    resolved = uri or f"file://{(Path.cwd() / 'mlruns').as_posix()}"
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
