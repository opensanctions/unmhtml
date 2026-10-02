# unmhtml

[![PyPI version](https://badge.fury.io/py/unmhtml.svg)](https://pypi.org/project/unmhtml/)

Convert MHTML files — or any HTML document with its resources — to a single
standalone HTML string: CSS inlined, images and fonts embedded as data URIs,
active content sanitized for safe display.

## Installation

```bash
pip install unmhtml
```

## Usage

Convert an MHTML archive:

```python
from pathlib import Path

from unmhtml import load_mhtml, to_standalone_html

document = load_mhtml(Path("saved_page.mhtml").read_bytes())
html = to_standalone_html(document)
```

Or bring your own HTML and resources — a rendered page plus the bodies
captured in a HAR archive, for example:

```python
from unmhtml import Document, Resource, to_standalone_html

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

References resolve against `base_url` and match resource keys exactly; CSS
references inside a stylesheet resolve against the stylesheet's own URL.
Anything unresolvable is neutralized, so the result never makes network
requests.

## Security

Conversion is secure by default: scripts, event handlers and dangerous URLs
are removed, forms are defused, head furniture that could fetch or redirect
(`link`, `meta`, `base`) is dropped, and CSS that could still fetch or execute
is stripped. Each neutralization has its own flag on `Security`
(`remove_javascript`, `disable_forms`, `sanitize_css`), all defaulting to on:

```python
from unmhtml import Security, to_standalone_html

html = to_standalone_html(
    document,
    security=Security(remove_javascript=False),  # flags are independent
)
```

The contract is reduction, not isolation: the output makes no network
requests, but this is defense in depth, not a sandbox — display untrusted
output in a sandboxed context of your own, such as a sandboxed iframe
without `allow-scripts`, combined with a Content-Security-Policy.

## API

- `load_mhtml(data) -> Document` — parse MHTML content; raises `ValueError`
  when no HTML part exists
- `Document(html, resources, base_url)` — a parsed document; resources map
  absolute URLs to `Resource` values
- `Resource(data, mime_type)` — one resource; the MIME type is guessed from
  the reference URL when omitted
- `to_standalone_html(document, *, security=Security()) -> str` — the
  document as one self-contained HTML string

The output is an HTML fragment: `html`/`head`/`body` wrappers and head
furniture (`title`, `meta`, `link`, `base`) are removed and the original
doctype is re-emitted. HTML comments are removed, relative anchor targets
are made absolute against `base_url`, and every anchor carries
`rel="noopener noreferrer"`.

## Requirements

Python 3.8+. The single dependency is [nh3](https://pypi.org/project/nh3/)
(Python bindings to the Rust [ammonia](https://github.com/rust-ammonia/ammonia)
sanitizer) — zero transitive runtime dependencies, wheels for all major
platforms.

## License

MIT
