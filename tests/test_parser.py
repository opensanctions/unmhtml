import base64
import email

import pytest

from unmhtml.parser import MHTMLParser


class TestMHTMLParser:
    def test_parse_simple_mhtml(self, simple_mhtml):
        """Test parsing a simple MHTML file"""
        parser = MHTMLParser(simple_mhtml)
        html, resources = parser.parse()

        # Check that HTML is extracted
        assert "<!DOCTYPE html>" in html
        assert "<title>Test Page</title>" in html
        assert "<h1>Hello World</h1>" in html

        # Check that resources are extracted
        assert "https://example.com/style.css" in resources
        assert "https://example.com/image.png" in resources

        # Check CSS content
        css_content = resources["https://example.com/style.css"]
        assert b"font-family: Arial" in css_content

        # Check image content (base64 decoded)
        image_content = resources["https://example.com/image.png"]
        assert len(image_content) > 0
        assert image_content.startswith(b"\x89PNG")  # PNG header

    def test_parse_malformed_mhtml(self, malformed_mhtml):
        """Test graceful handling of malformed MHTML"""
        parser = MHTMLParser(malformed_mhtml)
        html, resources = parser.parse()

        # Should return the original content as HTML
        assert html == malformed_mhtml
        assert resources == {}

    def test_parse_empty_mhtml(self, empty_mhtml):
        """Test parsing empty MHTML"""
        parser = MHTMLParser(empty_mhtml)
        html, resources = parser.parse()

        # Should return empty HTML and no resources
        assert html == ""
        assert resources == {}

    def test_decode_part_text(self):
        """Test text part decoding"""
        parser = MHTMLParser("")

        # Create a mock part for testing
        msg = email.message_from_string("""Content-Type: text/html
Content-Transfer-Encoding: quoted-printable

<html><body>Test</body></html>""")

        result = parser._decode_part(msg)
        assert "<html>" in result
        assert "Test" in result

    def test_decode_part_binary(self):
        """Test binary part decoding"""
        parser = MHTMLParser("")

        # Create a mock part for testing
        test_data = b"test binary data"
        encoded_data = base64.b64encode(test_data).decode("ascii")

        msg = email.message_from_string(f"""Content-Type: image/png
Content-Transfer-Encoding: base64

{encoded_data}""")

        result = parser._decode_part_binary(msg)
        assert result == test_data

    def test_decode_part_error_handling(self):
        """Test error handling in part decoding"""
        parser = MHTMLParser("")

        # Create a mock part with invalid base64
        msg = email.message_from_string("""Content-Type: text/html
Content-Transfer-Encoding: base64

invalid-base64-data!@#$%""")

        # Should return empty string on error
        result = parser._decode_part(msg)
        assert result == ""

        # Binary should return None on error
        result = parser._decode_part_binary(msg)
        assert result is None

    def test_decode_part_no_encoding(self):
        """Test decoding part without transfer encoding"""
        parser = MHTMLParser("")

        msg = email.message_from_string("""Content-Type: text/html

<html><body>Plain text</body></html>""")

        result = parser._decode_part(msg)
        assert "<html>" in result
        assert "Plain text" in result

    def test_decode_part_quoted_printable(self):
        """Test quoted-printable decoding"""
        parser = MHTMLParser("")

        msg = email.message_from_string("""Content-Type: text/html
Content-Transfer-Encoding: quoted-printable

<html><body>Test=20with=20spaces</body></html>""")

        result = parser._decode_part(msg)
        assert "Test with spaces" in result

    @pytest.mark.parametrize(
        "content_type,expected",
        [
            ("text/html", True),
            ("text/css", False),
            ("image/png", False),
            ("application/javascript", False),
        ],
    )
    def test_html_content_detection(self, content_type, expected):
        """Test HTML content type detection"""
        mhtml_content = f"""From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: {content_type}

<html><body>Test</body></html>

--test--
"""

        parser = MHTMLParser(mhtml_content)
        html, _ = parser.parse()

        if expected:
            assert "<html>" in html
        else:
            assert html == "" or "<html>" not in html
