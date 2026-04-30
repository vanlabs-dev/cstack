"""Test fixtures for cstack-ml-anomaly.

Sprint 3.5b gated two ML paths behind env vars
(``CSTACK_ML_TRAINING_TOPOLOGY``, ``CSTACK_ML_OFF_HOURS_ADMIN_ENABLED``).
Tests must opt in explicitly so a CI runner that exports either flag at
the runner level cannot silently activate the gated paths during
unrelated tests. Sprint 3.5b's final report flagged this as the "gate
concern"; Sprint 6.7 closes it with this autouse fixture.
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
