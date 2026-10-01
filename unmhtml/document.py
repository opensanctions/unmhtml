"""The document model: parsed HTML plus the resources it references."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class Resource:
    """One resource belonging to a document.

    mime_type is the MIME type as known by the resource's source; when None,
    it is guessed from the reference URL at embedding time.
    """

    data: bytes
    mime_type: str | None = None


@dataclass(frozen=True)
class Document:
    """A parsed document.

    resources maps absolute URLs to their content. base_url is the URL the
    HTML was loaded from, used to resolve relative references against.
    """

    html: str
    resources: Mapping[str, Resource] = field(default_factory=dict)
    base_url: str | None = None
