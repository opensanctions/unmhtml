"""Tests for load_mhtml."""

import base64

import pytest

from unmhtml import Document, Resource, load_mhtml

BASE_URL = "https://example.com/page.html"


class TestLoadMhtml:
    def test_load_simple_mhtml(self, simple_mhtml):
        document = load_mhtml(simple_mhtml)

        assert isinstance(document, Document)
        assert "<title>Test Page</title>" in document.html
        assert "<h1>Hello World</h1>" in document.html
        assert document.base_url == BASE_URL
        assert set(document.resources) == {
            "https://example.com/style.css",
            "https://example.com/image.png",
        }

    def test_resource_content_and_mime_types(self, simple_mhtml):
        document = load_mhtml(simple_mhtml)

        css = document.resources["https://example.com/style.css"]
        assert css.mime_type == "text/css"
        assert b"font-family: Arial" in css.data
        assert b"=" not in css.data  # quoted-printable decoded

        image = document.resources["https://example.com/image.png"]
        assert image.mime_type == "image/png"
        assert image.data.startswith(b"\x89PNG")

    def test_base64_encoded_html(self):
        html = base64.b64encode(
            b"<!DOCTYPE html><html><head><title>Test</title></head>"
            b"<body><h1>Hello World</h1></body></html>"
        ).decode("ascii")
        mhtml = f"""From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html
Content-Transfer-Encoding: base64

{html}

--test--
"""
        document = load_mhtml(mhtml)

        assert "<!DOCTYPE html>" in document.html
        assert "<h1>Hello World</h1>" in document.html
        assert document.resources == {}

    def test_bytes_and_str_input_agree(self, simple_mhtml):
        from_str = load_mhtml(simple_mhtml)
        from_bytes = load_mhtml(simple_mhtml.encode("utf-8"))

        assert from_str == from_bytes

    def test_single_part_html(self):
        mhtml = """Content-Type: text/html; charset=utf-8

<html><body><h1>Hello</h1></body></html>"""
        document = load_mhtml(mhtml)

        assert document.html == "<html><body><h1>Hello</h1></body></html>"
        assert document.resources == {}
        assert document.base_url is None

    def test_declared_charset_is_used(self):
        html = "Ångström".encode("iso-8859-1")
        mhtml = b"Content-Type: text/html; charset=iso-8859-1\n\n" + html
        document = load_mhtml(mhtml)

        assert "Ångström" in document.html

    def test_malformed_mhtml_raises(self, malformed_mhtml):
        with pytest.raises(ValueError, match="no text/html part"):
            load_mhtml(malformed_mhtml)

    def test_empty_mhtml_raises(self, empty_mhtml):
        with pytest.raises(ValueError, match="no text/html part"):
            load_mhtml(empty_mhtml)

    def test_binary_resource_from_unencoded_part(self):
        mhtml = """MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<html><body>Hi</body></html>

--test
Content-Type: application/octet-stream
Content-Location: https://example.com/blob.bin

data

--test--
"""
        document = load_mhtml(mhtml)

        blob = document.resources["https://example.com/blob.bin"]
        assert isinstance(blob, Resource)
        assert blob.mime_type == "application/octet-stream"
        assert blob.data.strip() == b"data"
