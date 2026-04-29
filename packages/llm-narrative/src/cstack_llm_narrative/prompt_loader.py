"""Loader for markdown prompt files with YAML-ish frontmatter.

A full YAML parser is overkill: the frontmatter is intentionally
flat key-value with comma-separated lists. Keeping the parser tiny
avoids dragging PyYAML into a package whose only YAML use case is six
lines of metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    version: str
    description: str
    inputs: list[str]
    body: str

    @property
    def filename(self) -> str:
        return f"{self.id}_{self.version}.md"


class PromptNotFoundError(LookupError):
    pass


class PromptInputMissingError(KeyError):
    pass


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a markdown file with leading ``---`` frontmatter into a
    metadata dict and the remaining body. Frontmatter is required: prompts
    without it fail loud at load time, not at render time.
    """

    if not text.startswith("---"):
        raise ValueError("prompt is missing leading frontmatter delimiter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("prompt frontmatter is not closed by a second '---' line")
    raw_meta = parts[1].strip()
    body = parts[2].lstrip("\n")

    meta: dict[str, str] = {}
    for line in raw_meta.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"frontmatter line missing colon: {line!r}")
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body


@lru_cache(maxsize=64)
def load_prompt(prompt_id: str, version: str) -> PromptTemplate:
    path = PROMPTS_DIR / f"{prompt_id}_{version}.md"
    if not path.exists():
        raise PromptNotFoundError(f"prompt not found: {path}")
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    required = {"id", "version", "description", "inputs"}
    missing = required - meta.keys()
    if missing:
        raise ValueError(
            f"prompt {prompt_id}_{version} missing frontmatter keys: {sorted(missing)}"
        )
    if meta["id"] != prompt_id or meta["version"] != version:
        raise ValueError(
            f"prompt frontmatter id/version mismatch for {prompt_id}_{version}: "
            f"got id={meta['id']!r} version={meta['version']!r}"
        )

    inputs = [item.strip() for item in meta["inputs"].split(",") if item.strip()]
    return PromptTemplate(
        id=meta["id"],
        version=meta["version"],
        description=meta["description"],
        inputs=inputs,
        body=body,
    )


def list_prompt_versions(prompt_id: str) -> list[str]:
    if not PROMPTS_DIR.exists():
        return []
    versions: list[str] = []
    for path in PROMPTS_DIR.glob(f"{prompt_id}_*.md"):
        version = path.stem.removeprefix(f"{prompt_id}_")
        versions.append(version)
    return sorted(versions)


def render_prompt(template: PromptTemplate, params: dict[str, object]) -> str:
    """String-substitute ``{key}`` placeholders. Raises if any declared input
    is missing from params; extra keys in params are silently ignored.
    """

    missing = [key for key in template.inputs if key not in params]
    if missing:
        raise PromptInputMissingError(
            f"prompt {template.id}_{template.version} missing inputs: {sorted(missing)}"
        )
    rendered = template.body
    for key in template.inputs:
        placeholder = "{" + key + "}"
        rendered = rendered.replace(placeholder, str(params[key]))
    return rendered
