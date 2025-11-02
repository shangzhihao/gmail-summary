from __future__ import annotations

import base64
import quopri
from datetime import UTC

from gmail_digest_tool.models.email_models import (
    EmailMessage,
    extract_body_content,
    extract_body_text,
)


def test_email_message_from_gmail_api_extracts_fields() -> None:
    payload = {
        "id": "123",
        "threadId": "thread",
        "snippet": "Snippet",
        "internalDate": "1704067200000",  # 2024-01-01
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "user@example.com"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": "SGVsbG8gV29ybGQh",  # "Hello World!"
                    },
                }
            ],
        },
    }

    message = EmailMessage.from_gmail_api(payload)
    assert message.subject == "Test Subject"
    assert message.sender == "sender@example.com"
    assert message.body_text == "Hello World!"
    assert message.body_charset == "utf-8"
    assert message.body_declared_charset is None
    assert message.internal_date.tzinfo == UTC


def test_extract_body_text_decodes_nested_base64() -> None:
    original_text = "Weekly digest: remember to review your pipeline runs."
    base64_encoded = base64.b64encode(original_text.encode("utf-8"))
    gmail_data = base64.urlsafe_b64encode(base64_encoded).decode("ascii")

    payload = {
        "mimeType": "text/plain",
        "headers": [
            {"name": "Content-Transfer-Encoding", "value": "base64"},
            {"name": "Content-Type", "value": 'text/plain; charset="utf-8"'},
        ],
        "body": {"data": gmail_data},
    }

    assert extract_body_text(payload) == original_text


def test_extract_body_text_renders_html_to_plain_text() -> None:
    html = (
        "<html><body><p>Hello <strong>team</strong>,</p>"
        "<p>Status update.</p></body></html>"
    )
    encoded = base64.b64encode(html.encode("utf-8"))
    gmail_data = base64.urlsafe_b64encode(encoded).decode("ascii")

    payload = {
        "mimeType": "text/html",
        "headers": [
            {"name": "Content-Transfer-Encoding", "value": "base64"},
            {"name": "Content-Type", "value": 'text/html; charset="utf-8"'},
        ],
        "body": {"data": gmail_data},
    }

    assert extract_body_text(payload) == "Hello team, Status update."


def test_extract_body_text_decodes_quoted_printable() -> None:
    original = "Reminder: stand-up at 9am."
    quoted = quopri.encodestring(original.encode("utf-8"))
    gmail_data = base64.urlsafe_b64encode(quoted).decode("ascii")

    payload = {
        "mimeType": "text/plain",
        "headers": [
            {"name": "Content-Transfer-Encoding", "value": "quoted-printable"},
            {"name": "Content-Type", "value": 'text/plain; charset="utf-8"'},
        ],
        "body": {"data": gmail_data},
    }

    assert extract_body_text(payload) == original


def test_extract_body_content_preserves_iso_charset() -> None:
    original = "Olá Café"
    raw_bytes = original.encode("iso-8859-1")
    gmail_data = base64.urlsafe_b64encode(raw_bytes).decode("ascii")

    payload = {
        "mimeType": "text/plain",
        "headers": [
            {"name": "Content-Transfer-Encoding", "value": "7bit"},
            {"name": "Content-Type", "value": 'text/plain; charset="iso-8859-1"'},
        ],
        "body": {"data": gmail_data},
    }

    body = extract_body_content(payload)
    assert body.text == original
    assert body.charset == "iso-8859-1"
    assert body.declared_charset == "iso-8859-1"


def test_extract_body_content_handles_unknown_charset_with_fallback() -> None:
    original = "Status: all systems go 🚀"
    raw_bytes = original.encode("utf-8")
    gmail_data = base64.urlsafe_b64encode(raw_bytes).decode("ascii")

    payload = {
        "mimeType": "text/plain",
        "headers": [
            {"name": "Content-Transfer-Encoding", "value": "7bit"},
            {"name": "Content-Type", "value": 'text/plain; charset="x-unknown"'},
        ],
        "body": {"data": gmail_data},
    }

    body = extract_body_content(payload)
    assert body.text == original
    assert body.charset == "utf-8"
    assert body.declared_charset == "x-unknown"
