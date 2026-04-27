from azure.identity import CertificateCredential
from msgraph import GraphServiceClient  # type: ignore[attr-defined]

DEFAULT_SCOPES: tuple[str, ...] = ("https://graph.microsoft.com/.default",)


def build_client(credential: CertificateCredential) -> GraphServiceClient:
    """Build a Microsoft Graph client backed by the given certificate credential."""
    return GraphServiceClient(credentials=credential, scopes=list(DEFAULT_SCOPES))
