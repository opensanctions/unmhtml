# unmhtml

Python library that converts MHTML — or any HTML document with its
resources — to standalone sanitized HTML. Published on PyPI: public API
changes are breaking. Single runtime dependency, nh3 — keep it that way.

## Commands

```bash
uv sync --extra test  # env setup — use uv, not pip; the test extra carries pytest
uv run pytest         # tests; run before any change is done
uv run ruff check .
uv run ruff format .
```

Ruff runs its defaults; there is no project config to consult.

## Rules

- Supports Python 3.8, developed on 3.12 — keep syntax 3.8-compatible
  (`from __future__ import annotations` is what makes `X | Y` annotations
  legal).
- Constructing an `nh3.Cleaner` without explicit `clean_content_tags` panics
  when `style` is an allowed tag — the Rust-side default is
  `{'script', 'style'}`.
- Malformed MHTML raises `ValueError` by design; don't add silent
  degradation.
- Changes to sanitizer behavior or output shape need adversarial coverage
  (`tests/test_adversarial.py`).
- Releases: never bump `version` in `pyproject.toml` or `__version__`
  in `unmhtml/__init__.py` unless explicitly asked to cut a release —
  a breaking API change is not a bump trigger; the maintainer decides
  when to release. When asked, bump both together; publishing runs
  automatically from a GitHub release.
