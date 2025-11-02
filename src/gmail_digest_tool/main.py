"""Application entrypoint coordinating the Gmail digest workflow."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from loguru import logger

from gmail_digest_tool.clients.gmail_client import GmailClient
from gmail_digest_tool.clients.openai_client import OpenAIClient
from gmail_digest_tool.config.settings import AppSettings, get_settings
from gmail_digest_tool.models.email_models import EmailSummary
from gmail_digest_tool.services.digest_builder import build_digest
from gmail_digest_tool.services.email_fetcher import EmailFetcher
from gmail_digest_tool.services.file_writer import write_digest
from gmail_digest_tool.services.summarizer import Summarizer, SummarizerConfig
from gmail_digest_tool.services.summary_store import SummaryRecord, SummaryStore
from gmail_digest_tool.utils.logging import configure_logging


def run_digest(
    unread_only: bool,
    from_datetime: datetime | None,
    to_datetime: datetime | None,
    *,
    settings: AppSettings | None = None,
) -> Path:
    """Run the end-to-end digest workflow."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    logger.info(
        f"Starting digest run (unread_only={unread_only}, "
        f"from={from_datetime}, to={to_datetime})"
    )

    gmail_client = GmailClient(
        credentials_path=settings.gmail_credentials_path,
        token_path=settings.gmail_token_path,
    )
    fetcher = EmailFetcher(gmail_client)
    summary_store = SummaryStore(settings.summary_csv_path)
    summarized_ids = summary_store.load_summarized_ids()
    if summarized_ids:
        logger.info(f"Found {len(summarized_ids)} previously summarized messages.")

    llm_client = OpenAIClient(
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_base_url,
        model=settings.openai_model,
    )
    summarizer = Summarizer(
        llm_client,
        config=SummarizerConfig(
            temperature=settings.summarizer_temperature,
            max_tokens=settings.summarizer_max_tokens,
            concurrency_limit=settings.summarizer_concurrency,
        ),
    )

    messages, criteria = fetcher.fetch(
        unread_only=unread_only,
        from_datetime=from_datetime,
        to_datetime=to_datetime,
        exclude_ids=summarized_ids,
    )
    logger.info(f"Fetched {len(messages)} new messages for summarization.")

    def _summarize_async() -> list[EmailSummary]:
        try:
            return asyncio.run(summarizer.summarize_many_async(messages))
        except RuntimeError as error:  # pragma: no cover - fallback for nested loops
            if "asyncio.run() cannot be called" not in str(error):
                raise
            logger.warning(
                "Async summarization unavailable in current event loop; "
                "falling back to sequential mode."
            )
            sequential_summaries: list[EmailSummary] = []
            for message in messages:
                subject_preview = (
                    message.subject
                    if len(message.subject) <= 80
                    else f"{message.subject[:77]}..."
                )
                logger.info(
                    f"Summarizing message {message.id} from {message.sender} "
                    f"(subject={subject_preview})"
                )
                try:
                    sequential_summaries.append(summarizer.summarize_email(message))
                except Exception as inner_error:  # pragma: no cover - defensive
                    logger.exception(
                        f"Failed to summarize message {message.id}: {inner_error}",
                    )
            return sequential_summaries

    summaries = _summarize_async()

    summary_store.append(
        SummaryRecord(
            email_id=item.message_id,
            sender=item.sender,
            summary=item.summary,
            received_at=item.internal_date,
        )
        for item in summaries
    )
    if summaries:
        logger.info(
            f"Persisted {len(summaries)} new summaries "
            f"to {settings.summary_csv_path}."
        )
    else:
        logger.info("No new summaries generated; summary CSV left unchanged.")

    digest_content = build_digest(summaries, run_time=criteria.end)
    output_path = write_digest(
        digest_content,
        settings.output_dir,
        run_time=criteria.end,
    )

    logger.success(f"Digest generated with {len(summaries)} entries.")
    return output_path
