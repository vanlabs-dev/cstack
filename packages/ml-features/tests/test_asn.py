"""ASN lookup tests.

Sprint 6.7 wired in the MaxMind GeoLite2 path with a fixture-aware
fallback. These tests exercise both branches and the cached reader.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import geoip2.errors
import pytest
from cstack_ml_features.asn import AsnLookup, _reader, lookup_asn


@pytest.fixture(autouse=True)
def _clear_reader_cache() -> Iterator[None]:
    """``_reader`` is lru_cache'd; reset between tests so env-var
    changes are picked up."""
    _reader.cache_clear()
    yield
    _reader.cache_clear()


def test_lookup_returns_none_for_empty_input() -> None:
    assert lookup_asn(None) == AsnLookup(None, None)
    assert lookup_asn("") == AsnLookup(None, None)


def test_lookup_uses_fixture_fallback_when_db_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No DB at the configured path: TEST-NET prefix still resolves via
    the synthesizer-aware fallback."""
    monkeypatch.setenv("CSTACK_GEOIP_ASN_DB", str(tmp_path / "missing.mmdb"))
    result = lookup_asn("203.0.113.10")
    assert result.number == 4648  # Spark NZ in the fixture table
    assert result.organization is None


def test_lookup_uses_real_db_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the geoip2 reader so the test verifies the lookup path
    without needing a real GeoLite2-ASN.mmdb file."""
    fake_response = MagicMock()
    fake_response.autonomous_system_number = 13335
    fake_response.autonomous_system_organization = "Cloudflare, Inc."
    fake_reader = MagicMock()
    fake_reader.asn.return_value = fake_response

    with patch("cstack_ml_features.asn._reader", return_value=fake_reader):
        result = lookup_asn("1.1.1.1")
    assert result.number == 13335
    assert result.organization == "Cloudflare, Inc."
    fake_reader.asn.assert_called_once_with("1.1.1.1")


def test_lookup_falls_through_when_real_db_misses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real DB lookup that raises AddressNotFoundError falls through
    to the fixture fallback so synthesizer ranges still resolve."""
    fake_reader = MagicMock()
    fake_reader.asn.side_effect = geoip2.errors.AddressNotFoundError("not found")

    with patch("cstack_ml_features.asn._reader", return_value=fake_reader):
        result = lookup_asn("203.0.113.10")
    assert result.number == 4648  # fell through to fixture table
    assert result.organization is None


def test_lookup_handles_malformed_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed IP that geoip2 rejects with ValueError still gets
    resolved via the fallback path."""
    fake_reader = MagicMock()
    fake_reader.asn.side_effect = ValueError("not a valid address")

    with patch("cstack_ml_features.asn._reader", return_value=fake_reader):
        # Less-than-two-part IP: fallback returns None.
        assert lookup_asn("garbage").number is None


def test_fixture_fallback_is_deterministic() -> None:
    """The same novel IP always resolves to the same synthetic AS
    number, so user history comparisons stay coherent."""
    a = lookup_asn("198.51.100.42")
    b = lookup_asn("198.51.100.42")
    assert a.number == b.number
