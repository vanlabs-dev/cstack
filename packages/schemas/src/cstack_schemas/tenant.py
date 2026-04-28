from datetime import datetime
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
    """Persistent registration record for a tenant in the local cstack store."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tenant_id: str = Field(description="Microsoft Entra tenant UUID")
    display_name: str
    client_id: str = Field(description="Application (client) ID of the cstack app reg")
    cert_thumbprint: str = Field(description="SHA-1 hex of the auth cert, uppercased")
    cert_subject: str
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
    def _normalise_thumbprint(cls, value: str) -> str:
        normalised = value.replace(":", "").replace(" ", "").upper()
        if len(normalised) != 40 or any(c not in "0123456789ABCDEF" for c in normalised):
            raise ValueError("cert_thumbprint must be a 40-char SHA-1 hex string")
        return normalised
