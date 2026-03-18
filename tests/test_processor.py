import pytest
from unmhtml.processor import HTMLProcessor


class TestHTMLProcessor:
    def test_embed_css(self, html_with_css, sample_resources):
        """Test CSS embedding functionality"""
        processor = HTMLProcessor(html_with_css, sample_resources)
        result = processor.process()

        # Check that link tags are replaced with style tags
        assert '<link rel="stylesheet"' not in result
        assert '<style type="text/css">' in result

        # Check that CSS content is embedded
        assert "font-family: Arial" in result
        assert "color: red" in result

    def test_convert_to_data_uris(self, sample_resources):
        """Test resource conversion to data URIs"""
        html = '<img src="image.png" alt="test"><img src="https://example.com/logo.png" alt="logo">'
        processor = HTMLProcessor(html, sample_resources)
        result = processor.process()

        # Check that src attributes are converted to data URIs
        assert 'src="data:image/png;base64,' in result
        assert 'src="image.png"' not in result
        assert 'src="https://example.com/logo.png"' not in result

    def test_css_url_replacement(self, sample_css, sample_resources):
        """Test CSS url() replacement"""
        html = f"<style>{sample_css}</style>"
        processor = HTMLProcessor(html, sample_resources)
        result = processor.process()

        # Check that CSS urls are converted to data URIs
        assert 'url("data:image/jpeg;base64,' in result  # background.jpg
        assert 'url("data:image/png;base64,' in result  # pattern.png
        assert "url('background.jpg')" not in result
        assert 'url("pattern.png")' not in result

    def test_preserve_existing_data_uris(self, sample_resources):
        """Test that existing data URIs are preserved"""
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        html = f'<img src="{data_uri}" alt="test">'
        processor = HTMLProcessor(html, sample_resources)
        result = processor.process()

        # Should not modify existing data URIs
        assert data_uri in result

    def test_find_resource_by_url(self, sample_resources):
        """Test resource finding with various URL formats"""
        processor = HTMLProcessor("", sample_resources)

        # Test exact match
        result = processor._find_resource_by_url("image.png")
        assert len(result) > 0
        assert result.startswith(b"\x89PNG")

        # Test URL match
        result = processor._find_resource_by_url("https://example.com/logo.png")
        assert len(result) > 0

        # Test not found
        result = processor._find_resource_by_url("nonexistent.png")
        assert result == b""

    @pytest.mark.parametrize(
        "filename,expected_mime",
        [
            ("image.png", "image/png"),
            ("style.css", "text/css"),
            ("script.js", "text/javascript"),
            ("page.html", "text/html"),
            ("font.woff", "font/woff"),
            ("unknown.xyz", "application/octet-stream"),
        ],
    )
    def test_get_mime_type(self, filename, expected_mime):
        """Test MIME type detection"""
        processor = HTMLProcessor("", {})
        result = processor._get_mime_type(filename)
        assert result == expected_mime

    def test_complex_html_processing(self, sample_resources):
        """Test processing complex HTML with multiple resources"""
        complex_html = """
        <html>
        <head>
            <link rel="stylesheet" href="style.css">
            <style>
                body { background: url('background.jpg'); }
            </style>
        </head>
        <body>
            <img src="image.png" alt="test">
            <img src="https://example.com/logo.png" alt="logo">
        </body>
        </html>
        """

        processor = HTMLProcessor(complex_html, sample_resources)
        result = processor.process()

        assert '<style type="text/css">' in result
        assert "font-family: Arial" in result
        assert 'src="data:image/png;base64,' in result
        assert 'url("data:image/jpeg;base64,' in result
        assert 'src="image.png"' not in result
        assert "background.jpg" not in result

    def test_malformed_html_handling(self, sample_resources):
        """Test handling of malformed HTML"""
        malformed_html = (
            '<img src="image.png" alt="test><link rel="stylesheet" href="style.css"'
        )
        processor = HTMLProcessor(malformed_html, sample_resources)

        # Should not crash and should attempt to process
        result = processor.process()
        assert isinstance(result, str)

    def test_multiple_css_links(self, sample_resources):
        """Test processing multiple CSS links"""
        html = """
        <html>
        <head>
            <link rel="stylesheet" href="style.css">
            <link rel="stylesheet" href="https://example.com/external.css">
            <link rel="icon" href="favicon.ico">
        </head>
        <body>Test</body>
        </html>
        """

        processor = HTMLProcessor(html, sample_resources)
        result = processor.process()

        # Should convert stylesheet links but icon link should be removed (missing resource)
        assert '<link rel="stylesheet"' not in result
        assert '<style type="text/css">' in result
        assert "font-family: Arial" in result
        assert "color: red" in result

    def test_css_with_media_queries(self, sample_resources):
        """Test CSS with media queries"""
        html = """
        <html>
        <head>
            <link rel="stylesheet" href="style.css" media="screen">
            <link rel="stylesheet" href="https://example.com/external.css" media="print">
        </head>
        <body>Test</body>
        </html>
        """

        processor = HTMLProcessor(html, sample_resources)
        result = processor.process()

        # Should still convert to style tags
        assert '<style type="text/css">' in result
        assert "font-family: Arial" in result
        assert "color: red" in result

    def test_resource_url_variations(self, sample_resources):
        """Test handling of various resource URL formats"""
        html = """
        <img src="image.png">
        <img src="./image.png">
        <img src="/image.png">
        <img src="image.png?v=1">
        """

        processor = HTMLProcessor(html, sample_resources)
        result = processor.process()

        # At least one should be converted (exact match)
        assert "data:image/png;base64," in result

    def test_empty_resources(self):
        """Test processing with empty resources"""
        html = '<img src="image.png" alt="test">'
        processor = HTMLProcessor(html, {})
        result = processor.process()

        # Should not crash, should strip unresolvable src to prevent network requests
        assert 'src=""' in result

    def test_no_resources_to_process(self):
        """Test HTML with no resources to process"""
        html = "<html><body><p>Just text content</p></body></html>"
        processor = HTMLProcessor(html, {})
        result = processor.process()
        assert "Just text content" in result

    def test_processor_handles_all_resources(self):
        """Test that processor handles all provided resources without filtering"""
        html = """<html>
        <body>
            <script src="app.js"></script>
            <img src="image.png" alt="test">
            <link rel="stylesheet" href="style.css">
        </body>
        </html>"""

        resources = {
            "app.js": b'alert("hello world");',
            "image.png": b"fake_image_data",
            "style.css": b"body { color: red; }",
        }

        processor = HTMLProcessor(html, resources)
        result = processor.process()

        # All resources should be embedded as data URIs
        assert "data:text/javascript;base64," in result
        assert "data:image/png;base64," in result

    def test_css_embedding_with_mixed_resources(self):
        """Test CSS embedding works correctly with mixed resource types"""
        html = """<html>
        <head>
            <link rel="stylesheet" href="style.css">
        </head>
        <body>
            <script src="app.js"></script>
            <img src="image.png" alt="test">
        </body>
        </html>"""

        resources = {
            "app.js": b'console.log("test");',
            "image.png": b"fake_image_data",
            "style.css": b"body { background: blue; }",
        }

        processor = HTMLProcessor(html, resources)
        result = processor.process()

        assert '<style type="text/css">' in result
        assert "background: blue" in result
        assert "data:text/javascript;base64," in result
        assert "data:image/png;base64," in result

    def test_css_url_with_html_encoded_quotes(self):
        """Test that url() with &quot; in inline styles gets resolved to data URIs."""
        resources = {
            "https://example.com/dyn/assets/images/icons/acceo.jpg": b"\xff\xd8\xff\xe0fake-jpeg",
        }
        html = '<div style="background-image: url(&quot;/dyn/assets/images/icons/acceo.jpg&quot;);"></div>'
        processor = HTMLProcessor(html, resources)
        result = processor.process()

        assert "data:image/jpeg;base64," in result
        assert "/dyn/assets/images/icons/acceo.jpg" not in result

    def test_favicon_with_existing_resource(self):
        """Test that favicon links are preserved when the resource exists."""
        resources = {
            "favicon.ico": b"\x00\x00\x01\x00",
        }
        html = '<link rel="icon" href="favicon.ico">'
        processor = HTMLProcessor(html, resources)
        result = processor.process()

        # Should convert to data URI since resource exists
        assert "data:" in result

    def test_missing_favicon_removed(self):
        """Test that favicon links are removed when the resource is missing."""
        html = '<link rel="icon" href="missing-favicon.ico">'
        processor = HTMLProcessor(html, {})
        result = processor.process()

        assert "favicon" not in result

    def test_html_entities_preserved(self):
        """Test that HTML entities in content are preserved."""
        html = "<p>Hello &amp; world &lt;3</p>"
        processor = HTMLProcessor(html, {})
        result = processor.process()

        assert "&amp;" in result
        assert "&lt;" in result

    def test_html_comments_preserved(self):
        """Test that HTML comments pass through."""
        html = "<!-- comment --><p>text</p>"
        processor = HTMLProcessor(html, {})
        result = processor.process()

        assert "<!-- comment -->" in result
        assert "<p>text</p>" in result

    def test_doctype_preserved(self):
        """Test that DOCTYPE declarations pass through."""
        html = "<!DOCTYPE html><html><body>test</body></html>"
        processor = HTMLProcessor(html, {})
        result = processor.process()

        assert "<!DOCTYPE html>" in result
