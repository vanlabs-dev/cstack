import pytest
from cstack_llm_provider import clear_registry


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    clear_registry()
