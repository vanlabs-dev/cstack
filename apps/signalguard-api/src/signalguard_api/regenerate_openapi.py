"""Regenerate ``apps/signalguard-api/openapi.json`` from the live FastAPI app.

Run via ``uv run python -m signalguard_api.regenerate_openapi``. CI also
runs this and asserts no diff so contract drift fails the build.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from signalguard_api.config import Settings
from signalguard_api.main import create_app


def _serialise() -> str:
    app = create_app(settings=Settings(dev_api_key="dev"))
    spec = app.openapi()
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


def main() -> int:
    out = Path(__file__).parent.parent.parent / "openapi.json"
    payload = _serialise()
    out.write_text(payload, encoding="utf-8")
    print(f"wrote {out} ({len(payload)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
