"""Sanitization policies for untrusted HTML."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass

import nh3

# --------------------------------------------------------------------------
# CSS sanitization (post-embed, whole-document regex passes)
# --------------------------------------------------------------------------

# @import statements whose target is not an embedded data URI, in url()
# or string form; embedded imports are self-contained and survive
CSS_IMPORT = re.compile(
    r'@import\s+(?:url\s*\(\s*(?!["\']?data:)[^)]*\)|["\'](?!data:)[^"\']*["\'])[^;]*;?',
    re.IGNORECASE,
)
# Any url() whose target is not a data URI or fragment reference. Runs after
# embedding, so resolvable references have already become data: URIs and
# everything left is a live external request.
CSS_URL_NON_DATA = re.compile(
    r'url\s*\(\s*["\']?(?!data:|#)([^"\')\s]+)["\']?\s*\)', re.IGNORECASE
)

_DOCTYPE = re.compile(r"^\s*<!DOCTYPE[^>]*>", re.IGNORECASE)

# Characters browsers strip from URLs: tab/newline/carriage-return anywhere.
_URL_CONTROLS = re.compile(r"[\t\n\r]")
# URL-bearing attributes the data: URI policy must see. nh3 scheme-checks
# the URL attributes it knows (href, src, xlink:href, action), but never
# inspects srcset — and a scheme check cannot express "data: URIs only for
# passive media", which is the filter's actual job.
_URL_ATTRIBUTES = frozenset(
    {"href", "xlink:href", "src", "data", "poster", "action", "srcset"}
)
# data: URIs that may reference a document rather than passive media
_SVG_HOST_TAGS = frozenset({"iframe", "embed", "object"})

# Tags nh3 does not allow by default that archived pages need
_CONTENT_TAGS = frozenset(
    {
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
    sanitize_css: bool = True


def sanitize_css(html: str) -> str:
    """Remove CSS constructs that can make network requests.

    Meant to run after resource embedding: @import targets and url()
    references that were resolvable have already become data URIs, so this
    strips what is left — external @import statements, and url() references
    that are not data URIs or #fragment references.
    """
    for pattern in (CSS_IMPORT, CSS_URL_NON_DATA):
        html = pattern.sub("", html)
    return html


def _build_cleaner(security: Security) -> nh3.Cleaner:
    """Build the post-embed cleaner: nh3's defaults plus the tag and
    attribute sets archived pages need.

    What the defaults buy — head furniture cleaned away, anchors stamped
    with rel="noopener noreferrer", href/src scheme-checked — is invisible
    here precisely because it is not configured.
    """
    tags = nh3.ALLOWED_TAGS | _CONTENT_TAGS | _SVG_TAGS | _MATHML_TAGS
    clean_content_tags = {"noscript", "title"}
    if security.remove_javascript:
        clean_content_tags.add("script")
    else:
        tags = tags | {"script"}

    attributes = _build_attributes(security)
    url_schemes = nh3.ALLOWED_URL_SCHEMES | {"data"}
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
        # nh3's scheme filter has no data: URI media-type policy.
        if attr in _URL_ATTRIBUTES:
            url = _URL_CONTROLS.sub("", value).strip()
            if url[:5].lower() == "data:" and not _data_uri_allowed(tag, url):
                return None
        return value

    return nh3.Cleaner(
        tags=tags,
        # nh3's hidden Rust default is {'script', 'style'}, which panics when
        # style is also allowed in tags — always pass this explicitly.
        clean_content_tags=clean_content_tags,
        attributes=attributes,
        attribute_filter=attribute_filter,
        url_schemes=url_schemes,
        generic_attribute_prefixes=generic_prefixes,
    )


def _build_attributes(security: Security) -> dict[str, set[str]]:
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
    attributes["style"] = {"type"}
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
    attributes["math"] = {"display", "xmlns", "alttext"}

    if security.disable_forms:
        attributes["form"] = {"name"}
    else:
        attributes["form"] = set(_FORM_ACTION_ATTRIBUTES)
        attributes["button"] |= _FORM_REFERENCE_ATTRIBUTES
        attributes["input"] |= _FORM_REFERENCE_ATTRIBUTES
    return attributes


def _data_uri_allowed(tag: str, url: str) -> bool:
    header = url.partition(":")[2].partition(",")[0]
    media_type = header.partition(";")[0].strip().lower()
    if tag == "script":
        return media_type in {"text/javascript", "application/javascript"}
    if not media_type or media_type in {
        "text/plain",
        "text/css",
        "application/font-woff",
    }:
        return True
    if media_type.startswith(("image/", "font/", "audio/", "video/")):
        return media_type != "image/svg+xml" or tag not in _SVG_HOST_TAGS
    return False


def clean(html: str, security: Security) -> str:
    """Apply *security* to *html* after resource embedding.

    The doctype does not survive fragment cleaning, so a leading doctype
    is re-emitted to keep the result out of quirks mode. The pass is
    skipped entirely when both remove_javascript and disable_forms are
    off.
    """
    if not (security.remove_javascript or security.disable_forms):
        return html

    cleaned = _build_cleaner(security).clean(html)

    doctype = _DOCTYPE.match(html)
    if doctype:
        cleaned = doctype.group(0) + "\n" + cleaned
    return cleaned
