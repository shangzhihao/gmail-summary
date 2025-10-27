from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from gmail_digest_tool.services.summary_store import SummaryRecord, SummaryStore


def test_summary_store_loads_empty(tmp_path: Path) -> None:
    store = SummaryStore(tmp_path / "summary.csv")
    assert store.load_summarized_ids() == set()


def test_summary_store_appends_and_loads(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    store = SummaryStore(path)

    records = [
        SummaryRecord(
            email_id="id-1",
            sender="sender@example.com",
            summary="Hello",
            received_at=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        SummaryRecord(
            email_id="id-2",
            sender="other@example.com",
            summary="World",
            received_at=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    ]

    store.append(records)
    assert path.exists()

    ids = store.load_summarized_ids()
    assert ids == {"id-1", "id-2"}

    # Appending again should not rewrite headers
    store.append(
        [
            SummaryRecord(
                email_id="id-3",
                sender="x",
                summary="y",
                received_at=datetime(2024, 1, 3, tzinfo=UTC),
            )
        ]
    )
    assert store.load_summarized_ids() == {"id-1", "id-2", "id-3"}

    rows = path.read_text(encoding="utf-8").strip().splitlines()
    assert rows[0] == "email_id,sender,summary,received_at"
    assert rows[1].startswith("id-3,")
    assert rows[2].startswith("id-1,")
    assert rows[3].startswith("id-2,")


def test_summary_store_ignores_empty_appends(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    store = SummaryStore(path)

    store.append([])
    assert not path.exists()
