"""Convert a document to standalone HTML."""

from __future__ import annotations

from .document import Document
from .embed import embed
from .security import Security, apply_security, sanitize_css

DEFAULT_SECURITY = Security()


def to_standalone_html(
    document: Document, *, security: Security = DEFAULT_SECURITY
) -> str:
    """Return *document* as a single self-contained HTML string.

    A structural nh3 pass runs before embedding — it normalizes the
    document and strips active content (scripts, event handlers, form
    submission attributes, meta redirects). CSS sanitization runs after
    embedding, so every reference the document can resolve is embedded as
    a data URI and only genuinely external CSS survives to be stripped.
    """
    html = apply_security(document.html, security, base_url=document.base_url)

    html = embed(html, document.resources, document.base_url)

    if security.sanitize_css:
        html = sanitize_css(html)

    return html
