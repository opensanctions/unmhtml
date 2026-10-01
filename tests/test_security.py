import pytest

from unmhtml.security import (
    is_javascript_file,
    remove_forms,
    remove_javascript_content,
    remove_meta_redirects,
    sanitize_css,
)


class TestSecurity:
    def test_remove_javascript_content_script_removal(self):
        """Test script tag removal"""
        html_with_script = (
            '<html><body><script>alert("test")</script><p>Hello</p></body></html>'
        )
        cleaned = remove_javascript_content(html_with_script)
        assert "<script>" not in cleaned
        assert 'alert("test")' not in cleaned
        assert "<p>Hello</p>" in cleaned

    def test_remove_javascript_content_event_handlers(self):
        """Test event handler removal"""
        html_with_events = (
            '<div onclick="alert(1)" onload="bad()" class="test">Hello</div>'
        )
        cleaned = remove_javascript_content(html_with_events)
        assert "onclick=" not in cleaned
        assert "onload=" not in cleaned
        assert 'class="test"' in cleaned
        assert "Hello" in cleaned

    def test_remove_javascript_content_javascript_urls(self):
        """Test javascript: URL removal"""
        html_with_js_url = '<a href="javascript:alert(1)">Link</a>'
        cleaned = remove_javascript_content(html_with_js_url)
        assert "javascript:" not in cleaned
        assert 'href="#"' in cleaned
        assert "Link" in cleaned

    def test_remove_javascript_content_complex(self):
        """Test complex HTML cleaning"""
        complex_html = """
        <html>
        <head>
            <script type="text/javascript">
                function malicious() { alert("bad"); }
            </script>
        </head>
        <body onclick="malicious()">
            <p>Good content</p>
            <a href="javascript:void(0)">Bad link</a>
            <img src="image.png" onload="track()" alt="test">
        </body>
        </html>
        """
        cleaned = remove_javascript_content(complex_html)
        assert "<script>" not in cleaned
        assert "onclick=" not in cleaned
        assert "onload=" not in cleaned
        assert "javascript:" not in cleaned
        assert "Good content" in cleaned
        assert 'src="image.png"' in cleaned
        assert 'alt="test"' in cleaned

    def test_remove_javascript_content_preserves_good_content(self):
        """Test that good content is preserved"""
        good_html = """
        <html>
        <head>
            <title>Test Page</title>
            <link rel="stylesheet" href="style.css">
        </head>
        <body>
            <h1>Title</h1>
            <p class="content">This is good content</p>
            <img src="image.png" alt="test">
            <a href="page.html">Good link</a>
        </body>
        </html>
        """
        cleaned = remove_javascript_content(good_html)
        assert "<title>Test Page</title>" in cleaned
        assert '<link rel="stylesheet"' in cleaned
        assert "<h1>Title</h1>" in cleaned
        assert 'class="content"' in cleaned
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
    def test_remove_javascript_content_integration(self, input_html, should_contain):
        """Test HTML cleaning integration with various inputs"""
        result = remove_javascript_content(input_html)
        assert should_contain in result

        # Should not contain dangerous content
        assert "script>" not in result
        assert "javascript:" not in result
        assert "on" not in result or "onclick" not in result

    # Tests for JavaScript file detection
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("app.js", True),
            ("script.mjs", True),
            ("component.jsx", True),
            ("module.ts", True),
            ("component.tsx", True),
            ("APP.JS", True),  # Case insensitive
            ("style.css", False),
            ("image.png", False),
            ("page.html", False),
            ("data.json", False),
            ("", False),
        ],
    )
    def test_is_javascript_file_by_extension(self, url, expected):
        """Test JavaScript file detection by extension"""
        assert is_javascript_file(url) == expected

    @pytest.mark.parametrize(
        "url,content_type,expected",
        [
            ("unknown", "text/javascript", True),
            ("unknown", "application/javascript", True),
            ("unknown", "application/x-javascript", True),
            ("unknown", "text/ecmascript", True),
            ("unknown", "application/ecmascript", True),
            ("unknown", "TEXT/JAVASCRIPT", True),  # Case insensitive
            ("unknown", "text/css", False),
            ("unknown", "image/png", False),
            ("unknown", "text/html", False),
            ("unknown", "", False),
            ("unknown", None, False),
        ],
    )
    def test_is_javascript_file_by_content_type(self, url, content_type, expected):
        """Test JavaScript file detection by content type"""
        assert is_javascript_file(url, content_type) == expected

    def test_is_javascript_file_combined(self):
        """Test JavaScript file detection with both extension and content type"""
        # Extension overrides content type
        assert is_javascript_file("app.js", "text/css")
        assert is_javascript_file("style.css", "text/javascript")

        # Both indicate JavaScript
        assert is_javascript_file("app.js", "text/javascript")

        # Neither indicates JavaScript
        assert not is_javascript_file("style.css", "text/css")

    # Tests for CSS sanitization
    def test_sanitize_css_removes_url_properties(self):
        """Test CSS url() property removal - external URLs removed, data URIs and relative URLs preserved"""
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
        # External URLs should be removed
        assert "http://evil.com/track.png" not in cleaned
        assert "//cdn.evil.com/img.png" not in cleaned
        assert "/static/bg.jpg" not in cleaned
        # Data URIs should be preserved
        assert "data:image/png;base64,good" in cleaned
        assert 'url("data:image/png;base64,good")' in cleaned
        # Relative URLs should be preserved (will be converted to data URIs later)
        assert "images/icon.png" in cleaned
        assert "../fonts/myfont.woff" in cleaned

    def test_sanitize_css_removes_import_statements(self):
        """Test CSS @import statement removal"""
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

    def test_sanitize_css_removes_expression_properties(self):
        """Test CSS expression() property removal"""
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

    def test_sanitize_css_removes_behavior_properties(self):
        """Test CSS behavior: property removal"""
        html_with_behavior = """
        <style>
            .evil { behavior: url('evil.htc'); }
            .good { color: green; }
        </style>
        """
        cleaned = sanitize_css(html_with_behavior)
        assert "behavior:" not in cleaned
        assert "evil.htc" not in cleaned
        assert "color: green" in cleaned

    def test_sanitize_css_inline_styles(self):
        """Test CSS sanitization of inline style attributes"""
        html_with_inline = """
        <div style="background: url('http://evil.com/track.png'); color: red;">
            <p style="list-style: url(data:image/png;base64,good); margin: 10px;">Good content</p>
            <span style="background-image: url('local/image.png'); padding: 5px;">Relative URL</span>
        </div>
        """
        cleaned = sanitize_css(html_with_inline)
        # External URLs should be removed from inline styles
        assert "http://evil.com/track.png" not in cleaned
        # Safe properties should remain
        assert "color: red" in cleaned
        assert "margin: 10px" in cleaned
        assert "padding: 5px" in cleaned
        # Data URIs should be preserved in inline styles
        assert "data:image/png;base64,good" in cleaned
        # Relative URLs should be preserved in inline styles
        assert "local/image.png" in cleaned

    # Tests for form removal
    def test_remove_forms_complete_removal(self):
        """Test complete form removal"""
        html_with_forms = """
        <div>
            <h1>Title</h1>
            <form action="/submit" method="post">
                <label for="name">Name:</label>
                <input type="text" id="name" name="name">
                <textarea name="message" placeholder="Message"></textarea>
                <select name="category">
                    <option value="general">General</option>
                    <option value="support">Support</option>
                </select>
                <button type="submit">Submit</button>
                <input type="hidden" name="csrf" value="token">
            </form>
            <p>Good content</p>
        </div>
        """
        cleaned = remove_forms(html_with_forms)
        assert "<form" not in cleaned
        assert "<input" not in cleaned
        assert "<textarea" not in cleaned
        assert "<select" not in cleaned
        assert "<option" not in cleaned
        assert "<button" not in cleaned
        assert "<label" not in cleaned
        assert "<h1>Title</h1>" in cleaned
        assert "<p>Good content</p>" in cleaned

    def test_remove_forms_fieldset_and_datalist(self):
        """Test removal of fieldset and datalist elements"""
        html_with_fieldset = """
        <div>
            <fieldset>
                <legend>Personal Information</legend>
                <input type="text" name="firstname">
            </fieldset>
            <datalist id="browsers">
                <option value="Chrome">
                <option value="Firefox">
            </datalist>
            <p>Safe content</p>
        </div>
        """
        cleaned = remove_forms(html_with_fieldset)
        assert "<fieldset" not in cleaned
        assert "<legend" not in cleaned
        assert "<datalist" not in cleaned
        assert "<option" not in cleaned
        assert "<input" not in cleaned
        assert "<p>Safe content</p>" in cleaned

    # Tests for meta redirect removal
    def test_remove_meta_redirects_refresh(self):
        """Test meta refresh tag removal"""
        html_with_refresh = """
        <html>
        <head>
            <meta http-equiv="refresh" content="0;url=http://evil.com">
            <meta name="description" content="Good meta tag">
            <title>Test</title>
        </head>
        <body>Content</body>
        </html>
        """
        cleaned = remove_meta_redirects(html_with_refresh)
        assert 'http-equiv="refresh"' not in cleaned
        assert "http://evil.com" not in cleaned
        assert 'name="description"' in cleaned
        assert "<title>Test</title>" in cleaned

    def test_remove_meta_redirects_set_cookie(self):
        """Test meta set-cookie tag removal"""
        html_with_cookie = """
        <html>
        <head>
            <meta http-equiv="set-cookie" content="session=abc123">
            <meta charset="utf-8">
            <title>Test</title>
        </head>
        </html>
        """
        cleaned = remove_meta_redirects(html_with_cookie)
        assert 'http-equiv="set-cookie"' not in cleaned
        assert "session=abc123" not in cleaned
        assert 'charset="utf-8"' in cleaned
        assert "<title>Test</title>" in cleaned

    def test_remove_meta_redirects_dns_prefetch(self):
        """Test meta dns-prefetch tag removal"""
        html_with_dns = """
        <html>
        <head>
            <meta name="dns-prefetch" content="evil.com">
            <meta name="viewport" content="width=device-width">
            <title>Test</title>
        </head>
        </html>
        """
        cleaned = remove_meta_redirects(html_with_dns)
        assert 'name="dns-prefetch"' not in cleaned
        assert "evil.com" not in cleaned
        assert 'name="viewport"' in cleaned
        assert "<title>Test</title>" in cleaned
