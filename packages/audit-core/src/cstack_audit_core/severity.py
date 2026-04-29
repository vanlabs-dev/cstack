from enum import StrEnum

# Severity ranks, lowest to highest. Used to compare members and to filter
# findings by ``min_severity``. Keeping the ordering explicit avoids relying
# on member-definition order, which is brittle under refactors.
_RANK: dict[str, int] = {
    "INFO": 1,
    "LOW": 2,
    "MEDIUM": 3,
    "HIGH": 4,
    "CRITICAL": 5,
}


class Severity(StrEnum):
    """Finding severity ladder, ordered Info < Low < Medium < High < Critical.

    StrEnum so JSON serialisation uses the string value directly. Comparison
    operators delegate to a fixed rank table so members compare by intent, not
    by definition order.
    """

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    def _rank(self) -> int:
        return _RANK[self.value]

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Severity):
            return self._rank() < other._rank()
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Severity):
            return self._rank() <= other._rank()
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Severity):
            return self._rank() > other._rank()
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Severity):
            return self._rank() >= other._rank()
        return NotImplemented
