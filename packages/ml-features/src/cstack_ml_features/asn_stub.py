"""V1 stub for ASN lookup. Matches the synthesizer's IP-prefix layout so the
fixture pipeline produces stable ASNs without an external GeoIP database.

TODO(sprint-7): swap to a real maxmind/ipinfo lookup once we run against a
live tenant. Keep the function signature; only the body needs to change.
"""

from __future__ import annotations

import hashlib

# Prefixes match the IP allocation in cstack_fixtures.synth.signins so that
# fixture sign-ins resolve to the named NZ ISPs and well-known cloud ASNs.
_PREFIX_TO_ASN: dict[str, str] = {
    "203.0": "AS4648",  # Spark NZ
    "122.56": "AS9500",  # Vodafone NZ
    "110.175": "AS45177",  # 2degrees NZ Mobile
    "52.96": "AS8075",  # Microsoft Azure
    "54.240": "AS16509",  # AWS
    "35.240": "AS15169",  # Google Cloud
}


def lookup_asn(ip_address: str | None) -> str | None:
    """Resolve an IPv4 address to a synthetic ASN using a static prefix table.

    Returns None when no IP is provided. Falls back to a stable hash-derived
    AS number so each unique IP maps to one ASN consistently across calls.
    """

    if not ip_address:
        return None
    parts = ip_address.split(".")
    if len(parts) < 2:
        return None
    prefix = f"{parts[0]}.{parts[1]}"
    if prefix in _PREFIX_TO_ASN:
        return _PREFIX_TO_ASN[prefix]
    # Stable fallback so the model learns "this user normally appears under
    # one of these synthetic ASNs", instead of every novel IP being flagged.
    digest = hashlib.sha256(ip_address.encode("utf-8")).hexdigest()[:6]
    return f"AS{int(digest, 16) % 65535:05d}"
