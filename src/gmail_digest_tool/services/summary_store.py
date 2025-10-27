"""Persistence layer for summarized email records."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from loguru import logger

CSV_HEADERS = ("email_id", "sender", "summary", "received_at")


@dataclass(frozen=True)
class SummaryRecord:
    """A single summarized email entry."""

    email_id: str
    sender: str
    summary: str
    received_at: datetime


class SummaryStore:
    """Manage loading and persisting summarized email data."""

    def __init__(self, path: Path) -> None:
        """Initialize the store for a specific CSV path."""
        self._path = path

    def load_summarized_ids(self) -> set[str]:
        """Return the set of email IDs already persisted."""
        records = self._read_all_records()
        if not records:
            return set()
        ids = {record.email_id for record in records}
        logger.info(f"Loaded {len(ids)} summarized message IDs from {self._path}.")
        return ids

    def append(self, records: Iterable[SummaryRecord]) -> None:
        """Append new summary records to the CSV."""
        items = list(records)
        if not items:
            logger.info("No new summary records to persist.")
            return

        existing = {record.email_id: record for record in self._read_all_records()}
        for record in items:
            existing[record.email_id] = record

        ordered_records = sorted(
            existing.values(), key=lambda record: record.received_at, reverse=True
        )

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for record in ordered_records:
                writer.writerow(
                    {
                        "email_id": record.email_id,
                        "sender": record.sender,
                        "summary": record.summary,
                        "received_at": record.received_at.isoformat(),
                    }
                )
        logger.info(
            f"Persisted {len(items)} new summary records to {self._path} "
            f"(total rows: {len(ordered_records)})."
        )

    def _read_all_records(self) -> list[SummaryRecord]:
        """Load all summary records from disk."""
        if not self._path.exists():
            logger.info(f"Summary ledger {self._path} does not exist yet.")
            return []

        records: list[SummaryRecord] = []
        with self._path.open("r", newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            for row in reader:
                email_id = row.get("email_id")
                timestamp_raw = row.get("received_at") or row.get("timestamp")
                if not email_id or not timestamp_raw:
                    continue
                try:
                    timestamp = datetime.fromisoformat(timestamp_raw)
                except ValueError:
                    logger.warning(
                        f"Skipping summary row with invalid timestamp "
                        f"{timestamp_raw} for email {email_id}."
                    )
                    continue
                records.append(
                    SummaryRecord(
                        email_id=email_id,
                        sender=row.get("sender", ""),
                        summary=row.get("summary", ""),
                        received_at=timestamp,
                    )
                )
        return records
