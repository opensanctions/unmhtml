"""Load MHTML archives as documents."""

from __future__ import annotations

import email
import email.message

from .document import Document, Resource


def load_mhtml(data: str | bytes) -> Document:
    """Parse MHTML content into a :class:`Document`.

    The first text/html part becomes the document's HTML and its
    Content-Location (when present) the base URL. Every other located part
    becomes a resource keyed by its Content-Location, typed by its
    Content-Type header.

    Raises:
        ValueError: If the content contains no text/html part.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    message = email.message_from_bytes(data)

    html: str | None = None
    base_url: str | None = None
    resources: dict[str, Resource] = {}

    for part in message.walk():
        if part.get_content_maintype() == "multipart":
            continue

        location = part.get("Content-Location", "").strip()
        if part.get_content_type() == "text/html" and html is None:
            html = _decode_text(part)
            base_url = location or None
        elif location:
            payload = part.get_payload(decode=True)
            if payload is not None:
                resources[location] = Resource(payload, part.get_content_type())

    if html is None:
        raise ValueError("no text/html part found in MHTML content")

    return Document(html=html, resources=resources, base_url=base_url)


def _decode_text(part: email.message.Message) -> str:
    """Decode a text part using its declared charset, defaulting to UTF-8."""
    payload = part.get_payload(decode=True)
    charset = part.get_content_charset() or "utf-8"
    return (payload or b"").decode(charset, errors="replace")
