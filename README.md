# unmhtml

[![PyPI version](https://badge.fury.io/py/unmhtml.svg)](https://pypi.org/project/unmhtml/)

Convert MHTML files to standalone HTML with embedded CSS and resources.

## Installation

```bash
pip install unmhtml
```

## Usage

```python
from unmhtml import MHTMLConverter

# Convert MHTML file to HTML (secure by default)
converter = MHTMLConverter()
html_content = converter.convert_file("saved_page.mhtml")

# Save as standalone HTML
with open("output.html", "w") as f:
    f.write(html_content)

# Unsafe conversion preserving original content
unsafe_converter = MHTMLConverter(
    remove_javascript=False,
    sanitize_css=False,
    remove_forms=False,
    remove_meta_redirects=False,
)
html_content = unsafe_converter.convert_file("trusted_page.mhtml")
```

## Features

- **Pure Python** - No external dependencies, uses only standard library
- **Standalone HTML** - Embeds CSS and converts resources to data URIs
- **Secure by Default** - All security sanitization enabled by default for safe processing
- **Graceful degradation** - Handles malformed MHTML files
- **Memory efficient** - Processes large files without excessive memory usage

## Security

The library is **secure by default** - all security features are enabled automatically to safely display untrusted content:

### Available Security Options (All Enabled by Default)

- **`remove_javascript=True`** - Removes `<script>` tags, event handlers (onclick, onload, etc.), and converts `javascript:` URLs to safe `#` anchors
- **`sanitize_css=True`** - Removes external CSS URLs (`http://`, `https://`, `//`, `/absolute`) while preserving relative URLs (`image.png`, `../fonts/font.woff`) and data URIs
- **`remove_forms=True`** - Removes form elements (`<form>`, `<input>`, `<textarea>`, `<select>`) that could submit data externally
- **`remove_meta_redirects=True`** - Removes dangerous meta tags (refresh redirects, set-cookie, dns-prefetch) that could be used maliciously

## Requirements

- Python 3.8+

## License

MIT
