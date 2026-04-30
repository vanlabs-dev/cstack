from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantApiKey(BaseModel):
    """A hashed API key authorised to act on behalf of a tenant.

    Plaintext keys are never persisted: the CLI generates a key, prints it
    once, stores its SHA-256 hex digest here, and forgets the original.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    key_hash: str = Field(description="SHA-256 hex digest of the issued key")
    label: str = Field(description="Human-readable label, e.g. 'gha-dashboard'")
    created_at: datetime

    @field_validator("key_hash")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        normalised = value.lower()
        if len(normalised) != 64 or any(c not in "0123456789abcdef" for c in normalised):
            raise ValueError("key_hash must be a 64-char SHA-256 hex digest")
        return normalised


class TenantConfig(BaseModel):
    """Persistent registration record for a tenant in the local cstack store.

    Sprint 6.7 added PFX-based cert auth (``cert_pfx_path`` plus
    ``cert_pfx_password_env_var``) and made the legacy ``cert_thumbprint``
    field optional. Live tenants registered after Sprint 6.7 use the PFX
    path; fixture tenants keep their synthetic thumbprint string for
    schema continuity. New tenants must supply at least one of the two
    auth sources unless ``is_fixture`` is set.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    tenant_id: str = Field(description="Microsoft Entra tenant UUID")
    display_name: str
    client_id: str = Field(description="Application (client) ID of the cstack app reg")
    cert_thumbprint: str | None = Field(
        default=None,
        description=(
            "SHA-1 hex of the auth cert, uppercased. Legacy field; new tenants "
            "should use cert_pfx_path instead. Kept for fixture compatibility."
        ),
    )
    cert_subject: str
    cert_pfx_path: Path | None = Field(
        default=None,
        description=(
            "Filesystem path to a PFX (PKCS#12) bundle containing the cert plus "
            "private key. Loaded at runtime by the graph-client credentials "
            "module. Path may be absolute or relative to the tenants.json directory."
        ),
    )
    cert_pfx_password_env_var: str | None = Field(
        default=None,
        description=(
            "Name of the environment variable that holds the PFX password. The "
            "password itself is never persisted in tenants.json; cstack reads it "
            "at credential-load time. Set to None for unencrypted PFX files."
        ),
    )
    added_at: datetime
    is_fixture: bool = False
    api_keys: list[TenantApiKey] = Field(default_factory=list)

    @field_validator("tenant_id", "client_id")
    @classmethod
    def _validate_uuid(cls, value: str) -> str:
        # Caller passes a string so persisted JSON stays human-readable;
        # parsing through UUID just enforces canonical form.
        UUID(value)
        return value

    @field_validator("cert_thumbprint")
    @classmethod
    def _normalise_thumbprint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalised = value.replace(":", "").replace(" ", "").upper()
        if len(normalised) != 40 or any(c not in "0123456789ABCDEF" for c in normalised):
            raise ValueError("cert_thumbprint must be a 40-char SHA-1 hex string")
        return normalised
