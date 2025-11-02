"""Summarization service for email content."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol, cast

from loguru import logger

from gmail_digest_tool.models.email_models import EmailMessage, EmailSummary

DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 180
DEFAULT_CONCURRENCY = 4


@dataclass(frozen=True)
class SummarizerConfig:
    """Configuration parameters for the summarizer."""

    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    concurrency_limit: int = DEFAULT_CONCURRENCY


class SummarizationClient(Protocol):
    """Protocol for clients capable of summarizing emails."""

    def summarize(
        self,
        messages: Iterable[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str: ...

    async def summarize_async(
        self,
        messages: Iterable[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str: ...


class Summarizer:
    """Summarize emails using an OpenAI-compatible client."""

    def __init__(
        self, client: SummarizationClient, config: SummarizerConfig | None = None
    ) -> None:
        """Initialize the summarizer."""
        self._client = client
        self._config = config or SummarizerConfig()

    @property
    def config(self) -> SummarizerConfig:
        """Return the summarizer configuration."""
        return self._config

    def summarize_email(self, email: EmailMessage) -> EmailSummary:
        """Generate a concise summary for an email message."""
        logger.debug(f"Summarizing email {email.id}")
        prompt = self._build_prompt(email)
        summary_text = self._client.summarize(
            prompt,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )
        logger.success(f"summary:{summary_text}")
        return self._build_email_summary(email, summary_text)

    async def summarize_email_async(self, email: EmailMessage) -> EmailSummary:
        """Generate a summary for an email message using async execution."""
        logger.debug(f"Summarizing email {email.id}")
        prompt = self._build_prompt(email)
        summary_text = await self._call_client_async(prompt)
        logger.success(f"summary:{summary_text}")
        return self._build_email_summary(email, summary_text)

    async def summarize_many_async(
        self, emails: Iterable[EmailMessage]
    ) -> list[EmailSummary]:
        """Summarize emails concurrently with bounded concurrency."""
        email_list = list(emails)
        if not email_list:
            return []

        concurrency = max(1, self._config.concurrency_limit)
        semaphore = asyncio.Semaphore(concurrency)

        for email in email_list:
            subject_preview = (
                email.subject if len(email.subject) <= 80 else f"{email.subject[:77]}..."
            )
            logger.info(
                f"Summarizing message {email.id} from {email.sender} "
                f"(subject={subject_preview})"
            )

        async def summarize_single(email: EmailMessage) -> EmailSummary:
            async with semaphore:
                return await self.summarize_email_async(email)

        tasks = [asyncio.create_task(summarize_single(email)) for email in email_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        summaries: list[EmailSummary] = []
        for email, result in zip(email_list, results):
            if isinstance(result, Exception):
                logger.exception(
                    f"Failed to summarize message {email.id}: {result}",
                )
                continue
            summaries.append(result)

        return summaries

    def _build_prompt(self, email: EmailMessage) -> list[dict[str, str]]:
        """Construct the chat prompt for the LLM."""
        system_instructions = (
            "你是一个负责汇总每日邮件摘要的多语言助手。"
            "用一句话总结邮件，要尽量做到简洁。"
            "无论邮件是什么语言，都要给出中文的总结。"
        )
        user_message = (
            f"Subject: {email.subject}\n"
            f"From: {email.sender}\n"
            f"To: {', '.join(email.recipients) if email.recipients else 'Unknown'}\n"
            f"Body:\n{email.body_text.strip() or email.snippet}"
        )
        return [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_message},
        ]

    async def _call_client_async(
        self, prompt: list[dict[str, str]]
    ) -> str:
        """Invoke the underlying client asynchronously."""
        summarize_async = getattr(self._client, "summarize_async", None)
        if summarize_async is not None:
            async_callable = cast(
                Callable[..., Awaitable[str]],
                summarize_async,
            )
            return await async_callable(
                prompt,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
            )
        return await asyncio.to_thread(
            self._client.summarize,
            prompt,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )

    def _build_email_summary(self, email: EmailMessage, summary_text: str) -> EmailSummary:
        """Assemble an EmailSummary from the LLM response."""
        return EmailSummary(
            message_id=email.id,
            summary=summary_text,
            subject=email.subject,
            sender=email.sender,
            recipients=email.recipients,
            internal_date=email.internal_date,
            web_link=cast(str, email.web_link),
        )
