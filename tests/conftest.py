"""Pytest configuration and fixtures"""

import os
import tempfile

import pytest


@pytest.fixture
def simple_mhtml():
    """Simple MHTML content for testing"""
    return """From: <Saved by Blink>
Snapshot-Content-Location: https://example.com/page.html
Subject: Test Page
Date: Mon, 1 Jan 2024 12:00:00 GMT
MIME-Version: 1.0
Content-Type: multipart/related;
	type="text/html";
	boundary="----MultipartBoundary--test123"

------MultipartBoundary--test123
Content-Type: text/html
Content-ID: <frame-test@example.com>
Content-Transfer-Encoding: quoted-printable
Content-Location: https://example.com/page.html

<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>Hello World</h1>
    <img src="image.png" alt="Test Image">
</body>
</html>

------MultipartBoundary--test123
Content-Type: text/css
Content-Transfer-Encoding: quoted-printable
Content-Location: https://example.com/style.css

body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
}

h1 {
    color: #333;
}

------MultipartBoundary--test123
Content-Type: image/png
Content-Transfer-Encoding: base64
Content-Location: https://example.com/image.png

iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==

------MultipartBoundary--test123--
"""


@pytest.fixture
def malformed_mhtml():
    """Malformed MHTML content for testing error handling"""
    return """This is not a valid MHTML file
Just some random text
Without proper MIME structure
"""


@pytest.fixture
def empty_mhtml():
    """Empty MHTML content for testing"""
    return """From: <Saved by Blink>
MIME-Version: 1.0
Content-Type: multipart/related;
	boundary="----MultipartBoundary--empty"

------MultipartBoundary--empty--
"""


@pytest.fixture
def html_with_css():
    """HTML content with CSS links for testing"""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="https://example.com/external.css">
</head>
<body>
    <h1>Hello World</h1>
    <p>This is a test page.</p>
    <img src="image.png" alt="Test Image">
    <img src="https://example.com/logo.png" alt="Logo">
</body>
</html>"""


@pytest.fixture
def sample_css():
    """Sample CSS content for testing"""
    return """body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background: url('background.jpg');
}

h1 {
    color: #333;
}

.container {
    background-image: url("pattern.png");
}"""


@pytest.fixture
def sample_resources():
    """Sample resource map for testing"""
    return {
        "style.css": b"body { font-family: Arial; }",
        "https://example.com/external.css": b"h1 { color: red; }",
        "image.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x98\x81\xf1\x7f\x0f\x00\x02\x87\x01\x80\xebG\xba\x92\x00\x00\x00\x00IEND\xaeB`\x82",
        "https://example.com/logo.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x98\x81\xf1\x7f\x0f\x00\x02\x87\x01\x80\xebG\xba\x92\x00\x00\x00\x00IEND\xaeB`\x82",
        "background.jpg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf5\xff\xd9",
        "pattern.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x98\x81\xf1\x7f\x0f\x00\x02\x87\x01\x80\xebG\xba\x92\x00\x00\x00\x00IEND\xaeB`\x82",
    }


@pytest.fixture
def temp_mhtml_file(simple_mhtml):
    """Create a temporary MHTML file for testing"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mhtml", delete=False) as f:
        f.write(simple_mhtml)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)
