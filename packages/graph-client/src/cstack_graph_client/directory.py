from typing import Any

from msgraph import GraphServiceClient  # type: ignore[attr-defined]

from cstack_graph_client._pagination import collect_paginated

USER_SELECT_FIELDS: tuple[str, ...] = (
    "id",
    "displayName",
    "userPrincipalName",
    "accountEnabled",
    "userType",
    "signInActivity",
)


async def fetch_all_users(client: GraphServiceClient) -> list[dict[str, Any]]:
    """Fetch every user with the fields the audit logic in Sprint 2 needs."""
    return await collect_paginated(
        get_first_page=lambda: client.users.get(request_configuration=_user_request_config(client)),
        get_next_page=lambda url: client.users.with_url(url).get(),
    )


async def fetch_all_groups(client: GraphServiceClient) -> list[dict[str, Any]]:
    """Fetch every group as a raw dict."""
    return await collect_paginated(
        get_first_page=lambda: client.groups.get(),
        get_next_page=lambda url: client.groups.with_url(url).get(),
    )


async def fetch_all_directory_roles(client: GraphServiceClient) -> list[dict[str, Any]]:
    """Fetch every activated directory role as a raw dict."""
    return await collect_paginated(
        get_first_page=lambda: client.directory_roles.get(),
        get_next_page=lambda url: client.directory_roles.with_url(url).get(),
    )


def _user_request_config(client: GraphServiceClient) -> Any:
    """Build a request configuration that selects the audit-relevant user fields.

    Centralised so the field list stays consistent if Sprint 2 adds more
    columns. The exact configuration class lives inside the kiota-generated
    request builder; we look it up dynamically to avoid pinning to a specific
    SDK build.
    """
    builder = client.users
    config_factory = getattr(builder, "UsersRequestBuilderGetRequestConfiguration", None)
    if config_factory is None:
        # Older or newer SDK shapes may not expose the nested class; in that
        # case fall back to no-config (full payloads). Sprint 7 will harden
        # this path against the live SDK.
        return None
    query_factory = getattr(builder, "UsersRequestBuilderGetQueryParameters", None)
    if query_factory is not None:
        params = query_factory(select=list(USER_SELECT_FIELDS))
        return config_factory(query_parameters=params)
    return config_factory()
