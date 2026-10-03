"""Embed a document's resources into its HTML as data URIs."""

from __future__ import annotations

import base64
import mimetypes
import re
from html import escape
from html.parser import HTMLParser
from typing import Mapping
from urllib.parse import urljoin

from .document import Resource

_CSS_URL = re.compile(r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)', re.IGNORECASE)
# One srcset candidate: a URL (data: URIs may contain commas) plus an
# optional descriptor like "2x" or "640w".
_SRCSET_ITEM = re.compile(r"\s*(data:[^\s]+|\S+)(?:\s+[\d.]+[wx])?\s*(?:,|$)")


def embed(html: str, resources: Mapping[str, Resource], base_url: str | None) -> str:
    """Return *html* with every reference resolvable in *resources* embedded.

    References are resolved against *base_url* and matched exactly. What
    cannot be resolved is neutralized (empty src, dropped srcset candidates,
    empty CSS url()) so the result never makes network requests. Imported
    stylesheets are embedded as data URIs after their own references have
    been resolved — or neutralized — the same way. Anchor
    hrefs navigate rather than load: they are kept, made absolute — the
    cleaner that runs afterwards strips <base>, so nothing else would
    resolve them. Link tags other than stylesheets are left for the cleaner
    to drop along with the rest of the head.
    """
    parser = _EmbeddingParser(resources, base_url)
    parser.feed(html)
    return parser.get_result()


class _EmbeddingParser(HTMLParser):
    """Single-pass HTML rewriter that embeds resources as data URIs.

    References inside an inlined stylesheet resolve against the stylesheet's
    own URL, as CSS requires; all other references resolve against the
    document's base URL.
    """

    def __init__(self, resources: Mapping[str, Resource], base_url: str | None):
        super().__init__(convert_charrefs=False)
        self._resources = resources
        self._base_url = base_url
        self._output: list[str] = []
        self._style_parts: list[str] | None = None

    def _resolve(self, ref: str, base: str | None = None) -> str:
        return urljoin(base or self._base_url, ref)

    def _lookup(self, ref: str, base: str | None = None) -> Resource | None:
        return self._resources.get(self._resolve(ref, base))

    def _data_uri(self, data: bytes, mime_type: str) -> str:
        payload = base64.b64encode(data).decode("ascii")
        return f"data:{mime_type};base64,{payload}"

    def _embed_src(self, ref: str) -> str:
        """Data URI for a subresource reference, empty when unresolvable."""
        if ref.startswith("data:"):
            return ref
        resource = self._lookup(ref)
        if resource is None:
            return ""
        return self._data_uri(
            resource.data, resource.mime_type or _guess_mime_type(ref)
        )

    def _embed_srcset(self, value: str) -> str:
        """Srcset with resolvable candidates embedded, others dropped."""
        items = []
        for match in _SRCSET_ITEM.finditer(value):
            ref = match.group(1)
            if ref.startswith("data:"):
                items.append(match.group(0).strip(" ,"))
                continue
            resource = self._lookup(ref)
            if resource is not None:
                data_uri = self._data_uri(
                    resource.data, resource.mime_type or _guess_mime_type(ref)
                )
                items.append(match.group(0).strip(" ,").replace(ref, data_uri))
        return ", ".join(items)

    def _navigation_href(self, ref: str) -> str:
        """Anchor target, kept but made absolute: anchors navigate."""
        if ref.startswith("#"):
            return ref
        return self._resolve(ref)

    def _replace_css_urls(
        self, css_text: str, base: str | None = None, seen: frozenset[str] = frozenset()
    ) -> str:
        """Rewrite every resolvable url() to a data URI, others to url("").

        Stylesheet references (@import targets) carry CSS themselves: their
        text is rewritten first, resolving against the stylesheet's own URL,
        with *seen* breaking import cycles.
        """

        def replace(match: re.Match) -> str:
            ref = match.group(1)
            if ref.startswith(("data:", "#")):
                return match.group(0)
            url = self._resolve(ref, base)
            if url in seen:
                return 'url("")'
            resource = self._resources.get(url)
            if resource is None:
                return 'url("")'
            mime_type = resource.mime_type or _guess_mime_type(ref)
            if mime_type == "text/css":
                css_text = resource.data.decode("utf-8", errors="replace")
                css_text = self._replace_css_urls(css_text, base=url, seen=seen | {url})
                return f"url({self._data_uri(css_text.encode(), mime_type)})"
            return f"url({self._data_uri(resource.data, mime_type)})"

        return _CSS_URL.sub(replace, css_text)

    def _process_tag(self, tag: str, attrs: list, self_closing: bool = False):
        tag_lower = tag.lower()
        attr_dict = {k.lower(): v for k, v in attrs}

        if tag_lower == "link":
            rel = (attr_dict.get("rel") or "").lower()
            if "stylesheet" in rel:
                href = attr_dict.get("href") or ""
                if href and not href.startswith("data:"):
                    sheet_url = self._resolve(href)
                    resource = self._resources.get(sheet_url)
                    if resource is not None:
                        css_text = resource.data.decode("utf-8", errors="replace")
                        css_text = self._replace_css_urls(css_text, base=sheet_url)
                        self._output.append(
                            f'<style type="text/css">\n{css_text}\n</style>'
                        )
                        return
                # Unresolvable stylesheet: drop the tag
                return

        new_attrs = []
        for name, value in attrs:
            name_lower = name.lower()
            if value is not None and name_lower in (
                "src",
                "poster",
                "data",
                "background",
                "xlink:href",
            ):
                value = self._embed_src(value)
            elif value is not None and name_lower == "srcset":
                value = self._embed_srcset(value)
            elif value is not None and name_lower == "href":
                if tag_lower in ("a", "area"):
                    value = self._navigation_href(value)
                else:
                    value = self._embed_src(value)
            elif name_lower == "style" and value is not None:
                # HTMLParser already decoded entities, so url() quotes are plain
                value = self._replace_css_urls(value)
            new_attrs.append((name, value))

        if tag_lower == "style" and not self_closing:
            self._style_parts = []

        self._output.append(_build_tag(tag, new_attrs, self_closing))

    def handle_starttag(self, tag, attrs):
        self._process_tag(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag, attrs):
        self._process_tag(tag, attrs, self_closing=True)

    def handle_endtag(self, tag):
        if tag.lower() == "style" and self._style_parts is not None:
            css_text = "".join(self._style_parts)
            self._output.append(self._replace_css_urls(css_text))
            self._style_parts = None
        self._output.append(f"</{tag}>")

    def handle_data(self, data):
        if self._style_parts is not None:
            self._style_parts.append(data)
        else:
            self._output.append(data)

    def handle_entityref(self, name):
        self._output.append(f"&{name};")

    def handle_charref(self, name):
        self._output.append(f"&#{name};")

    def handle_comment(self, data):
        self._output.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self._output.append(f"<!{decl}>")

    def handle_pi(self, data):
        self._output.append(f"<?{data}>")

    def unknown_decl(self, data):
        self._output.append(f"<![{data}]>")

    def get_result(self) -> str:
        return "".join(self._output)


def _build_tag(tag: str, attrs: list, self_closing: bool = False) -> str:
    parts = [f"<{tag}"]
    for name, value in attrs:
        if value is None:
            parts.append(f" {name}")
        else:
            parts.append(f' {name}="{escape(value, quote=True)}"')
    if self_closing:
        parts.append(" /")
    parts.append(">")
    return "".join(parts)


def _guess_mime_type(url: str) -> str:
    """MIME detection with font/js special cases."""
    if url.endswith(".woff"):
        return "font/woff"
    elif url.endswith(".woff2"):
        return "font/woff2"
    elif url.endswith(".ttf"):
        return "font/ttf"
    elif url.endswith(".otf"):
        return "font/otf"
    elif url.endswith(".js"):
        return "text/javascript"

    mime_type, _ = mimetypes.guess_type(url.split("?")[0].split("#")[0])
    if mime_type and not mime_type.startswith("chemical/"):
        return mime_type

    return "application/octet-stream"
