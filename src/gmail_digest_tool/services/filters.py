"""Filtering utilities for Gmail messages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

DEFAULT_LABELS: tuple[str, ...] = ()
EXCLUDE_QUERY = "-in:spam -in:trash"


@dataclass(frozen=True)
class FilterCriteria:
    """Resolved filter parameters for Gmail queries."""

    unread_only: bool
    start: datetime
    end: datetime

    def to_query(self) -> str:
        """Return the Gmail search query string."""
        base_query = EXCLUDE_QUERY
        if self.unread_only:
            base_query = f"is:unread {base_query}"

        after_ts = int(self.start.timestamp())
        before_ts = int(self.end.timestamp())
        time_clause = f"after:{after_ts} before:{before_ts}"

        return f"{base_query} {time_clause}".strip()


def resolve_time_range(
    from_datetime: datetime | None,
    to_datetime: datetime | None,
    *,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Resolve the effective time range for message queries.

    If both ``from_datetime`` and ``to_datetime`` are provided, they are validated
    and returned in UTC order. Otherwise the function returns the trailing 24-hour
    window ending at ``now`` (defaulting to current UTC time).
    """
    current = (now or datetime.now(UTC)).astimezone(UTC)

    if from_datetime and to_datetime:
        start = from_datetime.astimezone(UTC)
        end = to_datetime.astimezone(UTC)
        if start > end:
            msg = "from_datetime must be earlier than or equal to to_datetime."
            raise ValueError(msg)
        return start, end

    end = current
    start = end - timedelta(hours=24)
    return start, end


def build_filter_criteria(
    unread_only: bool,
    from_datetime: datetime | None,
    to_datetime: datetime | None,
    *,
    now: datetime | None = None,
) -> FilterCriteria:
    """Construct filter criteria object from raw parameters."""
    start, end = resolve_time_range(from_datetime, to_datetime, now=now)
    return FilterCriteria(unread_only=unread_only, start=start, end=end)
