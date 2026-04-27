class GraphAuthError(Exception):
    """Raised when authentication or token acquisition fails."""


class CertificateNotFoundError(GraphAuthError):
    """Raised when the auth certificate cannot be located in the store or PFX."""


class GraphRequestError(Exception):
    """Raised when a Graph API request fails or returns malformed data."""
