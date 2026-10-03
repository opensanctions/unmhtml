"""Tests for the security sanitization layer, through the public API."""

import dataclasses

import pytest

from unmhtml import Document, Security, to_standalone_html
from unmhtml.security import sanitize_css


class TestSecurityDefaults:
    def test_all_neutralizations_enabled_by_default(self):
        security = Security()

        assert security.remove_javascript
        assert security.disable_forms
        assert security.sanitize_css

    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            Security().remove_javascript = False


class TestJavascriptRemovedByDefault:
    def test_script_tags_and_content_removed(self):
        html = '<div><script type="text/javascript">alert("xss")</script><p>content</p></div>'
        result = to_standalone_html(Document(html=html))

        assert "<script" not in result
        assert "alert" not in result
        assert "<p>content</p>" in result

    def test_event_handlers_removed(self):
        html = '<div onclick="bad()" onmouseover="bad()">text</div>'
        result = to_standalone_html(Document(html=html))

        assert result == "<div>text</div>"

    def test_javascript_urls_lose_the_attribute(self):
        html = '<a href="javascript:void(0)">link</a><img src="javascript:alert()">'
        result = to_standalone_html(Document(html=html))

        assert result == '<a rel="noopener noreferrer">link</a><img src="">'
        assert "javascript:" not in result

    def test_noscript_content_removed(self):
        html = "<div><noscript><img src='https://evil.com/track.png'></noscript>x</div>"
        result = to_standalone_html(Document(html=html))

        assert "<noscript" not in result
        assert "evil.com" not in result
        assert "<div>x</div>" in result

    def test_complex_document(self):
        html = """<!DOCTYPE html>
<html>
<head>
    <script src="https://evil.com/track.js"></script>
</head>
<body onload="track()">
    <h1>Title</h1>
    <a href="https://good.com">Good link</a>
</body>
</html>"""
        result = to_standalone_html(Document(html=html))

        assert "<script" not in result
        assert "onload" not in result
        assert "<h1>Title</h1>" in result
        assert 'href="https://good.com"' in result
        assert "<!DOCTYPE html>" in result


class TestJavascriptPreservedWhenDisabled:
    def test_script_content_preserved(self):
        html = "<div><script>if (a &lt; b) { alert('hi'); }</script></div>"
        result = to_standalone_html(
            Document(html=html), security=Security(remove_javascript=False)
        )

        assert "<script>if (a &lt; b) { alert('hi'); }</script>" in result

    def test_event_handlers_preserved(self):
        html = '<div onload="track()" data-x="1" aria-label="l">text</div>'
        result = to_standalone_html(
            Document(html=html), security=Security(remove_javascript=False)
        )

        assert 'onload="track()"' in result
        assert 'data-x="1"' in result
        assert 'aria-label="l"' in result

    def test_javascript_urls_preserved(self):
        html = '<a href="javascript:void(0)">link</a>'
        result = to_standalone_html(
            Document(html=html), security=Security(remove_javascript=False)
        )

        assert 'href="javascript:void(0)"' in result


class TestFormsDefusedByDefault:
    def test_submission_attributes_stripped(self):
        html = (
            "<form action='/submit' method='post' accept-charset='utf-8'>"
            "<input type='text' name='q' required>"
            "<button type='submit' formaction='/go'>Go</button>"
            "</form>"
        )
        result = to_standalone_html(Document(html=html))

        assert "<form>" in result
        assert "<input" in result
        assert "<button" in result
        assert "action" not in result
        assert "method" not in result
        assert "accept-charset" not in result
        assert "formaction" not in result
        assert 'name="q"' in result
        assert "Go" in result

    def test_controls_survive(self):
        html = (
            "<label for='q'>Q</label>"
            "<select name='s'><option value='1' selected>One</option></select>"
            "<textarea name='t' rows='3'>text</textarea>"
        )
        result = to_standalone_html(Document(html=html))

        assert "<label" in result
        assert "<select" in result
        assert "<option" in result
        assert "<textarea" in result
        assert "One" in result
        assert "text" in result

    def test_forms_functional_when_enabled(self):
        html = (
            "<form action='/submit' method='post' novalidate>"
            "<input type='text' name='q' formaction='/go'>"
            "<button type='submit' formmethod='get'>Go</button>"
            "</form>"
        )
        result = to_standalone_html(
            Document(html=html), security=Security(disable_forms=False)
        )

        assert '<form action="/submit" method="post" novalidate="">' in result
        assert 'formaction="/go"' in result
        assert 'formmethod="get"' in result


class TestHeadFurnitureRemovedByDefault:
    """title, meta, link and base are not in the cleaner's tag set: nothing
    from the head survives to fetch, redirect, or leak at display time."""

    def test_meta_refresh_removed(self):
        html = '<meta http-equiv="refresh" content="0;url=http://evil.com">'
        result = to_standalone_html(Document(html=html))

        assert result == ""

    def test_meta_set_cookie_removed(self):
        html = '<meta http-equiv="set-cookie" content="session=abc123">'
        result = to_standalone_html(Document(html=html))

        assert result == ""

    def test_dns_prefetch_meta_removed(self):
        html = '<meta name="dns-prefetch" content="evil.com">'
        result = to_standalone_html(Document(html=html))

        assert result == ""

    def test_viewport_and_charset_removed(self):
        html = (
            '<meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width">'
            "<p>content</p>"
        )
        result = to_standalone_html(Document(html=html))

        assert result == "<p>content</p>"

    def test_title_removed_without_text_leak(self):
        html = "<html><head><title>T</title></head><body><p>x</p></body></html>"
        result = to_standalone_html(Document(html=html))

        assert result == "<p>x</p>"


class TestUnsafePassthrough:
    def test_no_cleaning_when_all_flags_disabled(self):
        html = (
            "<body onload=\"x()\"><script>alert('hi')</script>"
            '<form action="/x"><input name="q"></form>'
            '<meta http-equiv="refresh" content="0;url=http://evil.com">'
            "</body>"
        )
        result = to_standalone_html(
            Document(html=html),
            security=Security(
                remove_javascript=False,
                disable_forms=False,
            ),
        )

        assert result == html


class TestSanitizeCss:
    def test_removes_non_data_urls(self):
        """Post-embedding semantics: any url() that is not a data URI is a
        live external request and gets removed."""
        html_with_css = """
        <style>
            body { background: url('http://evil.com/track.png'); }
            .test { list-style-image: url("data:image/png;base64,good"); }
            .icon { background-image: url('images/icon.png'); }
            .font { font-family: url('../fonts/myfont.woff'); }
            .abs { background: url('/static/bg.jpg'); }
            .protocol { background: url('//cdn.evil.com/img.png'); }
        </style>
        """
        cleaned = sanitize_css(html_with_css)
        # Non-data URLs are removed, embedded or not
        assert "http://evil.com/track.png" not in cleaned
        assert "//cdn.evil.com/img.png" not in cleaned
        assert "/static/bg.jpg" not in cleaned
        assert "images/icon.png" not in cleaned
        assert "../fonts/myfont.woff" not in cleaned
        # Data URIs are preserved
        assert 'url("data:image/png;base64,good")' in cleaned

    def test_preserves_fragment_references(self):
        html = "<style>rect { fill: url(#gradient); }</style>"
        cleaned = sanitize_css(html)

        assert "url(#gradient)" in cleaned

    def test_removes_import_statements(self):
        html_with_imports = """
        <style>
            @import url("http://evil.com/malicious.css");
            @import "local-evil.css";
            body { color: red; }
        </style>
        """
        cleaned = sanitize_css(html_with_imports)
        assert "@import" not in cleaned
        assert "http://evil.com/malicious.css" not in cleaned
        assert "local-evil.css" not in cleaned
        assert "color: red" in cleaned

    def test_embedded_data_imports_preserved(self):
        """Embedded imports are self-contained; only external ones go."""
        html_with_imports = """
        <style>
            @import url("data:text/css;base64,e2NvbG9yOnJlZH0=");
            @import "data:text/css;base64,e2NvbG9yOmJsdWV9";
            body { color: red; }
        </style>
        """
        cleaned = sanitize_css(html_with_imports)
        assert cleaned.count("@import") == 2
        assert "color: red" in cleaned

    def test_inline_styles(self):
        html = """<div style="background: url('http://evil.com/x.png'); color: red">text</div>
<div style="background: url('data:image/png;base64,good')">ok</div>"""
        cleaned = sanitize_css(html)

        assert "evil.com" not in cleaned
        assert "color: red" in cleaned
        assert "data:image/png;base64,good" in cleaned
