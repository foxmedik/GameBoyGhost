from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Document:
    source_id: str
    kind: str
    url: str
    canonical_url: str
    title: str
    text: str
    raw: bytes
    ext: str = "md"
    author: str | None = None
    published_at: str | None = None
    license: str = "unknown"
    revision: str = ""
    http_status: int = 200
    content_type: str = "text/markdown"
    extra: dict = field(default_factory=dict)
