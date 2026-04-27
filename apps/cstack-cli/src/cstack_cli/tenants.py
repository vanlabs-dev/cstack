import json
from pathlib import Path

from cstack_schemas import TenantConfig


def load_tenants(path: Path) -> list[TenantConfig]:
    """Read tenants.json. Returns an empty list when the file does not exist
    so first-run flows do not need to special-case the path."""
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected a JSON array, got {type(payload).__name__}")
    return [TenantConfig.model_validate(item) for item in payload]


def save_tenants(path: Path, tenants: list[TenantConfig]) -> None:
    """Atomically rewrite tenants.json. Creates the parent dir if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [t.model_dump(mode="json") for t in tenants]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def find_tenant(tenants: list[TenantConfig], identifier: str) -> TenantConfig | None:
    """Match by tenant_id or display_name. Returns the first match or None."""
    for tenant in tenants:
        if tenant.tenant_id == identifier or tenant.display_name == identifier:
            return tenant
    return None
