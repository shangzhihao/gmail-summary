from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from gmail_digest_tool.services.file_writer import write_digest


def test_write_digest_creates_file(tmp_path: Path) -> None:
    run_time = datetime(2024, 1, 1, 12, tzinfo=UTC)
    output_path = write_digest("content", tmp_path, run_time=run_time)
    assert output_path.exists()
    assert output_path.read_text() == "content"
    assert output_path.name.startswith("gmail_digest_20240101T120000Z")
