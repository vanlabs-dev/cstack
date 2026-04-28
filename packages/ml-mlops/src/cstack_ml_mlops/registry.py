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
    """Register a model artifact under ``name``. Returns the ModelVersion."""
    model_uri = f"runs:/{run_id}/{artifact_path}"
    return mlflow.register_model(model_uri, name)


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
