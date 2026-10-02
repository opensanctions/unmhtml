"""Convert a document to standalone HTML."""

from __future__ import annotations

from .document import Document
from .embed import embed
from .security import Security, clean, sanitize_css

DEFAULT_SECURITY = Security()


def to_standalone_html(
    document: Document, *, security: Security = DEFAULT_SECURITY
) -> str:
    """Return *document* as a single self-contained HTML string.

    Resources are embedded first, so the cleaner that follows can afford
    to be strict: a single nh3 pass — nh3's defaults plus the tag and
    attribute sets archived pages need — strips active content and the
    head's request-making furniture (link, meta, base) and reduces the
    document to a fragment. CSS sanitization runs last, when every
    reference the document could resolve is already a data URI and only
    genuinely external CSS is left to strip.
    """
    html = embed(document.html, document.resources, document.base_url)

    html = clean(html, security)

    if security.sanitize_css:
        html = sanitize_css(html)

    return html
