"""Certificate credential loading.

Sprint 6.7 dropped the Windows-cert-store + PowerShell shell-out path
in favour of explicit PFX (PKCS#12) files on disk. The PFX path lives
in ``TenantConfig.cert_pfx_path`` and the password is read at
credential-load time from the env var named in
``TenantConfig.cert_pfx_password_env_var`` (or absent for unencrypted
PFX files). Onboarding adds one explicit step ("export the cert as a
PFX") and removes the brittle subprocess boundary that fought with
PowerShell Execution Policy on dev machines.
"""

from __future__ import annotations

import os
from pathlib import Path

from azure.identity import CertificateCredential
from cryptography.hazmat.primitives.serialization import pkcs12
from cstack_schemas import TenantConfig

from cstack_graph_client.exceptions import CertificateNotFoundError


def load_certificate_credential_from_pfx(
    tenant_id: str,
    client_id: str,
    pfx_path: Path,
    password: str | None,
) -> CertificateCredential:
    """Build a CertificateCredential from a PFX file on disk.

    ``password`` is forwarded directly to azure-identity. Pass ``None``
    for an unencrypted PFX; the SDK accepts that form.
    """
    if not pfx_path.exists():
        raise CertificateNotFoundError(f"PFX file not found: {pfx_path}")
    return CertificateCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        certificate_path=str(pfx_path),
        password=password,
    )


def load_certificate_credential_for_tenant(
    tenant: TenantConfig,
) -> CertificateCredential:
    """Build a CertificateCredential for ``tenant`` using its configured PFX.

    Reads the PFX password from the env var named in
    ``tenant.cert_pfx_password_env_var`` if set; passes None otherwise.
    Raises ``CertificateNotFoundError`` when the tenant has no PFX
    configured (e.g. a fixture tenant accidentally routed through the
    live-credential path).
    """
    if tenant.cert_pfx_path is None:
        raise CertificateNotFoundError(
            f"tenant {tenant.tenant_id} has no cert_pfx_path configured; "
            "register the tenant with --cert-pfx-path before live extract"
        )
    password: str | None = None
    if tenant.cert_pfx_password_env_var is not None:
        password = os.environ.get(tenant.cert_pfx_password_env_var)
        if password is None:
            raise CertificateNotFoundError(
                f"env var {tenant.cert_pfx_password_env_var!r} (configured as "
                f"the PFX password source for tenant {tenant.tenant_id}) is unset"
            )
    return load_certificate_credential_from_pfx(
        tenant_id=tenant.tenant_id,
        client_id=tenant.client_id,
        pfx_path=tenant.cert_pfx_path,
        password=password,
    )


def load_pfx_certificate_thumbprint(pfx_path: Path, password: str | None) -> str:
    """Return the SHA-1 thumbprint of the cert inside a PFX file.

    Useful for tenant onboarding: the user supplies a PFX, cstack
    derives and records the thumbprint so live request signing can be
    verified against the App Registration's known cert. The PFX itself
    is the source of truth at runtime.
    """
    from cryptography.hazmat.primitives import hashes

    pfx_bytes = pfx_path.read_bytes()
    pfx_pwd = password.encode() if password is not None else None
    _key, cert, _additional = pkcs12.load_key_and_certificates(pfx_bytes, pfx_pwd)
    if cert is None:
        raise CertificateNotFoundError(f"PFX at {pfx_path} did not contain a certificate")
    return cert.fingerprint(hashes.SHA1()).hex().upper()
