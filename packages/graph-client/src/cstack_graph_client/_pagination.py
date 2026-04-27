from collections.abc import Awaitable, Callable
from typing import Any

from cstack_graph_client._serialisation import parsable_to_dict


async def collect_paginated(
    get_first_page: Callable[[], Awaitable[Any]],
    get_next_page: Callable[[str], Awaitable[Any]],
) -> list[dict[str, Any]]:
    """Walk a Microsoft Graph paginated response chain.

    Calls ``get_first_page`` once, then ``get_next_page(url)`` while the
    response carries an ``odata_next_link``. SDK Parsable instances are
    serialised to plain dicts; mocked tests can return plain dicts directly.
    """
    items: list[dict[str, Any]] = []
    response = await get_first_page()
    while response is not None:
        for entry in getattr(response, "value", None) or []:
            items.append(parsable_to_dict(entry))
        next_link = getattr(response, "odata_next_link", None)
        if not next_link:
            break
        response = await get_next_page(next_link)
    return items
