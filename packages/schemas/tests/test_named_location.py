from cstack_schemas import (
    CountryNamedLocation,
    IpNamedLocation,
    NamedLocationAdapter,
)


def test_ip_named_location_parses() -> None:
    payload: dict[str, object] = {
        "@odata.type": "#microsoft.graph.ipNamedLocation",
        "id": "loc-1",
        "displayName": "office network",
        "isTrusted": True,
        "ipRanges": [
            {
                "@odata.type": "#microsoft.graph.iPv4CidrRange",
                "cidrAddress": "203.0.113.0/24",
            }
        ],
    }
    parsed = NamedLocationAdapter.validate_python(payload)
    assert isinstance(parsed, IpNamedLocation)
    assert parsed.is_trusted is True
    assert parsed.ip_ranges[0].cidr_address == "203.0.113.0/24"


def test_country_named_location_parses() -> None:
    payload: dict[str, object] = {
        "@odata.type": "#microsoft.graph.countryNamedLocation",
        "id": "loc-2",
        "displayName": "approved countries",
        "countriesAndRegions": ["NZ", "AU"],
        "includeUnknownCountriesAndRegions": False,
    }
    parsed = NamedLocationAdapter.validate_python(payload)
    assert isinstance(parsed, CountryNamedLocation)
    assert parsed.countries_and_regions == ["NZ", "AU"]
    assert parsed.include_unknown_countries_and_regions is False
