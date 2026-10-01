"""Sanitization policies for untrusted HTML."""

from __future__ import annotations

from dataclasses import dataclass

from .regex_utils import (
    RegexPatterns,
    remove_event_handlers,
    remove_html_tags,
    replace_attribute_values,
    sanitize_inline_styles,
)


@dataclass(frozen=True)
class Security:
    """What classes of active or request-making content to remove.

    Defaults remove all of them, making the result safe to display as
    untrusted content.
    """

    remove_javascript: bool = True
    sanitize_css: bool = True
    remove_forms: bool = True
    remove_meta_redirects: bool = True


def remove_javascript_content(html: str) -> str:
    """
    Remove potentially dangerous JavaScript content from HTML.

    This function removes potentially dangerous JavaScript content to make it
    safer for display:

    1. Removes all <script> tags and their contents (including external script references)
    2. Removes all event handlers (onclick, onload, onmouseover, etc.)
    3. Converts javascript: URLs to safe # anchors
    4. Removes data URIs containing JavaScript
    5. Removes noscript tags (they may contain fallback JavaScript)
    6. Removes SVG script elements

    Args:
        html: HTML content to clean

    Returns:
        HTML string with dangerous JavaScript elements removed

    Example:
        >>> html = '<div onclick="alert()">Hello</div><script>alert("bad")</script>'
        >>> remove_javascript_content(html)
        '<div>Hello</div>'

        >>> html = '<a href="javascript:alert()">Link</a>'
        >>> remove_javascript_content(html)
        '<a href="#">Link</a>'
    """
    script_patterns = [RegexPatterns.SCRIPT_TAGS, RegexPatterns.NOSCRIPT_TAGS]
    html = remove_html_tags(html, script_patterns)

    # Remove SVG script elements (special case requiring lambda)
    html = RegexPatterns.SVG_SCRIPT_TAGS.sub(
        lambda m: RegexPatterns.SCRIPT_TAGS.sub("", m.group(0)), html
    )

    # Remove event handlers
    html = remove_event_handlers(html)

    # Replace javascript: URLs with safe anchors
    html = replace_attribute_values(
        html, RegexPatterns.JAVASCRIPT_URLS_HREF, 'href="#"'
    )
    html = replace_attribute_values(html, RegexPatterns.JAVASCRIPT_URLS_SRC, 'src="#"')
    html = replace_attribute_values(html, RegexPatterns.DATA_URI_JAVASCRIPT, r'\1="#"')

    # Remove expression() CSS
    html = RegexPatterns.EXPRESSION_CSS.sub("", html)

    return html


def sanitize_css(html: str) -> str:
    """
    Remove CSS constructs that can make network requests or execute code.

    Meant to run after resource embedding: url() references that were
    resolvable have already become data URIs, so this strips what is left.

    1. Removes @import statements that load external stylesheets
    2. Removes url() references that are not data URIs (preserving
       data: URIs and #fragment references)
    3. Removes IE-specific expression() properties
    4. Removes behavior: properties

    Args:
        html: HTML content containing CSS to sanitize

    Returns:
        HTML string with dangerous CSS properties removed

    Example:
        >>> html = '<style>@import url("http://evil.com/style.css");</style>'
        >>> sanitize_css(html)
        '<style></style>'
    """
    css_patterns = [
        RegexPatterns.CSS_IMPORT,
        RegexPatterns.CSS_URL_NON_DATA,
        RegexPatterns.EXPRESSION_CSS,
        RegexPatterns.CSS_BEHAVIOR,
    ]

    for pattern in css_patterns:
        html = pattern.sub("", html)

    # Also sanitize inline style attributes
    html = sanitize_inline_styles(html)

    return html


def remove_forms(html: str) -> str:
    """
    Remove form elements that could submit data externally.

    This function removes potentially dangerous form elements that could be used to
    submit data to external endpoints:

    1. Removes <form> elements and their contents
    2. Removes <input> elements (all types)
    3. Removes <textarea> elements
    4. Removes <select> elements and their <option> children
    5. Removes <button type="submit"> elements
    6. Removes <fieldset> and <legend> elements
    7. Removes <label> elements (as they become meaningless without form controls)

    Args:
        html: HTML content containing forms to remove

    Returns:
        HTML string with form elements removed

    Example:
        >>> html = '<form action="/submit"><input type="text" name="data"><button type="submit">Submit</button></form>'
        >>> remove_forms(html)
        ''

        >>> html = '<div><p>Text</p><form><input type="hidden" name="csrf"></form><p>More text</p></div>'
        >>> remove_forms(html)
        '<div><p>Text</p><p>More text</p></div>'
    """
    form_patterns = [
        RegexPatterns.FORM_TAGS,
        RegexPatterns.INPUT_TAGS,
        RegexPatterns.TEXTAREA_TAGS,
        RegexPatterns.SELECT_TAGS,
        RegexPatterns.BUTTON_TAGS,
        RegexPatterns.FIELDSET_TAGS,
        RegexPatterns.LEGEND_TAGS,
        RegexPatterns.LABEL_TAGS,
        RegexPatterns.DATALIST_TAGS,
    ]
    return remove_html_tags(html, form_patterns)


def remove_meta_redirects(html: str) -> str:
    """
    Remove dangerous meta tags that can redirect or set cookies.

    This function removes potentially dangerous meta tags that could be used for
    malicious redirects or tracking:

    1. Removes meta refresh tags that automatically redirect pages
    2. Removes meta http-equiv set-cookie tags
    3. Removes meta dns-prefetch tags that could leak information

    Args:
        html: HTML content containing meta tags to sanitize

    Returns:
        HTML string with dangerous meta tags removed

    Example:
        >>> html = '<meta http-equiv="refresh" content="0;url=http://evil.com">'
        >>> remove_meta_redirects(html)
        ''
    """
    meta_patterns = [
        RegexPatterns.META_REFRESH,
        RegexPatterns.META_SET_COOKIE,
        RegexPatterns.META_DNS_PREFETCH,
    ]
    return remove_html_tags(html, meta_patterns)
