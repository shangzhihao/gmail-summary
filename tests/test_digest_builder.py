from __future__ import annotations

from datetime import UTC, datetime

from gmail_digest_tool.models.email_models import EmailSummary
from gmail_digest_tool.services.digest_builder import build_digest


def make_summary(index: int) -> EmailSummary:
    return EmailSummary(
        message_id=f"id-{index}",
        summary=f"Summary {index}",
        subject=f"Subject {index}",
        sender="Sender",
        recipients=["recipient@example.com"],
        internal_date=datetime(2024, 1, index + 1, tzinfo=UTC),
        web_link=f"https://mail.google.com/mail/u/0/#inbox/id-{index}",
    )


def test_build_digest_with_entries() -> None:
    summaries = [make_summary(1), make_summary(2)]
    digest = build_digest(summaries, run_time=datetime(2024, 1, 10, tzinfo=UTC))
    assert "Gmail Digest" in digest
    assert "Message ID: id-1" in digest
    assert "From: Sender" in digest
    assert "Received:" in digest
    assert "Summary 2" in digest
    assert "Subject" not in digest
    assert digest.index("Message ID: id-2") < digest.index("Message ID: id-1")
    assert digest.index("Summary 2") < digest.index("Summary 1")


def test_build_digest_empty() -> None:
    digest = build_digest([], run_time=datetime(2024, 1, 10, tzinfo=UTC))
    assert "No matching emails" in digest
