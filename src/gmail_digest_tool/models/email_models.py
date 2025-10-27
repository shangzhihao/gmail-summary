"""Pydantic data models for Gmail messages and summaries."""

from __future__ import annotations

import binascii
import quopri
import re
from base64 import b64decode, urlsafe_b64decode
from datetime import UTC, datetime
from html import unescape
from typing import Any

from pydantic import BaseModel, Field, computed_field

BASE64_ALLOWED_BYTES = set(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r-_"
)
PRINTABLE_BYTES = set(range(32, 127)) | {9, 10, 13}


class EmailMessage(BaseModel):
    """Normalized representation of a Gmail message."""

    id: str
    thread_id: str
    subject: str
    sender: str
    recipients: list[str] = Field(default_factory=list)
    snippet: str
    body_text: str
    internal_date: datetime
    labels: list[str] = Field(default_factory=list)
    gmail_metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    def web_link(self) -> str:
        """Return a Gmail web link to the message."""
        return f"https://mail.google.com/mail/u/0/#inbox/{self.id}"

    @classmethod
    def from_gmail_api(cls, payload: dict[str, Any]) -> EmailMessage:
        """Create an instance from a Gmail API response."""
        internal_date_raw = payload.get("internalDate", "0")
        internal_date = datetime.fromtimestamp(int(internal_date_raw) / 1000, tz=UTC)

        headers = {h["name"].lower(): h["value"] for h in payload["payload"]["headers"]}
        subject = headers.get("subject", "(no subject)")
        sender = headers.get("from", "unknown sender")

        recipients: list[str] = []
        if "to" in headers:
            recipients = [addr.strip() for addr in headers["to"].split(",") if addr]

        body_text = extract_body_text(payload.get("payload", {}))

        return cls(
            id=payload["id"],
            thread_id=payload.get("threadId", payload["id"]),
            subject=subject,
            sender=sender,
            recipients=recipients,
            snippet=payload.get("snippet", ""),
            body_text=body_text,
            internal_date=internal_date,
            labels=payload.get("labelIds", []),
            gmail_metadata=payload,
        )


class EmailSummary(BaseModel):
    """Summary generated for an email message."""

    message_id: str
    summary: str
    subject: str
    sender: str
    recipients: list[str] = Field(default_factory=list)
    internal_date: datetime
    web_link: str


def extract_body_text(payload: dict[str, Any]) -> str:
    """Extract plain-text body content from a Gmail message payload."""
    if not payload:
        return ""

    candidates = _gather_text_parts(payload)
    for mime_type, text in candidates:
        stripped = text.strip()
        if mime_type == "text/plain" and stripped:
            return stripped

    for mime_type, text in candidates:
        stripped = text.strip()
        if mime_type == "text/html" and stripped:
            return _html_to_plain_text(stripped)

    for _, text in candidates:
        stripped = text.strip()
        if stripped:
            return stripped

    return ""


def _gather_text_parts(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """Recursively collect (mime_type, text) tuples from the payload."""
    mime_type = (payload.get("mimeType") or "").lower()
    if mime_type.startswith("multipart/"):
        texts: list[tuple[str, str]] = []
        for part in payload.get("parts", []):
            texts.extend(_gather_text_parts(part))
        return texts

    text = _decode_part_to_text(payload)
    if text:
        return [(mime_type, text)]
    return []


def _decode_part_to_text(part: dict[str, Any]) -> str:
    """Decode a single MIME part into text."""
    mime_type = (part.get("mimeType") or "").lower()
    if not mime_type.startswith("text/"):
        return ""

    body = part.get("body") or {}
    data = body.get("data")
    if not data or body.get("attachmentId"):
        return ""

    decoded = _decode_body_data(data)
    if not decoded:
        return ""

    headers = _build_header_map(part)
    transfer_encoding = headers.get("content-transfer-encoding", "")
    decoded = _apply_transfer_encoding(decoded, transfer_encoding)
    decoded = _maybe_decode_nested_base64(decoded, transfer_encoding)

    charset = _extract_charset(headers)
    try:
        return decoded.decode(charset, errors="ignore")
    except LookupError:
        return decoded.decode("utf-8", errors="ignore")


def _decode_body_data(data: str) -> bytes:
    """Decode the base64url-encoded data field provided by the Gmail API."""
    normalized = data.strip()
    padding = (-len(normalized)) % 4
    if padding:
        normalized += "=" * padding

    try:
        return urlsafe_b64decode(normalized)
    except (binascii.Error, ValueError):
        return b""


def _apply_transfer_encoding(data: bytes, encoding: str | None) -> bytes:
    """Apply the MIME Content-Transfer-Encoding if present."""
    if not data:
        return data

    encoding_normalized = (encoding or "").strip().lower()
    if encoding_normalized == "base64":
        try:
            return b64decode(data, validate=False)
        except binascii.Error:
            return data

    if encoding_normalized == "quoted-printable":
        return quopri.decodestring(data)

    return data


def _maybe_decode_nested_base64(data: bytes, encoding: str | None) -> bytes:
    """Decode nested base64 payloads even if headers omit the transfer encoding."""
    if not data:
        return data

    if (encoding or "").strip().lower() == "base64":
        return data

    sample = data.strip()
    if len(sample) < 32:
        return data

    compact = sample.replace(b"\n", b"").replace(b"\r", b"")
    if len(compact) % 4 != 0:
        return data

    if not compact or any(byte not in BASE64_ALLOWED_BYTES for byte in compact):
        return data

    try:
        decoded = b64decode(compact, validate=False)
    except binascii.Error:
        return data

    return decoded if decoded and _is_likely_text(decoded) else data


def _is_likely_text(data: bytes) -> bool:
    """Return whether the byte sequence looks like human-readable text."""
    if not data:
        return False

    printable = sum(1 for byte in data if byte in PRINTABLE_BYTES)
    return printable / len(data) >= 0.75


def _extract_charset(headers: dict[str, str]) -> str:
    """Determine the charset for decoding the bytes payload."""
    content_type = headers.get("content-type", "")
    match = re.search(
        r"charset=([\"']?)([^;\"']+)\1", content_type, flags=re.IGNORECASE
    )
    if match:
        return match.group(2).strip()
    return "utf-8"


def _html_to_plain_text(html: str) -> str:
    """Convert HTML content into a readable plain-text string."""
    cleaned = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    cleaned = re.sub(r"(?i)<br\\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</(p|div)>", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned.strip()


def _build_header_map(part: dict[str, Any]) -> dict[str, str]:
    """Construct a case-insensitive header lookup for a MIME part."""
    headers: dict[str, str] = {}
    for header in part.get("headers", []):
        name = header.get("name")
        value = header.get("value")
        if name and value:
            headers[name.lower()] = value
    return headers
