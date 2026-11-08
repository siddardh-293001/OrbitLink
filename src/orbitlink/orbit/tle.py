"""Two-line element parsing and data-quality checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


def _checksum(line: str) -> int:
    return (sum(int(ch) for ch in line[:68] if ch.isdigit()) + line[:68].count("-")) % 10


def _validate_line(line: str, number: str) -> None:
    if len(line) != 69:
        raise ValueError(f"TLE line {number} must be exactly 69 characters")
    if line[0] != number or not line[1].isspace():
        raise ValueError(f"expected TLE line {number}")
    if not line[68].isdigit() or int(line[68]) != _checksum(line):
        raise ValueError(f"TLE line {number} checksum is invalid")


@dataclass(frozen=True)
class TLERecord:
    name: str
    line1: str
    line2: str
    satellite_id: str
    epoch: datetime

    @classmethod
    def parse(cls, text: str) -> "TLERecord":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) == 3 and not lines[0].startswith(("1 ", "2 ")):
            name, line1, line2 = lines
        elif len(lines) == 2:
            line1, line2 = lines
            name = f"NORAD {line1[2:7].strip()}"
        else:
            raise ValueError("TLE input must contain two element lines and an optional name")
        _validate_line(line1, "1")
        _validate_line(line2, "2")
        catalog1, catalog2 = line1[2:7].strip(), line2[2:7].strip()
        if not catalog1 or catalog1 != catalog2:
            raise ValueError("satellite catalog numbers do not match")
        try:
            year2 = int(line1[18:20])
            year = 1900 + year2 if year2 >= 57 else 2000 + year2
            day_of_year = float(line1[20:32])
            if not 1 <= day_of_year < 367:
                raise ValueError
            epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)
        except (ValueError, OverflowError) as exc:
            raise ValueError("TLE epoch field is invalid") from exc
        return cls(name, line1, line2, catalog1, epoch)

    def age_days(self, at_time: datetime) -> float:
        at_time = _as_utc(at_time)
        return (at_time - self.epoch).total_seconds() / 86400.0

    def quality(self, at_time: datetime, *, max_age_days: float = 14.0) -> tuple[str, ...]:
        age = self.age_days(at_time)
        issues = []
        if age < 0:
            issues.append("TLE epoch is in the future relative to simulation time")
        if age > max_age_days:
            issues.append(f"TLE is stale ({age:.1f} days old; limit {max_age_days:g})")
        return tuple(issues)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
