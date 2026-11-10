from __future__ import annotations

from dataclasses import dataclass, field

# Usage classes are ordered from most reusable to least.  A document may only
# be exported as body text when its class is in PUBLIC_BODY_CLASSES.
USAGE_CLASSES = (
    "public-domain",
    "permissive",
    "share-alike",
    "nc-nd",
    "copyrighted-local",
    "unknown",
)

PUBLIC_BODY_CLASSES = frozenset({"public-domain", "permissive", "share-alike"})
RESTRICTED_CLASSES = frozenset({"nc-nd", "copyrighted-local", "unknown"})
RETRIEVAL_METHODS = frozenset({"direct", "wayback", "manual"})


def validate_usage_class(value: str) -> str:
    if value not in USAGE_CLASSES:
        raise ValueError(
            f"invalid usage_class {value!r}; expected one of {', '.join(USAGE_CLASSES)}"
        )
    return value


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
    usage_class: str = "unknown"
    license_evidence_url: str = ""
    usage_notes: str = ""
    revision: str = ""
    http_status: int = 200
    content_type: str = "text/markdown"
    retrieved_via: str = "direct"
    snapshot_at: str | None = None
    snapshot_url: str | None = None
    extra: dict = field(default_factory=dict)
