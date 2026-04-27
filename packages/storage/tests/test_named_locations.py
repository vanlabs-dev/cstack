import duckdb
from cstack_schemas import NamedLocationAdapter
from cstack_storage import get_named_locations, upsert_named_locations

TENANT = "00000000-0000-0000-0000-0000000000bb"


def _ip_loc() -> object:
    return NamedLocationAdapter.validate_python(
        {
            "@odata.type": "#microsoft.graph.ipNamedLocation",
            "id": "loc-ip",
            "displayName": "office",
            "isTrusted": True,
            "ipRanges": [
                {"@odata.type": "#microsoft.graph.iPv4CidrRange", "cidrAddress": "10.0.0.0/8"}
            ],
        }
    )


def _country_loc() -> object:
    return NamedLocationAdapter.validate_python(
        {
            "@odata.type": "#microsoft.graph.countryNamedLocation",
            "id": "loc-country",
            "displayName": "approved",
            "countriesAndRegions": ["NZ", "AU"],
        }
    )


def test_upsert_mixed_variants(db: duckdb.DuckDBPyConnection) -> None:
    written = upsert_named_locations(db, TENANT, [_ip_loc(), _country_loc()])  # type: ignore[list-item]
    assert written == 2
    fetched = get_named_locations(db, TENANT)
    ids = {loc.id for loc in fetched}
    assert ids == {"loc-ip", "loc-country"}


def test_upsert_is_idempotent(db: duckdb.DuckDBPyConnection) -> None:
    upsert_named_locations(db, TENANT, [_ip_loc()])  # type: ignore[list-item]
    upsert_named_locations(db, TENANT, [_ip_loc()])  # type: ignore[list-item]
    assert len(get_named_locations(db, TENANT)) == 1
