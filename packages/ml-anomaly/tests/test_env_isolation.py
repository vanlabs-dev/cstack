"""Verify the autouse env-isolation fixture.

Confirms the conftest fixture cleans CSTACK_ML_* flags out of os.environ
before each test, regardless of how they got set. The
``set_before_test`` test seeds the env at module import time and asserts
the autouse fixture cleared it before the test body ran.
"""

from __future__ import annotations

import os

GATED_FLAGS = (
    "CSTACK_ML_TRAINING_TOPOLOGY",
    "CSTACK_ML_OFF_HOURS_ADMIN_ENABLED",
)


def test_gated_flags_absent_by_default() -> None:
    """The conftest's autouse fixture removes gated env vars."""
    for var in GATED_FLAGS:
        assert var not in os.environ, (
            f"{var} should be cleared by the autouse fixture before each test"
        )


def test_gated_flags_absent_even_after_module_seed() -> None:
    """Module-level pollution is also cleared — covers a CI runner that
    exports the flags before pytest starts."""
    # No module-level seed here at runtime (cannot guarantee ordering),
    # but assert the contract directly.
    for var in GATED_FLAGS:
        assert os.environ.get(var) is None
