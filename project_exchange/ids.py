from __future__ import annotations

from datetime import UTC, datetime


def year() -> str:
    return str(datetime.now(UTC).year)


def next_sequence_id(prefix: str, count: int, width: int = 6, include_year: bool = True) -> str:
    if include_year:
        return f"{prefix}-{year()}-{count + 1:0{width}d}"
    return f"{prefix}-{count + 1:0{width}d}"
