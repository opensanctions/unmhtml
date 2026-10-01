"""Tests for the security sanitization functions."""

import dataclasses

import pytest

from unmhtml.security import (
    Security,
    remove_forms,
    remove_javascript_content,
    remove_meta_redirects,
    sanitize_css,
)


class TestSecurityDefaults:
    def test_all_removals_enabled_by_default(self):
        security = Security()

        assert security.remove_javascript
        assert security.sanitize_css
        assert security.remove_forms
        assert security.remove_meta_redirects

    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            Security().remove_javascript = False


class TestRemoveJavascriptContent:
    def test_script_removal(self):
        html = '<html><body><script type="text/javascript">alert("xss")</script><p>content</p></body></html>'
        cleaned = remove_javascript_content(html)

        assert "<script" not in cleaned
        assert "alert" not in cleaned
        assert "<p>content</p>" in cleaned

    def test_event_handlers(self):
        html = '<div onclick="bad()" onmouseover="bad()">text</div>'
        cleaned = remove_javascript_content(html)

        assert "onclick" not in cleaned
        assert "onmouseover" not in cleaned
        assert "<div>text</div>" in cleaned

    def test_javascript_urls(self):
        html = '<a href="javascript:void(0)">link</a><img src="javascript:alert()">'
        cleaned = remove_javascript_content(html)

        assert 'href="#"' in cleaned
        assert 'src="#"' in cleaned
        assert "javascript:" not in cleaned

    def test_complex_document(self):
        html = """<!DOCTYPE html>
<html>
<head>
    <script src="https://evil.com/track.js"></script>
    <noscript><img src="https://evil.com/track.png"></noscript>
</head>
<body onload="track()">
    <h1>Title</h1>
    <a href="https://good.com">Good link</a>
    <img src="image.png" alt="test">
    <a href="page.html">Relative link</a>
</body>
</html>"""
        cleaned = remove_javascript_content(html)

        assert "<script" not in cleaned
        assert "<noscript" not in cleaned
        assert "onload" not in cleaned
        assert 'src="image.png"' in cleaned
        assert 'href="page.html"' in cleaned

    @pytest.mark.parametrize(
        "input_html,should_contain",
        [
            ('<script>alert("xss")</script><p>content</p>', "<p>content</p>"),
            ('<div onclick="bad()">text</div>', "<div>text</div>"),
            ('<a href="javascript:void(0)">link</a>', '<a href="#">link</a>'),
            ('<img src="image.png" onload="track()" alt="test">', 'src="image.png"'),
        ],
    )
    def test_integration(self, input_html, should_contain):
        result = remove_javascript_content(input_html)
        assert should_contain in result

        # Should not contain dangerous content
        assert "script>" not in result
        assert "javascript:" not in result
        assert "onclick" not in result


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

    def test_removes_expression_properties(self):
        html_with_expressions = """
        <style>
            .test { width: expression(document.body.scrollWidth > 600 ? "600px" : "auto"); }
            body { color: blue; }
        </style>
        """
        cleaned = sanitize_css(html_with_expressions)
        assert "expression(" not in cleaned
        assert "document.body" not in cleaned
        assert "color: blue" in cleaned

    def test_removes_behavior_properties(self):
        html_with_behavior = """
        <style>
            .test { behavior: url(evil.htc); }
            body { color: green; }
        </style>
        """
        cleaned = sanitize_css(html_with_behavior)
        assert "behavior" not in cleaned
        assert "color: green" in cleaned

    def test_inline_styles(self):
        html = """<div style="background: url('http://evil.com/x.png'); color: red">text</div>
<div style="background: url('data:image/png;base64,good')">ok</div>"""
        cleaned = sanitize_css(html)

        assert "evil.com" not in cleaned
        assert "color: red" in cleaned
        assert "data:image/png;base64,good" in cleaned


class TestRemoveForms:
    def test_complete_removal(self):
        html = """<html>
<body>
    <h1>Page Title</h1>
    <form action="/submit" method="post">
        <input type="text" name="username">
        <input type="password" name="password">
        <textarea name="comments">Default</textarea>
        <select name="choice"><option value="1">One</option></select>
        <button type="submit">Submit</button>
        <label>Username</label>
    </form>
    <p>Footer content</p>
</body>
</html>"""
        cleaned = remove_forms(html)

        assert "<form" not in cleaned
        assert "<input" not in cleaned
        assert "<textarea" not in cleaned
        assert "<select" not in cleaned
        assert "<button" not in cleaned
        assert "<label" not in cleaned
        assert "<h1>Page Title</h1>" in cleaned
        assert "<p>Footer content</p>" in cleaned

    def test_fieldset_and_datalist(self):
        html = """<div>
    <fieldset><legend>Group</legend><input name="a"></fieldset>
    <datalist id="list"><option value="x"></datalist>
    <p>Content</p>
</div>"""
        cleaned = remove_forms(html)

        assert "<fieldset" not in cleaned
        assert "<legend" not in cleaned
        assert "<datalist" not in cleaned
        assert "<p>Content</p>" in cleaned


class TestRemoveMetaRedirects:
    def test_refresh(self):
        html = '<html><head><meta http-equiv="refresh" content="0;url=http://evil.com"></head><body>content</body></html>'
        cleaned = remove_meta_redirects(html)

        assert "<meta" not in cleaned
        assert "evil.com" not in cleaned
        assert "content" in cleaned

    def test_set_cookie(self):
        html = '<html><head><meta http-equiv="set-cookie" content="session=abc123"></head><body>content</body></html>'
        cleaned = remove_meta_redirects(html)

        assert "<meta" not in cleaned
        assert "session" not in cleaned

    def test_dns_prefetch(self):
        html = """<html>
<head>
    <meta name="dns-prefetch" content="evil.com">
    <meta name="viewport" content="width=device-width">
</head>
<body>content</body>
</html>"""
        cleaned = remove_meta_redirects(html)

        assert 'name="dns-prefetch"' not in cleaned
        assert "evil.com" not in cleaned
        assert 'name="viewport"' in cleaned

    def test_regular_meta_tags_preserved(self):
        html = '<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head><body>content</body></html>'
        cleaned = remove_meta_redirects(html)

        assert '<meta charset="utf-8">' in cleaned
        assert 'name="viewport"' in cleaned
