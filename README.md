# unmhtml

[![PyPI version](https://badge.fury.net/py/unmhtml.svg)](https://pypi.org/project/unmhtml/)

Convert MHTML files — or any parsed HTML document with its resources — to standalone HTML with embedded CSS and resources.

## Installation

```bash
pip install unmhtml
```

The only runtime dependency is [nh3](https://pypi.org/project/nh3/) — Python
bindings to the Rust [ammonia](https://github.com/rust-ammonia/ammonia)
sanitizer (html5ever-based), which powers the structural sanitization pass.

## Usage

Convert an MHTML archive (secure by default):

```python
from pathlib import Path

from unmhtml import load_mhtml, to_standalone_html

document = load_mhtml(Path("saved_page.mhtml").read_bytes())
html = to_standalone_html(document)

with open("output.html", "w") as f:
    f.write(html)
```

Or work with HTML and resources you already have — for example, a rendered
page plus the bodies captured in a HAR archive:

```python
from unmhtml import Document, Resource, Security, to_standalone_html

document = Document(
    html=rendered_html,
    resources={
        "https://example.com/style.css": Resource(css_bytes, "text/css"),
        "https://example.com/logo.png": Resource(png_bytes, "image/png"),
    },
    base_url="https://example.com/page.html",
)
html = to_standalone_html(document)
```

References in the HTML are resolved against `base_url` and matched exactly
against the resource keys. CSS references inside an inlined stylesheet
resolve against the stylesheet's own URL, as CSS requires. What cannot be
resolved is neutralized — empty `src`, dropped stylesheet and icon links,
empty CSS `url()` — so the result never makes network requests.

## How conversion works

A structural sanitization pass runs before embedding; CSS sanitization runs
after. This means every reference the document can resolve is embedded as a
data URI, and only genuinely external CSS survives to be stripped. Malformed
MHTML raises `ValueError` instead of degrading silently.

## Security

Conversion is **secure by default** — all neutralizations are enabled, making
the result safe to display as untrusted content:

- **`remove_javascript=True`** — Removes `<script>` tags and their content, event handlers (onclick, onload, etc.), and `javascript:` URLs (the whole attribute is dropped)
- **`disable_forms=True`** — Defuses form elements: `<form>`, `<input>`, `<button>` and friends survive, but submission attributes (`action`, `method`, `formaction`, ...) are stripped
- **`remove_meta_redirects=True`** — Defuses dangerous meta tags: `http-equiv` refresh/set-cookie and `name` dns-prefetch attributes are stripped, leaving an inert stub
- **`sanitize_css=True`** — Removes CSS that can still make requests after embedding: `@import` statements, `url()` references that are not data URIs (fragment references like `url(#gradient)` are preserved), `expression()`, and `behavior:`

Adjust the policy with a `Security` value:

```python
from unmhtml import Security, to_standalone_html

# Preserve original content, including scripts and functional forms
html = to_standalone_html(
    document,
    security=Security(
        remove_javascript=False,
        disable_forms=False,
        remove_meta_redirects=False,
        sanitize_css=False,
    ),
)
```

### Threat model

The contract is reduction, not isolation: sanitization strips active
content, and the embedding step neutralizes every unresolvable reference, so
the output makes no network requests. This is defense in depth, **not** a
complete sandbox — untrusted documents must still be displayed in a sandboxed
context of your own, such as a sandboxed iframe without `allow-scripts` or
`allow-same-origin`, combined with a Content-Security-Policy.

Documented behavior: HTML comments are preserved verbatim (an accepted risk —
they are inert in modern browsers), and the output is an HTML fragment —
`html`/`head`/`body` wrappers are removed and the original doctype is
re-emitted verbatim.

## API

- `load_mhtml(data: str | bytes) -> Document` — parse MHTML content; the first `text/html` part becomes the document, other located parts become resources
- `Document(html, resources, base_url)` — a parsed document; resources map absolute URLs to `Resource(data, mime_type)`
- `Resource(data: bytes, mime_type: str | None)` — one resource; the MIME type is guessed from the reference URL when omitted
- `to_standalone_html(document, *, security=Security()) -> str` — return the document as a single self-contained HTML string

## Requirements

- Python 3.8+
- [nh3](https://pypi.org/project/nh3/) — the only dependency: zero transitive
  runtime dependencies, wheels for all major platforms

## License

MIT
