import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from cstack_graph_client import CertificateNotFoundError, load_certificate_credential


@pytest.mark.skipif(sys.platform != "win32", reason="windows-only path")
def test_missing_thumbprint_raises_certificate_not_found() -> None:
    """When PowerShell exits 2 (cert not found), surface a typed error."""

    class FakeCompleted:
        returncode = 2
        stdout = b""
        stderr = b""

    with (
        patch("cstack_graph_client.credentials.subprocess.run", return_value=FakeCompleted()),
        pytest.raises(CertificateNotFoundError),
    ):
        load_certificate_credential(
            tenant_id="00000000-0000-0000-0000-000000000001",
            client_id="00000000-0000-0000-0000-000000000002",
            cert_thumbprint="A" * 40,
        )


@pytest.mark.skipif(sys.platform == "win32", reason="non-windows path")
def test_non_windows_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        load_certificate_credential(
            tenant_id="00000000-0000-0000-0000-000000000001",
            client_id="00000000-0000-0000-0000-000000000002",
            cert_thumbprint="A" * 40,
        )


def test_pfx_loader_delegates_to_certificate_credential(tmp_path: Path) -> None:
    """The PFX-based loader passes through to azure-identity's
    CertificateCredential without inspecting the PFX itself; verify the
    constructor is called with the expected kwargs."""
    from cstack_graph_client import load_certificate_credential_from_pfx

    pfx_path = tmp_path / "fake.pfx"
    pfx_path.write_bytes(b"")

    with patch("cstack_graph_client.credentials.CertificateCredential") as mock_cred:
        load_certificate_credential_from_pfx(
            tenant_id="00000000-0000-0000-0000-000000000001",
            client_id="00000000-0000-0000-0000-000000000002",
            pfx_path=pfx_path,
            password="example",
        )

    mock_cred.assert_called_once()
    kwargs = mock_cred.call_args.kwargs
    assert kwargs["tenant_id"] == "00000000-0000-0000-0000-000000000001"
    assert kwargs["client_id"] == "00000000-0000-0000-0000-000000000002"
    assert kwargs["certificate_path"] == str(pfx_path)
    assert kwargs["password"] == "example"
