from __future__ import annotations

import re

# Common regex flags used throughout the application
COMMON_FLAGS = re.DOTALL | re.IGNORECASE
IGNORECASE_ONLY = re.IGNORECASE


class RegexPatterns:
    """
    Centralized collection of regex patterns used across the converter.

    This class provides compiled regex patterns and common operations to avoid
    duplication and ensure consistency across the codebase.
    """

    # JavaScript removal patterns
    SCRIPT_TAGS = re.compile(r"<script[^>]*>.*?</script>", COMMON_FLAGS)
    NOSCRIPT_TAGS = re.compile(r"<noscript[^>]*>.*?</noscript>", COMMON_FLAGS)
    SVG_SCRIPT_TAGS = re.compile(
        r"<svg[^>]*>.*?<script[^>]*>.*?</script>.*?</svg>", COMMON_FLAGS
    )
    JAVASCRIPT_URLS_HREF = re.compile(
        r'href\s*=\s*["\']javascript:[^"\']*["\']', IGNORECASE_ONLY
    )
    JAVASCRIPT_URLS_SRC = re.compile(
        r'src\s*=\s*["\']javascript:[^"\']*["\']', IGNORECASE_ONLY
    )
    DATA_URI_JAVASCRIPT = re.compile(
        r'(src|href)\s*=\s*["\']data:[^"\']*javascript[^"\']*["\']', IGNORECASE_ONLY
    )
    EXPRESSION_CSS = re.compile(r"expression\s*\([^)]*\)", IGNORECASE_ONLY)

    # CSS sanitization patterns
    CSS_IMPORT = re.compile(
        r'@import\s+(?:url\([^)]*\)|["\'][^"\']*["\'])[^;]*;?', IGNORECASE_ONLY
    )
    # Any url() whose target is not a data URI or fragment reference. Runs
    # after embedding, so resolvable references have already become data:
    # URIs and everything left is a live external request.
    CSS_URL_NON_DATA = re.compile(
        r'url\s*\(\s*["\']?(?!data:|#)([^"\')\s]+)["\']?\s*\)', IGNORECASE_ONLY
    )
    CSS_BEHAVIOR = re.compile(r"behavior\s*:\s*[^;]+;?", IGNORECASE_ONLY)

    # Form removal patterns
    FORM_TAGS = re.compile(r"<form[^>]*>.*?</form>", COMMON_FLAGS)
    INPUT_TAGS = re.compile(r"<input[^>]*/?>", IGNORECASE_ONLY)
    TEXTAREA_TAGS = re.compile(r"<textarea[^>]*>.*?</textarea>", COMMON_FLAGS)
    SELECT_TAGS = re.compile(r"<select[^>]*>.*?</select>", COMMON_FLAGS)
    BUTTON_TAGS = re.compile(r"<button[^>]*>.*?</button>", COMMON_FLAGS)
    FIELDSET_TAGS = re.compile(r"<fieldset[^>]*>.*?</fieldset>", COMMON_FLAGS)
    LEGEND_TAGS = re.compile(r"<legend[^>]*>.*?</legend>", COMMON_FLAGS)
    LABEL_TAGS = re.compile(r"<label[^>]*>.*?</label>", COMMON_FLAGS)
    DATALIST_TAGS = re.compile(r"<datalist[^>]*>.*?</datalist>", COMMON_FLAGS)

    # Meta tag removal patterns
    META_REFRESH = re.compile(
        r'<meta[^>]*http-equiv\s*=\s*["\']?refresh["\']?[^>]*>', IGNORECASE_ONLY
    )
    META_SET_COOKIE = re.compile(
        r'<meta[^>]*http-equiv\s*=\s*["\']?set-cookie["\']?[^>]*>', IGNORECASE_ONLY
    )
    META_DNS_PREFETCH = re.compile(
        r'<meta[^>]*name\s*=\s*["\']?dns-prefetch["\']?[^>]*>', IGNORECASE_ONLY
    )

    # Event handler removal patterns
    EVENT_HANDLERS = re.compile(
        r'\s+on(?:abort|beforeunload|blur|change|click|contextmenu|copy|cut|dblclick|drag|dragend|dragenter|dragleave|dragover|dragstart|drop|error|focus|hashchange|input|keydown|keypress|keyup|load|mousedown|mousemove|mouseout|mouseover|mouseup|mousewheel|offline|online|paste|reset|resize|scroll|select|storage|submit|unload|wheel)\s*=\s*["\'][^"\']*["\']',
        IGNORECASE_ONLY,
    )

    # Inline style sanitization pattern
    INLINE_STYLE_ATTR = re.compile(
        r'(style\s*=\s*["\'])([^"\']*)["\']', IGNORECASE_ONLY
    )


def remove_html_tags(html: str, patterns: list[re.Pattern]) -> str:
    """
    Generic HTML tag removal utility.

    Applies multiple regex patterns to remove HTML tags from HTML content.

    Args:
        html: HTML content to process
        patterns: List of compiled regex patterns to apply

    Returns:
        HTML string with matching tags removed
    """
    for pattern in patterns:
        html = pattern.sub("", html)
    return html


def replace_attribute_values(html: str, pattern: re.Pattern, replacement: str) -> str:
    """
    Generic attribute value replacement utility.

    Replaces attribute values that match a pattern with a safe replacement.

    Args:
        html: HTML content to process
        pattern: Compiled regex pattern to match
        replacement: Replacement string

    Returns:
        HTML string with attribute values replaced
    """
    return pattern.sub(replacement, html)


def remove_event_handlers(html: str) -> str:
    """
    Remove all JavaScript event handlers from HTML.

    Args:
        html: HTML content to process

    Returns:
        HTML string with event handler attributes removed
    """
    return RegexPatterns.EVENT_HANDLERS.sub("", html)


def sanitize_inline_styles(html: str) -> str:
    """
    Sanitize inline style attributes by removing dangerous CSS properties.

    Removes CSS properties from inline style attributes that could be used to
    make external requests or execute JavaScript. Data URIs and fragment
    references are preserved.

    Args:
        html: HTML content to process

    Returns:
        HTML string with sanitized inline styles
    """

    def sanitize_style_content(match):
        prefix = match.group(1)
        style_content = match.group(2)
        suffix = '"'

        style_content = RegexPatterns.CSS_IMPORT.sub("", style_content)
        style_content = RegexPatterns.CSS_URL_NON_DATA.sub("", style_content)
        style_content = RegexPatterns.EXPRESSION_CSS.sub("", style_content)
        style_content = RegexPatterns.CSS_BEHAVIOR.sub("", style_content)

        return f"{prefix}{style_content}{suffix}"

    return RegexPatterns.INLINE_STYLE_ATTR.sub(sanitize_style_content, html)
