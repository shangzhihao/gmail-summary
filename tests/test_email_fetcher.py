from __future__ import annotations

from datetime import UTC, datetime, timedelta

from gmail_digest_tool.models.email_models import EmailMessage
from gmail_digest_tool.services.email_fetcher import EmailFetcher


class StubGmailClient:
    def __init__(self, messages: list[EmailMessage]) -> None:
        self.messages = messages
        self.calls: list[dict[str, object]] = []

    def fetch_messages(
        self,
        query: str,
        label_ids: list[str] | None = None,
        max_results: int | None = None,
        exclude_ids: set[str] | None = None,
    ) -> list[EmailMessage]:
        self.calls.append(
            {
                "query": query,
                "label_ids": label_ids,
                "max_results": max_results,
                "exclude_ids": set(exclude_ids or set()),
            }
        )
        excluded = exclude_ids or set()
        return [message for message in self.messages if message.id not in excluded]


def make_message(timestamp: datetime, message_id: str = "msg") -> EmailMessage:
    return EmailMessage(
        id=message_id,
        thread_id="thread",
        subject="Subject",
        sender="sender@example.com",
        recipients=["user@example.com"],
        snippet="Snippet",
        body_text="Body",
        internal_date=timestamp,
        labels=[],
        gmail_metadata={},
    )


def test_email_fetcher_filters_by_time_range() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=24)
    messages = [
        make_message(start + timedelta(hours=1)),
        make_message(start - timedelta(hours=1)),
    ]
    client = StubGmailClient(messages)
    fetcher = EmailFetcher(client)  # type: ignore[arg-type]

    filtered, criteria = fetcher.fetch(
        unread_only=True,
        from_datetime=start,
        to_datetime=end,
    )

    assert len(filtered) == 1
    assert filtered[0].internal_date == start + timedelta(hours=1)
    assert criteria.start == start
    assert criteria.end == end
    assert client.calls, "Expected Gmail client to be invoked."


def test_email_fetcher_excludes_known_ids() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    messages = [
        make_message(start, message_id="keep"),
        make_message(start, message_id="skip"),
    ]
    client = StubGmailClient(messages)
    fetcher = EmailFetcher(client)  # type: ignore[arg-type]

    filtered, _ = fetcher.fetch(
        unread_only=False,
        from_datetime=start,
        to_datetime=start,
        exclude_ids={"skip"},
    )

    assert {message.id for message in filtered} == {"keep"}
    assert client.calls[0]["exclude_ids"] == {"skip"}
