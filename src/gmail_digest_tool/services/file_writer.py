"""Utilities for persisting digests to disk."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from loguru import logger


def write_digest(
    content: str,
    output_dir: Path,
    *,
    run_time: datetime | None = None,
) -> Path:
    """Write the digest content to a timestamped file and return the path."""
    timestamp = (run_time or datetime.now(UTC)).astimezone(UTC)
    filename = f"gmail_digest_{timestamp.strftime('%Y%m%dT%H%M%SZ')}.txt"

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / filename
    destination.write_text(content, encoding="utf-8")
    logger.info(f"Wrote digest to {destination}")
    return destination
