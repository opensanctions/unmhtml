"""Tests for to_standalone_html."""

import base64
import re

import pytest

from unmhtml import Document, Resource, Security, load_mhtml, to_standalone_html

from .conftest import JPEG_BYTES, PNG_BYTES

BASE_URL = "https://example.com/page.html"

UNSAFE = Security(
    remove_javascript=False,
    sanitize_css=False,
    disable_forms=False,
    remove_meta_redirects=False,
)

PNG_DATA_URI = "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode()


def data_uri(mime: str, data: bytes) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


class TestFromMhtml:
    def test_simple_mhtml(self, simple_mhtml):
        result = to_standalone_html(load_mhtml(simple_mhtml))

        assert "<!DOCTYPE html>" in result
        assert "<title>Test Page</title>" in result
        assert "<h1>Hello World</h1>" in result
        assert 'alt="Test Image"' in result

        assert '<link rel="stylesheet"' not in result
        assert '<style type="text/css">' in result
        assert "font-family: Arial, sans-serif" in result
        assert "color: #333" in result

        assert 'src="data:image/png;base64,' in result
        assert 'src="image.png"' not in result

        assert "https://example.com/style.css" not in result
        assert "https://example.com/image.png" not in result

    def test_malformed_mhtml_raises(self, malformed_mhtml):
        with pytest.raises(ValueError, match="no text/html part"):
            load_mhtml(malformed_mhtml)

    def test_document_without_resources(self):
        document = Document(html="<html><body><h1>Hello</h1></body></html>")
        result = to_standalone_html(document)

        assert "<h1>Hello</h1>" in result


class TestDocumentEmbedding:
    def test_relative_references_resolve_against_base_url(
        self, html_with_css, sample_resources
    ):
        document = Document(
            html=html_with_css, resources=sample_resources, base_url=BASE_URL
        )
        result = to_standalone_html(document)

        assert '<style type="text/css">' in result
        assert "font-family: Arial" in result
        assert f'src="{PNG_DATA_URI}"' in result

    def test_absolute_references_without_base_url(self):
        document = Document(
            html='<img src="https://example.com/image.png">',
            resources={"https://example.com/image.png": Resource(PNG_BYTES)},
        )
        result = to_standalone_html(document)

        assert f'src="{PNG_DATA_URI}"' in result

    def test_resource_mime_type_wins_over_url_extension(self):
        document = Document(
            html='<img src="https://example.com/avatar?id=3">',
            resources={
                "https://example.com/avatar?id=3": Resource(PNG_BYTES, "image/webp")
            },
            base_url=BASE_URL,
        )
        result = to_standalone_html(document)

        assert f'src="{data_uri("image/webp", PNG_BYTES)}"' in result

    def test_stylesheet_references_resolve_against_stylesheet_url(self):
        css = 'body { background: url("bg.png"); font: url("body.woff"); }'
        document = Document(
            html='<link rel="stylesheet" href="assets/theme.css">',
            resources={
                "https://example.com/assets/theme.css": Resource(
                    css.encode(), "text/css"
                ),
                "https://example.com/assets/bg.png": Resource(JPEG_BYTES, "image/jpeg"),
                "https://example.com/assets/body.woff": Resource(b"wOFF", "font/woff"),
            },
            base_url=BASE_URL,
        )
        result = to_standalone_html(document)

        assert f"url({data_uri('image/jpeg', JPEG_BYTES)})" in result
        assert f"url({data_uri('font/woff', b'wOFF')})" in result
        assert 'url("bg.png")' not in result

    def test_style_block_references_resolve_against_base_url(
        self, sample_css, sample_resources
    ):
        html = f"<style>{sample_css}</style>"
        result = to_standalone_html(
            Document(html=html, resources=sample_resources, base_url=BASE_URL)
        )

        assert f"url({data_uri('image/jpeg', JPEG_BYTES)})" in result
        assert f"url({PNG_DATA_URI})" in result
        assert "background.jpg" not in result
        assert "pattern.png" not in result

    def test_inline_style_attribute_references_resolve(self, sample_resources):
        html = "<div style=\"background: url('pattern.png')\">Hi</div>"
        result = to_standalone_html(
            Document(html=html, resources=sample_resources, base_url=BASE_URL)
        )

        assert f"url({PNG_DATA_URI})" in result

    def test_mime_type_falls_back_to_url_extension(self):
        document = Document(
            html='<img src="image.png">',
            resources={"https://example.com/image.png": Resource(PNG_BYTES)},
            base_url=BASE_URL,
        )
        result = to_standalone_html(document)

        assert f'src="{PNG_DATA_URI}"' in result

    def test_existing_data_uris_preserved(self):
        html = '<img src="data:image/gif;base64,R0lGOD">'
        result = to_standalone_html(Document(html=html))

        assert 'src="data:image/gif;base64,R0lGOD"' in result


class TestUnresolvedReferences:
    def test_unresolved_src_stripped(self):
        html = '<img src="missing.png" alt="x">'
        result = to_standalone_html(Document(html=html, base_url=BASE_URL))

        assert 'src=""' in result
        assert 'src="missing.png"' not in result

    def test_unresolved_stylesheet_dropped(self):
        html = '<head><link rel="stylesheet" href="missing.css"></head>'
        result = to_standalone_html(Document(html=html, base_url=BASE_URL))

        assert "<link" not in result

    def test_unresolved_favicon_dropped(self):
        html = '<head><link rel="icon" href="favicon.ico"></head>'
        result = to_standalone_html(Document(html=html, base_url=BASE_URL))

        assert "<link" not in result

    def test_favicon_with_resource_embedded(self, sample_resources):
        html = '<head><link rel="icon" href="image.png"></head>'
        result = to_standalone_html(
            Document(html=html, resources=sample_resources, base_url=BASE_URL)
        )

        assert f'href="{PNG_DATA_URI}"' in result

    def test_unresolved_css_url_emptied(self):
        html = "<style>body { background: url('missing.png'); }</style>"
        result = to_standalone_html(Document(html=html, base_url=BASE_URL))

        assert "url('')" in result or 'url("")' in result
        assert "missing.png" not in result

    def test_anchor_href_kept_when_unresolved(self):
        html = '<a href="https://example.org/elsewhere">Link</a>'
        result = to_standalone_html(Document(html=html, base_url=BASE_URL))

        assert 'href="https://example.org/elsewhere"' in result

    def test_css_fragment_references_kept(self):
        html = "<style>rect { fill: url(#gradient); }</style>"
        result = to_standalone_html(Document(html=html, base_url=BASE_URL))

        assert "url(#gradient)" in result

    def test_unresolved_srcset_candidates_dropped(self):
        html = '<img src="fallback.png" srcset="missing.png 1x, other.png 2x">'
        result = to_standalone_html(Document(html=html, base_url=BASE_URL))

        assert 'srcset=""' in result
        assert "missing.png" not in result
        assert "other.png" not in result

    def test_resolvable_srcset_candidates_embedded(self, sample_resources):
        html = '<img src="image.png" srcset="image.png 1x, pattern.png 2x">'
        result = to_standalone_html(
            Document(html=html, resources=sample_resources, base_url=BASE_URL)
        )

        assert f'srcset="{PNG_DATA_URI} 1x, {PNG_DATA_URI} 2x"' in result

    def test_srcset_data_uri_candidates_preserved(self):
        html = '<img src="a.png" srcset="data:image/gif;base64,R0lGOD 1x">'
        result = to_standalone_html(Document(html=html, base_url=BASE_URL))

        assert "data:image/gif;base64,R0lGOD 1x" in result

    def test_unresolved_poster_neutralized(self):
        html = "<video poster='missing.jpg' controls></video>"
        result = to_standalone_html(Document(html=html, base_url=BASE_URL))

        assert 'poster=""' in result
        assert "missing.jpg" not in result

    def test_unresolved_object_data_neutralized(self):
        html = '<object data="plugin.swf"></object>'
        result = to_standalone_html(Document(html=html, base_url=BASE_URL))

        assert 'data=""' in result
        assert "plugin.swf" not in result


class TestEmbeddingOrder:
    """Embedding runs before CSS sanitization, so resolvable references
    survive the sanitizer instead of being stripped as external URLs."""

    def test_absolute_css_url_embedded_not_stripped(self, sample_resources):
        html = "<style>.hero { background: url('https://example.com/pattern.png'); }</style>"
        result = to_standalone_html(Document(html=html, resources=sample_resources))

        assert f"url({PNG_DATA_URI})" in result
        assert "pattern.png" not in result

    def test_absolute_inline_style_url_embedded_not_stripped(self, sample_resources):
        html = "<div style=\"background-image: url('https://example.com/pattern.png')\">Hi</div>"
        result = to_standalone_html(Document(html=html, resources=sample_resources))

        assert f"url({PNG_DATA_URI})" in result

    def test_root_relative_css_url_embedded_not_stripped(self, sample_resources):
        html = "<style>.hero { background: url('/pattern.png'); }</style>"
        result = to_standalone_html(
            Document(html=html, resources=sample_resources, base_url=BASE_URL)
        )

        assert f"url({PNG_DATA_URI})" in result

    def test_post_embed_sanitizer_strips_unembedded_imports(self, sample_resources):
        html = '<head><link rel="stylesheet" href="style.css"></head>'
        css = '@import url("https://example.com/other.css");\nbody { color: red; }'
        resources = dict(sample_resources)
        resources["https://example.com/style.css"] = Resource(css.encode(), "text/css")
        result = to_standalone_html(
            Document(html=html, resources=resources, base_url=BASE_URL)
        )

        assert "@import" not in result
        assert "color: red" in result


class TestSanitizationInvariant:
    """The security invariant: after conversion, no CSS url() survives that
    could make a network request, whatever the inputs contain."""

    NON_DATA_URL = re.compile(r'url\s*\(\s*["\']?(?!data:|#)([^"\')\s]+)')

    def test_adversarial_mime_type_cannot_smuggle_requests(self):
        # mime_type values come from untrusted headers; try to break out of
        # the emitted url(data:{mime};base64,...) to inject a live request.
        evil_mime = "image/png;base64,x) ; background:url(//evil.example/leak"
        document = Document(
            html="<style>.x { background: url('img.png'); }</style>",
            resources={"https://example.com/img.png": Resource(PNG_BYTES, evil_mime)},
            base_url=BASE_URL,
        )
        result = to_standalone_html(document)

        assert not self.NON_DATA_URL.findall(result)
        assert "evil.example" not in result

    def test_hostile_css_cannot_leave_requests_behind(self):
        hostile = """<html><head><style>
@import url(//evil.example/import);
.a { background: url(//evil.example/a); }
</style></head><body>
<div style="background:url(//evil.example/inline)">t</div>
<img src="//evil.example/pixel" srcset="//evil.example/x 1x">
<video poster="//evil.example/poster"></video>
</body></html>"""
        result = to_standalone_html(
            Document(html=hostile, base_url="https://good.com/")
        )

        assert not self.NON_DATA_URL.findall(result)
        assert "//evil.example" not in result


class TestSecurityFlags:
    def test_javascript_removed_by_default(self):
        html = (
            "<html><head><script src='app.js'></script></head>"
            "<body onload='alert()'><h1>Hi</h1>"
            "<a href='javascript:alert()'>x</a></body></html>"
        )
        result = to_standalone_html(Document(html=html))

        assert "<script" not in result
        assert "onload" not in result
        assert "javascript:" not in result
        assert "<a>x</a>" in result
        assert "<h1>Hi</h1>" in result

    def test_javascript_preserved_when_disabled(self):
        html = "<html><body><script>alert('hi')</script><h1>Hi</h1></body></html>"
        result = to_standalone_html(Document(html=html), security=UNSAFE)

        assert "<script>alert('hi')</script>" in result

    def test_script_src_embedded_when_javascript_kept(self):
        js = b"alert('hi')"
        document = Document(
            html="<script src='app.js'></script>",
            resources={"https://example.com/app.js": Resource(js, "text/javascript")},
            base_url=BASE_URL,
        )
        result = to_standalone_html(document, security=UNSAFE)

        assert f'src="{data_uri("text/javascript", js)}"' in result

    def test_forms_defused_by_default(self):
        html = "<html><body><h1>Hi</h1><form action='/x'><input name='q'></form></body></html>"
        result = to_standalone_html(Document(html=html))

        assert "<form>" in result
        assert '<input name="q">' in result
        assert "action" not in result
        assert "<h1>Hi</h1>" in result

    def test_forms_functional_when_disabled(self):
        html = "<html><body><form action='/x'><input name='q'></form></body></html>"
        result = to_standalone_html(Document(html=html), security=UNSAFE)

        assert '<form action="/x"><input name="q"></form>' in result

    def test_meta_redirects_removed_by_default(self):
        html = (
            "<html><head>"
            '<meta http-equiv="refresh" content="0;url=http://evil.com">'
            "</head><body>Hi</body></html>"
        )
        result = to_standalone_html(Document(html=html))

        assert "http-equiv" not in result
        assert '<meta content="0;url=http://evil.com">' in result
        assert "Hi" in result

    def test_meta_redirects_preserved_when_disabled(self):
        html = (
            "<html><head>"
            '<meta http-equiv="refresh" content="5">'
            "</head><body>Hi</body></html>"
        )
        result = to_standalone_html(Document(html=html), security=UNSAFE)

        assert 'http-equiv="refresh"' in result

    def test_unsafe_conversion_preserves_content(self, sample_resources):
        html = (
            "<html><head><link rel='stylesheet' href='style.css'></head>"
            "<body onload='x()'><h1>Hi</h1>"
            "<img src='image.png'><form><input name='q'></form>"
            "<style>.x { background: url('missing.png'); }</style>"
            "</body></html>"
        )
        document = Document(html=html, resources=sample_resources, base_url=BASE_URL)
        result = to_standalone_html(document, security=UNSAFE)

        assert "onload" in result
        assert "<form>" in result
        assert f'src="{PNG_DATA_URI}"' in result
        assert "font-family: Arial" in result
        # Even unsafe, the result is standalone: unresolvable refs neutralized
        assert "missing.png" not in result


class TestStructurePreservation:
    def test_comments_entities_and_doctype_preserved(self):
        html = (
            "<!DOCTYPE html>\n<!-- a comment -->\n<p>5 &lt; 6 &amp; 7 &gt; 4 &#65; &copy;</p>"
        )
        result = to_standalone_html(Document(html=html))

        assert "<!DOCTYPE html>" in result
        assert "<!-- a comment -->" in result
        assert "5 &lt; 6 &amp; 7 &gt; 4 A ©" in result

    def test_malformed_html_does_not_crash(self):
        result = to_standalone_html(Document(html="<div><p>unclosed"))

        assert "<div><p>unclosed</p></div>" in result

    def test_multiple_stylesheets_inlined_in_order(self, sample_resources):
        resources = dict(sample_resources)
        resources["https://example.com/second.css"] = Resource(
            b".second { color: blue; }", "text/css"
        )
        html = (
            "<head><link rel='stylesheet' href='style.css'>"
            "<link rel='stylesheet' href='second.css'></head>"
        )
        result = to_standalone_html(
            Document(html=html, resources=resources, base_url=BASE_URL)
        )

        assert result.index("font-family: Arial") < result.index("color: blue")
