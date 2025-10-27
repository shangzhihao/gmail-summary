"""Helper script to generate a digest for the last 10 days of all emails."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gmail_digest_tool.config.settings import get_settings  # noqa: E402
from gmail_digest_tool.main import run_digest  # noqa: E402


def main() -> None:
    """Generate a digest covering the last ten days of email (including read)."""
    now = datetime.now(UTC)
    from_dt = now - timedelta(days=0.5)

    settings = get_settings()
    output_path = run_digest(
        unread_only=False,
        from_datetime=from_dt,
        to_datetime=now,
        settings=settings,
    )
    print(f"Digest generated at {output_path}")


if __name__ == "__main__":
    main()
