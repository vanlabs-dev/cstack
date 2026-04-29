"""Loader for the hand-curated golden-set examples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cstack_audit_core import Finding

DATA_DIR = Path(__file__).parent.parent.parent / "data"
GOLDEN_SET_PATH = DATA_DIR / "golden_set.json"


@dataclass(frozen=True)
class GoldenExample:
    """One hand-curated finding plus its gold-standard narrative.

    The reference narrative is the human ceiling the eval harness compares
    LLM-generated narratives against in pairwise mode.
    """

    finding: Finding
    reference_narrative: str
    scenario_notes: str


def load_golden_set(path: Path | None = None) -> list[GoldenExample]:
    """Read the JSON golden set into dataclasses. Defaults to the bundled file."""
    target = path if path is not None else GOLDEN_SET_PATH
    if not target.exists():
        raise FileNotFoundError(
            f"golden set not found at {target}; run cstack narrative golden-init"
        )
    raw = json.loads(target.read_text(encoding="utf-8"))
    out: list[GoldenExample] = []
    for entry in raw:
        finding = Finding.model_validate(entry["finding"])
        out.append(
            GoldenExample(
                finding=finding,
                reference_narrative=entry["reference_narrative"],
                scenario_notes=entry.get("scenario_notes", ""),
            )
        )
    return out
