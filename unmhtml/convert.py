"""Convert a document to standalone HTML."""

from __future__ import annotations

from .document import Document
from .embed import embed
from .security import (
    Security,
    remove_forms,
    remove_javascript_content,
    remove_meta_redirects,
    sanitize_css,
)

DEFAULT_SECURITY = Security()


def to_standalone_html(
    document: Document, *, security: Security = DEFAULT_SECURITY
) -> str:
    """Return *document* as a single self-contained HTML string.

    Content removals run before embedding — nothing they remove needs
    embedding. CSS sanitization runs after embedding, so every reference the
    document can resolve is embedded as a data URI and only genuinely
    external CSS survives to be stripped.
    """
    html = document.html

    if security.remove_javascript:
        html = remove_javascript_content(html)
    if security.remove_forms:
        html = remove_forms(html)
    if security.remove_meta_redirects:
        html = remove_meta_redirects(html)

    html = embed(html, document.resources, document.base_url)

    if security.sanitize_css:
        html = sanitize_css(html)

    return html
