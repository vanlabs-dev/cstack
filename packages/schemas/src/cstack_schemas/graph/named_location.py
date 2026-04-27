from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter

from cstack_schemas.graph._base import GraphModel


class IpRange(GraphModel):
    """A single CIDR-format IP range entry inside an IP named location."""

    odata_type: str = Field(alias="@odata.type")
    cidr_address: str | None = None


class IpNamedLocation(GraphModel):
    odata_type: Literal["#microsoft.graph.ipNamedLocation"] = Field(alias="@odata.type")
    id: str
    display_name: str
    is_trusted: bool | None = None
    ip_ranges: list[IpRange] = Field(default_factory=list)
    created_date_time: datetime | None = None
    modified_date_time: datetime | None = None


class CountryNamedLocation(GraphModel):
    odata_type: Literal["#microsoft.graph.countryNamedLocation"] = Field(alias="@odata.type")
    id: str
    display_name: str
    countries_and_regions: list[str] = Field(default_factory=list)
    include_unknown_countries_and_regions: bool | None = None
    country_lookup_method: str | None = None
    created_date_time: datetime | None = None
    modified_date_time: datetime | None = None


# Discriminated union on the Graph @odata.type marker. Use NamedLocationAdapter
# for parsing arbitrary payloads where the variant is decided per item.
NamedLocation = Annotated[
    IpNamedLocation | CountryNamedLocation,
    Field(discriminator="odata_type"),
]

NamedLocationAdapter: TypeAdapter[IpNamedLocation | CountryNamedLocation] = TypeAdapter(
    NamedLocation
)
