"""Sanitization policies for untrusted HTML."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass

import nh3

# --------------------------------------------------------------------------
# CSS sanitization (post-embed, whole-document regex passes)
# --------------------------------------------------------------------------

# @import statements, in url() or string form
CSS_IMPORT = re.compile(
    r'@import\s+(?:url\([^)]*\)|["\'][^"\']*["\'])[^;]*;?', re.IGNORECASE
)
# Any url() whose target is not a data URI or fragment reference. Runs after
# embedding, so resolvable references have already become data: URIs and
# everything left is a live external request.
CSS_URL_NON_DATA = re.compile(
    r'url\s*\(\s*["\']?(?!data:|#)([^"\')\s]+)["\']?\s*\)', re.IGNORECASE
)
# IE-specific expression() properties
EXPRESSION_CSS = re.compile(r"expression\s*\([^)]*\)", re.IGNORECASE)
# IE-specific behavior: properties
CSS_BEHAVIOR = re.compile(r"behavior\s*:\s*[^;]+;?", re.IGNORECASE)

# Inline style attributes
INLINE_STYLE_ATTR = re.compile(r'(style\s*=\s*["\'])([^"\']*)["\']', re.IGNORECASE)

_DOCTYPE = re.compile(r"^\s*<!DOCTYPE[^>]*>", re.IGNORECASE)

# Characters browsers strip from URLs: C0 controls and space at either end,
# and tab/newline/carriage-return anywhere.
_URL_EDGE_CHARS = "".join(chr(c) for c in range(0x21))
_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")
_URL_ATTRIBUTES = frozenset(
    {"href", "src", "data", "poster", "background", "cite", "longdesc"}
)
_URL_SCHEMES = frozenset({"http", "https", "mailto", "tel", "ftp", "data"})
# data: URIs that may reference a document rather than passive media
_SVG_HOST_TAGS = frozenset({"iframe", "embed", "object"})

# Tags nh3 does not allow by default that archived pages need
_CONTENT_TAGS = frozenset(
    {
        "title",
        "meta",
        "link",
        "style",
        "picture",
        "source",
        "audio",
        "video",
        "track",
        "canvas",
        "iframe",
        "embed",
        "object",
        "param",
        "template",
        "dialog",
        "output",
        "meter",
        "progress",
        "datalist",
        "form",
        "input",
        "button",
        "select",
        "option",
        "optgroup",
        "textarea",
        "label",
        "fieldset",
        "legend",
    }
)

_SVG_TAGS = frozenset(
    {
        "svg",
        "g",
        "defs",
        "symbol",
        "use",
        "path",
        "rect",
        "circle",
        "ellipse",
        "line",
        "polyline",
        "polygon",
        "text",
        "tspan",
        "textPath",
        "marker",
        "pattern",
        "clipPath",
        "mask",
        "linearGradient",
        "radialGradient",
        "stop",
        "image",
        "switch",
        "foreignObject",
        "animate",
        "animateMotion",
        "animateTransform",
        "set",
        "filter",
        "feBlend",
        "feColorMatrix",
        "feComponentTransfer",
        "feComposite",
        "feConvolveMatrix",
        "feDiffuseLighting",
        "feDisplacementMap",
        "feDistantLight",
        "feDropShadow",
        "feFlood",
        "feFuncA",
        "feFuncB",
        "feFuncG",
        "feFuncR",
        "feGaussianBlur",
        "feImage",
        "feMerge",
        "feMergeNode",
        "feMorphology",
        "feOffset",
        "fePointLight",
        "feSpecularLighting",
        "feSpotLight",
        "feTile",
        "feTurbulence",
    }
)

_MATHML_TAGS = frozenset(
    {
        "math",
        "mi",
        "mn",
        "mo",
        "ms",
        "mtext",
        "mrow",
        "mfrac",
        "msqrt",
        "mroot",
        "mstyle",
        "merror",
        "mpadded",
        "mphantom",
        "mfenced",
        "menclose",
        "msub",
        "msup",
        "msubsup",
        "munder",
        "mover",
        "munderover",
        "mmultiscripts",
        "mtable",
        "mtr",
        "mtd",
        "mspace",
        "maction",
        "semantics",
        "annotation",
        "annotation-xml",
    }
)

# SVG configuration matching is case-sensitive and html5ever emits camelCase
# names for foreign attributes, so spell them exactly as parsed.
_SVG_ATTRIBUTES = frozenset(
    {
        "viewBox",
        "preserveAspectRatio",
        "gradientTransform",
        "gradientUnits",
        "patternUnits",
        "patternContentUnits",
        "patternTransform",
        "clipPathUnits",
        "maskUnits",
        "maskContentUnits",
        "filterUnits",
        "primitiveUnits",
        "markerWidth",
        "markerHeight",
        "refX",
        "refY",
        "textLength",
        "lengthAdjust",
        "spreadMethod",
        "d",
        "r",
        "cx",
        "cy",
        "rx",
        "ry",
        "x",
        "y",
        "x1",
        "x2",
        "y1",
        "y2",
        "width",
        "height",
        "points",
        "transform",
        "fill",
        "fill-opacity",
        "fill-rule",
        "stroke",
        "stroke-width",
        "stroke-opacity",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-dasharray",
        "stroke-dashoffset",
        "stroke-miterlimit",
        "opacity",
        "clip-path",
        "clip-rule",
        "mask",
        "filter",
        "color",
        "stop-color",
        "stop-opacity",
        "offset",
        "fx",
        "fy",
        "version",
        "xmlns",
        "xmlns:xlink",
        "dx",
        "dy",
        "rotate",
        "text-anchor",
        "font-family",
        "font-size",
        "font-weight",
        "href",
        "xlink:href",
        "target",
        "style",
        "class",
        "id",
    }
)

_MEDIA_ATTRIBUTES = frozenset(
    {
        "controls",
        "preload",
        "muted",
        "loop",
        "playsinline",
        "poster",
        "src",
        "srcset",
        "sizes",
        "type",
        "media",
        "width",
        "height",
        "crossorigin",
    }
)

_LIST_ATTRIBUTES = frozenset(
    {"name", "disabled", "multiple", "size", "value", "selected", "label"}
)

_INPUT_ATTRIBUTES = frozenset(
    {
        "type",
        "name",
        "value",
        "checked",
        "disabled",
        "placeholder",
        "readonly",
        "required",
        "size",
        "maxlength",
        "min",
        "max",
        "step",
        "list",
        "accept",
    }
)

_FORM_ACTION_ATTRIBUTES = frozenset(
    {
        "action",
        "method",
        "enctype",
        "target",
        "accept-charset",
        "novalidate",
    }
)
_FORM_REFERENCE_ATTRIBUTES = frozenset(
    {
        "formaction",
        "formmethod",
        "formtarget",
        "form",
        "formenctype",
        "formnovalidate",
    }
)


@dataclass(frozen=True)
class Security:
    """What classes of active or request-making content to neutralize.

    Defaults neutralize all of them, making the result safe to display as
    untrusted content.
    """

    remove_javascript: bool = True
    disable_forms: bool = True
    remove_meta_redirects: bool = True
    sanitize_css: bool = True


def sanitize_css(html: str) -> str:
    """Remove CSS constructs that can make network requests or execute code.

    Meant to run after resource embedding: url() references that were
    resolvable have already become data URIs, so this strips what is left.

    1. Removes @import statements that load external stylesheets
    2. Removes url() references that are not data URIs (preserving
       data: URIs and #fragment references)
    3. Removes IE-specific expression() properties
    4. Removes behavior: properties
    """
    for pattern in (CSS_IMPORT, CSS_URL_NON_DATA, EXPRESSION_CSS, CSS_BEHAVIOR):
        html = pattern.sub("", html)

    def sanitize_style_content(match: re.Match) -> str:
        style_content = match.group(2)
        for pattern in (CSS_IMPORT, CSS_URL_NON_DATA, EXPRESSION_CSS, CSS_BEHAVIOR):
            style_content = pattern.sub("", style_content)
        return f'{match.group(1)}{style_content}"'

    return INLINE_STYLE_ATTR.sub(sanitize_style_content, html)


def _build_cleaner(security: Security, base_url: str | None) -> nh3.Cleaner:
    """Build the pre-embed structural cleaner for *security*."""
    tags = nh3.ALLOWED_TAGS | _CONTENT_TAGS | _SVG_TAGS | _MATHML_TAGS
    if base_url is not None:
        tags = tags | {"base"}
    clean_content_tags = {"noscript"}
    if security.remove_javascript:
        clean_content_tags.add("script")
    else:
        tags = tags | {"script"}

    attributes = _build_attributes(security, base_url)
    url_schemes = set(_URL_SCHEMES)
    generic_prefixes = {"data-", "aria-"}
    if not security.remove_javascript:
        url_schemes.add("javascript")
        generic_prefixes.add("on")
        attributes["script"] = {
            "src",
            "type",
            "async",
            "defer",
            "crossorigin",
            "integrity",
            "charset",
        }

    def attribute_filter(tag: str, attr: str, value: str) -> str | None:
        if security.remove_meta_redirects and tag == "meta":
            lowered = value.strip().lower()
            if attr == "http-equiv" and lowered in {"refresh", "set-cookie"}:
                return None
            if attr == "name" and lowered == "dns-prefetch":
                return None
        if attr in _URL_ATTRIBUTES:
            if not _url_allowed(tag, value, url_schemes):
                return None
        elif attr == "srcset":
            if not all(
                _url_allowed(tag, url, url_schemes) for url in _srcset_urls(value)
            ):
                return None
        elif attr == "style" and security.remove_javascript:
            return EXPRESSION_CSS.sub("", value)
        return value

    return nh3.Cleaner(
        tags=tags,
        # nh3's hidden Rust default is {'script', 'style'}, which panics when
        # style is also allowed in tags — always pass this explicitly.
        clean_content_tags=clean_content_tags,
        attributes=attributes,
        attribute_filter=attribute_filter,
        strip_comments=False,
        link_rel=None,
        url_relative="pass_through",
        generic_attribute_prefixes=generic_prefixes,
        url_schemes=url_schemes,
        set_tag_attribute_values=(
            {"base": {"href": base_url}} if base_url is not None else None
        ),
    )


def _build_attributes(security: Security, base_url: str | None) -> dict[str, set[str]]:
    attributes = deepcopy(nh3.ALLOWED_ATTRIBUTES)
    attributes["*"] = {
        "style",
        "class",
        "id",
        "title",
        "lang",
        "dir",
        "hidden",
        "role",
        "tabindex",
    }
    attributes["img"] |= {"srcset", "sizes", "loading", "decoding"}
    attributes["a"] |= {"target", "name"}
    attributes["link"] = {"rel", "href", "type", "media"}
    attributes["meta"] = {"charset", "name", "content", "http-equiv", "property"}
    if base_url is not None:
        attributes["base"] = {"href"}
    attributes["input"] = set(_INPUT_ATTRIBUTES)
    attributes["button"] = {"type", "name", "value", "disabled"}
    attributes["select"] = attributes["option"] = attributes["optgroup"] = set(
        _LIST_ATTRIBUTES
    )
    attributes["textarea"] = {
        "name",
        "rows",
        "cols",
        "placeholder",
        "disabled",
        "readonly",
        "required",
        "maxlength",
    }
    for tag in ("audio", "video", "source", "track"):
        attributes[tag] = set(_MEDIA_ATTRIBUTES)
    attributes["iframe"] = {
        "src",
        "width",
        "height",
        "allow",
        "allowfullscreen",
        "loading",
        "referrerpolicy",
        "title",
    }
    attributes["object"] = {"data", "width", "height", "type", "name"}
    attributes["embed"] = {"src", "width", "height", "type"}
    attributes["param"] = {"name", "value"}
    for tag in _SVG_TAGS:
        attributes[tag] = set(_SVG_ATTRIBUTES)
    for tag in _MATHML_TAGS:
        attributes[tag] = {"display", "xmlns", "alttext"} if tag == "math" else set()

    if security.disable_forms:
        attributes["form"] = {"name"}
    else:
        attributes["form"] = set(_FORM_ACTION_ATTRIBUTES)
        attributes["button"] |= _FORM_REFERENCE_ATTRIBUTES
        attributes["input"] |= _FORM_REFERENCE_ATTRIBUTES
    return attributes


def _url_allowed(tag: str, value: str, schemes: set[str]) -> bool:
    """Check one URL value against *schemes* and the data: media policy."""
    url = re.sub(r"[\t\n\r]", "", value).strip(_URL_EDGE_CHARS)
    match = _SCHEME.match(url)
    if match is None:
        return True  # relative reference
    scheme = match.group()[:-1].lower()
    if scheme not in schemes:
        return False
    return scheme != "data" or _data_uri_allowed(tag, url)


def _data_uri_allowed(tag: str, url: str) -> bool:
    header = url.partition(":")[2].partition(",")[0]
    media_type = header.partition(";")[0].strip().lower()
    if not media_type or media_type in {
        "text/plain",
        "text/css",
        "application/font-woff",
    }:
        return True
    if media_type.startswith(("image/", "font/", "audio/", "video/")):
        return media_type != "image/svg+xml" or tag not in _SVG_HOST_TAGS
    return False


def _srcset_urls(value: str):
    """Yield the first whitespace token of each comma-separated candidate."""
    for part in value.split(","):
        tokens = part.split()
        if tokens:
            yield tokens[0]


def apply_security(html: str, security: Security, base_url: str | None = None) -> str:
    """Apply *security* to *html* ahead of resource embedding.

    One nh3 structural pass strips active content (scripts, event handlers,
    form submission attributes, meta redirects) and normalizes the markup.
    The document skeleton — doctype, html, head, body — does not survive
    fragment cleaning, so a leading doctype is re-emitted to keep the
    result out of quirks mode.
    """
    if not (
        security.remove_javascript
        or security.disable_forms
        or security.remove_meta_redirects
    ):
        return html

    cleaner = _build_cleaner(security, base_url)
    cleaned = cleaner.clean(html)

    doctype = _DOCTYPE.match(html)
    if doctype:
        cleaned = doctype.group(0) + "\n" + cleaned
    return cleaned
