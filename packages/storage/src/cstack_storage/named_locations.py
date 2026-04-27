import json
from datetime import UTC, datetime

import duckdb
from cstack_schemas import (
    CountryNamedLocation,
    IpNamedLocation,
    NamedLocationAdapter,
)

LocationVariant = IpNamedLocation | CountryNamedLocation


def upsert_named_locations(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    locations: list[LocationVariant],
) -> int:
    """Insert or replace named-location rows. Returns rows written."""
    if not locations:
        return 0
    now = datetime.now(UTC)
    rows: list[tuple[object, ...]] = []
    for location in locations:
        if isinstance(location, IpNamedLocation):
            rows.append(
                (
                    tenant_id,
                    location.id,
                    location.display_name,
                    "ip",
                    json.dumps(
                        [r.model_dump(by_alias=True, exclude_none=True) for r in location.ip_ranges]
                    ),
                    None,
                    location.is_trusted,
                    now,
                )
            )
        else:
            rows.append(
                (
                    tenant_id,
                    location.id,
                    location.display_name,
                    "country",
                    None,
                    json.dumps(location.countries_and_regions),
                    None,
                    now,
                )
            )
    conn.executemany(
        """
        INSERT OR REPLACE INTO named_locations
            (tenant_id, id, display_name, location_type, ip_ranges, countries,
             is_trusted, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def get_named_locations(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> list[LocationVariant]:
    """Read parsed named locations for a tenant."""
    rows = conn.execute(
        """
        SELECT id, display_name, location_type, ip_ranges, countries, is_trusted
        FROM named_locations WHERE tenant_id = ?
        ORDER BY display_name
        """,
        [tenant_id],
    ).fetchall()
    parsed: list[LocationVariant] = []
    for row in rows:
        location_type = row[2]
        if location_type == "ip":
            payload: dict[str, object] = {
                "@odata.type": "#microsoft.graph.ipNamedLocation",
                "id": row[0],
                "displayName": row[1],
                "isTrusted": row[5],
                "ipRanges": json.loads(row[3]) if row[3] is not None else [],
            }
        elif location_type == "country":
            payload = {
                "@odata.type": "#microsoft.graph.countryNamedLocation",
                "id": row[0],
                "displayName": row[1],
                "countriesAndRegions": json.loads(row[4]) if row[4] is not None else [],
            }
        else:
            raise ValueError(f"unknown location_type {location_type!r}")
        parsed.append(NamedLocationAdapter.validate_python(payload))
    return parsed
