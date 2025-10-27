"""Summarization service for email content."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, cast

from loguru import logger

from gmail_digest_tool.models.email_models import EmailMessage, EmailSummary

DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 180


@dataclass(frozen=True)
class SummarizerConfig:
    """Configuration parameters for the summarizer."""

    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS


class SummarizationClient(Protocol):
    """Protocol for clients capable of summarizing emails."""

    def summarize(
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

    def summarize_email(self, email: EmailMessage) -> EmailSummary:
        """Generate a concise summary for an email message."""
        logger.debug(f"Summarizing email {email.id}")
        prompt = self._build_prompt(email)
        summary_text = self._client.summarize(
            prompt,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )
        return EmailSummary(
            message_id=email.id,
            summary=summary_text,
            subject=email.subject,
            sender=email.sender,
            recipients=email.recipients,
            internal_date=email.internal_date,
            web_link=cast(str, email.web_link),
        )

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
