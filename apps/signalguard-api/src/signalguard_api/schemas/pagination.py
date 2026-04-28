"""Generic ``Paginated[T]`` envelope for list endpoints.

Pydantic v2 supports the PEP 695 generic-class syntax once the project
targets Python 3.12, so the ``Generic`` import is unnecessary.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Paginated[T](BaseModel):
    """List response with offset/limit metadata.

    ``has_more`` is computed by the router rather than relying on clients
    to compare ``offset + len(items)`` against ``total``.
    """

    items: list[T]
    total: int = Field(description="Total rows matching the query, ignoring limit/offset.")
    limit: int
    offset: int
    has_more: bool
