import asyncio
from typing import Any

from cstack_graph_client._pagination import collect_paginated


class _FakePage:
    """Stand-in for a kiota collection response, exposing the same attribute names."""

    def __init__(self, value: list[Any] | None, odata_next_link: str | None = None) -> None:
        self.value = value
        self.odata_next_link = odata_next_link


def test_collect_paginated_walks_multiple_pages() -> None:
    page_1 = _FakePage([{"id": "1"}, {"id": "2"}], odata_next_link="https://graph/page2")
    page_2 = _FakePage([{"id": "3"}], odata_next_link=None)

    visited: list[str] = []

    async def first() -> _FakePage:
        return page_1

    async def follow(url: str) -> _FakePage:
        visited.append(url)
        return page_2

    items = asyncio.run(collect_paginated(first, follow))
    assert items == [{"id": "1"}, {"id": "2"}, {"id": "3"}]
    assert visited == ["https://graph/page2"]


def test_collect_paginated_handles_single_page() -> None:
    page = _FakePage([{"id": "only"}])

    async def first() -> _FakePage:
        return page

    async def follow(_url: str) -> _FakePage:
        raise AssertionError("follow must not be called when there is no next link")

    items = asyncio.run(collect_paginated(first, follow))
    assert items == [{"id": "only"}]


def test_collect_paginated_handles_empty_response() -> None:
    page = _FakePage(value=None)

    async def first() -> _FakePage:
        return page

    async def follow(_url: str) -> _FakePage:
        raise AssertionError("unreachable")

    assert asyncio.run(collect_paginated(first, follow)) == []
