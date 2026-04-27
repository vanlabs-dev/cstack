from cstack_audit_core import Severity


def test_ordering_low_to_high() -> None:
    assert Severity.INFO < Severity.LOW < Severity.MEDIUM < Severity.HIGH < Severity.CRITICAL


def test_descending_sort() -> None:
    items = [Severity.LOW, Severity.CRITICAL, Severity.INFO, Severity.HIGH, Severity.MEDIUM]
    sorted_desc = sorted(items, reverse=True)
    assert sorted_desc == [
        Severity.CRITICAL,
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.LOW,
        Severity.INFO,
    ]


def test_string_value_round_trips() -> None:
    assert Severity("CRITICAL") is Severity.CRITICAL
    assert Severity.HIGH.value == "HIGH"
