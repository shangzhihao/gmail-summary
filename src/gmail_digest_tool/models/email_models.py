"""Pydantic data models for Gmail messages and summaries."""

from __future__ import annotations

import binascii
import codecs
import quopri
import re
from base64 import b64decode, urlsafe_b64decode
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from typing import Any

from pydantic import BaseModel, Field, computed_field

BASE64_ALLOWED_BYTES = set(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r-_"
)
PRINTABLE_BYTES = set(range(32, 127)) | {9, 10, 13}
DEFAULT_CHARSET = "utf-8"
FALLBACK_CHARSETS: tuple[str, ...] = (DEFAULT_CHARSET, "windows-1252", "latin-1")


@dataclass(frozen=True)
class DecodedBodyPart:
    """Decoded representation of a MIME body part."""

    mime_type: str
    text: str
    charset: str
    declared_charset: str | None = None


class EmailMessage(BaseModel):
    """Normalized representation of a Gmail message."""

    id: str
    thread_id: str
    subject: str
    sender: str
    recipients: list[str] = Field(default_factory=list)
    snippet: str
    body_text: str
    body_charset: str = Field(default=DEFAULT_CHARSET)
    body_declared_charset: str | None = Field(default=None)
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

        body_content = extract_body_content(payload.get("payload", {}))

        return cls(
            id=payload["id"],
            thread_id=payload.get("threadId", payload["id"]),
            subject=subject,
            sender=sender,
            recipients=recipients,
            snippet=payload.get("snippet", ""),
            body_text=body_content.text,
            body_charset=body_content.charset,
            body_declared_charset=body_content.declared_charset,
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
    return extract_body_content(payload).text


def extract_body_content(payload: dict[str, Any]) -> DecodedBodyPart:
    """Extract plain-text body content from a Gmail message payload."""
    if not payload:
        return DecodedBodyPart(
            mime_type="",
            text="",
            charset=DEFAULT_CHARSET,
            declared_charset=None,
        )

    candidates = _gather_text_parts(payload)
    for part in candidates:
        stripped = part.text.strip()
        if part.mime_type == "text/plain" and stripped:
            return DecodedBodyPart(
                mime_type="text/plain",
                text=stripped,
                charset=part.charset,
                declared_charset=part.declared_charset,
            )

    for part in candidates:
        stripped = part.text.strip()
        if part.mime_type == "text/html" and stripped:
            return DecodedBodyPart(
                mime_type="text/plain",
                text=_html_to_plain_text(stripped),
                charset=part.charset,
                declared_charset=part.declared_charset,
            )

    for part in candidates:
        stripped = part.text.strip()
        if stripped:
            return DecodedBodyPart(
                mime_type=part.mime_type or "text/plain",
                text=stripped,
                charset=part.charset,
                declared_charset=part.declared_charset,
            )

    return DecodedBodyPart(
        mime_type="",
        text="",
        charset=DEFAULT_CHARSET,
        declared_charset=None,
    )


def _gather_text_parts(payload: dict[str, Any]) -> list[DecodedBodyPart]:
    """Recursively collect decoded text parts from the payload."""
    mime_type = (payload.get("mimeType") or "").lower()
    if mime_type.startswith("multipart/"):
        texts: list[DecodedBodyPart] = []
        for part in payload.get("parts", []):
            texts.extend(_gather_text_parts(part))
        return texts

    decoded_part = _decode_part_to_text(payload)
    if decoded_part:
        return [decoded_part]
    return []


def _decode_part_to_text(part: dict[str, Any]) -> DecodedBodyPart | None:
    """Decode a single MIME part into text."""
    mime_type = (part.get("mimeType") or "").lower()
    if not mime_type.startswith("text/"):
        return None

    body = part.get("body") or {}
    data = body.get("data")
    if not data or body.get("attachmentId"):
        return None

    decoded = _decode_body_data(data)
    if not decoded:
        return None

    headers = _build_header_map(part)
    transfer_encoding = headers.get("content-transfer-encoding", "")
    decoded = _apply_transfer_encoding(decoded, transfer_encoding)
    decoded = _maybe_decode_nested_base64(decoded, transfer_encoding)

    declared_charset = _extract_charset(headers)
    text, effective_charset = _decode_bytes_with_charset(decoded, declared_charset)

    return DecodedBodyPart(
        mime_type=mime_type,
        text=text,
        charset=effective_charset,
        declared_charset=declared_charset,
    )


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


def _decode_bytes_with_charset(
    data: bytes, declared_charset: str | None
) -> tuple[str, str]:
    """Decode bytes using the declared charset with sensible fallbacks."""
    candidates = _build_charset_candidates(declared_charset)
    for candidate in candidates:
        try:
            return data.decode(candidate, errors="strict"), candidate
        except (LookupError, UnicodeDecodeError):
            continue

    # Final fallback: replace undecodable bytes using UTF-8.
    return data.decode(DEFAULT_CHARSET, errors="replace"), DEFAULT_CHARSET


def _build_charset_candidates(declared_charset: str | None) -> list[str]:
    """Return the ordered list of charset candidates to try for decoding."""
    candidates: list[str] = []
    if declared_charset:
        stripped = declared_charset.strip()
        if stripped and stripped not in candidates:
            candidates.append(stripped)

        normalized = _normalize_charset_name(stripped)
        if normalized and normalized not in candidates:
            candidates.insert(0, normalized)

        lowered = stripped.lower()
        if lowered not in candidates:
            candidates.append(lowered)

        dashed = lowered.replace("_", "-")
        if dashed not in candidates:
            candidates.append(dashed)

    for fallback in FALLBACK_CHARSETS:
        if fallback not in candidates:
            candidates.append(fallback)

    return candidates


def _normalize_charset_name(charset: str | None) -> str | None:
    """Return a Python-compatible charset name if available."""
    if not charset:
        return None

    cleaned = charset.strip().strip('"').strip("'")
    if not cleaned:
        return None

    for candidate in (
        cleaned,
        cleaned.lower(),
        cleaned.lower().replace("_", "-"),
    ):
        try:
            codecs.lookup(candidate)
        except LookupError:
            continue
        return candidate

    return None


def _extract_charset(headers: dict[str, str]) -> str | None:
    """Determine the charset declared for a MIME part, if any."""
    content_type = headers.get("content-type", "")
    match = re.search(
        r"charset=([\"']?)([^;\"']+)\1", content_type, flags=re.IGNORECASE
    )
    if match:
        return match.group(2).strip()

    charset_header = headers.get("charset")
    if charset_header:
        return charset_header.strip()

    return None


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
