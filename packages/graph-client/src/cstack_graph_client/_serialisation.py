import json
from typing import Any, cast


def parsable_to_dict(item: Any) -> dict[str, Any]:
    """Convert a kiota-generated Graph SDK model into a plain dict.

    Tests can pass plain dicts and they pass through unchanged. Live SDK
    objects implement ``serialize`` and are written via the kiota JSON writer
    so callers can hand the result straight to the storage layer's pydantic
    models without depending on SDK types.
    """
    if isinstance(item, dict):
        return cast(dict[str, Any], item)

    # Imported lazily so test runs that supply plain dicts do not require the
    # full kiota serialisation stack to be importable.
    from kiota_serialization_json.json_serialization_writer import (
        JsonSerializationWriter,
    )

    writer = JsonSerializationWriter()
    item.serialize(writer)
    raw = writer.get_serialized_content().decode()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise TypeError(f"expected dict from kiota serialiser, got {type(parsed).__name__}")
    return cast(dict[str, Any], parsed)
