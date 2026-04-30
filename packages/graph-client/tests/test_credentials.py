"""Credential loader tests.

Sprint 6.7 dropped the Windows-cert-store + PowerShell shell-out path;
the only remaining auth flow is PFX file on disk. The fixture below
mints a self-signed cert + PFX bundle in tmp_path so tests exercise
the real loader against a real PFX without needing a Windows-only
runtime or any mocking.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from cstack_graph_client import (
    CertificateNotFoundError,
    load_certificate_credential_for_tenant,
    load_certificate_credential_from_pfx,
    load_pfx_certificate_thumbprint,
)
from cstack_schemas import TenantConfig


def _make_pfx(path: Path, password: str | None = None) -> str:
    """Generate a self-signed cert + PFX at ``path``. Returns SHA-1 thumbprint."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "cstack-test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    encryption = (
        serialization.BestAvailableEncryption(password.encode())
        if password is not None
        else serialization.NoEncryption()
    )
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=b"cstack-test",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=encryption,
    )
    path.write_bytes(pfx_bytes)
    return cert.fingerprint(hashes.SHA1()).hex().upper()


def test_load_pfx_thumbprint_matches_cert(tmp_path: Path) -> None:
    """The thumbprint helper returns the same SHA-1 hex the cert reports."""
    pfx_path = tmp_path / "cert.pfx"
    expected = _make_pfx(pfx_path, password=None)
    assert load_pfx_certificate_thumbprint(pfx_path, password=None) == expected


def test_load_pfx_thumbprint_with_password(tmp_path: Path) -> None:
    pfx_path = tmp_path / "cert.pfx"
    expected = _make_pfx(pfx_path, password="hunter2")
    assert load_pfx_certificate_thumbprint(pfx_path, password="hunter2") == expected


def test_load_pfx_thumbprint_wrong_password_raises(tmp_path: Path) -> None:
    pfx_path = tmp_path / "cert.pfx"
    _make_pfx(pfx_path, password="hunter2")
    # cryptography raises ValueError on wrong password; we don't translate
    # that here because the CLI command surfaces it directly.
    with pytest.raises(ValueError):
        load_pfx_certificate_thumbprint(pfx_path, password="wrong")


def test_load_credential_from_pfx_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(CertificateNotFoundError, match="PFX file not found"):
        load_certificate_credential_from_pfx(
            tenant_id="00000000-0000-0000-0000-000000000001",
            client_id="00000000-0000-0000-0000-000000000002",
            pfx_path=tmp_path / "does-not-exist.pfx",
            password=None,
        )


def test_load_credential_from_pfx_returns_credential(tmp_path: Path) -> None:
    """End-to-end: real PFX, real azure-identity construction."""
    pfx_path = tmp_path / "cert.pfx"
    _make_pfx(pfx_path, password=None)
    credential = load_certificate_credential_from_pfx(
        tenant_id="00000000-0000-0000-0000-000000000001",
        client_id="00000000-0000-0000-0000-000000000002",
        pfx_path=pfx_path,
        password=None,
    )
    # azure-identity's CertificateCredential keeps tenant + client ids on the
    # instance under private attributes; we just assert construction succeeded
    # without inspecting internals.
    assert credential is not None


def test_load_credential_for_tenant_unencrypted_pfx(tmp_path: Path) -> None:
    pfx_path = tmp_path / "tenant.pfx"
    thumbprint = _make_pfx(pfx_path, password=None)
    tenant = TenantConfig(
        tenant_id="00000000-0000-0000-0000-000000000001",
        display_name="Test Tenant",
        client_id="00000000-0000-0000-0000-000000000002",
        cert_thumbprint=thumbprint,
        cert_subject="CN=cstack-test",
        cert_pfx_path=pfx_path,
        cert_pfx_password_env_var=None,
        added_at=datetime.now(UTC),
        is_fixture=False,
    )
    credential = load_certificate_credential_for_tenant(tenant)
    assert credential is not None


def test_load_credential_for_tenant_reads_password_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pfx_path = tmp_path / "tenant.pfx"
    thumbprint = _make_pfx(pfx_path, password="hunter2")
    monkeypatch.setenv("CSTACK_TEST_PFX_PASSWORD", "hunter2")
    tenant = TenantConfig(
        tenant_id="00000000-0000-0000-0000-000000000001",
        display_name="Test Tenant",
        client_id="00000000-0000-0000-0000-000000000002",
        cert_thumbprint=thumbprint,
        cert_subject="CN=cstack-test",
        cert_pfx_path=pfx_path,
        cert_pfx_password_env_var="CSTACK_TEST_PFX_PASSWORD",
        added_at=datetime.now(UTC),
        is_fixture=False,
    )
    credential = load_certificate_credential_for_tenant(tenant)
    assert credential is not None


def test_load_credential_for_tenant_missing_pfx_path_raises() -> None:
    tenant = TenantConfig(
        tenant_id="00000000-0000-0000-0000-000000000001",
        display_name="Test Tenant",
        client_id="00000000-0000-0000-0000-000000000002",
        cert_thumbprint="A" * 40,
        cert_subject="CN=cstack-test",
        cert_pfx_path=None,
        added_at=datetime.now(UTC),
        is_fixture=False,
    )
    with pytest.raises(CertificateNotFoundError, match="no cert_pfx_path"):
        load_certificate_credential_for_tenant(tenant)


def test_load_credential_for_tenant_missing_password_env_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pfx_path = tmp_path / "tenant.pfx"
    thumbprint = _make_pfx(pfx_path, password="hunter2")
    monkeypatch.delenv("CSTACK_MISSING_PFX_PASSWORD", raising=False)
    tenant = TenantConfig(
        tenant_id="00000000-0000-0000-0000-000000000001",
        display_name="Test Tenant",
        client_id="00000000-0000-0000-0000-000000000002",
        cert_thumbprint=thumbprint,
        cert_subject="CN=cstack-test",
        cert_pfx_path=pfx_path,
        cert_pfx_password_env_var="CSTACK_MISSING_PFX_PASSWORD",
        added_at=datetime.now(UTC),
        is_fixture=False,
    )
    with pytest.raises(CertificateNotFoundError, match="is unset"):
        load_certificate_credential_for_tenant(tenant)
