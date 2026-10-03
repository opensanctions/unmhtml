"""
unmhtml - make HTML documents self-contained

A library for converting MHTML files — or any parsed HTML document
with its resources — into standalone HTML with embedded CSS and resources,
sanitized for safe display of untrusted content.

Basic Usage:
    >>> from unmhtml import load_mhtml, to_standalone_html
    >>> document = load_mhtml(mhtml_content)
    >>> html_content = to_standalone_html(document)
    >>> with open('output.html', 'w') as f:
    ...     f.write(html_content)

Working with HTML and resources directly (e.g. from a HAR archive):
    >>> from unmhtml import Document, Resource, Security, to_standalone_html
    >>> document = Document(
    ...     html=rendered_html,
    ...     resources={'https://example.com/logo.png': Resource(png_bytes, 'image/png')},
    ...     base_url='https://example.com/page.html',
    ... )
    >>> html_content = to_standalone_html(document)

Conversion is secure by default; pass a Security value to adjust what is
removed:
    >>> html_content = to_standalone_html(document, security=Security(disable_forms=False))
"""

from .convert import to_standalone_html
from .document import Document, Resource
from .mhtml import load_mhtml
from .security import Security

__version__ = "0.4.0"
__all__ = [
    "Document",
    "Resource",
    "Security",
    "load_mhtml",
    "to_standalone_html",
]
