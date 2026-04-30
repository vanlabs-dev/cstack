"""Test fixtures for cstack-ml-features.

Mirrors the autouse env-isolation fixture from cstack-ml-anomaly so
ML feature-flag leaks from CI runners cannot affect feature-pipeline
tests either. See packages/ml-anomaly/tests/conftest.py for the
Sprint 3.5b motivation.
"""

from __future__ import annotations

import pytest

_GATED_FLAGS = (
    "CSTACK_ML_TRAINING_TOPOLOGY",
    "CSTACK_ML_OFF_HOURS_ADMIN_ENABLED",
)


@pytest.fixture(autouse=True)
def isolate_cstack_ml_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scrub ML feature flags before each test; tests opt in explicitly."""
    for var in _GATED_FLAGS:
        monkeypatch.delenv(var, raising=False)
