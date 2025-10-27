from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from gmail_digest_tool.models.email_models import EmailMessage
from gmail_digest_tool.services.summarizer import Summarizer, SummarizerConfig


class StubOpenAIClient:
    def __init__(self) -> None:
        self.requests: list[list[dict[str, str]]] = []

    def summarize(
        self,
        messages: Iterable[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        self.requests.append(list(messages))
        return f"summary tokens={max_tokens} temp={temperature}"


def test_summarizer_returns_email_summary() -> None:
    client = StubOpenAIClient()
    summarizer = Summarizer(client, SummarizerConfig(temperature=0.1, max_tokens=50))
    email = EmailMessage(
        id="abc",
        thread_id="thread",
        subject="Hello",
        sender="sender@example.com",
        recipients=["user@example.com"],
        snippet="Snippet",
        body_text="Body text",
        internal_date=datetime(2024, 1, 1, tzinfo=UTC),
        labels=[],
        gmail_metadata={},
    )

    summary = summarizer.summarize_email(email)
    assert summary.summary.startswith("summary")
    assert summary.message_id == "abc"
    assert len(client.requests) == 1
