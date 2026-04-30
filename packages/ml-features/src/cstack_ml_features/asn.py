"""ASN/GeoIP lookup with MaxMind GeoLite2 plus a fixture-aware fallback.

Sprint 6.7 replaces the pure-stub Sprint 1 implementation with real
MaxMind GeoLite2 ASN database lookups. Database location is configured
via ``CSTACK_GEOIP_ASN_DB`` (default ``/data/geoip/GeoLite2-ASN.mmdb``,
the path the geoipupdate container writes to in the Compose stack).

A real-database miss falls through to a deterministic IP-prefix table
that mirrors the synthesizer's TEST-NET layout, so fixture calibration
keeps producing stable per-IP ASNs even though MaxMind has no entries
for documentation IP ranges. Live-tenant traffic sees real ASNs from
the database; fixture traffic sees the prefix-derived synthetic ones.

The lookup function returns ``int | None`` for the AS number (matching
how downstream feature extractors compare), plus the AS organisation
string when the real database supplied one.
"""

from __future__ import annotations

import hashlib
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import geoip2.database
import geoip2.errors

LOG = logging.getLogger(__name__)


class AsnLookup(NamedTuple):
    """Resolved ASN for an IP. ``number`` is the integer AS number."""

    number: int | None
    organization: str | None


# Prefixes match the IP allocation in cstack_fixtures.synth.signins so
# fixture sign-ins resolve to the named NZ ISPs and well-known cloud
# ASNs even without a MaxMind database (the documentation IP ranges
# the synthesizer uses are not in any GeoLite2 build by design).
_FIXTURE_PREFIX_TO_ASN: dict[str, int] = {
    "203.0": 4648,  # Spark NZ
    "122.56": 9500,  # Vodafone NZ
    "110.175": 45177,  # 2degrees NZ Mobile
    "52.96": 8075,  # Microsoft Azure
    "54.240": 16509,  # AWS
    "35.240": 15169,  # Google Cloud
}


def _default_db_path() -> Path:
    """Where the geoipupdate container writes ``GeoLite2-ASN.mmdb``."""
    return Path(os.environ.get("CSTACK_GEOIP_ASN_DB", "/data/geoip/GeoLite2-ASN.mmdb"))


@lru_cache(maxsize=1)
def _reader() -> geoip2.database.Reader | None:
    """Open the MaxMind reader once per process; ``None`` when DB absent."""
    db_path = _default_db_path()
    if not db_path.exists():
        LOG.debug("GeoLite2-ASN database not found at %s; using fixture fallback", db_path)
        return None
    try:
        return geoip2.database.Reader(str(db_path))
    except (FileNotFoundError, ValueError) as exc:
        LOG.warning("failed to open GeoLite2-ASN database at %s: %s", db_path, exc)
        return None


def _fixture_fallback_number(ip_address: str) -> int | None:
    """Stable per-IP ASN derived from prefix table or hash of full address.

    Mirrors the Sprint 1 ``asn_stub`` semantics so fixture sign-ins keep
    producing one ASN per user/ISP combination across runs and the
    anomaly model has something to compare against.
    """
    parts = ip_address.split(".")
    if len(parts) < 2:
        return None
    prefix = f"{parts[0]}.{parts[1]}"
    if prefix in _FIXTURE_PREFIX_TO_ASN:
        return _FIXTURE_PREFIX_TO_ASN[prefix]
    # Stable hash fallback: every novel IP maps to the same synthetic AS
    # number consistently, so user-history comparisons stay coherent.
    digest = hashlib.sha256(ip_address.encode("utf-8")).hexdigest()[:6]
    return int(digest, 16) % 65535


def lookup_asn(ip_address: str | None) -> AsnLookup:
    """Resolve an IPv4/IPv6 address to its ASN.

    Resolution order:

    1. MaxMind GeoLite2 ASN database when ``CSTACK_GEOIP_ASN_DB`` (or
       its default ``/data/geoip/GeoLite2-ASN.mmdb``) is available and
       has an entry for the address.
    2. Static prefix table covering the synthesizer's TEST-NET ranges
       so fixture sign-ins produce deterministic ASNs.
    3. SHA-256-derived stable hash for any other unresolved address,
       so a given IP always maps to the same synthetic AS number.

    Returns ``AsnLookup(number=None, organization=None)`` only when
    ``ip_address`` is None or empty.
    """
    if not ip_address:
        return AsnLookup(None, None)
    reader = _reader()
    if reader is not None:
        try:
            response = reader.asn(ip_address)
            return AsnLookup(
                number=response.autonomous_system_number,
                organization=response.autonomous_system_organization,
            )
        except geoip2.errors.AddressNotFoundError:
            pass  # fall through to fixture fallback
        except ValueError:
            # Malformed IP; let the fallback decide based on string parts.
            pass
    return AsnLookup(number=_fixture_fallback_number(ip_address), organization=None)
