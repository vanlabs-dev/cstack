"""MLflow tracking helpers.

Resolution order for the tracking URI:

1. Explicit ``uri`` argument (highest priority; tests inject deterministic
   in-memory or per-test paths via this).
2. ``MLFLOW_TRACKING_URI`` environment variable (containers and CI set this).
3. SQLite at ``./mlruns/mlflow.sqlite`` (default for production paths;
   multi-process safe and works under Compose bind mounts).

Artifact location resolution:

1. Explicit ``artifact_location`` argument when supplied.
2. ``MLFLOW_ARTIFACT_ROOT`` environment variable when set.
3. Derived from the tracking URI when it is ``sqlite:///``: artifacts
   land in ``<sqlite-dir>/artifacts``.

Setting an explicit artifact_location is what removed the
``working_dir: /data`` Compose hack: with no artifact_location MLflow
writes ``./mlruns/<run>/artifacts`` relative to cwd, which forced every
CLI bootstrap container to chdir to /data. Pinning the location keeps
artifacts on the bind mount regardless of cwd.

The historical file:// backend remains available by passing it
explicitly or via the env var; tests still use it because per-test
``tmp_path`` filesystems are simpler than per-test SQLite databases.
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


def _resolve_artifact_location(explicit: str | None, tracking_uri: str) -> str | None:
    """Pick an artifact_location to pin against the experiment.

    Returns None when no source can supply one (e.g. file:// tracking
    URIs leave artifacts in their colocated subtree, which already has
    a stable layout).
    """
    if explicit is not None:
        return explicit
    env = os.environ.get("MLFLOW_ARTIFACT_ROOT")
    if env:
        return env
    if tracking_uri.startswith("sqlite:///"):
        sqlite_path = Path(tracking_uri.replace("sqlite:///", "", 1))
        artifact_dir = (sqlite_path.parent / "artifacts").resolve()
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return artifact_dir.as_uri()
    return None


def configure_tracking(
    uri: str | None = None,
    experiment_name: str = DEFAULT_EXPERIMENT,
    tracking_uri: str | None = None,
    artifact_location: str | None = None,
) -> str:
    """Set tracking URI and experiment. Returns the resolved tracking URI.

    The legacy ``uri`` keyword is still accepted for backwards compatibility
    with the rest of the codebase; ``tracking_uri`` is the new canonical
    spelling that matches the env var and Compose service config.

    Resolution order (described in the module docstring): explicit argument,
    then ``MLFLOW_TRACKING_URI``, then a SQLite fallback. Creates the
    experiment if it does not exist; idempotent.

    ``artifact_location`` (or the ``MLFLOW_ARTIFACT_ROOT`` env var) pins
    the experiment's artifact storage path so it does not default to
    ``./mlruns/<run>/artifacts`` relative to cwd.
    """

    explicit = tracking_uri if tracking_uri is not None else uri
    if explicit is not None:
        resolved = explicit
    else:
        env_uri = os.environ.get("MLFLOW_TRACKING_URI")
        resolved = env_uri or _default_tracking_uri()
    mlflow.set_tracking_uri(resolved)
    artifact_loc = _resolve_artifact_location(artifact_location, resolved)
    if artifact_loc is not None:
        # artifact_location only sticks at create-time. Look up the
        # experiment first; create it with the location only when it
        # does not yet exist. If it already exists with a different
        # location MLflow keeps the original.
        existing = mlflow.get_experiment_by_name(experiment_name)
        if existing is None:
            mlflow.create_experiment(experiment_name, artifact_location=artifact_loc)
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
