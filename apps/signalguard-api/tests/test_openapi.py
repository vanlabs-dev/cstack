"""OpenAPI stability and quality checks.

These guard against silent API contract drift. The committed
``openapi.json`` becomes a build artefact for the frontend client
generator in Sprint 5; any change to a Pydantic schema, router signature,
or tag must be reflected in a regen step.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from signalguard_api.config import Settings
from signalguard_api.main import create_app

_OPENAPI_PATH = Path(__file__).parent.parent / "openapi.json"


def _normalise(spec: dict[str, Any]) -> str:
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


def _spec() -> dict[str, Any]:
    """Build the OpenAPI spec the same way ``scripts/regen-openapi`` does."""
    app = create_app(settings=Settings(dev_api_key="dev"))
    return app.openapi()


def test_openapi_spec_matches_committed_artefact() -> None:
    if not _OPENAPI_PATH.exists():
        pytest.skip("openapi.json has not been committed yet")
    expected = _OPENAPI_PATH.read_text(encoding="utf-8")
    actual = _normalise(_spec())
    assert actual == expected, (
        "openapi.json drifted. Regenerate via "
        "`uv run python -m signalguard_api.regenerate_openapi` and commit."
    )


def test_every_endpoint_has_a_summary() -> None:
    spec = _spec()
    missing: list[str] = []
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            if not op.get("summary"):
                missing.append(f"{method.upper()} {path}")
    assert not missing, f"endpoints missing summary: {missing}"


def test_every_endpoint_has_at_least_one_tag() -> None:
    spec = _spec()
    untagged: list[str] = []
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            tags = op.get("tags", [])
            if not tags:
                untagged.append(f"{method.upper()} {path}")
    assert not untagged, f"endpoints missing tag: {untagged}"


def test_top_level_tags_have_descriptions() -> None:
    spec = _spec()
    missing = [t["name"] for t in spec.get("tags", []) if not t.get("description")]
    assert not missing, f"top-level tags missing description: {missing}"
