"""MLflow model registry helpers using the modern aliases API.

Stages (Staging/Production) are deprecated; we use aliases @champion and
@challenger so promotion is a single set_alias call rather than a state
transition. This also keeps numbered versions intact for rollback.
"""

from __future__ import annotations

from typing import Any

import mlflow
from mlflow.tracking import MlflowClient

CHAMPION_ALIAS = "champion"
CHALLENGER_ALIAS = "challenger"


def register_model(run_id: str, artifact_path: str, name: str) -> Any:
    """Register a model artifact under ``name``. Returns the ModelVersion.

    Works with both sklearn-flavour models (logged via
    ``mlflow.sklearn.log_model``) and generic artifacts (logged via
    ``mlflow.log_artifact``). For the generic case we go through
    ``MlflowClient.create_model_version`` because ``mlflow.register_model``
    requires a logged_model entry under the run.
    """
    client = MlflowClient()
    # Idempotent: if the registered model already exists this raises; we
    # swallow that and reuse the existing entry. The backend may emit
    # either an ``MlflowException`` ("already exists") or ``RestException``
    # ("RESOURCE_ALREADY_EXISTS") depending on tracking store flavour.
    try:
        client.create_registered_model(name)
    except mlflow.exceptions.RestException:
        pass
    except mlflow.exceptions.MlflowException as exc:
        msg = str(exc).lower()
        if "already exists" not in msg and "resource_already_exists" not in msg:
            raise
    run = client.get_run(run_id)
    source = f"{run.info.artifact_uri}/{artifact_path}"
    return client.create_model_version(name=name, source=source, run_id=run_id)


def set_alias(model_name: str, version: str | int, alias: str) -> None:
    """Move ``alias`` to ``version`` of ``model_name``."""
    client = MlflowClient()
    client.set_registered_model_alias(model_name, alias, str(version))


def get_alias_version(model_name: str, alias: str) -> Any:
    """Return the ModelVersion currently pointed at by alias, or None."""
    client = MlflowClient()
    try:
        return client.get_model_version_by_alias(model_name, alias)
    except mlflow.exceptions.RestException:
        return None
    except mlflow.exceptions.MlflowException as exc:
        # Local file-backend raises a generic exception when alias missing.
        if "RESOURCE_DOES_NOT_EXIST" in str(exc) or "not found" in str(exc).lower():
            return None
        raise


def load_by_alias(model_name: str, alias: str) -> Any:
    """Load a sklearn model by alias. Raises if alias not set."""
    return mlflow.sklearn.load_model(f"models:/{model_name}@{alias}")


def download_artifact_by_alias(model_name: str, alias: str) -> str:
    """Download the registered model's artifact directory and return its path.

    Useful when the registered artefact is not in the sklearn flavour
    (e.g. a joblib-serialised wrapper bundle that callers need to load
    with ``joblib.load``). The returned path points at the directory the
    artefact was logged under at training time.
    """
    return mlflow.artifacts.download_artifacts(f"models:/{model_name}@{alias}")


def search_registered_models(name_prefix: str | None = None) -> list[Any]:
    """Return RegisteredModel objects, optionally filtered by name prefix.

    Used by the API to enumerate models for a tenant. The MLflow file
    backend supports a SQL-like ``filter_string``; the REST backend supports
    the same string syntax.
    """
    client = MlflowClient()
    filter_string = f"name LIKE '{name_prefix}%'" if name_prefix else ""
    return list(client.search_registered_models(filter_string=filter_string))


def list_model_versions(model_name: str) -> list[Any]:
    """Return every ModelVersion for ``model_name`` ordered newest-first."""
    client = MlflowClient()
    versions = client.search_model_versions(filter_string=f"name='{model_name}'")
    return sorted(versions, key=lambda v: int(v.version), reverse=True)


def get_run_metrics(run_id: str) -> dict[str, float]:
    """Read the final metrics dict from a finished run, or {} on missing."""
    client = MlflowClient()
    try:
        run = client.get_run(run_id)
    except (mlflow.exceptions.RestException, mlflow.exceptions.MlflowException):
        return {}
    return dict(run.data.metrics or {})
