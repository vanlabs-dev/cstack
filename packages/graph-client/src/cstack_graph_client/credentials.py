import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

from azure.identity import CertificateCredential
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

from cstack_graph_client.exceptions import CertificateNotFoundError


def load_certificate_credential(
    tenant_id: str,
    client_id: str,
    cert_thumbprint: str,
) -> CertificateCredential:
    """Build a CertificateCredential from the Windows current-user cert store.

    Looks up the cert by thumbprint in ``Cert:\\CurrentUser\\My``, exports the
    private key and cert chain, and constructs an azure-identity credential
    backed by the resulting PEM bytes. Provisional implementation: it shells
    out to PowerShell because that avoids a hard pywin32 dependency for
    Sprint 1; revisit for Sprint 7 when this path goes live.

    On non-Windows platforms raises ``NotImplementedError``; use
    :func:`load_certificate_credential_from_pfx` instead.
    """
    if sys.platform != "win32":
        raise NotImplementedError(
            "Windows certificate-store lookup is Windows-only; use "
            "load_certificate_credential_from_pfx on this platform"
        )
    pem_bytes = _export_pem_from_windows_store(cert_thumbprint)
    return CertificateCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        certificate_data=pem_bytes,
    )


def load_certificate_credential_from_pfx(
    tenant_id: str,
    client_id: str,
    pfx_path: Path,
    password: str,
) -> CertificateCredential:
    """Build a CertificateCredential from a PFX file on disk."""
    return CertificateCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        certificate_path=str(pfx_path),
        password=password,
    )


def _export_pem_from_windows_store(thumbprint: str) -> bytes:
    """Export a CurrentUser\\My cert + private key as PEM bytes.

    PowerShell's ``Export-PfxCertificate`` is the most portable way to get
    private-key material out of the cert store without taking on pywin32 as a
    Windows-only Python dependency for the whole project. The PFX is written
    to a tempdir, parsed back into PEM via ``cryptography``, and the temp dir
    is removed when the function returns.
    """
    normalised = thumbprint.replace(":", "").replace(" ", "").upper()
    transient_password = secrets.token_urlsafe(24)
    with tempfile.TemporaryDirectory() as tmp_dir:
        pfx_path = Path(tmp_dir) / "cstack-export.pfx"
        ps_command = (
            f"$cert = Get-Item -Path 'Cert:\\CurrentUser\\My\\{normalised}' "
            "-ErrorAction SilentlyContinue; "
            "if (-not $cert) { exit 2 }; "
            f"Export-PfxCertificate -Cert $cert -FilePath '{pfx_path}' "
            f"-Password (ConvertTo-SecureString -String '{transient_password}' "
            "-AsPlainText -Force) | Out-Null"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_command],
            capture_output=True,
            check=False,
        )
        if completed.returncode == 2:
            raise CertificateNotFoundError(f"certificate {normalised} not found in CurrentUser\\My")
        if completed.returncode != 0:
            raise CertificateNotFoundError(
                "PowerShell export failed: " + completed.stderr.decode(errors="replace").strip()
            )
        if not pfx_path.exists():
            raise CertificateNotFoundError(
                f"PowerShell did not produce a PFX for thumbprint {normalised}"
            )
        pfx_bytes = pfx_path.read_bytes()
    return _pfx_to_pem(pfx_bytes, transient_password.encode())


def _pfx_to_pem(pfx_bytes: bytes, password: bytes) -> bytes:
    private_key, cert, additional_certs = pkcs12.load_key_and_certificates(pfx_bytes, password)
    if private_key is None or cert is None:
        raise CertificateNotFoundError("PFX did not contain both a private key and a certificate")
    pem_segments: list[bytes] = [
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        cert.public_bytes(serialization.Encoding.PEM),
    ]
    pem_segments.extend(c.public_bytes(serialization.Encoding.PEM) for c in additional_certs)
    return b"".join(pem_segments)
