"""Service for retrieving email messages from Gmail."""

from __future__ import annotations

from datetime import datetime

from loguru import logger

from gmail_digest_tool.clients.gmail_client import GmailClient
from gmail_digest_tool.models.email_models import EmailMessage
from gmail_digest_tool.services.filters import (
    DEFAULT_LABELS,
    FilterCriteria,
    build_filter_criteria,
)


class EmailFetcher:
    """Fetch email messages using the Gmail client."""

    def __init__(self, client: GmailClient) -> None:
        """Initialize the email fetcher with a Gmail client."""
        self._client = client

    def fetch(
        self,
        unread_only: bool,
        from_datetime: datetime | None,
        to_datetime: datetime | None,
        *,
        exclude_ids: set[str] | None = None,
    ) -> tuple[list[EmailMessage], FilterCriteria]:
        """Fetch email messages using the requested filters."""
        criteria = build_filter_criteria(
            unread_only=unread_only,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
        )

        query = criteria.to_query()
        logger.info(
            f"Fetching Gmail messages with filters "
            f"unread_only={criteria.unread_only}, "
            f"start={criteria.start}, end={criteria.end}"
        )

        messages = self._client.fetch_messages(
            query=query,
            label_ids=DEFAULT_LABELS or None,
            exclude_ids=exclude_ids or set(),
        )
        filtered = self._post_filter(messages, criteria)
        logger.info(f"Retained {len(filtered)} messages after post-filtering.")
        return filtered, criteria

    @staticmethod
    def _post_filter(
        messages: list[EmailMessage],
        criteria: FilterCriteria,
    ) -> list[EmailMessage]:
        """Apply final validation on message timestamps."""
        return [
            message
            for message in messages
            if criteria.start <= message.internal_date <= criteria.end
        ]
