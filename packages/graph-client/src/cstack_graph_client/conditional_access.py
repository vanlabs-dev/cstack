from typing import Any

from msgraph import GraphServiceClient  # type: ignore[attr-defined]

from cstack_graph_client._pagination import collect_paginated


async def fetch_all_ca_policies(client: GraphServiceClient) -> list[dict[str, Any]]:
    """Fetch every conditional access policy as a raw dict."""
    return await collect_paginated(
        get_first_page=lambda: client.identity.conditional_access.policies.get(),
        get_next_page=lambda url: client.identity.conditional_access.policies.with_url(url).get(),
    )


async def fetch_all_named_locations(client: GraphServiceClient) -> list[dict[str, Any]]:
    """Fetch every named location as a raw dict."""
    return await collect_paginated(
        get_first_page=lambda: client.identity.conditional_access.named_locations.get(),
        get_next_page=lambda url: client.identity.conditional_access.named_locations.with_url(
            url
        ).get(),
    )
