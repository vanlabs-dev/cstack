"""API response shapes for the /tenants/{id}/api-keys endpoints.

The plaintext key is returned once at create time and never persisted.
List responses expose only label and metadata, never the hash itself.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(default="default", min_length=1, max_length=64)


class ApiKeyCreateResponse(BaseModel):
    """First-and-only-time view of a freshly minted API key."""

    model_config = ConfigDict(frozen=True)

    key: str
    key_label: str
    created_at: datetime


class ApiKeySummary(BaseModel):
    """Listing entry. Hash and plaintext are never exposed."""

    model_config = ConfigDict(frozen=True)

    label: str
    created_at: datetime
