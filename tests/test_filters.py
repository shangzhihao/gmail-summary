from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from gmail_digest_tool.services.filters import (
    EXCLUDE_QUERY,
    FilterCriteria,
    build_filter_criteria,
    resolve_time_range,
)


def test_resolve_time_range_defaults_to_last_24_hours() -> None:
    now = datetime(2024, 1, 2, 12, tzinfo=UTC)
    start, end = resolve_time_range(None, None, now=now)
    assert end == now
    assert start == now - timedelta(hours=24)


def test_resolve_time_range_validates_order() -> None:
    from_dt = datetime(2024, 1, 2, tzinfo=UTC)
    to_dt = datetime(2024, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError):
        resolve_time_range(from_dt, to_dt)


def test_build_filter_criteria_query_with_unread() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 2, tzinfo=UTC)
    criteria = build_filter_criteria(True, start, end)
    assert isinstance(criteria, FilterCriteria)
    query = criteria.to_query()
    assert "is:unread" in query
    assert EXCLUDE_QUERY in query
    assert f"after:{int(start.timestamp())}" in query
    assert f"before:{int(end.timestamp())}" in query
