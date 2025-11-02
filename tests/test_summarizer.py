from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime

import pytest

from gmail_digest_tool.models.email_models import EmailMessage
from gmail_digest_tool.services.summarizer import Summarizer, SummarizerConfig


class StubOpenAIClient:
    def __init__(self) -> None:
        self.requests: list[list[dict[str, str]]] = []
        self.async_requests: list[list[dict[str, str]]] = []

    def summarize(
        self,
        messages: Iterable[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        self.requests.append(list(messages))
        return f"summary tokens={max_tokens} temp={temperature}"

    async def summarize_async(
        self,
        messages: Iterable[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        await asyncio.sleep(0)
        batch = list(messages)
        self.async_requests.append(batch)
        return self.summarize(batch, max_tokens=max_tokens, temperature=temperature)


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


@pytest.mark.asyncio
async def test_summarizer_summarize_many_async_returns_all_summaries() -> None:
    client = StubOpenAIClient()
    summarizer = Summarizer(
        client,
        SummarizerConfig(temperature=0.1, max_tokens=50, concurrency_limit=2),
    )
    emails = [
        EmailMessage(
            id=f"msg-{index}",
            thread_id="thread",
            subject=f"Subject {index}",
            sender="sender@example.com",
            recipients=["user@example.com"],
            snippet="Snippet",
            body_text="Body text",
            internal_date=datetime(2024, 1, 1, tzinfo=UTC),
            labels=[],
            gmail_metadata={},
        )
        for index in range(3)
    ]

    summaries = await summarizer.summarize_many_async(emails)

    assert len(summaries) == len(emails)
    assert len(client.async_requests) == len(emails)
