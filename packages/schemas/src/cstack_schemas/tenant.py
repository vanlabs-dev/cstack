from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
