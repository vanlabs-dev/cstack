"""JSON logging setup with correlation-id and header redaction.

The redaction filter strips known sensitive headers (``Authorization``,
``X-API-Key``, ``X-Api-Key``) from any log record that names them, so a
caller that accidentally logs ``request.headers`` cannot leak credentials
into the structured log output.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from signalguard_api.correlation import get_correlation_id

_REDACTED = "[redacted]"
_SENSITIVE_HEADERS: frozenset[str] = frozenset({"authorization", "x-api-key", "x-apikey"})


class CorrelationIdFilter(logging.Filter):
    """Attach the current request's correlation id to every record.

    Falls back to ``-`` for log lines emitted outside a request scope (e.g.
    application startup) so the field is always present.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class HeaderRedactionFilter(logging.Filter):
    """Best-effort scrub of header-shaped values in a record's extra fields.

    Walks a depth-1 mapping (lists of mappings included) and replaces values
    keyed by sensitive header names. Deeper nesting is intentionally not
    rewritten; routers should not be logging arbitrary blobs in the first
    place.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        for attr_name, value in list(record.__dict__.items()):
            if isinstance(value, Mapping):
                record.__dict__[attr_name] = _redact_mapping(value)
            elif isinstance(value, str):
                lower = attr_name.lower()
                if lower in _SENSITIVE_HEADERS:
                    record.__dict__[attr_name] = _REDACTED
        msg = record.getMessage()
        for header in _SENSITIVE_HEADERS:
            needle = f"{header}="
            if needle in msg.lower():
                record.msg = _scrub_inline_kv(msg, needle)
                record.args = None
        return True


def _redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in value.items():
        if isinstance(k, str) and k.lower() in _SENSITIVE_HEADERS:
            out[k] = _REDACTED
        else:
            out[k] = v
    return out


def _scrub_inline_kv(msg: str, needle_lower: str) -> str:
    """Replace ``header=<value>`` in a free-form log message with a redaction.

    Case-insensitive on the header name, value runs to the next whitespace or
    end of string. Keeps the rest of the message intact so log readers can
    still correlate the surrounding context.
    """
    lowered = msg.lower()
    out: list[str] = []
    i = 0
    while i < len(msg):
        idx = lowered.find(needle_lower, i)
        if idx == -1:
            out.append(msg[i:])
            break
        out.append(msg[i:idx])
        end = idx + len(needle_lower)
        while end < len(msg) and not msg[end].isspace():
            end += 1
        out.append(msg[idx : idx + len(needle_lower)] + _REDACTED)
        i = end
    return "".join(out)


def configure_logging(level: str) -> None:
    """Install the JSON handler, correlation filter, and redaction filter."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s %(correlation_id)s")
    )
    handler.addFilter(CorrelationIdFilter())
    handler.addFilter(HeaderRedactionFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
