from datetime import UTC, datetime

import pytest
from cstack_schemas import TenantConfig
from pydantic import ValidationError

VALID_TENANT_ID = "00000000-0000-0000-0000-000000000001"
VALID_CLIENT_ID = "00000000-0000-0000-0000-000000000002"
VALID_THUMBPRINT = "A" * 40


def _make(**overrides: object) -> TenantConfig:
    base: dict[str, object] = {
        "tenant_id": VALID_TENANT_ID,
        "display_name": "example",
        "client_id": VALID_CLIENT_ID,
        "cert_thumbprint": VALID_THUMBPRINT,
        "cert_subject": "CN=cstack-signalguard",
        "added_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    base.update(overrides)
    return TenantConfig.model_validate(base)


def test_construct_minimum_valid() -> None:
    tenant = _make()
    assert tenant.is_fixture is False
    assert tenant.cert_thumbprint == VALID_THUMBPRINT


def test_thumbprint_normalises_colons_and_case() -> None:
    raw = "aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99:aa:bb:cc:dd"
    tenant = _make(cert_thumbprint=raw)
    assert tenant.cert_thumbprint == "AABBCCDDEEFF00112233445566778899AABBCCDD"


def test_thumbprint_rejects_non_hex() -> None:
    with pytest.raises(ValidationError):
        _make(cert_thumbprint="notavalidthumbprint" * 2 + "xy")


def test_thumbprint_rejects_wrong_length() -> None:
    with pytest.raises(ValidationError):
        _make(cert_thumbprint="ABCD")


def test_tenant_id_rejects_non_uuid() -> None:
    with pytest.raises(ValidationError):
        _make(tenant_id="not-a-uuid")


def test_is_fixture_flag_round_trips() -> None:
    tenant = _make(is_fixture=True)
    assert tenant.is_fixture is True
