import pytest

from unmhtml.converter import MHTMLConverter


class TestMHTMLConverter:
    def test_convert_simple_mhtml(self, simple_mhtml):
        """Test converting simple MHTML content"""
        converter = MHTMLConverter()
        result = converter.convert(simple_mhtml)

        # Check that HTML structure is preserved
        assert "<!DOCTYPE html>" in result
        assert "<title>Test Page</title>" in result
        assert "<h1>Hello World</h1>" in result

        # Check that CSS is embedded
        assert '<style type="text/css">' in result
        assert "font-family: Arial" in result
        assert '<link rel="stylesheet"' not in result

        # Check that image is converted to data URI
        assert 'src="data:image/png;base64,' in result
        assert 'src="image.png"' not in result

    def test_convert_file(self, temp_mhtml_file):
        """Test converting MHTML from file"""
        converter = MHTMLConverter()
        result = converter.convert_file(temp_mhtml_file)

        # Check that conversion worked
        assert "<!DOCTYPE html>" in result
        assert '<style type="text/css">' in result
        assert 'src="data:image/png;base64,' in result

    def test_convert_file_not_found(self):
        """Test error handling for non-existent file"""
        converter = MHTMLConverter()

        with pytest.raises(ValueError, match="Failed to read MHTML file"):
            converter.convert_file("nonexistent.mhtml")

    def test_convert_malformed_mhtml(self, malformed_mhtml):
        """Test converting malformed MHTML"""
        converter = MHTMLConverter()

        with pytest.raises(ValueError, match="Failed to convert MHTML"):
            converter.convert(malformed_mhtml)

    def test_convert_empty_mhtml(self, empty_mhtml):
        """Test converting empty MHTML"""
        converter = MHTMLConverter()

        with pytest.raises(ValueError, match="No HTML content found"):
            converter.convert(empty_mhtml)

    @pytest.mark.integration
    def test_convert_integration(self, simple_mhtml):
        """Test full integration of parser and processor"""
        converter = MHTMLConverter()
        result = converter.convert(simple_mhtml)

        # Verify the complete transformation pipeline

        # 1. HTML structure is preserved
        assert "<html>" in result
        assert "<head>" in result
        assert "<body>" in result

        # 2. CSS link is converted to embedded style
        assert '<link rel="stylesheet"' not in result
        assert '<style type="text/css">' in result

        # 3. CSS content is properly embedded
        assert "font-family: Arial, sans-serif" in result
        assert "color: #333" in result

        # 4. Images are converted to data URIs
        assert 'src="data:image/png;base64,' in result
        assert 'src="image.png"' not in result

        # 5. No external references remain
        assert "https://example.com/style.css" not in result
        assert "https://example.com/image.png" not in result

    def test_convert_with_encoding_issues(self):
        """Test handling of encoding issues in MHTML"""
        # Create MHTML with potential encoding issues
        mhtml_with_encoding = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html
Content-Transfer-Encoding: base64

PCFET0NUWVBFIGh0bWw+CjxodG1sPgo8aGVhZD4KICAgIDx0aXRsZT5UZXN0PC90aXRsZT4KPC9oZWFkPgo8Ym9keT4KICAgIDxoMT5IZWxsbyBXb3JsZDwvaDE+CjwvYm9keT4KPC9odG1sPg==

--test--
"""

        converter = MHTMLConverter()
        result = converter.convert(mhtml_with_encoding)

        # Check that base64 encoded HTML is properly decoded
        assert "<!DOCTYPE html>" in result
        assert "<h1>Hello World</h1>" in result

    def test_convert_preserves_html_structure(self, simple_mhtml):
        """Test that HTML structure and attributes are preserved"""
        converter = MHTMLConverter()
        result = converter.convert(simple_mhtml)

        # Check that HTML attributes are preserved
        assert 'alt="Test Image"' in result

        # Check that HTML structure is maintained
        assert "<head>" in result
        assert "<body>" in result
        assert "</html>" in result

    def test_convert_error_propagation(self):
        """Test that errors are properly propagated"""
        converter = MHTMLConverter()

        # Test with completely invalid input
        with pytest.raises(ValueError):
            converter.convert("")

        # Test with None input
        with pytest.raises(TypeError, match="must be a string"):
            converter.convert(None)

    def test_convert_multiple_resources(self):
        """Test conversion with multiple resources"""
        mhtml_with_multiple = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="style1.css">
    <link rel="stylesheet" href="style2.css">
</head>
<body>
    <img src="image1.png">
    <img src="image2.png">
</body>
</html>

--test
Content-Type: text/css
Content-Location: style1.css

body { color: red; }

--test
Content-Type: text/css
Content-Location: style2.css

h1 { color: blue; }

--test
Content-Type: image/png
Content-Transfer-Encoding: base64
Content-Location: image1.png

iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==

--test
Content-Type: image/png
Content-Transfer-Encoding: base64
Content-Location: image2.png

iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==

--test--
"""

        converter = MHTMLConverter()
        result = converter.convert(mhtml_with_multiple)

        # Check that all CSS is embedded
        assert '<style type="text/css">' in result
        assert "color: red" in result
        assert "color: blue" in result

        # Check that all images are converted
        assert result.count('src="data:image/png;base64,') == 2
        assert 'src="image1.png"' not in result
        assert 'src="image2.png"' not in result

    def test_convert_no_resources(self):
        """Test conversion with HTML that has no resources"""
        mhtml_no_resources = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <title>Simple Page</title>
</head>
<body>
    <h1>Hello World</h1>
    <p>This is a simple page with no external resources.</p>
</body>
</html>

--test--
"""

        converter = MHTMLConverter()
        result = converter.convert(mhtml_no_resources)

        # Should work fine with no resources
        assert "<!DOCTYPE html>" in result
        assert "<h1>Hello World</h1>" in result
        assert "This is a simple page" in result

    def test_convert_with_relative_paths(self):
        """Test conversion with relative resource paths"""
        mhtml_relative = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="./css/style.css">
</head>
<body>
    <img src="../images/logo.png">
</body>
</html>

--test
Content-Type: text/css
Content-Location: ./css/style.css

body { margin: 0; }

--test
Content-Type: image/png
Content-Transfer-Encoding: base64
Content-Location: ../images/logo.png

iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==

--test--
"""

        converter = MHTMLConverter()
        result = converter.convert(mhtml_relative)

        # Should handle relative paths
        assert '<style type="text/css">' in result
        assert "margin: 0" in result
        assert 'src="data:image/png;base64,' in result

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "",
            "not mhtml at all",
            "From: test\n\nEmpty content",
        ],
    )
    def test_convert_invalid_inputs(self, invalid_input):
        """Test conversion with various invalid inputs"""
        converter = MHTMLConverter()

        with pytest.raises(ValueError):
            converter.convert(invalid_input)

    def test_convert_with_remove_javascript_enabled(self):
        """Test conversion with JavaScript removal enabled (default behavior)"""
        mhtml_with_js = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <script>alert('test')</script>
</head>
<body onclick="malicious()">
    <h1>Hello World</h1>
    <p>Good content</p>
    <a href="javascript:alert('bad')">Bad link</a>
    <img src="image.png" onload="track()" alt="test">
</body>
</html>

--test
Content-Type: image/png
Content-Transfer-Encoding: base64
Content-Location: image.png

iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==

--test--
"""

        # Test with default behavior (remove_javascript=True)
        converter = MHTMLConverter()
        result = converter.convert(mhtml_with_js)

        # Should remove dangerous content
        assert "<script>" not in result
        assert "alert(" not in result
        assert "onclick=" not in result
        assert "onload=" not in result
        assert "javascript:" not in result
        assert 'href="#"' in result

        # Should preserve good content
        assert "<h1>Hello World</h1>" in result
        assert "<p>Good content</p>" in result
        assert 'alt="test"' in result
        assert 'src="data:image/png;base64,' in result

    def test_convert_with_remove_javascript_disabled(self):
        """Test conversion with JavaScript removal disabled (non-default)"""
        mhtml_with_js = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <script>alert('test')</script>
</head>
<body onclick="malicious()">
    <h1>Hello World</h1>
    <p>Good content</p>
    <a href="javascript:alert('bad')">Bad link</a>
</body>
</html>

--test--
"""

        # Test with remove_javascript=False (non-default)
        converter = MHTMLConverter(remove_javascript=False)
        result = converter.convert(mhtml_with_js)

        # Should preserve all content including dangerous parts
        assert "<script>" in result
        assert "alert(" in result
        assert "onclick=" in result
        assert "javascript:" in result

        # Should also preserve good content
        assert "<h1>Hello World</h1>" in result
        assert "<p>Good content</p>" in result

    def test_convert_file_with_remove_javascript(self, tmp_path):
        """Test file conversion with JavaScript removal"""
        mhtml_content = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <script>alert('test')</script>
</head>
<body>
    <h1>Hello World</h1>
</body>
</html>

--test--
"""

        # Create temporary file
        temp_file = tmp_path / "test.mhtml"
        temp_file.write_text(mhtml_content)

        try:
            # Test with default behavior (remove_javascript=True)
            converter = MHTMLConverter()
            result = converter.convert_file(str(temp_file))

            # Should remove script tags
            assert "<script>" not in result
            assert "alert(" not in result
            assert "<h1>Hello World</h1>" in result

        finally:
            pass  # tmp_path cleanup handled by pytest

    def test_convert_with_remove_forms_enabled(self):
        """Test conversion with form removal enabled (default behavior)"""
        mhtml_with_forms = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Hello World</h1>
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
    <fieldset>
        <legend>Additional Info</legend>
        <input type="checkbox" name="newsletter">
    </fieldset>
    <datalist id="suggestions">
        <option value="Option 1">
        <option value="Option 2">
    </datalist>
</body>
</html>

--test--
"""

        # Test with default behavior (remove_forms=True)
        converter = MHTMLConverter()
        result = converter.convert(mhtml_with_forms)

        # Should remove all form elements
        assert "<form" not in result
        assert "<input" not in result
        assert "<textarea" not in result
        assert "<select" not in result
        assert "<option" not in result
        assert "<button" not in result
        assert "<fieldset" not in result
        assert "<legend" not in result
        assert "<label" not in result
        assert "<datalist" not in result

        # Should preserve good content
        assert "<h1>Hello World</h1>" in result
        assert "<p>Good content</p>" in result
        assert "<title>Test Page</title>" in result

    def test_convert_with_remove_meta_redirects_enabled(self):
        """Test conversion with meta redirect removal enabled (default behavior)"""
        mhtml_with_meta = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0;url=http://evil.com">
    <meta http-equiv="set-cookie" content="session=abc123">
    <meta name="dns-prefetch" content="evil.com">
    <meta name="viewport" content="width=device-width">
    <title>Test Page</title>
</head>
<body>
    <h1>Hello World</h1>
    <p>Good content</p>
</body>
</html>

--test--
"""

        # Test with default behavior (remove_meta_redirects=True)
        converter = MHTMLConverter()
        result = converter.convert(mhtml_with_meta)

        # Should remove dangerous meta tags
        assert 'http-equiv="refresh"' not in result
        assert 'http-equiv="set-cookie"' not in result
        assert 'name="dns-prefetch"' not in result
        assert "http://evil.com" not in result
        assert "session=abc123" not in result

        # Should preserve good content
        assert 'name="viewport"' in result
        assert "<title>Test Page</title>" in result
        assert "<h1>Hello World</h1>" in result
        assert "<p>Good content</p>" in result

    def test_convert_with_remove_meta_redirects_disabled(self):
        """Test conversion with meta redirect removal disabled (non-default)"""
        mhtml_with_meta = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0;url=http://example.com">
    <meta http-equiv="set-cookie" content="test=value">
    <title>Test Page</title>
</head>
<body>
    <h1>Hello World</h1>
</body>
</html>

--test--
"""

        # Test with remove_meta_redirects=False (non-default)
        converter = MHTMLConverter(remove_meta_redirects=False)
        result = converter.convert(mhtml_with_meta)

        # Should preserve all meta tags
        assert 'http-equiv="refresh"' in result
        assert 'http-equiv="set-cookie"' in result
        assert "http://example.com" in result
        assert "test=value" in result

        # Should also preserve good content
        assert "<title>Test Page</title>" in result
        assert "<h1>Hello World</h1>" in result

    def test_convert_with_remove_forms_disabled(self):
        """Test conversion with form removal disabled (non-default)"""
        mhtml_with_forms = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Hello World</h1>
    <form action="/submit">
        <input type="text" name="name">
        <button type="submit">Submit</button>
    </form>
    <p>Good content</p>
</body>
</html>

--test--
"""

        # Test with remove_forms=False (non-default)
        converter = MHTMLConverter(remove_forms=False)
        result = converter.convert(mhtml_with_forms)

        # Should preserve all form elements
        assert "<form" in result
        assert "<input" in result
        assert "<button" in result
        assert 'action="/submit"' in result
        assert 'type="text"' in result
        assert 'type="submit"' in result

        # Should also preserve good content
        assert "<h1>Hello World</h1>" in result
        assert "<p>Good content</p>" in result

    def test_convert_with_multiple_security_options(self):
        """Test conversion with multiple security options enabled"""
        mhtml_with_threats = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <script>alert('malicious')</script>
    <style>
        body { background: url('http://evil.com/track.png'); }
        .test { behavior: url('evil.htc'); }
    </style>
</head>
<body onclick="track()">
    <h1>Hello World</h1>
    <form action="http://evil.com/submit">
        <input type="hidden" name="stolen" value="data">
        <button type="submit">Submit</button>
    </form>
    <p>Good content</p>
</body>
</html>

--test--
"""

        # Test with default behavior (all security options enabled)
        converter = MHTMLConverter()
        result = converter.convert(mhtml_with_threats)

        # Should remove JavaScript threats
        assert "<script>" not in result
        assert "alert(" not in result
        assert "onclick=" not in result

        # Should remove CSS threats
        assert "url(" not in result
        assert "behavior:" not in result
        assert "http://evil.com/track.png" not in result

        # Should remove form threats
        assert "<form" not in result
        assert "<input" not in result
        assert "<button" not in result
        assert "http://evil.com/submit" not in result

        # Should preserve good content
        assert "<h1>Hello World</h1>" in result
        assert "<p>Good content</p>" in result
        assert "<title>Test Page</title>" in result

    def test_javascript_file_resource_filtering(self):
        """Test that JavaScript files are filtered from resources when remove_javascript=True"""
        mhtml_with_js_file = """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
</head>
<body>
    <script src="app.js"></script>
    <img src="image.png" alt="test">
</body>
</html>

--test
Content-Type: text/javascript
Content-Location: app.js

alert('This should not be embedded');

--test
Content-Type: image/png  
Content-Transfer-Encoding: base64
Content-Location: image.png

iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==

--test--
"""

        # Test with remove_javascript=True (default)
        converter = MHTMLConverter()
        result = converter.convert(mhtml_with_js_file)

        # JavaScript file should NOT be embedded as data URI
        assert "data:text/javascript;base64," not in result
        # Image should still be embedded
        assert "data:image/png;base64," in result
        # Script tag should be completely removed by remove_javascript_content()
        assert "<script" not in result
        assert "app.js" not in result

        # Test with remove_javascript=False
        converter_unsafe = MHTMLConverter(remove_javascript=False)
        result_unsafe = converter_unsafe.convert(mhtml_with_js_file)

        # JavaScript file should be embedded as data URI
        assert "data:text/javascript;base64," in result_unsafe
        # Image should still be embedded
        assert "data:image/png;base64," in result_unsafe
