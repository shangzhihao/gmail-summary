"""Digest builder for summarized emails."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from gmail_digest_tool.models.email_models import EmailSummary


def build_digest(
    summaries: Iterable[EmailSummary],
    *,
    run_time: datetime | None = None,
) -> str:
    """Construct a human-readable digest from email summaries."""
    run_timestamp = (run_time or datetime.now(UTC)).astimezone(UTC)
    sorted_summaries = sorted(
        summaries,
        key=lambda item: item.internal_date,
        reverse=True,
    )

    header = (
        f"Gmail Digest — {run_timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
        f"Total conversations: {len(sorted_summaries)}\n"
    )
    if not sorted_summaries:
        return f"{header}\nNo matching emails found in the selected interval.\n"

    sections: list[str] = [header]
    for index, summary in enumerate(sorted_summaries, start=1):
        entry_lines = [
            f"{index}. Message ID: {summary.message_id}",
            f"   From: {summary.sender}",
            "   Received: "
            + summary.internal_date.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S %Z"),
            "   Summary:",
            f"     {summary.summary}",
        ]
        sections.append("\n".join(entry_lines))

    return "\n\n".join(sections) + "\n"
