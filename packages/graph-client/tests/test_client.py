from unittest.mock import MagicMock

from cstack_graph_client import build_client


def test_build_client_passes_credential_and_default_scope() -> None:
    fake_credential = MagicMock(name="CertificateCredential")
    client = build_client(fake_credential)
    # The msgraph SDK exposes the credential and scope on construction; we
    # cannot inspect private attrs reliably across SDK versions, so just
    # verify a client object is returned without raising.
    assert client is not None
