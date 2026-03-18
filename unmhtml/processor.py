import re
import base64
import html
import mimetypes
from html.parser import HTMLParser
from typing import Dict


class _ResourceEmbeddingParser(HTMLParser):
    """Internal HTMLParser subclass that embeds resources in a single pass."""

    def __init__(self, processor: "HTMLProcessor"):
        super().__init__(convert_charrefs=False)
        self.processor = processor
        self.output: list[str] = []
        self._in_style = False
        self._style_parts: list[str] = []

    def _build_tag(self, tag: str, attrs: list, self_closing: bool = False) -> str:
        parts = [f"<{tag}"]
        for name, value in attrs:
            if value is None:
                parts.append(f" {name}")
            else:
                parts.append(f' {name}="{html.escape(value, quote=True)}"')
        if self_closing:
            parts.append(" /")
        parts.append(">")
        return "".join(parts)

    def _process_tag(self, tag: str, attrs: list, self_closing: bool = False):
        tag_lower = tag.lower()
        attr_dict = {k.lower(): v for k, v in attrs}

        # Handle <link rel="stylesheet"> → <style>
        if tag_lower == "link":
            rel = (attr_dict.get("rel") or "").lower()
            if "stylesheet" in rel:
                href = attr_dict.get("href", "")
                if href:
                    css_data = self.processor._find_resource_by_url(href)
                    if css_data:
                        css_text = css_data.decode("utf-8", errors="ignore")
                        css_text = self.processor._replace_css_urls(css_text)
                        self.output.append(
                            f'<style type="text/css">\n{css_text}\n</style>'
                        )
                        return
                # CSS not found, drop the tag to prevent network requests
                return

            # Handle favicon/icon links — remove if resource missing
            if rel in ("icon", "apple-touch-icon"):
                href = attr_dict.get("href", "")
                if href and not self.processor._find_resource_by_url(href):
                    return  # drop the tag
                # Resource exists, fall through to normal processing

        # Process attributes
        new_attrs = []
        for name, value in attrs:
            name_lower = name.lower()
            if value is None:
                new_attrs.append((name, value))
                continue

            if name_lower == "src":
                if not value.startswith("data:"):
                    data = self.processor._find_resource_by_url(value)
                    if data:
                        value = self.processor._create_data_uri(data, value)
                    else:
                        # Strip unresolvable src to prevent network requests
                        value = ""
            elif name_lower == "href":
                if not value.startswith("data:"):
                    data = self.processor._find_resource_by_url(value)
                    if data:
                        value = self.processor._create_data_uri(data, value)
            elif name_lower == "style":
                # HTMLParser already decoded entities, so url() quotes are plain
                value = self.processor._replace_css_urls(value)

            new_attrs.append((name, value))

        if tag_lower == "style" and not self_closing:
            self._in_style = True
            self._style_parts = []

        self.output.append(self._build_tag(tag, new_attrs, self_closing))

    def handle_starttag(self, tag, attrs):
        self._process_tag(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag, attrs):
        self._process_tag(tag, attrs, self_closing=True)

    def handle_endtag(self, tag):
        if tag.lower() == "style" and self._in_style:
            css_text = "".join(self._style_parts)
            css_text = self.processor._replace_css_urls(css_text)
            self.output.append(css_text)
            self._in_style = False
            self._style_parts = []
        self.output.append(f"</{tag}>")

    def handle_data(self, data):
        if self._in_style:
            self._style_parts.append(data)
        else:
            self.output.append(data)

    def handle_entityref(self, name):
        self.output.append(f"&{name};")

    def handle_charref(self, name):
        self.output.append(f"&#{name};")

    def handle_comment(self, data):
        self.output.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.output.append(f"<!{decl}>")

    def handle_pi(self, data):
        self.output.append(f"<?{data}>")

    def unknown_decl(self, data):
        self.output.append(f"<![{data}]>")

    def get_result(self) -> str:
        return "".join(self.output)


class HTMLProcessor:
    """
    Processor for embedding CSS and converting resources to data URIs in HTML.

    Uses stdlib HTMLParser to process HTML in a single pass, which naturally
    handles HTML-encoded entities in attribute values (e.g. &quot; in style attrs).

    Args:
        html_content: The HTML content to process
        resources: Dictionary mapping resource URLs to their binary content
    """

    def __init__(self, html_content: str, resources: Dict[str, bytes]):
        self.html_content = html_content
        self.resources = resources

    def process(self) -> str:
        """Embed CSS, convert resources to data URIs, remove missing favicons. One pass."""
        parser = _ResourceEmbeddingParser(self)
        parser.feed(self.html_content)
        return parser.get_result()

    def _find_resource_by_url(self, url: str) -> bytes:
        """Flexible URL matching: exact, basename, query-stripped."""
        if url in self.resources:
            return self.resources[url]

        for resource_url, content in self.resources.items():
            if resource_url.endswith(url) or url.endswith(resource_url.split("/")[-1]):
                return content

        url_without_query = url.split("?")[0]
        if url_without_query in self.resources:
            return self.resources[url_without_query]

        return b""

    def _create_data_uri(self, data: bytes, url: str) -> str:
        """Create a base64-encoded data URI."""
        mime_type = self._get_mime_type(url)
        b64_data = base64.b64encode(data).decode("ascii")
        return f"data:{mime_type};base64,{b64_data}"

    def _get_mime_type(self, url: str) -> str:
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

        mime_type, _ = mimetypes.guess_type(url)
        if mime_type and not mime_type.startswith("chemical/"):
            return mime_type

        return "application/octet-stream"

    def _replace_css_urls(self, css_text: str) -> str:
        """Replace url() references in CSS text with data URIs."""
        css_url_pattern = r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)'

        def _replace(match):
            url = match.group(1)
            if url.startswith("data:"):
                return match.group(0)
            data = self._find_resource_by_url(url)
            if data:
                data_uri = self._create_data_uri(data, url)
                return f'url("{data_uri}")'
            # Strip unresolvable url() to prevent network requests
            return 'url("")'

        return re.sub(css_url_pattern, _replace, css_text, flags=re.IGNORECASE)
